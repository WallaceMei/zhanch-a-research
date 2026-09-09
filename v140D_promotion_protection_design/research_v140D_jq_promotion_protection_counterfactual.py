# -*- coding: utf-8 -*-
#
# research_v140D_jq_promotion_protection_counterfactual.py
#
# Research-only counterfactual study (NO trading, NO backtest engine).
# Purpose: quantify, for 7 historical "promotion-block take-profit" events,
#   how 5 candidate protection variants (PV_*) would have changed the
#   captured return, AND what that does to the strategy's profit
#   concentration (Top-N dependency) -- the known robustness weak spot.
#
# HARD CONSTRAINTS (enforced by design, do not relax):
#   - This file MUST NOT contain any of:
#       order / order_value / order_target / order_target_value /
#       run_backtest / schedule_function
#   - get_price MUST NOT pass start_date and count together.
#   - All output paths are RELATIVE. No absolute "D:\\" paths.
#   - Python 3.6 compatible. Code region is pure ASCII.
#
# Run location: JoinQuant research notebook (jqdata available).
# If jqdata is unavailable, the script still runs in PROXY mode using the
# embedded block-day close prices (ranking-only, flagged as distorted).

import os
import json
import zipfile
import datetime

import numpy as np
import pandas as pd

try:
    from jqdata import *  # noqa: F401,F403
    _HAS_JQDATA = True
except Exception:
    _HAS_JQDATA = False


# ---------------------------------------------------------------------------
# 0. Output config (relative paths only)
# ---------------------------------------------------------------------------

OUT_DIR = "promotion_protection_outputs"

# Spec 5.5 output names (do not rename).
OUT_CASES = "jq_promotion_protection_counterfactual_cases.csv"
OUT_SUMMARY = "jq_promotion_protection_summary.csv"
OUT_SENSITIVITY = "jq_promotion_protection_sensitivity.csv"
OUT_REPORT = "jq_promotion_protection_report.md"
OUT_ZIP = "v140D_promotion_protection_counterfactual_outputs.zip"


def _ensure_out_dir():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)


# ---------------------------------------------------------------------------
# 1. BASELINE_LEDGER: the realized 37-trade ledger (from smoke-test audit).
#    Used ONLY to recompute profit concentration after a counterfactual
#    change to the 7 promotion-block trades. pnl_val is realized RMB pnl.
# ---------------------------------------------------------------------------

BASELINE_LEDGER = [
    # stock, name, exit_date, pnl_val
    ("000510.XSHE", "xinjinlu_1", "2026-01-28", 19138.0),
    ("605069.XSHG", "zhenghe", "2026-01-12", -400.0),
    ("002278.XSHE", "shenkai", "2026-01-15", -1305.0),
    ("603920.XSHG", "shiyun", "2026-01-22", -387.0),
    ("000603.XSHE", "shengda", "2026-01-22", -495.0),
    ("600487.XSHG", "hengtong", "2026-01-28", 1190.0),
    ("603629.XSHG", "litong", "2026-02-13", 22804.0),
    ("603396.XSHG", "jinchen", "2026-02-03", -1080.0),
    ("603212.XSHG", "saiwu", "2026-02-04", 820.0),
    ("002283.XSHE", "tianrun", "2026-03-03", 10793.0),
    ("603301.XSHG", "zhende", "2026-02-24", -1416.0),
    ("002378.XSHE", "zhangyuan", "2026-03-05", 8778.0),
    ("000510.XSHE", "xinjinlu_2", "2026-02-27", 1881.0),
    ("600549.XSHG", "xiamen_w", "2026-03-06", -2055.0),
    ("600821.XSHG", "jinkai", "2026-03-17", 7348.0),
    ("000815.XSHE", "meiliyun", "2026-03-13", -2156.0),
    ("600773.XSHG", "xizang_ct", "2026-03-13", 672.0),
    ("601869.XSHG", "changfei", "2026-03-19", -858.0),
    ("002980.XSHE", "huasheng", "2026-03-19", -2450.0),
    ("002082.XSHE", "wanbangde", "2026-04-09", 9230.0),
    ("603601.XSHG", "zaisheng", "2026-04-03", -1968.0),
    ("601872.XSHG", "zhaoshang", "2026-04-09", -2000.0),
    ("002824.XSHE", "hesheng", "2026-04-24", -210.0),
    ("000762.XSHE", "xizang_ky", "2026-05-13", -588.0),
    ("002943.XSHE", "yujing_1", "2026-04-22", -328.0),
    ("002176.XSHE", "jiangte", "2026-04-24", 2299.0),
    ("002647.XSHE", "rendong", "2026-05-15", -1637.0),
    ("002222.XSHE", "fujing", "2026-05-07", 1078.0),
    ("002560.XSHE", "tongda", "2026-05-11", -1296.0),
    ("603002.XSHG", "hongchang", "2026-05-15", -1695.0),
    ("002885.XSHE", "jingquanhua", "2026-05-19", -1104.0),
    ("002943.XSHE", "yujing_2", "2026-05-25", -112.0),
    ("002491.XSHE", "tongding", "2026-05-26", -799.0),
    ("000021.XSHE", "shenkeji", "2026-05-27", 1975.0),
    ("002745.XSHE", "mulinsen", "2026-05-29", -1768.0),
    ("605111.XSHG", "xinjieneng", "2026-05-29", -1045.0),
    ("605589.XSHG", "shengquan", "2026-05-29", -1032.0),
]


