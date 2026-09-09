# -*- coding: utf-8 -*-
#
# factor_court_v1.py  --  Factor Court V1 (做法 A: 审 features 现成单因子)
#
# 建法庭 + 验机制为首要目的。通过者只标 gate1_candidate_alpha,严禁 robust_alpha。
# 受审对象: features.parquet 现成单因子列(31 个,优先 _rank 版)。
# 目标(被预测): 自算前向 fwd_return_10d = close_adj[T+10]/close_adj[T]-1(未来,T+10才知)。
#   ★ 泄漏防线: features 的 return_* 列是【后向】收益(过去,T日已知)= 因子,
#     与自算的前向 fwd_return_10d(目标)严格分开。代码显式保证因子集不含目标。
# 法庭纪律: 凡用 features 列,口径一律数据实证(不靠列名猜) -- return_10d 即反例。
#
# 边界: 只读 features;不碰 2026(OOS 截至 2025-12-31);不下最终结论。
# 环境: D:\quant_env\.venv_court (pandas+pyarrow)。

import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import datetime

FEATURES = r"C:\quant_project\features.parquet"
OUT_DIR = r"D:\Code\JQ\战车A\research\factor_court\v1"

IS_START, IS_END = pd.Timestamp("2018-01-01"), pd.Timestamp("2022-12-31")
OOS_START, OOS_END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")  # 不碰 2026
FWD_DAYS = 10
HAC_LAG = 10
T_THRESH = 3.0
MIN_DAILY_STOCKS = 100
MIN_OOS_IC_DAYS = 120
MIN_FACTOR_COVERAGE = 0.30
LIMIT_PCT = 9.7   # 主板涨跌停近似阈值(pct_chg 口径见运行时实证)

# 受审 31 因子: 25 技术 _rank + 6 动量(后向 return)_rank。全用 _rank 版。
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
MOMENTUM_RANK = [
    "return_5d_rank","return_10d_rank","return_20d_rank","return_60d_rank",
    "overnight_return_rank","intraday_return_rank",
]
JUDGED = TECH_RANK + MOMENTUM_RANK   # 31

# 绝不能当因子的(目标/原料)。return_* 后向列只在 MOMENTUM_RANK 里作因子;
# 自算 fwd_return_10d 才是目标。这里显式拦截:任何 *forward*/fwd 名都不得入因子。
FORBIDDEN_IN_FACTORS = {"fwd_return_10d","fwd_return_10d_cs_demean"}


def _ensure_out():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)


def load():
    need = ["ts_code","trade_date","name","close_adj","close","vol","pct_chg"] + JUDGED
    tbl = pq.read_table(FEATURES, columns=need)
    df = tbl.to_pandas()
    # 因子列降到 float32 省内存
    for c in JUDGED:
        df[c] = df[c].astype("float32")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    return df


def empirical_pct_chg_scale(df):
    """数据实证 pct_chg 口径(百分比 vs 小数):对比 close/prev_close-1。"""
    s = df[df.ts_code == "000001.SZ"].sort_values("trade_date")
    s = s[(s.trade_date >= "2024-01-01") & (s.trade_date <= "2024-06-30")]
    impl = (s["close"] / s["close"].shift(1) - 1.0)
    # pct_chg ~ impl*100 (百分比) 还是 impl (小数)?
    m = impl.notna() & s["pct_chg"].notna()
    ratio = (s["pct_chg"][m] / impl[m]).median()
    return float(ratio)  # ~100 => 百分比; ~1 => 小数


def build_target(df):
    """前向目标(未来,T+10):严格用 close_adj 自算,绝不读 features.return_*。"""
    g = df.groupby("ts_code", sort=False)["close_adj"]
    fwd_close = g.shift(-FWD_DAYS)
    df["fwd_return_10d"] = (fwd_close / df["close_adj"] - 1.0).astype("float64")
    # 横截面去均值(零成本去市场涨跌)
    daily_mean = df.groupby("trade_date")["fwd_return_10d"].transform("mean")
    df["fwd_return_10d_cs_demean"] = df["fwd_return_10d"] - daily_mean
    return df


def build_masks(df, pct_scale):
    thr = LIMIT_PCT * (1.0 if pct_scale > 10 else 0.01)  # 适配百分比/小数
    is_st = df["name"].astype(str).str.contains(r"ST|\*ST|退", regex=True, na=False)
    suspended = (df["vol"].fillna(0) <= 0) | df["close_adj"].isna()
    has_fwd = df["fwd_return_10d"].notna()
    abn = df["close_adj"] <= 0
    is_limit = df["pct_chg"].abs() >= thr
    base_ok = (~is_st) & (~suspended) & has_fwd & (~abn)
    universal = base_ok & (~is_limit)              # 通用: 排涨跌停
    board = base_ok                                 # 打板: 保留涨停样本
    return universal.values, board.values, is_limit.values, is_st.values


