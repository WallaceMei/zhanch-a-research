#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v1.4.0C P1~P5 independent research master script.

Research-only. Supports two explicit modes:

1. local_analysis
   Reads existing `role_rotation_result_bundle V140C` outputs and writes offline
   diagnostics. This mode is only a replay/diagnosis mode and must not be used
   as the final strategy conclusion.

2. jq_direct_sim
   Runs inside JoinQuant research after the caller injects jqdata APIs. It first
   calls the existing direct simulator (`research_role_rotation_direct_sim_v1`)
   to regenerate v1.4.0C baseline / role_rotation_observer from real daily data,
   then runs P1~P5 diagnostics on those freshly generated results.

It does not modify strategy files, does not modify research_role_rotation_direct_sim_v1.py,
does not call order APIs, does not relax deep_water, does not expand position caps,
and does not auto-search best parameters.

Usage:
    import research_v14C_P1_to_P5_master as p
    p.run_all_p1_to_p5(mode="local_analysis")

JoinQuant research usage:
    from jqdata import *
    import importlib
    import research_v14C_P1_to_P5_master as p
    importlib.reload(p)
    p.get_price = get_price
    p.get_trade_days = get_trade_days
    p.get_all_securities = get_all_securities
    p.get_extras = get_extras
    p.get_call_auction = get_call_auction
    p.run_all_p1_to_p5(mode="jq_direct_sim")
