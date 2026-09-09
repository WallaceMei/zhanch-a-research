# -*- coding: utf-8 -*-
#
# factor_seg1_jq_bare_signal_ic.py
#
# Segment 1 of the factor-validation line (research-only).
# Goal: for the 2067 WATCH_POOL_ADD deep_water signals, fetch T+1/3/5/10/20
# forward prices in JoinQuant, then quantify the BARE signal:
#   - forward IC of signal_score vs forward return (Spearman + Pearson)
#   - score-layer (quintile + high/low half) mean forward returns
#   - per-year IC (2023/24/25/26) to check cross-year consistency
#   - ALL returns also expressed as EXCESS vs CSI1000 (000852.XSHG),
#     because the portfolio-level excess is -5.38% and absolute returns
#     are polluted by market beta.
#
# HARD CONSTRAINTS (do not relax):
#   - NO orders / order_value / order_target / run_backtest / schedule_function.
#   - get_price MUST NOT pass start_date and count together (JoinQuant rule).
#     We resolve explicit [start,end] windows via the trade calendar first.
#   - Look-ahead safe: signal day T uses only <=T info (signal_score from log);
#     forward returns use ONLY T+1..T+20 closes (strictly after T).
#   - All paths RELATIVE. Python 3.6 compatible. Code region pure ASCII.
#
# Run location: JoinQuant research notebook (jqdata available). Upload both
#   this script and jq_factor_signal_universe.csv into the same working dir.
# Local: this file only gets syntax+encoding checked (py_compile). Real prices
#   are fetched when the user runs it inside JoinQuant. NO local jqdata faking.
#
# This segment does NOT emit a VERDICT and does NOT test the confirm chain.

import os
import zipfile

import numpy as np
import pandas as pd

try:
    from jqdata import *  # noqa: F401,F403
    _HAS_JQDATA = True
except Exception:
    _HAS_JQDATA = False


# ---------------------------------------------------------------------------
# 0. Config (relative paths only).
# ---------------------------------------------------------------------------

IN_UNIVERSE = "jq_factor_signal_universe.csv"

OUT_DIR = "factor_seg1_outputs"
OUT_FWD = "jq_factor_seg1_signal_forward.csv"
OUT_IC = "jq_factor_seg1_ic_summary.csv"
OUT_LAYER = "jq_factor_seg1_score_layer.csv"
OUT_REPORT = "jq_factor_seg1_report.md"
OUT_ZIP = "factor_seg1_outputs.zip"

BENCH = "000852.XSHG"          # CSI 1000 index
HORIZONS = [1, 3, 5, 10, 20]   # forward trade-day horizons
MAX_H = max(HORIZONS)
# Calendar end cap: must cover T+20 of the latest signal (2026-06-18).
CAL_END_CAP = "2026-08-31"
N_QUANTILE = 5                 # score-layer quantiles


def _ensure_out_dir():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)


# ---------------------------------------------------------------------------
# 1. Load the signal universe (produced locally from the authoritative log).
# ---------------------------------------------------------------------------

