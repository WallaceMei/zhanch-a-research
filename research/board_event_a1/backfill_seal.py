# -*- coding: utf-8 -*-
# A1a 回填: 从 limit_list_d 派生 seal 类字段并入事件面板,重做 194 预审。
# 口径钉死: seal_strength=fd_amount/float_mv; seal_ratio=fd_amount/amount;
#   seal_minutes=first_time->15:00 封板持续分钟; open_times 直接; float_mv_yi=float_mv/1e8;
#   limit_turnover=turnover_ratio; industry_limit_count=按industry当日涨停家数。
# ★ seal 类只在 limit_list_d(封住涨停)行有值; failed/near 行 NaN(真实"没封板没封单",不填0/不ffill)。
#   标记 in_limit_list_d 区分。提醒A1b: seal类IC样本限sealed子集。
import os, json
import numpy as np, pandas as pd
from collections import Counter

A1=r"D:\Code\JQ\战车A\research\board_event_a1"
PANEL=os.path.join(A1,"board_event_panel_full.parquet")
LLD=os.path.join(A1,"_limit_list_d_2024_2025.parquet")
JSONL=r"C:\quant_project\limit_up\qlib_results\rdagent_factors_v4.jsonl"

def seal_minutes_from(ft):
    # ft: HHMMSS 字符串/数字; 返回 first_time->15:00 的封板持续(交易分钟,0..240)
    try:
        s=str(int(float(ft))).zfill(6); hh=int(s[:2]); mm=int(s[2:4])
    except: return np.nan
    t=hh*60+mm
    op,ls,le,cl=570,690,780,900   # 9:30 / 11:30 / 13:00 / 15:00
    if t<=op: el=0
    elif t<=ls: el=t-op
    elif t<le: el=120
    else: el=min(240,120+(t-le))
    return float(240-el)

