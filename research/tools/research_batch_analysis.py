# -*- coding: utf-8 -*-
"""
JoinQuant research batch analysis for A-strategy signal templates.

Run this in JoinQuant Research/Notebook, not in a backtest strategy editor.
It uses data APIs only and intentionally avoids order/context/schedule APIs.
"""

from __future__ import print_function

import itertools
import math
import os
from collections import defaultdict

import numpy as np
import pandas as pd

try:
    from jqdata import *  # noqa
except Exception:
    # JoinQuant research normally provides jqdata. This fallback only lets
    # local syntax checks import the file without executing research APIs.
    pass


# =========================
# User parameters
# =========================

START_DATE = "2026-05-21"
END_DATE = "2026-05-27"

OUTPUT_DIR = "."
UNIVERSE_INDEX = None          # None = all A shares after prefix/new-stock filters.
NEW_STOCK_DAYS = 50
CHUNK_SIZE = 800
TOP_N_PER_DAY = 12

# Faster default: use daily open as the tradable open proxy.
# Set True only when you accept much slower per-stock get_call_auction calls.
USE_CALL_AUCTION = False

EXCLUDE_PREFIXES = ("30", "688", "689", "8", "4", "9")

ALIGNMENT_CHECKS = {
    "2026-05-21": ["000636.XSHE"],
    "2026-05-26": ["002380.XSHE"],
    "2026-05-27": ["002745.XSHE"],
}


CFG = {
    "regime_index": "000852.XSHG",
    "regime_secondary_index": "000300.XSHG",
    "regime_lookback": 20,
    "regime_bull_ma_fast": 5,
    "regime_bull_ma_mid": 10,
    "regime_bull_ma_slow": 20,
    "regime_crash_3d_threshold": -0.05,
    "dragon_ret3_top_n": 160,
    "dragon_money_top_pct": 0.20,
    "dragon_auc_top_n": 80,
    "dragon_min_auction_amount": 8.0e6,
    "dragon_min_auction_ratio": 0.006,
    "dragon_min_prev_money": 1.5e8,
    "dragon_max_avg_daily_range": 0.08,
    "dragon_prev_auction_mult": 0.50,
    "dragon_score_mode": "v3",
    "dragon_min_ret_3d": 0.03,
    "lowopen_gap_min": 0.96,
    "lowopen_gap_max": 0.97,
    "lowopen_rp_fixed": 0.50,
    "lowopen_min_money": 1e8,
}


SWEEP = {
    "deep_water_only": [False, True],
    "open_ratio_max": [0.03, 0.04, 0.05, 0.065],
    "score_quantile": [0.0, 0.5, 0.7, 0.8],
    "trend_core_enabled": [True, False],
    "regime_filter_enabled": [False, True],
}


# =========================
# Utilities
# =========================

def _to_date_str(x):
    return str(pd.Timestamp(x).date())


def _ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path)


def _chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _safe_float(value, default=np.nan):
    try:
        if value is None:
            return default
        if isinstance(value, str) and value.strip() == "":
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def _safe_int(value, default=0):
    out = _safe_float(value, default)
    try:
        if out is None or math.isnan(out) or math.isinf(out):
            return default
        return int(out)
    except Exception:
        return default


def _pct(value):
    return value * 100.0 if pd.notnull(value) else np.nan


def _is_missing(value):
    try:
        return pd.isnull(value)
    except Exception:
        return value is None


def _daily_auction_ratio_proxy(open_ratio):
    """Daily-only proxy used when call auction data is unavailable.

    The mother strategy requires real auction ratio >= min_ratio * 1.2 for
    deep_water. Using min_ratio itself makes deep_water impossible, so this
    proxy marks the data mode honestly and only removes the artificial block.
    """
    min_ratio = CFG["dragon_min_auction_ratio"]
    if _is_missing(open_ratio):
        return min_ratio * 1.25
    return max(min_ratio * 1.25, min(0.03, abs(open_ratio) * 0.25))


def _alignment_targets_for_date(date):
    return set(ALIGNMENT_CHECKS.get(date, []))


