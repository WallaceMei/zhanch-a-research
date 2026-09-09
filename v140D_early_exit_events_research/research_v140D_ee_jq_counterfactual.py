# -*- coding: utf-8 -*-
#
# research_v140D_ee_jq_counterfactual.py
#
# v140D Early-Exit Events multi-direction counterfactual study (research-only).
# Runs in the JoinQuant research notebook (jqdata available).
#
# This is the MAIN script. It is built up across stages S4..S7. The current
# file implements through S4 (event load + forward price fetch + 5 protection
# variants -> cases). S5/S6/S7 sections (by_subclass, mergeability, sensitivity,
# report, zip) are added in later stages.
#
# LOCKED CONFIG (user decision after S3, 2026-06-21):
#   - ee_ledger_early main profit gate = >=3%.
#   - dedup rule: the 7 overlapping events go to ee_promotion_block and are
#     REMOVED from ee_ledger_early. The three subclasses are mutually exclusive.
#   => promotion 7 + failed 12 + ledger_early 6 = 25 distinct events.
#
# HARD CONSTRAINTS (do not relax):
#   - Research-only. NO order / order_value / order_target / order_target_value
#     / run_backtest / schedule_function anywhere.
#   - get_price MUST NOT pass start_date and count together.
#   - All output paths RELATIVE. No absolute "D:\\" paths.
#   - Python 3.6 compatible. Code region pure ASCII.
#   - The 5 protection variant scorers are copied VERBATIM from the accepted
#     script research_v140D_jq_promotion_protection_counterfactual.py. Do not
#     rewrite, add, or remove variants.
#   - Anti-look-ahead: forward evaluation uses ONLY T+1..T+10 closes/highs;
#     MA5 at the exit day uses the exit day plus the 4 PRIOR trade days (history,
#     not future). No survivorship screening is performed: events are a fixed
#     list of already-held real positions, not a universe selection.

import os
import csv
import zipfile

import numpy as np
import pandas as pd

try:
    from jqdata import *  # noqa: F401,F403
    _HAS_JQDATA = True
except Exception:
    _HAS_JQDATA = False


# ---------------------------------------------------------------------------
# 0. Output config (relative paths only). Spec 3.7 file names.
# ---------------------------------------------------------------------------

OUT_DIR = "ee_outputs"
OUT_UNIVERSE = "jq_ee_event_universe.csv"
OUT_CASES = "jq_ee_cases.csv"
OUT_BY_SUBCLASS = "jq_ee_by_subclass_summary.csv"
OUT_MERGEABILITY = "jq_ee_mergeability.csv"
OUT_SENSITIVITY = "jq_ee_sensitivity.csv"
OUT_REPORT = "jq_ee_report.md"
OUT_ZIP = "v140D_ee_outputs.zip"


def _ensure_out_dir():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)


# ---------------------------------------------------------------------------
# 1. Real ledger (37 trades), transcribed from
#    v140D_smoke_test_audit/04_entry_exit/entry_exit_matched.csv.
#    Fields: name, stock, entry_date, exit_date, exit_reason,
#    pnl_pct (PERCENT units), pnl_val (RMB), hold_days.
#    Romanized names match the accepted counterfactual script.
# ---------------------------------------------------------------------------

LEDGER = [
    ("xinjinlu_1", "000510.XSHE", "2026-01-05", "2026-01-28", "dragon_half_protect", 54.64, 19138.0, 23),
    ("zhenghe", "605069.XSHG", "2026-01-05", "2026-01-12", "dragon_fail_fast", -1.63, -400.0, 7),
    ("shenkai", "002278.XSHE", "2026-01-13", "2026-01-15", "dragon_confirm_stop", -5.90, -1305.0, 2),
    ("shiyun", "603920.XSHG", "2026-01-20", "2026-01-22", "dragon_fail_fast", -2.15, -387.0, 2),
    ("shengda", "000603.XSHE", "2026-01-21", "2026-01-22", "gap_down_stop", -3.60, -495.0, 1),
    ("hengtong", "600487.XSHG", "2026-01-26", "2026-01-28", "shadow_no_promotion_take_profit", 7.63, 1190.0, 2),
    ("litong", "603629.XSHG", "2026-01-30", "2026-02-13", "dragon_half_protect", 39.89, 22804.0, 14),
    ("jinchen", "603396.XSHG", "2026-02-02", "2026-02-03", "dragon_delayed_stop", -3.63, -1080.0, 1),
    ("saiwu", "603212.XSHG", "2026-02-03", "2026-02-04", "shadow_no_promotion_take_profit", 4.68, 820.0, 1),
    ("tianrun", "002283.XSHE", "2026-02-05", "2026-03-03", "dragon_half_protect", 21.49, 10793.0, 26),
    ("zhende", "603301.XSHG", "2026-02-13", "2026-02-24", "dragon_confirm_stop", -5.25, -1416.0, 11),
    ("zhangyuan", "002378.XSHE", "2026-02-25", "2026-03-05", "dragon_half_protect", 19.17, 8778.0, 8),
    ("xinjinlu_2", "000510.XSHE", "2026-02-25", "2026-02-27", "shadow_no_promotion_take_profit", 9.14, 1881.0, 2),
    ("xiamen_w", "600549.XSHG", "2026-03-05", "2026-03-06", "dragon_confirm_stop", -5.24, -2055.0, 1),
    ("jinkai", "600821.XSHG", "2026-03-06", "2026-03-17", "dragon_half_protect", 11.62, 7348.0, 11),
    ("meiliyun", "000815.XSHE", "2026-03-11", "2026-03-13", "dragon_confirm_stop", -5.40, -2156.0, 2),
    ("xizang_ct", "600773.XSHG", "2026-03-11", "2026-03-13", "shadow_no_promotion_take_profit", 5.57, 672.0, 2),
    ("changfei", "601869.XSHG", "2026-03-18", "2026-03-19", "dragon_fail_fast", -1.96, -858.0, 1),
    ("huasheng", "002980.XSHE", "2026-03-18", "2026-03-19", "dragon_confirm_stop", -6.28, -2450.0, 1),
    ("wanbangde", "002082.XSHE", "2026-03-31", "2026-04-09", "dragon_half_protect", 16.72, 9230.0, 9),
    ("zaisheng", "603601.XSHG", "2026-04-02", "2026-04-03", "dragon_confirm_stop", -5.45, -1968.0, 1),
    ("zhaoshang", "601872.XSHG", "2026-04-07", "2026-04-09", "dragon_confirm_stop", -6.19, -2000.0, 2),
    ("hesheng", "002824.XSHE", "2026-04-14", "2026-04-24", "dragon_fail_fast_confirmed", -0.37, -210.0, 10),
    ("xizang_ky", "000762.XSHE", "2026-04-14", "2026-05-13", "dragon_fail_fast_confirmed", -0.92, -588.0, 29),
    ("yujing_1", "002943.XSHE", "2026-04-16", "2026-04-22", "shadow_below_ma5_loss", -1.43, -328.0, 6),
    ("jiangte", "002176.XSHE", "2026-04-22", "2026-04-24", "shadow_no_promotion_take_profit", 9.75, 2299.0, 2),
    ("rendong", "002647.XSHE", "2026-04-27", "2026-05-15", "dragon_fail_fast", -2.95, -1637.0, 18),
    ("fujing", "002222.XSHE", "2026-05-06", "2026-05-07", "shadow_no_promotion_take_profit", 5.81, 1078.0, 1),
    ("tongda", "002560.XSHE", "2026-05-07", "2026-05-11", "minute_stop_loss", -5.06, -1296.0, 4),
    ("hongchang", "603002.XSHG", "2026-05-13", "2026-05-15", "minute_stop_loss", -6.98, -1695.0, 2),
    ("yujing_2", "002943.XSHE", "2026-05-18", "2026-05-25", "dragon_fail_fast_confirmed", -0.20, -112.0, 7),
    ("jingquanhua", "002885.XSHE", "2026-05-18", "2026-05-19", "dragon_fail_fast", -3.05, -1104.0, 1),
    ("tongding", "002491.XSHE", "2026-05-22", "2026-05-26", "dragon_fail_fast", -2.09, -799.0, 4),
    ("shenkeji", "000021.XSHE", "2026-05-25", "2026-05-27", "shadow_no_promotion_take_profit", 9.60, 1975.0, 2),
    ("mulinsen", "002745.XSHE", "2026-05-27", "2026-05-29", "dragon_fail_fast", -3.17, -1768.0, 2),
    ("xinjieneng", "605111.XSHG", "2026-05-28", "2026-05-29", "dragon_fail_fast", -3.07, -1045.0, 1),
    ("shengquan", "605589.XSHG", "2026-05-28", "2026-05-29", "minute_stop_loss", -5.27, -1032.0, 1),
]