# ---------------------------------------------------------------------------
# 2. PROMOTION_EVENTS: the 7 promotion-block take-profit trades.
#    These are the satellite slices exited early by the
#    shadow_no_promotion_take_profit rule. block_date is the realized
#    exit date; block_return / block_pnl_val are realized at that exit.
#    ledger_key links back to BASELINE_LEDGER for concentration recompute.
# ---------------------------------------------------------------------------

PROMOTION_EVENTS = [
    {
        "ledger_key": "hengtong",
        "stock": "600487.XSHG",
        "name": "hengtong",
        "block_date": "2026-01-28",
        "block_price": 33.590,
        "block_return": 0.0763,
        "block_pnl_val": 1190.0,
        "hold_days_at_block": 2,
        "phase": "pre_oos",
    },
    {
        "ledger_key": "saiwu",
        "stock": "603212.XSHG",
        "name": "saiwu",
        "block_date": "2026-02-04",
        "block_price": 18.330,
        "block_return": 0.0468,
        "block_pnl_val": 820.0,
        "hold_days_at_block": 1,
        "phase": "pre_oos",
    },
    {
        "ledger_key": "xinjinlu_2",
        "stock": "000510.XSHE",
        "name": "xinjinlu_2",
        "block_date": "2026-02-27",
        "block_price": 20.410,
        "block_return": 0.0914,
        "block_pnl_val": 1881.0,
        "hold_days_at_block": 2,
        "phase": "pre_oos",
    },
    {
        "ledger_key": "xizang_ct",
        "stock": "600773.XSHG",
        "name": "xizang_ct",
        "block_date": "2026-03-13",
        "block_price": 18.210,
        "block_return": 0.0557,
        "block_pnl_val": 672.0,
        "hold_days_at_block": 2,
        "phase": "pre_oos",
    },
    {
        "ledger_key": "jiangte",
        "stock": "002176.XSHE",
        "name": "jiangte",
        "block_date": "2026-04-24",
        "block_price": 13.620,
        "block_return": 0.0975,
        "block_pnl_val": 2299.0,
        "hold_days_at_block": 2,
        "phase": "oos",
    },
    {
        "ledger_key": "fujing",
        "stock": "002222.XSHE",
        "name": "fujing",
        "block_date": "2026-05-07",
        "block_price": 98.210,
        "block_return": 0.0581,
        "block_pnl_val": 1078.0,
        "hold_days_at_block": 1,
        "phase": "oos",
    },
    {
        "ledger_key": "shenkeji",
        "stock": "000021.XSHE",
        "name": "shenkeji",
        "block_date": "2026-05-27",
        "block_price": 45.100,
        "block_return": 0.0960,
        "block_pnl_val": 1975.0,
        "hold_days_at_block": 2,
        "phase": "oos",
    },
]