def get_research_universe(date):
    """Research-safe universe builder: no get_current_data, no context."""
    if UNIVERSE_INDEX:
        stocks = list(get_index_stocks(UNIVERSE_INDEX, date=date))
        sec = get_all_securities(["stock"], date=date)
        sec = sec.loc[sec.index.intersection(stocks)]
    else:
        sec = get_all_securities(["stock"], date=date)

    if sec is None or sec.empty:
        return []

    sec = sec[~sec.index.to_series().str.startswith(EXCLUDE_PREFIXES)]
    cutoff = pd.Timestamp(date) - pd.Timedelta(days=NEW_STOCK_DAYS)
    if "start_date" in sec.columns:
        sec = sec[pd.to_datetime(sec["start_date"]) < cutoff]
    return sec.index.tolist()


def explain_universe_exclusion(stock, date):
    try:
        sec = get_all_securities(["stock"], date=date)
    except Exception as e:
        return "get_all_securities_error:{}".format(e)
    if sec is None or sec.empty:
        return "get_all_securities_empty"
    if stock not in sec.index:
        return "not_listed_by_get_all_securities_prev_date"
    if stock.startswith(EXCLUDE_PREFIXES):
        return "excluded_by_prefix"
    cutoff = pd.Timestamp(date) - pd.Timedelta(days=NEW_STOCK_DAYS)
    if "start_date" in sec.columns:
        start_date = pd.Timestamp(sec.loc[stock, "start_date"])
        if start_date >= cutoff:
            return "new_stock_start_date_{}".format(start_date.date())
    return "not_in_research_universe_unknown"


def get_price_panel(stocks, start_date, end_date):
    """Batch daily OHLCV. Returns DataFrame indexed by date/code columns."""
    frames = []
    fields = ["open", "close", "high", "low", "money", "volume", "high_limit", "paused"]
    for chunk in _chunked(stocks, CHUNK_SIZE):
        try:
            df = get_price(
                chunk,
                start_date=start_date,
                end_date=end_date,
                frequency="daily",
                fields=fields,
                skip_paused=False,
                fq="pre",
                panel=False,
                fill_paused=False,
            )
            if df is not None and not df.empty:
                frames.append(df)
        except Exception as e:
            print("get_price chunk failed: {} stocks, {}".format(len(chunk), e))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["time"] = pd.to_datetime(out["time"]).dt.date.astype(str)
    return out


def get_single_index_regime(index_code, date):
    h = get_price(
        index_code,
        end_date=date,
        count=CFG["regime_lookback"],
        frequency="daily",
        fields=["close"],
        skip_paused=True,
        fq="pre",
        panel=False,
    )
    if h is None or len(h) < CFG["regime_lookback"]:
        return "neutral"
    close_s = h["close"]
    ma_fast = close_s.iloc[-CFG["regime_bull_ma_fast"]:].mean()
    ma_mid = close_s.iloc[-CFG["regime_bull_ma_mid"]:].mean()
    ma_slow = close_s.iloc[-CFG["regime_bull_ma_slow"]:].mean()
    ret3 = close_s.iloc[-1] / close_s.iloc[-4] - 1 if len(close_s) >= 4 else 0.0
    if ret3 <= CFG["regime_crash_3d_threshold"]:
        return "bear"
    if ma_fast > ma_mid > ma_slow:
        return "bull"
    if ma_fast < ma_mid < ma_slow:
        return "bear"
    return "neutral"


def get_market_regime(date):
    return get_single_index_regime(CFG["regime_index"], date)


def close_to_high_template(close_to_high, ret3, open_ratio, auction_ratio):
    tpl = "trend_core"
    if (0.90 <= close_to_high < 0.975
            and open_ratio >= 0.015
            and auction_ratio >= CFG["dragon_min_auction_ratio"] * 1.2):
        tpl = "deep_water"
    return tpl


def calc_dragon_score(row):
    ret3 = row["ret3"]
    auction_ratio = row["auction_ratio"]
    close_to_high = row["close_to_high"]
    avg_range = row.get("avg_range", 0.0)
    tpl = row["tpl"]

    inv_c2h = 1.0 - close_to_high
    score = 0.0
    score += inv_c2h * 2.5
    score += avg_range * 4.0
    score += max(0, 0.03 - auction_ratio) * 8.0
    score += min(max(ret3, 0.0), 0.25) * inv_c2h * 2.0
    score += min(max(ret3, 0.0), 0.30) * 0.50
    if tpl == "deep_water":
        score += 0.15
    return score


