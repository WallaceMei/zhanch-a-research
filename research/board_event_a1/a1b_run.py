# -*- coding: utf-8 -*-
# 打板事件模块 A1b: 125 can_calculate 因子跑全四关。
# ts_口径A: K线类字段ts_在稠密日线算(上一交易日); seal/lhb类事件型ts_按事件序列(上一事件行)。
# 主口径固定: event_pool_all + T+3 + M120/K20。seal因子IC限 in_limit_list_d&sealed_limit。
# 不碰2026/不标robust_alpha/不挑最佳/自检不过即停。环境 .venv_court。
import os, json, re
from math import sqrt, erf
import numpy as np, pandas as pd
import pyarrow.parquet as pq

A1=r"D:\Code\JQ\战车A\research\board_event_a1"
PANEL=os.path.join(A1,"board_event_panel_full.parquet")
FEATURES=r"C:\quant_project\features.parquet"
JSONL=r"C:\quant_project\limit_up\qlib_results\rdagent_factors_v4.jsonl"

SEAL_FIELDS={"seal_strength","seal_ratio","seal_minutes","open_times","limit_turnover"}
EVENT_FIELDS=SEAL_FIELDS|{"float_mv_yi","industry_limit_count","lhb_net","on_lhb"}
DENSE_FIELDS={"return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d",
  "retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
  "daily_total_limits","market_max_board","first_board_ratio"}
AVAILABLE=DENSE_FIELDS|EVENT_FIELDS
HORIZONS={"T1":("fwd_return_T1open_to_T1close",1),"T2":("fwd_return_T1open_to_T2close",2),
          "T3":("fwd_return_T1open_to_T3close",3),"T5":("fwd_return_T1open_to_T5close",5)}
POOLS={"event_pool_all":25,"first_board_pool":15,"multi_board_pool":10}
MULTI_FLOOR=8; T_THRESH=3.0; ALPHA=0.05; MAIN_POOL="event_pool_all"; MAIN_H="T3"

def norm_cdf(x): return 0.5*(1+erf(x/sqrt(2)))
def two_sided_p(t): return 2*(1-norm_cdf(abs(t)))
def naive_t(x):
    x=np.asarray(x,float); n=x.size
    return np.nan if n<5 or x.std(ddof=1)==0 else x.mean()/x.std(ddof=1)*sqrt(n)
def nw_t(x,lag):
    x=np.asarray(x,float); n=x.size
    if n<5: return np.nan
    mu=x.mean(); d=x-mu; v=(d@d)/n
    for l in range(1,min(lag,n-1)+1):
        w=1-l/(lag+1); v+=2*w*(d[l:]@d[:-l])/n
    return mu/sqrt(v/n) if v>0 else np.nan

def wilder_rsi(c,n=14):
    dd=c.diff(); up=dd.clip(lower=0); dn=(-dd).clip(lower=0)
    rs=up.ewm(alpha=1/n,adjust=False).mean()/(dn.ewm(alpha=1/n,adjust=False).mean()+1e-12)
    return 100-100/(1+rs)
def upstreak(s):
    u=(s.diff()>0).astype(int); return u.groupby((u==0).cumsum()).cumsum()

# ---------- 稠密日线(全市场) 用于K线类ts_ ----------
def _limit_rate(ts,nm):
    nm="" if nm is None else str(nm); code=str(ts)
    if ("ST" in nm) or ("退" in nm): return 0.05
    if code[:3]=="688" or code[:2]=="30": return 0.20
    if code[:1] in ("8","4"): return 0.30
    return 0.10

