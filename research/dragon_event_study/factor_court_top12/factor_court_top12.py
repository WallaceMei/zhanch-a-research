# -*- coding: utf-8 -*-
"""战车A研究第二步 — Top12 候选池内单因子四关法庭(全量)。

★conditioned_on_dragon_top12:在 dragon Top12 幸存者池内,审单因子还能否区分赢家(big10)。
不是全市场alpha/不是多因子评分/不是robust_alpha;只单因子,不组合不调权重不改dragon_score;2026完全不碰。

四关:Gate1(池内big10区分力 HAC t + 方向IS锁OOS不翻向 + 打乱归零自检)
      Gate2(BH-FDR 族=8)Gate3(big10 IC序列正相关去冗余>0.7,负相关标互补)
      Gate4(年度衰减,2026不参与)。任一自检不过→SELF_CHECK_FAILED停。
final_verdict ∈ {gate1_fail,gate2_fail,gate3_redundant,gate_pass_but_decaying,
                 gate_all_pass_candidate,super20_specific_candidate,insufficient_data}。严禁robust_alpha。
py-3.10。
"""
import io
import os
import sys
import json
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = 0.05
CORR_THR = 0.7
NEG_THR = -0.7
RUN = "RUN"   # 复现:不取 now


# ============ 自检(四关) ============
def selfcheck_gate1(df):
    """★最关键:打乱 big10 后,每个因子池内IC应归零、HAC t退回N(0,1)。"""
    rows = []; ok_all = True
    for f in C.PRIMARY_FACTORS:
        nmu, nt, real = C.shuffle_null(df, f, C.MAIN_LABEL, C.HAC_LAG_EVENT, "IS",
                                       n_shuffle=120, seed=42)
        null_mu_mean = float(np.mean(nmu)); null_t_std = float(np.std(nt))
        null_sig = float(np.mean(np.abs(nt) > 1.96))
        ok = abs(null_mu_mean) < 0.01 and null_t_std < 1.5 and null_sig < 0.15
        ok_all = ok_all and ok
        rows.append({"factor": f, "real_mean_ic": round(real["mean_ic"], 5),
                     "null_ic_mean": round(null_mu_mean, 5),
                     "null_t_std": round(null_t_std, 3), "null_sig_pct": round(null_sig, 3),
                     "gate1_shuffle_zero_pass": bool(ok)})
    return rows, ok_all


def selfcheck_gate2():
    rng = np.random.RandomState(20)
    tn = rng.randn(20)
    pn = np.array([C.two_sided_p(t) for t in tn])
    passed, _, _ = C.bh_fdr(pn, ALPHA, 20)
    return int(passed.sum()) <= 1, int(passed.sum())


def selfcheck_gate3():
    rng = np.random.RandomState(3)
    A = rng.randn(200); B = A + 0.05 * rng.randn(200); Cc = rng.randn(200); D = -A + 0.05 * rng.randn(200)
    names = ["A", "B", "Cc", "D"]
    M = pd.DataFrame(np.corrcoef([A, B, Cc, D]), index=names, columns=names)
    clusters = C.union_find_clusters(names, M, CORR_THR)
    cl = {n: i for i, c in enumerate(clusters) for n in c}
    ok = (cl["A"] == cl["B"]) and (cl["A"] != cl["Cc"]) and (cl["A"] != cl["D"]) and (M.loc["A", "D"] < NEG_THR)
    return ok


def selfcheck_gate4():
    # 用例按 decay_status_6y 的 era-mean 口径标定:
    #   stable: OOS期/IS期 ≥0.7;warning: 0.5~0.7;decaying: <0.5 或反向
    cases = {"stable": {2020: .03, 2021: .03, 2022: .031, 2023: .029, 2024: .030, 2025: .029},
             "warning": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .020, 2025: .016},
             "decaying": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .012, 2025: .008},
             "reversal": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .005, 2025: -.01}}
    exp = {"stable": "stable", "warning": "decay_warning", "decaying": "decaying", "reversal": "decaying"}
    ok = True
    for name, yr in cases.items():
        st, _, _ = C.decay_status_6y(yr)
        ok = ok and (st == exp[name])
    return ok