def get_call_auction_proxy(stock, date, y_close, y_vol):
    """Optional slow path. Returns open price proxy, auction ratio, amount."""
    if not USE_CALL_AUCTION:
        return np.nan, np.nan, np.nan
    try:
        start = "{} 09:15:00".format(date)
        end = "{} 09:26:00".format(date)
        ad = get_call_auction(stock, start_date=start, end_date=end, fields=["time", "current", "volume"])
        if ad is None or ad.empty:
            return np.nan, np.nan, np.nan
        curr = _safe_float(ad["current"].iloc[-1])
        auc_vol = _safe_float(ad["volume"].iloc[-1], 0.0)
        return curr, auc_vol / max(y_vol, 1.0), curr * auc_vol
    except Exception:
        return np.nan, np.nan, np.nan


# =========================
# Signal builders
# =========================

def _new_alignment_row(date, stock, universe_hit=False):
    return {
        "date": date,
        "stock": stock,
        "universe": bool(universe_hit),
        "prefilter": False,
        "dragon_candidate": False,
        "top12": False,
        "rank": np.nan,
        "tpl": "",
        "dragon_score": np.nan,
        "open_ratio": np.nan,
        "close_to_high": np.nan,
        "auc_ratio": np.nan,
        "prev_money": np.nan,
        "ret3": np.nan,
        "data_mode": "",
        "filtered_reason": "not_checked",
    }


def _update_alignment_row(row, data, reason=None):
    for key in [
            "tpl", "dragon_score", "open_ratio", "close_to_high", "auc_ratio",
            "prev_money", "ret3", "data_mode"]:
        if key in data:
            row[key] = data[key]
    if reason is not None:
        row["filtered_reason"] = reason