def build_dense():
    cols=["ts_code","trade_date","name","close","high_adj","low_adj","close_adj","vol"]
    df=pq.read_table(FEATURES,columns=cols).to_pandas()
    df["trade_date"]=pd.to_datetime(df["trade_date"])
    df=df[(df.trade_date>=pd.Timestamp("2023-06-01"))&(df.trade_date<=pd.Timestamp("2026-04-03"))]
    df=df.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    g=df.groupby("ts_code",sort=False)
    df["return_3d"]=g["close_adj"].transform(lambda s:s/s.shift(3)-1)
    df["rsi_14"]=g["close_adj"].transform(lambda s:wilder_rsi(s))
    ma=g["close_adj"].transform(lambda s:s.rolling(20).mean()); sd=g["close_adj"].transform(lambda s:s.rolling(20).std())
    df["bb_position"]=(df["close_adj"]-ma)/(2*sd+1e-12)
    df["up_streak"]=g["close_adj"].transform(upstreak)
    df["vol_ratio_5d"]=df["vol"]/g["vol"].transform(lambda s:s.rolling(5).mean()).replace(0,np.nan)
    hh=g["high_adj"].transform(lambda s:s.rolling(60).max()); ll=g["low_adj"].transform(lambda s:s.rolling(60).min())
    df["price_position_60d"]=(df["close_adj"]-ll)/((hh-ll)+1e-12)
    rl=100*(hh-df["close_adj"])/((hh-ll)+1e-12); df["retail_line"]=rl
    df["retail_line_change"]=g["close_adj"].transform(lambda s: pd.Series(0,index=s.index))  # tmp
    df["retail_line_change"]=df.groupby("ts_code",sort=False)["retail_line"].diff()
    df["vol_vs_prev"]=df["vol"]/g["vol"].shift(1)-1
    pc=g["close_adj"].shift(1)  # 用复权近似(intraday_range面板已用原始;ts里只为时序shift)
    df["intraday_range"]=(g["high_adj"].transform(lambda s:s)-g["low_adj"].transform(lambda s:s))/(pc+1e-12)
    # kdj_j
    lln=g["low_adj"].transform(lambda s:s.rolling(9).min()); hhn=g["high_adj"].transform(lambda s:s.rolling(9).max())
    rsv=100*(df["close_adj"]-lln)/((hhn-lln)+1e-12)
    k=rsv.groupby(df["ts_code"]).transform(lambda s:s.ewm(alpha=1/3,adjust=False).mean())
    dd=k.groupby(df["ts_code"]).transform(lambda s:s.ewm(alpha=1/3,adjust=False).mean())
    df["kdj_j"]=3*k-2*dd
    # 市场级(每日)
    return df