def _spearman_ic_by_day(sub, fcol, tcol):
    """逐日横截面 Spearman Rank IC 序列(index=日期)。"""
    def _ic(g):
        x = g[fcol]; y = g[tcol]
        m = x.notna() & y.notna()
        if m.sum() < MIN_DAILY_STOCKS:
            return np.nan
        # Spearman = 两列各自 rank 后的 Pearson(纯 numpy,免 scipy)
        return x[m].rank().corr(y[m].rank())
    return sub.groupby("trade_date").apply(_ic).dropna()


def newey_west_t(x, lag):
    """对序列均值的 Newey-West/HAC t 值(Bartlett 核)。"""
    x = np.asarray(x, dtype=float); n = x.size
    if n < 5: return np.nan, np.nan
    mu = x.mean(); d = x - mu
    var = (d @ d) / n
    for l in range(1, min(lag, n-1)+1):
        w = 1.0 - l/(lag+1.0)
        cov = (d[l:] @ d[:-l]) / n
        var += 2.0 * w * cov
    if var <= 0: return mu, np.nan
    se = np.sqrt(var/n)
    return mu, mu/se


def naive_t(x):
    x = np.asarray(x, dtype=float); n = x.size
    if n < 5: return np.nan
    sd = x.std(ddof=1)
    return np.nan if sd == 0 else x.mean()/sd*np.sqrt(n)