def build_dragon_candidates_for_day(date, prev_date, future_dates, daily_df, regime,
                                    universe=None, alignment_stocks=None):
    by_code = {code: df.sort_values("time") for code, df in daily_df.groupby("code")}
    universe_set = set(universe or [])
    alignment_stocks = set(alignment_stocks or [])
    alignment = {
        stock: _new_alignment_row(date, stock, stock in universe_set)
        for stock in alignment_stocks
    }

    base_rows = []
    for stock, df in by_code.items():
        past = df[df["time"] <= prev_date].tail(4)
        today = df[df["time"] == date]
        future = df[df["time"].isin(future_dates)].sort_values("time")
        if len(past) < 4 or today.empty or len(future) < 1:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "missing_past_today_or_future_data"
            continue

        y = past.iloc[-1]
        t = today.iloc[0]
        if _safe_int(y.get("paused", 0), 0) == 1:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "paused_on_prev_date"
            continue
        y_close = _safe_float(y["close"])
        y_high = _safe_float(y["high"])
        y_high_limit = _safe_float(y.get("high_limit", np.nan))
        y_money = _safe_float(y["money"], 0.0)
        y_vol = _safe_float(y["volume"], 0.0)
        if y_close <= 0 or y_high <= 0:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "invalid_prev_close_or_high"
            continue
        if pd.notnull(y_high_limit) and y_close >= y_high_limit * 0.995:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "prev_close_near_high_limit"
            continue
        if y_money < CFG["dragon_min_prev_money"]:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "prev_money_below_min"
            continue

        ret3 = y_close / _safe_float(past["close"].iloc[0]) - 1
        ret1 = y_close / _safe_float(past["close"].iloc[-2]) - 1
        open_price = _safe_float(t["open"])
        today_high_limit = _safe_float(t.get("high_limit", np.nan))

        auc_price, auc_ratio, auc_amount = get_call_auction_proxy(stock, date, y_close, y_vol)
        if pd.isnull(auc_price):
            auc_price = open_price
        open_ratio = auc_price / y_close - 1 if y_close > 0 else np.nan
        if pd.isnull(auc_ratio):
            auc_ratio = _daily_auction_ratio_proxy(open_ratio)
        if pd.isnull(auc_amount):
            auc_amount = auc_price * y_vol * auc_ratio

        if pd.isnull(open_ratio) or open_ratio <= 0:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "open_ratio_not_positive"
                _update_alignment_row(alignment[stock], {
                    "open_ratio": open_ratio,
                    "auc_ratio": auc_ratio,
                    "prev_money": y_money,
                    "ret3": ret3,
                    "data_mode": "call_auction" if USE_CALL_AUCTION else "daily_open_proxy",
                })
            continue
        if pd.notnull(today_high_limit) and auc_price >= today_high_limit * 0.995:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "open_near_today_high_limit"
            continue
        if USE_CALL_AUCTION and (auc_ratio < CFG["dragon_min_auction_ratio"]
                                 or auc_amount < CFG["dragon_min_auction_amount"]):
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "auction_ratio_or_amount_below_min"
            continue

        close_to_high = y_close / max(y_high, 0.01)
        hist10_src = df[(df["time"] <= prev_date) & (df["paused"].apply(lambda x: _safe_int(x, 0)) == 0)]
        hist10 = hist10_src.tail(10)
        avg_range = float(((hist10["high"] - hist10["low"]) / hist10["close"]).mean()) \
            if len(hist10) >= 5 else 0.0
        if avg_range > CFG["dragon_max_avg_daily_range"]:
            if stock in alignment:
                alignment[stock]["filtered_reason"] = "avg_range_above_max"
            continue

        if stock in alignment:
            alignment[stock]["prefilter"] = True
            alignment[stock]["filtered_reason"] = "prefilter_pass_not_scored_yet"
            _update_alignment_row(alignment[stock], {
                "open_ratio": open_ratio,
                "close_to_high": close_to_high,
                "auc_ratio": auc_ratio,
                "prev_money": y_money,
                "ret3": ret3,
                "data_mode": "call_auction" if USE_CALL_AUCTION else "daily_open_proxy",
            })

        base_rows.append({
            "date": date,
            "stock": stock,
            "entry_type": "dragon_follow",
            "ret1": ret1,
            "ret3": ret3,
            "y_money": y_money,
            "prev_money": y_money,
            "y_close": y_close,
            "y_high": y_high,
            "open_price": auc_price,
            "open_ratio": open_ratio,
            "auction_ratio": auc_ratio,
            "auction_amount": auc_amount,
            "close_to_high": close_to_high,
            "avg_range": avg_range,
            "regime": regime,
            "data_mode": "call_auction" if USE_CALL_AUCTION else "daily_open_proxy",
        })

    for stock, row in alignment.items():
        if row["filtered_reason"] == "not_checked":
            if not row["universe"]:
                row["filtered_reason"] = "not_in_research_universe"
            elif stock not in by_code:
                row["filtered_reason"] = "no_daily_data_after_universe"
            else:
                row["filtered_reason"] = "not_reached_unknown"

    if not base_rows:
        return [], list(alignment.values())

    ret3_top = set([x["stock"] for x in sorted(base_rows, key=lambda r: r["ret3"], reverse=True)
                    [:CFG["dragon_ret3_top_n"]]])
    money_top_n = max(1, int(len(base_rows) * CFG["dragon_money_top_pct"]))
    money_top = set([x["stock"] for x in sorted(base_rows, key=lambda r: r["y_money"], reverse=True)
                     [:money_top_n]])
    seed = ret3_top | money_top
    auc_top = set([x["stock"] for x in sorted(base_rows, key=lambda r: r["open_ratio"], reverse=True)
                   [:CFG["dragon_auc_top_n"]]])

    rows = []
    for row in base_rows:
        if row["stock"] not in seed:
            if row["stock"] in alignment:
                alignment[row["stock"]]["filtered_reason"] = "not_in_ret3_or_money_seed"
            continue
        if row["stock"] not in auc_top and row["stock"] not in ret3_top:
            if row["stock"] in alignment:
                alignment[row["stock"]]["filtered_reason"] = "not_in_auc_top_or_ret3_top"
            continue
        tpl = close_to_high_template(
            row["close_to_high"], row["ret3"], row["open_ratio"], row["auction_ratio"]
        )
        row["tpl"] = tpl
        row["dragon_score"] = calc_dragon_score(row)
        if row["stock"] in alignment:
            alignment[row["stock"]]["dragon_candidate"] = True
            alignment[row["stock"]]["tpl"] = tpl
            alignment[row["stock"]]["dragon_score"] = row["dragon_score"]
            alignment[row["stock"]]["filtered_reason"] = "dragon_candidate_not_top12"
        rows.append(row)

    rows.sort(key=lambda r: r["dragon_score"], reverse=True)
    top_rows = rows[:TOP_N_PER_DAY]
    for rank, row in enumerate(top_rows, 1):
        row["rank"] = rank
        if row["stock"] in alignment:
            alignment[row["stock"]]["top12"] = True
            alignment[row["stock"]]["rank"] = rank
            alignment[row["stock"]]["filtered_reason"] = "top12"
    return top_rows, list(alignment.values())


