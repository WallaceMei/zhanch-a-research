# -*- coding: utf-8 -*-
#
# gate1_run.py -- 打板事件模块 A0 / Gate1: 池内 Rank IC + HAC t + 滚动验证 + 自检
#
# 读已落盘 board_event_panel.parquet;自算纯K线基础字段并入面板;
# 5 个纯K线测试因子(从194里筛出);三池×四收益周期;cs_rank 在"当日池内"算;
# 防泄漏(因子只用<=T);自检 10.3 泄漏 + 10.4 打乱目标必须归零(不归零即停)。
# 不接194全量、不做 Gate2/3/4、不碰2026调参、不标 robust_alpha。环境 .venv_court。

import os, json
from math import sqrt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OUT_DIR = r"D:\Code\JQ\战车A\research\board_event_a0"
PANEL   = os.path.join(OUT_DIR, "board_event_panel.parquet")
FEATURES= r"C:\quant_project\features.parquet"
LOAD_START, LOAD_END = pd.Timestamp("2023-06-01"), pd.Timestamp("2026-04-03")  # 留足 60 日 lookback

POOLS = {"event_pool_all":25, "first_board_pool":15, "multi_board_pool":10}
MULTI_FLOOR = 8
HORIZONS = {"T1":("fwd_return_T1open_to_T1close",1), "T2":("fwd_return_T1open_to_T2close",2),
            "T3":("fwd_return_T1open_to_T3close",3), "T5":("fwd_return_T1open_to_T5close",5)}
T_THRESH = 3.0

# ---- 5 个测试因子(从 rdagent_factors_v4.jsonl 筛出的纯K线因子,公式硬编码,cs_rank=池内pct rank)----
# 基础字段: return_3d, rsi_14, bb_position, up_streak, vol_ratio_5d, price_position_60d
def csr(s):  # cs_rank = 池内 pct rank
    return s.rank(pct=True)
FACTORS = {
 "F1_trend_breakout_a":      # #1: cs_rank(return_3d*price_position_60d)*(1-cs_rank(rsi_14))
   lambda d: csr(d["return_3d"]*d["price_position_60d"]) * (1 - csr(d["rsi_14"])),
 "F2_trend_breakout_b":      # #6: cs_rank(return_3d*bb_position)*cs_rank(1/(rsi_14+1e-5))*cs_rank(up_streak)
   lambda d: csr(d["return_3d"]*d["bb_position"]) * csr(1/(d["rsi_14"]+1e-5)) * csr(d["up_streak"]),
 "F3_trend_consolidation":   # #12
   lambda d: csr(d["return_3d"]*d["bb_position"]) * csr(d["price_position_60d"]) * csr(1/(d["rsi_14"]+1e-5)),
 "F4_trend_vol_confirm":     # #24
   lambda d: csr(d["return_3d"]*d["bb_position"]*d["up_streak"]) * csr(d["vol_ratio_5d"]/(d["rsi_14"]+1e-5)),
 "F5_trend_mom_vol_confirm": # #30 (与#24公式相同, 保留以验证法庭对同式因子的处理)
   lambda d: csr(d["return_3d"]*d["bb_position"]*d["up_streak"]) * csr(d["vol_ratio_5d"]/(d["rsi_14"]+1e-5)),
}
BASE_FIELDS = ["return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d"]
# 泄漏黑名单(自检10.3)
LEAK_TOKENS = ["fwd_return","future_return","fwd","T+1","T+2","T+3","T+5","_T1close","_T3close"]


def wilder_rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0.0); dn = (-d).clip(lower=0.0)
    rs = up.ewm(alpha=1.0/n, adjust=False).mean() / (dn.ewm(alpha=1.0/n, adjust=False).mean()+1e-12)
    return 100 - 100/(1+rs)

def up_streak_calc(close):
    up = (close.diff() > 0).astype(int)
    # 连续上涨天数
    grp = (up==0).cumsum()
    return up.groupby(grp).cumsum()

def build_base_fields():
    cols=["ts_code","trade_date","high_adj","low_adj","close_adj","vol"]
    df=pq.read_table(FEATURES,columns=cols).to_pandas()
    df["trade_date"]=pd.to_datetime(df["trade_date"])
    df=df[(df.trade_date>=LOAD_START)&(df.trade_date<=LOAD_END)].sort_values(["ts_code","trade_date"])
    g=df.groupby("ts_code",sort=False)
    c=df["close_adj"]
    df["return_3d"]=g["close_adj"].transform(lambda s: s/s.shift(3)-1.0)
    df["rsi_14"]=g["close_adj"].transform(lambda s: wilder_rsi(s,14))
    ma20=g["close_adj"].transform(lambda s: s.rolling(20).mean())
    sd20=g["close_adj"].transform(lambda s: s.rolling(20).std())
    df["bb_position"]=(df["close_adj"]-ma20)/(2*sd20+1e-12)
    df["up_streak"]=g["close_adj"].transform(lambda s: up_streak_calc(s))
    df["vol_ratio_5d"]=df["vol"]/g["vol"].transform(lambda s: s.rolling(5).mean()).replace(0,np.nan)
    hh=g["high_adj"].transform(lambda s: s.rolling(60).max())
    ll=g["low_adj"].transform(lambda s: s.rolling(60).min())
    df["price_position_60d"]=(df["close_adj"]-ll)/((hh-ll)+1e-12)
    return df[["ts_code","trade_date"]+BASE_FIELDS].rename(columns={"ts_code":"code","trade_date":"date"})