# ============ Gate1:逐因子 big10 / super20 / 连续周期 ============
def eval_factor(df, factor):
    out = {"factor": factor}
    # big10 IS/OOS
    ris, sis = C.gate1_eval(df, factor, C.MAIN_LABEL, C.HAC_LAG_EVENT, "IS")
    ros, _ = C.gate1_eval(df, factor, C.MAIN_LABEL, C.HAC_LAG_EVENT, "OOS")
    dir_is = int(np.sign(ris["mean_ic"])) if ris["mean_ic"] == ris["mean_ic"] else 0
    flip = (np.sign(ros["mean_ic"]) != dir_is) if ros["mean_ic"] == ros["mean_ic"] else True
    out.update(big10_is_ic=ris["mean_ic"], big10_is_t=ris["hac_t"], big10_is_p=ris["p_two_sided"],
               big10_is_ndays=ris["n_days"], big10_oos_ic=ros["mean_ic"], big10_oos_t=ros["hac_t"],
               big10_oos_p=ros["p_two_sided"], big10_oos_ndays=ros["n_days"],
               direction_is=dir_is, oos_flip=bool(flip))
    # super20 IS/OOS
    s_is, _ = C.gate1_eval(df, factor, "is_super_meat_20", C.HAC_LAG_EVENT, "IS")
    s_os, _ = C.gate1_eval(df, factor, "is_super_meat_20", C.HAC_LAG_EVENT, "OOS")
    s_dir = int(np.sign(s_is["mean_ic"])) if s_is["mean_ic"] == s_is["mean_ic"] else 0
    s_flip = (np.sign(s_os["mean_ic"]) != s_dir) if s_os["mean_ic"] == s_os["mean_ic"] else True
    out.update(super20_is_ic=s_is["mean_ic"], super20_is_t=s_is["hac_t"], super20_is_p=s_is["p_two_sided"],
               super20_oos_ic=s_os["mean_ic"], super20_oos_t=s_os["hac_t"], super20_oos_flip=bool(s_flip))
    # 连续前向收益 各周期(IS)
    for pk, col in C.FWD_PERIODS.items():
        r, _ = C.gate1_eval(df, factor, col, C.HAC_LAG_FWD[pk], "IS")
        out["fwd_%s_is_ic" % pk] = r["mean_ic"]; out["fwd_%s_is_t" % pk] = r["hac_t"]
    return out, sis


def yearly_ic(df, factor, label=C.MAIN_LABEL):
    """逐年池内 big10 区分力(2020-2025,★无2026)。"""
    res = {}
    for y in range(2020, 2026):
        sub = df[df.year == y]
        s = C.daily_ic_series(sub, factor, label)
        res[y] = float(s.mean()) if len(s) else np.nan
    return res