LEDGER_COLS = ("name", "stock", "entry_date", "exit_date", "exit_reason",
               "pnl_pct", "pnl_val", "hold_days")

PROMOTION_NAMES = [
    "hengtong", "saiwu", "xinjinlu_2", "xizang_ct",
    "jiangte", "fujing", "shenkeji",
]

FAILED_NAMES = [
    "hesheng", "xizang_ky", "yujing_1", "rendong", "tongda", "hongchang",
    "yujing_2", "jingquanhua", "tongding", "mulinsen", "xinjieneng", "shengquan",
]

# Locked S3 decision.
LEDGER_EARLY_GATE_PCT = 3.0      # main gate = >=3%
DEDUP_OVERLAP_TO_PROMOTION = True

OOS_START = "2026-04-16"


def _row_dict(row):
    return dict(zip(LEDGER_COLS, row))


def _phase_for(entry_date):
    return "oos" if entry_date >= OOS_START else "pre_oos"


def build_events():
    """Return the 25 locked events as dicts (no prices yet)."""
    by_name = {r[0]: _row_dict(r) for r in LEDGER}
    promo_set = set(PROMOTION_NAMES)
    events = []

    def mk(d, subclass):
        return {
            "subclass": subclass,
            "name": d["name"],
            "stock": d["stock"],
            "entry_date": d["entry_date"],
            "exit_date": d["exit_date"],
            "exit_reason": d["exit_reason"],
            "exit_pnl_pct": d["pnl_pct"],
            "pnl_val": d["pnl_val"],
            "hold_days": d["hold_days"],
            "phase": _phase_for(d["entry_date"]),
        }

    for nm in PROMOTION_NAMES:
        events.append(mk(by_name[nm], "ee_promotion_block"))
    for nm in FAILED_NAMES:
        d = by_name[nm]
        assert d["pnl_pct"] <= 0.0, "failed trade unexpectedly profitable: " + nm
        events.append(mk(d, "ee_failed_trade"))
    for r in LEDGER:
        d = _row_dict(r)
        if d["pnl_pct"] < LEDGER_EARLY_GATE_PCT:
            continue
        if DEDUP_OVERLAP_TO_PROMOTION and d["name"] in promo_set:
            continue
        events.append(mk(d, "ee_ledger_early"))

    return events


# ---------------------------------------------------------------------------
# 2. Protection variants (spec-locked, 5 ids). Copied verbatim from accepted
#    script. NONE place orders. captured_extra_return is a fraction of the
#    anchor price (= exit-day close). proxy_distortion_flag: trail=high (daily
#    high misses intraday peaks), all MA5/close variants=low.
# ---------------------------------------------------------------------------

PV_VARIANTS = [
    "pv_immediate_full_exit",
    "pv_half_exit_hold_half",
    "pv_delay_1d_confirm",
    "pv_trail_from_high",
    "pv_downgrade_small_pos",
]

PROXY_FLAG = {
    "pv_immediate_full_exit": "low",
    "pv_half_exit_hold_half": "low",
    "pv_delay_1d_confirm": "low",
    "pv_trail_from_high": "high",
    "pv_downgrade_small_pos": "low",
}

DEFAULT_TRAIL_PCT = 0.05
DEFAULT_DOWNGRADE_FRAC = 1.0 / 3.0

HOLD_LIMIT_DAYS = 5
MA5_DAYS = 5

GRID_TRAIL_PCT = [0.03, 0.05, 0.08]
GRID_DOWNGRADE_FRAC = [1.0 / 3.0, 0.5]

FORWARD_DAYS = 10
END_DATE_CAP = "2026-06-21"