def newey_west_t(x, lag):
    x=np.asarray(x,float); n=x.size
    if n<5: return np.nan
    mu=x.mean(); d=x-mu; var=(d@d)/n
    for l in range(1,min(lag,n-1)+1):
        w=1.0-l/(lag+1.0); var+=2.0*w*(d[l:]@d[:-l])/n
    if var<=0: return np.nan
    return mu/sqrt(var/n)

def naive_t(x):
    x=np.asarray(x,float); n=x.size
    if n<5: return np.nan
    sd=x.std(ddof=1)
    return np.nan if sd==0 else x.mean()/sd*sqrt(n)

def daily_ic_one(panel, fname, ffun, pool, ret_col, min_s, shuffle=False, seed=0):
    """逐日池内 Rank IC + spread。返回 DataFrame(date,sample_count,rank_ic,top_bottom_spread,small_sample_warning)。"""
    rows=[]
    rng=np.random.RandomState(seed)
    sub_all = panel[panel[pool] & panel["_valid"] & panel[ret_col].notna()]
    for d, g in sub_all.groupby("date"):
        g=g.dropna(subset=BASE_FIELDS)
        n=len(g)
        warn=False; eff_min=min_s
        if pool=="multi_board_pool" and n<min_s and n>=MULTI_FLOOR:
            eff_min=MULTI_FLOOR; warn=True
        if n<eff_min: continue
        fv=ffun(g)  # 池内 cs_rank 合成
        y=g[ret_col].values.copy()
        if shuffle: rng.shuffle(y)
        x=fv.values
        m=~(np.isnan(x)|np.isnan(y))
        if m.sum()<eff_min: continue
        xr=pd.Series(x[m]).rank(); yr=pd.Series(y[m]).rank()
        ic=xr.corr(yr)
        # spread top30%-bottom30%
        xs=pd.Series(x[m]); ys=y[m]
        q70=xs.quantile(0.7); q30=xs.quantile(0.3)
        top=ys[xs>=q70]; bot=ys[xs<=q30]
        spread=(top.mean()-bot.mean()) if (len(top)>0 and len(bot)>0) else np.nan
        rows.append({"date":d,"sample_count":int(m.sum()),"rank_ic":ic,
                     "top_bottom_spread":spread,"small_sample_warning":warn})
    return pd.DataFrame(rows)

def rolling_validate(ic_series, M, K, step):
    """ic_series: DataFrame(date, rank_ic) 已按日期排序。返回滚动窗口行。"""
    s=ic_series.dropna(subset=["rank_ic"]).reset_index(drop=True)
    out=[]; n=len(s)
    i=0
    while i+M+K<=n:
        tr=s.iloc[i:i+M]; va=s.iloc[i+M:i+M+K]
        direction=1 if tr["rank_ic"].mean()>=0 else -1
        tr_ic=tr["rank_ic"].mean()
        va_ic=va["rank_ic"].mean()*direction
        va_t=newey_west_t((va["rank_ic"]*direction).values, K)  # 验证窗 hac
        out.append({"train_start":tr["date"].iloc[0],"train_end":tr["date"].iloc[-1],
            "valid_start":va["date"].iloc[0],"valid_end":va["date"].iloc[-1],
            "train_mean_ic":tr_ic,"valid_mean_ic":va_ic,"valid_hac_t":va_t,
            "direction_locked_by_train":True,"direction":direction,
            "pass_validation":bool(va_ic>0)})
        i+=step
    return pd.DataFrame(out)

