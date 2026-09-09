# -*- coding: utf-8 -*-
"""dragon 整套策略·可交易收益回测(全量 2020-2025)。

诊断:dragon 选出 Top12 后,买 entry(T) open、持 N 天卖 T+N close(可交易、T+1合法、排除day1),
      在 2020-2025 实际可交易收益是多少。回答:整体赚不赚 / 熊市2022-2023赚不赚 / 高分票真赚更多吗。
★诊断现状,不优化不调dragon。conditioned_on_dragon_top12。2026 全程不碰。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
_DRAGON = os.path.dirname(HERE)
BASE = os.path.join(_DRAGON, "event_study_dragon_2020_2026.csv")
HOLD = {"hold_T3": "day4", "hold_T5": "day6", "hold_T10": "day11"}   # 买T open卖T+N close
MAIN = "hold_T5"
BEAR = [2022, 2023]
STRONG = [2020, 2021, 2024, 2025]


def load():
    d = pd.read_csv(BASE, dtype={"entry_date": str, "prev_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    d = d[d["year"] <= 2025].reset_index(drop=True)        # ★只用 2020-2025,2026 holdout
    assert d["year"].max() == 2025 and (d["year"] == 2026).sum() == 0, "红线:2026 进入!"
    for h, col in HOLD.items():
        d[h] = d[col]
    return d


def stats(s):
    s = s.dropna()
    if len(s) == 0:
        return dict(n=0, mean=np.nan, median=np.nan, win=np.nan, pl=np.nan)
    w = s[s > 0]; l = s[s < 0]
    pl = (w.mean() / abs(l.mean())) if (len(l) and l.mean() != 0) else np.nan
    return dict(n=len(s), mean=s.mean(), median=s.median(), win=(s > 0).mean() * 100,
                pl=pl, avg_win=(w.mean() if len(w) else np.nan),
                avg_loss=(l.mean() if len(l) else np.nan))


def fmt(st):
    return "n=%5d 平均=%+.3f%% 中位=%+.3f%% 胜率=%.1f%% 盈亏比=%s" % (
        st["n"], st["mean"], st["median"], st["win"],
        ("%.2f" % st["pl"]) if st["pl"] == st["pl"] else "NA")


def main():
    print("=" * 76)
    print("dragon 策略·可交易收益回测(全量 2020-2025) — conditioned_on_dragon_top12")
    print("=" * 76)
    d = load()
    print("总笔数(3版)=%d | 年=%s" % (len(d), sorted(d.year.unique())))

    # ---- 1) 整体(每笔)各版 各周期 ----
    rows = []
    for mode in ["v1", "v2", "v3"]:
        for h in HOLD:
            st = stats(d[d.score_mode == mode][h])
            rows.append(dict(mode=mode, hold=h, **st))
    overall = pd.DataFrame(rows)
    overall.to_csv(os.path.join(HERE, "bt_overall.csv"), index=False, encoding="utf-8-sig")
    print("\n[1] 整体每笔可交易收益(各版×周期)")
    for mode in ["v1", "v2", "v3"]:
        for h in HOLD:
            st = overall[(overall["mode"] == mode) & (overall.hold == h)].iloc[0].to_dict()
            print("  %s %-8s %s" % (mode, h, fmt(st)))

    # ---- 2) 牛熊分层(主周期 hold_T5)----
    print("\n[2] ★牛熊分层 hold_T5(熊市 2022/2023 vs 强势年)")
    bull_rows = []
    for mode in ["v1", "v2", "v3"]:
        dm = d[d.score_mode == mode]
        for y in range(2020, 2026):
            st = stats(dm[dm.year == y][MAIN]); bull_rows.append(dict(mode=mode, year=y, **st))
        bear = stats(dm[dm.year.isin(BEAR)][MAIN])
        strong = stats(dm[dm.year.isin(STRONG)][MAIN])
        bull_rows.append(dict(mode=mode, year="bear_2022_2023", **bear))
        bull_rows.append(dict(mode=mode, year="strong_rest", **strong))
    bydf = pd.DataFrame(bull_rows)
    bydf.to_csv(os.path.join(HERE, "bt_bull_bear.csv"), index=False, encoding="utf-8-sig")
    for mode in ["v1", "v2", "v3"]:
        print("  --- %s ---" % mode)
        for y in list(range(2020, 2026)) + ["bear_2022_2023", "strong_rest"]:
            st = bydf[(bydf["mode"] == mode) & (bydf.year == y)].iloc[0].to_dict()
            tag = " ★熊" if y in BEAR else ("  熊合计" if y == "bear_2022_2023" else "")
            print("    %-16s %s%s" % (str(y), fmt(st), tag))

    # ---- 3) rank 分层单调性(主周期 hold_T5)----
    print("\n[3] ★rank 分层 hold_T5(高分真赚更多吗)")
    def rbucket(r):
        return "rank1-3" if r <= 3 else ("rank4-8" if r <= 8 else "rank9-12")
    d["rbucket"] = d["rank"].apply(rbucket)
    rk_rows = []
    for mode in ["v1", "v2", "v3"]:
        dm = d[d.score_mode == mode]
        for b in ["rank1-3", "rank4-8", "rank9-12"]:
            st = stats(dm[dm.rbucket == b][MAIN]); rk_rows.append(dict(mode=mode, bucket=b, **st))
    rkdf = pd.DataFrame(rk_rows)
    rkdf.to_csv(os.path.join(HERE, "bt_rank_strata.csv"), index=False, encoding="utf-8-sig")
    for mode in ["v1", "v2", "v3"]:
        print("  --- %s ---" % mode)
        for b in ["rank1-3", "rank4-8", "rank9-12"]:
            st = rkdf[(rkdf["mode"] == mode) & (rkdf.bucket == b)].iloc[0].to_dict()
            print("    %-9s %s" % (b, fmt(st)))

    # ---- 4) 策略日均 + 累计(每日均值加总,避免重叠复利失真)----
    print("\n[4] 策略日均(每日Top12等权)hold_T5 + 累计(每日均值加总,additive)")
    cum_rows = []
    for mode in ["v1", "v2", "v3"]:
        dm = d[d.score_mode == mode]
        daily = dm.groupby("entry_date")[MAIN].mean().sort_index()
        cumsum = daily.cumsum()
        cum_rows.append(dict(mode=mode, n_days=len(daily), daily_mean=daily.mean(),
                             daily_win=(daily > 0).mean() * 100,
                             cum_sum_end=cumsum.iloc[-1] if len(cumsum) else np.nan))
        # 逐年累计加总
        ddf = daily.reset_index(); ddf["year"] = ddf.entry_date.str[:4].astype(int)
        yr_sum = ddf.groupby("year")[MAIN].sum()
        if mode == "v3":
            v3_year_cum = yr_sum
    cumdf = pd.DataFrame(cum_rows)
    cumdf.to_csv(os.path.join(HERE, "bt_cumulative.csv"), index=False, encoding="utf-8-sig")
    for r in cumdf.itertuples():
        print("  %s 日均=%+.3f%% 日胜率=%.1f%% 累计加总(全期)=%+.1f%% (%d日)" % (
            r.mode, r.daily_mean, r.daily_win, r.cum_sum_end, r.n_days))
    print("  v3 逐年累计加总: %s" % {int(y): round(v3_year_cum[y], 1) for y in v3_year_cum.index})

    write_report(d, overall, bydf, rkdf, cumdf, v3_year_cum)
    print("\n[done] 报告+CSV 落盘 dragon_tradable_backtest/。不自动下结论。")


def write_report(d, overall, bydf, rkdf, cumdf, v3_year_cum):
    def ov(mode, h):
        return overall[(overall["mode"] == mode) & (overall.hold == h)].iloc[0].to_dict()
    def by(mode, y):
        return bydf[(bydf["mode"] == mode) & (bydf.year == y)].iloc[0].to_dict()
    def rk(mode, b):
        return rkdf[(rkdf["mode"] == mode) & (rkdf.bucket == b)].iloc[0].to_dict()
    L = []
    L.append("# dragon 策略·可交易收益回测(2020-2025) — 诊断报告")
    L.append("")
    L.append("> **conditioned_on_dragon_top12**;可交易口径:买 entry(T) open、持 N 天卖 **T+N close**"
             "(底座 day(N+1)),**T+1合法**(排除 day1 的0天持仓);主周期 **hold_T5**,辅 hold_T3/T10。")
    L.append("> **诊断现状,非改策略**:未优化、未调参、未改 dragon。**2026 全程未碰**(holdout,max year=2025)。")
    L.append("> 累计用「每日Top12等权均值·逐日加总(additive)」,避免重叠持仓复利失真——是相对强弱示意,非可投资净值。")
    L.append("")
    L.append("## 回答 1:dragon 策略 2020-2025 整体可交易赚不赚(每笔)")
    L.append("| 版本 | 周期 | 笔数 | 平均 | 中位 | 胜率 | 盈亏比 |")
    L.append("|---|---|---|---|---|---|---|")
    for mode in ["v1", "v2", "v3"]:
        for h in ["hold_T3", "hold_T5", "hold_T10"]:
            s = ov(mode, h)
            L.append("| %s | %s | %d | %+.3f%% | %+.3f%% | %.1f%% | %s |" % (
                mode, h, s["n"], s["mean"], s["median"], s["win"],
                ("%.2f" % s["pl"]) if s["pl"] == s["pl"] else "NA"))
    L.append("")
    L.append("> 看「平均」是否>0、「中位」与「胜率」——若平均靠盈亏比(少数大肉)拉、中位为负胜率<50%,"
             "即「多数亏、靠少数大肉」结构。")
    L.append("")
    L.append("## 回答 2:★熊市 2022/2023 赚不赚(hold_T5,核心)")
    L.append("| 版本 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | 熊合计 | 强势合计 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for mode in ["v1", "v2", "v3"]:
        cells = []
        for y in range(2020, 2026):
            cells.append("%+.2f%%" % by(mode, y)["mean"])
        cells.append("%+.2f%%" % by(mode, "bear_2022_2023")["mean"])
        cells.append("%+.2f%%" % by(mode, "strong_rest")["mean"])
        L.append("| %s | %s |" % (mode, " | ".join(cells)))
    L.append("")
    L.append("| 版本 | 熊市2022/2023 笔数 | 熊市平均 | 熊市中位 | 熊市胜率 | 强势平均 | 强势胜率 |")
    L.append("|---|---|---|---|---|---|---|")
    for mode in ["v1", "v2", "v3"]:
        b = by(mode, "bear_2022_2023"); s = by(mode, "strong_rest")
        L.append("| %s | %d | %+.3f%% | %+.3f%% | %.1f%% | %+.3f%% | %.1f%% |" % (
            mode, b["n"], b["mean"], b["median"], b["win"], s["mean"], s["win"]))
    L.append("")
    L.append("> 核心问题:若熊市 2022/2023 平均为负、强势年为正 → dragon 只在强势市靠少数大肉好看,"
             "**2026 的「不错」很可能是强势市假象**。")
    L.append("")
    L.append("## 回答 3:★rank 分层——高分票持有收益更高吗(hold_T5)")
    L.append("| 版本 | rank1-3(高分) | rank4-8(中) | rank9-12(尾) | 单调? |")
    L.append("|---|---|---|---|---|")
    for mode in ["v1", "v2", "v3"]:
        a = rk(mode, "rank1-3")["mean"]; m = rk(mode, "rank4-8")["mean"]; t = rk(mode, "rank9-12")["mean"]
        mono = "高>低✓" if (a > m > t) else ("高<低(反向)" if (a < m < t) else "无单调")
        L.append("| %s | %+.3f%% | %+.3f%% | %+.3f%% | %s |" % (mode, a, m, t, mono))
    L.append("")
    L.append("> 若 rank1-3(高分)≤ rank9-12(尾段)→ dragon 高分不赚甚至反向,**印证单因子诊断"
             "「dragon_score 在 hold_T5 下 IC 为负」**(优化错靶子)。")
    L.append("")
    L.append("## 与单因子 dragon_score 诊断的一致性")
    L.append("- 单因子(上轮):dragon_score 在 hold_T5 下 IS IC=−0.039 / OOS IC=−0.060(显著为负,分越高持有越亏)。")
    L.append("- 本轮策略层:见上「rank 分层」——高分段 vs 尾段的 hold_T5 平均收益单调性,应与单因子诊断方向一致。")
    L.append("")
    L.append("## 累计(每日均值加总,additive;重叠口径,非净值)")
    L.append("| 版本 | 交易日 | 日均 | 日胜率 | 全期累计加总 |")
    L.append("|---|---|---|---|---|")
    for r in cumdf.itertuples():
        L.append("| %s | %d | %+.3f%% | %.1f%% | %+.1f%% |" % (
            r.mode, r.n_days, r.daily_mean, r.daily_win, r.cum_sum_end))
    L.append("")
    L.append("- v3 逐年累计加总(hold_T5):" + ", ".join(
        "%d=%+.1f%%" % (int(y), v3_year_cum[y]) for y in v3_year_cum.index))
    L.append("")
    L.append("## 声明(必读)")
    L.append("- **conditioned_on_dragon_top12**:仅 dragon Top12 幸存者池内的可交易收益,**不是**全市场 alpha。")
    L.append("- **诊断现状,非改策略**:未优化、未调参、未止盈止损、未改 dragon_score/选股。")
    L.append("- 可交易口径(买T open卖T+N close、T+1合法、排除day1);累计为 additive 示意,**未计交易成本/冲击**,非可投资净值。")
    L.append("- **2026 全程未碰**(Final holdout)。本报告不自动下实盘结论。")
    with open(os.path.join(HERE, "dragon_tradable_backtest_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