# ---------------------------------------------------------------------------
# 3. Protection variants (research-only, spec-locked).
#    Exactly the 5 spec variant ids (lowercase, do not rename or merge).
#    Each variant maps a post-block price path to a "captured_extra_return"
#    relative to the embedded block_price. NONE place orders.
#
#    pv_immediate_full_exit   : full exit at block, captured_extra = 0 (baseline)
#    pv_half_exit_hold_half   : sell half at block; hold the other half until
#                               close < MA5 or the 5th trade day (first wins).
#                               extra = 0.5*0 + 0.5*(half-slice return vs block)
#    pv_delay_1d_confirm      : do NOT exit on block day; next day if
#                               close < MA5 or return negative -> exit next
#                               close; else hold until close < MA5 or 5th day.
#    pv_trail_from_high       : trail stop from post-block high by trail_pct
#                               (proxy-distorted, ranking-only).
#    pv_downgrade_small_pos   : keep keep_frac small slice held until close<MA5
#                               or 5th day; extra = keep_frac*(slice return).
#                               NOT keep_frac*trail.
# ---------------------------------------------------------------------------

PV_VARIANTS = [
    "pv_immediate_full_exit",
    "pv_half_exit_hold_half",
    "pv_delay_1d_confirm",
    "pv_trail_from_high",
    "pv_downgrade_small_pos",
]

# close_proxy distortion flag per variant. Trail-from-high cannot see intraday
# peaks on daily bars -> high distortion (ranking-only). MA5 variants use the
# closing price, which is reliable under the close proxy -> low distortion.
PROXY_FLAG = {
    "pv_immediate_full_exit": "low",
    "pv_half_exit_hold_half": "low",
    "pv_delay_1d_confirm": "low",
    "pv_trail_from_high": "high",
    "pv_downgrade_small_pos": "low",
}

# Knobs (sensitivity grid overrides per run). No best-search, no profit tuning.
DEFAULT_TRAIL_PCT = 0.05
DEFAULT_DOWNGRADE_FRAC = 1.0 / 3.0

# Hold cap (trade days after block) for the MA5 exit variants.
HOLD_LIMIT_DAYS = 5
# Days needed to compute MA5 at the block day itself (4 prior + block).
MA5_DAYS = 5

GRID_TRAIL_PCT = [0.03, 0.05, 0.08]
GRID_DOWNGRADE_FRAC = [1.0 / 3.0, 0.5]

# Forward horizon (trade days after block) over which we evaluate paths.
FORWARD_DAYS = 10
END_DATE_CAP = "2026-07-01"


# ---------------------------------------------------------------------------
# 4. Price-path fetch.
#    JoinQuant rule: get_price MUST NOT receive start_date and count together.
#    We therefore resolve an explicit [start_date, end_date] window via
#    get_trade_days(start_date=..., count=...) FIRST, then call get_price with
#    that window only (no count argument).
# ---------------------------------------------------------------------------

def _price_window(block_date_str):
    """Return (start_date_str, end_date_str) spanning 4 trade days BEFORE the
    block (so MA5 is computable at the block day) through FORWARD_DAYS after.
    Both endpoints come from get_trade_days(count=...) (legal). get_price is
    called later WITHOUT count."""
    if not _HAS_JQDATA:
        return None, None

    # MA5_DAYS days ending at block_date = 4 prior + block day.
    pre = get_trade_days(end_date=block_date_str, count=MA5_DAYS)
    # FORWARD_DAYS + 1 days starting at block_date = block + FORWARD_DAYS.
    fwd = get_trade_days(start_date=block_date_str, count=FORWARD_DAYS + 1)
    if pre is None or len(pre) == 0 or fwd is None or len(fwd) == 0:
        return None, None
    start_str = str(pre[0])
    end_str = str(fwd[-1])
    if end_str > END_DATE_CAP:
        end_str = END_DATE_CAP
    return start_str, end_str


def _aligned_from_block(prices_df, block_date_str):
    """Build forward-aligned arrays from a price frame that includes pre-days.
    Returns dict with close/high/ma5 arrays where index 0 = block day, 1 =
    block+1, ... MA5 is a true rolling 5-close mean. None if block day absent."""
    if prices_df is None or len(prices_df) == 0:
        return None
    closes_all = np.asarray(prices_df["close"].values, dtype=float)
    highs_all = np.asarray(prices_df["high"].values, dtype=float)
    # True MA5: rolling mean of the last 5 closing prices (close_proxy-safe).
    ma5_all = pd.Series(closes_all).rolling(window=5).mean().values
    # Locate the block day within the frame index.
    block_idx = None
    for i, d in enumerate(prices_df.index):
        if str(d)[:10] == block_date_str:
            block_idx = i
            break
    if block_idx is None:
        return None
    return {
        "close": closes_all[block_idx:],
        "high": highs_all[block_idx:],
        "ma5": ma5_all[block_idx:],
    }


