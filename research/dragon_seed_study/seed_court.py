# -*- coding: utf-8 -*-
"""Top250 seed 池·hold_T5 单因子四关法庭(全量)+ A/B 判定。

★conditioned_on_dragon_seed(已涨已放量条件池:ret3_top∪成交额top→6因子预筛 Top250)。
主标签=**hold_T5(可交易:买entry open卖T+5 close、排除day1、T+1合法)**;辅 hold_T3/T10。
big10/super20 仅触及对照,不参与 verdict。**只单因子,不组合,2026不碰**(panel本就到2025-12-31)。
final_verdict ∈ {gate1_fail,gate2_fail,gate3_redundant,gate_pass_but_decaying,
                 gate_all_pass_candidate,insufficient_data}。严禁robust_alpha。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
_FC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dragon_event_study", "factor_court_top12")
sys.path.insert(0, _FC)
import core as C   # 复用纯统计

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(HERE, "seed250_panel_2020_2025.csv")
TOP12_TRADABLE_G1 = os.path.join(os.path.dirname(_FC), "factor_court_top12_tradable",
                                 "factor_court_top12_tradable_gate1.csv")
ALPHA = 0.05; CORR_THR = 0.7; NEG_THR = -0.7
FACTORS = ["open_ratio", "auc_ratio", "auc_amount", "close_to_high",
           "ret3", "avg_money", "close_to_20d_high", "avg_range"]
SEED_RELATED = {                         # ★自指标注
    "ret3": "seed ret3_top160(直接自指)",
    "avg_money": "seed money_top + 预筛 avg_money_5/10(直接自指)",
    "close_to_20d_high": "预筛6因子(0.15权,自指)",
    "avg_range": "预筛 range_10(0.15权,自指)",
    "open_ratio": "", "auc_ratio": "", "auc_amount": "", "close_to_high": "",
}
MAIN = "hold_T5"
LAG = {"hold_T3": 3, "hold_T5": 5, "hold_T10": 10}
BEAR = [2022, 2023]


def load():
    d = pd.read_csv(PANEL, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    assert d["year"].max() == 2025 and (d["year"] == 2026).sum() == 0, "红线:2026!"
    d["seg"] = np.where(d.year <= 2023, "IS", "OOS")
    return d


# ---- 自检(复用前轮口径)----
def sc_gate1(df):
    rows = []; ok = True
    for f in FACTORS:
        nmu, nt, real = C.shuffle_null(df, f, MAIN, LAG[MAIN], "IS", n_shuffle=120, seed=42)
        nm = float(np.mean(nmu)); ts = float(np.std(nt)); sig = float(np.mean(np.abs(nt) > 1.96))
        p = abs(nm) < 0.01 and ts < 1.5 and sig < 0.15
        ok = ok and p
        rows.append({"factor": f, "null_ic_mean": round(nm, 5), "null_t_std": round(ts, 3),
                     "null_sig_pct": round(sig, 3), "pass": bool(p)})
    return rows, ok


def sc_gate2():
    rng = np.random.RandomState(20); tn = rng.randn(20)
    pn = np.array([C.two_sided_p(t) for t in tn])
    passed, _, _ = C.bh_fdr(pn, ALPHA, 20)
    return int(passed.sum()) <= 1, int(passed.sum())


def sc_gate3():
    rng = np.random.RandomState(3)
    A = rng.randn(200); B = A + .05 * rng.randn(200); Cc = rng.randn(200); D = -A + .05 * rng.randn(200)
    nm = ["A", "B", "Cc", "D"]; M = pd.DataFrame(np.corrcoef([A, B, Cc, D]), index=nm, columns=nm)
    cl = {n: i for i, c in enumerate(C.union_find_clusters(nm, M, CORR_THR)) for n in c}
    return (cl["A"] == cl["B"]) and (cl["A"] != cl["Cc"]) and (cl["A"] != cl["D"]) and (M.loc["A", "D"] < NEG_THR)


def sc_gate4():
    cs = {"stable": {2020: .03, 2021: .03, 2022: .031, 2023: .029, 2024: .03, 2025: .029},
          "warning": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .02, 2025: .016},
          "decaying": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .012, 2025: .008},
          "reversal": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .005, 2025: -.01}}
    ex = {"stable": "stable", "warning": "decay_warning", "decaying": "decaying", "reversal": "decaying"}
    return all(C.decay_status_6y(v)[0] == ex[k] for k, v in cs.items())


def yearly(df, factor, label=MAIN):
    return {y: (float(C.daily_ic_series(df[df.year == y], factor, label).mean())
                if len(df[df.year == y]) else np.nan) for y in range(2020, 2026)}


def main():
    print("=" * 76)
    print("Top250 seed·hold_T5 四关法庭(全量) — conditioned_on_dragon_seed")
    print("=" * 76)
    d = load()
    print("行=%d IS=%d OOS=%d 2026=%d | hold_T5有效=%d" % (
        len(d), (d.seg == "IS").sum(), (d.seg == "OOS").sum(), (d.year == 2026).sum(),
        d[MAIN].notna().sum()))

    # 自检
    sc1, ok1 = sc_gate1(d); ok2, n2 = sc_gate2(); ok3 = sc_gate3(); ok4 = sc_gate4()
    pd.DataFrame(sc1).to_csv(os.path.join(HERE, "seed_court_selfcheck.csv"), index=False, encoding="utf-8-sig")
    print("自检: Gate1打乱归零=%s Gate2噪声FDR(过%d)=%s Gate3合成=%s Gate4衰减=%s" % (ok1, n2, ok2, ok3, ok4))
    if not (ok1 and ok2 and ok3 and ok4):
        print("SELF_CHECK_FAILED — 停止"); return

    # 跨池 Top12 可交易 holdT5 参照
    xpool = {}
    if os.path.exists(TOP12_TRADABLE_G1):
        t12 = pd.read_csv(TOP12_TRADABLE_G1)
        xpool = dict(zip(t12.factor, t12.holdT5_is_ic))

    # Gate1 逐因子(hold_T5 主 + T3/T10 辅)
    rows = []; ic_ser = {}
    for f in FACTORS:
        ris, sis = C.gate1_eval(d, f, MAIN, LAG[MAIN], "IS")
        ros, _ = C.gate1_eval(d, f, MAIN, LAG[MAIN], "OOS")
        dir_is = int(np.sign(ris["mean_ic"]))
        flip = np.sign(ros["mean_ic"]) != dir_is
        r3, _ = C.gate1_eval(d, f, "hold_T3", LAG["hold_T3"], "IS")
        r10, _ = C.gate1_eval(d, f, "hold_T10", LAG["hold_T10"], "IS")
        yr = yearly(d, f)
        bear_ok = (np.sign(yr[2022]) == dir_is) and (np.sign(yr[2023]) == dir_is)
        x12 = xpool.get(f, np.nan)
        xrev = (x12 == x12) and (np.sign(x12) != dir_is)
        ic_ser[f] = sis
        rows.append(dict(
            factor=f, seed_related=bool(SEED_RELATED[f]), seed_note=SEED_RELATED[f],
            is_ic=ris["mean_ic"], is_t=ris["hac_t"], is_p=ris["p_two_sided"], n_days=ris["n_days"],
            oos_ic=ros["mean_ic"], oos_t=ros["hac_t"], oos_p=ros["p_two_sided"],
            direction=dir_is, oos_flip=bool(flip),
            holdT3_is_ic=r3["mean_ic"], holdT3_is_t=r3["hac_t"],
            holdT10_is_ic=r10["mean_ic"], holdT10_is_t=r10["hac_t"],
            ic_2020=yr[2020], ic_2021=yr[2021], ic_2022=yr[2022], ic_2023=yr[2023],
            ic_2024=yr[2024], ic_2025=yr[2025], bear_holds=bool(bear_ok),
            top12_holdT5_is_ic=x12, cross_pool_sign_reversal=bool(xrev)))
    g1 = pd.DataFrame(rows)
    g1["gate1_pass"] = (g1.is_p < ALPHA) & (~g1.oos_flip)
    g1["is_sig"] = g1.is_p < ALPHA
    g1["oos_sig"] = g1.oos_p < ALPHA
    g1.to_csv(os.path.join(HERE, "seed_court_gate1.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ic_ser).to_csv(os.path.join(HERE, "seed_court_daily_ic_holdT5_is.csv"), encoding="utf-8-sig")
    print("Gate1 pass(IS显著+OOS不翻向): %d/8" % g1.gate1_pass.sum())

    # Gate2 BH-FDR(族=8,对 gate1 pass)
    gp = g1[g1.gate1_pass].copy()
    if len(gp):
        passed, q, thr = C.bh_fdr(gp.is_p.values, ALPHA, len(FACTORS))
        gp["bh_q"] = q; gp["gate2_pass"] = passed
    g2map = dict(zip(gp.factor, gp.gate2_pass)) if len(gp) else {}
    gp.to_csv(os.path.join(HERE, "seed_court_gate2_fdr.csv"), index=False, encoding="utf-8-sig")
    print("Gate2 BH-FDR pass: %d" % (int(gp.gate2_pass.sum()) if len(gp) else 0))

    # Gate3 去冗余(hold_T5 IS IC 序列正相关>0.7)
    g2p = [f for f in FACTORS if g2map.get(f)]
    reps = []; g3rows = []; negs = []
    if len(g2p) >= 1:
        ser = pd.DataFrame({f: ic_ser[f] for f in g2p}).dropna(how="all")
        corr = ser.corr()
        corr.to_csv(os.path.join(HERE, "seed_court_gate3_corr.csv"), encoding="utf-8-sig")
        clusters = C.union_find_clusters(g2p, corr, CORR_THR)
        tmap = dict(zip(g1.factor, g1.is_t))
        for cid, mem in enumerate(clusters):
            rep = sorted(mem, key=lambda n: -abs(tmap[n]))[0]; reps.append(rep)
            for n in mem:
                g3rows.append(dict(factor=n, cluster=cid, members="|".join(sorted(mem)),
                                   representative=rep, is_rep=(n == rep),
                                   status="keep" if n == rep else "gate3_redundant"))
        for i in range(len(g2p)):
            for j in range(i + 1, len(g2p)):
                if corr.iloc[i, j] < NEG_THR:
                    negs.append(dict(a=g2p[i], b=g2p[j], corr=round(float(corr.iloc[i, j]), 3)))
    pd.DataFrame(g3rows).to_csv(os.path.join(HERE, "seed_court_gate3_clusters.csv"), index=False, encoding="utf-8-sig")
    g3rep = {r["factor"]: r["is_rep"] for r in g3rows}
    print("Gate3 独立信号(代表): %d" % len(reps))

    # Gate4 衰减(hold_T5 年度;2026不参与)
    g4rows = []
    for f in FACTORS:
        yr = {y: g1[g1.factor == f]["ic_%d" % y].iloc[0] for y in range(2020, 2026)}
        st, isera, oosera = C.decay_status_6y(yr)
        g4rows.append(dict(factor=f, decay_status=st, is_era=round(isera, 5), oos_era=round(oosera, 5)))
    g4 = pd.DataFrame(g4rows)
    g4.to_csv(os.path.join(HERE, "seed_court_gate4_decay.csv"), index=False, encoding="utf-8-sig")
    decay_map = dict(zip(g4.factor, g4.decay_status))

    # final_verdict
    led = []
    for r in g1.itertuples():
        f = r.factor
        if r.n_days < 30:
            fv = "insufficient_data"
        elif not r.gate1_pass:
            fv = "gate1_fail"
        elif not g2map.get(f):
            fv = "gate2_fail"
        elif not g3rep.get(f):
            fv = "gate3_redundant"
        elif decay_map.get(f) == "decaying":
            fv = "gate_pass_but_decaying"
        else:
            fv = "gate_all_pass_candidate"
        led.append(dict(factor=f, seed_related=r.seed_related, final_verdict=fv,
                        is_ic=round(r.is_ic, 5), is_t=round(r.is_t, 2), is_p=round(r.is_p, 4),
                        oos_ic=round(r.oos_ic, 5), oos_t=round(r.oos_t, 2), oos_p=round(r.oos_p, 4),
                        oos_flip=r.oos_flip, bear_holds=r.bear_holds,
                        cross_pool_sign_reversal=r.cross_pool_sign_reversal,
                        decay=decay_map.get(f), conditioned_on="dragon_seed"))
    led = pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict)
    led.to_csv(os.path.join(HERE, "seed_court_ledger.csv"), index=False, encoding="utf-8-sig")

    # ===== A/B 判定 =====
    # A 因子:干净(非自指) + IS&OOS 都显著 + OOS不翻向 + 熊市2022&2023成立
    jA = g1[(~g1.seed_related) & g1.is_sig & g1.oos_sig & (~g1.oos_flip) & g1.bear_holds]
    verdict = "A" if len(jA) else "B"
    print("\n=== final_verdict 分布 ===")
    print(led.final_verdict.value_counts().to_string())
    print("\n=== A/B 判定: 落 %s ===" % verdict)
    if verdict == "A":
        print("满足全四条的干净因子:", jA.factor.tolist())

    write_report(d, g1, led, g4, reps, negs, g2map, g3rep, decay_map, jA, verdict,
                 sc1, n2, ok2, ok3, ok4)
    print("\n[done] 报告+CSV 落盘 dragon_seed_study/")


def write_report(d, g1, led, g4, reps, negs, g2map, g3rep, decay_map, jA, verdict,
                 sc1, n2, ok2, ok3, ok4):
    def row(f):
        return g1[g1.factor == f].iloc[0]
    L = []
    L.append("# Top250 seed 池·hold_T5 单因子四关法庭 — 报告 + A/B 判定")
    L.append("")
    L.append("> **conditioned_on_dragon_seed**(已涨已放量条件池:ret3_top∪成交额top→6因子预筛Top250,比Top12宽但仍是条件命题)。")
    L.append("> 主标签=**可交易 hold_T5**(买entry open卖T+5 close、排除day1、T+1合法);辅 hold_T3/T10。"
             "**不是**全市场alpha、**不是**多因子评分、**不是**robust_alpha。只单因子。**2026未碰**(panel到2025-12-31)、**未计成本**。")
    L.append("- 切分:IS=2020-2023(%d) / OOS=2024-2025(%d) / 2026=0。8因子,族=8。" % (
        (d.seg == "IS").sum(), (d.seg == "OOS").sum()))
    L.append("")
    L.append("## 0) ★自指标注(关键)")
    L.append("Top250 selection 用了 ret3 + 成交额 + 预筛6因子(avg_money_5/10,ret_5/10,close_to_20d_high,range_10):")
    L.append("| 因子 | 自指? | 说明 |")
    L.append("|---|---|---|")
    for f in FACTORS:
        L.append("| %s | %s | %s |" % (f, "★自指" if SEED_RELATED[f] else "干净",
                                       SEED_RELATED[f] or "非seed/预筛逻辑"))
    L.append("> ★真信号标准 = 干净(非自指) + 可交易 IS&OOS 都显著 + OOS不翻向 + 熊市成立。自指因子即便显著也存循环自证嫌疑。")
    L.append("")
    L.append("## 1) 机制自检(四关)")
    L.append("- Gate1 打乱 hold_T5 归零:8因子逐个打乱后 null IC≈0、t退回N(0,1)。详 seed_court_selfcheck.csv。")
    L.append("- Gate2 噪声FDR:20噪声通过 %d(应≈0)→ %s;Gate3 合成聚类 → %s;Gate4 人造衰减 → %s。" % (
        n2, "✓" if ok2 else "✗", "✓" if ok3 else "✗", "✓" if ok4 else "✗"))
    L.append("")
    L.append("## 2) 每因子 hold_T5 IS/OOS(主判据)+ 跨池对照")
    L.append("| 因子 | 自指 | IS IC | IS t | IS p | OOS IC | OOS t | OOS p | OOS翻向 | Top12可交易IC | 跨池反转 | Gate1 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for f in FACTORS:
        r = row(f)
        x = ("%+.4f" % r.top12_holdT5_is_ic) if r.top12_holdT5_is_ic == r.top12_holdT5_is_ic else "NA"
        L.append("| %s | %s | %+.4f | %+.2f | %.3f | %+.4f | %+.2f | %.3f | %s | %s | %s | %s |" % (
            f, "★" if r.seed_related else "", r.is_ic, r.is_t, r.is_p, r.oos_ic, r.oos_t, r.oos_p,
            "是" if r.oos_flip else "否", x, "★是" if r.cross_pool_sign_reversal else "否",
            "pass" if r.gate1_pass else "fail"))
    L.append("> ★open_ratio 跨池方向反转:Top250 为正、上轮 Top12 可交易为负 → **不是稳定跨池信号**,池子一变方向就反。")
    L.append("")
    L.append("## 3) hold_T3 / T10 周期对照(IS)")
    L.append("| 因子 | T3 IC(t) | T5 IC(t) | T10 IC(t) |")
    L.append("|---|---|---|---|")
    for f in FACTORS:
        r = row(f)
        L.append("| %s | %+.4f(%+.1f) | %+.4f(%+.1f) | %+.4f(%+.1f) |" % (
            f, r.holdT3_is_ic, r.holdT3_is_t, r.is_ic, r.is_t, r.holdT10_is_ic, r.holdT10_is_t))
    L.append("")
    L.append("## 4) ★牛熊分层(hold_T5 年度 IC;熊市 2022/2023 是判定关键)")
    L.append("| 因子 | 自指 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | 熊市成立? |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for f in FACTORS:
        r = row(f)
        L.append("| %s | %s | %+.3f | %+.3f | **%+.3f** | **%+.3f** | %+.3f | %+.3f | %s |" % (
            f, "★" if r.seed_related else "", r.ic_2020, r.ic_2021, r.ic_2022, r.ic_2023,
            r.ic_2024, r.ic_2025, "✓成立" if r.bear_holds else "✗(熊市翻向/不成立)"))
    L.append("> 熊市成立 = 2022 与 2023 年度 IC 方向都与 IS 锁定方向一致。")
    L.append("")
    n_g1 = int(g1.gate1_pass.sum()); n_g2 = sum(1 for f in FACTORS if g2map.get(f))
    L.append("## 5) Gate1-4 漏斗 + verdict 分布")
    L.append("```")
    L.append("受审 8 因子(4自指 + 4干净)")
    L.append("-> Gate1 pass(IS显著+OOS不翻向): %d" % n_g1)
    L.append("-> Gate2 BH-FDR(族=8): %d" % n_g2)
    L.append("-> Gate3 独立信号(代表): %d" % len(reps))
    L.append("-> Gate4 decaying: %d" % sum(1 for f in reps if decay_map.get(f) == "decaying"))
    L.append("```")
    for k, v in led.final_verdict.value_counts().items():
        L.append("- %s: %d (%s)" % (k, v, ", ".join(led[led.final_verdict == k].factor)))
    if negs:
        L.append("- 强负相关(potential_complement): " + "; ".join("%s/%s(%.2f)" % (n["a"], n["b"], n["corr"]) for n in negs))
    L.append("")
    L.append("## 6) ★★ A/B 判定(本步是入场选股能否找到 edge 的最后确认)")
    L.append("")
    L.append("**判定标准 A** = 存在因子同时满足:① 干净(非自指)② 可交易 hold_T5 下 IS&OOS 都显著 "
             "③ OOS 不翻向 ④ 熊市 2022&2023 都成立。")
    L.append("")
    if verdict == "A":
        L.append("### → 落【判定 A:入场选股有救】")
        L.append("同时满足全四条的干净因子:**%s**" % ", ".join(jA.factor.tolist()))
        for f in jA.factor:
            r = row(f)
            L.append("- %s:IS IC=%+.4f(p=%.3f)、OOS IC=%+.4f(p=%.3f)、熊市2022=%+.3f/2023=%+.3f、跨池反转=%s" % (
                f, r.is_ic, r.is_p, r.oos_ic, r.oos_p, r.ic_2022, r.ic_2023,
                "★是(警示)" if r.cross_pool_sign_reversal else "否"))
    else:
        L.append("### → 落【判定 B:入场选股边际薄】")
        L.append("**没有任何因子同时满足全四条**。逐因子卡在哪一条:")
        L.append("")
        L.append("| 因子 | 干净? | IS显著 | OOS显著 | OOS不翻向 | 熊市成立 | 卡在 |")
        L.append("|---|---|---|---|---|---|---|")
        for f in FACTORS:
            r = row(f)
            clean = not r.seed_related
            fails = []
            if not clean: fails.append("自指")
            if not r.is_sig: fails.append("IS不显著")
            if not r.oos_sig: fails.append("OOS不显著")
            if r.oos_flip: fails.append("OOS翻向")
            if not r.bear_holds: fails.append("熊市不成立")
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                f, "是" if clean else "否(自指)", "✓" if r.is_sig else "✗",
                "✓" if r.oos_sig else "✗", "✓" if not r.oos_flip else "✗",
                "✓" if r.bear_holds else "✗", ", ".join(fails) if fails else "—(全过?)"))
    L.append("")
    L.append("> 只摆事实判定,**不替你下「该不该转向」的决定**。")
    L.append("")
    L.append("## 声明")
    L.append("- conditioned_on_dragon_seed、可交易 hold_T5;**不是**全市场alpha、**不是**多因子评分、**不是**robust_alpha。")
    L.append("- 只单因子;**2026未碰**;**未计交易成本/冲击**(计了更差)。")
    with open(os.path.join(HERE, "seed_court_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
