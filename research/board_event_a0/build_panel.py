# -*- coding: utf-8 -*-
#
# build_panel.py -- 打板事件模块 A0 / Gate0: 事件面板
#
# 按主 Spec + 调整说明:C分层(首板/连板)+B扩展池(含冲板失败/炸板负样本);
# 收益从 T+1 open 起算(主 T+3,辅 T+1/2/5);防泄漏;只用现有 features.parquet(2024-2025)。
# 不接 194 全量、不做 Gate2/3/4、不碰 2026 调参、不标 robust_alpha。
# 环境 .venv_court。本步只建面板 + 事件池/收益对齐自检,不算 IC(Gate1)。

import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

FEATURES = r"C:\quant_project\features.parquet"
OUT_DIR  = r"D:\Code\JQ\战车A\research\board_event_a0"
DEV_START, DEV_END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")  # 开发验证;事件日限定此区间
# 读取多带前后文:前缀给 prev_consec/pre_close,后缀给 T+5 forward(可溢入2026仅作标签,不调参)
LOAD_START, LOAD_END = pd.Timestamp("2023-07-01"), pd.Timestamp("2026-04-03")

def limit_rate(ts_code, name):
    nm = "" if name is None else str(name)
    code = str(ts_code)
    if ("ST" in nm) or ("退" in nm):
        return 0.05
    head = code[:3]
    if head == "688" or code[:2] == "30":
        return 0.20
    if code[:1] in ("8","4"):   # 北交所(features 大概率无)
        return 0.30
    return 0.10

def trailing_consec(sealed):
    """previous_consecutive_limit_days: 截至 T-1 的连续 sealed_limit 天数。"""
    out = np.zeros(len(sealed), dtype=int)
    run = 0
    for i in range(len(sealed)):
        out[i] = run            # 用 T-1 的累计(本行先记,再更新)
        run = run + 1 if sealed[i] else 0
    return out

