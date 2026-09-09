# -*- coding: utf-8 -*-
#
# diag_seg1_pricecheck.py  --  price-fetch diagnostic for factor seg1.
#
# Purpose: BEFORE re-running the full 2067 batch, prove get_price actually
# returns real closes in THIS JoinQuant research environment, and SHOW the
# exact return shape (index / columns / dtypes) so the batch parser can be
# trusted. Run this in JoinQuant research; read the printout.
#
# Research-only. No orders, no backtest. get_price never gets start+count.
# Python 3.6 / pure ASCII.

import numpy as np
import pandas as pd

try:
    from jqdata import *  # noqa: F401,F403
    _HAS_JQDATA = True
except Exception:
    _HAS_JQDATA = False


TEST_STOCK = "002251.XSHE"
TEST_DATE = "2023-01-03"
BASKET = ["002251.XSHE", "600187.XSHG"]


def _window(center, back, fwd):
    """[start,end] spanning `back` trade days before center .. `fwd` after.
    Endpoints via get_trade_days(count=...); get_price later gets NO count."""
    pre = get_trade_days(end_date=center, count=back + 1)
    post = get_trade_days(start_date=center, count=fwd + 1)
    return str(pre[0])[:10], str(post[-1])[:10]


def _show(tag, df):
    print("---- %s ----" % tag)
    print("type        :", type(df))
    print("index type  :", type(df.index), "| name:", getattr(df.index, "name", None))
    print("index[:3]   :", list(df.index[:3]))
    print("columns     :", list(df.columns))
    print("dtypes      :\n", df.dtypes)
    print("head(6)     :\n", df.head(6))
    print()


def main():
    print("HAS_JQDATA =", _HAS_JQDATA)
    if not _HAS_JQDATA:
        print("Run inside JoinQuant research. Aborting (no local price faking).")
        return

    start, end = _window(TEST_DATE, 4, 22)
    print("resolved window: start=%s end=%s\n" % (start, end))

    # (1) single stock, close only
    s1 = get_price(TEST_STOCK, start_date=start, end_date=end,
                   frequency="daily", fields=["close"],
                   skip_paused=False, fq="pre")
    _show("single / fields=[close] / fq=pre", s1)

    # (2) single stock, close+paused
    try:
        s2 = get_price(TEST_STOCK, start_date=start, end_date=end,
                       frequency="daily", fields=["close", "paused"],
                       skip_paused=False, fq="pre")
        _show("single / fields=[close,paused]", s2)
    except Exception as e:
        print("single close+paused ERROR:", repr(e), "\n")

    # (3) basket, panel=False (this is what the batch uses)
    try:
        b = get_price(BASKET, start_date=start, end_date=end,
                      frequency="daily", fields=["close", "paused"],
                      skip_paused=False, fq="pre", panel=False)
        _show("basket / panel=False", b)
    except TypeError:
        b = get_price(BASKET, start_date=start, end_date=end,
                      frequency="daily", fields=["close", "paused"],
                      skip_paused=False, fq="pre")
        _show("basket / NO panel kw (fallback)", b)

    # (4) apply the VALUE-BASED parser used by the fixed batch and print result
    closes, paused = parse_basket(b, BASKET)
    print("==== parser output ====")
    for st in BASKET:
        cm = closes.get(st, {})
        ks = sorted(cm.keys())
        print("stock", st, "-> n_dates =", len(ks))
        for d in ks[:4]:
            print("    ", d, "close=", cm[d], "paused=", paused.get(st, {}).get(d))
    print()
    base = closes.get(TEST_STOCK, {}).get(start_trade_day(start, TEST_DATE))
    print("SANITY: a real close should print above (not empty). If n_dates>0 and")
    print("close values are floats, batch fetch is FIXED. If empty -> show this")
    print("printout so we read the real shape.")


def start_trade_day(start, center):
    # The first trade day >= center within the window (T).
    days = get_trade_days(start_date=center, count=1)
    return str(days[0])[:10]


def parse_basket(df, stocks):
    """VALUE-based column detection (no reliance on column NAMES, so a stray
    numeric 'index' column from reset_index cannot be mistaken for the date)."""
    closes, paused = {}, {}
    if df is None or len(df) == 0:
        return closes, paused
    work = df
    if not isinstance(work.index, pd.RangeIndex):
        work = work.reset_index()
    cols = list(work.columns)
    code_col = None
    for c in cols:
        if work[c].astype(str).str.contains(r"\.XSH", regex=True).any():
            code_col = c
            break
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
        print("WARN: no date-like column found; columns =", cols)
        return closes, paused
    single = (code_col is None)
    only = stocks[0] if single else None
    for _, row in work.iterrows():
        st = only if single else str(row[code_col])
        dt = str(row[time_col])[:10]
        cv = row["close"] if "close" in cols else np.nan
        pv = row["paused"] if "paused" in cols else 0
        closes.setdefault(st, {})[dt] = float(cv) if pd.notnull(cv) else np.nan
        paused.setdefault(st, {})[dt] = int(pv) if pd.notnull(pv) else 0
    return closes, paused


if __name__ == "__main__":
    main()