# ---------------------------------------------------------------------------
# 3. Price-path fetch. JoinQuant rule: get_price MUST NOT receive start_date
#    and count together. Resolve [start_date, end_date] via get_trade_days
#    (count is legal there), then call get_price with the window only.
# ---------------------------------------------------------------------------

def _price_window(exit_date_str):
    """(start_str, end_str): 4 trade days BEFORE the exit day (so MA5 is
    computable at the exit day) through FORWARD_DAYS after it."""
    if not _HAS_JQDATA:
        return None, None
    pre = get_trade_days(end_date=exit_date_str, count=MA5_DAYS)
    fwd = get_trade_days(start_date=exit_date_str, count=FORWARD_DAYS + 1)
    if pre is None or len(pre) == 0 or fwd is None or len(fwd) == 0:
        return None, None
    start_str = str(pre[0])
    end_str = str(fwd[-1])
    if end_str > END_DATE_CAP:
        end_str = END_DATE_CAP
    return start_str, end_str


def _aligned_from_exit(prices_df, exit_date_str):
    """Forward-aligned close/high/ma5 with index 0 = exit day. MA5 is a true
    rolling 5-close mean (close-proxy-safe). None if exit day absent."""
    if prices_df is None or len(prices_df) == 0:
        return None
    closes_all = np.asarray(prices_df["close"].values, dtype=float)
    highs_all = np.asarray(prices_df["high"].values, dtype=float)
    ma5_all = pd.Series(closes_all).rolling(window=5).mean().values
    exit_idx = None
    for i, d in enumerate(prices_df.index):
        if str(d)[:10] == exit_date_str:
            exit_idx = i
            break
    if exit_idx is None:
        return None
    return {
        "close": closes_all[exit_idx:],
        "high": highs_all[exit_idx:],
        "ma5": ma5_all[exit_idx:],
    }


def fetch_aligned(stock, exit_date_str):
    if not _HAS_JQDATA:
        return None
    start_str, end_str = _price_window(exit_date_str)
    if start_str is None:
        return None
    # IMPORTANT: no count= here. start_date + end_date only.
    prices_df = get_price(
        stock,
        start_date=start_str,
        end_date=end_str,
        frequency="daily",
        fields=["close", "high", "low"],
        skip_paused=False,
    )
    return _aligned_from_exit(prices_df, exit_date_str)


# ---------------------------------------------------------------------------
# 4. Variant scorers -- VERBATIM from the accepted script. Each returns
#    captured_extra_return as a fraction of the anchor price (block_price arg).
# ---------------------------------------------------------------------------

def _ma5_exit_close(al, block_price, start_i):
    fc = al["close"]
    fm = al["ma5"]
    n = fc.size
    last_i = min(HOLD_LIMIT_DAYS, n - 1)
    if last_i < start_i:
        return block_price
    for i in range(start_i, last_i + 1):
        if (not np.isnan(fm[i])) and fc[i] < fm[i]:
            return float(fc[i])
    return float(fc[last_i])


def score_half_exit_hold_half(al, block_price):
    if al is None or al["close"].size < 2:
        return 0.0
    exit_px = _ma5_exit_close(al, block_price, 1)
    half_return = (exit_px - block_price) / block_price
    return 0.5 * half_return


def score_delay_1d_confirm(al, block_price):
    if al is None or al["close"].size < 2:
        return 0.0
    fc = al["close"]
    fm = al["ma5"]
    below_ma5 = (not np.isnan(fm[1])) and fc[1] < fm[1]
    negative = fc[1] < block_price
    if below_ma5 or negative:
        return (float(fc[1]) - block_price) / block_price
    exit_px = _ma5_exit_close(al, block_price, 2)
    return (exit_px - block_price) / block_price


def score_trail_from_high(al, block_price, trail_pct):
    if al is None or al["close"].size < 2:
        return 0.0
    fc = al["close"]
    fh = al["high"]
    n = fc.size
    running_high = block_price
    exit_px = float(fc[-1])
    for i in range(1, n):
        if fh[i] > running_high:
            running_high = fh[i]
        stop_level = running_high * (1.0 - trail_pct)
        if fc[i] <= stop_level:
            exit_px = float(fc[i])
            break
    return (exit_px - block_price) / block_price


def score_downgrade_small_pos(al, block_price, keep_frac):
    if al is None or al["close"].size < 2:
        return 0.0
    exit_px = _ma5_exit_close(al, block_price, 1)
    slice_return = (exit_px - block_price) / block_price
    return keep_frac * slice_return


def score_variant(variant, al, block_price, knobs):
    if variant == "pv_immediate_full_exit":
        return 0.0
    if variant == "pv_half_exit_hold_half":
        return score_half_exit_hold_half(al, block_price)
    if variant == "pv_delay_1d_confirm":
        return score_delay_1d_confirm(al, block_price)
    if variant == "pv_trail_from_high":
        return score_trail_from_high(al, block_price, knobs["trail_pct"])
    if variant == "pv_downgrade_small_pos":
        return score_downgrade_small_pos(al, block_price, knobs["keep_frac"])
    return 0.0


def default_knobs():
    return {"trail_pct": DEFAULT_TRAIL_PCT, "keep_frac": DEFAULT_DOWNGRADE_FRAC}


# ---------------------------------------------------------------------------
# 5. S4 driver: fetch each event's forward path, score the 5 variants, build
#    cases. Also fills data_quality_flag for the event universe.
# ---------------------------------------------------------------------------

def _quality_flag(al):
    """Forward-path quality. 'ok' if >=FORWARD_DAYS forward days available;
    'insufficient_forward_days' if the path is shorter (e.g. near sample end /
    capped at END_DATE_CAP); 'no_data' if the exit day / frame is missing."""
    if al is None:
        return "no_data"
    # al['close'][0] is the exit day; need FORWARD_DAYS more after it.
    if al["close"].size < FORWARD_DAYS + 1:
        return "insufficient_forward_days"
    return "ok"


def fetch_all(events):
    paths = {}
    for ev in events:
        paths[ev["name"]] = fetch_aligned(ev["stock"], ev["exit_date"])
    return paths


