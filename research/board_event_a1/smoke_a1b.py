# -*- coding: utf-8 -*-
# A1b 冒烟测试: 字段审计 + 前几个因子 Gate1(主口径) + 打乱目标自检。
# 确认链路通 + 打乱归零, 再跑全量125。不下判定。环境 .venv_court。
import os, json, re
from math import sqrt
import numpy as np, pandas as pd
import pyarrow.parquet as pq

A1=r"D:\Code\JQ\战车A\research\board_event_a1"
PANEL=os.path.join(A1,"board_event_panel_full.parquet")
FEATURES=r"C:\quant_project\features.parquet"
JSONL=r"C:\quant_project\limit_up\qlib_results\rdagent_factors_v4.jsonl"
SEAL_FIELDS={"seal_strength","seal_ratio","seal_minutes","open_times","limit_turnover"}
AVAILABLE={"return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d",
  "retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
  "daily_total_limits","market_max_board","first_board_ratio","lhb_net","on_lhb",
  "seal_strength","seal_ratio","seal_minutes","open_times","float_mv_yi","limit_turnover","industry_limit_count"}

def wilder_rsi(c,n=14):
    d=c.diff(); up=d.clip(lower=0); dn=(-d).clip(lower=0)
    rs=up.ewm(alpha=1/n,adjust=False).mean()/(dn.ewm(alpha=1/n,adjust=False).mean()+1e-12)
    return 100-100/(1+rs)

def add_kline_base(panel):
    cols=["ts_code","trade_date","high_adj","low_adj","close_adj","vol"]
    df=pq.read_table(FEATURES,columns=cols).to_pandas()
    df["trade_date"]=pd.to_datetime(df["trade_date"])
    df=df[(df.trade_date>=pd.Timestamp("2023-06-01"))&(df.trade_date<=pd.Timestamp("2026-04-03"))]
    df=df.sort_values(["ts_code","trade_date"])
    g=df.groupby("ts_code",sort=False)
    df["return_3d"]=g["close_adj"].transform(lambda s:s/s.shift(3)-1)
    df["rsi_14"]=g["close_adj"].transform(lambda s:wilder_rsi(s))
    ma20=g["close_adj"].transform(lambda s:s.rolling(20).mean()); sd20=g["close_adj"].transform(lambda s:s.rolling(20).std())
    df["bb_position"]=(df["close_adj"]-ma20)/(2*sd20+1e-12)
    df["up_streak"]=g["close_adj"].transform(lambda s:( (s.diff()>0).astype(int) ).groupby((s.diff()<=0).cumsum()).cumsum() if False else None)
    # up_streak 用简单实现
    def ups(s):
        u=(s.diff()>0).astype(int); grp=(u==0).cumsum(); return u.groupby(grp).cumsum()
    df["up_streak"]=g["close_adj"].transform(ups)
    df["vol_ratio_5d"]=df["vol"]/g["vol"].transform(lambda s:s.rolling(5).mean()).replace(0,np.nan)
    hh=g["high_adj"].transform(lambda s:s.rolling(60).max()); ll=g["low_adj"].transform(lambda s:s.rolling(60).min())
    df["price_position_60d"]=(df["close_adj"]-ll)/((hh-ll)+1e-12)
    base=df[["ts_code","trade_date","return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d"]]\
        .rename(columns={"ts_code":"code","trade_date":"date"})
    return panel.merge(base,on=["code","date"],how="left")

def make_eval(formula):
    ns_funcs={"cs_rank":lambda s: s.rank(pct=True), "np":np}
    def f(sub):
        return eval(formula, {"__builtins__":{}}, dict(ns_funcs, df=sub))
    return f

def nw_t(x,lag):
    x=np.asarray(x,float); n=x.size
    if n<5: return np.nan
    mu=x.mean(); d=x-mu; v=(d@d)/n
    for l in range(1,min(lag,n-1)+1):
        w=1-l/(lag+1); v+=2*w*(d[l:]@d[:-l])/n
    return mu/sqrt(v/n) if v>0 else np.nan