def load_universe():
    df = pd.read_csv(IN_UNIVERSE, encoding="utf-8")
    df["stock"] = df["stock"].astype(str)
    df["signal_date"] = df["signal_date"].astype(str).str[:10]
    df["signal_price"] = pd.to_numeric(df["signal_price"], errors="coerce")
    df["signal_score"] = pd.to_numeric(df["signal_score"], errors="coerce")
    df["signal_rank"] = pd.to_numeric(df.get("signal_rank", 0), errors="coerce")
    df["year"] = df["signal_date"].str[:4]
    df = df.dropna(subset=["signal_price", "signal_score"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. Trade calendar + index series (each fetched ONCE; get_price never gets
#    start_date and count together).
# ---------------------------------------------------------------------------

def build_calendar(min_date):
    """Full trade-day list [min_date .. CAL_END_CAP] as 'YYYY-MM-DD' strings,
    plus a position map for O(1) T -> T+k lookups. Future (untraded) calendar
    days are included by the exchange calendar; their prices will be missing
    and get flagged downstream."""
    days = get_trade_days(start_date=min_date, end_date=CAL_END_CAP)
    cal = [str(d)[:10] for d in days]
    pos = dict((d, i) for i, d in enumerate(cal))
    return cal, pos


def fetch_index_close(min_date):
    """CSI1000 daily close over the whole span, ONE call (start+end, no count).
    Returns date_str -> close."""
    df = get_price(
        BENCH, start_date=min_date, end_date=CAL_END_CAP,
        frequency="daily", fields=["close"], skip_paused=False,
    )
    out = {}
    for idx, val in zip(df.index, df["close"].values):
        out[str(idx)[:10]] = float(val)
    return out


def _resolve_T_pos(signal_date, cal, pos):
    """Position of the signal trade day T in the calendar. If signal_date is a
    trade day use it; else the first trade day >= signal_date."""
    if signal_date in pos:
        return pos[signal_date]
    for i, d in enumerate(cal):
        if d >= signal_date:
            return i
    return None


# ---------------------------------------------------------------------------
# 3. Batched forward-price fetch: one get_price per unique signal_date, pulling
#    the whole basket of that day's stocks over [T .. T+MAX_H]. This keeps the
#    number of get_price calls ~= number of unique signal_dates (hundreds),
#    NOT 2067 single-stock loops.
# ---------------------------------------------------------------------------

def _basket_panel(stocks, start_str, end_str):
    """get_price for a list of stocks over [start,end] (no count). Returns
    closes: stock -> {date_str: close} and paused: stock -> {date_str: paused}.

    Column roles are detected BY VALUE, not by name: the code column is the one
    whose values match '*.XSHE/.XSHG' and the date column is the one whose values
    are date-like. This avoids the earlier bug where a numeric 'index' column
    (added by reset_index) was mistaken for the date column -> every date key
    became a row number -> 100% no_base_price."""
    closes = {}
    paused = {}
    try:
        df = get_price(
            stocks, start_date=start_str, end_date=end_str,
            frequency="daily", fields=["close", "paused"],
            skip_paused=False, fq="pre", panel=False,
        )
    except TypeError:
        # Older API without panel kw: fall back to default return shape.
        df = get_price(
            stocks, start_date=start_str, end_date=end_str,
            frequency="daily", fields=["close", "paused"],
            skip_paused=False, fq="pre",
        )
    if df is None or len(df) == 0:
        return closes, paused
    work = df
    if not isinstance(work.index, pd.RangeIndex):
        work = work.reset_index()
    cols = list(work.columns)
    # code column: values look like 'XXXXXX.XSHE' / 'XXXXXX.XSHG'
    code_col = None
    for c in cols:
        if work[c].astype(str).str.contains(r"\.XSH", regex=True).any():
            code_col = c
            break
    # date column: first non-code column whose values are date-like
    time_col = None
    for c in cols:
        if c == code_col:
            continue
        s = work[c].dropna()
        if len(s) == 0:
            continue
        v = s.iloc[0]
        if hasattr(v, "year") or (isinstance(v, str) and len(v) >= 8 and "-" in v):
            time_col = c
            break
    if time_col is None:
        return closes, paused
    single = (code_col is None)
    only_stock = stocks[0] if (single and len(stocks) >= 1) else None
    have_close = "close" in cols
    have_paused = "paused" in cols
    for _, row in work.iterrows():
        st = only_stock if single else str(row[code_col])
        dt = str(row[time_col])[:10]
        cv = row["close"] if have_close else np.nan
        pv = row["paused"] if have_paused else 0
        closes.setdefault(st, {})[dt] = float(cv) if pd.notnull(cv) else np.nan
        paused.setdefault(st, {})[dt] = int(pv) if pd.notnull(pv) else 0
    return closes, paused


def compute_forward(uni, cal, pos, idx_close):
    """For each signal, compute abs and excess forward returns at each horizon.
    Base = close[T] (fq=pre, internally consistent and split/dividend-safe);
    signal_price kept only for a QC gap flag."""
    rows = []
    # Group signals by signal_date for batched fetching.
    for sd, grp in uni.groupby("signal_date"):
        T_pos = _resolve_T_pos(sd, cal, pos)
        if T_pos is None or T_pos + 1 >= len(cal):
            for _, s in grp.iterrows():
                rows.append(_empty_row(s, "no_calendar"))
            continue
        T = cal[T_pos]
        end_pos = min(T_pos + MAX_H, len(cal) - 1)
        end_d = cal[end_pos]
        stocks = sorted(set(grp["stock"].tolist()))
        try:
            closes, paused = _basket_panel(stocks, T, end_d)
        except Exception:
            for _, s in grp.iterrows():
                rows.append(_empty_row(s, "fetch_error"))
            continue
        # index base at T
        idx_T = idx_close.get(T, np.nan)
        for _, s in grp.iterrows():
            st = s["stock"]
            cmap = closes.get(st, {})
            pmap = paused.get(st, {})
            base = cmap.get(T, np.nan)
            row = {
                "stock": st, "signal_date": sd, "year": s["year"],
                "signal_score": s["signal_score"], "signal_rank": s["signal_rank"],
                "signal_price": s["signal_price"], "close_T": base,
                "base_gap_vs_signal_price": (base / s["signal_price"] - 1.0)
                if (pd.notnull(base) and s["signal_price"]) else np.nan,
                "data_quality_flag": "ok",
            }
            if (not pd.notnull(base)) or base <= 0 or int(pmap.get(T, 0)) == 1:
                row["data_quality_flag"] = "no_base_price"
            for k in HORIZONS:
                tk_pos = T_pos + k
                abs_k = np.nan
                exc_k = np.nan
                qual = ""
                if tk_pos >= len(cal):
                    qual = "insufficient_forward_days"
                else:
                    tk = cal[tk_pos]
                    ck = cmap.get(tk, np.nan)
                    if row["data_quality_flag"] == "no_base_price":
                        qual = "no_base_price"
                    elif (not pd.notnull(ck)) or ck <= 0:
                        qual = "missing_forward_close"
                    elif int(pmap.get(tk, 0)) == 1:
                        qual = "paused_at_horizon"
                    else:
                        abs_k = ck / base - 1.0
                        idx_tk = idx_close.get(tk, np.nan)
                        if pd.notnull(idx_T) and pd.notnull(idx_tk) and idx_T > 0:
                            exc_k = abs_k - (idx_tk / idx_T - 1.0)
                        else:
                            qual = "missing_bench"
                row["abs_ret_%d" % k] = abs_k
                row["exc_ret_%d" % k] = exc_k
                row["flag_%d" % k] = qual
            rows.append(row)
    return pd.DataFrame(rows)


def _empty_row(s, flag):
    row = {
        "stock": s["stock"], "signal_date": s["signal_date"], "year": s["year"],
        "signal_score": s["signal_score"], "signal_rank": s["signal_rank"],
        "signal_price": s["signal_price"], "close_T": np.nan,
        "base_gap_vs_signal_price": np.nan, "data_quality_flag": flag,
    }
    for k in HORIZONS:
        row["abs_ret_%d" % k] = np.nan
        row["exc_ret_%d" % k] = np.nan
        row["flag_%d" % k] = flag
    return row


# ---------------------------------------------------------------------------
# 4. IC (Spearman rank IC + Pearson) of signal_score vs forward return.
# ---------------------------------------------------------------------------

def _corr(a, b, method):
    sa = pd.Series(np.asarray(a, dtype=float))
    sb = pd.Series(np.asarray(b, dtype=float))
    if sa.notnull().sum() < 5 or sb.notnull().sum() < 5:
        return float("nan")
    try:
        return float(sa.corr(sb, method=method))
    except Exception:
        return float("nan")


def build_ic_summary(fwd):
    scopes = ["all", "2023", "2024", "2025", "2026"]
    rows = []
    for scope in scopes:
        sub = fwd if scope == "all" else fwd[fwd["year"] == scope]
        for k in HORIZONS:
            for basis in ["exc", "abs"]:
                col = "%s_ret_%d" % (basis, k)
                v = sub[["signal_score", col]].dropna()
                rows.append({
                    "scope": scope, "horizon": k, "basis": basis,
                    "n": int(len(v)),
                    "ic_spearman": _corr(v["signal_score"], v[col], "spearman"),
                    "ic_pearson": _corr(v["signal_score"], v[col], "pearson"),
                    "mean_ret": float(v[col].mean()) if len(v) else float("nan"),
                })
    cols = ["scope", "horizon", "basis", "n", "ic_spearman", "ic_pearson", "mean_ret"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 5. Score layer: quintiles + high/low half, mean forward return per horizon.
#    Reported per scope (all + each year) for excess and absolute.
# ---------------------------------------------------------------------------

def build_score_layer(fwd):
    rows = []
    scopes = ["all", "2023", "2024", "2025", "2026"]
    for scope in scopes:
        sub = fwd if scope == "all" else fwd[fwd["year"] == scope]
        if len(sub) < N_QUANTILE * 2:
            continue
        score = sub["signal_score"]
        # Quintile labels by score (low rank 0 -> high rank N-1).
        try:
            q = pd.qcut(score.rank(method="first"), N_QUANTILE, labels=False)
        except Exception:
            continue
        half = (score >= score.median()).map({True: "high_half", False: "low_half"})
        for k in HORIZONS:
            for basis in ["exc", "abs"]:
                col = "%s_ret_%d" % (basis, k)
                # quintiles
                for ql in range(N_QUANTILE):
                    vals = sub.loc[q == ql, col].dropna()
                    rows.append({
                        "scope": scope, "group_type": "quintile",
                        "group_label": "Q%d" % (ql + 1), "horizon": k,
                        "basis": basis, "n": int(len(vals)),
                        "mean_ret": float(vals.mean()) if len(vals) else float("nan"),
                    })
                # top-bottom spread (Q5 - Q1)
                top = sub.loc[q == N_QUANTILE - 1, col].dropna()
                bot = sub.loc[q == 0, col].dropna()
                rows.append({
                    "scope": scope, "group_type": "quintile",
                    "group_label": "Q5_minus_Q1", "horizon": k, "basis": basis,
                    "n": int(min(len(top), len(bot))),
                    "mean_ret": (float(top.mean()) - float(bot.mean()))
                    if (len(top) and len(bot)) else float("nan"),
                })
                # halves
                for hl in ["high_half", "low_half"]:
                    vals = sub.loc[half == hl, col].dropna()
                    rows.append({
                        "scope": scope, "group_type": "half",
                        "group_label": hl, "horizon": k, "basis": basis,
                        "n": int(len(vals)),
                        "mean_ret": float(vals.mean()) if len(vals) else float("nan"),
                    })
    cols = ["scope", "group_type", "group_label", "horizon", "basis", "n", "mean_ret"]
    return pd.DataFrame(rows)[cols]


# ---------------------------------------------------------------------------
# 6. Report (descriptive only; NO verdict, NO confirm-chain test).
# ---------------------------------------------------------------------------

def write_report(uni, fwd, ic):
    lines = []
    lines.append("# Factor Validation Segment 1 -- Bare Signal Forward IC")
    lines.append("")
    lines.append("Research-only. No orders, no backtest, no main-strategy change.")
    lines.append("Forward returns are EXCESS vs CSI1000 (000852.XSHG) unless noted.")
    lines.append("Base price = close[T] (fq=pre); look-ahead safe (T+1..T+20 only).")
    lines.append("This segment emits NO verdict and does NOT test the confirm chain.")
    lines.append("")
    lines.append("Signals loaded: %d" % len(uni))
    by_year = uni.groupby("year").size()
    lines.append("By year: " + ", ".join("%s=%d" % (y, n) for y, n in by_year.items()))
    lines.append("")
    # coverage / data quality
    n_ok = int((fwd["data_quality_flag"] == "ok").sum())
    lines.append("Rows with usable base price: %d / %d" % (n_ok, len(fwd)))
    for k in HORIZONS:
        good = int(fwd["exc_ret_%d" % k].notnull().sum())
        lines.append("  horizon T+%d: usable excess returns = %d" % (k, good))
    lines.append("")
    lines.append("## Excess IC by horizon (scope=all)")
    lines.append("")
    lines.append("| horizon | n | IC_spearman | IC_pearson | mean_excess |")
    lines.append("|---|---|---|---|---|")
    sub = ic[(ic["scope"] == "all") & (ic["basis"] == "exc")]
    for _, r in sub.iterrows():
        lines.append("| T+%d | %d | %.4f | %.4f | %+.4f |" % (
            r["horizon"], r["n"], r["ic_spearman"], r["ic_pearson"], r["mean_ret"]))
    lines.append("")
    lines.append("## Excess IC_spearman by year (consistency check)")
    lines.append("")
    lines.append("| horizon | 2023 | 2024 | 2025 | 2026 |")
    lines.append("|---|---|---|---|---|")
    for k in HORIZONS:
        cells = []
        for y in ["2023", "2024", "2025", "2026"]:
            r = ic[(ic["scope"] == y) & (ic["basis"] == "exc") & (ic["horizon"] == k)]
            cells.append("%.4f" % r["ic_spearman"].values[0] if len(r) else "na")
        lines.append("| T+%d | %s |" % (k, " | ".join(cells)))
    lines.append("")
    lines.append("See jq_factor_seg1_ic_summary.csv (abs+exc, all scopes) and")
    lines.append("jq_factor_seg1_score_layer.csv (quintile/half means) for detail.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. Entry point.
# ---------------------------------------------------------------------------

def main():
    _ensure_out_dir()
    uni = load_universe()

    if not _HAS_JQDATA:
        print("jqdata NOT available -> run this inside JoinQuant research.")
        print("Universe rows loaded =", len(uni))
        print("Unique signal_dates  =", uni["signal_date"].nunique())
        print("No prices fetched (no local jqdata faking). Exiting.")
        return

    min_date = uni["signal_date"].min()
    cal, pos = build_calendar(min_date)
    idx_close = fetch_index_close(min_date)

    fwd = compute_forward(uni, cal, pos, idx_close)
    ic = build_ic_summary(fwd)
    layer = build_score_layer(fwd)

    fwd_path = os.path.join(OUT_DIR, OUT_FWD)
    ic_path = os.path.join(OUT_DIR, OUT_IC)
    layer_path = os.path.join(OUT_DIR, OUT_LAYER)
    report_path = os.path.join(OUT_DIR, OUT_REPORT)

    fwd.to_csv(fwd_path, index=False, encoding="utf-8")
    ic.to_csv(ic_path, index=False, encoding="utf-8")
    layer.to_csv(layer_path, index=False, encoding="utf-8")
    with open(report_path, "w") as f:
        f.write(write_report(uni, fwd, ic))

    zip_path = os.path.join(OUT_DIR, OUT_ZIP)
    members = [fwd_path, ic_path, layer_path, report_path]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in members:
            zf.write(p, arcname=os.path.basename(p))

    print("done. wrote:")
    for p in members + [zip_path]:
        print("  ", p)


if __name__ == "__main__":
    main()
