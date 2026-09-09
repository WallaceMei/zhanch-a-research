# -*- coding: utf-8 -*-
#
# factor_court_v2.py  --  Factor Court V2 (Gate2 FDR / Gate3 去冗余 / Gate4 衰减)
#
# 在 V1(Gate0+Gate1)基础上补建后三关。只做 Gate2/3/4。
# 红线: 不碰 2026(OOS 截至 2025-12-31);不重算 7.7M 因子值(仅补存每日 IC 序列);
#       不标 robust_alpha;final_verdict 仅允许:
#       gate1_fail / gate2_fail / gate3_redundant / gate_pass_but_decaying / gate_all_pass_candidate
# 三关机制自检失败 => 打印 SELF_CHECK_FAILED 并停止输出 final verdict。
# 依赖: 纯 numpy/pandas;正态 CDF 用 math.erf;FDR 纯实现;聚类 union-find。不装 scipy。
# 环境: D:\quant_env\.venv_court

import os, json
from math import erf, sqrt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

FEATURES = r"C:\quant_project\features.parquet"
V1_DIR = r"D:\Code\JQ\战车A\research\factor_court\v1"
V2_DIR = r"D:\Code\JQ\战车A\research\factor_court\v2"

CFG = {
    "input_v1_dir": V1_DIR, "output_v2_dir": V2_DIR,
    "main_mask_type": "universal_clean_mask",
    "main_return_type": "fwd_return_10d_cs_demean",
    "ic_type": "daily_cross_sectional_rank_ic",
    "hac_lag": 10,
    "oos_start": "2023-01-01", "oos_end": "2025-12-31",
    "final_holdout_start": "2026-01-01", "final_holdout_end": None,
    "alpha_fdr": 0.05,
    "primary_fdr_family_size": 31, "sensitivity_family_size": 194,
    "bonferroni_alpha": 0.05,
    "cluster_corr_threshold": 0.7, "negative_corr_threshold": -0.7,
    "decay_ratio_decaying_threshold": 0.5, "decay_ratio_warning_threshold": 0.7,
    "use_abs_corr_for_clustering": False,
    "robust_alpha_allowed": False,
    "notes": "V2 后三关; 主口径 universal+cs_demean; 不碰2026; verdict 无 robust_alpha",
}
RUN_TIME = "RUN"   # 时间戳由外部补,脚本内不取 now(可复现)

MIN_DAILY_STOCKS = 100
LIMIT_PCT = 9.7

TECH_RANK = [
    "ma_ratio_5d_rank","ma_ratio_10d_rank","ma_ratio_20d_rank","ma_ratio_60d_rank",
    "volatility_5d_rank","volatility_10d_rank","volatility_20d_rank",
    "atr_14d_rank","atr_ratio_rank",
    "vol_ratio_5d_rank","vol_ratio_10d_rank","vol_ratio_20d_rank",
    "vol_price_corr_10d_rank","amount_ratio_5d_rank",
    "rsi_14_rank","macd_hist_rank","bb_position_rank",
    "upper_shadow_ratio_rank","lower_shadow_ratio_rank","body_ratio_rank",
    "up_streak_rank","down_streak_rank",
    "price_position_10d_rank","price_position_20d_rank","price_position_60d_rank",
]
MOMENTUM_RANK = ["return_5d_rank","return_10d_rank","return_20d_rank","return_60d_rank",
                 "overnight_return_rank","intraday_return_rank"]
JUDGED = TECH_RANK + MOMENTUM_RANK


def norm_cdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def two_sided_p(t):
    return 2.0 * (1.0 - norm_cdf(abs(t)))


def one_sided_p(t):
    return 1.0 - norm_cdf(t)