def main():
    panel=pd.read_parquet(PANEL); panel["date"]=pd.to_datetime(panel["date"])
    lld=pd.read_parquet(LLD); lld["date"]=pd.to_datetime(lld["trade_date"])
    lld=lld.rename(columns={"ts_code":"code"})
    # 派生
    fd=pd.to_numeric(lld["fd_amount"],errors="coerce"); fm=pd.to_numeric(lld["float_mv"],errors="coerce")
    am=pd.to_numeric(lld["amount"],errors="coerce")
    lld["seal_strength"]=fd/fm
    lld["seal_ratio"]=fd/am
    lld["seal_minutes"]=lld["first_time"].map(seal_minutes_from)
    lld["open_times_d"]=pd.to_numeric(lld["open_times"],errors="coerce")
    lld["float_mv_yi"]=fm/1e8
    lld["limit_turnover"]=pd.to_numeric(lld["turnover_ratio"],errors="coerce")
    # industry_limit_count: 按(date,industry)当日涨停家数
    ic=lld.groupby(["date","industry"]).size().rename("industry_limit_count").reset_index()
    lld=lld.merge(ic,on=["date","industry"],how="left")
    lld["in_limit_list_d"]=True
    keep=["code","date","seal_strength","seal_ratio","seal_minutes","open_times_d",
          "float_mv_yi","limit_turnover","industry_limit_count","in_limit_list_d"]
    der=lld[keep].rename(columns={"open_times_d":"open_times"})
    der=der.drop_duplicates(["code","date"])

    # 并入面板(覆盖之前的 NaN 占位列)
    DROP=["seal_strength","seal_ratio","seal_minutes","open_times","float_mv_yi",
          "limit_turnover","industry_limit_count"]
    panel=panel.drop(columns=[c for c in DROP if c in panel.columns])
    panel=panel.merge(der,on=["code","date"],how="left")
    panel["in_limit_list_d"]=panel["in_limit_list_d"].fillna(False)
    panel.to_parquet(PANEL,index=False)

    # 覆盖率(全池 + sealed子集)
    sealed=panel[panel["sealed_limit"]]
    inlld=panel[panel["in_limit_list_d"]]
    print("[panel] 行=%d | sealed_limit=%d | in_limit_list_d=%d"%(len(panel),len(sealed),len(inlld)))
    NEW=["seal_strength","seal_ratio","seal_minutes","open_times","float_mv_yi","limit_turnover","industry_limit_count"]
    covrows=[]
    for c in NEW:
        nn=int(panel[c].notna().sum()); nn_sealed=int(sealed[c].notna().sum())
        covrows.append({"field":c,"non_null_count":nn,"coverage_ratio_fullpool":round(nn/len(panel),4),
            "coverage_ratio_sealed":round(nn_sealed/max(len(sealed),1),4),
            "data_source":"Tushare limit_list_d派生","quality_status":"ok_sealed_subset",
            "note":"仅封住涨停行有值;failed/near=NaN(真实无封单)"})
    print("\n=== seal类字段覆盖 ===")
    for r in covrows: print("  %-22s 全池%.0f%% sealed子集%.0f%%"%(r["field"],100*r["coverage_ratio_fullpool"],100*r["coverage_ratio_sealed"]))
    # seal_strength 量级复核
    ss=panel["seal_strength"].dropna()
    print("\nseal_strength(面板内): n=%d 中位=%.5f <0.007占比=%.0f%%"%(len(ss),ss.median(),100*(ss<0.007).mean()))
    sm=panel["seal_minutes"].dropna()
    print("seal_minutes: 中位=%.0f分 min=%.0f max=%.0f (240=一字/早封)"%(sm.median(),sm.min(),sm.max()))

    # 合并进 board_field_coverage.csv(追加 seal 类)
    base_cov=pd.read_csv(os.path.join(A1,"board_field_coverage.csv"))
    base_cov=base_cov[~base_cov["field"].isin(NEW)]  # 去掉旧的 unavailable 行
    newcov=pd.DataFrame([{"field":r["field"],"non_null_count":r["non_null_count"],
        "coverage_ratio":r["coverage_ratio_fullpool"],"coverage_start":"2024-01-02","coverage_end":"2025-12-31",
        "data_source":r["data_source"],"quality_status":r["quality_status"]} for r in covrows])
    pd.concat([base_cov,newcov],ignore_index=True).to_csv(os.path.join(A1,"board_field_coverage.csv"),index=False,encoding="utf-8-sig")

    # ---- 重做 194 预审 ----
    AVAILABLE=set(["return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d",
      "retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
      "daily_total_limits","market_max_board","first_board_ratio","lhb_net","on_lhb",
      "seal_strength","seal_ratio","seal_minutes","open_times","float_mv_yi","limit_turnover","industry_limit_count"])
    UNAVAIL_REASON={"morning_vol_ratio":"需分钟(未补)","tail_vol_ratio":"需分钟(未补)","inst_net":"需龙虎榜机构明细(deferred)"}
    recs=[]
    for line in open(JSONL,encoding="utf-8"):
        line=line.strip()
        if line: recs.append(json.loads(line))
    LEAK=["fwd_return","future_return","_t1close","_t3close","_t5close"]
    pre=[]; blk=Counter()
    for i,r in enumerate(recs):
        fu=[str(x).strip() for x in (r.get("fields_used") or [])]
        miss=[x for x in fu if x not in AVAILABLE]
        leak=[x for x in fu if any(t in x.lower() for t in LEAK)]
        can=(len(miss)==0 and len(leak)==0)
        for x in miss: blk[x]+=1
        status=("leakage_suspected" if leak else ("can_calculate" if can else "field_unavailable"))
        uses_seal=any(x.startswith("seal") for x in fu)
        pre.append({"factor_id":i,"factor_name":r["name"],"required_fields":"|".join(fu),
            "available_fields":"|".join(x for x in fu if x in AVAILABLE),"missing_fields":"|".join(miss),
            "can_calculate":can,"field_status":status,
            "uses_seal_fields(IC需限sealed子集)":uses_seal})
    pre=pd.DataFrame(pre); pre.to_csv(os.path.join(A1,"board_factor_field_audit_precheck.csv"),index=False,encoding="utf-8-sig")
    can=int(pre.can_calculate.sum()); fu_n=int((pre.field_status=="field_unavailable").sum())
    leak_n=int((pre.field_status=="leakage_suspected").sum()); seal_n=int(pre["uses_seal_fields(IC需限sealed子集)"].sum())
    print("\n=== 194 预审(回填后)===")
    print("can_calculate=%d | field_unavailable=%d | leakage_suspected=%d"%(can,fu_n,leak_n))
    print("用到seal类字段(IC需限sealed子集)的因子=%d"%seal_n)
    print("剩余拦路字段:")
    for k,v in blk.most_common(): print("  %-20s 挡 %d 个 (%s)"%(k,v,UNAVAIL_REASON.get(k,"?")))
    json.dump({"can_calculate":can,"field_unavailable":fu_n,"leakage_suspected":leak_n,
        "uses_seal":seal_n,"blockers":dict(blk.most_common())},
        open(os.path.join(A1,"_precheck_counts.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

if __name__=="__main__":
    main()
