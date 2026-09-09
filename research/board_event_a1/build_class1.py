# -*- coding: utf-8 -*-
# A1a 类1: 纯K线/日线/市场级字段补齐(零外部依赖)。复用 A0 事件池,不重造。
# 类1a 逐股日线: retail_line, retail_line_change, vol_vs_prev, intraday_range, kdj_j
# 类1b 市场级:  daily_total_limits, market_max_board, first_board_ratio
# 不碰2026调参(标签可溢);不硬造缺失字段。环境 .venv_court。
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

A0_PANEL = r"D:\Code\JQ\战车A\research\board_event_a0\board_event_panel.parquet"
FEATURES = r"C:\quant_project\features.parquet"
OUT_DIR  = r"D:\Code\JQ\战车A\research\board_event_a1"
LOAD_START, LOAD_END = pd.Timestamp("2023-06-01"), pd.Timestamp("2026-04-03")

def limit_rate(ts_code, name):
    nm="" if name is None else str(name); code=str(ts_code)
    if ("ST" in nm) or ("退" in nm): return 0.05
    if code[:3]=="688" or code[:2]=="30": return 0.20
    if code[:1] in ("8","4"): return 0.30
    return 0.10

def kdj_j(high, low, close, n=9):
    llv=low.rolling(n).min(); hhv=high.rolling(n).max()
    rsv=100*(close-llv)/((hhv-llv)+1e-12)
    k=rsv.ewm(alpha=1/3,adjust=False).mean()
    d=k.ewm(alpha=1/3,adjust=False).mean()
    return 3*k-2*d

