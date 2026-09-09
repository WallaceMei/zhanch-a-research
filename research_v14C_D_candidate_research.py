#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v14C D-candidate research script.

Research-only. Reads v14C P1~P5 full-result outputs, labels P1 entry features
with sell outcomes, and builds D0~D4 candidate summaries for the next research
stage. It does not modify strategy files, does not call order APIs, does not
relax deep_water, does not expand position caps, and does not auto-search
parameters.

Default input:
    role_rotation_result_bundle V140C_P1_P5_JQ_FULL

Default output:
    role_rotation_result_bundle V140C_D_candidate_research

Usage:
    import research_v14C_D_candidate_research as d
    d.run()
"""

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "role_rotation_observer"
INITIAL_CASH = 1000000.0
TRAIN_END = pd.Timestamp("2025-12-31")
VALIDATION_END = pd.Timestamp("2026-03-31")

FEATURE_COMPARE_COLUMNS = [
    "entry_open_ratio",
    "entry_day_ret",
    "entry_close_to_high",
    "entry_volume_ratio",
    "entry_auc_ratio",
    "entry_ma5_distance",
    "entry_ma10_distance",
    "breadth_up_ratio",
    "entry_score",
]


def resolve_dir(path):
    p = Path(path)
    return p if p.is_absolute() else Path.cwd() / p


def read_csv_safe(path):
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def df_to_markdown_compat(df, n=80):
    if df is None or df.empty:
        return "No feature comparison rows."
    view = df.head(n)
    try:
        return view.to_markdown(index=False)
    except Exception:
        return "```text\n" + view.to_string(index=False) + "\n```"


def normalize_dates(df):
    out = df.copy()
    for col in out.columns:
        if col == "date" or col.endswith("_date"):
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def load_tables(source_dir):
    names = [
        "role_rotation_daily_nav",
        "role_rotation_trades",
        "role_rotation_positions",
        "role_rotation_decisions",
        "role_rotation_summary",
        "role_rotation_cap_check",
        "p1_jq_entry_features",
        "p1_entry_feature_missing_summary",
        "p2_daily_nav",
        "p2_trades",
        "p2_positions",
        "p2_decisions",
        "p2_fast_loss_experiment_summary",
        "p3_daily_nav",
        "p3_trades",
        "p3_positions",
        "p3_decisions",
        "p3_cap_and_regime_summary",
        "p4_daily_nav",
        "p4_trades",
        "p4_positions",
        "p4_decisions",
        "p4_promotion_protection_summary",
        "p5_daily_nav",
        "p5_trades",
        "p5_positions",
        "p5_decisions",
        "p5_combined_observer_summary",
    ]
    tables = {}
    missing = []
    for name in names:
        path = source_dir / (name + ".csv")
        df = read_csv_safe(path)
        if df.empty and not path.exists():
            missing.append(name + ".csv")
        tables[name] = normalize_dates(df) if not df.empty else df
    return tables, missing


def pick_variant(df, variant, target_variant=None):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if target_variant and "variant" in out.columns:
        out = out[out["variant"].astype(str).eq(target_variant)].copy()
    if "variant" in out.columns:
        out["variant"] = variant
    return out


def classify_outcome(row):
    pnl_pct = row.get("pnl_pct", np.nan)
    pnl_val = row.get("pnl_val", np.nan)
    hold_days = row.get("hold_days_cal", np.nan)
    if not pd.isna(pnl_val) and pnl_val < 0 and not pd.isna(hold_days) and hold_days <= 5:
        return "fast_loss"
    if not pd.isna(pnl_pct) and pnl_pct > 0.20:
        return "super_meat_20"
    if not pd.isna(pnl_pct) and pnl_pct > 0.10:
        return "big_meat_10"
    if not pd.isna(pnl_val) and pnl_val < 0:
        return "normal_loss"
    if not pd.isna(pnl_val) and pnl_val > 0:
        return "normal_win"
    return "unknown"


def build_entry_outcome_labeled(tables):
    entries = tables.get("p1_jq_entry_features", pd.DataFrame()).copy()
    trades = tables.get("role_rotation_trades", pd.DataFrame()).copy()
    if entries.empty:
        return pd.DataFrame()
    if trades.empty:
        out = entries.copy()
        for col in ["exit_date", "exit_reason", "pnl_pct", "pnl_val", "hold_days_cal", "is_fast_loss", "is_big_meat_10", "is_super_meat_20", "trade_category", "outcome_group"]:
            out[col] = np.nan
        return out

    entries["date"] = pd.to_datetime(entries["date"], errors="coerce")
    if "variant" not in entries.columns:
        entries["variant"] = TARGET
    entries["entry_row_id"] = range(len(entries))

    trades["date"] = pd.to_datetime(trades["date"], errors="coerce")
    sells = trades[trades.get("action", "").astype(str).str.upper().eq("SELL")].copy()
    if "variant" not in sells.columns:
        sells["variant"] = TARGET
    sells = sells.sort_values(["variant", "stock", "date"])

    labeled = []
    for _, entry in entries.sort_values(["variant", "stock", "date", "entry_row_id"]).iterrows():
        variant = str(entry.get("variant", TARGET))
        stock = str(entry.get("stock"))
        entry_date = entry.get("date")
        candidates = sells[
            sells["variant"].astype(str).eq(variant)
            & sells["stock"].astype(str).eq(stock)
            & (sells["date"] >= entry_date)
        ].copy()
        row = entry.to_dict()
        if candidates.empty:
            row.update({
                "exit_date": pd.NaT,
                "exit_reason": "",
                "matched_sell_index": np.nan,
                "matched_sell_date": pd.NaT,
                "matched_sell_reason": "",
                "pnl_pct": np.nan,
                "pnl_val": np.nan,
                "hold_days_cal": np.nan,
                "is_fast_loss": False,
                "is_big_meat_10": False,
                "is_super_meat_20": False,
                "trade_category": "",
                "outcome_group": "unknown",
            })
        else:
            sell = candidates.iloc[0]
            pnl_pct = pd.to_numeric(pd.Series([sell.get("pnl_pct", np.nan)]), errors="coerce").iloc[0]
            pnl_val = pd.to_numeric(pd.Series([sell.get("pnl_val", np.nan)]), errors="coerce").iloc[0]
            hold_days = pd.to_numeric(pd.Series([sell.get("hold_days_cal", np.nan)]), errors="coerce").iloc[0]
            row.update({
                "exit_date": sell.get("date"),
                "exit_reason": sell.get("reason", ""),
                "matched_sell_index": sell.name,
                "matched_sell_date": sell.get("date"),
                "matched_sell_reason": sell.get("reason", ""),
                "pnl_pct": pnl_pct,
                "pnl_val": pnl_val,
                "hold_days_cal": hold_days,
                "is_fast_loss": bool(not pd.isna(pnl_val) and pnl_val < 0 and not pd.isna(hold_days) and hold_days <= 5),
                "is_big_meat_10": bool(not pd.isna(pnl_pct) and pnl_pct > 0.10),
                "is_super_meat_20": bool(not pd.isna(pnl_pct) and pnl_pct > 0.20),
                "trade_category": sell.get("trade_category", ""),
            })
            row["outcome_group"] = classify_outcome(row)
        labeled.append(row)
    return pd.DataFrame(labeled)


def reason_col_for_feature(feature):
    if feature == "entry_auc_ratio":
        return "entry_auc_missing_reason"
    if feature == "breadth_up_ratio":
        return "breadth_missing_reason"
    if feature == "entry_score":
        return "entry_score_missing_reason"
    return feature + "_missing_reason"


def build_entry_feature_outcome_compare(labeled):
    rows = []
    if labeled.empty:
        return pd.DataFrame(columns=[
            "outcome_group", "feature", "sample_count", "available_count", "missing_count",
            "available_rate", "mean", "median", "missing_reason_top1",
        ])
    for group in ["fast_loss", "big_meat_10", "super_meat_20", "normal_loss", "normal_win"]:
        g = labeled[labeled.get("outcome_group").astype(str).eq(group)].copy()
        for feature in FEATURE_COMPARE_COLUMNS:
            vals = pd.to_numeric(g.get(feature, pd.Series(dtype=float)), errors="coerce")
            available = int(vals.notna().sum())
            missing = int(len(g) - available)
            reason_col = reason_col_for_feature(feature)
            reasons = g.get(reason_col, pd.Series(dtype=str)).astype(str) if reason_col in g.columns else pd.Series(dtype=str)
            reasons = reasons[reasons.ne("") & reasons.ne("nan")]
            rows.append({
                "outcome_group": group,
                "feature": feature,
                "sample_count": int(len(g)),
                "available_count": available,
                "missing_count": missing,
                "available_rate": available / len(g) if len(g) else np.nan,
                "mean": vals.mean(),
                "median": vals.median(),
                "missing_reason_top1": reasons.mode().iloc[0] if not reasons.mode().empty and missing > 0 else "",
            })
    return pd.DataFrame(rows)


def max_drawdown(nav):
    if nav.empty or "nav" not in nav.columns:
        return np.nan
    s = pd.to_numeric(nav["nav"], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float((s / s.cummax() - 1).min())


def summarize_candidate(variant, daily_nav, trades, decisions, cap_check=None, cap_variant=None):
    rows = []
    if daily_nav.empty:
        return pd.DataFrame([{"variant": variant, "segment": "full", "status": "missing_daily_nav"}])
    nav = daily_nav.copy()
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    tr = trades.copy()
    if not tr.empty and "date" in tr.columns:
        tr["date"] = pd.to_datetime(tr["date"], errors="coerce")
    dec = decisions.copy()
    if not dec.empty and "date" in dec.columns:
        dec["date"] = pd.to_datetime(dec["date"], errors="coerce")
    for segment, mask in [
        ("full", pd.Series(True, index=nav.index)),
        ("train", nav["date"].le(TRAIN_END)),
        ("validation", nav["date"].gt(TRAIN_END) & nav["date"].le(VALIDATION_END)),
        ("oos", nav["date"].gt(VALIDATION_END)),
    ]:
        g = nav[mask].copy()
        if g.empty:
            continue
        sells = tr[tr.get("action", pd.Series(dtype=str)).astype(str).str.upper().eq("SELL")].copy() if not tr.empty else pd.DataFrame()
        if not sells.empty:
            sells = sells[sells["date"].ge(g["date"].min()) & sells["date"].le(g["date"].max())]
        pnl = pd.to_numeric(sells.get("pnl_val", pd.Series(dtype=float)), errors="coerce") if not sells.empty else pd.Series(dtype=float)
        pnl_pct = pd.to_numeric(sells.get("pnl_pct", pd.Series(dtype=float)), errors="coerce") if not sells.empty else pd.Series(dtype=float)
        hold = pd.to_numeric(sells.get("hold_days_cal", pd.Series(dtype=float)), errors="coerce") if not sells.empty else pd.Series(dtype=float)
        fast = pnl.lt(0) & hold.le(5)
        pos_profit = pnl[pnl.gt(0)].sort_values(ascending=False)
        seg_dec = dec.copy()
        if not seg_dec.empty:
            seg_dec = seg_dec[seg_dec["date"].ge(g["date"].min()) & seg_dec["date"].le(g["date"].max())]
        cap_exceeded_on_buy = int(pd.to_numeric(seg_dec.get("cap_exceeded_on_buy", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not seg_dec.empty else 0
        max_post_buy_ratio = pd.to_numeric(seg_dec.get("post_total_ratio", pd.Series(dtype=float)), errors="coerce").max() if not seg_dec.empty else np.nan
        cap_exceeded_after_mark_to_market = np.nan
        if cap_check is not None and isinstance(cap_check, pd.DataFrame) and not cap_check.empty:
            cc = cap_check.copy()
            if cap_variant and "variant" in cc.columns:
                cc = cc[cc["variant"].astype(str).eq(cap_variant)].copy()
            if "date" in cc.columns:
                cc["date"] = pd.to_datetime(cc["date"], errors="coerce")
                cc = cc[cc["date"].ge(g["date"].min()) & cc["date"].le(g["date"].max())]
            cap_exceeded_on_buy = int(pd.to_numeric(cc.get("cap_exceeded_on_buy", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not cc.empty else 0
            ratio_col = next((c for c in ["max_post_buy_ratio", "post_buy_total_ratio", "post_total_ratio", "post_buy_ratio"] if c in cc.columns), None)
            max_post_buy_ratio = pd.to_numeric(cc[ratio_col], errors="coerce").max() if ratio_col and not cc.empty else np.nan
            cap_exceeded_after_mark_to_market = int(pd.to_numeric(cc.get("cap_exceeded_after_mark_to_market", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if "cap_exceeded_after_mark_to_market" in cc.columns and not cc.empty else np.nan
        rows.append({
            "variant": variant,
            "segment": segment,
            "total_return": float(g["nav"].iloc[-1] / g["nav"].iloc[0] - 1) if len(g) > 1 else 0.0,
            "annual_return": float((g["nav"].iloc[-1] / g["nav"].iloc[0] - 1) * 252 / max(len(g), 1)) if len(g) > 1 else 0.0,
            "max_drawdown": max_drawdown(g),
            "sharpe": float(g["nav"].pct_change().mean() / g["nav"].pct_change().std() * math.sqrt(252)) if len(g) > 2 and g["nav"].pct_change().std() else np.nan,
            "win_rate": float(pnl.gt(0).sum() / len(pnl)) if len(pnl) else np.nan,
            "trade_count": int(len(sells)),
            "fast_loss_count": int(fast.sum()) if len(sells) else 0,
            "fast_loss_amount": float(-pnl[fast].sum()) if len(sells) else 0.0,
            "big_meat_count": int(pnl_pct.gt(0.10).sum()) if len(sells) else 0,
            "super_meat_count": int(pnl_pct.gt(0.20).sum()) if len(sells) else 0,
            "top3_profit_concentration": float(pos_profit.head(3).sum() / pos_profit.sum()) if pos_profit.sum() else np.nan,
            "cap_exceeded_on_buy": cap_exceeded_on_buy,
            "max_post_buy_ratio": max_post_buy_ratio,
            "cap_exceeded_after_mark_to_market": cap_exceeded_after_mark_to_market,
        })
    return pd.DataFrame(rows)


def segment_returns(summary):
    result = {}
    if summary.empty:
        return result
    for seg in ["train", "validation", "oos"]:
        g = summary[summary["segment"].astype(str).eq(seg)]
        result[seg + "_return"] = g["total_return"].iloc[0] if not g.empty and "total_return" in g.columns else np.nan
    return result


def filter_existing_variant(tables, prefix, target_variant, candidate_name):
    daily = pick_variant(tables.get(prefix + "_daily_nav", pd.DataFrame()), candidate_name, target_variant)
    trades = pick_variant(tables.get(prefix + "_trades", pd.DataFrame()), candidate_name, target_variant)
    positions = pick_variant(tables.get(prefix + "_positions", pd.DataFrame()), candidate_name, target_variant)
    decisions = pick_variant(tables.get(prefix + "_decisions", pd.DataFrame()), candidate_name, target_variant)
    return daily, trades, positions, decisions


def original_candidate(tables, candidate_name):
    daily = pick_variant(tables.get("role_rotation_daily_nav", pd.DataFrame()), candidate_name, TARGET)
    trades = pick_variant(tables.get("role_rotation_trades", pd.DataFrame()), candidate_name, TARGET)
    positions = pick_variant(tables.get("role_rotation_positions", pd.DataFrame()), candidate_name, TARGET)
    decisions = pick_variant(tables.get("role_rotation_decisions", pd.DataFrame()), candidate_name, TARGET)
    return daily, trades, positions, decisions


def replay_candidate(tables, candidate_name, policy, start_date, end_date):
    try:
        import research_v14C_P1_to_P5_master as master
    except Exception as exc:
        raise RuntimeError("Cannot import research_v14C_P1_to_P5_master for combo replay: {}".format(exc))
    path = master.simulate_replay_path(tables, candidate_name, policy, start_date, end_date)
    return path["daily_nav"], path["trades"], path["positions"], path["decisions"]


def candidate_paths(tables, start_date, end_date):
    specs = [
        ("D0_original_role_rotation", "existing_original", None, None),
        ("D1_cap_fixed_only", "existing_p3", "p3_cap_fixed", None),
        ("D2_no_promotion_take_profit", "existing_p4", "p4_no_promotion", None),
        ("D3_no_promotion_take_profit_plus_cap_fixed", "replay", None, {"no_promotion": True, "cap_fixed": True}),
        ("D4_promotion_protect_plus_cap_fixed", "replay", None, {"promotion_protect": True, "cap_fixed": True}),
    ]
    result = {}
    for name, mode, variant, policy in specs:
        if mode == "existing_original":
            daily, trades, positions, decisions = original_candidate(tables, name)
        elif mode == "existing_p3":
            daily, trades, positions, decisions = filter_existing_variant(tables, "p3", variant, name)
        elif mode == "existing_p4":
            daily, trades, positions, decisions = filter_existing_variant(tables, "p4", variant, name)
        else:
            daily, trades, positions, decisions = replay_candidate(tables, name, policy, start_date, end_date)
        summary = summarize_candidate(
            name, daily, trades, decisions,
            cap_check=tables.get("role_rotation_cap_check", pd.DataFrame()) if name == "D0_original_role_rotation" else None,
            cap_variant=TARGET if name == "D0_original_role_rotation" else None,
        )
        extra = segment_returns(summary)
        for key, val in extra.items():
            summary[key] = val
        result[name] = {
            "daily_nav": daily,
            "trades": trades,
            "positions": positions,
            "decisions": decisions,
            "summary": summary,
        }
    return result


def full_row(summary):
    if summary is None or summary.empty:
        return pd.Series(dtype=object)
    g = summary[summary["segment"].astype(str).eq("full")]
    return g.iloc[0] if not g.empty else pd.Series(dtype=object)


def fmt_pct(x):
    return "NA" if pd.isna(x) else "{:.2%}".format(float(x))


def report_answer(candidate_outputs, compare, missing, source_dir, output_dir):
    d0 = full_row(candidate_outputs.get("D0_original_role_rotation", {}).get("summary"))
    d1 = full_row(candidate_outputs.get("D1_cap_fixed_only", {}).get("summary"))
    d2 = full_row(candidate_outputs.get("D2_no_promotion_take_profit", {}).get("summary"))
    d3 = full_row(candidate_outputs.get("D3_no_promotion_take_profit_plus_cap_fixed", {}).get("summary"))
    d4 = full_row(candidate_outputs.get("D4_promotion_protect_plus_cap_fixed", {}).get("summary"))

    def better(a, b, metric):
        if pd.isna(a.get(metric, np.nan)) or pd.isna(b.get(metric, np.nan)):
            return "evidence_missing"
        return "yes" if a.get(metric) > b.get(metric) else "no"

    fast_vs_meat = compare[compare["outcome_group"].isin(["fast_loss", "big_meat_10", "super_meat_20"])].copy()
    lines = [
        "# v14C D Candidate Research Report",
        "",
        "## 1. Research Boundary",
        "",
        "* This is a research branch only.",
        "* Not a mainline strategy.",
        "* Not a live-trading version.",
        "* Does not relax deep_water.",
        "* Does not expand position caps.",
        "* Does not auto-search parameters.",
        "",
        "## 2. Inputs",
        "",
        "* source_dir: `{}`".format(source_dir),
        "* output_dir: `{}`".format(output_dir),
        "* missing_inputs: `{}`".format(",".join(missing) if missing else "none"),
        "",
        "## 3. D Candidate Summary",
        "",
        "| Candidate | Return | MaxDD | WinRate | Trades | FastLossAmt |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, data in candidate_outputs.items():
        r = full_row(data["summary"])
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            name,
            fmt_pct(r.get("total_return", np.nan)),
            fmt_pct(r.get("max_drawdown", np.nan)),
            fmt_pct(r.get("win_rate", np.nan)),
            int(r.get("trade_count", 0)) if not pd.isna(r.get("trade_count", np.nan)) else "NA",
            "{:.2f}".format(float(r.get("fast_loss_amount", np.nan))) if not pd.isna(r.get("fast_loss_amount", np.nan)) else "NA",
        ))
    lines += [
        "",
        "## 4. Key Questions",
        "",
        "* P4 no_promotion 是否稳定优于原版：{}。需要同时看 full / train / validation / oos，不可只看单段收益。".format(better(d2, d0, "total_return")),
        "* cap_fixed 是否应该作为默认基础修复：{}。核心证据看 cap_exceeded_on_buy、max_drawdown 与收益牺牲。".format(better(d1, d0, "total_return")),
        "* promotion 是否应该废除：若 D2/D3 在 validation/oos 同时优于 D0，才进入下一轮；否则只保留研究假设。",
        "* promotion_protect 是否有保留价值：对比 D4 与 D2/D3，若收益更低且回撤未改善，则暂不主推。",
        "* P5 combined 为什么不作为主候选：P5 混合多个组件，归因不干净，容易把多个效应叠加成过拟合。",
        "* P1 entry features 是否能区分 fast_loss 和 big_meat：见 `entry_feature_outcome_compare.csv`，若关键字段缺失率高，则不能下强结论。",
        "",
        "## 5. Entry Feature Outcome Compare",
        "",
        df_to_markdown_compat(fast_vs_meat, 80),
        "",
        "## 6. Next Step",
        "",
        "Only candidates that survive train / validation / oos, cap check, fast-loss check, and feature attribution should enter v1.4.0D research. Do not promote directly to mainline.",
    ]
    return "\n".join(lines)


def run(
    source_dir="role_rotation_result_bundle V140C_P1_P5_JQ_FULL",
    output_dir="role_rotation_result_bundle V140C_D_candidate_research",
):
    source = resolve_dir(source_dir)
    output = resolve_dir(output_dir)
    if not source.exists():
        raise FileNotFoundError("source_dir not found: {}".format(source))
    output.mkdir(parents=True, exist_ok=True)

    tables, missing = load_tables(source)
    labeled = build_entry_outcome_labeled(tables)
    compare = build_entry_feature_outcome_compare(labeled)
    write_csv(labeled, output / "entry_feature_outcome_labeled.csv")
    write_csv(compare, output / "entry_feature_outcome_compare.csv")

    daily = tables.get("role_rotation_daily_nav", pd.DataFrame())
    if daily.empty or "date" not in daily.columns:
        raise RuntimeError("role_rotation_daily_nav.csv is required to infer date range")
    start_date = pd.to_datetime(daily["date"], errors="coerce").min().strftime("%Y-%m-%d")
    end_date = pd.to_datetime(daily["date"], errors="coerce").max().strftime("%Y-%m-%d")

    candidates = candidate_paths(tables, start_date, end_date)
    all_summary = []
    for name, data in candidates.items():
        write_csv(data["daily_nav"], output / "{}_daily_nav.csv".format(name))
        write_csv(data["trades"], output / "{}_trades.csv".format(name))
        write_csv(data["positions"], output / "{}_positions.csv".format(name))
        write_csv(data["decisions"], output / "{}_decisions.csv".format(name))
        write_csv(data["summary"], output / "{}_summary.csv".format(name))
        all_summary.append(data["summary"])

    summary_all = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    write_csv(summary_all, output / "D_candidate_summary_all.csv")

    report = report_answer(candidates, compare, missing, source, output)
    (output / "v14C_D_candidate_research_report.md").write_text(report, encoding="utf-8-sig")

    manifest = {
        "script": Path(__file__).name,
        "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(source),
        "output_dir": str(output),
        "research_only": True,
        "not_mainline_strategy": True,
        "not_live_trading": True,
        "no_deep_water_relaxation": True,
        "no_position_expansion": True,
        "no_auto_parameter_search": True,
        "missing_inputs": missing,
        "candidates": list(candidates.keys()),
        "outputs": sorted([p.name for p in output.iterdir() if p.is_file()]),
    }
    (output / "v14C_D_candidate_research_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("D_CANDIDATE|output_dir={}".format(output))
    print("D_CANDIDATE|report={}".format(output / "v14C_D_candidate_research_report.md"))
    print("D_CANDIDATE|done=1")
    return {
        "output_dir": output,
        "report": output / "v14C_D_candidate_research_report.md",
        "manifest": output / "v14C_D_candidate_research_manifest.json",
    }


if __name__ == "__main__":
    run()