def main():
    print("=" * 74)
    print("Top12 池内单因子四关法庭(全量) — conditioned_on_dragon_top12")
    print("=" * 74)
    df = C.load_pool(verbose=True)
    assert (df.year == 2026).sum() == 0 and df.year.max() == 2025, "红线:2026 进入!"

    # -------- 自检(四关) --------
    print("\n[自检] Gate1 打乱归零(8因子)...")
    sc1_rows, ok1 = selfcheck_gate1(df)
    ok2, n2 = selfcheck_gate2()
    ok3 = selfcheck_gate3()
    ok4 = selfcheck_gate4()
    pd.DataFrame(sc1_rows).to_csv(os.path.join(HERE, "selfcheck_gate1_shuffle.csv"),
                                  index=False, encoding="utf-8-sig")
    print("  Gate1 shuffle归零: %s | Gate2 噪声FDR(过%d/20): %s | Gate3 合成聚类: %s | Gate4 人造衰减: %s"
          % (ok1, n2, ok2, ok3, ok4))
    if not (ok1 and ok2 and ok3 and ok4):
        print("\nSELF_CHECK_FAILED — 停止,不输出 final verdict。")
        return

    # -------- Gate1:逐因子 --------
    print("\n[Gate1] 逐因子 big10/super20/连续周期...")
    rows = []; ic_series = {}
    for f in C.PRIMARY_FACTORS:
        r, sis = eval_factor(df, f)
        rows.append(r); ic_series[f] = sis
    g1 = pd.DataFrame(rows)
    # Gate1 判定:IS 显著(p<0.05) 且 OOS 不翻向
    g1["gate1_big10_pass"] = (g1.big10_is_p < ALPHA) & (~g1.oos_flip)
    g1["gate1_super20_pass"] = (g1.super20_is_p < ALPHA) & (~g1.super20_oos_flip)
    g1.to_csv(os.path.join(HERE, "gate1_results.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ic_series).to_csv(os.path.join(HERE, "daily_ic_big10_is.csv"), encoding="utf-8-sig")
    print("  Gate1 big10 pass: %d/%d | super20 pass: %d/%d"
          % (g1.gate1_big10_pass.sum(), len(g1), g1.gate1_super20_pass.sum(), len(g1)))

    # benchmark dragon_score(v3)— 仅对照,不进族/不进候选
    bench = C.benchmark_series()
    dfb = df.merge(bench, on=["entry_date", "code"], how="left")
    rb_is, _ = C.gate1_eval(dfb.assign(**{"dragon_score": dfb["dragon_score"]}),
                            "dragon_score", C.MAIN_LABEL, C.HAC_LAG_EVENT, "IS")
    rb_os, _ = C.gate1_eval(dfb, "dragon_score", C.MAIN_LABEL, C.HAC_LAG_EVENT, "OOS")
    bench_row = {"factor": "dragon_score(benchmark,v3)", "big10_is_ic": rb_is["mean_ic"],
                 "big10_is_t": rb_is["hac_t"], "big10_is_p": rb_is["p_two_sided"],
                 "big10_oos_ic": rb_os["mean_ic"], "big10_oos_t": rb_os["hac_t"],
                 "note": "benchmark_only_not_candidate"}

    # -------- Gate2: BH-FDR(族=8,只对 gate1 big10 pass)--------
    fam = len(C.PRIMARY_FACTORS)
    g1p = g1[g1.gate1_big10_pass].copy()
    if len(g1p):
        passed, q, thr = C.bh_fdr(g1p.big10_is_p.values, ALPHA, fam)
        g1p["bh_q"] = q; g1p["bh_thr"] = thr; g1p["gate2_pass"] = passed
    else:
        g1p["bh_q"] = []; g1p["gate2_pass"] = []
    g2map = dict(zip(g1p.factor, g1p.gate2_pass)) if len(g1p) else {}
    g1p.to_csv(os.path.join(HERE, "gate2_fdr.csv"), index=False, encoding="utf-8-sig")
    print("  Gate2 BH-FDR(族=%d) pass: %d" % (fam, int(g1p.gate2_pass.sum()) if len(g1p) else 0))

    # -------- Gate3: 去冗余(big10 IS IC 序列正相关>0.7)--------
    g2pass = [f for f in C.PRIMARY_FACTORS if g2map.get(f, False)]
    g3rows = []; reps = []; negrows = []
    if len(g2pass) >= 1:
        ser = pd.DataFrame({f: ic_series[f] for f in g2pass}).dropna(how="all")
        corr = ser.corr(method="pearson")
        corr.to_csv(os.path.join(HERE, "gate3_corr_matrix.csv"), encoding="utf-8-sig")
        clusters = C.union_find_clusters(g2pass, corr, CORR_THR)
        tmap = dict(zip(g1.factor, g1.big10_is_t))
        for cid, members in enumerate(clusters):
            rep = sorted(members, key=lambda n: -abs(tmap[n]))[0]
            reps.append(rep)
            for n in members:
                g3rows.append({"factor": n, "cluster_id": cid, "cluster_size": len(members),
                               "members": "|".join(sorted(members)), "representative": rep,
                               "is_representative": (n == rep),
                               "corr_to_rep": round(float(corr.loc[n, rep]), 4),
                               "gate3_status": "keep" if n == rep else "gate3_redundant"})
        for i in range(len(g2pass)):
            for j in range(i + 1, len(g2pass)):
                c = corr.iloc[i, j]
                if c < NEG_THR:
                    negrows.append({"factor_a": g2pass[i], "factor_b": g2pass[j],
                                    "ic_corr": round(float(c), 4), "note": "potential_complement"})
    pd.DataFrame(g3rows).to_csv(os.path.join(HERE, "gate3_clusters.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(negrows, columns=["factor_a", "factor_b", "ic_corr", "note"]).to_csv(
        os.path.join(HERE, "gate3_negative_corr.csv"), index=False, encoding="utf-8-sig")
    g3rep = {r["factor"]: r["is_representative"] for r in g3rows}
    print("  Gate3: gate2pass=%d → 独立簇=%d 代表=%d 冗余=%d 负相关对=%d"
          % (len(g2pass), len(reps), len(reps), len(g3rows) - len(reps), len(negrows)))

    # -------- Gate4: 衰减(对代表)+ 全因子年度IC(牛熊分层)--------
    yic_rows = []
    for f in C.PRIMARY_FACTORS:
        yr = yearly_ic(df, f)
        row = {"factor": f}; row.update({"ic_%d" % y: round(yr[y], 5) for y in range(2020, 2026)})
        row["bear_2022"] = round(yr[2022], 5); row["bear_2023"] = round(yr[2023], 5)
        st, isic, oosic = C.decay_status_6y(yr)
        row["decay_status"] = st; row["is_era_ic"] = round(isic, 5); row["oos_era_ic"] = round(oosic, 5)
        yic_rows.append(row)
    yic = pd.DataFrame(yic_rows)
    yic.to_csv(os.path.join(HERE, "gate4_yearly_ic.csv"), index=False, encoding="utf-8-sig")
    decay_map = dict(zip(yic.factor, yic.decay_status))
    print("  Gate4 衰减(全因子): " + " ".join("%s=%s" % (r.factor, r.decay_status)
          for r in yic.itertuples()))

    # -------- final_verdict --------
    led = []
    for r in g1.itertuples():
        f = r.factor
        if r.big10_is_ndays < 30:
            fv = "insufficient_data"
        elif not r.gate1_big10_pass:
            fv = "super20_specific_candidate" if r.gate1_super20_pass else "gate1_fail"
        elif not g2map.get(f, False):
            fv = "gate2_fail"
        elif not g3rep.get(f, False):
            fv = "gate3_redundant"
        elif decay_map.get(f) == "decaying":
            fv = "gate_pass_but_decaying"
        else:
            fv = "gate_all_pass_candidate"
        led.append({"factor": f, "final_verdict": fv,
                    "big10_is_ic": round(r.big10_is_ic, 5), "big10_is_t": round(r.big10_is_t, 3),
                    "big10_is_p": round(r.big10_is_p, 5), "big10_oos_ic": round(r.big10_oos_ic, 5),
                    "big10_oos_t": round(r.big10_oos_t, 3), "oos_flip": r.oos_flip,
                    "super20_is_t": round(r.super20_is_t, 3), "gate1_big10_pass": r.gate1_big10_pass,
                    "gate2_pass": bool(g2map.get(f, False)),
                    "gate3_representative": bool(g3rep.get(f, False)),
                    "decay_status": decay_map.get(f, "n/a"),
                    "conditioned_on": "dragon_top12"})
    led = pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict), "红线:出现 robust_alpha!"
    led.to_csv(os.path.join(HERE, "factor_court_top12_ledger.csv"), index=False, encoding="utf-8-sig")
    print("\n=== final_verdict 分布 ===")
    print(led.final_verdict.value_counts().to_string())

    write_summary(df, g1, led, yic, reps, negrows, g2pass, bench_row,
                  sc1_rows, ok2, ok3, ok4, n2, fam, decay_map)
    print("\n[done] 报告 + CSV 已落盘于 factor_court_top12/")


def write_summary(df, g1, led, yic, reps, negrows, g2pass, bench_row,
                  sc1_rows, ok2, ok3, ok4, n2, fam, decay_map):
    L = []
    L.append("# 战车A 第二步·①验因子 — Top12 候选池内单因子四关法庭")
    L.append("")
    L.append("> **conditioned_on_dragon_top12(条件命题)**:本报告只回答"
             "「在 dragon Top12 最终幸存者池**内部**,哪些单因子还能区分赢家(big10)」。")
    L.append("> **不是**全市场 alpha、**不是**大预筛池选牛股、**不是**多因子评分、**不是** robust_alpha。"
             "只单因子审判,不组合/不调权重/不拼新score/不改 dragon_score。**2026 完全未碰**(holdout)。")
    L.append("")
    L.append("- 数据底座 event_study_dragon_2020_2026.csv;Top12池=v1/v2/v3并集去重 unique(date,code)。")
    L.append("- 切分:IS=2020-2023(%d) / OOS=2024-2025(%d) / **2026 holdout 未进任何计算**。"
             % ((df.seg == "IS").sum(), (df.seg == "OOS").sum()))
    L.append("- 主判据=is_big_meat_10(≥10%,池内逐日Spearman区分力,HAC lag=20);"
             "辅助=is_super_meat_20;连续周期 T3/T5/T10 Rank IC 作周期对照。")
    L.append("- 受审因子(族=%d):%s;benchmark=dragon_score(v3,仅对照)。" % (fam, ", ".join(C.PRIMARY_FACTORS)))
    L.append("")
    # 6 打乱自检
    L.append("## 1) 四关机制自检(每关)")
    L.append("- **Gate1 打乱 big10 归零(最关键)**:8 因子逐个打乱标签后,null IC 均值≈0、null HAC t 退回 N(0,1)(std≈1、显著率≈5%)。逐因子见 selfcheck_gate1_shuffle.csv。")
    for r in sc1_rows:
        L.append("  - %-18s null_ic=%.4f null_t_std=%.2f sig%%=%.0f%% → %s"
                 % (r["factor"], r["null_ic_mean"], r["null_t_std"], r["null_sig_pct"] * 100,
                    "归零✓" if r["gate1_shuffle_zero_pass"] else "✗"))
    L.append("- Gate2 噪声 FDR 自检:20 个 N(0,1) 噪声,BH-FDR 通过 %d 个(应≈0)→ %s" % (n2, "✓" if ok2 else "✗"))
    L.append("- Gate3 合成相关自检:A~B 同簇、A≠C、A/D 强负相关标互补 → %s" % ("✓" if ok3 else "✗"))
    L.append("- Gate4 人造衰减自检:stable/warning/decaying/reversal 4/4 判对 → %s" % ("✓" if ok4 else "✗"))
    L.append("")
    # 1 每因子 big10
    L.append("## 2) 每因子对 big10 结果(IS 锁方向,OOS 验不翻向)")
    L.append("| 因子 | IS IC | IS t | IS p | OOS IC | OOS t | OOS翻向 | Gate1 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in g1.itertuples():
        L.append("| %s | %+.4f | %+.2f | %.3f | %+.4f | %+.2f | %s | %s |"
                 % (r.factor, r.big10_is_ic, r.big10_is_t, r.big10_is_p, r.big10_oos_ic,
                    r.big10_oos_t, "是" if r.oos_flip else "否", "pass" if r.gate1_big10_pass else "fail"))
    L.append("| **%s** | %+.4f | %+.2f | %.3f | %+.4f | %+.2f | — | benchmark |"
             % (bench_row["factor"], bench_row["big10_is_ic"], bench_row["big10_is_t"],
                bench_row["big10_is_p"], bench_row["big10_oos_ic"], bench_row["big10_oos_t"]))
    L.append("")
    # 2 super20 对照
    L.append("## 3) 每因子 super20 对照(≥20% 大肉能力)")
    L.append("| 因子 | super20 IS IC | IS t | IS p | OOS翻向 | super20_pass |")
    L.append("|---|---|---|---|---|---|")
    for r in g1.itertuples():
        L.append("| %s | %+.4f | %+.2f | %.3f | %s | %s |"
                 % (r.factor, r.super20_is_ic, r.super20_is_t, r.super20_is_p,
                    "是" if r.super20_oos_flip else "否", "pass" if r.gate1_super20_pass else "fail"))
    L.append("")
    # 连续周期
    L.append("## 4) 连续前向收益 Rank IC(IS,看哪个周期最强;big10为主判据)")
    L.append("| 因子 | T3 IC(t) | T5 IC(t) | T10 IC(t) |")
    L.append("|---|---|---|---|")
    for r in g1.itertuples():
        L.append("| %s | %+.4f(%+.1f) | %+.4f(%+.1f) | %+.4f(%+.1f) |"
                 % (r.factor, r.fwd_T3_is_ic, r.fwd_T3_is_t, r.fwd_T5_is_ic, r.fwd_T5_is_t,
                    r.fwd_T10_is_ic, r.fwd_T10_is_t))
    L.append("> 注:连续收益 IC 与 big10(触及)可能方向相反——高动量票易盘中触+10%但持有到收盘回落。big10 为主判据。")
    L.append("")
    # 4 牛熊分层
    L.append("## 5) ★牛熊年份分层(big10 池内区分力,逐年;2026未计)")
    L.append("| 因子 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | IS期 | OOS期 | 衰减 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in yic.itertuples():
        L.append("| %s | %+.3f | %+.3f | **%+.3f** | **%+.3f** | %+.3f | %+.3f | %+.3f | %+.3f | %s |"
                 % (r.factor, r.ic_2020, r.ic_2021, r.bear_2022, r.bear_2023, r.ic_2024, r.ic_2025,
                    r.is_era_ic, r.oos_era_ic, r.decay_status))
    L.append("> 核心问题:因子在 2022/2023 熊市还成立吗?看 bear 两列符号是否与 IS 方向一致、是否归零/反向。")
    L.append("")
    # 5 漏斗
    n_g1 = int(g1.gate1_big10_pass.sum())
    n_g2 = len(g2pass)
    vc = led.final_verdict.value_counts().to_dict()
    L.append("## 6) Gate1-4 漏斗")
    L.append("```")
    L.append("受审单因子(族): %d" % fam)
    L.append("-> Gate1 big10 通过(IS显著+OOS不翻向): %d" % n_g1)
    L.append("-> Gate2 BH-FDR(族=%d)通过: %d" % (fam, n_g2))
    L.append("-> Gate3 去冗余后独立信号(代表): %d" % len(reps))
    L.append("-> Gate4 代表中 decaying: %d" % sum(1 for f in reps if decay_map.get(f) == "decaying"))
    L.append("-> gate_all_pass_candidate: %d" % vc.get("gate_all_pass_candidate", 0))
    L.append("```")
    L.append("")
    L.append("## 7) 去冗余后剩几个独立信号")
    L.append("- 独立簇代表(%d 个):%s" % (len(reps), ", ".join(reps) if reps else "无"))
    if negrows:
        L.append("- 强负相关(potential_complement,不判冗余):"
                 + "; ".join("%s vs %s(%.2f)" % (n["factor_a"], n["factor_b"], n["ic_corr"]) for n in negrows))
    else:
        L.append("- 无 corr<-0.7 的强负相关对。")
    L.append("")
    L.append("## 8) dragon_score benchmark 对照")
    L.append("- dragon_score(v3) big10 IS IC=%+.4f t=%+.2f / OOS IC=%+.4f t=%+.2f。"
             % (bench_row["big10_is_ic"], bench_row["big10_is_t"],
                bench_row["big10_oos_ic"], bench_row["big10_oos_t"]))
    L.append("- ★它是 benchmark(在自己选出的 Top12 内的自指标),**不是主候选**,不进 FDR 族、不参与去冗余。仅供单因子强弱参照。")
    L.append("")
    L.append("## 9) final_verdict 分布")
    for k, v in led.final_verdict.value_counts().items():
        L.append("- %s: %d (%s)" % (k, v, ", ".join(led[led.final_verdict == k].factor.tolist())))
    L.append("")
    L.append("## 10) ★声明(必读)")
    L.append("- 本报告是 **Top12 条件池内单因子验证**,标签 **conditioned_on_dragon_top12**。")
    L.append("- **不是**全市场 alpha、**不是**从大预筛池选牛股、**不是**多因子评分、**不是** robust_alpha。")
    L.append("- 只单因子审判:未组合、未调权重、未拼新 score、未改 dragon_score。")
    L.append("- **2026 全程未碰**(Final holdout):不用于调规则/选因子/任何 Gate。")
    L.append("- gate_all_pass_candidate 仅表示「在本四关口径下,该单因子在 Top12 内对 big10 仍有显著且未翻向、非冗余、未衰减的区分力」,**不等于可实盘、不等于新 alpha**。")
    L.append("")
    with open(os.path.join(HERE, "factor_court_top12_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