def fetch_aligned(stock, block_date_str):
    """Fetch the price window and return forward-aligned close/high/ma5, or
    None in proxy mode."""
    if not _HAS_JQDATA:
        return None
    start_str, end_str = _price_window(block_date_str)
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
    return _aligned_from_block(prices_df, block_date_str)


# ---------------------------------------------------------------------------
# 5. Variant scorers. Each returns captured_extra_return: the return captured
#    AFTER the block close, expressed as a fraction of block_price.
#    Positive means the variant captured more than the realized block exit.
#    These are PROXY-LEVEL when paths come from daily close/high (ranking only).
# ---------------------------------------------------------------------------

def _ma5_exit_close(al, block_price, start_i):
    """Walk forward days [start_i .. HOLD_LIMIT_DAYS]; exit at the first close
    that breaks below that day's MA5, else at the HOLD_LIMIT_DAYS-th day (or
    the last available day). Returns the exit close, or block_price if no
    forward day exists."""
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
    """Sell half at block (0 extra); hold the other half until close<MA5 or the
    5th trade day. captured_extra = 0.5*0 + 0.5*(half-slice return vs block)."""
    if al is None or al["close"].size < 2:
        return 0.0
    exit_px = _ma5_exit_close(al, block_price, 1)
    half_return = (exit_px - block_price) / block_price
    return 0.5 * half_return


def score_delay_1d_confirm(al, block_price):
    """Do not exit on block day. Next day: if close<MA5 or return<0 -> exit at
    next close; else hold until close<MA5 or the 5th day."""
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
    """Trail stop from the post-block running high by trail_pct. PROXY-LEVEL:
    daily high misses intraday peaks (ranking-only, proxy_distortion=high)."""
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
    """Keep a small keep_frac slice held until close<MA5 or the 5th day.
    captured_extra = keep_frac*(slice return vs block). NOT keep_frac*trail."""
    if al is None or al["close"].size < 2:
        return 0.0
    exit_px = _ma5_exit_close(al, block_price, 1)
    slice_return = (exit_px - block_price) / block_price
    return keep_frac * slice_return


# ---------------------------------------------------------------------------
# 6. Variant dispatcher: given a variant id + knobs, return captured_extra.
# ---------------------------------------------------------------------------

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
    return {
        "trail_pct": DEFAULT_TRAIL_PCT,
        "keep_frac": DEFAULT_DOWNGRADE_FRAC,
    }


# ---------------------------------------------------------------------------
# 7. Concentration recompute.
#    For a given variant + knob set, replace each promotion-block trade's
#    realized pnl with its counterfactual pnl, then recompute the strategy's
#    net pnl and Top-N dependency. position_value is backed out from the
#    realized block trade: position_value = block_pnl_val / block_return.
# ---------------------------------------------------------------------------

def baseline_pnls():
    return [row[3] for row in BASELINE_LEDGER]


def concentration_metrics(pnl_list):
    arr = np.asarray(pnl_list, dtype=float)
    net = float(arr.sum())
    gross_profit = float(arr[arr > 0].sum())
    gross_loss = float(arr[arr < 0].sum())
    winners = np.sort(arr[arr > 0])[::-1]
    top1 = float(winners[:1].sum())
    top3 = float(winners[:3].sum())
    top5 = float(winners[:5].sum())
    net_excl_top5 = net - top5
    return {
        "net_pnl": net,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "top1": top1,
        "top3": top3,
        "top5": top5,
        "top3_share_of_net": (top3 / net) if net != 0 else float("nan"),
        "top5_share_of_net": (top5 / net) if net != 0 else float("nan"),
        "net_excl_top5": net_excl_top5,
    }


