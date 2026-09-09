# -*- coding: utf-8 -*-
"""第二步·①验因子 第二轮 — Top12 池内单因子四关法庭(可交易持有收益 hold_T5,全量)。

★conditioned_on_dragon_top12:在 dragon Top12 幸存者池内,用**可交易持有收益**复核单因子,
  校正 big10"触及"标签的波动率假阳性。买=entry(T) open,卖=T+k close(底座day(k+1)),
  主判据 hold_T5=day6(持5天,T+1合法),辅 hold_T3=day4/hold_T10=day11;排除day1(0天非法)。
不是全市场alpha/不多因子评分/不robust_alpha;只单因子;2026完全不碰。
final_verdict ∈ {gate1_fail,gate2_fail,gate3_redundant,gate_pass_but_decaying,
                 gate_all_pass_candidate,insufficient_data}。严禁robust_alpha。
复用 ../factor_court_top12/core.py。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "factor_court_top12")
sys.path.insert(0, _CORE)
import core as C

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = 0.05; CORR_THR = 0.7; NEG_THR = -0.7
HOLD = {"T3": "day4", "T5": "day6", "T10": "day11"}
HOLD_LAG = {"T3": 3, "T5": 5, "T10": 10}
MAIN = "hold_T5"; MAIN_LAG = 5


def load_pool_tradable(verbose=True):
    d = pd.read_csv(C.BASE, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    keep = (["entry_date", "code", "year"] + C.BASE_FACTORS +
            ["is_big_meat_10", "is_super_meat_20"] + list(HOLD.values()))
    u = d.drop_duplicates(["entry_date", "code"])[keep].copy()
    aug = pd.read_csv(os.path.join(_CORE, "_factors_augmented.csv"), dtype={"entry_date": str, "code": str})
    u = u.merge(aug, on=["entry_date", "code"], how="left")
    u = u[u["year"] != C.HOLDOUT_YEAR].reset_index(drop=True)
    assert (u["year"] == C.HOLDOUT_YEAR).sum() == 0 and u["year"].max() <= 2025, "红线:2026进入!"
    for k, col in HOLD.items():
        u["hold_%s" % k] = u[col]
    u["seg"] = np.where(u["year"] <= C.IS_YEARS[1], "IS",
                        np.where(u["year"] <= C.OOS_YEARS[1], "OOS", "DROP"))
    if verbose:
        print("[load] unique 去2026=%d | IS=%d OOS=%d" % (
            len(u), (u.seg == "IS").sum(), (u.seg == "OOS").sum()))
    return u


def benchmark_df(df):
    d = pd.read_csv(C.BASE, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    v3 = d[(d.score_mode == "v3") & (d.year != C.HOLDOUT_YEAR)][
        ["entry_date", "code", "dragon_score"]].drop_duplicates(["entry_date", "code"])
    return df.merge(v3, on=["entry_date", "code"], how="left")


# ---- 自检 ----
def selfcheck_gate1(df):
    rows = []; ok = True
    for f in C.PRIMARY_FACTORS:
        nmu, nt, real = C.shuffle_null(df, f, MAIN, MAIN_LAG, "IS", n_shuffle=120, seed=42)
        nm = float(np.mean(nmu)); ts = float(np.std(nt)); sig = float(np.mean(np.abs(nt) > 1.96))
        good = abs(nm) < 0.01 and ts < 1.5 and sig < 0.15
        ok = ok and good
        rows.append({"factor": f, "real_ic": round(real["mean_ic"], 5), "null_ic_mean": round(nm, 5),
                     "null_t_std": round(ts, 3), "null_sig_pct": round(sig, 3), "pass": bool(good)})
    return rows, ok


def selfcheck_gate2():
    rng = np.random.RandomState(20); tn = rng.randn(20)
    pn = np.array([C.two_sided_p(t) for t in tn]); passed, _, _ = C.bh_fdr(pn, ALPHA, 20)
    return int(passed.sum()) <= 1, int(passed.sum())


def selfcheck_gate3():
    rng = np.random.RandomState(3)
    A = rng.randn(200); B = A + 0.05 * rng.randn(200); Cc = rng.randn(200); D = -A + 0.05 * rng.randn(200)
    names = ["A", "B", "Cc", "D"]; M = pd.DataFrame(np.corrcoef([A, B, Cc, D]), index=names, columns=names)
    cl = {n: i for i, c in enumerate(C.union_find_clusters(names, M, CORR_THR)) for n in c}
    return (cl["A"] == cl["B"]) and (cl["A"] != cl["Cc"]) and (cl["A"] != cl["D"]) and (M.loc["A", "D"] < NEG_THR)


def selfcheck_gate4():
    cases = {"stable": {2020: .03, 2021: .03, 2022: .031, 2023: .029, 2024: .030, 2025: .029},
             "warning": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .020, 2025: .016},
             "decaying": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .012, 2025: .008},
             "reversal": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .005, 2025: -.01}}
    exp = {"stable": "stable", "warning": "decay_warning", "decaying": "decaying", "reversal": "decaying"}
    return all(C.decay_status_6y(yr)[0] == exp[n] for n, yr in cases.items())


def yearly_ic(df, factor, target):
    return {y: (float(C.daily_ic_series(df[df.year == y], factor, target).mean())
                if len(C.daily_ic_series(df[df.year == y], factor, target)) else np.nan)
            for y in range(2020, 2026)}


def main():
    print("=" * 76)
    print("Top12 池内单因子四关法庭 — 可交易持有收益 hold_T5(全量) conditioned_on_dragon_top12")
    print("=" * 76)
    df = load_pool_tradable()
    assert (df.year == 2026).sum() == 0 and df.year.max() == 2025

    # 自检
    sc1, ok1 = selfcheck_gate1(df); ok2, n2 = selfcheck_gate2(); ok3 = selfcheck_gate3(); ok4 = selfcheck_gate4()
    pd.DataFrame(sc1).to_csv(os.path.join(HERE, "factor_court_top12_tradable_selfcheck.csv"),
                             index=False, encoding="utf-8-sig")
    print("[自检] Gate1打乱归零=%s Gate2噪声FDR(过%d)=%s Gate3聚类=%s Gate4衰减=%s" % (ok1, n2, ok2, ok3, ok4))
    if not (ok1 and ok2 and ok3 and ok4):
        print("\nSELF_CHECK_FAILED — 停止。"); return

    # Gate1:每因子 hold_T5 / T3 / T10 + big10对照
    rows = []; ic_series = {}
    for f in C.PRIMARY_FACTORS:
        r = {"factor": f}
        h_is, s_is = C.gate1_eval(df, f, MAIN, MAIN_LAG, "IS")
        h_os, _ = C.gate1_eval(df, f, MAIN, MAIN_LAG, "OOS")
        ic_series[f] = s_is
        dir_is = int(np.sign(h_is["mean_ic"])) if h_is["mean_ic"] == h_is["mean_ic"] else 0
        flip = (np.sign(h_os["mean_ic"]) != dir_is) if h_os["mean_ic"] == h_os["mean_ic"] else True
        r.update(holdT5_is_ic=h_is["mean_ic"], holdT5_is_t=h_is["hac_t"], holdT5_is_p=h_is["p_two_sided"],
                 holdT5_is_ndays=h_is["n_days"], holdT5_oos_ic=h_os["mean_ic"], holdT5_oos_t=h_os["hac_t"],
                 holdT5_oos_p=h_os["p_two_sided"], direction_is=dir_is, oos_flip=bool(flip))
        for pk in ("T3", "T10"):
            rr, _ = C.gate1_eval(df, f, "hold_%s" % pk, HOLD_LAG[pk], "IS")
            r["hold%s_is_ic" % pk] = rr["mean_ic"]; r["hold%s_is_t" % pk] = rr["hac_t"]
        b_is, _ = C.gate1_eval(df, f, "is_big_meat_10", C.HAC_LAG_EVENT, "IS")
        b_os, _ = C.gate1_eval(df, f, "is_big_meat_10", C.HAC_LAG_EVENT, "OOS")
        r.update(big10_is_ic=b_is["mean_ic"], big10_is_t=b_is["hac_t"], big10_is_p=b_is["p_two_sided"],
                 big10_oos_ic=b_os["mean_ic"])
        rows.append(r)
    g1 = pd.DataFrame(rows)
    g1["gate1_pass"] = (g1.holdT5_is_p < ALPHA) & (~g1.oos_flip)

    # ★核心诊断:big10 vs hold_T5 标签对照
    def diag(r):
        big_sig = r.big10_is_p < ALPHA
        hold_sig = r.holdT5_is_p < ALPHA
        same = np.sign(r.big10_is_ic) == np.sign(r.holdT5_is_ic)
        # ★先判翻向假阳性:big10显著 + hold_T5显著但反向 → 触及标签把它读反了
        if big_sig and hold_sig and not same:
            return "touch_false_positive_FLIP"
        # big10显著但可交易收益不显著 → 触及虚高(波动率/触及钻空子)
        if big_sig and not hold_sig:
            return "touch_only_weakened"
        # hold_T5显著且OOS不翻向:与big10同向且big10也显著=真信号;否则=仅可交易方向新浮现
        if hold_sig and not r.oos_flip:
            return "tradable_signal" if (big_sig and same) else "tradable_only_newdir"
        return "neither"
    g1["label_diagnosis"] = g1.apply(diag, axis=1)
    g1.to_csv(os.path.join(HERE, "factor_court_top12_tradable_gate1.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ic_series).to_csv(os.path.join(HERE, "daily_ic_holdT5_is.csv"), encoding="utf-8-sig")
    print("[Gate1] hold_T5 pass: %d/%d" % (g1.gate1_pass.sum(), len(g1)))

    # benchmark dragon_score(v3) under hold_T5 + big10
    dfb = benchmark_df(df)
    rb_h_is, _ = C.gate1_eval(dfb, "dragon_score", MAIN, MAIN_LAG, "IS")
    rb_h_os, _ = C.gate1_eval(dfb, "dragon_score", MAIN, MAIN_LAG, "OOS")
    rb_b_is, _ = C.gate1_eval(dfb, "dragon_score", "is_big_meat_10", C.HAC_LAG_EVENT, "IS")
    bench = {"holdT5_is_ic": rb_h_is["mean_ic"], "holdT5_is_t": rb_h_is["hac_t"],
             "holdT5_oos_ic": rb_h_os["mean_ic"], "holdT5_oos_t": rb_h_os["hac_t"],
             "big10_is_ic": rb_b_is["mean_ic"], "big10_is_t": rb_b_is["hac_t"]}

    # Gate2 BH-FDR(族=8)
    fam = len(C.PRIMARY_FACTORS)
    g1p = g1[g1.gate1_pass].copy()
    if len(g1p):
        passed, q, thr = C.bh_fdr(g1p.holdT5_is_p.values, ALPHA, fam)
        g1p["bh_q"] = q; g1p["gate2_pass"] = passed
    g2map = dict(zip(g1p.factor, g1p.gate2_pass)) if len(g1p) else {}
    g1p.to_csv(os.path.join(HERE, "factor_court_top12_tradable_gate2_fdr.csv"), index=False, encoding="utf-8-sig")
    print("[Gate2] BH-FDR(族=%d) pass: %d" % (fam, int(g1p.gate2_pass.sum()) if len(g1p) else 0))

    # Gate3 去冗余(hold_T5 IS IC 序列)
    g2pass = [f for f in C.PRIMARY_FACTORS if g2map.get(f, False)]
    g3rows = []; reps = []; negrows = []
    if g2pass:
        ser = pd.DataFrame({f: ic_series[f] for f in g2pass}).dropna(how="all")
        corr = ser.corr(); corr.to_csv(os.path.join(HERE, "gate3_corr_matrix.csv"), encoding="utf-8-sig")
        tmap = dict(zip(g1.factor, g1.holdT5_is_t))
        for cid, mem in enumerate(C.union_find_clusters(g2pass, corr, CORR_THR)):
            rep = sorted(mem, key=lambda n: -abs(tmap[n]))[0]; reps.append(rep)
            for n in mem:
                g3rows.append({"factor": n, "cluster_id": cid, "members": "|".join(sorted(mem)),
                               "representative": rep, "is_representative": (n == rep),
                               "gate3_status": "keep" if n == rep else "gate3_redundant"})
        for i in range(len(g2pass)):
            for j in range(i + 1, len(g2pass)):
                if corr.iloc[i, j] < NEG_THR:
                    negrows.append({"factor_a": g2pass[i], "factor_b": g2pass[j],
                                    "ic_corr": round(float(corr.iloc[i, j]), 4), "note": "potential_complement"})
    pd.DataFrame(g3rows).to_csv(os.path.join(HERE, "factor_court_top12_tradable_gate3_clusters.csv"),
                                index=False, encoding="utf-8-sig")
    g3rep = {r["factor"]: r["is_representative"] for r in g3rows}
    print("[Gate3] gate2pass=%d → 独立簇=%d 冗余=%d 负相关对=%d" % (
        len(g2pass), len(reps), len(g3rows) - len(reps), len(negrows)))

    # Gate4 衰减 + 年度IC(牛熊)
    yrows = []
    for f in C.PRIMARY_FACTORS:
        yr = yearly_ic(df, f, MAIN)
        st, isic, oosic = C.decay_status_6y(yr)
        row = {"factor": f}; row.update({"ic_%d" % y: round(yr[y], 5) for y in range(2020, 2026)})
        row.update(bear_2022=round(yr[2022], 5), bear_2023=round(yr[2023], 5),
                   is_era_ic=round(isic, 5), oos_era_ic=round(oosic, 5), decay_status=st)
        yrows.append(row)
    yic = pd.DataFrame(yrows); yic.to_csv(os.path.join(HERE, "factor_court_top12_tradable_gate4_decay.csv"),
                                          index=False, encoding="utf-8-sig")
    decay_map = dict(zip(yic.factor, yic.decay_status))
    print("[Gate4] " + " ".join("%s=%s" % (r.factor, r.decay_status) for r in yic.itertuples()))

    # final_verdict
    led = []
    for r in g1.itertuples():
        f = r.factor
        if r.holdT5_is_ndays < 30:
            fv = "insufficient_data"
        elif not r.gate1_pass:
            fv = "gate1_fail"
        elif not g2map.get(f, False):
            fv = "gate2_fail"
        elif not g3rep.get(f, False):
            fv = "gate3_redundant"
        elif decay_map.get(f) == "decaying":
            fv = "gate_pass_but_decaying"
        else:
            fv = "gate_all_pass_candidate"
        led.append({"factor": f, "final_verdict": fv, "label_diagnosis": r.label_diagnosis,
                    "holdT5_is_ic": round(r.holdT5_is_ic, 5), "holdT5_is_t": round(r.holdT5_is_t, 3),
                    "holdT5_is_p": round(r.holdT5_is_p, 5), "holdT5_oos_ic": round(r.holdT5_oos_ic, 5),
                    "holdT5_oos_t": round(r.holdT5_oos_t, 3), "oos_flip": r.oos_flip,
                    "big10_is_ic": round(r.big10_is_ic, 5), "big10_is_t": round(r.big10_is_t, 3),
                    "gate1_pass": r.gate1_pass, "gate2_pass": bool(g2map.get(f, False)),
                    "gate3_rep": bool(g3rep.get(f, False)), "decay_status": decay_map.get(f, "n/a"),
                    "conditioned_on": "dragon_top12"})
    led = pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict)
    led.to_csv(os.path.join(HERE, "factor_court_top12_tradable_ledger.csv"), index=False, encoding="utf-8-sig")
    print("\n=== final_verdict 分布 ===\n" + led.final_verdict.value_counts().to_string())
    print("\n=== 标签诊断分布 ===\n" + g1.label_diagnosis.value_counts().to_string())

    write_summary(df, g1, led, yic, reps, negrows, g2pass, bench, sc1, ok2, ok3, ok4, n2, fam, decay_map)
    print("\n[done] 报告+CSV 落盘于 factor_court_top12_tradable/")


def write_summary(df, g1, led, yic, reps, negrows, g2pass, bench, sc1, ok2, ok3, ok4, n2, fam, decay_map):
    L = []
    L.append("# 战车A 第二步·①验因子 第二轮 — 可交易持有收益(hold_T5)四关法庭")
    L.append("")
    L.append("> **conditioned_on_dragon_top12**;主判据=**hold_T5(可交易持有5天收益)**:买 entry(T) open、卖 T+5 close"
             "(底座 day6),持5天、**T+1合法**(排除 day1 的0天持仓);辅 hold_T3=day4/hold_T10=day11。")
    L.append("> 本轮目的:用可交易收益**复核 big10「触及」标签的波动率假阳性**。"
             "**不是**全市场 alpha、**不是**多因子评分、**不是** robust_alpha;只单因子;**2026 全程未碰**。")
    L.append("- 切分:IS=2020-2023(%d) / OOS=2024-2025(%d) / 2026 holdout 未进。"
             % ((df.seg == "IS").sum(), (df.seg == "OOS").sum()))
    L.append("- 受审 8 因子(族=%d):%s;benchmark=dragon_score(v3,仅对照)。" % (fam, ", ".join(C.PRIMARY_FACTORS)))
    L.append("")
    L.append("## ★1) 核心:big10(触及) vs hold_T5(可交易) IC 对照 —— 照出假阳性")
    L.append("| 因子 | big10 IS IC(t) | hold_T5 IS IC(t) | hold_T5 OOS IC(t) | 标签诊断 |")
    L.append("|---|---|---|---|---|")
    for r in g1.itertuples():
        L.append("| %s | %+.4f(%+.1f) | %+.4f(%+.1f) | %+.4f(%+.1f) | %s |" % (
            r.factor, r.big10_is_ic, r.big10_is_t, r.holdT5_is_ic, r.holdT5_is_t,
            r.holdT5_oos_ic, r.holdT5_oos_t, r.label_diagnosis))
    L.append("| **dragon_score(bench,v3)** | %+.4f(%+.1f) | %+.4f(%+.1f) | %+.4f(%+.1f) | benchmark |" % (
        bench["big10_is_ic"], bench["big10_is_t"], bench["holdT5_is_ic"], bench["holdT5_is_t"],
        bench["holdT5_oos_ic"], bench["holdT5_oos_t"]))
    L.append("")
    L.append("诊断口径:`touch_false_positive_FLIP`=big10显著但hold_T5显著反向(触及假阳性);"
             "`touch_only_weakened`=big10显著但hold_T5不显著(触及虚高);"
             "`tradable_signal`=hold_T5显著且OOS不翻向(且与big10同向,真信号);"
             "`tradable_only`=hold_T5有效但big10下不显著;`neither`=两标签都无效。")
    L.append("")
    L.append("## 2) hold_T5 四关结果(IS锁方向,OOS验不翻向)")
    L.append("| 因子 | IS IC | IS t | IS p | OOS IC | OOS t | OOS翻向 | Gate1 | Gate2 | Gate3代表 | 衰减 | final |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    lm = led.set_index("factor")
    for r in g1.itertuples():
        f = r.factor
        L.append("| %s | %+.4f | %+.2f | %.3f | %+.4f | %+.2f | %s | %s | %s | %s | %s | %s |" % (
            f, r.holdT5_is_ic, r.holdT5_is_t, r.holdT5_is_p, r.holdT5_oos_ic, r.holdT5_oos_t,
            "是" if r.oos_flip else "否", "pass" if r.gate1_pass else "fail",
            "pass" if lm.loc[f, "gate2_pass"] else "-", "是" if lm.loc[f, "gate3_rep"] else "-",
            lm.loc[f, "decay_status"], lm.loc[f, "final_verdict"]))
    L.append("")
    L.append("## 3) 周期对照(IS Rank IC):hold_T3 / hold_T5 / hold_T10")
    L.append("| 因子 | T3 IC(t) | **T5 IC(t)主** | T10 IC(t) |")
    L.append("|---|---|---|---|")
    for r in g1.itertuples():
        L.append("| %s | %+.4f(%+.1f) | **%+.4f(%+.1f)** | %+.4f(%+.1f) |" % (
            r.factor, r.holdT3_is_ic, r.holdT3_is_t, r.holdT5_is_ic, r.holdT5_is_t,
            r.holdT10_is_ic, r.holdT10_is_t))
    L.append("")
    L.append("## 4) dragon_score benchmark 在 hold_T5 下还强吗")
    L.append("- big10 下:IS IC=%+.4f(t%+.1f) —— 第一轮很强。" % (bench["big10_is_ic"], bench["big10_is_t"]))
    L.append("- **hold_T5(可交易)下:IS IC=%+.4f(t%+.1f) / OOS IC=%+.4f(t%+.1f)**。"
             % (bench["holdT5_is_ic"], bench["holdT5_is_t"], bench["holdT5_oos_ic"], bench["holdT5_oos_t"]))
    L.append("- 解读见结论:若 big10 强而 hold_T5 弱/反向,提示 dragon_score 可能优化在「触及」靶子上,而非可交易收益。")
    L.append("")
    L.append("## 5) 牛熊年份分层(hold_T5 池内 Rank IC,逐年;2026未计)")
    L.append("| 因子 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | IS期 | OOS期 | 衰减 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in yic.itertuples():
        L.append("| %s | %+.3f | %+.3f | **%+.3f** | **%+.3f** | %+.3f | %+.3f | %+.3f | %+.3f | %s |" % (
            r.factor, r.ic_2020, r.ic_2021, r.bear_2022, r.bear_2023, r.ic_2024, r.ic_2025,
            r.is_era_ic, r.oos_era_ic, r.decay_status))
    L.append("")
    L.append("## 6) Gate1-4 漏斗 + 打乱归零自检")
    L.append("```")
    L.append("受审单因子(族): %d" % fam)
    L.append("-> Gate1 hold_T5 通过(IS显著+OOS不翻向): %d" % int(g1.gate1_pass.sum()))
    L.append("-> Gate2 BH-FDR(族=%d): %d" % (fam, len(g2pass)))
    L.append("-> Gate3 去冗余独立信号: %d" % len(reps))
    L.append("-> Gate4 代表中 decaying: %d" % sum(1 for f in reps if decay_map.get(f) == "decaying"))
    L.append("-> gate_all_pass_candidate: %d" % int((led.final_verdict == "gate_all_pass_candidate").sum()))
    L.append("```")
    L.append("- 打乱 hold_T5 归零自检(每因子):" + "; ".join(
        "%s null_ic=%.4f t_std=%.2f %s" % (s["factor"], s["null_ic_mean"], s["null_t_std"],
        "✓" if s["pass"] else "✗") for s in sc1))
    L.append("- Gate2噪声FDR(过%d/20)=%s;Gate3合成聚类=%s;Gate4人造衰减=%s。" % (
        n2, "✓" if ok2 else "✗", "✓" if ok3 else "✗", "✓" if ok4 else "✗"))
    if reps:
        L.append("- 独立簇代表:%s。" % ", ".join(reps))
    if negrows:
        L.append("- 强负相关(potential_complement):" + "; ".join(
            "%s vs %s(%.2f)" % (n["factor_a"], n["factor_b"], n["ic_corr"]) for n in negrows))
    L.append("")
    L.append("## 7) final_verdict 分布")
    for k, v in led.final_verdict.value_counts().items():
        L.append("- %s: %d (%s)" % (k, v, ", ".join(led[led.final_verdict == k].factor.tolist())))
    L.append("")
    L.append("## 8) ★声明(必读)")
    L.append("- 本报告 **conditioned_on_dragon_top12**,主标签=**可交易持有收益 hold_T5**(买T open卖T+5 close、排除day1、T+1合法)。")
    L.append("- **不是**全市场 alpha、**不是**多因子评分、**不是** robust_alpha;只单因子审判,未组合/未调权重/未改 dragon_score。")
    L.append("- **2026 全程未碰**(Final holdout)。big10/super20 仅作触及对照,不参与本轮 verdict。")
    L.append("- 本轮目的=校正牛股定义(触及→可交易收益),照出波动率假阳性;不下实盘结论。")
    L.append("")
    with open(os.path.join(HERE, "factor_court_top12_tradable_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