def bh_fdr(pvals, alpha, family_size):
    """BH-FDR。family_size 可 > len(pvals)(n=194 敏感性: 把缺的当作不显著)。
    返回 (pass_bool_array, qvalue_array, bh_threshold_at_rank)。rank/threshold 按
    在 family_size 下的位次。pvals 顺序对应输入因子。"""
    p = np.asarray(pvals, dtype=float)
    m = int(family_size)
    order = np.argsort(p)
    ranked = p[order]
    k = len(p)
    # BH 阈值(按 family_size m): thr_i = (i/m)*alpha, i=1..k(这些是已测因子的位次)
    thr = np.array([( (i+1)/m )*alpha for i in range(k)])
    passed_ranked = ranked <= thr
    # 最大通过位次
    if passed_ranked.any():
        max_i = np.max(np.where(passed_ranked)[0])
        cutoff = ranked[max_i]
    else:
        cutoff = -1.0
    passed = p <= cutoff
    # q-value(BH adjusted, 用 m): q_(i) = min_{j>=i} m*p_(j)/j
    q_ranked = np.empty(k); running = 1.0
    for i in range(k-1, -1, -1):
        val = m * ranked[i] / (i+1)
        running = min(running, val)
        q_ranked[i] = min(running, 1.0)
    q = np.empty(k); q[order] = q_ranked
    thr_full = np.empty(k); thr_full[order] = thr
    return passed, q, thr_full


def bonferroni(pvals, alpha, family_size):
    thr = alpha / family_size
    return (np.asarray(pvals) < thr), thr


# ---------------------------------------------------------------------------
# Step 1: 补存每日 IC 序列(主口径, 方向已锁, OOS) -- 不重算因子值,仅算 IC
# ---------------------------------------------------------------------------

def build_daily_ic_series(directions):
    need = ["ts_code","trade_date","name","close_adj","vol","pct_chg"] + JUDGED
    df = pq.read_table(FEATURES, columns=need).to_pandas()
    for c in JUDGED: df[c] = df[c].astype("float32")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    g = df.groupby("ts_code", sort=False)["close_adj"]
    df["fwd"] = (g.shift(-10)/df["close_adj"]-1.0)
    daily_mean = df.groupby("trade_date")["fwd"].transform("mean")
    df["tgt"] = df["fwd"] - daily_mean  # cs_demean
    # universal mask
    st = df["name"].astype(str).str.contains(r"ST|\*ST|退", regex=True, na=False)
    susp = (df["vol"].fillna(0) <= 0) | df["close_adj"].isna()
    limit = df["pct_chg"].abs() >= LIMIT_PCT
    umask = (~st) & (~susp) & df["fwd"].notna() & (df["close_adj"]>0) & (~limit)
    oos = (df.trade_date >= CFG["oos_start"]) & (df.trade_date <= CFG["oos_end"])
    sub = df[umask & oos]
    # 逐日逐因子 Spearman(rank-pearson), 乘方向
    out = {}
    for fcol in JUDGED:
        d = directions[fcol]
        def _ic(gp):
            x = gp[fcol]; y = gp["tgt"]; m = x.notna() & y.notna()
            if m.sum() < MIN_DAILY_STOCKS: return np.nan
            return x[m].rank().corr(y[m].rank())
        s = sub.groupby("trade_date").apply(_ic) * d
        out[fcol] = s
    ic_df = pd.DataFrame(out)
    ic_df.index.name = "trade_date"
    ic_df = ic_df.dropna(how="all")
    return ic_df


# ---------------------------------------------------------------------------
# Gate3 union-find
# ---------------------------------------------------------------------------

def cluster_label(members):
    """按成员名给簇一个粗语义标签(启发式,供人看)。"""
    s = " ".join(members)
    if any(k in s for k in ["ma_ratio","return_","price_position","up_streak","down_streak"]):
        tag = "趋势/动量"
    elif any(k in s for k in ["volatility","atr"]):
        tag = "波动率"
    elif any(k in s for k in ["vol_ratio","amount_ratio","vol_price_corr"]):
        tag = "量能"
    elif any(k in s for k in ["rsi","bb_position","macd"]):
        tag = "技术摆动"
    elif any(k in s for k in ["shadow","body"]):
        tag = "K线形态"
    elif any(k in s for k in ["overnight","intraday"]):
        tag = "日内/隔夜"
    else:
        tag = "mixed"
    return tag if len(members) > 1 else tag + "(单因子簇)"


