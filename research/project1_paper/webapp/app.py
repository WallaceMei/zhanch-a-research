# -*- coding: utf-8 -*-
"""Project1 Paper — 只读对照看板(spec §6;FastAPI+Jinja2,复用 quant_platform 同栈)。

⚠️ 护栏3:纯展示只读 —— 只有 GET 端点;不 import xttrader / xtdata;
   不含任何下单/交易/写状态接口。数据全部来自 paper_state / out 的落盘文件。
⚠️ 护栏1:横幅常驻"实时链路未经实盘验证"直到周一实测通过。

启动: py -3.10 -m uvicorn app:app --host 127.0.0.1 --port 8765
     (cwd = research/project1_paper/webapp)
数据源切换:?src=step1(历史对照占位)/ drill(mock演习)/ real(真实paper,周一后)
"""
import os
import sys
import json
import glob

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

_HERE = os.path.dirname(os.path.abspath(__file__))
_PAPER = os.path.normpath(os.path.join(_HERE, '..'))
for p in (_PAPER,):
    if p not in sys.path:
        sys.path.insert(0, p)
import paper_config as C     # noqa: E402

app = FastAPI(title="Project1 Paper 三组对照看板(只读)", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=os.path.join(_HERE, "templates"))

SRC_LABEL = dict(
    step1="Step1 历史对照占位(IS2023,占位AI=score top3,无价值含义;实时数据待周一起)",
    drill="mock 演习数据(管线验证,AI=机械规则占位,无价值含义)",
    real="真实 paper(forward,周一实测通过后启用)")


def _stats_from_trades(td, eq_first_last):
    out = {}
    for g, gdf in td.groupby('group'):
        rets = pd.to_numeric(gdf['net_return'], errors='coerce').dropna()
        wins = rets[rets > 0]; losses = rets[rets <= 0]
        pf = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else None
        pk = pd.to_numeric(gdf['peak_return'], errors='coerce')
        cap = (rets.clip(lower=0) / pk).where(pk > 0).dropna()
        out[g] = dict(n_trades=int(len(gdf)),
                      win_rate=round(float(len(wins)) / len(rets), 4) if len(rets) else None,
                      profit_factor=round(pf, 3) if pf else None,
                      bigmeat_capture=round(float(cap.mean()), 3) if len(cap) else None)
    for g, (e0, e1, mdd) in eq_first_last.items():
        out.setdefault(g, {})
        out[g].update(total_return=round(e1 / e0 - 1.0, 4), max_drawdown=round(mdd, 4))
    return out


def _equity_payload(eqw):
    """eqw: wide df(index d8 str, columns=groups)。"""
    eqw = eqw.sort_index()
    groups = [c for c in eqw.columns]
    ai_col = next((c for c in groups if c.startswith('ai_')), None)
    rel = {}
    if ai_col:
        for base in ('all_in', 'random3'):
            if base in eqw.columns:
                rel['AI减%s' % ('全进' if base == 'all_in' else '随机')] = \
                    (eqw[ai_col] - eqw[base]).round(4).tolist()
    fl = {g: (float(eqw[g].iloc[0]), float(eqw[g].iloc[-1]),
              float((eqw[g] / eqw[g].cummax() - 1.0).min())) for g in groups}
    return dict(dates=list(eqw.index), series={g: eqw[g].round(4).tolist() for g in groups},
                rel=rel), fl


def _load_step1():
    pre = os.path.join(C.OUT_DIR, "paper_step1_IS2023")
    eq = pd.read_csv(pre + "_equity.csv", dtype={'d8': str}).set_index('d8')
    eqw = eq[[c for c in eq.columns if not c.startswith('rel_')]]
    payload, fl = _equity_payload(eqw)
    tds = []
    for g in eqw.columns:
        t = pd.read_csv(pre + "_%s_trades.csv" % g)
        tds.append(t)
    td = pd.concat(tds, ignore_index=True) if tds else pd.DataFrame()
    dec = pd.read_csv(pre + "_daily_decisions.csv", dtype={'date': str})
    dec = dec.rename(columns={'date': 'd8'})
    return payload, _stats_from_trades(td, fl), \
        dec.tail(120).fillna('').to_dict('records'), \
        td.tail(60).fillna('').to_dict('records'), []


def _load_state(kind):
    d = C.STATE_DIR if kind == 'real' else C.DRILL_STATE_DIR
    eqp = os.path.join(d, "equity.csv")
    if not os.path.exists(eqp):
        return None, {}, [], [], []
    eq = pd.read_csv(eqp, dtype={'d8': str})
    eqw = eq.pivot_table(index='d8', columns='group', values='equity', aggfunc='last')
    payload, fl = _equity_payload(eqw)
    tp = os.path.join(d, "trades.csv")
    td = pd.read_csv(tp) if os.path.exists(tp) else pd.DataFrame(
        columns=['group', 'net_return', 'peak_return'])
    dp = os.path.join(d, "decisions.csv")
    dec = pd.read_csv(dp, dtype={'d8': str}) if os.path.exists(dp) else pd.DataFrame()
    ai_logs = []
    for mp in sorted(glob.glob(os.path.join(d, "ai_log", "*_meta.json")), reverse=True)[:30]:
        try:
            with open(mp, "r", encoding="utf-8") as f:
                m = json.load(f)
            m['d8'] = os.path.basename(mp).split('_')[0]
            ai_logs.append(m)
        except Exception:
            pass
    return payload, _stats_from_trades(td, fl), \
        (dec.tail(120).fillna('').to_dict('records') if len(dec) else []), \
        (td.tail(60).fillna('').to_dict('records') if len(td) else []), ai_logs


@app.get("/")
def index(request: Request, src: str = "step1"):
    return templates.TemplateResponse(
        request, "dashboard.html", dict(src=src, src_label=SRC_LABEL.get(src, src)))


@app.get("/api/data")
def api_data(src: str = "step1"):
    if src == "step1":
        payload, stats, dec, td, ai_logs = _load_step1()
    elif src in ("drill", "real"):
        payload, stats, dec, td, ai_logs = _load_state(src)
        if payload is None:
            return JSONResponse(dict(empty=True, msg="该数据源暂无数据(%s)" % SRC_LABEL[src]))
    else:
        return JSONResponse(dict(error="unknown src"), status_code=400)
    return JSONResponse(dict(equity=payload, stats=stats, decisions=dec,
                             trades=td, ai_logs=ai_logs, src=src,
                             src_label=SRC_LABEL.get(src, src)))


@app.get("/api/ai_raw/{kind}/{d8}", response_class=PlainTextResponse)
def api_ai_raw(kind: str, d8: str):
    """AI 留痕原文(prompt+raw response),只读。"""
    if kind not in ("real", "drill") or not d8.isdigit():
        return PlainTextResponse("bad request", status_code=400)
    d = C.STATE_DIR if kind == 'real' else C.DRILL_STATE_DIR
    parts = []
    for suf in ("prompt.txt", "raw_response.txt", "meta.json"):
        p = os.path.join(d, "ai_log", "%s_%s" % (d8, suf))
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                parts.append("===== %s =====\n%s" % (suf, f.read()))
    return "\n\n".join(parts) or "无留痕"
