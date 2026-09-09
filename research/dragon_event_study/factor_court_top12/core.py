# -*- coding: utf-8 -*-
"""战车A研究第二步 — Top12 候选池内单因子验证(core 机制)。

★这是什么:在 dragon Top12 最终幸存者池**内部**,审单因子还能否区分赢家(big10)。
★这不是:全市场 alpha / 大预筛池选牛股 / 多因子评分 / robust_alpha。
★红线:只单因子,不组合/不调权重/不拼score/不改dragon_score;**2026 完全不碰**(holdout)。
       结论一律标 conditioned_on_dragon_top12(条件命题)。

复用 factor_court v2 的关卡机制(bh_fdr/union_find/decay),但数据层与 Gate1 是新的(Top12 池内)。
纯 numpy/pandas;HAC(Newey-West)自实现。py-3.10。
"""
import os
from math import erf, sqrt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(os.path.dirname(HERE), "event_study_dragon_2020_2026.csv")

# ---- 样本切分(钉死)----
IS_YEARS = (2020, 2023)        # In-Sample
OOS_YEARS = (2024, 2025)       # Out-of-Sample
HOLDOUT_YEAR = 2026            # ★Final holdout —— 完全不碰,任何计算前先剔除

# ---- 因子 ----
#   底座5个(mode无关) + 重算3个(avg_money/close_to_20d_high/avg_range,augment_factors.py补)
BASE_FACTORS = ["open_ratio", "auc_ratio", "auc_amount", "close_to_high", "ret3"]
AUG_FACTORS = ["avg_money", "close_to_20d_high", "avg_range"]
PRIMARY_FACTORS = BASE_FACTORS + AUG_FACTORS
BENCHMARK_FACTOR = "dragon_score"   # 仅 benchmark 对照,mode相关(用v3),不当主审因子
LABELS = ["is_big_meat_10", "is_super_meat_20"]
FWD_PERIODS = {"T3": "day3", "T5": "day5", "T10": "day10"}   # 固定周期前向收益(看哪个周期最强)

MAIN_LABEL = "is_big_meat_10"   # 主判据
MIN_DAILY_STOCKS = 5            # 当日池内少于此数 → 该日不计 IC(池中位16,门槛宽松)
HAC_LAG_EVENT = 20             # big10/super20 是20日窗内触及 → HAC lag=20
HAC_LAG_FWD = {"T3": 3, "T5": 5, "T10": 10}


# ============ 统计工具 ============
def norm_cdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def two_sided_p(t):
    return 2.0 * (1.0 - norm_cdf(abs(t)))


def hac_t_mean(x, lag):
    """检验序列 x 的均值是否为0的 Newey-West(HAC)t 统计量。
    lrv = g0 + 2*sum_{k=1..L}(1-k/(L+1)) g_k;SE = sqrt(lrv/n);t = mean/SE。"""
    x = np.asarray([v for v in x if v == v], dtype=float)   # 去 NaN
    n = len(x)
    if n < 10:
        return np.nan, np.nan, n
    mu = x.mean()
    d = x - mu
    g0 = np.dot(d, d) / n
    lrv = g0
    L = min(int(lag), n - 1)
    for k in range(1, L + 1):
        gk = np.dot(d[k:], d[:-k]) / n
        lrv += 2.0 * (1.0 - k / (L + 1.0)) * gk
    if lrv <= 0:
        return np.nan, mu, n
    se = sqrt(lrv / n)
    if se == 0:
        return np.nan, mu, n
    return mu / se, mu, n


def bh_fdr(pvals, alpha, family_size):
    """BH-FDR(复用 factor_court v2)。family_size=受审因子族大小。返回(pass数组,q值,阈值)。"""
    p = np.asarray(pvals, dtype=float)
    m = int(family_size)
    order = np.argsort(p)
    ranked = p[order]
    k = len(p)
    thr = np.array([((i + 1) / m) * alpha for i in range(k)])
    passed_ranked = ranked <= thr
    if passed_ranked.any():
        cutoff = ranked[np.max(np.where(passed_ranked)[0])]
    else:
        cutoff = -1.0
    passed = p <= cutoff
    q_ranked = np.empty(k); running = 1.0
    for i in range(k - 1, -1, -1):
        running = min(running, m * ranked[i] / (i + 1))
        q_ranked[i] = min(running, 1.0)
    q = np.empty(k); q[order] = q_ranked
    thr_full = np.empty(k); thr_full[order] = thr
    return passed, q, thr_full


def union_find_clusters(names, corr, thr):
    """相关>thr 的因子并查集聚类(★只用正相关,负相关另标互补)。复用 v2。"""
    parent = {n: n for n in names}
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if corr.loc[names[i], names[j]] > thr:
                union(names[i], names[j])
    clusters = {}
    for n in names:
        clusters.setdefault(find(n), []).append(n)
    return list(clusters.values())


def decay_status_6y(yearly):
    """衰减判定:yearly=dict{year:ic}(2020-2025,★无2026)。
    比 OOS期(2024-2025)均值 vs IS期(2020-2023)均值。"""
    is_ic = np.nanmean([yearly.get(y, np.nan) for y in range(2020, 2024)])
    oos_ic = np.nanmean([yearly.get(y, np.nan) for y in range(2024, 2026)])
    if is_ic == 0 or np.isnan(is_ic):
        return "insufficient", is_ic, oos_ic
    ratio = oos_ic / abs(is_ic)
    same_sign = np.sign(oos_ic) == np.sign(is_ic)
    if (not same_sign) or oos_ic == 0 or (same_sign and abs(oos_ic) < abs(is_ic) * 0.5):
        return "decaying", is_ic, oos_ic
    if abs(oos_ic) < abs(is_ic) * 0.7:
        return "decay_warning", is_ic, oos_ic
    return "stable", is_ic, oos_ic