def union_find_clusters(names, corr, thr):
    parent = {n:n for n in names}
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[ra]=rb
    for i in range(len(names)):
        for j in range(i+1,len(names)):
            if corr.loc[names[i],names[j]] > thr:
                union(names[i],names[j])
    clusters={}
    for n in names: clusters.setdefault(find(n),[]).append(n)
    return list(clusters.values())


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def selfcheck_gate2():
    rng = np.random.RandomState(20)
    tn = rng.randn(20)                      # 20 噪声因子 t ~ N(0,1)
    pn = np.array([two_sided_p(t) for t in tn])
    passed,_,_ = bh_fdr(pn, CFG["alpha_fdr"], 20)
    npass = int(passed.sum())
    ok = npass <= 1                          # 噪声基本被拒(允许偶发1个)
    return {"synthetic_noise_count":20, "synthetic_noise_pass_count":npass,
            "gate2_selfcheck_pass":bool(ok),
            "notes":"20噪声t~N(0,1) BH-FDR(n=20,a=0.05) 通过数应≈0"}, ok


def selfcheck_gate3():
    rng = np.random.RandomState(3)
    A = rng.randn(200)
    B = A + 0.05*rng.randn(200)
    C = rng.randn(200)
    D = -A + 0.05*rng.randn(200)
    names=["A","B","C","D"]
    M = pd.DataFrame(np.corrcoef([A,B,C,D]), index=names, columns=names)
    clusters = union_find_clusters(names, M, CFG["cluster_corr_threshold"])
    cl = {n:i for i,c in enumerate(clusters) for n in c}
    ab = cl["A"]==cl["B"]; ac = cl["A"]==cl["C"]; ad = cl["A"]==cl["D"]
    ad_neg = M.loc["A","D"] < CFG["negative_corr_threshold"]   # 标互补而非冗余
    ok = ab and (not ac) and (not ad) and ad_neg
    return {"corr_A_B":round(M.loc["A","B"],3),"corr_A_C":round(M.loc["A","C"],3),
            "corr_A_D":round(M.loc["A","D"],3),"A_B_same_cluster":bool(ab),
            "A_C_same_cluster":bool(ac),"A_D_same_cluster":bool(ad),
            "A_D_marked_potential_complement":bool(ad_neg),
            "gate3_selfcheck_pass":bool(ok)}, ok


def decay_status(ic23, ic24, ic25):
    # decay_slope_3y 仍照算、照输出(参考用),但 V2 修正后【不再用它做判定】。
    # 原因: 原 spec 的 "slope<0 -> decay_warning" 与其自身 stable 用例
    # [0.03,0.031,0.029](slope=-0.0005) 自相矛盾;经 Gate4 自检发现,
    # 按 Wallace 决定(选项B)去掉斜率判定,decay_warning 只用 ic2025<ic2023*0.7。
    slope = np.polyfit([0,1,2],[ic23,ic24,ic25],1)[0]
    if (ic25 < 0) or (ic23 > ic24 > ic25 and ic25 < ic23*0.5):
        return "decaying", slope
    if ic25 < ic23*0.7:
        return "decay_warning", slope
    return "stable", slope