def counterfactual_pnls(extra_by_key):
    """Return a new pnl list where each promotion-block trade's pnl is
    replaced by block_pnl_val + position_value * captured_extra_return."""
    # Map ledger_key -> counterfactual pnl.
    cf_by_key = {}
    for ev in PROMOTION_EVENTS:
        key = ev["ledger_key"]
        block_return = ev["block_return"]
        block_pnl = ev["block_pnl_val"]
        position_value = block_pnl / block_return if block_return != 0 else 0.0
        extra = extra_by_key.get(key, 0.0)
        cf_by_key[key] = block_pnl + position_value * extra

    new_pnls = []
    for row in BASELINE_LEDGER:
        key = row[1]
        if key in cf_by_key:
            new_pnls.append(cf_by_key[key])
        else:
            new_pnls.append(row[3])
    return new_pnls


# ---------------------------------------------------------------------------
# 8. Main driver.
# ---------------------------------------------------------------------------

def _fetch_all_paths():
    """Fetch (or proxy) the forward-aligned path for each promotion event."""
    paths = {}
    for ev in PROMOTION_EVENTS:
        paths[ev["ledger_key"]] = fetch_aligned(ev["stock"], ev["block_date"])
    return paths


def build_variant_event_matrix(paths, knobs):
    """Long-format rows: one per (variant, event) with captured_extra and the
    resulting counterfactual pnl for that single trade. Spec output: cases."""
    rows = []
    for variant in PV_VARIANTS:
        for ev in PROMOTION_EVENTS:
            key = ev["ledger_key"]
            al = paths.get(key)
            block_return = ev["block_return"]
            block_pnl = ev["block_pnl_val"]
            position_value = block_pnl / block_return if block_return != 0 else 0.0
            extra = score_variant(variant, al, ev["block_price"], knobs)
            cf_pnl = block_pnl + position_value * extra
            rows.append({
                "variant": variant,
                "ledger_key": key,
                "stock": ev["stock"],
                "block_date": ev["block_date"],
                "phase": ev["phase"],
                "block_return": block_return,
                "block_pnl_val": block_pnl,
                "position_value": position_value,
                "captured_extra_return": extra,
                "counterfactual_pnl_val": cf_pnl,
                "delta_pnl_val": cf_pnl - block_pnl,
                "proxy_distortion_flag": PROXY_FLAG[variant],
                "proxy_mode": (al is None),
            })
    return pd.DataFrame(rows)


def build_concentration_recompute(paths, knobs):
    """One row per variant (plus the realized baseline): portfolio-level
    concentration metrics after applying that variant to all 7 promotion-block
    trades. Spec output: summary (standalone)."""
    rows = []
    base = concentration_metrics(baseline_pnls())
    base_row = dict(base)
    base_row["variant"] = "REALIZED_BASELINE"
    base_row["proxy_distortion_flag"] = "none"
    rows.append(base_row)

    for variant in PV_VARIANTS:
        extra_by_key = {}
        for ev in PROMOTION_EVENTS:
            al = paths.get(ev["ledger_key"])
            extra_by_key[ev["ledger_key"]] = score_variant(
                variant, al, ev["block_price"], knobs
            )
        m = concentration_metrics(counterfactual_pnls(extra_by_key))
        m["variant"] = variant
        m["proxy_distortion_flag"] = PROXY_FLAG[variant]
        rows.append(m)

    df = pd.DataFrame(rows)
    cols = ["variant", "net_pnl", "gross_profit", "gross_loss",
            "top1", "top3", "top5", "top3_share_of_net",
            "top5_share_of_net", "net_excl_top5", "proxy_distortion_flag"]
    return df[cols]