def build_cases(events, paths, knobs):
    """Long format: one row per (event, variant) with captured_extra_return.
    Carries subclass for the S5/S6 stages."""
    rows = []
    for ev in events:
        al = paths.get(ev["name"])
        proxy_mode = (al is None)
        anchor_price = float(al["close"][0]) if (al is not None and al["close"].size >= 1) else float("nan")
        qflag = _quality_flag(al)
        for variant in PV_VARIANTS:
            extra = score_variant(variant, al, anchor_price, knobs) if (al is not None) else 0.0
            rows.append({
                "subclass": ev["subclass"],
                "name": ev["name"],
                "stock": ev["stock"],
                "exit_date": ev["exit_date"],
                "exit_reason": ev["exit_reason"],
                "exit_pnl_pct": ev["exit_pnl_pct"],
                "phase": ev["phase"],
                "variant": variant,
                "anchor_price": anchor_price,
                "captured_extra_return": extra,
                "proxy_distortion_flag": PROXY_FLAG[variant],
                "data_quality_flag": qflag,
                "proxy_mode": proxy_mode,
            })
    return pd.DataFrame(rows)


def build_universe(events, paths):
    rows = []
    for ev in events:
        al = paths.get(ev["name"])
        rows.append({
            "subclass": ev["subclass"],
            "stock": ev["stock"],
            "name": ev["name"],
            "entry_date": ev["entry_date"],
            "exit_date": ev["exit_date"],
            "exit_reason": ev["exit_reason"],
            "exit_pnl_pct": ev["exit_pnl_pct"],
            "pnl_val": ev["pnl_val"],
            "hold_days": ev["hold_days"],
            "phase": ev["phase"],
            "data_quality_flag": _quality_flag(al),
        })
    cols = ["subclass", "stock", "name", "entry_date", "exit_date",
            "exit_reason", "exit_pnl_pct", "pnl_val", "hold_days", "phase",
            "data_quality_flag"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 5b. S5 -- LAYER ONE: per-subclass independent distribution + concentration.
#     For each (subclass, variant): n, hit_rate (captured_extra>0 share),
#     mean, median, and profit concentration (top-10%-of-events contribution
#     share, and whether the sum stays positive after removing that top 10%).
#     Subclasses are NOT mixed here (mixing/mergeability is S6). Events flagged
#     no_data / insufficient_forward_days are excluded from the main
#     distribution (spec 3.2/3.4) and counted in n_excluded.
# ---------------------------------------------------------------------------

import math


def _concentration(values):
    """Profit-concentration of a captured_extra vector across EVENTS.
    top-10% = ceil(0.10 * n) events by captured_extra (at least 1).
    Returns total, top-k share of total, sum after removing the top-k, and
    whether that residual sum stays positive (outlier-driven check)."""
    arr = sorted((float(v) for v in values), reverse=True)
    n = len(arr)
    if n == 0:
        return {"k": 0, "total": 0.0, "topk_sum": 0.0,
                "topk_share_of_total": float("nan"),
                "sum_excl_topk": 0.0, "positive_after_excl_topk": False}
    k = max(1, int(math.ceil(0.10 * n)))
    total = float(sum(arr))
    topk_sum = float(sum(arr[:k]))
    sum_excl = total - topk_sum
    share = (topk_sum / total) if total != 0 else float("nan")
    return {"k": k, "total": total, "topk_sum": topk_sum,
            "topk_share_of_total": share, "sum_excl_topk": sum_excl,
            "positive_after_excl_topk": bool(sum_excl > 0)}


def build_by_subclass_summary(cases_df):
    """One row per (subclass, variant) over the MAIN distribution
    (data_quality_flag == 'ok'). Spec output: by_subclass summary."""
    subclasses = ["ee_promotion_block", "ee_failed_trade", "ee_ledger_early"]
    rows = []
    for sub in subclasses:
        sub_all = cases_df[cases_df["subclass"] == sub]
        for variant in PV_VARIANTS:
            v_all = sub_all[sub_all["variant"] == variant]
            v_ok = v_all[v_all["data_quality_flag"] == "ok"]
            vals = [float(x) for x in v_ok["captured_extra_return"].values]
            n = len(vals)
            n_excluded = len(v_all) - n
            if n > 0:
                hit = float(sum(1 for x in vals if x > 0)) / n
                mean = float(np.mean(vals))
                median = float(np.median(vals))
            else:
                hit = float("nan")
                mean = float("nan")
                median = float("nan")
            c = _concentration(vals)
            rows.append({
                "subclass": sub,
                "variant": variant,
                "n": n,
                "n_excluded": n_excluded,
                "hit_rate": hit,
                "mean_captured_extra": mean,
                "median_captured_extra": median,
                "total_captured_extra": c["total"],
                "top10pct_k_events": c["k"],
                "top10pct_share_of_total": c["topk_share_of_total"],
                "sum_excl_top10pct": c["sum_excl_topk"],
                "positive_after_excl_top10pct": c["positive_after_excl_topk"],
                "proxy_distortion_flag": PROXY_FLAG[variant],
            })
    cols = ["subclass", "variant", "n", "n_excluded", "hit_rate",
            "mean_captured_extra", "median_captured_extra",
            "total_captured_extra", "top10pct_k_events",
            "top10pct_share_of_total", "sum_excl_top10pct",
            "positive_after_excl_top10pct", "proxy_distortion_flag"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 5c. S6 -- LAYER TWO: mergeability check. Do NOT pool the three subclasses
#     blindly. First test whether they are the same population: compare the
#     exit_pnl_pct distributions AND the captured_extra distributions across
#     subclasses (descriptive stats + simple sign/spread comparison). The
#     pooled distribution is computed for INSPECTION ONLY and is NOT an
#     endorsement of merging -- the merge decision is the user's (spec 3.5).
# ---------------------------------------------------------------------------

SUBCLASSES = ["ee_promotion_block", "ee_failed_trade", "ee_ledger_early"]
# Tradeable evidence variants = low proxy-distortion, excluding the zero
# baseline. trail (high distortion) is ranking-only, never core evidence.
LOW_NONBASE_VARIANTS = [v for v in PV_VARIANTS
                        if PROXY_FLAG[v] == "low" and v != "pv_immediate_full_exit"]


def _desc(values):
    if not values:
        return {"n": 0, "mean": float("nan"), "median": float("nan"),
                "std": float("nan"), "p25": float("nan"), "p75": float("nan"),
                "pos_share": float("nan")}
    arr = np.asarray(values, dtype=float)
    return {
        "n": len(values),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=0)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "pos_share": float(np.mean(arr > 0)),
    }


def _ok_captured(cases_df, subclass, variant):
    m = cases_df[(cases_df["subclass"] == subclass)
                 & (cases_df["variant"] == variant)
                 & (cases_df["data_quality_flag"] == "ok")]
    return [float(x) for x in m["captured_extra_return"].values]


def _ok_exit_pnl(cases_df, subclass):
    # exit_pnl_pct is per-event; take it from one variant slice (immediate),
    # restricted to ok rows so it matches the main distribution.
    m = cases_df[(cases_df["subclass"] == subclass)
                 & (cases_df["variant"] == "pv_immediate_full_exit")
                 & (cases_df["data_quality_flag"] == "ok")]
    return [float(x) for x in m["exit_pnl_pct"].values]


def _sign(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def build_mergeability(cases_df):
    """Spec output: mergeability. Rows:
      row_type=per_subclass  : descriptive stats of a metric per subclass
      row_type=cross_subclass: sign-agreement + spread across the 3 subclasses
      row_type=pooled        : pooled-if-merged captured_extra (inspection only)
    """
    rows = []

    def emit_desc(row_type, metric, variant, subclass, d, extra=None):
        r = {
            "row_type": row_type,
            "metric": metric,
            "variant": variant,
            "subclass": subclass,
            "n": d["n"],
            "mean": d["mean"],
            "median": d["median"],
            "std": d["std"],
            "p25": d["p25"],
            "p75": d["p75"],
            "pos_share": d["pos_share"],
            "same_sign_mean": "",
            "same_sign_median": "",
            "mean_spread": "",
            "mergeable_hint": "",
        }
        if extra:
            r.update(extra)
        rows.append(r)

    # (A) exit_pnl_pct per subclass (population identity).
    for sub in SUBCLASSES:
        emit_desc("per_subclass", "exit_pnl_pct", "", sub,
                  _desc(_ok_exit_pnl(cases_df, sub)))
    # exit_pnl_pct cross-subclass consistency.
    means = [_desc(_ok_exit_pnl(cases_df, s))["mean"] for s in SUBCLASSES]
    meds = [_desc(_ok_exit_pnl(cases_df, s))["median"] for s in SUBCLASSES]
    valid_means = [m for m in means if not math.isnan(m)]
    same_mean = len(set(_sign(m) for m in valid_means)) <= 1 and len(valid_means) > 0
    same_med = len(set(_sign(m) for m in meds if not math.isnan(m))) <= 1
    spread = (max(valid_means) - min(valid_means)) if valid_means else float("nan")
    emit_desc("cross_subclass", "exit_pnl_pct", "", "", _desc([]),
              {"n": "", "mean": "", "median": "", "std": "", "p25": "",
               "p75": "", "pos_share": "",
               "same_sign_mean": same_mean, "same_sign_median": same_med,
               "mean_spread": spread,
               "mergeable_hint": "populations differ (failed is loss-only)"
               if not same_mean else "exit_pnl signs agree"})

    # (B) captured_extra per (variant, subclass) + cross-subclass consistency.
    for variant in PV_VARIANTS:
        sub_means = {}
        sub_meds = {}
        for sub in SUBCLASSES:
            vals = _ok_captured(cases_df, sub, variant)
            d = _desc(vals)
            sub_means[sub] = d["mean"]
            sub_meds[sub] = d["median"]
            emit_desc("per_subclass", "captured_extra", variant, sub, d)
        vm = [m for m in sub_means.values() if not math.isnan(m)]
        vmed = [m for m in sub_meds.values() if not math.isnan(m)]
        same_mean = (len(vm) > 0) and (len(set(_sign(m) for m in vm)) <= 1)
        same_med = (len(vmed) > 0) and (len(set(_sign(m) for m in vmed)) <= 1)
        spread = (max(vm) - min(vm)) if vm else float("nan")
        # Descriptive hint only -- NOT a merge decision.
        hint = "consistent_direction" if (same_mean and same_med) else "divergent"
        emit_desc("cross_subclass", "captured_extra", variant, "", _desc([]),
                  {"n": "", "mean": "", "median": "", "std": "", "p25": "",
                   "p75": "", "pos_share": "",
                   "same_sign_mean": same_mean, "same_sign_median": same_med,
                   "mean_spread": spread, "mergeable_hint": hint})

        # (C) pooled-if-merged distribution (INSPECTION ONLY).
        pooled = []
        for sub in SUBCLASSES:
            pooled += _ok_captured(cases_df, sub, variant)
        emit_desc("pooled", "captured_extra", variant, "POOLED_3CLASS",
                  _desc(pooled),
                  {"mergeable_hint": "inspection_only_not_endorsed"})

    cols = ["row_type", "metric", "variant", "subclass", "n", "mean", "median",
            "std", "p25", "p75", "pos_share", "same_sign_mean",
            "same_sign_median", "mean_spread", "mergeable_hint"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 5d. S7a -- sensitivity grid. Spread the knobs and record dispersion of the
#     knob-dependent variants per subclass. NO best mark, NO ranking/selection
#     (spec 3.6). trail_pct -> pv_trail_from_high; keep_frac ->
#     pv_downgrade_small_pos. Other variants are knob-invariant (not re-listed).
# ---------------------------------------------------------------------------

def build_sensitivity(events, paths):
    rows = []

    def stats_for(variant, knobs):
        out = {}
        for sub in SUBCLASSES:
            vals = []
            for ev in events:
                if ev["subclass"] != sub:
                    continue
                al = paths.get(ev["name"])
                if al is None or _quality_flag(al) != "ok":
                    continue
                anchor = float(al["close"][0])
                vals.append(score_variant(variant, al, anchor, knobs))
            c = _concentration(vals)
            d = _desc(vals)
            out[sub] = (d, c)
        return out

    for trail_pct in GRID_TRAIL_PCT:
        knobs = {"trail_pct": trail_pct, "keep_frac": DEFAULT_DOWNGRADE_FRAC}
        res = stats_for("pv_trail_from_high", knobs)
        for sub in SUBCLASSES:
            d, c = res[sub]
            rows.append({
                "variant": "pv_trail_from_high",
                "knob_name": "trail_pct",
                "knob_value": trail_pct,
                "subclass": sub,
                "n": d["n"], "mean": d["mean"], "median": d["median"],
                "total": c["total"],
                "top10pct_share_of_total": c["topk_share_of_total"],
                "sum_excl_top10pct": c["sum_excl_topk"],
                "proxy_distortion_flag": "high",
            })

    for keep_frac in GRID_DOWNGRADE_FRAC:
        knobs = {"trail_pct": DEFAULT_TRAIL_PCT, "keep_frac": keep_frac}
        res = stats_for("pv_downgrade_small_pos", knobs)
        for sub in SUBCLASSES:
            d, c = res[sub]
            rows.append({
                "variant": "pv_downgrade_small_pos",
                "knob_name": "keep_frac",
                "knob_value": keep_frac,
                "subclass": sub,
                "n": d["n"], "mean": d["mean"], "median": d["median"],
                "total": c["total"],
                "top10pct_share_of_total": c["topk_share_of_total"],
                "sum_excl_top10pct": c["sum_excl_topk"],
                "proxy_distortion_flag": "low",
            })

    cols = ["variant", "knob_name", "knob_value", "subclass", "n", "mean",
            "median", "total", "top10pct_share_of_total", "sum_excl_top10pct",
            "proxy_distortion_flag"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 5e. S7b -- SUGGESTED verdict selector + report. This produces a HEURISTIC
#     SUGGESTION ONLY, derived from the CSVs. The FINAL verdict is set by the
#     user after reading the real CSVs (the report separates "suggested" from
#     "awaiting manual confirmation"). Per spec 5, the suggestion only proposes
#     protection_robust_design_next when concentration (gains survive removing
#     the top 10%) AND mergeability (consistent direction) hold on a sample that
#     is NOT padded by pooling non-mergeable subclasses.
#
#     Logic order (corrected): mergeability/heterogeneity FIRST, THEN sample
#     sufficiency. Sample sufficiency uses pooled n ONLY when the subclasses
#     look mergeable; otherwise it uses the largest SINGLE-subclass n (no
#     pooling across populations of different exit semantics).
#
#     SAMPLE_SUFFICIENCY_HINT is a SOFT label threshold, not a hard gate -- it
#     only tags the sample as 'adequate' vs 'thin'. It is admittedly a judgment
#     call, not a power calculation.
# ---------------------------------------------------------------------------

SAMPLE_SUFFICIENCY_HINT = 15  # soft label only: design_n >= this -> 'adequate'


def select_verdict(by_subclass_df, mergeability_df, cases_df, proxy_mode):
    """Return (suggested_verdict, reasons, meta). suggested_verdict is a
    reference suggestion only; the user confirms the final verdict from CSVs."""
    reasons = []

    # Per-subclass and pooled ok event counts (one row per event = immediate).
    ok_imm = cases_df[(cases_df["variant"] == "pv_immediate_full_exit")
                      & (cases_df["data_quality_flag"] == "ok")]
    per_sub_n = {sub: int(len(ok_imm[ok_imm["subclass"] == sub]))
                 for sub in SUBCLASSES}
    pooled_n = int(len(ok_imm))
    reasons.append("ok events per subclass: %s ; pooled=%d" %
                   (per_sub_n, pooled_n))

    meta = {
        "sample_sufficiency": "thin",
        "design_n": 0,
        "design_basis": "",
        "per_subclass_n": per_sub_n,
        "pooled_n": pooled_n,
        "frac_consistent": float("nan"),
        "mergeable_signal": False,
        "is_suggestion": True,
    }

    if proxy_mode:
        reasons.append("proxy run (jqdata unavailable): no real forward paths; "
                       "rerun inside JoinQuant before any verdict is meaningful.")
        return ("VERDICT_data_insufficient_continue", reasons, meta)

    # Mergeability signal: are low-distortion variants consistent in direction?
    cross = mergeability_df[(mergeability_df["row_type"] == "cross_subclass")
                            & (mergeability_df["metric"] == "captured_extra")]
    consistent = []
    for v in LOW_NONBASE_VARIANTS:
        row = cross[cross["variant"] == v]
        if len(row) and bool(row.iloc[0]["same_sign_mean"]) and bool(row.iloc[0]["same_sign_median"]):
            consistent.append(v)
    frac_consistent = (len(consistent) / float(len(LOW_NONBASE_VARIANTS))
                       if LOW_NONBASE_VARIANTS else 0.0)
    mergeable_signal = frac_consistent >= 0.5
    meta["frac_consistent"] = frac_consistent
    meta["mergeable_signal"] = mergeable_signal
    reasons.append("low-distortion variants consistent in direction across "
                   "subclasses: %d/%d (%s) -> mergeable_signal=%s" % (
                       len(consistent), len(LOW_NONBASE_VARIANTS),
                       ", ".join(consistent) or "none", mergeable_signal))

    # Sample sufficiency: pooled n ONLY if mergeable, else largest single-subclass.
    if mergeable_signal:
        design_n = pooled_n
        design_basis = "pooled (subclasses look mergeable)"
    else:
        design_n = max(per_sub_n.values()) if per_sub_n else 0
        design_basis = ("largest single subclass (subclasses NOT mergeable -> "
                        "no pooling across exit semantics)")
    sufficiency = "adequate" if design_n >= SAMPLE_SUFFICIENCY_HINT else "thin"
    meta["design_n"] = design_n
    meta["design_basis"] = design_basis
    meta["sample_sufficiency"] = sufficiency
    reasons.append("design-relevant n = %d via %s -> sample_sufficiency=%s "
                   "(soft hint threshold=%d, NOT a hard gate)" %
                   (design_n, design_basis, sufficiency, SAMPLE_SUFFICIENCY_HINT))

    # Concentration: do gains survive removing top 10% (per-subclass, ok dist)?
    bs = by_subclass_df
    survive = 0
    total_checked = 0
    for v in LOW_NONBASE_VARIANTS:
        sl = bs[bs["variant"] == v]
        for _, r in sl.iterrows():
            if r["n"] and r["n"] > 0:
                total_checked += 1
                if bool(r["positive_after_excl_top10pct"]):
                    survive += 1
    frac_survive = (survive / float(total_checked)) if total_checked else 0.0
    reasons.append("subclass x low-variant cells where gains survive removing "
                   "top 10%%: %d/%d" % (survive, total_checked))

    # Suggestion tree: heterogeneity FIRST, THEN sufficiency, THEN concentration.
    if not mergeable_signal:
        reasons.append("subclasses diverge on most low-distortion variants -> "
                       "not one population; study per subclass")
        return ("VERDICT_subclass_heterogeneous_split", reasons, meta)

    if sufficiency == "thin":
        reasons.append("mergeable but design-relevant sample is thin -> keep "
                       "collecting before any design talk")
        return ("VERDICT_data_insufficient_continue", reasons, meta)

    if frac_survive >= 0.5:
        reasons.append("mergeable + adequate + gains survive top-10% removal -> "
                       "CSV supports proposing design")
        return ("VERDICT_protection_robust_design_next", reasons, meta)

    reasons.append("mergeable + adequate but gains vanish once top 10% removed "
                   "-> outlier-driven")
    return ("VERDICT_still_outlier_driven_no_design", reasons, meta)


def _fmt(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "nan"
        return "%.4f" % float(x)
    except (TypeError, ValueError):
        return str(x)


def write_report(by_subclass_df, mergeability_df, sens_df, cases_df,
                 events, proxy_mode, suggested_verdict, verdict_reasons, meta):
    L = []
    L.append("# v140D Early-Exit Events -- Multi-Direction Counterfactual Report")
    L.append("")
    L.append("Research-only. No orders, no backtest engine, no live trading, "
             "no mechanism design, no parameter search. Strategy code and "
             "ledgers are read-only.")
    L.append("")
    if proxy_mode:
        L.append("> MODE: PROXY (jqdata unavailable). Forward paths were not "
                 "fetched; captured_extra is 0 everywhere and the suggested "
                 "verdict is forced to data_insufficient. Rerun inside JoinQuant.")
        L.append("")
    L.append("Locked config (user, after S3): ee_ledger_early gate = >=3%; "
             "overlapping 7 events assigned to ee_promotion_block and removed "
             "from ee_ledger_early. Subclasses mutually exclusive: "
             "promotion 7 + failed 12 + ledger_early 6 = 25 events.")
    L.append("Anchor price = exit-day close, uniform across subclasses "
             "(comparability; differs slightly from S2 promotion-only run).")
    L.append("")

    # Q1 sample sizes.
    L.append("## Q1. Subclass sample sizes and overlap")
    L.append("")
    counts = {}
    for sub in SUBCLASSES:
        counts[sub] = sum(1 for e in events if e["subclass"] == sub)
    L.append("- ee_promotion_block: %d (S2-reconciled, verbatim)" % counts["ee_promotion_block"])
    L.append("- ee_failed_trade: %d (loss-only; no overlap with the profit "
             "subclasses)" % counts["ee_failed_trade"])
    L.append("- ee_ledger_early (>=3%%, dedup): %d new events; the 7 overlapping "
             "profitable exits were moved to ee_promotion_block." % counts["ee_ledger_early"])
    L.append("- Gate counts seen at S3: >0%=13, >=3%=13, >=5%=12 (overlap with "
             "the 7 promotion = 7/7/6). The profitable-exit sample barely "
             "expands; the 6 new ledger_early events are all big-meat "
             "dragon_half_protect (>=11%).")
    ok_imm = cases_df[(cases_df["variant"] == "pv_immediate_full_exit")
                      & (cases_df["data_quality_flag"] == "ok")]
    L.append("- Events with usable forward path (ok): %d of %d." %
             (len(ok_imm), len(events)))
    L.append("")

    # Q2 layer-one per subclass.
    L.append("## Q2. Layer one -- per-subclass distribution (independent)")
    L.append("")
    L.append("| subclass | variant | n | hit_rate | mean | median | "
             "top10%_share | sum_excl_top10% | pos_after_excl | proxy |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in by_subclass_df.iterrows():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["subclass"], r["variant"], r["n"], _fmt(r["hit_rate"]),
            _fmt(r["mean_captured_extra"]), _fmt(r["median_captured_extra"]),
            _fmt(r["top10pct_share_of_total"]), _fmt(r["sum_excl_top10pct"]),
            r["positive_after_excl_top10pct"], r["proxy_distortion_flag"]))
    L.append("")
    L.append("Read: compare ee_promotion_block vs ee_failed_trade vs "
             "ee_ledger_early on the same variant -- do the early exits behave "
             "like the same illness?")
    L.append("")

    # Q3 concentration.
    L.append("## Q3. Concentration -- are gains outlier-driven?")
    L.append("")
    L.append("For each subclass x variant, 'pos_after_excl' = does the summed "
             "captured_extra stay positive after removing the top 10% of "
             "events? If it flips negative, the gain was outlier-driven. See "
             "the table above (sum_excl_top10% and pos_after_excl columns).")
    L.append("")

    # Q4 mergeability.
    L.append("## Q4. Layer two -- mergeability of the three subclasses")
    L.append("")
    L.append("Per-subclass exit_pnl_pct and captured_extra distributions plus "
             "cross-subclass sign agreement are in jq_ee_mergeability.csv. "
             "Key cross-subclass signals (captured_extra):")
    L.append("")
    L.append("| variant | same_sign_mean | same_sign_median | mean_spread | hint |")
    L.append("|---|---|---|---|---|")
    cross = mergeability_df[(mergeability_df["row_type"] == "cross_subclass")
                            & (mergeability_df["metric"] == "captured_extra")]
    for _, r in cross.iterrows():
        L.append("| %s | %s | %s | %s | %s |" % (
            r["variant"], r["same_sign_mean"], r["same_sign_median"],
            _fmt(r["mean_spread"]), r["mergeable_hint"]))
    L.append("")
    L.append("exit_pnl_pct populations: ee_failed_trade is loss-only while the "
             "other two are profit-only -- a strong prior that the subclasses "
             "are NOT one population. Merging is NOT done by default; the "
             "pooled rows in the CSV are for inspection only. Final merge "
             "decision is the user's.")
    L.append("")

    # Q5 MA5 on bigger sample.
    L.append("## Q5. Do MA5-class protections still fail on 'kill-then-rally'?")
    L.append("")
    L.append("Inspect pv_half_exit_hold_half / pv_delay_1d_confirm / "
             "pv_downgrade_small_pos (all proxy=low) in the per-subclass table. "
             "If hit_rate stays low and means hug zero/negative on the larger "
             "ledger_early + failed samples, the MA5 logic still misses "
             "kill-then-rally moves.")
    L.append("")

    # Q6 trail.
    L.append("## Q6. Is the trail class (proxy=high) still ranking-only?")
    L.append("")
    L.append("pv_trail_from_high uses daily highs and misses intraday peaks "
             "(proxy_distortion_flag=high). It stays RANKING-ONLY and is "
             "excluded from core verdict evidence regardless of how good it "
             "looks. See jq_ee_sensitivity.csv for its knob dispersion.")
    L.append("")

    # Q7 / Q8.
    L.append("## Q7. Is the sample large enough to discuss mechanism design?")
    L.append("")
    L.append("This is a LABEL, not a hard gate. design-relevant n = %d via %s; "
             "sample_sufficiency = %s (soft hint threshold = %d). Per-subclass "
             "ok events: %s ; pooled = %d." % (
                 meta["design_n"], meta["design_basis"],
                 meta["sample_sufficiency"], SAMPLE_SUFFICIENCY_HINT,
                 meta["per_subclass_n"], meta["pooled_n"]))
    L.append("")
    L.append("Important: when the subclasses are NOT mergeable, the "
             "design-relevant n is the largest SINGLE subclass (no pooling "
             "across different exit semantics) -- the pooled 25 does NOT count "
             "as 'sample sufficient' unless mergeability holds.")
    L.append("")
    L.append("## Q8. Are master-line / live / tuning / new-strategy still forbidden?")
    L.append("")
    L.append("YES. This stage designs nothing, tunes nothing, writes no new "
             "strategy, touches no master line, places no orders, and makes no "
             "git changes.")
    L.append("")

    # Suggested verdict (reference only).
    L.append("## SUGGESTED VERDICT (reference only -- NOT final)")
    L.append("")
    L.append("**%s**" % suggested_verdict)
    L.append("")
    L.append("This is a heuristic suggestion derived from the CSVs. "
             "Concentration + mergeability are the core drivers. Evidence:")
    for r in verdict_reasons:
        L.append("- " + r)
    L.append("")
    L.append("Suggestion rules: heterogeneity is checked FIRST; sample "
             "sufficiency is a SOFT label checked AFTER, and uses pooled n ONLY "
             "when the subclasses look mergeable. protection_robust_design_next "
             "is suggested ONLY with consistent cross-subclass direction AND "
             "gains that survive removing the top 10% on a non-pooled-padded "
             "sample.")
    L.append("")

    # Manual confirmation (the real decision).
    L.append("## AWAITING MANUAL CONFIRMATION (final verdict = user's call)")
    L.append("")
    L.append("The FINAL verdict is set by the user after reading the real CSVs "
             "above. The suggestion is advisory only and may be overridden. "
             "Choose ONE: VERDICT_protection_robust_design_next / "
             "VERDICT_still_outlier_driven_no_design / "
             "VERDICT_subclass_heterogeneous_split / "
             "VERDICT_data_insufficient_continue. Per spec 5, do NOT pick "
             "protection_robust_design_next unless the CSVs clearly support it "
             "(concentration survives top-10% removal AND subclasses are "
             "genuinely mergeable on an adequate, non-padded sample).")
    L.append("")
    L.append("FINAL VERDICT: __________ (fill in after review)")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# 6. Entry point (full pipeline: universe + cases + by_subclass + mergeability
#    + sensitivity + report + zip).
# ---------------------------------------------------------------------------

def main():
    _ensure_out_dir()
    knobs = default_knobs()
    events = build_events()
    paths = fetch_all(events)
    proxy_mode = all(v is None for v in paths.values())

    universe_df = build_universe(events, paths)
    cases_df = build_cases(events, paths, knobs)
    by_subclass_df = build_by_subclass_summary(cases_df)
    mergeability_df = build_mergeability(cases_df)
    sens_df = build_sensitivity(events, paths)

    suggested_verdict, verdict_reasons, verdict_meta = select_verdict(
        by_subclass_df, mergeability_df, cases_df, proxy_mode)
    report_text = write_report(by_subclass_df, mergeability_df, sens_df,
                               cases_df, events, proxy_mode, suggested_verdict,
                               verdict_reasons, verdict_meta)

    uni_path = os.path.join(OUT_DIR, OUT_UNIVERSE)
    cases_path = os.path.join(OUT_DIR, OUT_CASES)
    by_sub_path = os.path.join(OUT_DIR, OUT_BY_SUBCLASS)
    merge_path = os.path.join(OUT_DIR, OUT_MERGEABILITY)
    sens_path = os.path.join(OUT_DIR, OUT_SENSITIVITY)
    report_path = os.path.join(OUT_DIR, OUT_REPORT)

    universe_df.to_csv(uni_path, index=False, encoding="utf-8")
    cases_df.to_csv(cases_path, index=False, encoding="utf-8")
    by_subclass_df.to_csv(by_sub_path, index=False, encoding="utf-8")
    mergeability_df.to_csv(merge_path, index=False, encoding="utf-8")
    sens_df.to_csv(sens_path, index=False, encoding="utf-8")
    with open(report_path, "w") as f:
        f.write(report_text)

    # Bundle outputs. zip stores file names only, no directory prefix.
    zip_path = os.path.join(OUT_DIR, OUT_ZIP)
    member_paths = [uni_path, cases_path, by_sub_path, merge_path,
                    sens_path, report_path]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in member_paths:
            zf.write(p, arcname=os.path.basename(p))

    print("proxy_mode =", proxy_mode, "(True means jqdata unavailable)")
    print("events =", len(events), "cases rows =", len(cases_df))
    print("SUGGESTED VERDICT (reference only) =", suggested_verdict)
    print("sample_sufficiency =", verdict_meta["sample_sufficiency"],
          "design_n =", verdict_meta["design_n"],
          "via", verdict_meta["design_basis"])
    print("FINAL VERDICT = user decides from CSVs")
    for p in member_paths + [zip_path]:
        print("wrote:", p)


if __name__ == "__main__":
    main()