"""
from __future__ import annotations

import importlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

# JoinQuant API injection points. In local_analysis mode these remain None.
# In jq_direct_sim mode the notebook must assign jqdata functions to them.
get_price = None
get_trade_days = None
get_all_securities = None
get_extras = None
get_call_auction = None

TARGET = "role_rotation_observer"
REQUIRED = [
    "role_rotation_summary.csv", "role_rotation_daily_nav.csv", "role_rotation_trades.csv",
    "role_rotation_positions.csv", "role_rotation_decisions.csv", "role_rotation_diagnostics.csv",
    "role_rotation_overfit_check.csv", "role_rotation_sensitivity.csv", "role_rotation_cost_sensitivity.csv",
    "role_rotation_promotion_attribution.csv", "role_rotation_cap_check.csv", "v14C_full_diagnosis_report.md",
    "v14C_loss_bigmeat_summary.csv", "v14C_fast_loss_samples.csv", "v14C_big_meat_samples.csv",
    "v14C_promotion_profit_summary.csv", "v14C_overfit_final_check.csv", "v14C_entry_feature_need_list.csv",
]
ENTRY_FEATURES = [
    "entry_open_ratio", "entry_day_ret", "entry_close_to_high", "entry_volume_ratio", "entry_auc_ratio",
    "entry_ma5_distance", "entry_ma10_distance", "entry_turnover", "entry_rank", "entry_score",
    "sector_strength_rank", "breadth_up_ratio", "market_state", "market_10d_ret",
]


def resolve_dir(p):
    path = Path(p)
    return path if path.is_absolute() else Path.cwd() / path


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            pass
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            pass
    return pd.read_csv(path)


def norm(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for c in out.columns:
        if c == "date" or c.endswith("_date"):
            out[c] = pd.to_datetime(out[c], errors="coerce")
        elif out[c].dtype == object:
            v = pd.to_numeric(out[c], errors="coerce")
            if v.notna().sum() >= max(3, len(out) // 2):
                out[c] = v
    return out


def load_bundle(source_dir: Path):
    tables, texts, missing = {}, {}, []
    for name in REQUIRED:
        p = source_dir / name
        if not p.exists():
            missing.append(name)
        elif name.endswith(".csv"):
            tables[name[:-4]] = norm(read_csv(p))
        elif name.endswith(".md"):
            texts[name] = read_text(p)
    mp = source_dir / "run_manifest.json"
    if mp.exists():
        texts["run_manifest.json"] = read_text(mp)
    return tables, texts, missing


def _api_name(fn):
    return getattr(fn, "__name__", str(fn)) if fn is not None else "None"


def ensure_jq_apis():
    """Fail loudly when jq_direct_sim is requested outside JoinQuant research."""
    required = {
        "get_price": get_price,
        "get_trade_days": get_trade_days,
        "get_all_securities": get_all_securities,
        "get_extras": get_extras,
        "get_call_auction": get_call_auction,
    }
    missing = [name for name, fn in required.items() if fn is None]
    if missing:
        raise RuntimeError(
            "jq_direct_sim requires JoinQuant API injection; missing: {}. "
            "In notebook, run: p.get_price=get_price; p.get_trade_days=get_trade_days; "
            "p.get_all_securities=get_all_securities; p.get_extras=get_extras; "
            "p.get_call_auction=get_call_auction".format(",".join(missing))
        )
    return {name: _api_name(fn) for name, fn in required.items()}


def run_jq_direct_baseline(start_date: str, end_date: str, output_dir: Path):
    """Run the existing v14C direct simulator with injected jqdata APIs.

    This keeps the v14C trading simulation in one source of truth while this
    master script owns only P1~P5 research orchestration and reporting.
    """
    api_names = ensure_jq_apis()
    try:
        rr = importlib.import_module("research_role_rotation_direct_sim_v1")
    except Exception as exc:
        raise RuntimeError(
            "jq_direct_sim requires research_role_rotation_direct_sim_v1.py to be available "
            "in the JoinQuant notebook working directory. Import failed: {}".format(exc)
        )

    rr.get_price = get_price
    rr.get_trade_days = get_trade_days
    rr.get_all_securities = get_all_securities
    rr.get_extras = get_extras
    rr.get_call_auction = get_call_auction

    output_dir.mkdir(parents=True, exist_ok=True)
    sim_result = rr.run_research(
        start_date=start_date,
        end_date=end_date,
        output_dir=str(output_dir),
    )
    return {"api_names": api_names, "sim_result_type": type(sim_result).__name__}


def _safe_get_price(*args, **kwargs):
    try:
        return get_price(*args, **kwargs)
    except Exception:
        if "fields" in kwargs and "high_limit" in kwargs.get("fields", []):
            fields = [f for f in kwargs["fields"] if f != "high_limit"]
            kwargs = dict(kwargs)
            kwargs["fields"] = fields
            return get_price(*args, **kwargs)
        raise


def enrich_entry_features_from_jq(tables: Dict[str, pd.DataFrame], start_date: str, end_date: str):
    """Collect P1 entry features from real JoinQuant daily bars for BUY trades.

    The direct simulator already generated buys/sells. This function does not
    alter any simulated trade; it only attaches entry-day and prior-day features
    needed for P1/P2 diagnostics.
    """
    trades = tables.get("role_rotation_trades", pd.DataFrame()).copy()
    if trades.empty or "action" not in trades or "stock" not in trades:
        return pd.DataFrame(), pd.DataFrame([{"diagnostic": "jq_entry_features", "status": "empty_trades"}])

    buys = trades[(trades["action"].astype(str).str.upper() == "BUY") & (trades.get("variant") == TARGET)].copy()
    if buys.empty:
        return pd.DataFrame(), pd.DataFrame([{"diagnostic": "jq_entry_features", "status": "empty_target_buys"}])

    buys["date"] = pd.to_datetime(buys["date"], errors="coerce")
    stocks = sorted(buys["stock"].dropna().astype(str).unique())
    try:
        hist = _safe_get_price(
            stocks,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=["open", "close", "high", "low", "volume", "money", "pre_close", "paused", "high_limit"],
            panel=False,
            fq="pre",
        )
    except Exception as exc:
        diag = pd.DataFrame([{"diagnostic": "jq_entry_features", "status": "get_price_failed", "error": str(exc)}])
        return pd.DataFrame(), diag

    if hist is None or hist.empty:
        return pd.DataFrame(), pd.DataFrame([{"diagnostic": "jq_entry_features", "status": "empty_price"}])

    hist = hist.copy()
    if isinstance(hist.index, pd.MultiIndex):
        hist = hist.reset_index()
    elif hist.index.name is not None:
        hist = hist.reset_index()
    rename = {}
    for c in hist.columns:
        if c in ("time", "date", "index", "level_0"):
            rename[c] = "date"
        elif c in ("code", "security", "stock", "level_1"):
            rename[c] = "stock"
    if rename:
        hist = hist.rename(columns=rename)
    if "date" not in hist.columns or "stock" not in hist.columns:
        return pd.DataFrame(), pd.DataFrame([{"diagnostic": "jq_entry_features", "status": "price_shape_unsupported", "columns": ",".join(map(str, hist.columns))}])

    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist = hist.sort_values(["stock", "date"])
    for col in ["open", "close", "high", "low", "volume", "money", "pre_close", "high_limit"]:
        if col not in hist.columns:
            hist[col] = np.nan
        hist[col] = pd.to_numeric(hist[col], errors="coerce")
    if "paused" not in hist.columns:
        hist["paused"] = np.nan
    hist["prev_volume"] = hist.groupby("stock")["volume"].shift(1)
    hist["ma5"] = hist.groupby("stock")["close"].transform(lambda s: s.rolling(5, min_periods=1).mean())
    hist["ma10"] = hist.groupby("stock")["close"].transform(lambda s: s.rolling(10, min_periods=1).mean())
    hist["entry_open_ratio"] = hist["open"] / hist["pre_close"] - 1
    hist["entry_day_ret"] = hist["close"] / hist["pre_close"] - 1
    hist["entry_close_to_high"] = hist["close"] / hist["high"]
    hist["entry_volume_ratio"] = hist["volume"] / hist["prev_volume"]
    hist["entry_ma5_distance"] = hist["close"] / hist["ma5"] - 1
    hist["entry_ma10_distance"] = hist["close"] / hist["ma10"] - 1
    hist["entry_is_limit_up"] = np.where(hist["high_limit"].notna(), hist["close"] >= hist["high_limit"] * 0.999, np.nan)

    keep = [
        "date", "stock", "open", "close", "high", "low", "volume", "prev_volume", "money", "pre_close", "paused", "high_limit",
        "entry_open_ratio", "entry_day_ret", "entry_close_to_high", "entry_volume_ratio",
        "entry_ma5_distance", "entry_ma10_distance", "entry_is_limit_up",
    ]
    feat = buys.merge(hist[keep], on=["date", "stock"], how="left")
    # Rank / score: use only values already emitted by the direct simulator.
    rank_source = None
    for c in ("entry_rank", "prefilter_rank", "score_rank", "rank"):
        if c in feat.columns:
            rank_source = c
            break
    feat["entry_rank"] = feat[rank_source] if rank_source else np.nan
    feat["entry_rank_available"] = feat["entry_rank"].notna().astype(int)
    feat["entry_rank_missing_reason"] = np.where(feat["entry_rank_available"].eq(1), "", "entry_rank_not_in_source_outputs")
    feat["entry_rank_source"] = rank_source or ""

    if "signal_score" in feat.columns:
        feat["entry_score"] = feat["signal_score"]
        feat["entry_score_source"] = "signal_score"
    else:
        feat["entry_score"] = np.nan
        feat["entry_score_source"] = ""
    feat["entry_score_available"] = feat["entry_score"].notna().astype(int)
    feat["entry_score_missing_reason"] = np.where(feat["entry_score_available"].eq(1), "", "signal_score_not_in_source_outputs")

    # Auction ratio: real get_call_auction only. Missing stays explicit.
    feat["auction_volume"] = np.nan
    feat["auction_money"] = np.nan
    feat["auction_price"] = np.nan
    feat["entry_auc_ratio"] = np.nan
    feat["entry_auc_available"] = 0
    feat["entry_auc_missing_reason"] = "get_call_auction_not_available"
    if get_call_auction is not None:
        for idx, row in feat.iterrows():
            stock = str(row.get("stock"))
            day = pd.Timestamp(row.get("date"))
            try:
                auc = get_call_auction(
                    stock,
                    start_date=day.strftime("%Y-%m-%d 09:15:00"),
                    end_date=day.strftime("%Y-%m-%d 09:26:00"),
                    fields=["time", "volume", "current"],
                )
                if auc is None or len(auc) == 0:
                    feat.at[idx, "entry_auc_missing_reason"] = "auction_empty"
                    continue
                last = auc.iloc[-1]
                avol = pd.to_numeric(pd.Series([last.get("volume", np.nan)]), errors="coerce").iloc[0]
                aprice = pd.to_numeric(pd.Series([last.get("current", np.nan)]), errors="coerce").iloc[0]
                prev_vol = row.get("prev_volume", np.nan)
                feat.at[idx, "auction_volume"] = avol
                feat.at[idx, "auction_price"] = aprice
                feat.at[idx, "auction_money"] = avol * aprice if not pd.isna(avol) and not pd.isna(aprice) else np.nan
                if not pd.isna(avol) and not pd.isna(prev_vol) and prev_vol > 0:
                    feat.at[idx, "entry_auc_ratio"] = avol / prev_vol
                    feat.at[idx, "entry_auc_available"] = 1
                    feat.at[idx, "entry_auc_missing_reason"] = ""
                else:
                    feat.at[idx, "entry_auc_missing_reason"] = "previous_day_volume_missing"
            except Exception as exc:
                feat.at[idx, "entry_auc_missing_reason"] = "get_call_auction_failed:{}".format(str(exc)[:80])

    # Turnover and sector rank are not guessed.
    turnover_col = next((c for c in ("turnover_ratio", "turnover", "entry_turnover") if c in feat.columns), None)
    feat["entry_turnover"] = feat[turnover_col] if turnover_col else np.nan
    feat["entry_turnover_available"] = feat["entry_turnover"].notna().astype(int)
    feat["entry_turnover_missing_reason"] = np.where(feat["entry_turnover_available"].eq(1), "", "turnover_data_unavailable")
    feat["entry_turnover_source"] = turnover_col or ""

    feat["sector_code"] = np.nan
    feat["sector_name"] = np.nan
    feat["sector_5d_ret"] = np.nan
    feat["sector_strength_rank"] = np.nan
    feat["sector_strength_available"] = 0
    feat["sector_strength_missing_reason"] = "sector_classification_not_available"

    # Breadth: first direct diagnostics, then stock panel estimate.
    diag = tables.get("role_rotation_diagnostics", pd.DataFrame()).copy()
    breadth_col = next((c for c in ("breadth_up_ratio", "market_breadth", "up_ratio") if c in diag.columns), None) if not diag.empty else None
    feat["breadth_up_ratio"] = np.nan
    feat["breadth_source"] = ""
    if breadth_col and "date" in diag.columns:
        diag["date"] = pd.to_datetime(diag["date"], errors="coerce")
        b = diag[["date", breadth_col]].rename(columns={breadth_col: "_breadth_up_ratio"}).drop_duplicates("date")
        feat = feat.merge(b, on="date", how="left")
        feat["breadth_up_ratio"] = feat["_breadth_up_ratio"]
        feat["breadth_source"] = "role_rotation_diagnostics:{}".format(breadth_col)
        feat = feat.drop(columns=["_breadth_up_ratio"])
    if feat["breadth_up_ratio"].isna().all() and {"close", "pre_close"}.issubset(hist.columns):
        hb = hist.copy()
        hb["up"] = hb["close"] > hb["pre_close"]
        breadth = hb.groupby("date")["up"].mean().reset_index().rename(columns={"up": "_breadth_up_ratio"})
        feat = feat.merge(breadth, on="date", how="left")
        feat["breadth_up_ratio"] = feat["_breadth_up_ratio"]
        feat["breadth_source"] = "direct_sim_stock_panel_estimate"
        feat = feat.drop(columns=["_breadth_up_ratio"])
    feat["breadth_available"] = feat["breadth_up_ratio"].notna().astype(int)
    feat["breadth_missing_reason"] = np.where(feat["breadth_available"].eq(1), "", "breadth_data_unavailable")

    # Market 10d return: use index if available; otherwise explicit missing.
    feat["market_index_code"] = "000001.XSHG"
    feat["market_10d_ret"] = np.nan
    feat["market_10d_ret_available"] = 0
    feat["market_10d_ret_missing_reason"] = "market_index_get_price_not_available"
    if get_price is not None:
        try:
            idx = _safe_get_price(
                "000001.XSHG", start_date=start_date, end_date=end_date, frequency="daily",
                fields=["close"], panel=False, fq="pre"
            )
            if idx is not None and not idx.empty:
                idx = idx.copy()
                if idx.index.name is not None:
                    idx = idx.reset_index()
                rename_idx = {c: "date" for c in idx.columns if c in ("time", "date", "index")}
                idx = idx.rename(columns=rename_idx)
                if "date" in idx.columns and "close" in idx.columns:
                    idx["date"] = pd.to_datetime(idx["date"], errors="coerce")
                    idx["market_10d_ret"] = pd.to_numeric(idx["close"], errors="coerce") / pd.to_numeric(idx["close"], errors="coerce").shift(10) - 1
                    feat = feat.merge(idx[["date", "market_10d_ret"]], on="date", how="left", suffixes=("", "_idx"))
                    if "market_10d_ret_idx" in feat.columns:
                        feat["market_10d_ret"] = feat["market_10d_ret_idx"]
                        feat = feat.drop(columns=["market_10d_ret_idx"])
                    feat["market_10d_ret_available"] = feat["market_10d_ret"].notna().astype(int)
                    feat["market_10d_ret_missing_reason"] = np.where(feat["market_10d_ret_available"].eq(1), "", "market_10d_ret_insufficient_history")
        except Exception as exc:
            feat["market_10d_ret_missing_reason"] = "market_index_get_price_failed:{}".format(str(exc)[:80])

    for base in ["entry_open_ratio", "entry_day_ret", "entry_close_to_high", "entry_volume_ratio", "entry_ma5_distance", "entry_ma10_distance"]:
        feat[base + "_available"] = feat[base].notna().astype(int)
        feat[base + "_missing_reason"] = np.where(feat[base + "_available"].eq(1), "", base + "_price_data_missing")
    feat["entry_feature_source"] = "jq_get_price_daily"
    diag = pd.DataFrame([{
        "diagnostic": "jq_entry_features", "status": "ok", "buy_count": len(buys),
        "feature_rows": len(feat), "feature_hit_count": int(feat["close"].notna().sum()),
    }])
    return feat, diag


def hold_bucket(x):
    if pd.isna(x): return "unknown"
    x = float(x)
    if x <= 1: return "<=1d"
    if x <= 2: return "2d"
    if x <= 3: return "3d"
    if x <= 5: return "4-5d"
    if x <= 10: return "6-10d"
    return ">10d"


def target_sells(tables):
    t = tables.get("role_rotation_trades", pd.DataFrame()).copy()
    if t.empty: return t
    s = t[(t.get("variant") == TARGET) & (t.get("action") == "SELL")].copy()
    if s.empty: return s
    s["is_win"] = s["pnl_val"] > 0
    s["is_loss"] = s["pnl_val"] < 0
    s["is_fast_loss"] = (s["pnl_val"] < 0) & (s["hold_days_cal"].fillna(999) <= 5)
    s["is_big_meat_10"] = s["pnl_pct"] > 0.10
    s["is_super_meat_20"] = s["pnl_pct"] > 0.20
    s["hold_bucket"] = s["hold_days_cal"].map(hold_bucket)
    if "trade_category" not in s.columns: s["trade_category"] = s.get("role", "unknown")
    return s


def group_stats(df, keys: Iterable[str], section: str):
    if df.empty: return pd.DataFrame()
    out = df.groupby(list(keys), dropna=False).agg(
        trade_count=("stock", "count"), win_count=("is_win", "sum"), loss_count=("is_loss", "sum"),
        total_pnl_val=("pnl_val", "sum"), avg_pnl_pct=("pnl_pct", "mean"), median_pnl_pct=("pnl_pct", "median"),
        avg_hold_days=("hold_days_cal", "mean"), fast_loss_count=("is_fast_loss", "sum"),
        big_meat_10_count=("is_big_meat_10", "sum"), super_meat_20_count=("is_super_meat_20", "sum"),
    ).reset_index()
    out.insert(0, "section", section)
    out["win_rate"] = np.where(out.trade_count > 0, out.win_count / out.trade_count, np.nan)
    return out


INITIAL_CASH = 1000000.0
TRAIN_END = pd.Timestamp("2025-12-31")
VALIDATION_END = pd.Timestamp("2026-03-31")


def target_table(tables, name):
    df = tables.get(name, pd.DataFrame()).copy()
    if df.empty:
        return df
    if "variant" in df.columns:
        df = df[df["variant"] == TARGET].copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def trade_calendar_from_tables(tables, start_date, end_date):
    daily = tables.get("role_rotation_daily_nav", pd.DataFrame()).copy()
    if not daily.empty and "date" in daily.columns:
        dates = pd.to_datetime(daily["date"], errors="coerce").dropna().sort_values().unique()
        dates = [pd.Timestamp(d).normalize() for d in dates]
    elif get_trade_days is not None:
        dates = [pd.Timestamp(d).normalize() for d in get_trade_days(start_date=start_date, end_date=end_date)]
    else:
        dates = list(pd.date_range(start_date, end_date, freq="B"))
    lo, hi = pd.Timestamp(start_date), pd.Timestamp(end_date)
    return [d for d in dates if lo <= d <= hi]


def price_panel_from_tables(tables, start_date, end_date):
    trades = target_table(tables, "role_rotation_trades")
    positions = target_table(tables, "role_rotation_positions")
    stocks = sorted(set(trades.get("stock", pd.Series(dtype=str)).dropna().astype(str)))
    rows = []
    if stocks and get_price is not None:
        try:
            hist = _safe_get_price(
                stocks,
                start_date=start_date,
                end_date=end_date,
                frequency="daily",
                fields=["open", "close", "high", "low", "volume", "money", "pre_close", "paused", "high_limit"],
                panel=False,
                fq="pre",
            )
            if hist is not None and not hist.empty:
                hist = hist.copy()
                if isinstance(hist.index, pd.MultiIndex) or hist.index.name is not None:
                    hist = hist.reset_index()
                rename = {}
                for c in hist.columns:
                    if c in ("time", "date", "index", "level_0"):
                        rename[c] = "date"
                    elif c in ("code", "security", "stock", "level_1"):
                        rename[c] = "stock"
                hist = hist.rename(columns=rename)
                if "date" in hist.columns and "stock" in hist.columns:
                    hist["date"] = pd.to_datetime(hist["date"], errors="coerce").dt.normalize()
                    hist = hist.sort_values(["stock", "date"])
                    if "close" in hist.columns:
                        hist["ma5"] = hist.groupby("stock")["close"].transform(lambda s: pd.to_numeric(s, errors="coerce").rolling(5, min_periods=1).mean())
                    return hist
        except Exception:
            pass
    if not positions.empty:
        p = positions.copy()
        p["date"] = pd.to_datetime(p["date"], errors="coerce").dt.normalize()
        p["stock"] = p["stock"].astype(str)
        p["close"] = pd.to_numeric(p.get("price"), errors="coerce")
        for c in ["open", "high", "low", "pre_close"]:
            p[c] = p["close"]
        p["volume"] = np.nan
        p["money"] = np.nan
        p = p.sort_values(["stock", "date"])
        p["ma5"] = p.groupby("stock")["close"].transform(lambda s: pd.to_numeric(s, errors="coerce").rolling(5, min_periods=1).mean())
        return p[["date", "stock", "open", "close", "high", "low", "volume", "money", "pre_close", "ma5"]]
    if not trades.empty:
        t = trades.copy()
        t["date"] = pd.to_datetime(t["date"], errors="coerce").dt.normalize()
        t["stock"] = t["stock"].astype(str)
        t["close"] = pd.to_numeric(t.get("price"), errors="coerce")
        for c in ["open", "high", "low", "pre_close"]:
            t[c] = t["close"]
        t["volume"] = np.nan
        t["money"] = np.nan
        t = t.sort_values(["stock", "date"])
        t["ma5"] = t.groupby("stock")["close"].transform(lambda s: pd.to_numeric(s, errors="coerce").rolling(5, min_periods=1).mean())
        return t[["date", "stock", "open", "close", "high", "low", "volume", "money", "pre_close", "ma5"]]
    return pd.DataFrame(columns=["date", "stock", "open", "close", "high", "low", "volume", "money", "pre_close", "ma5"])


def make_price_lookup(price_df):
    if price_df is None or price_df.empty:
        return {}
    df = price_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["stock"] = df["stock"].astype(str)
    lookup = {}
    for _, r in df.iterrows():
        key = (r["stock"], pd.Timestamp(r["date"]).normalize())
        lookup[key] = r.to_dict()
    return lookup


def market_state_by_date(tables):
    daily = target_table(tables, "role_rotation_daily_nav")
    if daily.empty or "market_state" not in daily.columns:
        return {}
    return {pd.Timestamp(r["date"]).normalize(): r.get("market_state", "unknown") for _, r in daily.iterrows()}


def _event_rows(df, action):
    if df.empty or "action" not in df.columns:
        return pd.DataFrame()
    out = df[df["action"].astype(str).str.upper() == action].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    return out.sort_values(["date", "stock"])


def _price_for(price_lookup, stock, date, fallback):
    row = price_lookup.get((str(stock), pd.Timestamp(date).normalize()), {})
    px = row.get("close", np.nan)
    if pd.isna(px) or float(px) <= 0:
        px = fallback
    return float(px) if not pd.isna(px) and float(px) > 0 else np.nan, row


def _cap_limit_for_policy(policy, market_state):
    market_state = str(market_state or "unknown").lower()
    if policy.get("regime_position"):
        if market_state == "bull":
            return 0.75
        if market_state == "neutral":
            return 0.60
        if market_state == "bear":
            return 0.35
    if policy.get("cap_fixed") or policy.get("combined_observer"):
        return 0.75
    return None


def _policy_allows_buy(policy, row, state, post_total_ratio, post_single_ratio):
    role = str(row.get("role", ""))
    market_state = str(state.get("market_state", "unknown")).lower()
    if policy.get("regime_position") and market_state == "bear" and role == "satellite":
        return False, "bear_skip_satellite"
    return True, "buy_allowed"


def promotion_events_by_date(tables):
    dec = target_table(tables, "role_rotation_decisions")
    if dec.empty or "decision" not in dec.columns:
        return {}
    mask = dec["decision"].astype(str).str.upper().eq("ROLE_PROMOTION_EXECUTE")
    promo = dec[mask].copy()
    if promo.empty:
        return {}
    promo["date"] = pd.to_datetime(promo["date"], errors="coerce").dt.normalize()
    return {d: g.copy() for d, g in promo.groupby("date")}


def _policy_exit_reason(policy, pos, date, price, row):
    entry_price = pos.get("entry_price", np.nan)
    if pd.isna(entry_price) or entry_price <= 0 or pd.isna(price):
        return None
    pnl_pct = price / entry_price - 1
    pos["max_pnl_pct"] = max(float(pos.get("max_pnl_pct", pnl_pct)), float(pnl_pct))
    hold_days = max(0, (pd.Timestamp(date) - pd.Timestamp(pos["entry_date"])).days)
    if policy.get("next_day_acceptance") and hold_days >= 1 and pnl_pct <= -0.02:
        return "p2_next_day_acceptance_exit"
    if policy.get("quick_fail_exit") and hold_days >= 1 and pnl_pct <= -0.035:
        return "p2_quick_fail_exit"
    if policy.get("confirm_add") and pos.get("confirm_pending") and hold_days >= 1:
        # Do not clear confirm_pending here. The confirm-add check block below
        # owns all confirm_add_* detail rows, including weak/loss blocked cases.
        ma5 = row.get("ma5", np.nan) if isinstance(row, dict) else np.nan
        weak_close = False
        if not pd.isna(ma5) and ma5 > 0:
            weak_close = price < ma5
        if pnl_pct <= -0.02 or weak_close:
            pos["confirm_add_block_reason"] = "weak_or_loss"
    if policy.get("promotion_protect") and pos.get("promotion_state") in ("promoted_core", "promoted_core_observe"):
        days_after = max(0, (pd.Timestamp(date) - pd.Timestamp(pos.get("promotion_date", date))).days)
        post_entry = pos.get("post_promotion_entry_price", pos.get("entry_price"))
        post_pnl = price / post_entry - 1 if post_entry and post_entry > 0 else pnl_pct
        pos["post_promotion_pnl"] = post_pnl
        if post_pnl < 0:
            return "p4_promotion_post_pnl_negative_exit"
        if days_after >= 2 and post_pnl < 0.03:
            return "p4_promotion_not_strong_exit"
    if policy.get("combined_observer"):
        drawdown = float(pos.get("max_pnl_pct", pnl_pct)) - float(pnl_pct)
        if hold_days >= 1 and pnl_pct <= -0.035:
            return "p5_quick_fail_exit"
        if pos.get("promotion_state") in ("promoted_core", "promoted_core_observe"):
            days_after = max(0, (pd.Timestamp(date) - pd.Timestamp(pos.get("promotion_date", date))).days)
            post_entry = pos.get("post_promotion_entry_price", pos.get("entry_price"))
            post_pnl = price / post_entry - 1 if post_entry and post_entry > 0 else pnl_pct
            pos["post_promotion_pnl"] = post_pnl
            if post_pnl < 0 or (days_after >= 2 and post_pnl < 0.03):
                return "p5_promotion_protect_exit"
        elif pos.get("max_pnl_pct", 0) >= 0.10 and drawdown >= 0.06:
            return "p5_drawdown_protect_exit"
    return None


def simulate_replay_path(tables, variant, policy, start_date, end_date):
    trades = target_table(tables, "role_rotation_trades")
    dates = trade_calendar_from_tables(tables, start_date, end_date)
    price_df = price_panel_from_tables(tables, start_date, end_date)
    price_lookup = make_price_lookup(price_df)
    state_map = market_state_by_date(tables)
    buys = _event_rows(trades, "BUY")
    sells = _event_rows(trades, "SELL")
    promo_by_date = promotion_events_by_date(tables)
    buys_by_date = {d: g.copy() for d, g in buys.groupby("date")} if not buys.empty else {}
    sells_by_date = {d: g.copy() for d, g in sells.groupby("date")} if not sells.empty else {}
    cash = INITIAL_CASH
    positions = {}
    trade_rows, pos_rows, nav_rows, decision_rows = [], [], [], []
    cap_exceeded = 0
    skipped_due_to_no_capacity = 0
    confirm_add_rows = []

    for date in dates:
        date = pd.Timestamp(date).normalize()
        market_state = state_map.get(date, "unknown")

        for _, pe in promo_by_date.get(date, pd.DataFrame()).iterrows():
            stock = str(pe.get("stock"))
            if stock not in positions:
                continue
            pos = positions[stock]
            price, _ = _price_for(price_lookup, stock, date, pos.get("last_price", pos.get("entry_price")))
            if policy.get("no_promotion"):
                reason = "p4_no_promotion_take_profit"
                value = price * pos["shares"]
                pnl_val = value - pos["cost"]
                pnl_pct = pnl_val / pos["cost"] if pos["cost"] else np.nan
                cash += value
                trade_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "action": "SELL", "role": pos.get("role"), "price": price, "shares": pos["shares"], "value": value, "reason": reason, "pnl_pct": pnl_pct, "pnl_val": pnl_val, "trade_category": pos.get("role"), "hold_days_cal": (date - pos["entry_date"]).days, "entry_type": pos.get("entry_type"), "signal_score": pos.get("signal_score")})
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "PROMOTION_BLOCK_EXIT", "reason": reason, "role": pos.get("role"), "market_state": market_state, "promotion_date": date, "promotion_state": "blocked_exit", "promoted_from_role": pos.get("role"), "post_promotion_entry_price": price, "post_promotion_pnl": 0.0, "promotion_action": "exit_instead_of_promotion"})
                positions.pop(stock, None)
                continue
            if policy.get("label_only_no_add"):
                pos["promotion_state"] = "promoted_core_observe"
                pos["promotion_date"] = date
                pos["promoted_from_role"] = pos.get("role")
                pos["post_promotion_entry_price"] = price
                pos["promotion_action"] = "label_only_no_add"
                pos["role"] = "promoted_core_observe"
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "PROMOTION_LABEL_ONLY", "reason": "label_only_no_add", "role": pos.get("role"), "market_state": market_state, "promotion_date": date, "promotion_state": pos.get("promotion_state"), "promoted_from_role": pos.get("promoted_from_role"), "post_promotion_entry_price": price, "post_promotion_pnl": 0.0, "promotion_action": "label_only_no_add"})
                continue
            if policy.get("promotion_protect") or policy.get("combined_observer"):
                pos["promotion_state"] = "promoted_core"
                pos["promotion_date"] = date
                pos["promoted_from_role"] = pos.get("role")
                pos["post_promotion_entry_price"] = price
                pos["promotion_action"] = "promotion_protect_watch"
                pos["role"] = "core"
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "PROMOTION_STATE_ENTER", "reason": "promotion_protect_watch", "role": pos.get("role"), "market_state": market_state, "promotion_date": date, "promotion_state": pos.get("promotion_state"), "promoted_from_role": pos.get("promoted_from_role"), "post_promotion_entry_price": price, "post_promotion_pnl": 0.0, "promotion_action": "promotion_protect_watch"})

        # Policy exits first, then baseline exits, then baseline buys.
        for stock in list(positions.keys()):
            pos = positions.get(stock)
            price, prow = _price_for(price_lookup, stock, date, pos.get("last_price", pos.get("entry_price")))
            reason = _policy_exit_reason(policy, pos, date, price, prow)
            if reason:
                if pos.get("confirm_pending"):
                    confirm_add_rows.append({"variant": variant, "stock": stock, "name": pos.get("name"), "entry_date": pos.get("entry_date"), "check_date": date, "entry_price": pos.get("entry_price"), "check_price": price, "ma5": prow.get("ma5", np.nan) if isinstance(prow, dict) else np.nan, "pre_close": prow.get("pre_close", np.nan) if isinstance(prow, dict) else np.nan, "pnl_pct": price / pos.get("entry_price") - 1 if pos.get("entry_price") else np.nan, "target_value": pos.get("target_value"), "current_cost": pos.get("cost"), "add_value": 0.0, "ma5_ok": np.nan, "loss_ok": np.nan, "close_ok": np.nan, "reason": "confirm_add_policy_exit_before_check", "final_action": reason})
                value = price * pos["shares"]
                pnl_val = value - pos["cost"]
                pnl_pct = pnl_val / pos["cost"] if pos["cost"] else np.nan
                cash += value
                trade_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "action": "SELL", "role": pos.get("role"), "price": price, "shares": pos["shares"], "value": value, "reason": reason, "pnl_pct": pnl_pct, "pnl_val": pnl_val, "trade_category": pos.get("role"), "hold_days_cal": (date - pos["entry_date"]).days, "entry_type": pos.get("entry_type"), "signal_score": pos.get("signal_score")})
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "POLICY_EXIT", "reason": reason, "role": pos.get("role"), "market_state": market_state, "promotion_date": pos.get("promotion_date"), "promotion_state": pos.get("promotion_state"), "promoted_from_role": pos.get("promoted_from_role"), "post_promotion_entry_price": pos.get("post_promotion_entry_price"), "post_promotion_pnl": pos.get("post_promotion_pnl"), "promotion_action": pos.get("promotion_action")})
                positions.pop(stock, None)

        for _, r in sells_by_date.get(date, pd.DataFrame()).iterrows():
            stock = str(r.get("stock"))
            if stock not in positions:
                continue
            pos = positions[stock]
            price, _ = _price_for(price_lookup, stock, date, r.get("price", pos.get("last_price", pos.get("entry_price"))))
            if pos.get("confirm_pending"):
                confirm_add_rows.append({"variant": variant, "stock": stock, "name": pos.get("name"), "entry_date": pos.get("entry_date"), "check_date": date, "entry_price": pos.get("entry_price"), "check_price": price, "ma5": np.nan, "pre_close": np.nan, "pnl_pct": price / pos.get("entry_price") - 1 if pos.get("entry_price") else np.nan, "target_value": pos.get("target_value"), "current_cost": pos.get("cost"), "add_value": 0.0, "ma5_ok": np.nan, "loss_ok": np.nan, "close_ok": np.nan, "reason": "confirm_add_baseline_exit_before_check", "final_action": r.get("reason", "baseline_exit")})
            value = price * pos["shares"]
            pnl_val = value - pos["cost"]
            pnl_pct = pnl_val / pos["cost"] if pos["cost"] else np.nan
            cash += value
            trade_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "action": "SELL", "role": pos.get("role"), "price": price, "shares": pos["shares"], "value": value, "reason": r.get("reason", "baseline_exit"), "pnl_pct": pnl_pct, "pnl_val": pnl_val, "trade_category": pos.get("role"), "hold_days_cal": (date - pos["entry_date"]).days, "entry_type": pos.get("entry_type"), "signal_score": pos.get("signal_score")})
            decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "BASELINE_EXIT", "reason": r.get("reason", "baseline_exit"), "role": pos.get("role"), "market_state": market_state})
            positions.pop(stock, None)

        current_value = cash
        for s, pos in positions.items():
            px, _ = _price_for(price_lookup, s, date, pos.get("last_price", pos.get("entry_price")))
            pos["last_price"] = px
            current_value += px * pos["shares"]

        if policy.get("confirm_add"):
            for stock in list(positions.keys()):
                pos = positions[stock]
                if not pos.get("confirm_pending"):
                    continue
                hold_days = max(0, (date - pos["entry_date"]).days)
                if hold_days < 1:
                    continue
                price, prow = _price_for(price_lookup, stock, date, pos.get("last_price", pos.get("entry_price")))
                if pd.isna(price) or price <= 0:
                    pos["confirm_pending"] = False
                    confirm_add_rows.append({"variant": variant, "stock": stock, "name": pos.get("name"), "entry_date": pos.get("entry_date"), "check_date": date, "entry_price": pos.get("entry_price"), "check_price": price, "ma5": np.nan, "pre_close": np.nan, "pnl_pct": np.nan, "target_value": pos.get("target_value"), "current_cost": pos.get("cost"), "add_value": 0.0, "ma5_ok": np.nan, "loss_ok": np.nan, "close_ok": np.nan, "reason": "confirm_add_missing_price", "final_action": "missing_price"})
                    continue
                ma5 = prow.get("ma5", np.nan) if isinstance(prow, dict) else np.nan
                pre_close = prow.get("pre_close", np.nan) if isinstance(prow, dict) else np.nan
                pnl_pct = price / pos["entry_price"] - 1 if pos.get("entry_price") else np.nan
                ma5_ok = True if pd.isna(ma5) or ma5 <= 0 else price >= ma5
                loss_ok = True if pd.isna(pnl_pct) else pnl_pct > -0.01
                close_ok = True if pd.isna(pre_close) or pre_close <= 0 else price >= pre_close * 0.995
                add_value = max(0.0, float(pos.get("target_value", pos["cost"])) - float(pos["cost"]))
                reason = "confirm_add_ok" if ma5_ok and loss_ok and close_ok and add_value > 0 else "confirm_add_blocked"
                if reason == "confirm_add_ok":
                    pos_value_now = sum(p.get("last_price", p["entry_price"]) * p["shares"] for p in positions.values())
                    cap_limit = _cap_limit_for_policy(policy, market_state)
                    if cap_limit is not None:
                        available_value = max(0.0, cap_limit * current_value - pos_value_now)
                        add_value = min(add_value, available_value)
                    if add_value >= max(10000.0, current_value * 0.01) and add_value <= cash:
                        add_shares = add_value / price
                        cash -= add_value
                        pos["shares"] += add_shares
                        pos["cost"] += add_value
                        pos["confirm_pending"] = False
                        trade_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "action": "BUY", "role": pos.get("role"), "price": price, "shares": add_shares, "value": add_value, "reason": "p2_confirm_add", "pnl_pct": np.nan, "pnl_val": np.nan, "trade_category": np.nan, "hold_days_cal": np.nan, "entry_type": pos.get("entry_type"), "signal_score": pos.get("signal_score")})
                        decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": pos.get("name"), "decision": "CONFIRM_ADD", "reason": "p2_confirm_add", "role": pos.get("role"), "market_state": market_state})
                        final_action = "confirm_add_executed"
                    else:
                        reason = "confirm_add_no_capacity"
                        pos["confirm_pending"] = False
                        final_action = "no_capacity"
                else:
                    pos["confirm_pending"] = False
                    final_action = "blocked"
                confirm_add_rows.append({"variant": variant, "stock": stock, "name": pos.get("name"), "entry_date": pos.get("entry_date"), "check_date": date, "entry_price": pos.get("entry_price"), "check_price": price, "ma5": ma5, "pre_close": pre_close, "pnl_pct": pnl_pct, "target_value": pos.get("target_value"), "current_cost": pos.get("cost"), "add_value": add_value, "ma5_ok": ma5_ok, "loss_ok": loss_ok, "close_ok": close_ok, "reason": reason, "final_action": final_action})
                current_value = cash + sum(p.get("last_price", p["entry_price"]) * p["shares"] for p in positions.values())

        for _, r in buys_by_date.get(date, pd.DataFrame()).iterrows():
            stock = str(r.get("stock"))
            if stock in positions:
                continue
            price, _ = _price_for(price_lookup, stock, date, r.get("price", np.nan))
            if pd.isna(price) or price <= 0:
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": r.get("name"), "decision": "BUY_SKIP", "reason": "missing_price", "role": r.get("role"), "market_state": market_state})
                continue
            original_value = float(r.get("value", 0) or 0)
            value = original_value
            shares = float(r.get("shares", 0) or 0)
            if value <= 0 and shares > 0:
                value = shares * price
                original_value = value
            if shares <= 0 and value > 0:
                shares = value / price
            if value <= 0 or shares <= 0:
                continue
            if policy.get("confirm_add"):
                value = original_value * 0.65
                shares = value / price
            pos_value_now = sum(p.get("last_price", p["entry_price"]) * p["shares"] for p in positions.values())
            pre_buy_total_ratio = pos_value_now / max(current_value, 1)
            target_order_ratio = value / max(current_value, 1)
            cap_limit = _cap_limit_for_policy(policy, market_state)
            available_ratio = np.nan
            cap_trimmed = False
            if cap_limit is not None:
                available_ratio = max(0.0, cap_limit - pre_buy_total_ratio)
                if target_order_ratio > available_ratio:
                    value = max(0.0, available_ratio * current_value)
                    shares = value / price if price else 0
                    cap_trimmed = True
            post_total_ratio = (pos_value_now + value) / max(current_value, 1)
            post_single_ratio = value / max(current_value, 1)
            allow, reason = _policy_allows_buy(policy, r, {"market_state": market_state}, post_total_ratio, post_single_ratio)
            if not allow:
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": r.get("name"), "decision": "BUY_SKIP", "reason": reason, "role": r.get("role"), "market_state": market_state, "pre_buy_total_ratio": pre_buy_total_ratio, "target_order_ratio": target_order_ratio, "available_ratio": available_ratio, "post_total_ratio": post_total_ratio, "post_single_ratio": post_single_ratio, "cap_limit": cap_limit, "original_value": original_value, "actual_value": value, "cap_trimmed": cap_trimmed, "skipped_due_to_no_capacity": False})
                continue
            if value < max(10000.0, current_value * 0.01):
                skipped_due_to_no_capacity += 1
                decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": r.get("name"), "decision": "BUY_SKIP", "reason": "skipped_due_to_no_capacity", "role": r.get("role"), "market_state": market_state, "pre_buy_total_ratio": pre_buy_total_ratio, "target_order_ratio": target_order_ratio, "available_ratio": available_ratio, "post_total_ratio": post_total_ratio, "post_single_ratio": post_single_ratio, "cap_limit": cap_limit, "original_value": original_value, "actual_value": value, "cap_trimmed": cap_trimmed, "skipped_due_to_no_capacity": True})
                continue
            if value > cash:
                value = cash
                shares = value / price if price else 0
            if value <= 0 or shares <= 0:
                continue
            cash -= value
            actual_post_total_ratio = (pos_value_now + value) / max(current_value, 1)
            if cap_limit is not None and actual_post_total_ratio > cap_limit + 1e-6:
                cap_exceeded += 1
            positions[stock] = {"stock": stock, "name": r.get("name"), "role": r.get("role"), "shares": shares, "cost": value, "target_value": original_value, "entry_date": date, "entry_price": price, "last_price": price, "entry_type": r.get("entry_type"), "signal_score": r.get("signal_score"), "max_pnl_pct": 0.0, "confirm_pending": bool(policy.get("confirm_add") and original_value > value)}
            trade_rows.append({"date": date, "variant": variant, "stock": stock, "name": r.get("name"), "action": "BUY", "role": r.get("role"), "price": price, "shares": shares, "value": value, "reason": r.get("reason", "baseline_entry_replay"), "pnl_pct": np.nan, "pnl_val": np.nan, "trade_category": np.nan, "hold_days_cal": np.nan, "entry_type": r.get("entry_type"), "signal_score": r.get("signal_score")})
            decision_rows.append({"date": date, "variant": variant, "stock": stock, "name": r.get("name"), "decision": "BUY", "reason": reason, "role": r.get("role"), "market_state": market_state, "pre_buy_total_ratio": pre_buy_total_ratio, "target_order_ratio": target_order_ratio, "available_ratio": available_ratio, "post_total_ratio": actual_post_total_ratio, "post_single_ratio": value / max(current_value, 1), "cap_limit": cap_limit, "original_value": original_value, "actual_value": value, "cap_trimmed": cap_trimmed, "skipped_due_to_no_capacity": False})

        total_value = cash
        core_value = 0.0
        sat_value = 0.0
        for s, pos in positions.items():
            px, _ = _price_for(price_lookup, s, date, pos.get("last_price", pos.get("entry_price")))
            pos["last_price"] = px
            mv = px * pos["shares"]
            total_value += mv
            if pos.get("role") == "satellite":
                sat_value += mv
            else:
                core_value += mv
            pnl = mv - pos["cost"]
            post_entry = pos.get("post_promotion_entry_price", np.nan)
            post_pnl = px / post_entry - 1 if post_entry and not pd.isna(post_entry) and post_entry > 0 else np.nan
            if not pd.isna(post_pnl):
                pos["post_promotion_pnl"] = post_pnl
            pos_rows.append({"date": date, "variant": variant, "stock": s, "name": pos.get("name"), "role": pos.get("role"), "shares": pos["shares"], "price": px, "market_value": mv, "cost": pos["cost"], "pnl": pnl, "pnl_pct": pnl / pos["cost"] if pos["cost"] else np.nan, "weight": mv / max(total_value, 1), "hold_days": (date - pos["entry_date"]).days, "promotion_state": pos.get("promotion_state"), "promotion_date": pos.get("promotion_date"), "promoted_from_role": pos.get("promoted_from_role"), "post_promotion_entry_price": pos.get("post_promotion_entry_price"), "post_promotion_pnl": pos.get("post_promotion_pnl"), "promotion_action": pos.get("promotion_action")})
        nav_rows.append({"date": date, "variant": variant, "cash": cash, "total_value": total_value, "nav": total_value / INITIAL_CASH, "position_count": len(positions), "core_count": sum(1 for p in positions.values() if p.get("role") != "satellite"), "satellite_count": sum(1 for p in positions.values() if p.get("role") == "satellite"), "core_ratio": core_value / max(total_value, 1), "satellite_ratio": sat_value / max(total_value, 1), "total_ratio": (core_value + sat_value) / max(total_value, 1), "market_state": market_state})

    out = {
        "daily_nav": pd.DataFrame(nav_rows),
        "trades": pd.DataFrame(trade_rows),
        "positions": pd.DataFrame(pos_rows),
        "decisions": pd.DataFrame(decision_rows),
        "confirm_add_detail": pd.DataFrame(confirm_add_rows),
    }
    out["summary"] = summarize_path_outputs(out, variant, cap_exceeded, skipped_due_to_no_capacity)
    return out


def _max_drawdown(nav):
    if nav.empty or "nav" not in nav:
        return np.nan
    s = pd.to_numeric(nav["nav"], errors="coerce").dropna()
    if s.empty:
        return np.nan
    peak = s.cummax()
    return float((s / peak - 1).min())


def summarize_path_outputs(path, variant, cap_exceeded=0, skipped_due_to_no_capacity=0):
    nav = path.get("daily_nav", pd.DataFrame()).copy()
    trades = path.get("trades", pd.DataFrame()).copy()
    decisions = path.get("decisions", pd.DataFrame()).copy()
    rows = []
    if nav.empty:
        return pd.DataFrame([{"variant": variant, "segment": "full", "simulation_status": "NOT_A_REAL_PATH_SIMULATION"}])
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    sells = trades[trades.get("action", pd.Series(dtype=str)).astype(str).str.upper() == "SELL"].copy() if not trades.empty else pd.DataFrame()
    for seg, mask in [
        ("full", pd.Series(True, index=nav.index)),
        ("train", nav["date"] <= TRAIN_END),
        ("validation", (nav["date"] > TRAIN_END) & (nav["date"] <= VALIDATION_END)),
        ("oos", nav["date"] > VALIDATION_END),
    ]:
        g = nav[mask].copy()
        if g.empty:
            continue
        ret = float(g["nav"].iloc[-1] / g["nav"].iloc[0] - 1) if len(g) > 1 else 0.0
        dr = pd.to_numeric(g["nav"], errors="coerce").pct_change().dropna()
        sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) if len(dr) > 2 and dr.std() else np.nan
        seg_sells = sells.copy()
        if not seg_sells.empty and "date" in seg_sells:
            seg_sells["date"] = pd.to_datetime(seg_sells["date"], errors="coerce")
            seg_sells = seg_sells[(seg_sells["date"] >= g["date"].min()) & (seg_sells["date"] <= g["date"].max())]
        pnl = pd.to_numeric(seg_sells.get("pnl_val", pd.Series(dtype=float)), errors="coerce") if not seg_sells.empty else pd.Series(dtype=float)
        pnl_pct = pd.to_numeric(seg_sells.get("pnl_pct", pd.Series(dtype=float)), errors="coerce") if not seg_sells.empty else pd.Series(dtype=float)
        pos_profit = pnl[pnl > 0].sort_values(ascending=False)
        top3 = float(pos_profit.head(3).sum() / pos_profit.sum()) if pos_profit.sum() else np.nan
        fast_mask = (pnl < 0) & (pd.to_numeric(seg_sells.get("hold_days_cal", pd.Series(dtype=float)), errors="coerce").fillna(999) <= 5) if not seg_sells.empty else pd.Series(dtype=bool)
        seg_decisions = decisions.copy()
        if not seg_decisions.empty and "date" in seg_decisions:
            seg_decisions["date"] = pd.to_datetime(seg_decisions["date"], errors="coerce")
            seg_decisions = seg_decisions[(seg_decisions["date"] >= g["date"].min()) & (seg_decisions["date"] <= g["date"].max())]
        buy_dec = seg_decisions[seg_decisions.get("decision", pd.Series(dtype=str)).astype(str).eq("BUY")].copy() if not seg_decisions.empty else pd.DataFrame()
        cap_trimmed_count = int(pd.to_numeric(seg_decisions.get("cap_trimmed", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not seg_decisions.empty else 0
        avg_actual_value_ratio = np.nan
        if not buy_dec.empty and "actual_value" in buy_dec:
            avg_actual_value_ratio = (pd.to_numeric(buy_dec["actual_value"], errors="coerce") / INITIAL_CASH).mean()
        max_post_total_ratio = pd.to_numeric(seg_decisions.get("post_total_ratio", pd.Series(dtype=float)), errors="coerce").max() if not seg_decisions.empty else np.nan
        max_total_ratio = pd.to_numeric(g.get("total_ratio", pd.Series(dtype=float)), errors="coerce").max()
        buy_state = buy_dec.get("market_state", pd.Series(dtype=str)).astype(str).str.lower() if not buy_dec.empty else pd.Series(dtype=str)
        rows.append({
            "variant": variant, "segment": seg, "simulation_status": "REAL_PATH_SIMULATION_REPLAY",
            "total_return": ret, "annual_return": ret * 252 / max(len(g), 1), "max_drawdown": _max_drawdown(g),
            "sharpe": sharpe, "win_rate": float((pnl > 0).sum() / len(pnl)) if len(pnl) else np.nan,
            "trade_count": int(len(seg_sells)), "fast_loss_count": int(fast_mask.sum()) if len(seg_sells) else 0,
            "fast_loss_amount": float(-pnl[fast_mask].sum()) if len(seg_sells) else 0.0,
            "big_meat_count": int((pnl_pct > 0.10).sum()) if len(seg_sells) else 0,
            "super_meat_count": int((pnl_pct > 0.20).sum()) if len(seg_sells) else 0,
            "top3_profit_concentration": top3, "cap_exceeded_on_buy": cap_exceeded,
            "skipped_due_to_no_capacity": skipped_due_to_no_capacity,
            "cap_trimmed_count": cap_trimmed_count,
            "avg_actual_value_ratio": avg_actual_value_ratio,
            "max_post_total_ratio": max_post_total_ratio,
            "max_total_ratio": max_total_ratio,
            "bear_buy_count": int((buy_state == "bear").sum()) if len(buy_state) else 0,
            "neutral_buy_count": int((buy_state == "neutral").sum()) if len(buy_state) else 0,
            "bull_buy_count": int((buy_state == "bull").sum()) if len(buy_state) else 0,
        })
    return pd.DataFrame(rows)


def combine_paths(paths):
    out = {}
    for key in ["daily_nav", "trades", "positions", "decisions", "summary", "confirm_add_detail"]:
        frames = [p.get(key, pd.DataFrame()) for p in paths if isinstance(p.get(key, pd.DataFrame()), pd.DataFrame) and not p.get(key, pd.DataFrame()).empty]
        out[key] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return out


def fmtp(x):
    return "NA" if x is None or pd.isna(x) else f"{float(x):.2%}"


def fmtn(x, d=2):
    return "NA" if x is None or pd.isna(x) else f"{float(x):.{d}f}"


def md_table(df, n=40):
    if df is None or df.empty: return "无数据。"
    v = df.head(n).copy()
    try:
        return v.to_markdown(index=False, floatfmt=".4f")
    except Exception:
        return "```text\n" + v.to_string(index=False) + "\n```"


def build_p1_missing_summary(feature_df):
    rows = []
    df = feature_df.copy() if isinstance(feature_df, pd.DataFrame) else pd.DataFrame()
    for feature in ENTRY_FEATURES:
        available_col = feature + "_available"
        reason_col = feature + "_missing_reason"
        if feature == "entry_auc_ratio":
            available_col = "entry_auc_available"
            reason_col = "entry_auc_missing_reason"
        elif feature == "entry_turnover":
            available_col = "entry_turnover_available"
            reason_col = "entry_turnover_missing_reason"
        elif feature == "sector_strength_rank":
            available_col = "sector_strength_available"
            reason_col = "sector_strength_missing_reason"
        elif feature == "breadth_up_ratio":
            available_col = "breadth_available"
            reason_col = "breadth_missing_reason"
        elif feature == "market_10d_ret":
            available_col = "market_10d_ret_available"
            reason_col = "market_10d_ret_missing_reason"
        elif feature == "entry_rank":
            available_col = "entry_rank_available"
            reason_col = "entry_rank_missing_reason"
        elif feature == "entry_score":
            available_col = "entry_score_available"
            reason_col = "entry_score_missing_reason"

        sample_count = len(df)
        if df.empty or feature not in df.columns:
            available_count = 0
            missing_count = sample_count
            top_reason = "feature_not_generated"
        elif available_col in df.columns:
            available_count = int(pd.to_numeric(df[available_col], errors="coerce").fillna(0).sum())
            missing_count = int(sample_count - available_count)
            if reason_col in df.columns and missing_count > 0:
                reasons = df.loc[pd.to_numeric(df[available_col], errors="coerce").fillna(0).eq(0), reason_col].astype(str)
                reasons = reasons[reasons.ne("") & reasons.ne("nan")]
                top_reason = reasons.mode().iloc[0] if not reasons.mode().empty else "missing_reason_empty"
            else:
                top_reason = "" if missing_count == 0 else "missing_reason_not_available"
        else:
            available_count = int(df[feature].notna().sum())
            missing_count = int(sample_count - available_count)
            top_reason = "available_flag_missing" if missing_count > 0 else ""
        rows.append({
            "feature": feature,
            "available_count": available_count,
            "missing_count": missing_count,
            "available_rate": available_count / sample_count if sample_count else 0.0,
            "missing_reason_top1": top_reason,
            "must_fix_before_next_stage": int(feature in ["entry_auc_ratio", "entry_turnover", "sector_strength_rank", "breadth_up_ratio", "market_10d_ret", "entry_rank"] and missing_count > 0),
        })
    return pd.DataFrame(rows)


def ensure_columns(df, cols):
    out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    for col in cols:
        if col not in out.columns:
            out[col] = np.nan
    return out


def build_p1(tables):
    sells = target_sells(tables)
    fast = tables.get("v14C_fast_loss_samples", pd.DataFrame()).copy()
    meat = tables.get("v14C_big_meat_samples", pd.DataFrame()).copy()
    needs = tables.get("v14C_entry_feature_need_list", pd.DataFrame()).copy()
    cols = [c for c in ["date","stock","name","role","reason","pnl_pct","pnl_val","hold_days_cal","entry_type","signal_score","is_fast_loss","is_big_meat_10","is_super_meat_20"] if c in sells]
    log = sells[cols].copy() if cols else pd.DataFrame()
    for f in ENTRY_FEATURES:
        log[f + "_available"] = int(f in log.columns) if not log.empty else 0
    rows = []
    for label, df in [("fast_loss", fast), ("big_meat", meat), ("all_sells", sells)]:
        rows.append({
            "group": label, "sample_count": len(df),
            "avg_signal_score": df["signal_score"].mean() if "signal_score" in df else np.nan,
            "median_signal_score": df["signal_score"].median() if "signal_score" in df else np.nan,
            "avg_pnl_pct": df["pnl_pct"].mean() if "pnl_pct" in df else np.nan,
            "avg_pnl_val": df["pnl_val"].mean() if "pnl_val" in df else np.nan,
            "avg_hold_days": df["hold_days_cal"].mean() if "hold_days_cal" in df else np.nan,
            "dominant_reason": df["reason"].mode().iloc[0] if "reason" in df and not df["reason"].mode().empty else "",
        })
    compare = pd.DataFrame(rows)
    diag_rows = []
    available = set(sells.columns) | set(log.columns)
    for f in ENTRY_FEATURES:
        diag_rows.append({"feature": f, "available_now": int(f in available), "priority": "P1" if f not in available else "available", "collection_mode": "log only; do not alter trading"})
    if not needs.empty and "proposed_feature_need" in needs:
        g = needs.groupby("proposed_feature_need", dropna=False).agg(sample_count=("stock","count"), total_loss=("pnl_val","sum"), avg_loss_pct=("pnl_pct","mean")).reset_index().sort_values("total_loss")
        for _, r in g.iterrows():
            diag_rows.append({"feature": r.proposed_feature_need, "available_now": 0, "priority": "P1-loss-source", "collection_mode": f"loss_samples={int(r.sample_count)}, total_loss={r.total_loss:.0f}"})
    missing_summary = build_p1_missing_summary(log)
    return {"p1_entry_feature_trade_log": log, "p1_fast_loss_vs_big_meat_features": compare, "p1_entry_feature_diagnosis": pd.DataFrame(diag_rows), "p1_entry_feature_missing_summary": missing_summary}


def build_p2(tables, start_date, end_date):
    variants = [
        ("p2_confirm_add", {"confirm_add": True, "cap_fixed": True}),
        ("p2_quick_fail_exit", {"quick_fail_exit": True}),
        ("p2_next_day_acceptance", {"next_day_acceptance": True}),
    ]
    paths = [simulate_replay_path(tables, v, p, start_date, end_date) for v, p in variants]
    c = combine_paths(paths)
    detail_cols = ["variant", "stock", "name", "entry_date", "check_date", "entry_price", "check_price", "ma5", "pre_close", "pnl_pct", "target_value", "current_cost", "add_value", "ma5_ok", "loss_ok", "close_ok", "reason", "final_action"]
    detail = c.get("confirm_add_detail", pd.DataFrame())
    if detail.empty:
        detail = pd.DataFrame(columns=detail_cols)
    else:
        for col in detail_cols:
            if col not in detail.columns:
                detail[col] = np.nan
        detail = detail[detail_cols + [c for c in detail.columns if c not in detail_cols]]
    return {
        "p2_daily_nav": c["daily_nav"],
        "p2_trades": c["trades"],
        "p2_positions": c["positions"],
        "p2_decisions": c["decisions"],
        "p2_fast_loss_experiment_summary": c["summary"],
        "p2_confirm_add_position_detail": detail,
    }


def build_p3(tables, start_date, end_date):
    variants = [
        ("p3_cap_fixed", {"cap_fixed": True}),
        ("p3_regime_position", {"cap_fixed": True, "regime_position": True}),
    ]
    paths = [simulate_replay_path(tables, v, p, start_date, end_date) for v, p in variants]
    c = combine_paths(paths)
    p3_decision_cols = ["pre_buy_total_ratio", "target_order_ratio", "available_ratio", "post_total_ratio", "post_single_ratio", "cap_limit", "original_value", "actual_value", "cap_trimmed", "skipped_due_to_no_capacity", "market_state"]
    return {
        "p3_daily_nav": c["daily_nav"],
        "p3_trades": c["trades"],
        "p3_positions": c["positions"],
        "p3_decisions": ensure_columns(c["decisions"], p3_decision_cols),
        "p3_cap_and_regime_summary": c["summary"],
    }


def build_p4(tables, start_date, end_date):
    variants = [
        ("p4_no_promotion", {"no_promotion": True}),
        ("p4_label_only_no_add", {"label_only_no_add": True}),
        ("p4_promotion_protect", {"promotion_protect": True}),
    ]
    paths = [simulate_replay_path(tables, v, p, start_date, end_date) for v, p in variants]
    c = combine_paths(paths)
    p4_cols = ["promotion_date", "promotion_state", "promoted_from_role", "post_promotion_entry_price", "post_promotion_pnl", "promotion_action"]
    return {
        "p4_daily_nav": c["daily_nav"],
        "p4_trades": c["trades"],
        "p4_positions": ensure_columns(c["positions"], p4_cols),
        "p4_decisions": ensure_columns(c["decisions"], p4_cols),
        "p4_promotion_protection_summary": c["summary"],
    }


def unified_checks(tables):
    summary = tables.get("role_rotation_summary", pd.DataFrame())
    sens = tables.get("role_rotation_sensitivity", pd.DataFrame())
    cost = tables.get("role_rotation_cost_sensitivity", pd.DataFrame())
    conc = tables.get("role_rotation_overfit_check", pd.DataFrame())
    loss_big = tables.get("v14C_loss_bigmeat_summary", pd.DataFrame())
    cap = tables.get("role_rotation_cap_check", pd.DataFrame())
    final = tables.get("v14C_overfit_final_check", pd.DataFrame())
    rows = []
    if not summary.empty:
        for _, r in summary[summary.variant == TARGET].iterrows():
            rows.append({"check_group": "segment", "check_item": r.segment, "value": r.total_return, "assessment": "Pass" if r.total_return > 0 else "Fail", "evidence": f"return={fmtp(r.total_return)}, dd={fmtp(r.max_drawdown)}, win={fmtp(r.win_rate)}, sharpe={fmtn(r.sharpe)}"})
    if not sens.empty:
        rows.append({"check_group": "parameter_perturbation", "check_item": "return_std", "value": sens.total_return.std(), "assessment": "Fail" if sens.total_return.std() >= 0.10 else "Pass", "evidence": f"range={fmtp(sens.total_return.min())}~{fmtp(sens.total_return.max())}"})
    if not final.empty:
        for _, r in final.iterrows():
            rows.append({"check_group": "final_overfit_file", "check_item": r.metric, "value": r.value, "assessment": r.assessment, "evidence": f"status={r.status}, threshold={r.threshold}"})
    if not loss_big.empty:
        for _, r in loss_big.iterrows():
            rows.append({"check_group": "loss_bigmeat", "check_item": r.category, "value": r.total_pnl_val, "assessment": "Watch" if r.category in ("fast_loss", "big_loss") else "Info", "evidence": f"count={int(r.trade_count)}, pct={fmtp(r.pct_of_all_sells)}"})
    if not cap.empty:
        c = cap[cap.variant == TARGET]
        rows.append({"check_group": "cap", "check_item": "cap_exceeded_on_buy", "value": c.cap_exceeded_on_buy.sum(), "assessment": "Pass" if c.cap_exceeded_on_buy.sum() == 0 else "Fail", "evidence": f"max_post_buy_ratio={fmtp(c.post_buy_total_ratio.max())}"})
    return {"p_overfit_check_summary": pd.DataFrame(rows), "p_cost_sensitivity_summary": cost, "p_profit_concentration_summary": conc}


def baseline_fast_loss_amount(tables):
    trades = target_table(tables, "role_rotation_trades")
    if trades.empty or "action" not in trades.columns:
        return np.nan, "baseline_fast_loss_unavailable"
    sells = trades[trades["action"].astype(str).str.upper().eq("SELL")].copy()
    if sells.empty or "pnl_val" not in sells.columns or "hold_days_cal" not in sells.columns:
        return np.nan, "baseline_sell_fields_missing"
    pnl = pd.to_numeric(sells["pnl_val"], errors="coerce")
    hold = pd.to_numeric(sells["hold_days_cal"], errors="coerce")
    mask = hold.le(5) & pnl.lt(0)
    return float(-pnl[mask].sum()), ""


def build_p5(tables, checks, start_date, end_date):
    path = simulate_replay_path(
        tables,
        "p5_combined_observer",
        {"combined_observer": True, "cap_fixed": True, "regime_position": True, "promotion_protect": True},
        start_date,
        end_date,
    )
    summary = path["summary"].copy()
    if not summary.empty:
        summary["p1_status"] = "feature_collection_only"
        summary["p2_status"] = "independent_path_component"
        summary["p3_status"] = "independent_path_component"
        summary["p4_status"] = "independent_path_component"
        summary["used_p2_confirm_add"] = True
        summary["used_p2_quick_fail_exit"] = True
        summary["used_p3_cap_fixed"] = True
        summary["used_p3_regime_position"] = True
        summary["used_p4_promotion_protect"] = True
    base_summary = tables.get("role_rotation_summary", pd.DataFrame()).copy()
    base_full = base_summary[(base_summary.get("variant") == TARGET) & (base_summary.get("segment") == "full")].iloc[0] if not base_summary.empty and ((base_summary.get("variant") == TARGET) & (base_summary.get("segment") == "full")).any() else pd.Series(dtype=object)
    p5_full = summary[summary.get("segment") == "full"].iloc[0] if not summary.empty and (summary.get("segment") == "full").any() else pd.Series(dtype=object)
    base_ret, p5_ret = base_full.get("total_return", np.nan), p5_full.get("total_return", np.nan)
    base_dd, p5_dd = base_full.get("max_drawdown", np.nan), p5_full.get("max_drawdown", np.nan)
    base_fast_loss, fast_loss_warning = baseline_fast_loss_amount(tables)
    p5_fast_loss = p5_full.get("fast_loss_amount", np.nan)
    fast_loss_change = (
        p5_fast_loss - base_fast_loss
        if not pd.isna(p5_fast_loss) and not pd.isna(base_fast_loss)
        else np.nan
    )
    component_rows = []
    for component, target, expected in [
        ("p2_confirm_add", "improve entry staging", "reduce bad first-entry exposure while allowing confirmation add"),
        ("p2_quick_fail_exit", "reduce fast_loss", "cut weak positions earlier"),
        ("p3_cap_fixed", "avoid cap breach", "trim order instead of over-cap buy"),
        ("p3_regime_position", "reduce weak-market exposure", "dynamic cap by market state"),
        ("p4_promotion_protect", "protect post-promotion profit", "exit promoted position if not strong"),
    ]:
        component_rows.append({
            "component": component,
            "enabled": True,
            "effect_target": target,
            "expected_effect": expected,
            "actual_fast_loss_change": fast_loss_change,
            "actual_drawdown_change": p5_dd - base_dd if not pd.isna(p5_dd) and not pd.isna(base_dd) else np.nan,
            "actual_return_change": p5_ret - base_ret if not pd.isna(p5_ret) and not pd.isna(base_ret) else np.nan,
            "warning": "combined replay attribution; not isolated causal proof" + ("" if not fast_loss_warning else "; " + fast_loss_warning),
        })
    component_effect = pd.DataFrame(component_rows)
    report = "# P5 综合观测版报告\n\nP5 是研究用独立路径重放，不是主线，不是实盘版。\n\n" + md_table(summary) + "\n\n## 统一反过拟合检查\n\n" + md_table(checks.get("p_overfit_check_summary", pd.DataFrame()), 80)
    return {
        "p5_daily_nav": path["daily_nav"],
        "p5_trades": path["trades"],
        "p5_positions": path["positions"],
        "p5_decisions": path["decisions"],
        "p5_combined_observer_summary": summary,
        "p5_component_effect_summary": component_effect,
        "p5_combined_observer_report": report,
    }


def write_excel(path, tables):
    last = None
    for engine in ("openpyxl", "xlsxwriter"):
        try:
            with pd.ExcelWriter(path, engine=engine) as writer:
                for name, df in tables.items():
                    if isinstance(df, pd.DataFrame): df.to_excel(writer, sheet_name=name[:31], index=False)
            return
        except Exception as e:
            last = e
    raise RuntimeError(f"Excel export failed: {last}")


def zip_outputs(outdir, zip_path):
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(outdir.iterdir()):
            if p.is_file() and p != zip_path:
                zf.write(p, p.name)


def path_simulation_flags(outputs):
    flags = {"p1_is_feature_collection_only": True}
    for p in ["p2", "p3", "p4", "p5"]:
        daily_ok = isinstance(outputs.get(f"{p}_daily_nav"), pd.DataFrame) and not outputs.get(f"{p}_daily_nav").empty
        summary_name = {
            "p2": "p2_fast_loss_experiment_summary",
            "p3": "p3_cap_and_regime_summary",
            "p4": "p4_promotion_protection_summary",
            "p5": "p5_combined_observer_summary",
        }[p]
        summary_ok = isinstance(outputs.get(summary_name), pd.DataFrame) and not outputs.get(summary_name).empty
        keys_exist = all(f"{p}_{suffix}" in outputs and isinstance(outputs.get(f"{p}_{suffix}"), pd.DataFrame) for suffix in ["daily_nav", "trades", "positions", "decisions"])
        ok = daily_ok and summary_ok and keys_exist
        flags[f"{p}_is_independent_path_sim"] = bool(ok)
        flags[f"{p}_simulation_status"] = "REAL_PATH_SIMULATION_REPLAY" if ok else "NOT_A_REAL_PATH_SIMULATION"
    return flags


def path_simulation_status_table(outputs):
    flags = path_simulation_flags(outputs)
    rows = []
    rows.append({"module": "P1", "is_real_path_simulation": False, "status": "FEATURE_COLLECTION_ONLY", "required_outputs": "p1_jq_entry_features / p1_entry_feature_trade_log"})
    for p in ["p2", "p3", "p4", "p5"]:
        rows.append({
            "module": p.upper(),
            "is_real_path_simulation": flags[f"{p}_is_independent_path_sim"],
            "status": flags[f"{p}_simulation_status"],
            "required_outputs": ",".join([f"{p}_daily_nav", f"{p}_trades", f"{p}_positions", f"{p}_decisions"]),
        })
    return pd.DataFrame(rows)


def quality_manifest_flags(outputs):
    p1_missing = outputs.get("p1_entry_feature_missing_summary", pd.DataFrame())
    missing_features = []
    if isinstance(p1_missing, pd.DataFrame) and not p1_missing.empty and "missing_count" in p1_missing:
        missing_features = p1_missing.loc[pd.to_numeric(p1_missing["missing_count"], errors="coerce").fillna(0).gt(0), "feature"].astype(str).tolist()

    p2_detail = outputs.get("p2_confirm_add_position_detail", pd.DataFrame())
    p2_cols = ["variant", "stock", "name", "entry_date", "check_date", "entry_price", "check_price", "ma5", "pre_close", "pnl_pct", "target_value", "current_cost", "add_value", "ma5_ok", "loss_ok", "close_ok", "reason", "final_action"]
    p3_dec = outputs.get("p3_decisions", pd.DataFrame())
    p3_cols = ["pre_buy_total_ratio", "target_order_ratio", "available_ratio", "post_total_ratio", "post_single_ratio", "cap_limit", "original_value", "actual_value", "cap_trimmed", "skipped_due_to_no_capacity", "market_state"]
    p4_pos = outputs.get("p4_positions", pd.DataFrame())
    p4_dec = outputs.get("p4_decisions", pd.DataFrame())
    p4_cols = ["promotion_date", "promotion_state", "promoted_from_role", "post_promotion_entry_price", "post_promotion_pnl", "promotion_action"]
    p5_comp = outputs.get("p5_component_effect_summary", pd.DataFrame())
    return {
        "p1_all_required_features_present": len(missing_features) == 0,
        "p1_missing_required_features": missing_features,
        "p1_missing_feature_count": len(missing_features),
        "p2_confirm_add_detail_complete": isinstance(p2_detail, pd.DataFrame) and all(c in p2_detail.columns for c in p2_cols),
        "p3_cap_detail_complete": isinstance(p3_dec, pd.DataFrame) and all(c in p3_dec.columns for c in p3_cols),
        "p4_promotion_state_complete": isinstance(p4_pos, pd.DataFrame) and isinstance(p4_dec, pd.DataFrame) and all(c in p4_pos.columns for c in p4_cols) and all(c in p4_dec.columns for c in p4_cols),
        "p5_component_summary_complete": isinstance(p5_comp, pd.DataFrame) and not p5_comp.empty,
    }


def build_report(tables, outputs, source_dir, output_dir, missing, mode="local_analysis", sim_meta=None):
    summary = tables.get("role_rotation_summary", pd.DataFrame())
    target = summary[summary.variant == TARGET] if not summary.empty else pd.DataFrame()
    def seg(name):
        g = target[target.segment == name]
        return g.iloc[0] if not g.empty else pd.Series(dtype=object)
    full, train, validation, oos = seg("full"), seg("train"), seg("validation"), seg("oos")
    lines = [
        "# v14C P1~P5 Master Research Report", "",
        "## 0. 运行模式", "",
        f"* mode: `{mode}`",
        f"* environment: `{'joinquant' if mode == 'jq_direct_sim' else 'local'}`",
        "* local_analysis 只做已有 CSV/XLSX 复盘，不作为最终策略结论。" if mode == "local_analysis" else "* jq_direct_sim 已先调用聚宽研究环境行情 API 重新逐日模拟，再生成 P1~P5 研究结果。",
        f"* direct_sim_meta: `{json.dumps(sim_meta or {}, ensure_ascii=False)}`", "",
        "## 1. 执行摘要", "",
        "本脚本只读分析现有 v1.4.0C 结果包；不修改策略，不修改 `research_role_rotation_direct_sim_v1.py`，不进入主线，不实盘化。",
        f"源目录：`{source_dir}`", f"输出目录：`{output_dir}`", "",
        "## 2. v1.4.0C 当前问题复核", "",
        f"* full: return={fmtp(full.get('total_return', np.nan))}, drawdown={fmtp(full.get('max_drawdown', np.nan))}, win_rate={fmtp(full.get('win_rate', np.nan))}, sharpe={fmtn(full.get('sharpe', np.nan))}",
        f"* train / validation / oos return: {fmtp(train.get('total_return', np.nan))} / {fmtp(validation.get('total_return', np.nan))} / {fmtp(oos.get('total_return', np.nan))}",
        "* 不进主线理由：参数扰动不稳、Top3 盈利集中度 Fail、fast_loss 高、晋级后纯段 PnL 为负、cap 仍有超限记录。", "",
        "## 3. P1 entry feature 补采集结果", "", md_table(outputs.get("p1_entry_feature_diagnosis", pd.DataFrame()), 80), "",
        "## 3.0 P1 缺失字段摘要", "", md_table(outputs.get("p1_entry_feature_missing_summary", pd.DataFrame()), 80), "",
        "说明：P1 缺失字段不阻断研究脚本运行，但会影响选股归因完整性；缺失字段只能带 missing_reason，不能伪造。", "",
        "## 3.1 P2/P3/P4/P5 路径模拟验收", "", md_table(outputs.get("p_path_simulation_status", pd.DataFrame()), 20), "",
        "说明：P1 只允许是 feature collection；P2/P3/P4/P5 如果缺少 daily_nav/trades/positions/decisions，会标记 NOT_A_REAL_PATH_SIMULATION。", "",
        "## 4. P2 fast_loss 降损实验结果", "", md_table(outputs.get("p2_fast_loss_experiment_summary", pd.DataFrame()), 40), "",
        "## 5. P3 仓位 cap 与弱市降频实验结果", "", md_table(outputs.get("p3_cap_and_regime_summary", pd.DataFrame()), 40), "",
        "## 6. P4 晋级后保护实验结果", "", md_table(outputs.get("p4_promotion_protection_summary", pd.DataFrame()), 40), "",
        "## 7. P5 综合观测版结果", "", md_table(outputs.get("p5_combined_observer_summary", pd.DataFrame()), 20), "",
        "## 7.1 P5 组件效果摘要", "", md_table(outputs.get("p5_component_effect_summary", pd.DataFrame()), 20), "",
        "## 8. 统一反过拟合检查", "", md_table(outputs.get("p_overfit_check_summary", pd.DataFrame()), 100), "",
        "## 8.1 当前实验性质声明", "", "P2~P5 是基于 v1.4.0C 买入事件的反事实路径重放，不是主线策略，不是真实执行版。若 P1 字段仍缺失，只能继续做研究，不可直接进入策略决策。", "",
        "## 9. 是否建议进入主线", "", "否。当前 v1.4.0C 不进入主线。", "",
        "## 10. 是否建议进入真实执行版", "", "否。当前 v1.4.0C 不进入真实执行版。", "",
        "## 11. 是否建议继续研究", "", "是。P1~P5 只作为研究分支继续推进。", "",
        "## 12. 下一步最优先事项", "", "1. P1 entry feature 补采集。\n2. P2 fast_loss 降损观察。\n3. P3 cap 严格控制。\n4. P4 晋级后保护。", "",
        "## 13. 禁止事项", "", "不放宽 deep_water；不扩大仓位；不自动搜索最优参数；不因 full 收益高就进主线。",
    ]
    if missing:
        lines += ["", "## Source Warnings", "", md_table(pd.DataFrame({"missing_file": missing}))]
    return "\n".join(lines)


def write_outputs(
    outdir: Path,
    source_dir: Path,
    tables: Dict[str, pd.DataFrame],
    outputs: Dict[str, object],
    missing: List[str],
    start_date: str,
    end_date: str,
    mode: str = "local_analysis",
    sim_meta: Dict[str, object] = None,
):
    outdir.mkdir(parents=True, exist_ok=True)
    for name, obj in list(outputs.items()):
        if isinstance(obj, pd.DataFrame):
            obj.to_csv(outdir / f"{name}.csv", index=False, encoding="utf-8-sig")
        elif isinstance(obj, str):
            (outdir / f"{name}.md").write_text(obj, encoding="utf-8-sig")
    report = build_report(tables, outputs, source_dir, outdir, missing, mode=mode, sim_meta=sim_meta)
    prefix = "v14C_P1_to_P5_JQ" if mode == "jq_direct_sim" else "v14C_P1_to_P5"
    report_path = outdir / f"{prefix}_master_report.md"
    report_path.write_text(report, encoding="utf-8-sig")
    xlsx_path = outdir / f"{prefix}_outputs.xlsx"
    excel_tables = {k: v for k, v in outputs.items() if isinstance(v, pd.DataFrame)}
    excel_tables["source_missing_files"] = pd.DataFrame({"missing_file": missing})
    write_excel(xlsx_path, excel_tables)
    path_flags = path_simulation_flags(outputs)
    quality_flags = quality_manifest_flags(outputs)
    manifest = {
        "script": Path(__file__).name, "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": start_date, "end_date": end_date, "source_dir": str(source_dir), "output_dir": str(outdir),
        "mode": mode, "environment": "joinquant" if mode == "jq_direct_sim" else "local",
        "research_only": True, "no_strategy_files_modified": True, "no_mainline_promotion": True,
        "no_live_execution": True, "no_auto_parameter_search": True, "no_deep_water_relaxation": True,
        "no_position_expansion": True, "missing_files": missing,
        "local_analysis_is_final_conclusion": False,
        "jq_direct_sim_is_final_research_basis": mode == "jq_direct_sim",
        **path_flags,
        **quality_flags,
        "direct_sim_meta": sim_meta or {},
        "outputs": sorted([p.name for p in outdir.iterdir() if p.is_file()]),
    }
    manifest_path = outdir / f"{prefix}_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = outdir / f"{prefix}_result_bundle.zip"
    zip_outputs(outdir, zip_path)
    return {"report": report_path, "xlsx": xlsx_path, "manifest": manifest_path, "zip": zip_path}


def run_all_p1_to_p5(
    start_date="2025-07-01",
    end_date="2026-06-14",
    source_dir="role_rotation_result_bundle V140C",
    output_dir="role_rotation_result_bundle V140C_P1_P5_JQ",
    mode="jq_direct_sim",
    run_p1=True,
    run_p2=True,
    run_p3=True,
    run_p4=True,
    run_p5=True,
):
    if mode not in ("local_analysis", "jq_direct_sim"):
        raise ValueError("mode must be 'local_analysis' or 'jq_direct_sim'")

    source = resolve_dir(source_dir)
    outdir = resolve_dir(output_dir)
    sim_meta = {}

    if mode == "jq_direct_sim":
        print("P1_P5|mode=jq_direct_sim|step=run_role_rotation_direct_sim")
        sim_meta = run_jq_direct_baseline(start_date, end_date, outdir)
        # In jq_direct_sim, the freshly generated direct simulation output is the source of truth.
        source_for_analysis = outdir
    else:
        print("P1_P5|mode=local_analysis|note=existing_csv_replay_not_final_conclusion")
        source_for_analysis = source

    tables, texts, missing = load_bundle(source_for_analysis)
    outputs = {}
    p1 = build_p1(tables) if run_p1 else {}
    if mode == "jq_direct_sim" and run_p1:
        jq_entry, jq_entry_diag = enrich_entry_features_from_jq(tables, start_date, end_date)
        p1["p1_jq_entry_features"] = jq_entry
        p1["p1_jq_entry_feature_diagnostics"] = jq_entry_diag
        if "p1_entry_feature_trade_log" in p1 and not jq_entry.empty:
            p1["p1_entry_feature_trade_log"] = jq_entry
            p1["p1_entry_feature_missing_summary"] = build_p1_missing_summary(jq_entry)
    p2 = build_p2(tables, start_date, end_date) if run_p2 else {}
    p3 = build_p3(tables, start_date, end_date) if run_p3 else {}
    p4 = build_p4(tables, start_date, end_date) if run_p4 else {}
    checks = unified_checks(tables)
    p5 = build_p5(tables, checks, start_date, end_date) if run_p5 else {}
    for block in (p1, p2, p3, p4, checks, p5): outputs.update(block)
    outputs["p_path_simulation_status"] = path_simulation_status_table(outputs)
    paths = write_outputs(outdir, source_for_analysis, tables, outputs, missing, start_date, end_date, mode=mode, sim_meta=sim_meta)
    print(f"P1_P5|mode={mode}|output_dir={outdir}")
    print(f"P1_P5|report={paths['report']}")
    print(f"P1_P5|xlsx={paths['xlsx']}")
    print(f"P1_P5|manifest={paths['manifest']}")
    print(f"P1_P5|zip={paths['zip']}")
    print("P1_P5|done=1")
    return paths


if __name__ == "__main__":
    run_all_p1_to_p5(mode="local_analysis", output_dir="role_rotation_result_bundle V140C_P1_P5")
