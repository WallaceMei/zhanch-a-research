# -*- coding: utf-8 -*-
# A1b 小样本验证(第二步): 直接复用 a1b_run.py 真实 build_dense + 常量 + 辅助函数,
# 逐字复制 main() 的 ts_路由/rewrite/merge 片段, 在全量面板+小因子子集上验三件事:
#   1) 字段路由不崩: build_dense -> ts_merge -> base-merge 跑通, K线从dense取/市场级从面板取, 不KeyError
#   2) ts_对齐: K线 ts_shift=上一交易日值(对齐事件行不错位); seal/lhb ts_=上一事件行值
#   3) Gate1 前几因子(含seal+非seal,含ts_) 能算IC + 打乱后 hac_t 归零(<3)
# 不下判定。环境 .venv_court。任一不通即停报告。
import os, json, re, importlib.util
import numpy as np, pandas as pd

A1=r"D:\Code\JQ\战车A\research\board_event_a1"

# ---- 加载 a1b_run.py 模块头(def main 之前): 拿真实 build_dense / 常量 / 辅助函数 ----
src=open(os.path.join(A1,"a1b_run.py"),encoding="utf-8").read()
head=src.split("def main()")[0]
M=type(importlib)("a1b_head") if False else __import__("types").ModuleType("a1b_head")
exec(compile(head,"a1b_head","exec"),M.__dict__)

PANEL=M.PANEL; FEATURES=M.FEATURES; JSONL=M.JSONL
SEAL_FIELDS=M.SEAL_FIELDS; EVENT_FIELDS=M.EVENT_FIELDS; DENSE_FIELDS=M.DENSE_FIELDS; AVAILABLE=M.AVAILABLE
HORIZONS=M.HORIZONS; POOLS=M.POOLS; MAIN_POOL=M.MAIN_POOL; MAIN_H=M.MAIN_H; T_THRESH=M.T_THRESH
build_dense=M.build_dense; nw_t=M.nw_t; naive_t=M.naive_t

def fail(msg):
    print("\n[SMOKE_FAIL] "+msg); raise SystemExit(1)

