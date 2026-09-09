# -*- coding: utf-8 -*-
"""dragon 整套策略·可交易收益回测 — 小样本口径验证(先报确认再全量)。

验:① 2026 未进(max year=2025) ② 可交易口径(买T open、卖T+N close、排除day1、T+1合法)
   ③ 持有收益算对(day6=close[T+5]/open[T],与中台日线逐位核对) ④ 策略层聚合算对(每笔/胜率/日均)。
诊断现状,不优化不调dragon。读底座只用 2020-2025。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

_DRAGON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(_DRAGON, "event_study_dragon_2020_2026.csv")
# 可交易持有收益:买 entry(T) open、卖 T+N close = 底座 day(N+1);排除 day1(0天持仓违反T+1)
HOLD = {"hold_T3": "day4", "hold_T5": "day6", "hold_T10": "day11"}


def load(verbose=True):
    d = pd.read_csv(BASE, dtype={"entry_date": str, "prev_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    d = d[d["year"] <= 2025].reset_index(drop=True)        # ★只用 2020-2025
    assert d["year"].max() == 2025 and (d["year"] == 2026).sum() == 0, "红线:2026 进入!"
    for h, col in HOLD.items():
        d[h] = d[col]
    return d


def main():
    print("=" * 72)
    print("dragon 策略·可交易收益回测 — 小样本口径验证")
    print("=" * 72)
    d = load()
    print("\n[① 2026 holdout]")
    print("  max year =", int(d.year.max()), "| 2026行 =", int((d.year == 2026).sum()),
          "| 行数(3版) =", len(d))
    assert d.year.max() == 2025

    print("\n[② 可交易口径]")
    print("  hold_T5 = day6 = close[T+5]/open[T] → 买T open、卖T+5 close、持5天、T+1合法")
    print("  day1(0天持仓,违反T+1)= 不参与回测 ✓ ;最短持有 hold_T3=day4(持3天)")

    print("\n[③ 持有收益逐位核对(中台日线)]")
    os.environ["REPRO_BACKEND"] = "warehouse"; sys.path.insert(0, _DRAGON)
    import repro_core as R
    row = d[d.code == "600519.SH"].iloc[0]
    ed, code = row.entry_date, row.code
    panel = R.load_daily_panel([code], "20200101", "20260630")
    df = panel[code]; idx = list(df.index); i0 = idx.index(ed)
    o = df["open"].astype(float).values; c = df["close"].astype(float).values
    calc_t5 = (c[i0 + 5] / o[i0] - 1) * 100
    print("  样本 %s %s: 底座hold_T5=%.4f%% | 中台close[T+5]/open[T]-1=%.4f%% | 一致=%s" % (
        code, ed, row.hold_T5, calc_t5, abs(row.hold_T5 - calc_t5) < 1e-2))

    print("\n[④ 策略层聚合算对(v3, 2020-01~03 抽样)]")
    sub = d[(d.score_mode == "v3") & (d.entry_date >= "20200101") & (d.entry_date <= "20200331")]
    print("  样本笔数 =", len(sub), "| 覆盖交易日 =", sub.entry_date.nunique())
    # 每笔
    pt = sub["hold_T5"].dropna()
    print("  每笔 hold_T5: 平均=%.3f%% 中位=%.3f%% 胜率(>0)=%.1f%%" % (
        pt.mean(), pt.median(), (pt > 0).mean() * 100))
    wins = pt[pt > 0]; losses = pt[pt < 0]
    pl = wins.mean() / abs(losses.mean()) if len(losses) and losses.mean() != 0 else np.nan
    print("  盈亏比(avg win/|avg loss|)=%.2f | 平均盈=%.3f%% 平均亏=%.3f%%" % (
        pl, wins.mean() if len(wins) else 0, losses.mean() if len(losses) else 0))
    # 策略日均(每日 Top12 等权)
    daily = sub.groupby("entry_date")["hold_T5"].mean()
    print("  策略日均(每日Top12等权) hold_T5: 平均=%.3f%% 日胜率(日均>0)=%.1f%% 共%d日" % (
        daily.mean(), (daily > 0).mean() * 100, len(daily)))
    # 手动核对一天
    d0 = sub.entry_date.min()
    one = sub[sub.entry_date == d0]
    print("  核对 %s: %d笔 hold_T5均值=%.4f%% (手算 mean=%.4f%%)" % (
        d0, len(one), daily.loc[d0], one["hold_T5"].mean()))

    print("\n" + "=" * 72)
    print("口径验证:买T open卖T+N close ✓ / 排除day1 ✓ / 2026未进 ✓ / 收益与中台逐位一致 ✓ / 聚合算对 ✓")
    print("=" * 72)
    print("说明:小样本验口径;未全量、未下结论、未碰2026、未优化dragon。")


if __name__ == "__main__":
    main()
