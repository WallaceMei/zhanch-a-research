#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compare v1.4.0B shadow rotation logs and run a first-pass overfit audit.

This script is read-only for strategy/log inputs. It writes only analysis
artifacts requested by the task:

* v1.4.0B_fix_日志对比分析_过拟合初检报告.md
* v1.4.0B_fix_log_compare_outputs.xlsx
* a few companion CSV tables for auditability
"""

from __future__ import annotations

import math
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "log"
NOTEBOOK_DIR = ROOT / "过拟合检测"
REPORT_PATH = ROOT / "v1.4.0B_fix_日志对比分析_过拟合初检报告.md"
XLSX_PATH = ROOT / "v1.4.0B_fix_log_compare_outputs.xlsx"

PRIMARY_LOGS = {
    "v13A": "jq_v13A_20260101_20260614.log",
    "v130A": "jq_v130A_20260101_20260614.log",
    "v14A": "jq_v14A_20260101_20260614.log",
    "v14B": "jq_v140B_20260101_20260614.log",
    "v14B_fix": "jq_v140B_fix_20260101_20260614.log",
}

REFERENCE_LOGS = {
    "v121A_ref": "jq_v121A_20250701_20260614.log",
}


LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-\s+"
    r"(?P<level>\w+)\s+-\s+(?P<payload>.*)$"
)


def resolve_log_path(base_name: str) -> Optional[Path]:
    candidates = [
        LOG_DIR / base_name,
        LOG_DIR / (base_name + ".txt"),
    ]
    if base_name.endswith(".log"):
        candidates.append(LOG_DIR / (base_name[:-4] + ".log.txt"))
    for path in candidates:
        if path.exists():
            return path
    return None


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def split_event_payload(payload: str) -> Tuple[str, Dict[str, str]]:
    parts = payload.strip().split("|")
    event = parts[0].strip()
    fields: Dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key.strip()] = value.strip()
    return event, fields


def load_records(label: str, path: Path) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    text = read_text(path)
    for line_no, line in enumerate(text.splitlines(), 1):
        match = LINE_RE.match(line)
        if not match:
            continue
        payload = match.group("payload")
        if "|" not in payload:
            continue
        event, fields = split_event_payload(payload)
        row: Dict[str, object] = {
            "variant": label,
            "line_no": line_no,
            "timestamp": pd.to_datetime(match.group("ts"), errors="coerce"),
            "event": event,
            "payload_raw": payload,
        }
        row.update(fields)
        rows.append(row)
    return pd.DataFrame(rows)


def parse_pct(value) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    text = str(value).strip()
    if text in ("", "NA", "None", "nan"):
        return np.nan
    text = text.replace("%", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return np.nan


def parse_num(value) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    text = str(value).strip()
    if text in ("", "NA", "None", "nan"):
        return np.nan
    text = text.replace("%", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return np.nan


def event_frame(records: pd.DataFrame, event: str) -> pd.DataFrame:
    if records.empty:
        return pd.DataFrame()
    df = records[records["event"] == event].copy()
    if "date" in df.columns:
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date_dt"] = pd.to_datetime(df["timestamp"].dt.date, errors="coerce")
    return df


def normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in ("nav", "payoff"):
        if col in out.columns:
            out[col] = out[col].map(parse_num)
    for col in ("daily_ret", "max_drawdown", "win_rate"):
        if col in out.columns:
            out[col + "_pct"] = out[col].map(parse_pct)
    for col in ("positions", "closed_trades"):
        if col in out.columns:
            out[col] = out[col].map(parse_num)
    out = out.sort_values("date_dt")
    out["nav_return_pct"] = (out["nav"] - 1.0) * 100.0
    return out


def normalize_trades(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    numeric_cols = [
        "trade_ret",
        "buy_amount_accum",
        "sell_amount_accum",
        "final_sell_amount",
        "sell_value_accum",
        "final_sell_value",
        "total_sell_value",
        "total_buy_value",
        "realized_pnl_value",
        "accounting_error",
        "hold_days",
        "win",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col + ("_pct" if col == "trade_ret" else "")] = out[col].map(parse_pct if col == "trade_ret" else parse_num)
    if "trade_ret_pct" not in out.columns:
        out["trade_ret_pct"] = np.nan
    if "realized_pnl_value" not in out.columns:
        out["realized_pnl_value"] = np.nan
    else:
        out["realized_pnl_value"] = out["realized_pnl_value"].map(parse_num)
    if "entry_type" not in out.columns:
        out["entry_type"] = "unknown"
    out["bucket"] = np.where(out["entry_type"].eq("shadow_satellite"), "satellite", "core")
    return out.sort_values("timestamp")


def normalize_shadow_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    pct_cols = [
        "total_position_ratio",
        "satellite_position_ratio",
        "core_position_ratio",
    ]
    for col in pct_cols:
        if col in out.columns:
            out[col + "_pct"] = out[col].map(parse_pct)
    num_cols = [
        "watch_pool_size",
        "satellite_count",
        "core_count",
        "confirm_checked",
        "confirm_passed",
        "satellite_buys",
        "satellite_sells",
        "replace_count",
        "expired_count",
    ]
    for col in num_cols:
        if col in out.columns:
            out[col] = out[col].map(parse_num)
    return out.sort_values("date_dt")


def infer_start_cash(buys: pd.DataFrame, trades: pd.DataFrame) -> float:
    if not buys.empty and {"order_value", "actual_pos_ratio"}.issubset(buys.columns):
        tmp = buys.copy()
        tmp["order_value_num"] = tmp["order_value"].map(parse_num)
        tmp["actual_pos_ratio_pct"] = tmp["actual_pos_ratio"].map(parse_pct)
        tmp = tmp[(tmp["order_value_num"] > 0) & (tmp["actual_pos_ratio_pct"] > 0)]
        if not tmp.empty:
            return float((tmp.iloc[0]["order_value_num"] / (tmp.iloc[0]["actual_pos_ratio_pct"] / 100.0)))
    if not trades.empty and "total_buy_value" in trades.columns:
        val = trades["total_buy_value"].map(parse_num).dropna()
        if not val.empty:
            # These backtests are normally initialized with 100k. Round to keep
            # cost sensitivity readable when only trade logs are available.
            return 100000.0
    return 100000.0


def max_drawdown_from_nav(nav: pd.Series) -> float:
    if nav.empty:
        return np.nan
    peak = nav.cummax()
    dd = nav / peak - 1.0
    return float(abs(dd.min()) * 100.0)


def safe_sharpe(returns: pd.Series) -> float:
    returns = pd.Series(returns).dropna()
    if returns.empty:
        return np.nan
    sigma = returns.std(ddof=1)
    if pd.isna(sigma) or sigma <= 1e-12:
        return np.nan
    return float(returns.mean() / sigma * math.sqrt(252.0))


def daily_returns_from_nav(daily: pd.DataFrame) -> pd.Series:
    if daily.empty or "nav" not in daily.columns:
        return pd.Series(dtype=float)
    nav = daily.sort_values("date_dt")["nav"].dropna()
    if nav.empty:
        return pd.Series(dtype=float)
    return nav.pct_change().dropna()


def annual_return_from_daily(returns: pd.Series) -> float:
    returns = pd.Series(returns).dropna()
    if returns.empty:
        return np.nan
    total = float((1.0 + returns).prod() - 1.0)
    return float(((1.0 + total) ** (252.0 / len(returns)) - 1.0) * 100.0)


def max_consecutive_negative(returns: pd.Series) -> int:
    best = 0
    current = 0
    for val in pd.Series(returns).fillna(0):
        if val < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def build_nav_stability(daily: pd.DataFrame, variant: str) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    daily = daily.sort_values("date_dt").reset_index(drop=True)
    returns = daily_returns_from_nav(daily)
    if returns.empty:
        return pd.DataFrame([{"variant": variant, "sample_days": int(len(daily))}])
    nav = daily["nav"].dropna()
    rows = [{
        "variant": variant,
        "sample_days": int(len(daily)),
        "return_days": int(len(returns)),
        "final_nav": float(nav.iloc[-1]) if not nav.empty else np.nan,
        "total_return_pct": float((nav.iloc[-1] - 1.0) * 100.0) if not nav.empty else np.nan,
        "annual_return_proxy_pct": annual_return_from_daily(returns),
        "annual_vol_proxy_pct": float(returns.std(ddof=1) * math.sqrt(252.0) * 100.0) if len(returns) > 1 else np.nan,
        "daily_sharpe_proxy": safe_sharpe(returns),
        "max_drawdown_from_nav_pct": max_drawdown_from_nav(nav),
        "positive_day_rate_pct": float((returns > 0).mean() * 100.0),
        "avg_daily_ret_pct": float(returns.mean() * 100.0),
        "median_daily_ret_pct": float(returns.median() * 100.0),
        "best_daily_ret_pct": float(returns.max() * 100.0),
        "worst_daily_ret_pct": float(returns.min() * 100.0),
        "daily_ret_std_pct": float(returns.std(ddof=1) * 100.0) if len(returns) > 1 else np.nan,
        "max_consecutive_negative_days": max_consecutive_negative(returns),
    }]
    return pd.DataFrame(rows)


def summarize_trade_group(df: pd.DataFrame, variant: str, bucket: str) -> Dict[str, object]:
    if df.empty:
        return {
            "variant": variant,
            "bucket": bucket,
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "avg_trade_ret_pct": np.nan,
            "median_trade_ret_pct": np.nan,
            "avg_win_pct": np.nan,
            "avg_loss_pct": np.nan,
            "payoff": np.nan,
            "max_gain_pct": np.nan,
            "max_loss_pct": np.nan,
            "realized_pnl_sum": 0.0,
            "top_profit_share_pct": np.nan,
            "top3_profit_share_pct": np.nan,
        }
    rets = df["trade_ret_pct"].dropna()
    wins = df[df["trade_ret_pct"] > 0]
    losses = df[df["trade_ret_pct"] <= 0]
    profit_sum = wins["realized_pnl_value"].clip(lower=0).sum()
    positive_pnls = wins["realized_pnl_value"].clip(lower=0).sort_values(ascending=False)
    top1 = positive_pnls.iloc[0] / profit_sum * 100 if profit_sum > 0 and len(positive_pnls) else np.nan
    top3 = positive_pnls.head(3).sum() / profit_sum * 100 if profit_sum > 0 and len(positive_pnls) else np.nan
    avg_win = wins["trade_ret_pct"].mean() if not wins.empty else np.nan
    avg_loss = losses["trade_ret_pct"].mean() if not losses.empty else np.nan
    payoff = abs(avg_win / avg_loss) if pd.notna(avg_win) and pd.notna(avg_loss) and avg_loss != 0 else np.nan
    return {
        "variant": variant,
        "bucket": bucket,
        "trade_count": int(len(df)),
        "win_count": int(len(wins)),
        "loss_count": int(len(losses)),
        "win_rate_pct": len(wins) / len(df) * 100.0 if len(df) else 0.0,
        "avg_trade_ret_pct": rets.mean() if not rets.empty else np.nan,
        "median_trade_ret_pct": rets.median() if not rets.empty else np.nan,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "payoff": payoff,
        "max_gain_pct": rets.max() if not rets.empty else np.nan,
        "max_loss_pct": rets.min() if not rets.empty else np.nan,
        "realized_pnl_sum": float(df["realized_pnl_value"].sum(skipna=True)),
        "top_profit_share_pct": top1,
        "top3_profit_share_pct": top3,
    }


def build_monthly(daily: pd.DataFrame, variant: str) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    rows = []
    prev_nav = 1.0
    for month, g in daily.groupby(daily["date_dt"].dt.to_period("M")):
        g = g.sort_values("date_dt")
        end_nav = float(g.iloc[-1]["nav"])
        rows.append({
            "variant": variant,
            "month": str(month),
            "start_nav_base": prev_nav,
            "end_nav": end_nav,
            "month_return_pct": (end_nav / prev_nav - 1.0) * 100.0 if prev_nav else np.nan,
            "month_max_drawdown_pct": max_drawdown_from_nav(g["nav"]),
            "trading_days": int(len(g)),
            "positive_daily_rate_pct": float((g["daily_ret_pct"] > 0).mean() * 100.0) if "daily_ret_pct" in g else np.nan,
        })
        prev_nav = end_nav
    return pd.DataFrame(rows)


def build_rolling(daily: pd.DataFrame, variant: str) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    rows = []
    daily = daily.sort_values("date_dt").reset_index(drop=True)
    daily_ret = daily_returns_from_nav(daily)
    for window in (20, 40):
        if len(daily) < window:
            continue
        returns = daily["nav"] / daily["nav"].shift(window) - 1.0
        valid = returns.dropna() * 100.0
        rolling_sharpe = daily_ret.rolling(window).apply(lambda x: safe_sharpe(pd.Series(x)), raw=False).dropna()
        rows.append({
            "variant": variant,
            "window_days": window,
            "sample_count": int(len(valid)),
            "positive_rate_pct": float((valid > 0).mean() * 100.0),
            "negative_rate_pct": float((valid <= 0).mean() * 100.0),
            "avg_return_pct": float(valid.mean()),
            "median_return_pct": float(valid.median()),
            "min_return_pct": float(valid.min()),
            "max_return_pct": float(valid.max()),
            "avg_sharpe_proxy": float(rolling_sharpe.mean()) if not rolling_sharpe.empty else np.nan,
            "median_sharpe_proxy": float(rolling_sharpe.median()) if not rolling_sharpe.empty else np.nan,
            "min_sharpe_proxy": float(rolling_sharpe.min()) if not rolling_sharpe.empty else np.nan,
        })
    return pd.DataFrame(rows)


def build_block_bootstrap(daily: pd.DataFrame, variant: str, n_bootstrap: int = 500) -> pd.DataFrame:
    returns = daily_returns_from_nav(daily)
    n = len(returns)
    if n < 20:
        return pd.DataFrame([{
            "variant": variant,
            "sample_days": int(n),
            "bootstrap_available": 0,
            "reason": "sample_too_small",
        }])
    block_size = max(2, min(int(round(n ** (1.0 / 3.0))), max(2, n // 2)))
    rng = np.random.RandomState(42)
    values = returns.to_numpy(dtype=float)
    original_sharpe = safe_sharpe(returns)
    original_return = float((1.0 + returns).prod() - 1.0)
    boot_returns = []
    boot_sharpes = []
    boot_drawdowns = []
    for _ in range(n_bootstrap):
        blocks = []
        block_count = int(math.ceil(n / float(block_size)))
        for _ in range(block_count):
            start = rng.randint(0, n - block_size + 1)
            blocks.append(values[start:start + block_size])
        sample = np.concatenate(blocks)[:n]
        sample_ser = pd.Series(sample)
        boot_returns.append(float((1.0 + sample_ser).prod() - 1.0))
        boot_sharpes.append(safe_sharpe(sample_ser))
        boot_nav = (1.0 + sample_ser).cumprod()
        boot_drawdowns.append(max_drawdown_from_nav(boot_nav))
    boot_returns_s = pd.Series(boot_returns).dropna()
    boot_sharpes_s = pd.Series(boot_sharpes).dropna()
    boot_drawdowns_s = pd.Series(boot_drawdowns).dropna()
    sharpe_percentile = float((boot_sharpes_s <= original_sharpe).mean() * 100.0) if not boot_sharpes_s.empty and pd.notna(original_sharpe) else np.nan
    return_percentile = float((boot_returns_s <= original_return).mean() * 100.0) if not boot_returns_s.empty else np.nan
    return pd.DataFrame([{
        "variant": variant,
        "sample_days": int(n),
        "bootstrap_available": 1,
        "n_bootstrap": int(n_bootstrap),
        "block_size": int(block_size),
        "original_total_return_pct": original_return * 100.0,
        "bootstrap_median_return_pct": float(boot_returns_s.median() * 100.0) if not boot_returns_s.empty else np.nan,
        "bootstrap_p05_return_pct": float(boot_returns_s.quantile(0.05) * 100.0) if not boot_returns_s.empty else np.nan,
        "bootstrap_p95_return_pct": float(boot_returns_s.quantile(0.95) * 100.0) if not boot_returns_s.empty else np.nan,
        "prob_total_return_below_zero_pct": float((boot_returns_s < 0).mean() * 100.0) if not boot_returns_s.empty else np.nan,
        "original_sharpe_proxy": original_sharpe,
        "bootstrap_median_sharpe_proxy": float(boot_sharpes_s.median()) if not boot_sharpes_s.empty else np.nan,
        "bootstrap_p05_sharpe_proxy": float(boot_sharpes_s.quantile(0.05)) if not boot_sharpes_s.empty else np.nan,
        "bootstrap_p95_sharpe_proxy": float(boot_sharpes_s.quantile(0.95)) if not boot_sharpes_s.empty else np.nan,
        "original_sharpe_percentile_pct": sharpe_percentile,
        "original_return_percentile_pct": return_percentile,
        "bootstrap_median_max_drawdown_pct": float(boot_drawdowns_s.median()) if not boot_drawdowns_s.empty else np.nan,
        "bootstrap_p95_max_drawdown_pct": float(boot_drawdowns_s.quantile(0.95)) if not boot_drawdowns_s.empty else np.nan,
        "reason": "",
    }])


def build_cost_sensitivity(daily: pd.DataFrame, trades: pd.DataFrame, buys: pd.DataFrame, variant: str) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    final_nav = float(daily.iloc[-1]["nav"])
    start_cash = infer_start_cash(buys, trades)
    turnover = 0.0
    if not trades.empty:
        buy = trades["total_buy_value"].map(parse_num) if "total_buy_value" in trades else pd.Series(dtype=float)
        sell = trades["total_sell_value"].map(parse_num) if "total_sell_value" in trades else pd.Series(dtype=float)
        turnover = float(buy.sum(skipna=True) + sell.sum(skipna=True))
    rows = []
    for bps in (5, 10, 20, 50):
        nav_drag = turnover * (bps / 10000.0) / start_cash
        rows.append({
            "variant": variant,
            "extra_cost_bps_per_side_on_closed_turnover": bps,
            "estimated_start_cash": start_cash,
            "closed_turnover": turnover,
            "nav_drag": nav_drag,
            "final_nav_after_cost": final_nav - nav_drag,
            "total_return_after_cost_pct": (final_nav - nav_drag - 1.0) * 100.0,
        })
    return pd.DataFrame(rows)


def summarize_variant(label: str, records: pd.DataFrame, log_path: Optional[Path]) -> Dict[str, object]:
    daily = normalize_daily(event_frame(records, "DAILY_SUMMARY"))
    trades = normalize_trades(event_frame(records, "TRADE_CLOSE"))
    buys = event_frame(records, "BIGMEAT_BUY")
    shadow_daily = normalize_shadow_daily(event_frame(records, "SHADOW_DAILY_SUMMARY"))

    final = daily.iloc[-1] if not daily.empty else pd.Series(dtype=object)
    start_date = str(daily.iloc[0]["date_dt"].date()) if not daily.empty else ""
    end_date = str(daily.iloc[-1]["date_dt"].date()) if not daily.empty else ""

    core_trades = trades[trades["bucket"] == "core"] if not trades.empty else pd.DataFrame()
    sat_trades = trades[trades["bucket"] == "satellite"] if not trades.empty else pd.DataFrame()
    all_trade_stats = summarize_trade_group(trades, label, "all")
    core_stats = summarize_trade_group(core_trades, label, "core")
    sat_stats = summarize_trade_group(sat_trades, label, "satellite")

    accounting_warn_count = int((records["event"] == "TRADE_ACCOUNTING_WARN").sum()) if not records.empty else 0
    accounting_error_count = int((trades.get("accounting_error", pd.Series(dtype=float)).map(parse_num) == 1).sum()) if not trades.empty and "accounting_error" in trades else 0

    shadow_fields = {}
    if not shadow_daily.empty:
        for col in ("total_position_ratio_pct", "satellite_position_ratio_pct", "core_position_ratio_pct"):
            shadow_fields["avg_" + col] = float(shadow_daily[col].mean()) if col in shadow_daily else np.nan
            shadow_fields["max_" + col] = float(shadow_daily[col].max()) if col in shadow_daily else np.nan
        shadow_fields["max_satellite_count"] = int(shadow_daily["satellite_count"].max()) if "satellite_count" in shadow_daily else 0
        shadow_fields["satellite_days"] = int((shadow_daily.get("satellite_count", pd.Series(dtype=float)) > 0).sum())
        shadow_fields["replace_count_sum"] = float(shadow_daily.get("replace_count", pd.Series(dtype=float)).sum(skipna=True))
    else:
        shadow_fields = {
            "avg_total_position_ratio_pct": np.nan,
            "max_total_position_ratio_pct": np.nan,
            "avg_satellite_position_ratio_pct": np.nan,
            "max_satellite_position_ratio_pct": np.nan,
            "avg_core_position_ratio_pct": np.nan,
            "max_core_position_ratio_pct": np.nan,
            "max_satellite_count": 0,
            "satellite_days": 0,
            "replace_count_sum": 0,
        }

    events = {
        "watch_pool_add": int((records["event"] == "WATCH_POOL_ADD").sum()) if not records.empty else 0,
        "shadow_confirm_pass": int((records["event"] == "SHADOW_CONFIRM_PASS").sum()) if not records.empty else 0,
        "shadow_buy_submit": int((records["event"] == "SHADOW_BUY_SUBMIT").sum()) if not records.empty else 0,
        "shadow_buy_confirmed": int((records["event"] == "SHADOW_BUY_CONFIRMED").sum()) if not records.empty else 0,
        "shadow_buy_skip": int((records["event"] == "SHADOW_BUY_SKIP").sum()) if not records.empty else 0,
        "shadow_exit_confirmed": int((records["event"] == "SHADOW_EXIT_CONFIRMED").sum()) if not records.empty else 0,
        "shadow_replace_execute": int((records["event"] == "SHADOW_REPLACE_EXECUTE").sum()) if not records.empty else 0,
        "breadth_gap_sell": int((records["event"] == "BREADTH_GAP_RISK_SELL").sum()) if not records.empty else 0,
    }

    return {
        "variant": label,
        "log_file": str(log_path.name if log_path else ""),
        "date_start": start_date,
        "date_end": end_date,
        "daily_rows": int(len(daily)),
        "final_nav": float(final.get("nav", np.nan)),
        "total_return_pct": float((final.get("nav", np.nan) - 1.0) * 100.0) if pd.notna(final.get("nav", np.nan)) else np.nan,
        "max_drawdown_pct": float(final.get("max_drawdown_pct", daily["max_drawdown_pct"].max() if not daily.empty and "max_drawdown_pct" in daily else np.nan)),
        "closed_trades": int(final.get("closed_trades", len(trades))) if pd.notna(final.get("closed_trades", np.nan)) else int(len(trades)),
        "win_rate_pct": float(final.get("win_rate_pct", all_trade_stats["win_rate_pct"])),
        "payoff": float(final.get("payoff", all_trade_stats["payoff"])),
        "trade_count_log": int(len(trades)),
        "core_realized_pnl": core_stats["realized_pnl_sum"],
        "satellite_realized_pnl": sat_stats["realized_pnl_sum"],
        "all_realized_pnl": all_trade_stats["realized_pnl_sum"],
        "core_trade_count": core_stats["trade_count"],
        "satellite_trade_count": sat_stats["trade_count"],
        "satellite_win_rate_pct": sat_stats["win_rate_pct"],
        "satellite_avg_ret_pct": sat_stats["avg_trade_ret_pct"],
        "satellite_median_ret_pct": sat_stats["median_trade_ret_pct"],
        "satellite_max_loss_pct": sat_stats["max_loss_pct"],
        "top_profit_share_pct": all_trade_stats["top_profit_share_pct"],
        "top3_profit_share_pct": all_trade_stats["top3_profit_share_pct"],
        "accounting_warn_count": accounting_warn_count,
        "accounting_error_count": accounting_error_count,
        **shadow_fields,
        **events,
    }


def build_notebook_reference() -> pd.DataFrame:
    rows = []
    notebooks = sorted(NOTEBOOK_DIR.glob("*.ipynb")) if NOTEBOOK_DIR.exists() else []
    if not notebooks:
        return pd.DataFrame([{
            "notebook_read_success": 0,
            "notebook_path": "",
            "cell_count": 0,
            "method": "notebook_missing",
            "notebook_method": "",
            "offline_adaptation": "未找到 notebook；仅按日志分析要求执行",
            "status": "missing",
        }])
    for nb_path in notebooks:
        try:
            nb = json.loads(read_text(nb_path))
            cell_count = len(nb.get("cells", []))
            text = "\n".join("".join(cell.get("source", [])) for cell in nb.get("cells", []))
            method_specs = [
                ("样本量检查", "_check_sample_size" in text, "daily_rows / closed_trades / satellite_trade_count 风险标记", "offline_implemented"),
                ("净值曲线稳定性", "_annual_return" in text and "_max_drawdown" in text, "nav_stability sheet：年化 proxy、波动、夏普、回撤、连续亏损天数", "offline_implemented"),
                ("滚动夏普稳定性", "check_temporal_stability" in text, "rolling sheet：20/40 日滚动收益和滚动夏普 proxy", "offline_implemented"),
                ("月度收益稳定性", "rolling" in text or "稳定" in text, "monthly sheet：月度收益、月内回撤、日胜率", "offline_implemented"),
                ("块自助法", "block_bootstrap_sensitivity" in text, "block_bootstrap sheet：块自助收益/夏普分布、亏损概率", "offline_implemented"),
                ("成本敏感性", "transaction_cost_sensitivity" in text, "cost_sensitivity sheet：按 TRADE_CLOSE 闭合成交额估算额外成本拖累", "offline_implemented"),
                ("Chow 结构断点", "chow_test" in text, "本轮未直接做显著性检验；用滚动 20/40 日和月度稳定性替代观察", "reference_only"),
                ("滚动样本外验证", "rolling_cross_validation" in text, "缺少可重训策略函数和多参数矩阵，改为样本外风险文字提示", "reference_only"),
                ("近似 PBO", "approximate_pbo" in text, "缺少策略参数搜索矩阵，不能直接计算真实 PBO；改为参数过拟合风险说明", "reference_only"),
                ("get_backtest 在线数据", "get_backtest" in text, "本地无法调用聚宽在线回测 ID；改用日志 DAILY_SUMMARY / TRADE_CLOSE 离线检测", "online_unavailable"),
                ("实盘 vs 回测", "live_vs_backtest_comparison" in text, "缺少实盘收益序列；仅提示样本外风险", "data_unavailable"),
            ]
            for method, present, adaptation, status in method_specs:
                rows.append({
                    "notebook_read_success": 1,
                    "notebook_path": str(nb_path),
                    "cell_count": cell_count,
                    "method": method,
                    "notebook_method": "present" if present else "not_detected",
                    "offline_adaptation": adaptation,
                    "status": status if present else "not_detected",
                })
        except Exception as exc:
            rows.append({
                "notebook_read_success": 0,
                "notebook_path": str(nb_path),
                "cell_count": 0,
                "method": "read_failed",
                "notebook_method": "",
                "offline_adaptation": str(exc),
                "status": "read_failed",
            })
    return pd.DataFrame(rows)


def build_overfit_flags(
    summary: pd.DataFrame,
    monthly: pd.DataFrame,
    rolling: pd.DataFrame,
    trade_stats: pd.DataFrame,
    nav_stability: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        v = row["variant"]
        m = monthly[monthly["variant"] == v]
        r20 = rolling[(rolling["variant"] == v) & (rolling["window_days"] == 20)]
        r40 = rolling[(rolling["variant"] == v) & (rolling["window_days"] == 40)]
        sat = trade_stats[(trade_stats["variant"] == v) & (trade_stats["bucket"] == "satellite")]
        ns = nav_stability[nav_stability["variant"] == v]
        bs = bootstrap[bootstrap["variant"] == v]
        flags = []
        if row.get("daily_rows", 0) < 120:
            flags.append("daily_sample_below_120_days")
        if row.get("closed_trades", 0) < 30:
            flags.append("closed_trade_sample_below_30")
        if row.get("top_profit_share_pct", np.nan) >= 45:
            flags.append("top1_profit_concentration_high")
        if row.get("top3_profit_share_pct", np.nan) >= 75:
            flags.append("top3_profit_concentration_high")
        if not m.empty and (m["month_return_pct"] > 0).mean() < 0.5:
            flags.append("monthly_positive_rate_below_50pct")
        if not r20.empty and float(r20.iloc[0]["positive_rate_pct"]) < 50:
            flags.append("rolling20_positive_rate_below_50pct")
        if not r40.empty and float(r40.iloc[0]["positive_rate_pct"]) < 50:
            flags.append("rolling40_positive_rate_below_50pct")
        if not r20.empty and pd.notna(r20.iloc[0].get("min_sharpe_proxy", np.nan)) and float(r20.iloc[0]["min_sharpe_proxy"]) < -1.0:
            flags.append("rolling20_min_sharpe_below_minus_1")
        if not ns.empty and ns.iloc[0].get("max_consecutive_negative_days", 0) >= 5:
            flags.append("negative_streak_ge_5_days")
        if not bs.empty and bs.iloc[0].get("prob_total_return_below_zero_pct", 0) >= 10:
            flags.append("bootstrap_loss_probability_ge_10pct")
        if row.get("satellite_trade_count", 0) > 0 and row.get("satellite_trade_count", 0) < 10:
            flags.append("satellite_sample_small")
        if not sat.empty and float(sat.iloc[0].get("top_profit_share_pct", np.nan)) >= 60:
            flags.append("satellite_top_profit_concentration_high")
        if not sat.empty and float(sat.iloc[0].get("top3_profit_share_pct", np.nan)) >= 85:
            flags.append("satellite_top3_profit_concentration_high")
        if row.get("accounting_warn_count", 0) or row.get("accounting_error_count", 0):
            flags.append("accounting_warning_or_error")
        if v == "v14B" and row.get("max_satellite_count", 0) > 1:
            flags.append("v14B_single_satellite_limit_breached_in_log")
        risk = "low"
        if len(flags) >= 3:
            risk = "high"
        elif len(flags) >= 1:
            risk = "medium"
        rows.append({
            "variant": v,
            "risk_level": risk,
            "flag_count": len(flags),
            "flags": ", ".join(flags) if flags else "none",
        })
    return pd.DataFrame(rows)


def fmt_pct(x, digits=2) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}%"


def fmt_num(x, digits=4) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{digits}f}"


def table_text(df: pd.DataFrame, empty_msg: str = "无数据。") -> str:
    if df.empty:
        return empty_msg
    try:
        return df.to_markdown(index=False, floatfmt=".4f")
    except Exception:
        return "```text\n" + df.to_string(index=False) + "\n```"



def check_v14b_fix_anomalies(records: pd.DataFrame) -> List[Dict[str, str]]:
    anomalies = []
    if records.empty:
        return anomalies

    shadow_daily = records[records["event"] == "SHADOW_DAILY_SUMMARY"].copy()
    if not shadow_daily.empty:
        shadow_daily["satellite_count_num"] = shadow_daily["satellite_count"].map(parse_num)
        for _, row in shadow_daily[shadow_daily["satellite_count_num"] > 1].iterrows():
            anomalies.append({"date": str(row["timestamp"].date()), "event": "SHADOW_DAILY_SUMMARY", "reason": "max_satellite_count > 1", "sample": row.get("payload_raw", "")})

        shadow_daily["replace_count_num"] = shadow_daily["replace_count"].map(parse_num)
        for _, row in shadow_daily[shadow_daily["replace_count_num"] > 0].iterrows():
            anomalies.append({"date": str(row["timestamp"].date()), "event": "SHADOW_DAILY_SUMMARY", "reason": "replace_count > 0", "sample": row.get("payload_raw", "")})

        shadow_daily["total_pos_pct"] = shadow_daily["total_position_ratio"].map(parse_pct)
        for _, row in shadow_daily[shadow_daily["total_pos_pct"] > 75.001].iterrows():
            anomalies.append({"date": str(row["timestamp"].date()), "event": "SHADOW_DAILY_SUMMARY", "reason": "total_position_ratio > 75%", "sample": row.get("payload_raw", "")})

    buy_submits = records[records["event"] == "SHADOW_BUY_SUBMIT"].copy()
    if not buy_submits.empty:
        buy_submits["date_str"] = buy_submits["timestamp"].dt.date
        counts = buy_submits.groupby("date_str").size()
        for d in counts[counts > 1].index:
            samples = buy_submits[buy_submits["date_str"] == d]
            anomalies.append({"date": str(d), "event": "SHADOW_BUY_SUBMIT", "reason": "Same day SHADOW_BUY_SUBMIT > 1", "sample": " | ".join(samples["payload_raw"].astype(str).tolist()[:2])})

    for _, row in records[records["event"] == "SHADOW_REPLACE_EXECUTE"].iterrows():
        anomalies.append({"date": str(row["timestamp"].date()), "event": "SHADOW_REPLACE_EXECUTE", "reason": "SHADOW_REPLACE_EXECUTE found", "sample": row.get("payload_raw", "")})

    for _, row in records[records["event"] == "TRADE_ACCOUNTING_WARN"].iterrows():
        anomalies.append({"date": str(row["timestamp"].date()), "event": "TRADE_ACCOUNTING_WARN", "reason": "TRADE_ACCOUNTING_WARN found", "sample": row.get("payload_raw", "")})

    trades = records[records["event"] == "TRADE_CLOSE"].copy()
    if not trades.empty and "accounting_error" in trades.columns:
        trades["err_num"] = trades["accounting_error"].map(parse_num)
        for _, row in trades[trades["err_num"] == 1].iterrows():
            anomalies.append({"date": str(row["timestamp"].date()), "event": "TRADE_CLOSE", "reason": "accounting_error=1", "sample": row.get("payload_raw", "")})

    return anomalies

def comparison_rows(summary: pd.DataFrame) -> pd.DataFrame:
    base = summary.set_index("variant")
    rows = []
    if "v14B_fix" not in base.index:
        return pd.DataFrame()
    b = base.loc["v14B_fix"]
    for other in ("v14B", "v14A", "v13A", "v130A"):
        if other not in base.index:
            continue
        o = base.loc[other]
        rows.append({
            "compare": f"v14B_fix_vs_{other}",
            "nav_delta": b["final_nav"] - o["final_nav"],
            "return_delta_pct": b["total_return_pct"] - o["total_return_pct"],
            "max_drawdown_delta_pct": b["max_drawdown_pct"] - o["max_drawdown_pct"],
            "win_rate_delta_pct": b["win_rate_pct"] - o["win_rate_pct"],
            "payoff_delta": b["payoff"] - o["payoff"],
            "satellite_pnl_delta": b["satellite_realized_pnl"] - o["satellite_realized_pnl"],
        })
    return pd.DataFrame(rows)

from typing import List, Dict
import numpy as np

def make_report(
    summary: pd.DataFrame,
    compare: pd.DataFrame,
    trade_stats: pd.DataFrame,
    monthly: pd.DataFrame,
    rolling: pd.DataFrame,
    cost: pd.DataFrame,
    nav_stability: pd.DataFrame,
    bootstrap: pd.DataFrame,
    notebook_ref: pd.DataFrame,
    overfit: pd.DataFrame,
    diagnostics: pd.DataFrame,
    anomalies: List[Dict[str, str]],
):
    base = summary.set_index("variant")
    v14b_fix = base.loc["v14B_fix"] if "v14B_fix" in base.index else pd.Series(dtype=object)
    v14b = base.loc["v14B"] if "v14B" in base.index else pd.Series(dtype=object)
    v14a = base.loc["v14A"] if "v14A" in base.index else pd.Series(dtype=object)
    v13a = base.loc["v13A"] if "v13A" in base.index else pd.Series(dtype=object)
    v130a = base.loc["v130A"] if "v130A" in base.index else pd.Series(dtype=object)

    def better_nav(a, b):
        return pd.notna(a.get("final_nav", np.nan)) and pd.notna(b.get("final_nav", np.nan)) and a["final_nav"] > b["final_nav"]

    v14b_fix_better_v14b = better_nav(v14b_fix, v14b) if pd.notna(v14b.get("final_nav")) else "不确定"
    if v14b_fix_better_v14b is True: v14b_fix_better_v14b = "是"
    elif v14b_fix_better_v14b is False: v14b_fix_better_v14b = "否"

    v14b_fix_better_v14a = better_nav(v14b_fix, v14a) if pd.notna(v14a.get("final_nav")) else "不确定"
    if v14b_fix_better_v14a is True: v14b_fix_better_v14a = "是"
    elif v14b_fix_better_v14a is False: v14b_fix_better_v14a = "否"

    original_best_nav = max(v13a.get("final_nav", 0), v130a.get("final_nav", 0))
    if pd.isna(original_best_nav) or original_best_nav == 0:
        v14b_fix_better_original = "不确定"
    else:
        v14b_fix_better_original = "是" if v14b_fix.get("final_nav", 0) >= original_best_nav else "否"

    sat_positive = v14b_fix.get("satellite_realized_pnl", 0) > 0
    if pd.isna(v14b_fix.get("satellite_realized_pnl")): sat_positive_str = "样本不足"
    else: sat_positive_str = "是" if sat_positive else "否"

    # Concentration
    sat_trade_stats = trade_stats[(trade_stats["variant"] == "v14B_fix") & (trade_stats["bucket"] == "satellite")]
    if sat_trade_stats.empty or sat_trade_stats.iloc[0].get("trade_count", 0) < 5:
        sat_conc_str = "样本不足"
    else:
        sat_conc_str = "是" if sat_trade_stats.iloc[0].get("top3_profit_share_pct", 0) >= 80 else "否"

    v14b_fix_risk = overfit.set_index("variant").loc["v14B_fix"]["risk_level"] if "v14B_fix" in set(overfit["variant"]) else "unknown"
    risk_cn = {"low": "低", "medium": "中", "high": "高"}.get(v14b_fix_risk, "中")

    bug_fixed = "是" if len(anomalies) == 0 else "否"

    summary_view = summary[[
        "variant", "final_nav", "total_return_pct", "max_drawdown_pct",
        "closed_trades", "win_rate_pct", "payoff", "core_realized_pnl",
        "satellite_realized_pnl", "satellite_trade_count",
        "avg_total_position_ratio_pct", "avg_core_position_ratio_pct",
        "avg_satellite_position_ratio_pct", "max_satellite_count",
        "top_profit_share_pct", "accounting_warn_count", "accounting_error_count",
    ]].copy()

    lines = []
    lines.append("# v1.4.0B_fix 日志对比分析与过拟合初检报告")
    lines.append("")
    lines.append("## 1. 约束与异常检查")
    lines.append("")
    if anomalies:
        lines.append("发现以下异常：")
        for a in anomalies:
            lines.append(f"- **异常日期**: {a['date']}")
            lines.append(f"  - **异常事件**: {a['event']}")
            lines.append(f"  - **异常原因推测**: {a['reason']}")
            lines.append(f"  - **对应日志样例**: `{a['sample']}`")
    else:
        lines.append("未发现约束突破或账本异常。各项约束全部生效。")
    lines.append("")
    lines.append("## 2. 最终判断")
    lines.append("")
    lines.append(f"* v14B_fix 是否修复单卫星仓 bug：{bug_fixed}")
    lines.append(f"* v14B_fix 是否优于 v14B 未修复版：{v14b_fix_better_v14b}")
    lines.append(f"* v14B_fix 是否优于 v14A：{v14b_fix_better_v14a}")
    lines.append(f"* v14B_fix 是否接近或超过 v13A / v130A：{v14b_fix_better_original}")
    lines.append(f"* 卫星仓修复后是否仍为正贡献：{sat_positive_str}")
    lines.append(f"* 卫星仓收益是否仍高度集中：{sat_conc_str}")
    lines.append(f"* 过拟合风险：{risk_cn}")
    lines.append("* 是否建议继续优化 v14B_fix：否")
    lines.append("* 是否建议进入主线：否")
    lines.append("")
    lines.append("## 3. 核心指标对比")
    lines.append("")
    lines.append(table_text(summary_view))
    lines.append("")
    lines.append("## 4. 版本差异 (vs v14B_fix)")
    lines.append("")
    lines.append(table_text(compare, "无可比数据。"))
    lines.append("")
    lines.append("## 5. 核心仓 / 卫星仓归因")
    lines.append("")
    lines.append(table_text(trade_stats))
    lines.append("")
    lines.append("## 6. 月度与风险数据")
    lines.append("")
    lines.append(table_text(monthly, "无月度数据。"))
    lines.append("")
    lines.append(table_text(overfit, "无过拟合数据。"))
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8-sig")

def write_outputs(tables: Dict[str, pd.DataFrame]):
    last_error = None
    for engine in ("openpyxl", "xlsxwriter"):
        try:
            with pd.ExcelWriter(XLSX_PATH, engine=engine) as writer:
                for name, df in tables.items():
                    sheet = name[:31]
                    df.to_excel(writer, sheet_name=sheet, index=False)
            print(f"LOG_COMPARE|excel_export={XLSX_PATH.name}|engine={engine}")
            return
        except Exception as exc:
            last_error = exc
    print(f"LOG_COMPARE_WARN|excel_export_failed=1|reason={last_error}")


def main():
    diagnostics_rows = []
    all_records = []
    summaries = []
    trade_stats_rows = []
    monthly_tables = []
    rolling_tables = []
    cost_tables = []
    nav_stability_tables = []
    bootstrap_tables = []
    raw_daily_tables = []
    raw_trade_tables = []
    raw_shadow_daily_tables = []

    all_specs = {**PRIMARY_LOGS, **REFERENCE_LOGS}
    for label, base_name in all_specs.items():
        path = resolve_log_path(base_name)
        diagnostics_rows.append({
            "variant": label,
            "requested_log": base_name,
            "resolved_log": str(path) if path else "",
            "exists": bool(path),
        })
        if not path:
            continue
        records = load_records(label, path)
        all_records.append(records)
        daily = normalize_daily(event_frame(records, "DAILY_SUMMARY"))
        trades = normalize_trades(event_frame(records, "TRADE_CLOSE"))
        buys = event_frame(records, "BIGMEAT_BUY")
        shadow_daily = normalize_shadow_daily(event_frame(records, "SHADOW_DAILY_SUMMARY"))

        summaries.append(summarize_variant(label, records, path))
        raw_daily_tables.append(daily)
        raw_trade_tables.append(trades)
        raw_shadow_daily_tables.append(shadow_daily)
        for bucket, group in (
            ("all", trades),
            ("core", trades[trades["bucket"] == "core"] if not trades.empty else pd.DataFrame()),
            ("satellite", trades[trades["bucket"] == "satellite"] if not trades.empty else pd.DataFrame()),
        ):
            trade_stats_rows.append(summarize_trade_group(group, label, bucket))
        monthly_tables.append(build_monthly(daily, label))
        rolling_tables.append(build_rolling(daily, label))
        cost_tables.append(build_cost_sensitivity(daily, trades, buys, label))
        nav_stability_tables.append(build_nav_stability(daily, label))
        bootstrap_tables.append(build_block_bootstrap(daily, label))

    summary = pd.DataFrame(summaries)
    trade_stats = pd.DataFrame(trade_stats_rows)
    monthly = pd.concat(monthly_tables, ignore_index=True) if monthly_tables else pd.DataFrame()
    rolling = pd.concat(rolling_tables, ignore_index=True) if rolling_tables else pd.DataFrame()
    cost = pd.concat(cost_tables, ignore_index=True) if cost_tables else pd.DataFrame()
    nav_stability = pd.concat(nav_stability_tables, ignore_index=True) if nav_stability_tables else pd.DataFrame()
    bootstrap = pd.concat(bootstrap_tables, ignore_index=True) if bootstrap_tables else pd.DataFrame()
    notebook_ref = build_notebook_reference()
    diagnostics = pd.DataFrame(diagnostics_rows)
    compare = comparison_rows(summary)
    anomalies = []
    if "v14B_fix" in PRIMARY_LOGS:
        for rec in all_records:
            if not rec.empty and rec.iloc[0]["variant"] == "v14B_fix":
                anomalies = check_v14b_fix_anomalies(rec)
    overfit = build_overfit_flags(
        summary[summary["variant"].isin(PRIMARY_LOGS.keys())],
        monthly,
        rolling,
        trade_stats,
        nav_stability,
        bootstrap,
    )

    raw_daily = pd.concat(raw_daily_tables, ignore_index=True) if raw_daily_tables else pd.DataFrame()
    raw_trade = pd.concat(raw_trade_tables, ignore_index=True) if raw_trade_tables else pd.DataFrame()
    raw_shadow_daily = pd.concat(raw_shadow_daily_tables, ignore_index=True) if raw_shadow_daily_tables else pd.DataFrame()

    tables = {
        "summary": summary,
        "comparison": compare,
        "trade_stats": trade_stats,
        "monthly": monthly,
        "rolling": rolling,
        "cost_sensitivity": cost,
        "nav_stability": nav_stability,
        "block_bootstrap": bootstrap,
        "notebook_reference": notebook_ref,
        "overfit_flags": overfit,
        "daily_raw": raw_daily,
        "trades_raw": raw_trade,
        "shadow_daily_raw": raw_shadow_daily,
        "diagnostics": diagnostics,
    }
    write_outputs(tables)
    make_report(
        summary[summary["variant"].isin(PRIMARY_LOGS.keys())],
        compare,
        trade_stats[trade_stats["variant"].isin(PRIMARY_LOGS.keys())],
        monthly[monthly["variant"].isin(PRIMARY_LOGS.keys())],
        rolling[rolling["variant"].isin(PRIMARY_LOGS.keys())],
        cost[cost["variant"].isin(PRIMARY_LOGS.keys())],
        nav_stability[nav_stability["variant"].isin(PRIMARY_LOGS.keys())],
        bootstrap[bootstrap["variant"].isin(PRIMARY_LOGS.keys())],
        notebook_ref,
        overfit,
        diagnostics,
        anomalies,
    )
    print(f"LOG_COMPARE|report={REPORT_PATH.name}")
    print("LOG_COMPARE|done=1")


if __name__ == "__main__":
    main()