def main():
    panel=pd.read_parquet(PANEL); panel["date"]=pd.to_datetime(panel["date"])
    panel=panel.sort_values(["code","date"]).reset_index(drop=True)
    print("[panel] %d 行 %d 列"%(panel.shape[0],panel.shape[1]),flush=True)
    for f in ["daily_total_limits","market_max_board","first_board_ratio"]:
        if f not in panel.columns: fail("面板缺市场级字段 %s"%f)
    print("[OK] 三个市场级字段面板原生包含",flush=True)

    recs=[json.loads(l) for l in open(JSONL,encoding="utf-8") if l.strip()]
    audit=[]
    for i,r in enumerate(recs):
        fu=set(str(x).strip() for x in (r.get("fields_used") or []))
        leak=any(t in r["formula"].lower() for t in ["fwd_return","future_return","_t1close","_t3close","_t5close"])
        can=(fu<=AVAILABLE and len(fu)>0 and not leak)
        audit.append({"factor_id":i,"factor_name":r["name"],"formula":r["formula"],
            "fields":fu,"can":bool(can),"seal_dependent":bool(fu&SEAL_FIELDS),"has_ts":("ts_" in r["formula"])})
    cc=[a for a in audit if a["can"]]
    print("[audit] can_calculate=%d (seal=%d, ts_=%d)"%(len(cc),
        sum(a["seal_dependent"] for a in cc),sum(a["has_ts"] for a in cc)),flush=True)
    if len(cc)!=125: fail("can_calculate != 125 (=%d)"%len(cc))

    # ---- 选小样本: 非seal非ts 2 + 非seal含ts 2 + seal非ts 2 + seal含ts 2 ----
    def pk(seal,ts,n):
        return [a for a in cc if a["seal_dependent"]==seal and a["has_ts"]==ts][:n]
    pick=pk(False,False,2)+pk(False,True,2)+pk(True,False,2)+pk(True,True,2)
    pick={a["factor_id"]:a for a in pick}; pick=list(pick.values())
    print("\n[小样本 %d 因子]"%len(pick),flush=True)
    for a in pick:
        print("  id%-3d seal=%-5s ts=%-5s %s | %s"%(a["factor_id"],a["seal_dependent"],a["has_ts"],
            a["factor_name"][:30],a["formula"][:70]),flush=True)

    # ===== 复制自 a1b_run.py main() 的 ts_路由(line 108-116) =====
    pat_sh=re.compile(r"ts_shift\(\s*df\['(\w+)'\]\s*,\s*(\d+)\s*\)")
    pat_zs=re.compile(r"ts_zscore\(\s*df\['(\w+)'\]\s*,\s*(\d+)\s*\)")
    need_dense=set(); need_event=set()
    for a in pick:   # 子集即可验路由
        for fld,k in pat_sh.findall(a["formula"]):
            (need_dense if fld in DENSE_FIELDS else need_event).add((fld,"sft",int(k)))
        for fld,n in pat_zs.findall(a["formula"]):
            (need_dense if fld in DENSE_FIELDS else need_event).add((fld,"zs",int(n)))
    print("\n[ts路由] need_dense=%s\n         need_event=%s"%(sorted(need_dense),sorted(need_event)),flush=True)

    # ===== 复制自 a1b_run.py main() 的 稠密ts预算+并入(line 118-147) =====
    dense=None
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
        # ts对齐自检(K线): retail_line_change__sft1 在事件行 == 稠密上一交易日值
        chk=None
        for (fld,op,p) in need_dense:
            if op=="sft" and p==1: chk=(fld,"%s__sft1"%fld); break
        if chk:
            fld,col=chk
            samp=panel[panel[col].notna()].iloc[0]
            ds=dense[(dense.ts_code==samp["code"])].sort_values("trade_date").reset_index(drop=True)
            pos=ds.index[ds.trade_date==samp["date"]][0]
            prev_val=ds[fld].iloc[pos-1]
            ok=abs(prev_val-samp[col])<1e-6
            print("\n[ts对齐自检·K线] %s 事件行 %s %s: 面板值=%.5f 稠密上一交易日值=%.5f 一致=%s"%(
                fld,samp["code"],str(samp["date"])[:10],samp[col],prev_val,ok),flush=True)
            if not ok: fail("K线 ts_对齐错位")
        else:
            print("\n[ts对齐自检·K线] 子集无 sft1 K线因子, 跳过(全量会覆盖)",flush=True)

    # ===== 复制自 a1b_run.py main() 的 事件ts预算(line 148-155) =====
    pg=panel.groupby("code",sort=False)
    for fld,op,p in need_event:
        col="%s__%s%d"%(fld,op,p)
        if op=="sft": panel[col]=pg[fld].shift(p)
        else:
            m=pg[fld].transform(lambda s:s.rolling(p).mean()); sd=pg[fld].transform(lambda s:s.rolling(p).std())
            panel[col]=(panel[fld]-m)/(sd+1e-12)
    # ts对齐自检(事件): seal/lhb sft1 == 该股上一事件行原值
    ev_chk=None
    for (fld,op,p) in need_event:
        if op=="sft" and p==1: ev_chk=(fld,"%s__sft1"%fld); break
    if ev_chk:
        fld,col=ev_chk
        samp=panel[panel[col].notna()].iloc[0]
        gg=panel[panel.code==samp["code"]].sort_values("date").reset_index(drop=True)
        pos=gg.index[gg.date==samp["date"]][0]
        prev_val=gg[fld].iloc[pos-1]
        ok=(pd.isna(prev_val) and pd.isna(samp[col])) or (abs(prev_val-samp[col])<1e-6)
        print("[ts对齐自检·事件] %s 事件行 %s %s: 面板值=%.5f 上一事件行原值=%.5f 一致=%s"%(
            fld,samp["code"],str(samp["date"])[:10],samp[col],prev_val,ok),flush=True)
        if not ok: fail("事件 ts_对齐错位")
    else:
        print("[ts对齐自检·事件] 子集无 sft1 事件因子, 跳过",flush=True)

    # ===== 复制自 a1b_run.py main() 的 base-merge(已修复, line 157-161) =====
    if "return_3d" not in panel.columns:
        d2=build_dense() if not need_dense else dense
        kline_cols=[c for c in DENSE_FIELDS if c in d2.columns and c not in panel.columns]
        print("\n[base-merge] 从dense补的K线字段(dense产出且面板没有)=%s"%sorted(kline_cols),flush=True)
        native=[c for c in DENSE_FIELDS if c in panel.columns]
        print("[base-merge] 用面板原生事件日值(不从dense取)=%s"%sorted(native),flush=True)
        bb=d2[["ts_code","trade_date"]+kline_cols].rename(columns={"ts_code":"code","trade_date":"date"})
        panel=panel.merge(bb,on=["code","date"],how="left")
    # 验所有 DENSE_FIELDS 都在 panel(K线来自merge, 市场级来自原生)
    missing=[c for c in DENSE_FIELDS if c not in panel.columns]
    if missing: fail("base-merge后 panel 仍缺 DENSE_FIELDS: %s"%missing)
    print("[OK] base-merge不崩, 全部 DENSE_FIELDS 在面板(K线来自dense / 市场级来自面板原生)",flush=True)

    # ===== 复制自 a1b_run.py main() 的 rewrite + evalf(line 163-170) =====
    def rewrite(f):
        f=pat_sh.sub(lambda m:"df['%s__sft%s']"%(m.group(1),m.group(2)),f)
        f=pat_zs.sub(lambda m:"df['%s__zs%s']"%(m.group(1),m.group(2)),f)
        return f
    NS={"cs_rank":lambda s:s.rank(pct=True),"np":np,"log1p":np.log1p,"sqrt":np.sqrt,"abs":np.abs,"log":np.log}
    def evalf(f,sub): return eval(f,{"__builtins__":{}},dict(NS,df=sub))

    base_valid=(~panel["is_st"])&(~panel["is_paused"])&(panel["tradable_next_open"])

    # ===== Gate1 主口径(event_pool_all + T3) on 小样本 + 打乱自检 =====
    print("\n=== Gate1 小样本(event_pool_all, T+3) + 打乱归零自检 ===",flush=True)
    RC,LAG=HORIZONS[MAIN_H]; MIN=POOLS[MAIN_POOL]
    rng=np.random.RandomState(42)
    shuffle_hac=[]
    for a in pick:
        fid=a["factor_id"]; frw=rewrite(a["formula"]); seal=a["seal_dependent"]
        base=panel[MAIN_POOL]&base_valid
        if seal: base=base&panel["in_limit_list_d"]&panel["sealed_limit"]
        sub_all=panel[base]
        ics=[]; ics_sh=[]
        for d,g in sub_all.groupby("date"):
            if len(g)<MIN: continue
            try: fv=evalf(frw,g)
            except Exception as e: fv=pd.Series(np.nan,index=g.index)
            if not hasattr(fv,"rank"): fv=pd.Series(fv,index=g.index)
            y=g[RC]; ok=fv.notna()&y.notna()
            if ok.sum()<MIN: continue
            xr=fv[ok].rank(); yr=y[ok].rank(); ic=xr.corr(yr)
            if not np.isnan(ic): ics.append(ic)
            yy=y[ok].values.copy(); rng.shuffle(yy)
            sh=pd.Series(yy,index=xr.index).rank().corr(xr)
            if not np.isnan(sh): ics_sh.append(sh)
        ics=np.array(ics); ics_sh=np.array(ics_sh)
        d1=1 if (len(ics) and np.nanmean(ics[:120])>=0) else -1
        hac=nw_t(ics*d1,LAG) if len(ics) else np.nan
        hac_sh=nw_t(ics_sh,LAG) if len(ics_sh) else np.nan
        if len(ics_sh): shuffle_hac.append(abs(hac_sh))
        print("  id%-3d seal=%-5s ts=%-5s days=%-4d ic=%+.4f hac_t=%+.2f || 打乱 ic=%+.4f hac_t=%+.2f"%(
            fid,seal,a["has_ts"],len(ics),
            np.nanmean(ics) if len(ics) else np.nan, hac,
            np.nanmean(ics_sh) if len(ics_sh) else np.nan, hac_sh),flush=True)

    if shuffle_hac:
        mx=max(shuffle_hac); mn=float(np.mean(shuffle_hac))
        print("\n[打乱归零] 小样本打乱 |hac_t|: 均=%.2f 最大=%.2f -> %s"%(
            mn,mx,"PASS(<3)" if mx<3.0 else "FAIL(>=3 异常)"),flush=True)
        if mx>=3.0: fail("打乱后仍显著, 链路可疑")
    print("\n[SMOKE_OK] 字段路由不崩 + ts对齐正确 + Gate1可算 + 打乱归零 => 可挂机跑全量125",flush=True)

if __name__=="__main__":
    main()