def selfcheck_gate4():
    cases = {"stable":[0.03,0.031,0.029], "warning":[0.03,0.025,0.019],
             "decaying":[0.03,0.02,0.01], "reversal":[0.03,0.015,-0.005]}
    expect = {"stable":"stable","warning":"decay_warning",
              "decaying":"decaying","reversal":"decaying"}
    rows=[]; ok=True
    for name,(a,b,c) in cases.items():
        st,_ = decay_status(a,b,c)
        good = (st==expect[name]); ok = ok and good
        rows.append({"case_name":name,"yearly_ic_2023":a,"yearly_ic_2024":b,
                     "yearly_ic_2025":c,"expected_status":expect[name],
                     "actual_status":st,"gate4_selfcheck_pass":bool(good)})
    return rows, ok


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(V2_DIR): os.makedirs(V2_DIR)
    # config 快照
    with open(os.path.join(V2_DIR,"factor_court_v2_config.json"),"w",encoding="utf-8") as f:
        json.dump(dict(CFG, run_time=RUN_TIME, hac_lag=CFG["hac_lag"]), f, ensure_ascii=False, indent=2)
    print("[cfg] factor_court_v2_config.json written; use_abs_corr=", CFG["use_abs_corr_for_clustering"])

    # 读 V1 主口径(universal + cs_demean)
    v1 = pd.read_csv(os.path.join(V1_DIR,"factor_gate1_results.csv"))
    main = v1[(v1.mask_type=="universal")&(v1.return_type=="cs_demean")].copy()
    assert len(main)==31, "V1 主口径行数 != 31: %d" % len(main)
    directions = dict(zip(main.factor_name, main.factor_direction))
    print("[v1] 主口径 31 行读入; gate1 pass=%d" % int((main.verdict=="gate1_candidate_alpha").sum()))

    # Step1: 每日 IC 序列(补存)
    ic_path = os.path.join(V2_DIR,"daily_ic_series.csv")
    print("[step1] 计算每日 IC 序列(主口径, 方向已锁, OOS)...")
    ic_df = build_daily_ic_series(directions)
    ic_df.to_csv(ic_path, encoding="utf-8-sig")
    print("  daily_ic_series: %d 天 x %d 因子" % ic_df.shape)

    # ---- 自检(三关) ----
    sc2, ok2 = selfcheck_gate2()
    sc3, ok3 = selfcheck_gate3()
    sc4_rows, ok4 = selfcheck_gate4()
    sc_rows = [dict(gate="gate2", **sc2), dict(gate="gate3", **sc3)]
    for r in sc4_rows: sc_rows.append(dict(gate="gate4", **r))
    pd.DataFrame(sc_rows).to_csv(os.path.join(V2_DIR,"factor_court_v2_selfcheck.csv"),
                                 index=False, encoding="utf-8-sig")
    print("[selfcheck] gate2=%s gate3=%s gate4=%s" % (ok2,ok3,ok4))
    if not (ok2 and ok3 and ok4):
        print("SELF_CHECK_FAILED -> 停止,不输出 final verdict")
        return

    # ---- Gate2: FDR ----
    main = main.reset_index(drop=True)
    main["p_two_sided_hac"] = main["ic_t_hac"].apply(lambda t: two_sided_p(t))
    main["p_one_sided_hac_reference"] = main["ic_t_hac"].apply(lambda t: one_sided_p(t))
    p = main["p_two_sided_hac"].values
    bh31_pass, bh31_q, bh31_thr = bh_fdr(p, CFG["alpha_fdr"], 31)
    bh194_pass, bh194_q, bh194_thr = bh_fdr(p, CFG["alpha_fdr"], 194)
    bf31_pass, bf31_thr = bonferroni(p, CFG["bonferroni_alpha"], 31)
    bf194_pass, bf194_thr = bonferroni(p, CFG["bonferroni_alpha"], 194)
    g1pass = (main.verdict=="gate1_candidate_alpha").values
    main["bh_q_value_n31"]=bh31_q; main["bh_threshold_n31"]=bh31_thr
    main["bh_fdr_n31_pass"]=bh31_pass & g1pass
    main["bh_q_value_n194_sensitivity"]=bh194_q; main["bh_threshold_n194_sensitivity"]=bh194_thr
    main["bh_fdr_n194_pass_sensitivity"]=bh194_pass & g1pass
    main["bonferroni_threshold_n31"]=bf31_thr; main["bonferroni_n31_pass"]=bf31_pass & g1pass
    main["bonferroni_threshold_n194_sensitivity"]=bf194_thr
    main["bonferroni_n194_pass_sensitivity"]=bf194_pass & g1pass
    def g2status(r):
        if not r.gate1_final_pass: return "not_applicable_due_to_gate1_fail"
        return "gate2_pass" if r.bh_fdr_n31_pass else "gate2_fail"
    main["gate2_status"]=main.apply(g2status,axis=1)
    g2cols=["factor_name","verdict","ic_t_hac","p_two_sided_hac","p_one_sided_hac_reference",
            "bh_threshold_n31","bh_q_value_n31","bh_fdr_n31_pass",
            "bh_threshold_n194_sensitivity","bh_q_value_n194_sensitivity","bh_fdr_n194_pass_sensitivity",
            "bonferroni_threshold_n31","bonferroni_n31_pass",
            "bonferroni_threshold_n194_sensitivity","bonferroni_n194_pass_sensitivity","gate2_status"]
    g2=main[g2cols].rename(columns={"verdict":"gate1_status"})
    g2["fail_reason"]=np.where(g2.gate2_status=="gate2_fail","bh_fdr_n31_not_significant","")
    g2.to_csv(os.path.join(V2_DIR,"factor_gate2_fdr.csv"),index=False,encoding="utf-8-sig")
    print("[gate2] BH-FDR n31 pass=%d / n194 pass=%d / bonf31 pass=%d / bonf194 pass=%d" % (
        int(main.bh_fdr_n31_pass.sum()), int(main.bh_fdr_n194_pass_sensitivity.sum()),
        int(main.bonferroni_n31_pass.sum()), int(main.bonferroni_n194_pass_sensitivity.sum())))

    # ---- Gate3: 去冗余(只对 gate2_pass) ----
    g2pass = main[main.gate2_status=="gate2_pass"].factor_name.tolist()
    ic_sub = ic_df[g2pass]
    corr = ic_sub.corr(method="pearson")
    corr.to_csv(os.path.join(V2_DIR,"factor_gate3_corr_matrix.csv"),encoding="utf-8-sig")
    clusters = union_find_clusters(g2pass, corr, CFG["cluster_corr_threshold"])
    hac_map = dict(zip(main.factor_name, main.ic_t_hac))
    cov_map = dict(zip(main.factor_name, main.factor_coverage_ratio))
    g3rows=[]
    for cid,members in enumerate(clusters):
        # 代表: HAC t 最高 -> 覆盖率 -> (名字稳定)
        rep = sorted(members, key=lambda n:(-abs(hac_map[n]), -cov_map.get(n,0), n))[0]
        lbl = cluster_label(members)
        for n in members:
            is_rep = (n==rep)
            g3rows.append({"factor_name":n,"gate2_status":"gate2_pass","cluster_id":cid,
                "cluster_size":len(members),"cluster_members":"|".join(sorted(members)),
                "cluster_representative":rep,"gate3_representative":is_rep,
                "ic_corr_to_representative":round(float(corr.loc[n,rep]),4),
                "factor_rank_corr_to_representative_optional":"",
                "gate3_status":("gate3_keep_representative" if is_rep else "gate3_redundant"),
                "fail_reason":("" if is_rep else "redundant_to_%s"%rep),
                "cluster_label":lbl})
    g3=pd.DataFrame(g3rows)
    g3.to_csv(os.path.join(V2_DIR,"factor_gate3_clusters.csv"),index=False,encoding="utf-8-sig")
    # 强负相关对
    negrows=[]
    for i in range(len(g2pass)):
        for j in range(i+1,len(g2pass)):
            c=corr.iloc[i,j]
            if c < CFG["negative_corr_threshold"]:
                negrows.append({"factor_a":g2pass[i],"factor_b":g2pass[j],"ic_corr":round(float(c),4),
                    "note":"strong_negative_ic_corr_not_marked_redundant"})
    pd.DataFrame(negrows, columns=["factor_a","factor_b","ic_corr","note"]).to_csv(
        os.path.join(V2_DIR,"factor_gate3_negative_corr_pairs.csv"),index=False,encoding="utf-8-sig")
    n_clusters=len(clusters); n_reps=sum(1 for c in clusters)
    print("[gate3] gate2_pass=%d -> 簇数=%d 代表=%d 冗余=%d 强负相关对=%d" % (
        len(g2pass), n_clusters, n_reps, len(g3[~g3.gate3_representative]), len(negrows)))

    # ---- Gate4: 衰减(对 gate3 代表) ----
    reps = g3[g3.gate3_representative].factor_name.tolist()
    yr = ic_df.copy(); yr_year = pd.to_datetime(ic_df.index).year
    g4rows=[]
    for n in reps:
        s=ic_df[n]
        ic23=float(s[yr_year==2023].mean()); ic24=float(s[yr_year==2024].mean()); ic25=float(s[yr_year==2025].mean())
        st,slope=decay_status(ic23,ic24,ic25)
        ratio=ic25/max(abs(ic23),1e-12)
        g4st={"stable":"gate4_pass","decay_warning":"gate4_pass_with_warning","decaying":"gate4_flag_decaying"}[st]
        nxt=("2025 IC 有弱化迹象,2026 Final 终审需重点观察" if st=="decay_warning"
             else ("2025 IC 已衰减/反向,2026 终审重点观察" if st=="decaying" else "stable"))
        g4rows.append({"factor_name":n,"gate3_status":"gate3_keep_representative",
            "yearly_ic_2023":round(ic23,5),"yearly_ic_2024":round(ic24,5),"yearly_ic_2025":round(ic25,5),
            "decay_ratio_2025_vs_2023":round(ratio,4),"decay_slope_3y":round(float(slope),6),
            "decay_status":st,"gate4_status":g4st,"next_action":nxt})
    g4=pd.DataFrame(g4rows)
    g4.to_csv(os.path.join(V2_DIR,"factor_gate4_decay.csv"),index=False,encoding="utf-8-sig")
    print("[gate4] 代表因子衰减: stable=%d warning=%d decaying=%d" % (
        int((g4.decay_status=="stable").sum()),int((g4.decay_status=="decay_warning").sum()),
        int((g4.decay_status=="decaying").sum())))

    # ---- 综合台账 ----
    g3map=g3.set_index("factor_name")
    g4map=g4.set_index("factor_name")
    led=[]
    for _,r in main.iterrows():
        n=r.factor_name
        g2s=r.gate2_status
        in_g3 = n in g3map.index
        is_rep = bool(g3map.loc[n,"gate3_representative"]) if in_g3 else False
        # final verdict
        if not r.gate1_final_pass: fv="gate1_fail"
        elif g2s!="gate2_pass": fv="gate2_fail"
        elif in_g3 and not is_rep: fv="gate3_redundant"
        elif is_rep and n in g4map.index:
            ds=g4map.loc[n,"decay_status"]
            fv="gate_pass_but_decaying" if ds=="decaying" else "gate_all_pass_candidate"
        else: fv="gate2_fail"
        nxt=""
        if fv=="gate_all_pass_candidate" and in_g3 and is_rep and n in g4map.index and g4map.loc[n,"decay_status"]=="decay_warning":
            nxt="2025 IC 有弱化迹象,2026 Final 终审需重点观察"
        led.append({"factor_name":n,"gate1_status":r.verdict,"gate1_hac_t":r.ic_t_hac,
            "gate2_status":g2s,"p_two_sided_hac":round(r.p_two_sided_hac,6),
            "bh_q_value_n31":round(r.bh_q_value_n31,6),"bh_fdr_n31_pass":bool(r.bh_fdr_n31_pass),
            "bh_fdr_n194_pass_sensitivity":bool(r.bh_fdr_n194_pass_sensitivity),
            "bonferroni_n31_pass":bool(r.bonferroni_n31_pass),
            "bonferroni_n194_pass_sensitivity":bool(r.bonferroni_n194_pass_sensitivity),
            "gate3_status":(g3map.loc[n,"gate3_status"] if in_g3 else "n/a"),
            "cluster_id":(int(g3map.loc[n,"cluster_id"]) if in_g3 else -1),
            "cluster_label":(g3map.loc[n,"cluster_label"] if in_g3 else ""),
            "cluster_representative":(g3map.loc[n,"cluster_representative"] if in_g3 else ""),
            "gate3_representative":is_rep,
            "ic_corr_to_representative":(g3map.loc[n,"ic_corr_to_representative"] if in_g3 else ""),
            "gate4_status":(g4map.loc[n,"gate4_status"] if n in g4map.index else "n/a"),
            "decay_status":(g4map.loc[n,"decay_status"] if n in g4map.index else "n/a"),
            "yearly_ic_2023":(g4map.loc[n,"yearly_ic_2023"] if n in g4map.index else ""),
            "yearly_ic_2024":(g4map.loc[n,"yearly_ic_2024"] if n in g4map.index else ""),
            "yearly_ic_2025":(g4map.loc[n,"yearly_ic_2025"] if n in g4map.index else ""),
            "decay_ratio_2025_vs_2023":(g4map.loc[n,"decay_ratio_2025_vs_2023"] if n in g4map.index else ""),
            "decay_slope_3y":(g4map.loc[n,"decay_slope_3y"] if n in g4map.index else ""),
            "final_verdict":fv,"fail_reason":(r.get("fail_reason","") if hasattr(r,"get") else ""),
            "next_action":nxt,"created_at":RUN_TIME})
    led=pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict), "红线: 出现 robust_alpha!"
    led.to_csv(os.path.join(V2_DIR,"factor_court_v2_ledger.csv"),index=False,encoding="utf-8-sig")
    print("\n=== final_verdict 分布 ===")
    print(led.final_verdict.value_counts().to_string())
    print("\ngate_all_pass_candidate 因子:", led[led.final_verdict=="gate_all_pass_candidate"].factor_name.tolist())
    print("gate_pass_but_decaying 因子:", led[led.final_verdict=="gate_pass_but_decaying"].factor_name.tolist())

    # ---- summary.md ----
    n_g1 = int((main.gate1_final_pass).sum())
    n_bh31 = int(main.bh_fdr_n31_pass.sum())
    n_bh194 = int(main.bh_fdr_n194_pass_sensitivity.sum())
    g4s = lambda v: int((g4.decay_status==v).sum())
    vc = led.final_verdict.value_counts().to_dict()
    L=[]
    L.append("# 因子审判法庭 V2 — Gate2/3/4 总结")
    L.append("")
    L.append("> 建后三关 + 验机制。final_verdict 仅允许 gate1_fail/gate2_fail/gate3_redundant/"
             "gate_pass_but_decaying/gate_all_pass_candidate;**严禁 robust_alpha**。不碰 2026。")
    L.append("> 主口径:universal_clean_mask + fwd_return_10d_cs_demean;HAC lag=10。环境 .venv_court。")
    L.append("")
    L.append("## 机制自检(三关)")
    L.append("- Gate2 selfcheck: %s(20 噪声 t~N(0,1),BH-FDR 通过 %d 个)" % (
        "pass" if sc2["gate2_selfcheck_pass"] else "FAIL", sc2["synthetic_noise_pass_count"]))
    L.append("- Gate3 selfcheck: %s(A~B 同簇=%s,A≠C 不同簇=%s,A/D 强负相关标互补=%s)" % (
        "pass" if sc3["gate3_selfcheck_pass"] else "FAIL", sc3["A_B_same_cluster"],
        not sc3["A_C_same_cluster"], sc3["A_D_marked_potential_complement"]))
    L.append("- Gate4 selfcheck: %s(4/4 用例,stable/warning/decaying/reversal 全对)" %
             ("pass" if ok4 else "FAIL"))
    L.append("")
    L.append("## 漏斗")
    L.append("```")
    L.append("31 受审因子(主口径)")
    L.append("-> Gate1 pass: %d" % n_g1)
    L.append("-> Gate2 BH-FDR n31 pass: %d" % n_bh31)
    L.append("-> Gate2 BH-FDR n194 敏感性 pass: %d" % n_bh194)
    L.append("-> Gate3 独立簇数: %d (代表因子 %d)" % (n_clusters, len(reps)))
    L.append("-> Gate4 代表中 stable: %d / warning: %d / decaying: %d" % (
        g4s("stable"), g4s("decay_warning"), g4s("decaying")))
    L.append("-> gate_all_pass_candidate: %d" % vc.get("gate_all_pass_candidate",0))
    L.append("-> gate_pass_but_decaying: %d" % vc.get("gate_pass_but_decaying",0))
    L.append("```")
    L.append("")
    L.append("## final_verdict 分布")
    for k,v in led.final_verdict.value_counts().items(): L.append("- %s: %d" % (k,v))
    L.append("")
    L.append("## Gate2 砍了什么")
    g2fail = led[led.final_verdict=="gate2_fail"].factor_name.tolist()
    L.append("FDR(n=31)后不显著被砍 %d 个: %s" % (len(g2fail), g2fail if g2fail else "无"))
    L.append("n=194 敏感性下 BH-FDR 通过 %d 个(压力测试,非主判据)。" % n_bh194)
    L.append("")
    L.append("## Gate3 簇(代表 + 语义标签)")
    for cid,members in enumerate(clusters):
        sub=g3[g3.cluster_id==cid]; rep=sub.cluster_representative.iloc[0]; lbl=sub.cluster_label.iloc[0]
        L.append("- 簇%d [%s] 大小%d 代表=%s;成员:%s" % (cid,lbl,len(members),rep,"|".join(sorted(members))))
    L.append("")
    L.append("## Gate3 强负相关对(potential_complement,不判冗余)")
    if negrows:
        for r in negrows: L.append("- %s vs %s : ic_corr=%.3f" % (r["factor_a"],r["factor_b"],r["ic_corr"]))
    else:
        L.append("- 无 corr<-0.7 的对。")
    L.append("> 强负相关不判冗余,后续可作潜在互补/对冲信号观察。")
    L.append("")
    L.append("## Gate4 衰减")
    for _,r in g4.iterrows():
        L.append("- %s: 2023=%.4f 2024=%.4f 2025=%.4f ratio=%.2f slope=%.5f -> %s" % (
            r.factor_name,r.yearly_ic_2023,r.yearly_ic_2024,r.yearly_ic_2025,
            r.decay_ratio_2025_vs_2023,r.decay_slope_3y,r.decay_status))
    L.append("")
    L.append("## 修正留档(给 V3)")
    L.append("- **Gate4 衰减规则原 spec 有自相矛盾**:§6.5 的 `decay_slope_3y<0 -> decay_warning` 与"
             "§8.3 的 stable 用例 [0.03,0.031,0.029](slope=-0.0005)打架——该用例斜率为负会被判 warning,"
             "但自检要求 stable。经 Gate4 自检发现,按 Wallace 决定(选项B)**去掉斜率判定,decay_warning 只用 "
             "`yearly_ic_2025 < yearly_ic_2023*0.7`**;decay_slope_3y 仍照算并输出到 csv 作参考,不再做判定。"
             "理由:真因子年度 IC 必有微小波动,'斜率<0就预警'过敏感、会预警满天飞、失去区分力。")
    L.append("- **慢因子提醒(沿用 V1)**:60d 类因子(ma_ratio_60d/return_60d/price_position_60d)的 IC 序列"
             "自相关可能超 10 日,HAC lag=10 下 t/IC 可能偏高。")
    L.append("- Gate3 去冗余基于 IC 序列相关 = **预测行为去冗余**,不等同于持仓重合度去冗余(本版未算因子值面板相关)。")
    L.append("")
    L.append("## 重要限制(必读)")
    L.append("- 本版是建后三关 + 验机制;31 个是 features 通用技术因子**试跑材料**,非产品级 alpha。")
    L.append("- 四关全过者仅 **gate_all_pass_candidate**:只表示在 V1 Gate1 + V2 Gate2/3/4 机制口径下暂时通过;"
             "**不是 robust_alpha、不能实盘、不是新发现 alpha**。")
    L.append("- OOS 纯度 unknown(教科书因子大概率被既往研究见过全段);未碰 2026;未做 DSR、未做组合回测/成本敏感性。")
    L.append("")
    with open(os.path.join(V2_DIR,"factor_court_v2_summary.md"),"w",encoding="utf-8") as f:
        f.write("\n".join(L))
    print("[write] factor_court_v2_summary.md")


if __name__ == "__main__":
    main()