def build_normal_template_candidates_for_day(date, prev_date, future_dates, daily_df, regime):
    """Daily-data approximation for firstboard/lowopen/weak_to_strong."""
    rows = []
    for stock, df in daily_df.groupby("code"):
        df = df.sort_values("time")
        past = df[df["time"] <= prev_date].tail(101)
        today = df[df["time"] == date]
        future = df[df["time"].isin(future_dates)].sort_values("time")
        if len(past) < 4 or today.empty or len(future) < 1:
            continue
        y = past.iloc[-1]
        t = today.iloc[0]
        y_close = _safe_float(y["close"])
        y_high_limit = _safe_float(y.get("high_limit", np.nan))
        y_money = _safe_float(y["money"], 0.0)
        if y_close <= 0:
            continue
        open_price = _safe_float(t["open"])
        open_ratio = open_price / y_close - 1
        was_limit_up = pd.notnull(y_high_limit) and abs(y_close / y_high_limit - 1) < 0.001

        rp_60d = np.nan
        if len(past) >= 60:
            close60 = past["close"].tail(60)
            hi = close60.max()
            lo = close60.min()
            rp_60d = (y_close - lo) / (hi - lo) if hi > lo else 0.5

        if was_limit_up and y_money >= CFG["lowopen_min_money"]:
            gap = open_price / y_close
            if CFG["lowopen_gap_min"] <= gap <= CFG["lowopen_gap_max"] and (pd.isnull(rp_60d) or rp_60d <= 0.6):
                rows.append({
                    "date": date, "stock": stock, "entry_type": "firstboard_lowopen",
                    "tpl": "firstboard_lowopen", "dragon_score": np.nan,
                    "open_price": open_price, "open_ratio": open_ratio,
                    "regime": regime, "data_mode": "daily_open_proxy",
                })
            if open_ratio > 0:
                rows.append({
                    "date": date, "stock": stock, "entry_type": "firstboard",
                    "tpl": "firstboard", "dragon_score": np.nan,
                    "open_price": open_price, "open_ratio": open_ratio,
                    "regime": regime, "data_mode": "daily_open_proxy",
                })

        if len(past) >= 20:
            recent_high = past["high"].tail(20).iloc[:-1].max()
            if open_ratio > 0 and y_close >= recent_high * 0.98 and not was_limit_up:
                rows.append({
                    "date": date, "stock": stock, "entry_type": "weak_to_strong",
                    "tpl": "weak_to_strong", "dragon_score": np.nan,
                    "open_price": open_price, "open_ratio": open_ratio,
                    "regime": regime, "data_mode": "daily_open_proxy",
                })
    return rows


def add_forward_returns(rows, daily_df, date, future_dates):
    by_code = {code: df.sort_values("time") for code, df in daily_df.groupby("code")}
    out = []
    for row in rows:
        stock = row["stock"]
        df = by_code.get(stock)
        if df is None:
            continue
        fut = df[df["time"].isin(future_dates)].sort_values("time")
        if fut.empty:
            continue
        entry = row["open_price"]
        if pd.isnull(entry) or entry <= 0:
            continue
        f1 = fut.iloc[0]
        f2 = fut.iloc[min(1, len(fut) - 1)]
        f3 = fut.iloc[min(2, len(fut) - 1)]
        highs = fut.head(3)["high"]
        lows = fut.head(3)["low"]
        row = dict(row)
        row["next_open_ret"] = _safe_float(f1["open"]) / entry - 1
        row["next_close_ret"] = _safe_float(f1["close"]) / entry - 1
        row["ret_2d"] = _safe_float(f2["close"]) / entry - 1 if len(fut) >= 2 else np.nan
        row["ret_3d"] = _safe_float(f3["close"]) / entry - 1 if len(fut) >= 3 else np.nan
        row["mae_3d"] = lows.min() / entry - 1 if len(lows) else np.nan
        row["mfe_3d"] = highs.max() / entry - 1 if len(highs) else np.nan
        out.append(row)
    return out


# =========================
# Summaries and sweep
# =========================

