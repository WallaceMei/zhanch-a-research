# -*- coding: utf-8 -*-
# A1a 类2: AKShare 龙虎榜 lhb_net / on_lhb 批量(2024-2025,按月)。
# 用 quant_platform/.venv(已装 akshare,只读网络)。inst_net 本步 deferred(需逐股机构明细)。
# 红线: 只取"龙虎榜净买额",绝不用 detail 表里的"上榜后1/2/5/10日"(未来收益,泄漏)。
# 龙虎榜=T日收盘后信息,仅用于 T+1 open 之后收益验证。
import akshare as ak
import pandas as pd
import os

OUT = r"D:\Code\JQ\战车A\research\board_event_a1\_lhb_2024_2025.csv"
months=[]
for y in (2024,2025):
    for m in range(1,13):
        s="%d%02d01"%(y,m)
        e="%d%02d31"%(y,m)
        months.append((s,e))

rows=[]; fail=[]
for s,e in months:
    try:
        df=ak.stock_lhb_detail_em(start_date=s,end_date=e)
        if df is not None and len(df):
            # 列名按小样本验证: 代码/上榜日/龙虎榜净买额
            d=df.rename(columns={"代码":"code_raw","上榜日":"lhb_date","龙虎榜净买额":"lhb_net"})
            d=d[["code_raw","lhb_date","lhb_net"]].copy()
            rows.append(d)
        print("[%s-%s] rows=%d"%(s,e,0 if df is None else len(df)),flush=True)
    except Exception as ex:
        fail.append((s,repr(ex)[:80])); print("[%s] ERR %s"%(s,repr(ex)[:80]),flush=True)

all_=pd.concat(rows,ignore_index=True) if rows else pd.DataFrame(columns=["code_raw","lhb_date","lhb_net"])
# 规范代码: 6位 -> ts_code 600000.SH / 000001.SZ (与 features 对齐)
def to_ts(c):
    c=str(c).zfill(6)
    if c[0]=="6": return c+".SH"
    if c[0] in ("0","3"): return c+".SZ"
    if c[0] in ("8","4"): return c+".BJ"
    return c+".SZ"
all_["code"]=all_["code_raw"].map(to_ts)
all_["date"]=pd.to_datetime(all_["lhb_date"])
all_["lhb_net"]=pd.to_numeric(all_["lhb_net"],errors="coerce")
# 同一股同日多条(多上榜原因)聚合: 净买额求和, on_lhb=1
agg=all_.groupby(["code","date"],as_index=False)["lhb_net"].sum()
agg["on_lhb"]=1
agg.to_csv(OUT,index=False,encoding="utf-8-sig")
print("\n[done] 总上榜(股,日)记录=%d, 覆盖日期 %s..%s, 失败月=%d" % (
    len(agg), str(agg.date.min())[:10], str(agg.date.max())[:10], len(fail)))
print("lhb_net 样例:", agg.head(3).to_dict("records"))