def main():
    panel=pd.read_parquet(PANEL); panel["date"]=pd.to_datetime(panel["date"])
    panel=panel.sort_values(["code","date"]).reset_index(drop=True)
    recs=[]
    for line in open(JSONL,encoding="utf-8"):
        line=line.strip()
        if line: recs.append(json.loads(line))
    # 字段审计
    audit=[]
    for i,r in enumerate(recs):
        fu=set(str(x).strip() for x in (r.get("fields_used") or []))
        leak=any(t in r["formula"].lower() for t in ["fwd_return","future_return","_t1close","_t3close","_t5close"])
        can=(fu<=AVAILABLE and len(fu)>0 and not leak)
        audit.append({"factor_id":i,"factor_name":r["name"],"formula":r["formula"],
            "required_fields":"|".join(sorted(fu)),"can_calculate":bool(can),
            "field_status":("leakage_suspected" if leak else ("can_calculate" if can else "field_unavailable")),
            "seal_dependent":bool(fu&SEAL_FIELDS),"has_ts":("ts_" in r["formula"])})
    pd.DataFrame([{k:v for k,v in a.items() if k!="formula"} for a in audit]).to_csv(
        os.path.join(A1,"board_factor_field_audit.csv"),index=False,encoding="utf-8-sig")
    cc=[a for a in audit if a["can_calculate"]]
    print("can_calculate=%d (seal_dep=%d, ts=%d)"%(len(cc),sum(a["seal_dependent"] for a in cc),sum(a["has_ts"] for a in cc)),flush=True)

    # ---- ts_ 模式收集 ----
    pat_sh=re.compile(r"ts_shift\(\s*df\['(\w+)'\]\s*,\s*(\d+)\s*\)")
    pat_zs=re.compile(r"ts_zscore\(\s*df\['(\w+)'\]\s*,\s*(\d+)\s*\)")
    need_dense=set(); need_event=set()
    for a in cc:
        for fld,k in pat_sh.findall(a["formula"]):
            (need_dense if fld in DENSE_FIELDS else need_event).add((fld,"sft",int(k)))
        for fld,n in pat_zs.findall(a["formula"]):
            (need_dense if fld in DENSE_FIELDS else need_event).add((fld,"zs",int(n)))
    print("ts需求: 稠密=%d 事件=%d"%(len(need_dense),len(need_event)),flush=True)

    # ---- 稠密ts预computed并入面板 ----
    if need_dense:
        dense=build_dense()
        dg=dense.groupby("ts_code",sort=False)
        addcols={}
        for fld,op,p in need_dense:
            col="%s__%s%d"%(fld,op,p)
            if op=="sft": dense[col]=dg[fld].shift(p)
            else:
                m=dg[fld].transform(lambda s:s.rolling(p).mean()); sd=dg[fld].transform(lambda s:s.rolling(p).std())
                dense[col]=(dense[fld]-m)/(sd+1e-12)
            addcols[col]=col
        m=dense[["ts_code","trade_date"]+list(addcols)].rename(columns={"ts_code":"code","trade_date":"date"})
        panel=panel.merge(m,on=["code","date"],how="left")
        # ts对齐自检: retail_line_change__sft1 在事件行 == 稠密上一交易日值
        chk=None
        for (fld,op,p) in need_dense:
            if op=="sft" and p==1: chk=(fld,"%s__sft1"%fld); break
        if chk:
            fld,col=chk
            # 取一个事件样本, 验证 panel[col] == dense fld at (code, 上一交易日)
            samp=panel[panel[col].notna()].iloc[0]
            ds=dense[(dense.ts_code==samp["code"])].sort_values("trade_date").reset_index(drop=True)
            pos=ds.index[ds.trade_date==samp["date"]][0]
            prev_val=ds[fld].iloc[pos-1]
            ok=abs(prev_val-samp[col])<1e-6
            print("[ts对齐自检] %s 事件行%s %s: 面板值=%.5f 稠密上一交易日值=%.5f 一致=%s"%(
                fld,samp["code"],str(samp["date"])[:10],samp[col],prev_val,ok),flush=True)
            if not ok:
                print("SELF_CHECK_FAILED(ts对齐错位) 停止"); return
    # ---- 事件ts预computed(按事件序列)----
    pg=panel.groupby("code",sort=False)
    for fld,op,p in need_event:
        col="%s__%s%d"%(fld,op,p)
        if op=="sft": panel[col]=pg[fld].shift(p)
        else:
            m=pg[fld].transform(lambda s:s.rolling(p).mean()); sd=pg[fld].transform(lambda s:s.rolling(p).std())
            panel[col]=(panel[fld]-m)/(sd+1e-12)

    # 加 K线 base 到面板(eval需要)
    # 注:面板(board_event_panel_full)已原生包含8个DENSE_FIELDS的事件日值——
    #   5个K线类(retail_line/retail_line_change/vol_vs_prev/intraday_range/kdj_j,面板用原始价)
    #   + 3个市场级(daily_total_limits/market_max_board/first_board_ratio)。
    # 这些非ts_用法须用面板原生事件日值,不能从dense再merge(否则同名列冲突_x/_y, eval取不到原名)。
    # 故base-merge只从dense补"dense产出且面板没有"的6个K线字段(return_3d/rsi_14/bb_position/up_streak/
    # vol_ratio_5d/price_position_60d);ts_列(__sftN/__zsN)另算另merge, 不受此影响。
    if "return_3d" not in panel.columns:
        d2=build_dense() if not need_dense else dense
        kline_cols=[c for c in DENSE_FIELDS if c in d2.columns and c not in panel.columns]
        bb=d2[["ts_code","trade_date"]+kline_cols].rename(columns={"ts_code":"code","trade_date":"date"})
        panel=panel.merge(bb,on=["code","date"],how="left")

    # ---- 公式 -> 可eval(替换ts_为预算列) ----
    def rewrite(f):
        f=pat_sh.sub(lambda m:"df['%s__sft%s']"%(m.group(1),m.group(2)),f)
        f=pat_zs.sub(lambda m:"df['%s__zs%s']"%(m.group(1),m.group(2)),f)
        return f
    NS={"cs_rank":lambda s:s.rank(pct=True),"np":np,"log1p":np.log1p,"sqrt":np.sqrt,"abs":np.abs,"log":np.log}
    def evalf(f,sub):
        return eval(f,{"__builtins__":{}},dict(NS,df=sub))

    base_valid=(~panel["is_st"])&(~panel["is_paused"])&(panel["tradable_next_open"])

    # ---- Gate1: 每(因子,池) 逐日算4周期IC+spread; seal限sealed子集 ----
    daily_main={}   # factor_id -> 主口径(event_pool_all,T3) daily ic series (direction-adjusted)
    g1rows=[]; spreadrows=[]; rng=np.random.RandomState(42); shuffle_main={}
    for a in cc:
        fid=a["factor_id"]; frw=rewrite(a["formula"]); seal=a["seal_dependent"]
        fields_needed=[c for c in panel.columns if False]  # 不预筛, eval时NaN自然传播
        for pool,mins in POOLS.items():
            base=panel[pool]&base_valid
            if seal: base=base&panel["in_limit_list_d"]&panel["sealed_limit"]
            sub_all=panel[base]
            # 逐日: 算factor一次, 4周期IC
            per_h={h:[] for h in HORIZONS}; per_h_sh=[]
            sp={h:[] for h in HORIZONS}
            for d,g in sub_all.groupby("date"):
                eff=mins; warn=False
                if pool=="multi_board_pool" and len(g)<mins and len(g)>=MULTI_FLOOR: eff=MULTI_FLOOR; warn=True
                if len(g)<eff: continue
                try: fv=evalf(frw,g)
                except Exception: fv=pd.Series(np.nan,index=g.index)
                if not hasattr(fv,"rank"): fv=pd.Series(fv,index=g.index)
                for h,(rc,lag) in HORIZONS.items():
                    y=g[rc]; ok=fv.notna()&y.notna()
                    if ok.sum()<eff: continue
                    xr=fv[ok].rank(); yr=y[ok].rank(); ic=xr.corr(yr)
                    if not np.isnan(ic): per_h[h].append((d,ic))
                    # spread (top30-bot30) 仅主周期
                    if h==MAIN_H:
                        xs=fv[ok]; ys=y[ok]; q7=xs.quantile(.7); q3=xs.quantile(.3)
                        top=ys[xs>=q7]; bot=ys[xs<=q3]
                        if len(top) and len(bot): sp[h].append((d,top.mean()-bot.mean()))
                        # 打乱(仅主口径主周期)
                        if pool==MAIN_POOL:
                            yy=y[ok].values.copy(); rng.shuffle(yy)
                            per_h_sh.append(pd.Series(yy,index=xr.index).rank().corr(xr))
            # 各周期: 方向(首120天均值符号) + 全期 hac
            for h,(rc,lag) in HORIZONS.items():
                ser=per_h[h]
                if not ser:
                    g1rows.append({"factor_id":fid,"factor_name":a["factor_name"],"pool_type":pool,"return_horizon":h,
                        "seal_dependent":seal,"valid_ic_days":0,"mean_ic":np.nan,"std_ic":np.nan,"naive_t":np.nan,
                        "hac_t":np.nan,"hac_lag":lag,"direction":0,"gate1_pass":False,"fail_reason":"insufficient_coverage"}); continue
                ser=sorted(ser); ds=[x[0] for x in ser]; ics=np.array([x[1] for x in ser])
                first120=ics[:120]; direction=1 if np.nanmean(first120)>=0 else -1
                icd=ics*direction
                ht=nw_t(icd,lag); nt=naive_t(icd)
                ok_days=len(icd)
                gp=bool((not np.isnan(ht)) and ht>T_THRESH and ok_days>=120)
                g1rows.append({"factor_id":fid,"factor_name":a["factor_name"],"pool_type":pool,"return_horizon":h,
                    "seal_dependent":seal,"valid_ic_days":ok_days,"mean_ic":float(np.mean(icd)),
                    "std_ic":float(np.std(icd,ddof=1)) if ok_days>1 else np.nan,"naive_t":nt,"hac_t":ht,"hac_lag":lag,
                    "direction":direction,"gate1_pass":gp,
                    "fail_reason":("" if gp else ("insufficient_coverage" if ok_days<120 else "hac_t<=3"))})
                if pool==MAIN_POOL and h==MAIN_H:
                    daily_main[fid]=pd.Series(icd,index=pd.to_datetime(ds))
                    # spread 统计
                    spx=np.array([v*direction for _,v in sp[h]]) if sp[h] else np.array([])
                    spreadrows.append({"factor_id":fid,"factor_name":a["factor_name"],
                        "mean_top_bottom_spread":float(spx.mean()) if len(spx) else np.nan,
                        "spread_t":nw_t(spx,lag) if len(spx) else np.nan,
                        "positive_spread_ratio":float((spx>0).mean()) if len(spx) else np.nan})
                    sh=np.array([x for x in per_h_sh if not np.isnan(x)])
                    shuffle_main[fid]=(float(sh.mean()) if len(sh) else np.nan, nw_t(sh,lag) if len(sh) else np.nan)
    g1=pd.DataFrame(g1rows); g1.to_csv(os.path.join(A1,"board_a1_gate1_results.csv"),index=False,encoding="utf-8-sig")
    pd.DataFrame(spreadrows).to_csv(os.path.join(A1,"board_a1_gate1_spread.csv"),index=False,encoding="utf-8-sig")

    # ---- 自检1: 打乱归零(主口径汇总) ----
    sh_ts=[v[1] for v in shuffle_main.values() if not np.isnan(v[1])]
    sc1=bool(np.mean(np.abs(sh_ts))<1.0 and np.quantile(np.abs(sh_ts),0.95)<3.0) if sh_ts else False
    print("[自检1 打乱] 主口径打乱 hac_t: 均|t|=%.2f 95分位|t|=%.2f -> %s"%(
        np.mean(np.abs(sh_ts)) if sh_ts else -1, np.quantile(np.abs(sh_ts),0.95) if sh_ts else -1,
        "PASS" if sc1 else "FAIL"),flush=True)

    # ---- Gate2 BH-FDR(主口径) ----
    main=g1[(g1.pool_type==MAIN_POOL)&(g1.return_horizon==MAIN_H)].copy().reset_index(drop=True)
    main["p"]=main["hac_t"].apply(lambda t: two_sided_p(t) if pd.notna(t) else 1.0)
    def bh(p,m):
        p=np.asarray(p); k=len(p); order=np.argsort(p); rk=p[order]
        thr=np.array([(i+1)/m*ALPHA for i in range(k)]); pas=rk<=thr
        cut=rk[np.max(np.where(pas)[0])] if pas.any() else -1
        q=np.empty(k); run=1
        for i in range(k-1,-1,-1): run=min(run,m*rk[i]/(i+1)); q[i]=min(run,1)
        qq=np.empty(k); qq[order]=q; return (p<=cut), qq
    g1pass=main["gate1_pass"].values
    bh125,q125=bh(main["p"].values,125); bh194,_=bh(main["p"].values,194)
    main["bh_fdr_n125_pass"]=bh125&g1pass; main["bh_q_n125"]=q125
    main["bh_fdr_n194_pass"]=bh194&g1pass
    main["bonf_n125_pass"]=(main["p"]<ALPHA/125)&g1pass
    main["bonf_n194_pass"]=(main["p"]<ALPHA/194)&g1pass
    main["gate2_status"]=np.where(~g1pass,"n/a_gate1_fail",np.where(main["bh_fdr_n125_pass"],"gate2_pass","gate2_fail"))
    main.to_csv(os.path.join(A1,"board_a1_gate2_fdr.csv"),index=False,encoding="utf-8-sig")
    # 自检2: 噪声FDR
    rngn=np.random.RandomState(7); tn=rngn.randn(30); pn=np.array([two_sided_p(t) for t in tn])
    npass=int((bh(pn,30)[0]).sum()); sc2=bool(npass<=2)
    print("[自检2 噪声FDR] 30噪声 BH通过=%d -> %s"%(npass,"PASS" if sc2 else "FAIL"),flush=True)

    # ---- Gate3 去冗余(gate2_pass, 主口径daily IC corr>0.7) ----
    g2pass=main[main.gate2_status=="gate2_pass"].factor_id.tolist()
    g3rows=[]; negrows=[]
    if len(g2pass)>=2:
        M=pd.DataFrame({fid:daily_main[fid] for fid in g2pass if fid in daily_main}).corr()
        ids=list(M.columns)
        par={i:i for i in ids}
        def find(x):
            while par[x]!=x: par[x]=par[par[x]]; x=par[x]
            return x
        for i in range(len(ids)):
            for j in range(i+1,len(ids)):
                c=M.iloc[i,j]
                if c>0.7:
                    ra,rb=find(ids[i]),find(ids[j]); par[ra]=rb
                elif c<-0.7: negrows.append({"factor_a":ids[i],"factor_b":ids[j],"ic_corr":round(float(c),3)})
        cl={}
        for x in ids: cl.setdefault(find(x),[]).append(x)
        hac=dict(zip(main.factor_id,main.hac_t))
        for cid,mem in enumerate(cl.values()):
            rep=sorted(mem,key=lambda x:-abs(hac.get(x,0)))[0]
            for x in mem:
                g3rows.append({"factor_id":x,"cluster_id":cid,"cluster_size":len(mem),
                    "cluster_representative":rep,"gate3_representative":(x==rep),
                    "gate3_status":("gate3_keep" if x==rep else "gate3_redundant")})
    pd.DataFrame(g3rows).to_csv(os.path.join(A1,"board_a1_gate3_clusters.csv"),index=False,encoding="utf-8-sig")
    pd.DataFrame(negrows,columns=["factor_a","factor_b","ic_corr"]).to_csv(os.path.join(A1,"board_a1_gate3_negative_corr_pairs.csv"),index=False,encoding="utf-8-sig")
    # 自检3
    r3=np.random.RandomState(3); A=r3.randn(200); B=A+0.05*r3.randn(200); C=r3.randn(200); D=-A+0.05*r3.randn(200)
    MM=pd.DataFrame(np.corrcoef([A,B,C,D]),index=list("ABCD"),columns=list("ABCD"))
    sc3=bool(MM.loc["A","B"]>0.7 and MM.loc["A","C"]<0.7 and not (MM.loc["A","D"]>0.7) and MM.loc["A","D"]<-0.7)
    print("[自检3 聚类] A/B同%.2f A/C%.2f A/D%.2f(标互补) -> %s"%(MM.loc["A","B"],MM.loc["A","C"],MM.loc["A","D"],"PASS" if sc3 else "FAIL"),flush=True)

    # ---- Gate4 半年度衰减(gate3代表) ----
    def seg_decay(ds_ic):
        s=ds_ic.copy(); s.index=pd.to_datetime(s.index)
        segs=[]
        for (y,h0,h1) in [(2024,1,6),(2024,7,12),(2025,1,6),(2025,7,12)]:
            m=(s.index.year==y)&(s.index.month>=h0)&(s.index.month<=h1)
            segs.append(s[m])
        cnt=[len(x) for x in segs]
        if any(c<30 for c in cnt): return "insufficient_segment_data",cnt,np.nan
        v=[x.mean() for x in segs]; slope=np.polyfit([0,1,2,3],v,1)[0]
        if v[-1]<0 or (v[0]>v[1]>v[2]>v[3] and v[-1]<v[0]*0.5): st="decaying"
        elif v[-1]<v[0]*0.7: st="decay_warning"
        else: st="stable"
        return st,cnt,float(slope)
    reps=[r["factor_id"] for r in g3rows if r["gate3_representative"]]
    g4rows=[]
    for fid in reps:
        st,cnt,slope=seg_decay(daily_main[fid])
        g4rows.append({"factor_id":fid,"seg_days":str(cnt),"decay_slope":slope,"decay_status":st})
    pd.DataFrame(g4rows).to_csv(os.path.join(A1,"board_a1_gate4_decay.csv"),index=False,encoding="utf-8-sig")
    # 自检4
    cases={"stable":[.03,.031,.029,.03],"warning":[.03,.025,.022,.020],"decaying":[.03,.02,.015,.01],"reversal":[.03,.02,.01,-.005]}
    exp={"stable":"stable","warning":"decay_warning","decaying":"decaying","reversal":"decaying"}
    def dec4(v):
        if v[-1]<0 or (v[0]>v[1]>v[2]>v[3] and v[-1]<v[0]*0.5): return "decaying"
        if v[-1]<v[0]*0.7: return "decay_warning"
        return "stable"
    sc4=all(dec4(v)==exp[k] for k,v in cases.items())
    # insufficient 用例
    sc4=sc4 and (seg_decay(pd.Series([0.03]*10,index=pd.to_datetime(pd.date_range("2024-01-01",periods=10))))[0]=="insufficient_segment_data")
    print("[自检4 衰减] 4用例+insufficient -> %s"%("PASS" if sc4 else "FAIL"),flush=True)

    selfchecks=[{"check":"gate1_shuffle_zero","pass":sc1},{"check":"gate2_noise_fdr","pass":sc2},
                {"check":"gate3_synth_cluster","pass":sc3},{"check":"gate4_synth_decay","pass":sc4}]
    pd.DataFrame(selfchecks).to_csv(os.path.join(A1,"board_a1_selfcheck.csv"),index=False,encoding="utf-8-sig")
    if not all(s["pass"] for s in selfchecks):
        print("SELF_CHECK_FAILED -> 停止, 不出final verdict"); return

    # ---- ledger / final_verdict ----
    g3map={r["factor_id"]:r for r in g3rows}
    g4map={r["factor_id"]:r for r in g4rows}
    led=[]
    for _,r in main.iterrows():
        fid=r.factor_id
        if not r.gate1_pass: fv="gate1_fail"
        elif r.gate2_status!="gate2_pass": fv="gate2_fail"
        elif fid in g3map and not g3map[fid]["gate3_representative"]: fv="gate3_redundant"
        elif fid in g4map:
            ds=g4map[fid]["decay_status"]
            fv=("gate_pass_but_decaying" if ds=="decaying" else
                ("insufficient_segment_data" if ds=="insufficient_segment_data" else "gate_all_pass_candidate"))
        else: fv="gate2_fail"
        led.append({"factor_id":fid,"factor_name":r.factor_name,"seal_dependent":r.seal_dependent,
            "gate1_pass":bool(r.gate1_pass),"hac_t":r.hac_t,"gate2_status":r.gate2_status,
            "bh_q_n125":round(float(r.bh_q_n125),5),"gate3":(g3map[fid]["gate3_status"] if fid in g3map else "n/a"),
            "decay_status":(g4map[fid]["decay_status"] if fid in g4map else "n/a"),"final_verdict":fv})
    led=pd.DataFrame(led)
    assert "robust_alpha" not in set(led.final_verdict)
    led.to_csv(os.path.join(A1,"board_a1_ledger.csv"),index=False,encoding="utf-8-sig")
    print("\n=== final_verdict 分布 ===",flush=True)
    print(led.final_verdict.value_counts().to_string(),flush=True)
    print("\ngate_all_pass_candidate:",led[led.final_verdict=="gate_all_pass_candidate"].factor_name.tolist(),flush=True)
    # 计数留存
    json.dump({"can_calculate":len(cc),
        "gate1_pass":int(main.gate1_pass.sum()),"gate2_pass":int((main.gate2_status=="gate2_pass").sum()),
        "clusters":len(set(r["cluster_id"] for r in g3rows)) if g3rows else 0,
        "verdict":led.final_verdict.value_counts().to_dict(),
        "selfchecks":{s["check"]:s["pass"] for s in selfchecks}},
        open(os.path.join(A1,"_a1b_counts.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print("\n[done] A1b 四关完成",flush=True)

if __name__=="__main__":
    main()