def summarize_group(df):
    keys = ["tpl", "entry_type"]
    rows = []
    for key, g in df.groupby(keys):
        row = {
            "tpl": key[0],
            "entry_type": key[1],
            "n": len(g),
            "avg_next_open_ret": g["next_open_ret"].mean(),
            "avg_next_close_ret": g["next_close_ret"].mean(),
            "avg_ret_2d": g["ret_2d"].mean(),
            "avg_ret_3d": g["ret_3d"].mean(),
            "win_rate_1d_close": (g["next_close_ret"] > 0).mean(),
            "win_rate_3d": (g["ret_3d"] > 0).mean(),
            "avg_mae_3d": g["mae_3d"].mean(),
            "avg_mfe_3d": g["mfe_3d"].mean(),
            "median_score": g["dragon_score"].median(),
            "avg_open_ratio": g["open_ratio"].mean(),
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["avg_ret_3d", "n"], ascending=[False, False])


def run_param_sweep(df):
    rows = []
    if df.empty:
        return pd.DataFrame()

    dragon_scores = df["dragon_score"]
    for deep_only, open_max, q, trend_core_enabled, regime_filter in itertools.product(
            SWEEP["deep_water_only"],
            SWEEP["open_ratio_max"],
            SWEEP["score_quantile"],
            SWEEP["trend_core_enabled"],
            SWEEP["regime_filter_enabled"]):
        x = df.copy()
        x = x[x["entry_type"].isin(["dragon_follow"])]
        if deep_only:
            x = x[x["tpl"] == "deep_water"]
        if not trend_core_enabled:
            x = x[x["tpl"] != "trend_core"]
        x = x[x["open_ratio"] <= open_max]
        if q > 0 and x["dragon_score"].notnull().any():
            threshold = x["dragon_score"].quantile(q)
            x = x[x["dragon_score"] >= threshold]
        else:
            threshold = np.nan
        if regime_filter:
            x = x[x["regime"].isin(["bull", "neutral"])]

        rows.append({
            "deep_water_only": deep_only,
            "open_ratio_max": open_max,
            "score_quantile": q,
            "score_threshold": threshold,
            "trend_core_enabled": trend_core_enabled,
            "regime_filter_enabled": regime_filter,
            "n": len(x),
            "avg_next_close_ret": x["next_close_ret"].mean() if len(x) else np.nan,
            "avg_ret_2d": x["ret_2d"].mean() if len(x) else np.nan,
            "avg_ret_3d": x["ret_3d"].mean() if len(x) else np.nan,
            "win_rate_3d": (x["ret_3d"] > 0).mean() if len(x) else np.nan,
            "avg_mae_3d": x["mae_3d"].mean() if len(x) else np.nan,
            "avg_mfe_3d": x["mfe_3d"].mean() if len(x) else np.nan,
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["avg_ret_3d", "n"], ascending=[False, False])
    return out


def run_research():
    _ensure_dir(OUTPUT_DIR)
    trade_days = list(get_trade_days(start_date=START_DATE, end_date=END_DATE))
    trade_days = [_to_date_str(x) for x in trade_days]
    if not trade_days:
        raise ValueError("No trade days in range {} to {}".format(START_DATE, END_DATE))

    all_candidate_rows = []
    dragon_alignment_rows = []
    print("Research range: {} -> {}, {} trade days".format(START_DATE, END_DATE, len(trade_days)))
    for idx, date in enumerate(trade_days):
        if idx == 0:
            prev_days = get_trade_days(end_date=date, count=2)
            if len(prev_days) < 2:
                continue
            prev_date = _to_date_str(prev_days[-2])
        else:
            prev_date = trade_days[idx - 1]
        future = [_to_date_str(x) for x in get_trade_days(start_date=date, count=4)]
        future_dates = [x for x in future if x > date][:3]
        if len(future_dates) < 1:
            continue

        hist_start = _to_date_str(get_trade_days(end_date=prev_date, count=110)[0])
        hist_end = future_dates[-1]
        universe = get_research_universe(prev_date)
        daily_df = get_price_panel(universe, hist_start, hist_end)
        if daily_df.empty:
            print("{} no daily data".format(date))
            continue
        regime = get_market_regime(prev_date)

        alignment_stocks = _alignment_targets_for_date(date)
        dragon_rows, align_rows = build_dragon_candidates_for_day(
            date, prev_date, future_dates, daily_df, regime,
            universe=universe, alignment_stocks=alignment_stocks)
        for row in align_rows:
            if not row.get("universe", False):
                row["filtered_reason"] = explain_universe_exclusion(row["stock"], prev_date)
            row["row_type"] = "manual_check"
            dragon_alignment_rows.append(row)
        for rank, row in enumerate(dragon_rows, 1):
            dragon_alignment_rows.append({
                "date": date,
                "stock": row["stock"],
                "rank": rank,
                "tpl": row.get("tpl", ""),
                "dragon_score": row.get("dragon_score", np.nan),
                "open_ratio": row.get("open_ratio", np.nan),
                "close_to_high": row.get("close_to_high", np.nan),
                "auc_ratio": row.get("auction_ratio", np.nan),
                "prev_money": row.get("prev_money", row.get("y_money", np.nan)),
                "ret3": row.get("ret3", np.nan),
                "data_mode": row.get("data_mode", ""),
                "universe": True,
                "prefilter": True,
                "dragon_candidate": True,
                "top12": True,
                "filtered_reason": "top12",
                "row_type": "top12",
            })
        normal_rows = build_normal_template_candidates_for_day(date, prev_date, future_dates, daily_df, regime)
        rows = add_forward_returns(dragon_rows + normal_rows, daily_df, date, future_dates)
        all_candidate_rows.extend(rows)
        if dragon_rows:
            tpl_counts = pd.Series([x.get("tpl", "UNKNOWN") for x in dragon_rows]).value_counts().to_dict()
            top_detail = " | ".join([
                "{}:{} tpl={} s={:.3f} or={:.2%} c2h={:.3f}".format(
                    x.get("rank", i + 1), x["stock"], x.get("tpl", ""),
                    x.get("dragon_score", 0.0), x.get("open_ratio", 0.0),
                    x.get("close_to_high", np.nan))
                for i, x in enumerate(dragon_rows)
            ])
        else:
            tpl_counts = {}
            top_detail = ""
        print("{} candidates={} dragon={} normal={} regime={} dragon_tpl={}".format(
            date, len(rows), len(dragon_rows), len(normal_rows), regime, tpl_counts))
        print("{} Dragon Top{}: {}".format(date, TOP_N_PER_DAY, top_detail))
        if align_rows:
            for row in align_rows:
                print("{} CHECK {} universe={} prefilter={} candidate={} top12={} tpl={} reason={}".format(
                    date, row["stock"], row["universe"], row["prefilter"],
                    row["dragon_candidate"], row["top12"], row["tpl"], row["filtered_reason"]))

    cand = pd.DataFrame(all_candidate_rows)
    if cand.empty:
        raise ValueError("No candidates generated. Check date range/API availability.")

    percent_cols = [
        "open_ratio", "next_open_ret", "next_close_ret", "ret_2d", "ret_3d",
        "mae_3d", "mfe_3d", "auction_ratio", "ret1", "ret3", "close_to_high", "avg_range",
    ]
    for col in percent_cols:
        if col in cand.columns:
            cand[col + "_pct"] = cand[col].apply(_pct)

    group_summary = summarize_group(cand)
    sweep = run_param_sweep(cand)
    print("Group summary:")
    print(group_summary.to_string(index=False))

    cand_path = os.path.join(OUTPUT_DIR, "research_candidates.csv")
    group_path = os.path.join(OUTPUT_DIR, "research_group_summary.csv")
    sweep_path = os.path.join(OUTPUT_DIR, "research_param_sweep.csv")
    align_path = os.path.join(OUTPUT_DIR, "research_dragon_alignment.csv")
    cand.to_csv(cand_path, index=False, encoding="utf-8-sig")
    group_summary.to_csv(group_path, index=False, encoding="utf-8-sig")
    sweep.to_csv(sweep_path, index=False, encoding="utf-8-sig")
    if dragon_alignment_rows:
        align_df = pd.DataFrame(dragon_alignment_rows)
        align_df.to_csv(align_path, index=False, encoding="utf-8-sig")
    else:
        align_df = pd.DataFrame()
        align_df.to_csv(align_path, index=False, encoding="utf-8-sig")
    print("Wrote:", cand_path, group_path, sweep_path, align_path)
    return cand, group_summary, sweep


if __name__ == "__main__":
    run_research()