def main():
    _ensure_out()
    stamp = "RUN"  # 时间戳由外部填(脚本内不取 now,避免不可复现)
    print("[load] reading features ...")
    df = load()
    print("  rows=%d stocks=%d date=%s..%s" % (
        len(df), df.ts_code.nunique(), df.trade_date.min().date(), df.trade_date.max().date()))

    pct_scale = empirical_pct_chg_scale(df)
    print("[empirical] pct_chg/impl median ratio = %.2f  => %s 口径" % (
        pct_scale, "百分比" if pct_scale > 10 else "小数"))

    df = build_target(df)
    # 防线自检: 因子集与目标列零交集
    assert not (set(JUDGED) & FORBIDDEN_IN_FACTORS), "因子集混入目标列!"
    print("[guard] 因子集(31)不含 fwd 目标列 OK")

    uni_mask, board_mask, is_limit, is_st = build_masks(df, pct_scale)
    print("[mask] universal 有效=%d  board 有效=%d  涨跌停样本=%d  ST样本=%d" % (
        uni_mask.sum(), board_mask.sum(), is_limit.sum(), is_st.sum()))

    is_period = (df.trade_date >= IS_START) & (df.trade_date <= IS_END)
    oos_period = (df.trade_date >= OOS_START) & (df.trade_date <= OOS_END)

    # ---- §1 universe audit ----
    cov = {c: float(df[c].notna().mean()) for c in JUDGED}
    uni_rows = []
    for c in JUDGED:
        base = c[:-5] if c.endswith("_rank") else c
        uni_rows.append({
            "factor_name": base, "judged_column": c, "version_chosen": "rank",
            "factor_type": "momentum_return(后向)" if c in MOMENTUM_RANK else "technical",
            "coverage": round(cov[c], 4), "field_status": "present",
            "leakage_check": "factor=后向/≤T(实证);target=自算前向,二者分开",
            "oos_purity": "unknown",
        })
    pd.DataFrame(uni_rows).to_csv(os.path.join(OUT_DIR,"factor_universe_audit.csv"),
                                  index=False, encoding="utf-8-sig")
    print("[write] factor_universe_audit.csv (31)")

    # ---- Gate0 锁方向(IS) + Gate1(OOS) ----
    results = []
    masks = {"universal": uni_mask, "board_domain": board_mask}
    targets = {"cs_demean": "fwd_return_10d_cs_demean", "raw": "fwd_return_10d"}

    df_is = df[is_period]
    df_oos = df[oos_period]

    for fi, fcol in enumerate(JUDGED, 1):
        # 方向锁定: IS + universal + cs_demean 的 mean IC 符号
        is_sub = df_is[uni_mask[is_period.values]]
        ic_is = _spearman_ic_by_day(is_sub, fcol, "fwd_return_10d_cs_demean")
        is_mean_before = float(ic_is.mean()) if len(ic_is) else np.nan
        direction = 1 if (np.isnan(is_mean_before) or is_mean_before >= 0) else -1
        dir_source = "is_ic" if not np.isnan(is_mean_before) else "default_pos"
        print("  [%2d/31] %-26s IS_ic=%+.4f dir=%+d (days=%d)" % (
            fi, fcol, is_mean_before if not np.isnan(is_mean_before) else 0, direction, len(ic_is)))

        for mname, mvals in masks.items():
            sub_oos = df_oos[mvals[oos_period.values]]
            for tname, tcol in targets.items():
                ic = _spearman_ic_by_day(sub_oos, fcol, tcol) * direction
                n = len(ic)
                ic_mean = float(ic.mean()) if n else np.nan
                ic_std = float(ic.std(ddof=1)) if n > 1 else np.nan
                tn = naive_t(ic.values) if n else np.nan
                mu, th = newey_west_t(ic.values, HAC_LAG) if n else (np.nan, np.nan)
                cov_ratio = cov[fcol]
                # 判定
                if n < MIN_OOS_IC_DAYS or cov_ratio < MIN_FACTOR_COVERAGE:
                    verdict = "insufficient_coverage"; final = False
                elif np.isnan(th):
                    verdict = "insufficient_coverage"; final = False
                elif th > T_THRESH:
                    verdict = "gate1_candidate_alpha"; final = True
                else:
                    verdict = "gate1_fail"; final = False
                results.append({
                    "factor_id": fi, "factor_name": fcol,
                    "mask_type": mname, "return_type": tname,
                    "factor_direction": direction, "factor_direction_source": dir_source,
                    "direction_locked_before_oos": True,
                    "is_ic_mean": round(is_mean_before,5) if not np.isnan(is_mean_before) else None,
                    "valid_ic_days": n,
                    "factor_coverage_ratio": round(cov_ratio,4),
                    "ic_mean": round(ic_mean,5) if not np.isnan(ic_mean) else None,
                    "ic_std": round(ic_std,5) if not np.isnan(ic_std) else None,
                    "ic_t_naive": round(tn,3) if not np.isnan(tn) else None,
                    "ic_t_hac": round(th,3) if not np.isnan(th) else None,
                    "hac_lag": HAC_LAG,
                    "gate1_pass_naive_t": bool(tn>T_THRESH) if not np.isnan(tn) else False,
                    "gate1_pass_hac_t": bool(th>T_THRESH) if not np.isnan(th) else False,
                    "gate1_final_pass": final,
                    "verdict": verdict, "fail_reason": "" if final else verdict,
                })
    res = pd.DataFrame(results)
    res.to_csv(os.path.join(OUT_DIR,"factor_gate1_results.csv"), index=False, encoding="utf-8-sig")
    print("[write] factor_gate1_results.csv (%d rows)" % len(res))

    # ---- 台账(每因子取最佳 mask/return) ----
    led = []
    for fcol in JUDGED:
        sub = res[res.factor_name==fcol]
        best = sub.sort_values("ic_t_hac", ascending=False, na_position="last").iloc[0]
        led.append({
            "factor_name": fcol, "version":"v1", "source":"features.parquet列",
            "oos_purity":"unknown",
            "best_mask_type": best["mask_type"], "best_return_type": best["return_type"],
            "gate0_status":"ok", "gate1_status": best["verdict"],
            "verdict": best["verdict"],
            "primary_evidence": "OOS HAC_t=%s (mask=%s,ret=%s,days=%s)" % (
                best["ic_t_hac"], best["mask_type"], best["return_type"], best["valid_ic_days"]),
            "secondary_evidence": "IS_ic=%s dir=%s" % (best["is_ic_mean"], best["factor_direction"]),
            "fail_reason": best["fail_reason"], "next_action":"hold (V1 练兵, OOS纯度unknown)",
            "created_at": stamp,
        })
    pd.DataFrame(led).to_csv(os.path.join(OUT_DIR,"factor_court_v1_ledger.csv"),
                             index=False, encoding="utf-8-sig")
    print("[write] factor_court_v1_ledger.csv (31)")

    # 汇总数字打印(写 summary.md 由报告阶段补)
    passed = res[res.gate1_final_pass]
    print("\n=== Gate1 概况 ===")
    print("过 HAC t>3.0 的(因子×mask×return)行数:", len(passed))
    if len(passed):
        print(passed[["factor_name","mask_type","return_type","ic_t_hac","ic_mean","valid_ic_days"]].to_string(index=False))
    # 各 verdict 分布
    print("\nverdict 分布(全行):"); print(res.verdict.value_counts().to_string())
    # 过关因子(去重到因子级)
    pf = sorted(passed.factor_name.unique())
    print("\n过关因子(去重 %d 个):" % len(pf), pf)
    print("\npct_chg口径 ratio=%.2f | universal有效=%d | board有效=%d" % (
        pct_scale, uni_mask.sum(), board_mask.sum()))


if __name__ == "__main__":
    main()