def main():
    if not os.path.exists(OUT_DIR): os.makedirs(OUT_DIR)
    cols = ["ts_code","trade_date","name","open","high","low","close",
            "open_adj","close_adj","pct_chg","vol"]
    df = pq.read_table(FEATURES, columns=cols).to_pandas()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df[(df.trade_date>=LOAD_START)&(df.trade_date<=LOAD_END)]
    df = df.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    print("[load] rows=%d stocks=%d %s..%s" % (len(df), df.ts_code.nunique(),
          df.trade_date.min().date(), df.trade_date.max().date()))

    g = df.groupby("ts_code", sort=False)
    df["pre_close"] = g["close"].shift(1)
    df["rate"] = [limit_rate(c,n) for c,n in zip(df.ts_code, df.name)]
    df["limit_up_price"] = (df["pre_close"]*(1.0+df["rate"])).round(2)

    lp = df["limit_up_price"]
    pc = pd.to_numeric(df["pct_chg"], errors="coerce")  # 百分比
    df["sealed_limit"] = (df["close"] >= lp*0.995) & lp.notna()
    df["limit_touch"]  = (df["high"]  >= lp*0.995) & lp.notna()
    df["near_limit"]   = ((pc >= 7.0) | (df["close"] >= lp*0.97)) & lp.notna()
    df["failed_board"] = df["limit_touch"] & (~df["sealed_limit"])
    df["event_pool_all"] = ((pc >= 7.0) | (df["high"]>=lp*0.995) | (df["close"]>=lp*0.995)) & lp.notna()

    # previous_consecutive_limit_days
    df["previous_consecutive_limit_days"] = (
        g["sealed_limit"].transform(lambda s: trailing_consec(s.values)))
    df["first_board_pool"] = df["event_pool_all"] & (df["previous_consecutive_limit_days"]==0)
    df["multi_board_pool"] = df["event_pool_all"] & (df["previous_consecutive_limit_days"]>=1)

    # 质量/可交易标记
    df["is_st"] = df["name"].astype(str).str.contains(r"ST|\*ST|退", regex=True, na=False)
    df["is_paused"] = (df["vol"].fillna(0)<=0) | df["close"].isna()
    df["is_one_price_limit"] = (df["open"]>=lp*0.995) & (df["low"]>=lp*0.995) & lp.notna()  # 一字板
    # tradable_next_open: T+1 是否一开盘就封死(用 T+1 open vs T+1 涨停价=round(close[T]*(1+rate)))
    nxt_open = g["open"].shift(-1); nxt_open_adj = g["open_adj"].shift(-1)
    nxt_limit = (df["close"]*(1.0+df["rate"])).round(2)
    df["tradable_next_open"] = nxt_open.notna() & (nxt_open < nxt_limit*0.995)

    # 前向收益: T+1 open 起算(用复权价,防除权失真;标签可溢入2026)
    o1 = g["open_adj"].shift(-1)
    c1 = g["close_adj"].shift(-1); c2 = g["close_adj"].shift(-2)
    c3 = g["close_adj"].shift(-3); c5 = g["close_adj"].shift(-5)
    df["fwd_return_T1open_to_T1close"] = c1/o1 - 1.0
    df["fwd_return_T1open_to_T2close"] = c2/o1 - 1.0
    df["fwd_return_T1open_to_T3close"] = c3/o1 - 1.0
    df["fwd_return_T1open_to_T5close"] = c5/o1 - 1.0

    # 只保留开发区间事件日的行(事件池内),其余丢弃
    panel = df[df.event_pool_all & (df.trade_date>=DEV_START) & (df.trade_date<=DEV_END)].copy()
    keep = ["trade_date","ts_code","name","open","high","low","close","pre_close","pct_chg",
            "rate","limit_up_price","event_pool_all","first_board_pool","multi_board_pool",
            "sealed_limit","limit_touch","near_limit","failed_board",
            "previous_consecutive_limit_days","is_st","is_paused","is_one_price_limit",
            "tradable_next_open",
            "fwd_return_T1open_to_T1close","fwd_return_T1open_to_T2close",
            "fwd_return_T1open_to_T3close","fwd_return_T1open_to_T5close"]
    panel = panel[keep].rename(columns={"trade_date":"date","ts_code":"code"})
    panel.to_parquet(os.path.join(OUT_DIR,"board_event_panel.parquet"), index=False)
    print("[panel] 事件行=%d (2024-2025) 股票=%d 日期=%s..%s" % (
        len(panel), panel.code.nunique(), panel.date.min().date(), panel.date.max().date()))

    # ---- 自检 10.1 事件池(抽查若干日) ----
    print("\n=== 自检10.1 事件池(抽查5日)===")
    days = sorted(panel.date.unique())
    import numpy as _np
    pick = [days[int(x)] for x in _np.linspace(0, len(days)-1, 5)]
    for d in pick:
        s = panel[panel.date==d]
        print("  %s | event=%d sealed=%d failed=%d first=%d multi=%d" % (
            pd.Timestamp(d).date(), len(s), s.sealed_limit.sum(), s.failed_board.sum(),
            s.first_board_pool.sum(), s.multi_board_pool.sum()))
    # 整体统计
    print("\n事件池总计: event=%d sealed=%d(%.0f%%) failed=%d first=%d multi=%d 一字板=%d ST=%d" % (
        len(panel), panel.sealed_limit.sum(), 100*panel.sealed_limit.mean(),
        panel.failed_board.sum(), panel.first_board_pool.sum(), panel.multi_board_pool.sum(),
        panel.is_one_price_limit.sum(), panel.is_st.sum()))
    print("每日事件池规模: 中位=%d 均值=%.0f 最大=%d 天数=%d" % (
        int(panel.groupby('date').size().median()), panel.groupby('date').size().mean(),
        int(panel.groupby('date').size().max()), panel.date.nunique()))
    for pool in ["first_board_pool","multi_board_pool"]:
        sz = panel[panel[pool]].groupby("date").size()
        print("  %s 每日规模中位=%d (>=阈值天数见Gate1)" % (pool, int(sz.median()) if len(sz) else 0))

    # ---- 自检 10.2 收益对齐(抽查样本,打印 T close / T+1 open / T+3 close / 收益)----
    print("\n=== 自检10.2 收益对齐(抽查3样本,复权价)===")
    chk = panel[panel.fwd_return_T1open_to_T3close.notna()].head(3)
    # 取回这些样本的复权价确认
    for _,r in chk.iterrows():
        sub = df[(df.ts_code==r.code)].sort_values("trade_date").reset_index(drop=True)
        pos = sub.index[sub.trade_date==r.date][0]
        t1o = sub.open_adj.iloc[pos+1] if pos+1<len(sub) else np.nan
        t3c = sub.close_adj.iloc[pos+3] if pos+3<len(sub) else np.nan
        calc = t3c/t1o-1.0
        print("  %s %s | T close_adj=%.3f T+1 open_adj=%.3f T+3 close_adj=%.3f | 面板值=%.4f 复算=%.4f 一致=%s" % (
            r.code, pd.Timestamp(r.date).date(), sub.close_adj.iloc[pos], t1o, t3c,
            r.fwd_return_T1open_to_T3close, calc, abs(calc-r.fwd_return_T1open_to_T3close)<1e-6))
    miss = panel.fwd_return_T1open_to_T3close.isna().sum()
    print("\nT+3 收益缺失行(末端/停牌): %d / %d (末端2025-12事件正常缺T+3)" % (miss, len(panel)))

if __name__ == "__main__":
    main()