def main():
    # 自检 10.3 泄漏: 检查测试因子用到的字段名是否含未来标签
    leak=[f for f in BASE_FIELDS if any(tok.lower() in f.lower() for tok in ["fwd","future"])]
    selfcheck_103 = (len(leak)==0)
    print("[selfcheck10.3 泄漏] 测试因子基础字段:", BASE_FIELDS, "-> 含未来标签字段:", leak or "无", "=> ", "PASS" if selfcheck_103 else "FAIL")
    if not selfcheck_103:
        print("SELF_CHECK_FAILED(泄漏) 停止"); return

    panel=pd.read_parquet(PANEL)
    panel["date"]=pd.to_datetime(panel["date"])
    base=build_base_fields()
    panel=panel.merge(base, on=["code","date"], how="left")
    # 有效样本: 非ST 非停牌 T+1可买 (fwd 在各horizon各自判)
    panel["_valid"]=(~panel["is_st"]) & (~panel["is_paused"]) & (panel["tradable_next_open"])
    print("[merge] 面板 %d 行, 有效(非ST/非停/可买) %d 行, 基础字段非空 %d 行" % (
        len(panel), int(panel["_valid"].sum()), int(panel[BASE_FIELDS].notna().all(axis=1).sum())))

    daily_rows=[]; g1_rows=[]; roll_rows=[]; shuffle_rows=[]
    for fname,ffun in FACTORS.items():
        for pool,min_s in POOLS.items():
            for hz,(rc,lag) in HORIZONS.items():
                ic=daily_ic_one(panel,fname,ffun,pool,rc,min_s)
                if len(ic)==0:
                    g1_rows.append({"factor_name":fname,"pool_type":pool,"return_horizon":hz,
                        "valid_ic_days":0,"mean_ic":np.nan,"std_ic":np.nan,"naive_t":np.nan,
                        "hac_t":np.nan,"hac_lag":lag,"mean_top_bottom_spread":np.nan,
                        "gate1_pass":False,"fail_reason":"no_valid_days"})
                    continue
                ic=ic.sort_values("date").reset_index(drop=True)
                for _,r in ic.iterrows():
                    daily_rows.append({"factor_name":fname,"pool_type":pool,"return_horizon":hz,
                        "date":r["date"],"sample_count":r["sample_count"],"rank_ic":r["rank_ic"],
                        "top_bottom_spread":r["top_bottom_spread"],"small_sample_warning":r["small_sample_warning"]})
                arr=ic["rank_ic"].dropna().values
                nt=naive_t(arr); ht=newey_west_t(arr,lag)
                g1_rows.append({"factor_name":fname,"pool_type":pool,"return_horizon":hz,
                    "valid_ic_days":len(arr),"mean_ic":float(np.mean(arr)),"std_ic":float(np.std(arr,ddof=1)) if len(arr)>1 else np.nan,
                    "naive_t":nt,"hac_t":ht,"hac_lag":lag,
                    "mean_top_bottom_spread":float(ic["top_bottom_spread"].mean()),
                    "gate1_pass":bool((not np.isnan(ht)) and ht>T_THRESH and len(arr)>=60),
                    "fail_reason":("" if ((not np.isnan(ht)) and ht>T_THRESH and len(arr)>=60) else "hac_t<=3_or_few_days")})
                # 滚动 M120 / M60 (各 pool×horizon)
                for wt,M in [("M120",120),("M60",60)]:
                    rv=rolling_validate(ic[["date","rank_ic"]],M,20,20)
                    for _,w in rv.iterrows():
                        roll_rows.append({"factor_name":fname,"pool_type":pool,"return_horizon":hz,
                            "window_type":wt, **w.to_dict()})
        # 自检10.4 打乱目标(主池 event_pool_all × 主收益 T3)
        ic_sh=daily_ic_one(panel,fname,ffun,"event_pool_all","fwd_return_T1open_to_T3close",25,shuffle=True,seed=42)
        arr_sh=ic_sh["rank_ic"].dropna().values
        shuffle_rows.append({"factor_name":fname,"shuffled_mean_ic":float(np.mean(arr_sh)) if len(arr_sh) else np.nan,
            "shuffled_hac_t":newey_west_t(arr_sh,3) if len(arr_sh) else np.nan,"days":len(arr_sh)})

    pd.DataFrame(daily_rows).to_csv(os.path.join(OUT_DIR,"board_event_daily_ic.csv"),index=False,encoding="utf-8-sig")
    g1=pd.DataFrame(g1_rows); g1.to_csv(os.path.join(OUT_DIR,"board_event_gate1_results.csv"),index=False,encoding="utf-8-sig")
    pd.DataFrame(roll_rows).to_csv(os.path.join(OUT_DIR,"board_event_rolling_validation.csv"),index=False,encoding="utf-8-sig")

    # 自检10.4 判定
    sh=pd.DataFrame(shuffle_rows)
    sh_ok = bool((sh["shuffled_hac_t"].abs()<2.0).all() and (sh["shuffled_mean_ic"].abs()<0.02).all())
    print("\n=== 自检10.4 打乱目标(主池T3)===")
    print(sh.to_string(index=False))
    print("打乱后全部 |hac_t|<2 且 |mean_ic|<0.02 => ", "PASS(归零)" if sh_ok else "FAIL(未归零,疑泄漏)")

    print("\n=== Gate1 主口径(event_pool_all × T3)===")
    main_g1=g1[(g1.pool_type=="event_pool_all")&(g1.return_horizon=="T3")]
    print(main_g1[["factor_name","valid_ic_days","mean_ic","naive_t","hac_t","mean_top_bottom_spread","gate1_pass"]].to_string(index=False))
    if not sh_ok:
        print("\nSELF_CHECK_FAILED(打乱目标未归零) -> 停止,不下 Gate1 判定")
        return
    # 落 selfcheck 标记 + 返回 g1/sh 供 summary
    sh.to_csv(os.path.join(OUT_DIR,"_shuffle_selfcheck.csv"),index=False,encoding="utf-8-sig")
    print("\n[done] 4 文件已写; 自检10.3/10.4 通过")
    return

if __name__=="__main__":
    main()
