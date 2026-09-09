# -*- coding: utf-8 -*-
"""Top250 seed 池·打板次日(hold_T1)四关法庭(全量)+ T1-T20 衰减曲线 + 次日胜率 + A/B 判定。

★铁律:hold_T1..hold_T20 衰减矩阵**仅描述因子随持有期的形态**(短线/长持/无效),
       **绝不用 T6-T20 参与 A/B 判定或给因子平反**。主判据 = **hold_T1(打板次日)**(辅 T3/T5)。
       open_ratio 在 T1 翻车就是翻车,不准用某晚周期好看翻案。
conditioned_on_dragon_seed;买 entry(T) open、卖 T+N close(close[i0+N]/open[i0])、T+1合法、排除day1(0天)。
2026 未碰(panel 到 2025-12-31)、未计成本。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["REPRO_BACKEND"] = "warehouse"
_DRAGON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dragon_event_study")
_FC = os.path.join(_DRAGON, "factor_court_top12")
sys.path.insert(0, _FC); sys.path.insert(0, _DRAGON)
import core as C
import repro_core as R

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(HERE, "seed250_panel_2020_2025.csv")
BASE12 = os.path.join(_DRAGON, "event_study_dragon_2020_2026.csv")
AUG12 = os.path.join(_FC, "_factors_augmented.csv")
ALPHA = 0.05; CORR_THR = 0.7; NEG_THR = -0.7; MAXP = 20
FACTORS = ["open_ratio", "auc_ratio", "auc_amount", "close_to_high",
           "ret3", "avg_money", "close_to_20d_high", "avg_range"]
SEED_RELATED = {"ret3": "seed ret3_top160", "avg_money": "seed money_top+预筛avg_money",
                "close_to_20d_high": "预筛6因子(0.15权)", "avg_range": "预筛 range_10(0.15权)",
                "open_ratio": "", "auc_ratio": "", "auc_amount": "", "close_to_high": ""}
MAIN = "hold_T1"; AUX = ["hold_T3", "hold_T5"]; BEAR = [2022, 2023]


def load_panel_with_fwd():
    d = pd.read_csv(PANEL, dtype={"entry_date": str, "code": str}).reset_index(drop=True)
    d["year"] = d["entry_date"].str[:4].astype(int)
    assert d["year"].max() == 2025 and (d["year"] == 2026).sum() == 0
    d["seg"] = np.where(d.year <= 2023, "IS", "OOS")
    # 建 hold_T1..hold_T20 前向矩阵(close[i0+N]/open[i0];2026价格不加载→超窗NaN)
    codes = sorted(d.code.unique())
    panel = R.load_daily_panel(codes, "20200101", "20251231")
    fwd = np.full((len(d), MAXP), np.nan)
    for code, grp in d.groupby("code", sort=False):
        p = panel.get(code)
        if p is None or len(p) == 0:
            continue
        pos = {dt: i for i, dt in enumerate(p.index)}
        o = p["open"].astype(float).values; c = p["close"].astype(float).values; L = len(c)
        for ridx, ed in zip(grp.index, grp["entry_date"]):
            i0 = pos.get(ed)
            if i0 is None or o[i0] <= 0:
                continue
            buy = o[i0]
            for N in range(1, MAXP + 1):
                j = i0 + N
                if j < L:
                    fwd[ridx, N - 1] = (c[j] / buy - 1.0) * 100
    for N in range(1, MAXP + 1):
        d["hold_T%d" % N] = fwd[:, N - 1]
    return d


# ---- 自检(复用前轮口径)----
def selfchecks(df):
    rows = []; ok1 = True
    for f in FACTORS:
        nmu, nt, real = C.shuffle_null(df, f, MAIN, 1, "IS", n_shuffle=120, seed=42)
        nm = float(np.mean(nmu)); ts = float(np.std(nt)); sig = float(np.mean(np.abs(nt) > 1.96))
        p = abs(nm) < 0.01 and ts < 1.5 and sig < 0.15
        ok1 = ok1 and p
        rows.append(dict(factor=f, null_ic_mean=round(nm, 5), null_t_std=round(ts, 3),
                         null_sig_pct=round(sig, 3), shuffle_zero_pass=bool(p)))
    rng = np.random.RandomState(20); pn = np.array([C.two_sided_p(t) for t in rng.randn(20)])
    ok2 = int(C.bh_fdr(pn, ALPHA, 20)[0].sum()) <= 1
    rng = np.random.RandomState(3); A = rng.randn(200); B = A + .05 * rng.randn(200)
    Cc = rng.randn(200); D = -A + .05 * rng.randn(200)
    M = pd.DataFrame(np.corrcoef([A, B, Cc, D]), index=["A", "B", "Cc", "D"], columns=["A", "B", "Cc", "D"])
    cl = {n: i for i, c in enumerate(C.union_find_clusters(["A", "B", "Cc", "D"], M, CORR_THR)) for n in c}
    ok3 = cl["A"] == cl["B"] and cl["A"] != cl["Cc"] and cl["A"] != cl["D"] and M.loc["A", "D"] < NEG_THR
    cs = {"stable": {2020: .03, 2021: .03, 2022: .031, 2023: .029, 2024: .03, 2025: .029},
          "decaying": {2020: .03, 2021: .03, 2022: .03, 2023: .03, 2024: .012, 2025: .008}}
    ok4 = C.decay_status_6y(cs["stable"])[0] == "stable" and C.decay_status_6y(cs["decaying"])[0] == "decaying"
    return rows, ok1, ok2, ok3, ok4


def yearly(df, factor, label):
    return {y: (float(C.daily_ic_series(df[df.year == y], factor, label).mean())
                if len(df[df.year == y]) else np.nan) for y in range(2020, 2026)}


def winrate(df, factor, seg, direction, q=5):
    """每日按因子值分 q 组,各组次日(hold_T1)胜率(>0比例)。返回 (基准, 各组胜率list, 选好组WR, 排最差组WR)。"""
    sub = df[(df.seg == seg) & df[factor].notna() & df[MAIN].notna()].copy()
    base = float((sub[MAIN] > 0).mean())
    def _q(x):
        if x.nunique() < q:
            return pd.Series(np.nan, index=x.index)
        return pd.qcut(x.rank(method="first"), q, labels=False)
    sub["g"] = sub.groupby("entry_date")[factor].transform(_q)
    sub = sub.dropna(subset=["g"])
    wr = [float((sub[sub.g == i][MAIN] > 0).mean()) for i in range(q)]
    # 因子方向:正→好组=高分组(g=q-1),差组=低分组(g=0);负→反之
    good_g = q - 1 if direction > 0 else 0
    bad_g = 0 if direction > 0 else q - 1
    sel = float((sub[sub.g == good_g][MAIN] > 0).mean())
    excl = float((sub[sub.g != bad_g][MAIN] > 0).mean())
    return base, wr, sel, excl


def top12_holdT1_ic():
    """Top12 池 hold_T1(=底座 day2)IS IC(跨池对照)。"""
    b = pd.read_csv(BASE12, dtype={"entry_date": str, "code": str})
    b["year"] = b["entry_date"].str[:4].astype(int)
    b = b[b.year <= 2025].drop_duplicates(["entry_date", "code"])
    b["seg"] = np.where(b.year <= 2023, "IS", "OOS")
    b["hold_T1"] = b["day2"]
    if os.path.exists(AUG12):
        aug = pd.read_csv(AUG12, dtype={"entry_date": str, "code": str})
        b = b.merge(aug, on=["entry_date", "code"], how="left", suffixes=("", "_aug"))
    out = {}
    for f in FACTORS:
        if f in b.columns:
            r, _ = C.gate1_eval(b, f, "hold_T1", 1, "IS")
            out[f] = r["mean_ic"]
    return out


def main():
    print("=" * 78)
    print("Top250 seed·打板次日 hold_T1 四关法庭 + T1-T20衰减(铁律:衰减仅观察,取舍只认T1)")
    print("=" * 78)
    d = load_panel_with_fwd()
    print("行=%d IS=%d OOS=%d 2026=%d | hold_T1有效=%d" % (
        len(d), (d.seg == "IS").sum(), (d.seg == "OOS").sum(), (d.year == 2026).sum(), d[MAIN].notna().sum()))

    sc, ok1, ok2, ok3, ok4 = selfchecks(d)
    pd.DataFrame(sc).to_csv(os.path.join(HERE, "seed_t1_selfcheck.csv"), index=False, encoding="utf-8-sig")
    print("自检: 打乱hold_T1归零=%s 噪声FDR=%s 合成=%s 衰减=%s" % (ok1, ok2, ok3, ok4))
    if not (ok1 and ok2 and ok3 and ok4):
        print("SELF_CHECK_FAILED"); return

    # ===== T1-T20 衰减矩阵(描述性,IS/OOS Rank IC + HAC t)=====
    print("\n[衰减] 算 T1-T20 IC 矩阵(仅观察形态)...")
    dec_rows = []
    for f in FACTORS:
        row = {"factor": f, "seed_related": bool(SEED_RELATED[f])}
        for N in range(1, MAXP + 1):
            ri, _ = C.gate1_eval(d, f, "hold_T%d" % N, N, "IS")
            ro, _ = C.gate1_eval(d, f, "hold_T%d" % N, N, "OOS")
            row["is_ic_T%d" % N] = round(ri["mean_ic"], 5); row["is_t_T%d" % N] = round(ri["hac_t"], 2)
            row["oos_ic_T%d" % N] = round(ro["mean_ic"], 5)
        dec_rows.append(row)
    dec = pd.DataFrame(dec_rows)
    dec.to_csv(os.path.join(HERE, "seed_t1_decay_matrix.csv"), index=False, encoding="utf-8-sig")
    # 形态标注(描述性)
    shape = {}
    for f in FACTORS:
        r = dec[dec.factor == f].iloc[0]
        early = any(abs(r["is_t_T%d" % N]) > 1.96 for N in [1, 2, 3])
        late = any(abs(r["is_t_T%d" % N]) > 1.96 for N in range(10, 21))
        s1 = np.sign(r["is_ic_T1"]); slate = np.sign(np.mean([r["is_ic_T%d" % N] for N in range(10, 21)]))
        flip_in_life = (s1 != 0 and slate != 0 and s1 != slate)
        if early and not late:
            tag = "短线型(T1-3有效,晚周期消退)"
        elif early and late:
            tag = "短线起+长持续" + ("(中途翻向)" if flip_in_life else "")
        elif (not early) and late:
            tag = "长持型(晚周期才显著,打板拿不到)"
        else:
            tag = "全程无效/噪声"
        shape[f] = tag

    # ===== T1 主判据 四关(只认T1)=====
    print("\n[T1主判据] 四关(辅T3/T5对照)...")
    xpool = top12_holdT1_ic()
    g1rows = []; ic_ser = {}
    for f in FACTORS:
        ri, sis = C.gate1_eval(d, f, MAIN, 1, "IS")
        ro, _ = C.gate1_eval(d, f, MAIN, 1, "OOS")
        dir_is = int(np.sign(ri["mean_ic"])); flip = np.sign(ro["mean_ic"]) != dir_is
        yr = yearly(d, f, MAIN)
        bear_ok = (np.sign(yr[2022]) == dir_is) and (np.sign(yr[2023]) == dir_is)
        # 跨周期 T1 vs T5 方向
        t5 = dec[dec.factor == f].iloc[0]["is_ic_T5"]
        cross_period_flip = (np.sign(t5) != dir_is) and dir_is != 0
        x12 = xpool.get(f, np.nan)
        ic_ser[f] = sis
        g1rows.append(dict(factor=f, seed_related=bool(SEED_RELATED[f]),
            is_ic=ri["mean_ic"], is_t=ri["hac_t"], is_p=ri["p_two_sided"], n_days=ri["n_days"],
            oos_ic=ro["mean_ic"], oos_t=ro["hac_t"], oos_p=ro["p_two_sided"], direction=dir_is,
            oos_flip=bool(flip), bear_holds=bool(bear_ok),
            ic_2022=yr[2022], ic_2023=yr[2023],
            t5_is_ic=t5, t1_vs_t5_flip=bool(cross_period_flip),
            top12_t1_is_ic=x12, cross_pool_reversal=bool((x12 == x12) and np.sign(x12) != dir_is),
            shape=shape[f]))
    g1 = pd.DataFrame(g1rows)
    g1["is_sig"] = g1.is_p < ALPHA; g1["oos_sig"] = g1.oos_p < ALPHA
    g1["gate1_pass"] = g1.is_sig & (~g1.oos_flip)

    # Gate2/3/4(只在 T1 上)
    gp = g1[g1.gate1_pass].copy()
    if len(gp):
        passed, q, _ = C.bh_fdr(gp.is_p.values, ALPHA, len(FACTORS)); gp["gate2_pass"] = passed
    g2map = dict(zip(gp.factor, gp.gate2_pass)) if len(gp) else {}
    g2p = [f for f in FACTORS if g2map.get(f)]
    reps = []
    if len(g2p) >= 1:
        ser = pd.DataFrame({f: ic_ser[f] for f in g2p}).dropna(how="all")
        corr = ser.corr(); tmap = dict(zip(g1.factor, g1.is_t))
        for mem in C.union_find_clusters(g2p, corr, CORR_THR):
            reps.append(sorted(mem, key=lambda n: -abs(tmap[n]))[0])
    g3rep = {f: (f in reps) for f in g2p}
    decay_map = {}
    for f in FACTORS:
        yr = yearly(d, f, MAIN)
        decay_map[f] = C.decay_status_6y(yr)[0]

    # final_verdict(只认T1)
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
                        is_ic=round(r.is_ic, 5), is_p=round(r.is_p, 4), oos_ic=round(r.oos_ic, 5),
                        oos_p=round(r.oos_p, 4), oos_flip=r.oos_flip, bear_holds=r.bear_holds,
                        t1_vs_t5_flip=r.t1_vs_t5_flip, cross_pool_reversal=r.cross_pool_reversal,
                        shape=r.shape, conditioned_on="dragon_seed"))
    led = pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict)
    led.to_csv(os.path.join(HERE, "seed_t1_ledger.csv"), index=False, encoding="utf-8-sig")

    # A/B(只认T1)
    jA = g1[(~g1.seed_related) & g1.is_sig & g1.oos_sig & (~g1.oos_flip) & g1.bear_holds]
    verdict = "A" if len(jA) else "B"

    # ===== 次日胜率(干净因子)=====
    print("\n[次日胜率] 干净因子分组...")
    base_is = float((d[(d.seg == "IS")][MAIN] > 0).mean())
    base_oos = float((d[(d.seg == "OOS")][MAIN] > 0).mean())
    wr_rows = []
    for f in [x for x in FACTORS if not SEED_RELATED[x]]:
        dir_is = int(g1[g1.factor == f].direction.iloc[0])
        for seg, base in [("IS", base_is), ("OOS", base_oos)]:
            b, wr, sel, excl = winrate(d, f, seg, dir_is)
            wr_rows.append(dict(factor=f, seg=seg, direction=dir_is, baseline=round(base, 4),
                                **{"Q%d" % (i + 1): round(wr[i], 4) for i in range(len(wr))},
                                pick_good=round(sel, 4), exclude_worst=round(excl, 4),
                                lift_pick=round(sel - base, 4), lift_excl=round(excl - base, 4)))
    wrdf = pd.DataFrame(wr_rows)
    wrdf.to_csv(os.path.join(HERE, "seed_t1_winrate.csv"), index=False, encoding="utf-8-sig")

    print("\n=== final_verdict(T1) ===\n" + led.final_verdict.value_counts().to_string())
    print("=== A/B 判定(只认T1): 落 %s ===" % verdict)
    if verdict == "A":
        print("满足全四条的干净因子:", jA.factor.tolist())

    write_report(d, g1, led, dec, shape, wrdf, base_is, base_oos, jA, verdict,
                 sc, ok2, ok3, ok4, reps, g2map, decay_map, xpool)
    print("\n[done] 报告+CSV 落盘 dragon_seed_study/(seed_t1_*)")


def write_report(d, g1, led, dec, shape, wrdf, base_is, base_oos, jA, verdict,
                 sc, ok2, ok3, ok4, reps, g2map, decay_map, xpool):
    def r1(f): return g1[g1.factor == f].iloc[0]
    L = []
    L.append("# Top250 seed·打板次日(hold_T1)四关法庭 + T1-T20衰减 + 次日胜率 + A/B")
    L.append("")
    L.append("> **conditioned_on_dragon_seed**;**主判据 = hold_T1(打板次日:买entry open卖T+1 close、持1天、T+1合法、排除day1)**;辅 hold_T3/T5。")
    L.append("> ★**铁律**:T1-T20 衰减矩阵**仅描述因子随持有期形态**,**绝不用 T6-T20 参与 A/B 判定或给因子平反**。"
             "open_ratio 在 T1 翻车就是翻车。**不是**全市场alpha、**不是**多因子评分、**不是**robust_alpha;2026未碰、未计成本。")
    L.append("- 切分 IS=2020-2023(%d)/OOS=2024-2025(%d)/2026=0。族=8。自检:打乱hold_T1归零=%s 噪声FDR=%s 合成=%s 衰减=%s。" % (
        (d.seg == "IS").sum(), (d.seg == "OOS").sum(),
        all(x["shuffle_zero_pass"] for x in sc), ok2, ok3, ok4))
    L.append("")
    # 形态(衰减,描述)
    L.append("## A) T1-T20 衰减形态(★描述性,不用于挑因子)")
    L.append("| 因子 | 自指 | IS IC: T1 / T3 / T5 / T10 / T20 | 形态标注 |")
    L.append("|---|---|---|---|")
    for f in FACTORS:
        r = dec[dec.factor == f].iloc[0]
        L.append("| %s | %s | %+.3f / %+.3f / %+.3f / %+.3f / %+.3f | %s |" % (
            f, "★" if SEED_RELATED[f] else "", r.is_ic_T1, r.is_ic_T3, r.is_ic_T5,
            r.is_ic_T10, r.is_ic_T20, shape[f]))
    L.append("> 对打板:T1-T3 有效=可用短线信号;要 T10+ 才显著=持有周期不匹配、打板拿不到;全程无效=噪声。完整 T1-T20 见 seed_t1_decay_matrix.csv。")
    L.append("")
    # 跨周期翻车
    L.append("## B) ★跨周期翻车标注(T1 vs T5 方向)")
    L.append("| 因子 | T1 IS IC | T5 IS IC | T1↔T5 方向反? |")
    L.append("|---|---|---|---|")
    for f in FACTORS:
        r = r1(f)
        L.append("| %s | %+.4f | %+.4f | %s |" % (f, r.is_ic, r.t5_is_ic,
                 "★是(T5看着行/T1相反)" if r.t1_vs_t5_flip else "否"))
    L.append("> open_ratio 等若 T1 与 T5 方向相反 → 上轮用 T5 主判据会误判;**打板只认 T1**。")
    L.append("")
    # T1 四关
    L.append("## C) T1 主判据·每因子(IS锁方向→OOS不翻向)+ 跨池")
    L.append("| 因子 | 自指 | T1 IS IC | IS t | IS p | OOS IC | OOS t | OOS p | OOS翻向 | 熊市 | Top12 T1 IC | 跨池反 | Gate1 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for f in FACTORS:
        r = r1(f)
        x = ("%+.4f" % r.top12_t1_is_ic) if r.top12_t1_is_ic == r.top12_t1_is_ic else "NA"
        L.append("| %s | %s | %+.4f | %+.2f | %.3f | %+.4f | %+.2f | %.3f | %s | %s | %s | %s | %s |" % (
            f, "★" if r.seed_related else "", r.is_ic, r.is_t, r.is_p, r.oos_ic, r.oos_t, r.oos_p,
            "是" if r.oos_flip else "否", "✓" if r.bear_holds else "✗", x,
            "★" if r.cross_pool_reversal else "否", "pass" if r.gate1_pass else "fail"))
    L.append("")
    L.append("## D) 漏斗 + verdict(只认T1)")
    L.append("```")
    L.append("8因子 → Gate1 pass(IS显著+OOS不翻向): %d → Gate2 FDR: %d → Gate3独立: %d → Gate4 decaying: %d" % (
        int(g1.gate1_pass.sum()), sum(1 for f in FACTORS if g2map.get(f)), len(reps),
        sum(1 for f in reps if decay_map.get(f) == "decaying")))
    L.append("```")
    for k, v in led.final_verdict.value_counts().items():
        L.append("- %s: %d (%s)" % (k, v, ", ".join(led[led.final_verdict == k].factor)))
    L.append("")
    # A/B
    L.append("## E) ★★ A/B 判定(打板次日 hold_T1;铁律:只认 T1)")
    L.append("标准 A = 干净(非自指) + hold_T1 下 IS&OOS 都显著 + OOS 不翻向 + 熊市 2022&2023 成立。")
    L.append("")
    if verdict == "A":
        L.append("### → 落【判定 A】:%s" % ", ".join(jA.factor.tolist()))
        for f in jA.factor:
            r = r1(f)
            L.append("- %s:T1 IS IC=%+.4f(p=%.3f) OOS=%+.4f(p=%.3f) 熊市2022=%+.3f/2023=%+.3f" % (
                f, r.is_ic, r.is_p, r.oos_ic, r.oos_p, r.ic_2022 if hasattr(r, "ic_2022") else float("nan"),
                r.ic_2023 if hasattr(r, "ic_2023") else float("nan")))
    else:
        L.append("### → 落【判定 B:入场选股(打板次日)边际薄】")
        L.append("**没有任何干净因子在 T1 下同时满足全四条**。逐因子卡在哪条:")
        L.append("")
        L.append("| 因子 | 干净 | T1 IS显著 | T1 OOS显著 | OOS不翻向 | 熊市成立 | 卡在 |")
        L.append("|---|---|---|---|---|---|---|")
        for f in FACTORS:
            r = r1(f); clean = not r.seed_related; fails = []
            if not clean: fails.append("自指")
            if not r.is_sig: fails.append("IS不显著")
            if not r.oos_sig: fails.append("OOS不显著")
            if r.oos_flip: fails.append("OOS翻向")
            if not r.bear_holds: fails.append("熊市不成立")
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                f, "是" if clean else "否(自指)", "✓" if r.is_sig else "✗", "✓" if r.oos_sig else "✗",
                "✓" if not r.oos_flip else "✗", "✓" if r.bear_holds else "✗", ", ".join(fails) or "—"))
    L.append("> 只摆事实判定,**不替你下决定**。★T6-T20 不参与本判定(铁律)。")
    L.append("")
    # 次日胜率
    L.append("## F) ★次日胜率(你的核心诉求:选股能否提高次日胜率)")
    L.append("基准次日胜率(全池 hold_T1>0 占比):**IS %.1f%% / OOS %.1f%%**。" % (base_is * 100, base_oos * 100))
    L.append("每日按因子值分5组(Q1低→Q5高),各组次日胜率;按因子方向选好组 / 排最差组后的胜率与提升:")
    L.append("")
    L.append("| 因子 | seg | 方向 | Q1 | Q2 | Q3 | Q4 | Q5 | 基准 | 选好组 | 排最差组 | 选好组提升 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in wrdf.itertuples():
        L.append("| %s | %s | %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | **%.3f** | %.3f | **%+.3f** |" % (
            r.factor, r.seg, "正" if r.direction > 0 else "负", r.Q1, r.Q2, r.Q3, r.Q4, r.Q5,
            r.baseline, r.pick_good, r.exclude_worst, r.lift_pick))
    L.append("> 「选好组」=每日只取因子方向对应的最优 1/5;「排最差组」=剔掉最差 1/5 后其余的胜率。提升幅度即"
             "「用该单因子选股能把次日胜率提多少(条件池内、未计成本)」。")
    L.append("")
    L.append("## 声明")
    L.append("- conditioned_on_dragon_seed、主判据打板次日 hold_T1;衰减曲线**仅描述形态、不用于挑因子**(铁律)。")
    L.append("- **不是**全市场alpha、**不是**多因子评分、**不是**robust_alpha;只单因子;**2026未碰**;**未计成本**(计了更差)。")
    with open(os.path.join(HERE, "seed_court_t1_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