def main():
    panel=pd.read_parquet(PANEL); panel["date"]=pd.to_datetime(panel["date"])
    panel=add_kline_base(panel)
    print("[panel] %d 行, 加 kline base 后列=%d"%(len(panel),panel.shape[1]))

    # 字段审计(125 can_calc + seal_dependent)
    recs=[]
    for line in open(JSONL,encoding="utf-8"):
        line=line.strip()
        if line: recs.append(json.loads(line))
    audit=[]
    for i,r in enumerate(recs):
        fu=set(str(x).strip() for x in (r.get("fields_used") or []))
        can=fu<=AVAILABLE and len(fu)>0
        audit.append({"factor_id":i,"factor_name":r["name"],"formula":r["formula"],
            "fields":fu,"can":can,"seal_dependent":bool(fu&SEAL_FIELDS),"has_ts":("ts_" in r["formula"])})
    cc=[a for a in audit if a["can"]]
    print("can_calculate=%d (seal_dependent=%d, 含ts_=%d)"%(len(cc),
        sum(a["seal_dependent"] for a in cc), sum(a["has_ts"] for a in cc)))

    # 冒烟: 选5个无ts的(3非seal+2seal)
    nonts=[a for a in cc if not a["has_ts"]]
    nonseal=[a for a in nonts if not a["seal_dependent"]][:3]
    seal=[a for a in nonts if a["seal_dependent"]][:2]
    pick=nonseal+seal
    print("\n冒烟选 %d 个因子:"%len(pick))
    for a in pick: print("  id%d %s seal=%s | %s"%(a["factor_id"],a["factor_name"],a["seal_dependent"],a["formula"][:90]))

    # Gate1 主口径 event_pool_all + T3 + 打乱自检
    RC="fwd_return_T1open_to_T3close"; LAG=3; MIN=25
    base_valid=(~panel["is_st"])&(~panel["is_paused"])&(panel["tradable_next_open"])&(panel[RC].notna())
    print("\n=== 冒烟 Gate1(event_pool_all, T+3) + 打乱自检 ===")
    rng=np.random.RandomState(42)
    for a in pick:
        fields=list(a["fields"])
        fe=make_eval(a["formula"])
        # 样本: seal 因子限 in_limit_list_d & sealed_limit
        m=panel["event_pool_all"]&base_valid&panel[fields].notna().all(axis=1)
        if a["seal_dependent"]: m=m&panel["in_limit_list_d"]&panel["sealed_limit"]
        sub=panel[m]
        ics=[]; ics_sh=[]
        for d,g in sub.groupby("date"):
            if len(g)<MIN: continue
            fv=fe(g)
            y=g[RC].values
            ok=fv.notna()&pd.Series(y,index=g.index).notna()
            if ok.sum()<MIN: continue
            xr=fv[ok].rank(); yr=pd.Series(y,index=g.index)[ok].rank()
            ics.append(xr.corr(yr))
            ysh=y.copy(); rng.shuffle(ysh)
            yr2=pd.Series(ysh,index=g.index)[ok].rank()
            ics_sh.append(xr.corr(yr2))
        ics=np.array([x for x in ics if not np.isnan(x)]); ics_sh=np.array([x for x in ics_sh if not np.isnan(x)])
        print("  id%-3d %-34s days=%d ic_mean=%+.4f hac_t=%+.2f || 打乱 ic=%+.4f hac_t=%+.2f"%(
            a["factor_id"],a["factor_name"][:34],len(ics),
            ics.mean() if len(ics) else np.nan, nw_t(ics,LAG) if len(ics) else np.nan,
            ics_sh.mean() if len(ics_sh) else np.nan, nw_t(ics_sh,LAG) if len(ics_sh) else np.nan))
    print("\n[冒烟完] 若上面 days>0、ic 算出、打乱后 hac_t 接近0 => 链路通+归零, 可跑全量")

if __name__=="__main__":
    main()