def main():
    if not os.path.exists(OUT_DIR): os.makedirs(OUT_DIR)
    panel=pd.read_parquet(A0_PANEL); panel["date"]=pd.to_datetime(panel["date"])
    cols=["ts_code","trade_date","name","high","low","close","high_adj","low_adj","close_adj","vol"]
    df=pq.read_table(FEATURES,columns=cols).to_pandas()
    df["trade_date"]=pd.to_datetime(df["trade_date"])
    df=df[(df.trade_date>=LOAD_START)&(df.trade_date<=LOAD_END)].sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    g=df.groupby("ts_code",sort=False)

    # ---- 类1a 逐股 ----
    hh60=g["high_adj"].transform(lambda s:s.rolling(60).max())
    ll60=g["low_adj"].transform(lambda s:s.rolling(60).min())
    df["retail_line"]=100*(hh60-df["close_adj"])/((hh60-ll60)+1e-12)
    df["retail_line_change"]=df.groupby("ts_code",sort=False)["retail_line"].diff()  # 按股日变化
    df["vol_vs_prev"]=df["vol"]/g["vol"].shift(1)-1.0
    pre_close=g["close"].shift(1)
    df["intraday_range"]=(df["high"]-df["low"])/(pre_close+1e-12)
    df["kdj_j"]=df.groupby("ts_code",sort=False,group_keys=False).apply(
        lambda x: kdj_j(x["high_adj"],x["low_adj"],x["close_adj"]))

    # ---- 类1b 市场级(全市场每日聚合)----
    df["rate"]=[limit_rate(c,n) for c,n in zip(df.ts_code,df.name)]
    lp=(pre_close*(1+df["rate"])).round(2)
    df["_sealed"]=(df["close"]>=lp*0.995)&lp.notna()
    def trailing(s):
        out=np.zeros(len(s),int); run=0
        for i in range(len(s)): out[i]=run; run=run+1 if s[i] else 0
        return out
    df["_prev_consec"]=df.groupby("ts_code",sort=False)["_sealed"].transform(lambda s: trailing(s.values))
    df["_board_height"]=np.where(df["_sealed"], df["_prev_consec"]+1, 0)
    df["_first_board"]=df["_sealed"]&(df["_prev_consec"]==0)
    daily=df.groupby("trade_date").agg(
        daily_total_limits=("_sealed","sum"),
        market_max_board=("_board_height","max"),
        _first=("_first_board","sum")).reset_index()
    daily["first_board_ratio"]=daily["_first"]/daily["daily_total_limits"].replace(0,np.nan)
    mkt=daily[["trade_date","daily_total_limits","market_max_board","first_board_ratio"]].rename(columns={"trade_date":"date"})

    # ---- 并入 A0 事件面板 ----
    f1=df[["ts_code","trade_date","retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j"]]\
        .rename(columns={"ts_code":"code","trade_date":"date"})
    out=panel.merge(f1,on=["code","date"],how="left").merge(mkt,on="date",how="left")
    # industry_limit_count / morning_vol_ratio / tail_vol_ratio: 本步未补,标缺
    for c in ["industry_limit_count","morning_vol_ratio","tail_vol_ratio"]:
        out[c]=np.nan
    out.to_parquet(os.path.join(OUT_DIR,"board_event_panel_class1.parquet"),index=False)

    # ---- 覆盖率 ----
    NEW=["retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
         "daily_total_limits","market_max_board","first_board_ratio",
         "industry_limit_count","morning_vol_ratio","tail_vol_ratio"]
    src={"retail_line":"features日线(60HHV/LLV)","retail_line_change":"features日线",
         "vol_vs_prev":"features日线","intraday_range":"features日线","kdj_j":"features日线",
         "daily_total_limits":"features全市场聚合","market_max_board":"features全市场聚合",
         "first_board_ratio":"features全市场聚合","industry_limit_count":"需行业表(未补)",
         "morning_vol_ratio":"需分钟(未补)","tail_vol_ratio":"需分钟(未补)"}
    rows=[]
    for c in NEW:
        nn=int(out[c].notna().sum()); cr=nn/len(out)
        qs="ok" if cr>=0.95 else ("partial" if cr>=0.5 else ("unavailable" if nn==0 else "low_coverage"))
        rows.append({"field":c,"coverage_start":str(out.loc[out[c].notna(),"date"].min())[:10] if nn else "",
            "coverage_end":str(out.loc[out[c].notna(),"date"].max())[:10] if nn else "",
            "non_null_count":nn,"coverage_ratio":round(cr,4),"data_source":src[c],"quality_status":qs})
    cov=pd.DataFrame(rows); cov.to_csv(os.path.join(OUT_DIR,"board_field_coverage_class1.csv"),index=False,encoding="utf-8-sig")
    print("[class1] 面板行=%d" % len(out))
    print(cov.to_string(index=False))

    # ---- 小样本验证: retail_line 复算(1股手算对比)----
    print("\n=== retail_line 小样本验证(随机1股,手算HHV/LLV对比)===")
    s=df[df.ts_code=="000001.SZ"].sort_values("trade_date").reset_index(drop=True)
    s=s[s.trade_date>="2024-03-01"].reset_index(drop=True)
    for i in [70,90]:
        win=df[(df.ts_code=="000001.SZ")].sort_values("trade_date").reset_index(drop=True)
        pos=win.index[win.trade_date==s.trade_date[i]][0]
        w=win.iloc[pos-59:pos+1]
        hh=w["high_adj"].max(); ll=w["low_adj"].min(); c=win["close_adj"].iloc[pos]
        manual=100*(hh-c)/((hh-ll)+1e-12)
        print("  %s retail_line 模块=%.3f 手算=%.3f 一致=%s" % (
            str(s.trade_date[i])[:10], win["retail_line"].iloc[pos], manual, abs(manual-win["retail_line"].iloc[pos])<1e-3))
    print("\n=== 市场级抽查(几天 daily_total_limits / max_board / first_ratio)===")
    for d in ["2024-09-30","2024-10-08","2025-06-30","2025-12-31"]:
        r=mkt[mkt.date==pd.Timestamp(d)]
        if len(r): print("  %s total_limits=%d max_board=%d first_ratio=%.2f" % (
            d,r.daily_total_limits.iloc[0],r.market_max_board.iloc[0],r.first_board_ratio.iloc[0]))

if __name__=="__main__":
    main()
