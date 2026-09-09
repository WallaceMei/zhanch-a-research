# -*- coding: utf-8 -*-
"""验证"倒序买"假设:dragon_score 负IC,但买分最低组(Q1)次日是否真赚(正收益+胜率>50%)?
★负IC ≠ 倒序就正。结果说话,不搭策略。
口径:打板次日 hold_T1(买entry open卖T+1 close、T+1合法、排除day1)。2026不碰。
- Top250(seed池,dragon_score 来自v1/v2/v3)+ Top12子集 两个都看
- 每天按 dragon_score 分5组(quintile),算各组 hold_T1 平均/中位/胜率
- 重点 Q1(最低,倒序目标):正收益吗?胜率>50%吗?vs Q5 vs 基准
- IS/OOS分开、熊市2022/2023单独、v1/v2/v3都看
- 额外:Q1 流动性(avg_money)能否实盘执行
py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
_DRAGON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dragon_event_study")
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "seed250_panel_2020_2025.csv")
BASE = os.path.join(_DRAGON, "event_study_dragon_2020_2026.csv")
BEAR = [2022, 2023]


def qgrp(x, q=5):
    if x.nunique() < q:
        return pd.Series(np.nan, index=x.index)
    return pd.qcut(x.rank(method="first"), q, labels=False)


def grpstats(df, hold="hold_T1"):
    """按 dragon_score 每日5分组,各组 hold_T1 平均/中位/胜率/流动性。"""
    sub = df[df[hold].notna() & df["dragon_score"].notna()].copy()
    sub["g"] = sub.groupby("entry_date")["dragon_score"].transform(qgrp)
    sub = sub.dropna(subset=["g"])
    rows = []
    for g in range(5):
        s = sub[sub.g == g]
        rows.append(dict(group="Q%d" % (g + 1), n=len(s),
                         mean=s[hold].mean(), median=s[hold].median(),
                         win=(s[hold] > 0).mean() * 100,
                         avg_money_yi=(s["avg_money"].mean() / 1e8 if "avg_money" in s else np.nan)))
    base = dict(group="全池基准", n=len(sub), mean=sub[hold].mean(), median=sub[hold].median(),
                win=(sub[hold] > 0).mean() * 100,
                avg_money_yi=(sub["avg_money"].mean() / 1e8 if "avg_money" in sub else np.nan))
    return pd.DataFrame(rows), base


def load_seed():
    d = pd.read_csv(SEED, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    # seed面板没存dragon_score → 从底座(v1/v2/v3各自)merge
    b = pd.read_csv(BASE, dtype={"entry_date": str, "code": str})
    b["year"] = b["entry_date"].str[:4].astype(int)
    b = b[b.year <= 2025]
    return d, b


def main():
    print("=" * 76)
    print("『倒序买』假设验证 — dragon_score 分组次日(hold_T1)收益。2026未碰。")
    print("=" * 76)
    seed, base = load_seed()
    assert seed.year.max() == 2025 and base.year.max() <= 2025, "红线:2026!"
    seg = lambda df: np.where(df.year <= 2023, "IS", "OOS")
    seed["seg"] = seg(seed); base["seg"] = seg(base)

    out_all = []
    for mode in ["v1", "v2", "v3"]:
        bm = base[base.score_mode == mode][["entry_date", "code", "dragon_score", "day2"]].copy()
        bm = bm.rename(columns={"day2": "hold_T1_base"})
        # --- Top250池:seed + 该mode的dragon_score(只在该日Top12内有分,seed其余无分→该池='有score的seed子集') ---
        # 说明:dragon_score 只对进入Top12打分的票有;Top250里只有被选进Top12的有分。
        #   故"Top250按dragon_score分组"实际只能在"有dragon_score的票"上做=Top12子集。
        #   两个口径:① Top12子集(有score) ② 用seed因子近似无意义→只做Top12子集。
        m12 = seed.merge(bm, on=["entry_date", "code"], how="inner")  # 有dragon_score的=Top12子集
        m12["year"] = m12["entry_date"].str[:4].astype(int); m12["seg"] = seg(m12)
        for scope, df in [("Top12子集(有dragon_score)", m12)]:
            for segname in ["IS", "OOS"]:
                sub = df[df.seg == segname]
                g, b = grpstats(sub, "hold_T1")
                g["mode"] = mode; g["scope"] = scope; g["seg"] = segname
                out_all.append(g)
                print("\n[%s | %s | %s] 基准 hold_T1 平均=%.3f%% 胜率=%.1f%%" % (
                    mode, scope, segname, b["mean"], b["win"]))
                for r in g.itertuples():
                    flag = ""
                    if r.group == "Q1":
                        flag = "  ←倒序买目标:" + ("正收益✓" if r.mean > 0 else "仍负✗") + "/" + ("胜率>50%✓" if r.win > 50 else "胜率<50%✗")
                    print("    %s n=%5d 平均=%+.3f%% 中位=%+.3f%% 胜率=%.1f%% 流动性=%.1f亿%s" % (
                        r.group, r.n, r.mean, r.median, r.win, r.avg_money_yi, flag))
        # 熊市单独(Top12子集)
        bear = m12[m12.year.isin(BEAR)]
        g, b = grpstats(bear, "hold_T1")
        g["mode"] = mode; g["scope"] = "Top12子集"; g["seg"] = "bear_2022_2023"
        out_all.append(g)
        q1 = g[g.group == "Q1"].iloc[0]
        print("  [%s 熊市2022/2023] Q1 平均=%+.3f%% 胜率=%.1f%% (基准%.3f%%/%.1f%%) %s" % (
            mode, q1["mean"], q1["win"], b["mean"], b["win"],
            "倒序熊市成立" if (q1["mean"] > 0 and q1["win"] > 50) else "倒序熊市不成立"))

    res = pd.concat(out_all, ignore_index=True)
    res.to_csv(os.path.join(HERE, "reverse_buy_quintiles.csv"), index=False, encoding="utf-8-sig")
    print("\n落盘 reverse_buy_quintiles.csv")


if __name__ == "__main__":
    main()
