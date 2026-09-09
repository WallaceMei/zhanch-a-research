# -*- coding: utf-8 -*-
# A1a 组装: panel_full + 字段覆盖率 + 194因子字段预审 + tick验真留档。
# 字段补不出如实标 unavailable(spec §5.1),不硬造/不填0伪造/不forward fill。
import os, json
import numpy as np, pandas as pd

A1=r"D:\Code\JQ\战车A\research\board_event_a1"
CLASS1=os.path.join(A1,"board_event_panel_class1.parquet")
LHB=os.path.join(A1,"_lhb_2024_2025.csv")
JSONL=r"C:\quant_project\limit_up\qlib_results\rdagent_factors_v4.jsonl"

# 字段可用性(A1a 现状)
AVAILABLE_OK=["return_3d","rsi_14","bb_position","up_streak","vol_ratio_5d","price_position_60d",
  "retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
  "daily_total_limits","market_max_board","first_board_ratio","lhb_net","on_lhb"]
UNAVAILABLE={
  "seal_strength":"tick无2024-2025/qlib仅5%/zt_pool失效",
  "seal_ratio":"同seal_strength(需封单)",
  "seal_minutes":"需分钟/tick盘中(未补,留)",
  "open_times":"需分钟/tick盘中(未补,留)",
  "limit_turnover":"日线可算但未补(需流通股本)",
  "float_mv_yi":"需流通股本(xtdata快照,未补)",
  "inst_net":"龙虎榜机构明细需逐股,deferred",
  "industry_limit_count":"需行业表,未补",
  "morning_vol_ratio":"需分钟,与tick一起做(未补)",
  "tail_vol_ratio":"需分钟,与tick一起做(未补)"}

def main():
    panel=pd.read_parquet(CLASS1); panel["date"]=pd.to_datetime(panel["date"])
    lhb=pd.read_csv(LHB); lhb["date"]=pd.to_datetime(lhb["date"])
    # 并入 lhb: on_lhb=0/lhb_net=0 为真值(该股当日未上榜),非伪造
    panel=panel.merge(lhb[["code","date","lhb_net","on_lhb"]],on=["code","date"],how="left")
    panel["on_lhb"]=panel["on_lhb"].fillna(0).astype(int)
    panel["lhb_net"]=panel["lhb_net"].fillna(0.0)  # 未上榜=龙虎榜净买0(真值)
    # 不可用字段: NaN(已在class1有industry/morning/tail; 补其余)
    for c in UNAVAILABLE:
        if c not in panel.columns: panel[c]=np.nan
    panel.to_parquet(os.path.join(A1,"board_event_panel_full.parquet"),index=False)
    print("[panel_full] 行=%d 列=%d"%(len(panel),panel.shape[1]))

    # ---- 覆盖率(全部补的字段)----
    NEW=AVAILABLE_OK[6:]+list(UNAVAILABLE)  # class1+lhb+unavailable(去重A0已有的kline6)
    NEW=["retail_line","retail_line_change","vol_vs_prev","intraday_range","kdj_j",
         "daily_total_limits","market_max_board","first_board_ratio","lhb_net","on_lhb"]+list(UNAVAILABLE)
    rows=[]
    for c in dict.fromkeys(NEW):
        nn=int(panel[c].notna().sum()) if c in panel else 0
        cr=nn/len(panel) if len(panel) else 0
        if c in UNAVAILABLE and c not in ("lhb_net","on_lhb"):
            qs="unavailable" if nn==0 else "low_coverage"; src=UNAVAILABLE.get(c,"")
        else:
            qs="ok" if cr>=0.95 else ("partial" if cr>=0.5 else ("low_coverage" if nn>0 else "unavailable"))
            src={"lhb_net":"AKShare龙虎榜","on_lhb":"AKShare龙虎榜"}.get(c,"features日线/全市场")
        rows.append({"field":c,"non_null_count":nn,"coverage_ratio":round(cr,4),
            "coverage_start":str(panel.loc[panel[c].notna(),"date"].min())[:10] if nn else "",
            "coverage_end":str(panel.loc[panel[c].notna(),"date"].max())[:10] if nn else "",
            "data_source":src,"quality_status":qs})
    cov=pd.DataFrame(rows); cov.to_csv(os.path.join(A1,"board_field_coverage.csv"),index=False,encoding="utf-8-sig")

    # ---- 194 因子字段预审 ----
    recs=[]
    with open(JSONL,encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line: recs.append(json.loads(line))
    avail=set(AVAILABLE_OK)
    LEAK=["fwd_return","future_return","_t1close","_t3close","_t5close"]
    pre=[]
    for i,r in enumerate(recs):
        fu=[str(x).strip() for x in (r.get("fields_used") or [])]
        miss=[x for x in fu if x not in avail]
        leak=[x for x in fu if any(t in x.lower() for t in LEAK)]
        can=(len(miss)==0 and len(leak)==0)
        status=("leakage_suspected" if leak else ("can_calculate" if can else "field_unavailable"))
        pre.append({"factor_id":i,"factor_name":r["name"],
            "required_fields":"|".join(fu),"available_fields":"|".join(x for x in fu if x in avail),
            "missing_fields":"|".join(miss),"can_calculate":can,"field_status":status,
            "depends_industry_limit_count":("industry_limit_count" in fu),
            "depends_seal_strength":("seal_strength" in fu)})
    pre=pd.DataFrame(pre); pre.to_csv(os.path.join(A1,"board_factor_field_audit_precheck.csv"),index=False,encoding="utf-8-sig")

    can=int(pre.can_calculate.sum())
    fu_cnt=int((pre.field_status=="field_unavailable").sum())
    leak_cnt=int((pre.field_status=="leakage_suspected").sum())
    ind_cnt=int(pre.depends_industry_limit_count.sum())
    seal_cnt=int(pre.depends_seal_strength.sum())
    # 缺字段频次(missing 里哪些字段挡得最多)
    from collections import Counter
    blk=Counter()
    for m in pre.missing_fields:
        for x in m.split("|"):
            if x: blk[x]+=1
    print("\n=== 194 因子预审 ===")
    print("can_calculate=%d | field_unavailable=%d | leakage_suspected=%d"%(can,fu_cnt,leak_cnt))
    print("依赖 industry_limit_count 的因子=%d | 依赖 seal_strength 的=%d"%(ind_cnt,seal_cnt))
    print("\n挡因子最多的缺失字段 Top10:")
    for k,v in blk.most_common(10): print("  %-22s 挡 %d 个"%(k,v))
    print("\n=== 覆盖率表 ===")
    print(cov.to_string(index=False))
    # 存计数供报告
    json.dump({"can_calculate":can,"field_unavailable":fu_cnt,"leakage_suspected":leak_cnt,
        "depends_industry":ind_cnt,"depends_seal_strength":seal_cnt,
        "blockers":dict(blk.most_common(12))},
        open(os.path.join(A1,"_precheck_counts.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

if __name__=="__main__":
    main()