def spearman(x, y):
    """Spearman = Pearson(rank(x),rank(y))。x/y 已对齐无 NaN。常数序列→nan。"""
    if len(x) < 2:
        return np.nan
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    if np.std(rx) == 0 or np.std(ry) == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


# ============ 数据层:Top12 池 ============
def load_pool(verbose=True):
    """读数据底座 → Top12 幸存者池(union of v1/v2/v3, dedup 到 unique(entry_date,code))。
    ★先剔除 2026(holdout),并断言任何返回数据都不含 2026。"""
    d = pd.read_csv(BASE, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    n_all = len(d)

    # primary(底座5个)mode无关 → dedup 到 unique(date,code);保留因子/标签/前向(均 mode无关)
    keep = ["entry_date", "code", "year"] + BASE_FACTORS + LABELS + list(FWD_PERIODS.values())
    u = d.drop_duplicates(["entry_date", "code"])[keep].copy()
    # 合并重算的 3 个价量因子(augment_factors.py 产物,同口径)
    aug_path = os.path.join(HERE, "_factors_augmented.csv")
    if os.path.exists(aug_path):
        aug = pd.read_csv(aug_path, dtype={"entry_date": str, "code": str})
        u = u.merge(aug, on=["entry_date", "code"], how="left")
    else:
        raise FileNotFoundError("缺 _factors_augmented.csv,先跑 augment_factors.py")

    # ★剔除 2026 holdout —— 在任何分析之前
    u = u[u["year"] != HOLDOUT_YEAR].reset_index(drop=True)
    assert (u["year"] == HOLDOUT_YEAR).sum() == 0, "红线违反:2026 进入了分析数据!"
    assert u["year"].max() <= 2025, "红线违反:数据含 >2025 的年份!"

    u["seg"] = np.where(u["year"] <= IS_YEARS[1], "IS",
                        np.where(u["year"] <= OOS_YEARS[1], "OOS", "DROP"))
    if verbose:
        print("[load_pool] 底座行 %d → unique(date,code) 去2026后 %d" % (n_all, len(u)))
        print("  IS(%d-%d): %d | OOS(%d-%d): %d | 2026已剔除(holdout)" % (
            IS_YEARS[0], IS_YEARS[1], (u.seg == "IS").sum(),
            OOS_YEARS[0], OOS_YEARS[1], (u.seg == "OOS").sum()))
        print("  big10 基率 IS=%.3f OOS=%.3f" % (
            u[u.seg == "IS"][MAIN_LABEL].mean(), u[u.seg == "OOS"][MAIN_LABEL].mean()))
    return u


def benchmark_series(verbose=False):
    """dragon_score(v3)做 benchmark:返回 unique(date,code)的 v3 dragon_score(去2026)。"""
    d = pd.read_csv(BASE, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    v3 = d[(d.score_mode == "v3") & (d.year != HOLDOUT_YEAR)][
        ["entry_date", "code", "dragon_score"]].drop_duplicates(["entry_date", "code"])
    return v3


# ============ Gate1:池内逐日 rank-IC / big10 区分力 ============
def daily_ic_series(df, factor, target, min_stocks=MIN_DAILY_STOCKS):
    """逐日(entry_date)在池内算 Spearman(factor, target)。
    target 可为连续前向收益(dayN)或二元标签(big10/super20)。
    返回 pd.Series(index=entry_date) 当日 IC;当日有效票<min_stocks → 跳过。"""
    out = {}
    for date, g in df.groupby("entry_date", sort=True):
        x = g[factor].values
        y = g[target].values
        m = ~(pd.isna(x) | pd.isna(y))
        if m.sum() < min_stocks:
            continue
        ic = spearman(x[m], y[m])
        if ic == ic:
            out[date] = ic
    return pd.Series(out, name="ic").sort_index()


def gate1_eval(df, factor, target, hac_lag, seg):
    """对某 seg(IS/OOS)算池内逐日 IC 序列 + 均值 + HAC t + p。"""
    sub = df[df.seg == seg]
    s = daily_ic_series(sub, factor, target)
    t, mu, n = hac_t_mean(s.values, hac_lag)
    return {"seg": seg, "factor": factor, "target": target, "n_days": int(len(s)),
            "n_obs_days_hac": n, "mean_ic": (float(mu) if mu == mu else np.nan),
            "hac_t": (float(t) if t == t else np.nan),
            "p_two_sided": (two_sided_p(t) if t == t else np.nan)}, s


def shuffle_null(df, factor, target, hac_lag, seg, n_shuffle=200, seed=42):
    """★Gate1 打乱目标归零自检:打乱 target(切断 factor↔target),重算池内逐日 IC 均值分布。
    真实信号应远离该 null;null 的 |mean_ic| 应≈0、HAC t 不显著。
    返回 (null_mean_ic 数组, null_hac_t 数组, real_stat)。"""
    sub = df[df.seg == seg].copy()
    rng = np.random.RandomState(seed)
    real, _ = gate1_eval(df, factor, target, hac_lag, seg)
    null_mu, null_t = [], []
    tvals = sub[target].values
    for _ in range(n_shuffle):
        sh = sub.copy()
        sh[target] = rng.permutation(tvals)   # 全局打乱标签
        s = daily_ic_series(sh, factor, target)
        tt, mu, _ = hac_t_mean(s.values, hac_lag)
        if mu == mu:
            null_mu.append(mu)
        if tt == tt:
            null_t.append(tt)
    return np.array(null_mu), np.array(null_t), real
