# -*- coding: utf-8 -*-
# 批量拉 Tushare limit_list_d(涨停板每日明细)2024-2025 逐日,存 raw parquet。
# 口径已钉: seal_strength=fd_amount/float_mv(元/元,中位~0.0156,<0.007=弱封板),派生留回填步。
# 全程不打印 token,报错擦 token。环境 .venv_court。
import os, time
import pandas as pd

OUT=r"D:\Code\JQ\战车A\research\board_event_a1\_limit_list_d_2024_2025.parquet"
vals={}
for line in open(r"D:\quant_env\.env",encoding="utf-8"):
    line=line.strip()
    if "=" in line and not line.startswith("#"):
        k,_,v=line.partition("="); vals[k.strip()]=v.strip()
TOKEN=vals["TUSHARE_TOKEN"]; URL=vals["TUSHARE_HTTP_URL"]
def scrub(s): return str(s).replace(TOKEN,"***")
for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"): os.environ.pop(k,None)
import tushare as ts
ts.set_token(TOKEN); pro=ts.pro_api(); pro._DataApi__http_url=URL

cal=pro.trade_cal(exchange="SSE",start_date="20240101",end_date="20251231",is_open="1")
days=sorted(cal["cal_date"].tolist())
print("交易日数=%d (%s..%s)"%(len(days),days[0],days[-1]),flush=True)

frames=[]; fail=[]; n=0
for d in days:
    ok=False
    for attempt in range(3):
        try:
            df=pro.limit_list_d(trade_date=d, limit_type="U")
            if df is not None:
                frames.append(df); ok=True; break
        except Exception as e:
            if attempt==2: fail.append((d,scrub(repr(e))[:60]))
            time.sleep(0.6)
    n+=1
    if n%60==0: print("  进度 %d/%d"%(n,len(days)),flush=True)
    time.sleep(0.05)  # 控速

alld=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
alld.to_parquet(OUT,index=False)
print("\n[done] 总行=%d 覆盖日=%d 失败日=%d"%(len(alld), alld["trade_date"].nunique() if len(alld) else 0, len(fail)))
if fail: print("失败日(前10):", fail[:10])
# 全量口径自检
if len(alld):
    alld["seal_strength"]=pd.to_numeric(alld["fd_amount"],errors="coerce")/pd.to_numeric(alld["float_mv"],errors="coerce")
    s=alld["seal_strength"].dropna()
    print("全量 seal_strength: n=%d 中位=%.5f 10%%=%.5f 90%%=%.5f <0.007占比=%.0f%%"%(
        len(s),s.median(),s.quantile(.1),s.quantile(.9),100*(s<0.007).mean()))
    print("列:", list(alld.columns))
    print("fd_amount 非空率=%.2f float_mv 非空率=%.2f first_time 非空率=%.2f open_times 非空率=%.2f"%(
        alld.fd_amount.notna().mean(), alld.float_mv.notna().mean(),
        alld.first_time.notna().mean(), alld.open_times.notna().mean()))