def build_sensitivity_grid(paths):
    """Spread the threshold knobs and record portfolio net_excl_top5 (the
    concentration-robustness proxy). No best mark, no profit ranking -- the
    grid only shows dispersion. Spec output: sensitivity."""
    rows = []
    for trail_pct in GRID_TRAIL_PCT:
        for keep_frac in GRID_DOWNGRADE_FRAC:
            knobs = {"trail_pct": trail_pct, "keep_frac": keep_frac}
            for variant in PV_VARIANTS:
                extra_by_key = {}
                for ev in PROMOTION_EVENTS:
                    al = paths.get(ev["ledger_key"])
                    extra_by_key[ev["ledger_key"]] = score_variant(
                        variant, al, ev["block_price"], knobs
                    )
                m = concentration_metrics(counterfactual_pnls(extra_by_key))
                rows.append({
                    "variant": variant,
                    "trail_pct": trail_pct,
                    "keep_frac": keep_frac,
                    "net_pnl": m["net_pnl"],
                    "top5_share_of_net": m["top5_share_of_net"],
                    "net_excl_top5": m["net_excl_top5"],
                    "proxy_distortion_flag": PROXY_FLAG[variant],
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 9. Report writer.
# ---------------------------------------------------------------------------

def write_report(conc_df, proxy_mode):
    lines = []
    lines.append("# Promotion Protection Counterfactual -- Research Report")
    lines.append("")
    lines.append("Research-only. No orders, no backtest engine, no live trading.")
    lines.append("")
    if proxy_mode:
        lines.append("> MODE: PROXY (jqdata unavailable). Forward paths were not")
        lines.append("> fetched; only pv_immediate_full_exit is meaningful. All")
        lines.append("> other variants report captured_extra_return = 0. Re-run")
        lines.append("> inside JoinQuant research for real path-dependent results.")
    else:
        lines.append("> MODE: JQDATA. MA5 exit variants use closing prices and are")
        lines.append("> reliable under the close proxy (proxy_distortion_flag=low).")
    lines.append("")
    lines.append("> CLOSE_PROXY DISTORTION (trail class): pv_trail_from_high uses")
    lines.append("> daily high, which misses intraday peaks. Its results are")
    lines.append("> RANKING-ONLY, NOT tradeable (proxy_distortion_flag=high).")
    lines.append("")
    lines.append("## Concentration recompute by variant")
    lines.append("")
    lines.append("Baseline net pnl is 59822. Top5 already exceeds net (118%),")
    lines.append("so net_excl_top5 is THE robustness column: watch net_excl_top5,")
    lines.append("NOT net_pnl. A variant that pushes net_excl_top5 MORE NEGATIVE")
    lines.append("worsens fragility and is penalized -- however pretty its meat-")
    lines.append("grabbing looks. A variant is attractive only if it lifts")
    lines.append("net_excl_top5 (broadens the profit base).")
    lines.append("")
    header = ("| variant | net_pnl | top5 | top5_share_of_net "
              "| net_excl_top5 | proxy_distortion_flag |")
    lines.append(header)
    lines.append("|---|---|---|---|---|---|")
    for _, r in conc_df.iterrows():
        lines.append(
            "| {0} | {1:.0f} | {2:.0f} | {3:.3f} | {4:.0f} | {5} |".format(
                r["variant"], r["net_pnl"], r["top5"],
                r["top5_share_of_net"], r["net_excl_top5"],
                r["proxy_distortion_flag"]
            )
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 10. Entry point.
# ---------------------------------------------------------------------------

def main():
    _ensure_out_dir()
    knobs = default_knobs()
    paths = _fetch_all_paths()
    proxy_mode = all(v is None for v in paths.values())

    cases_df = build_variant_event_matrix(paths, knobs)
    summary_df = build_concentration_recompute(paths, knobs)
    sens_df = build_sensitivity_grid(paths)

    cases_path = os.path.join(OUT_DIR, OUT_CASES)
    summary_path = os.path.join(OUT_DIR, OUT_SUMMARY)
    sens_path = os.path.join(OUT_DIR, OUT_SENSITIVITY)
    report_path = os.path.join(OUT_DIR, OUT_REPORT)

    cases_df.to_csv(cases_path, index=False, encoding="utf-8")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    sens_df.to_csv(sens_path, index=False, encoding="utf-8")

    report_text = write_report(summary_df, proxy_mode)
    with open(report_path, "w") as f:
        f.write(report_text)

    # Bundle outputs. zip stores file names only, no directory prefix.
    zip_path = os.path.join(OUT_DIR, OUT_ZIP)
    member_paths = [cases_path, summary_path, sens_path, report_path]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in member_paths:
            zf.write(p, arcname=os.path.basename(p))

    print("proxy_mode =", proxy_mode)
    for p in member_paths + [zip_path]:
        print("wrote:", p)


if __name__ == "__main__":
    main()
