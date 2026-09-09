# -*- coding: utf-8 -*-
"""Project1 Paper Step2 — 回放等价验证:实时监测器 vs 批量版 find_signal 对拍。

方法:对验证期内每天的 dragon top12,取其当日全部 1m bar,**按到达顺序逐根喂给
GateMonitor(实时器)**,与 engine_phaseA.find_signal(批量版,Phase A 已验证)对拍:
  - 信号有无一致?信号 bar 序号/时刻一致?
  - 顺带统计 capture_price(信号bar close,实时口径) vs 下一根open(Phase A 回测买价基),
    差值分布供成本模型校准(不是谁对谁错,是两种"抓那一刻"口径的真实间隙)。

对拍全过 = 实时器"满足条件那一刻"的判定逻辑与已验证批量版完全一致,
剩下的实时风险只在数据feed层(bar到达完整性/时序),周一 live 小样本单独验。

用法: py -3.10 run_step2_replay_check.py --start 20230301 --end 20230331
只读 minute/cache,只写本目录 out/。
"""
import os
import sys
import time
import argparse

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import pool_repro as PR             # noqa: E402
import engine_phaseA as E           # noqa: E402
from rt_monitor import GateMonitor, GATE_DEFAULTS  # noqa: E402

OUT_DIR = os.path.join(_HERE, "out")


def check_one(code, d8, cfg):
    """单 (code,day) 对拍。返回 dict 或 None(无分钟数据)。"""
    day = E.minute_day(code, d8)
    if day is None:
        return None
    # 批量版(Phase A 已验证口径)
    sig_batch = E.find_signal(day, cfg)
    # 实时器:逐根喂
    mon = GateMonitor(code)
    sig_rt = None
    rows = day[['hm', 'open', 'high', 'low', 'close', 'volume', 'amount']].values
    for r in rows:
        s = mon.push_bar(r[0], r[1], r[2], r[3], r[4], r[5], r[6])
        if s is not None and sig_rt is None:
            sig_rt = s
            # 不break:验证命中后继续推bar不改变结果(实时器一次性固化)
    rt_i = sig_rt['bar_i'] if sig_rt else None
    match = (rt_i == sig_batch)
    rec = dict(code=code, d8=d8, batch_i=sig_batch, rt_i=rt_i,
               batch_hm=day['hm'].iloc[sig_batch] if sig_batch is not None else None,
               rt_hm=sig_rt['signal_hm'] if sig_rt else None,
               match=int(match), capture_price=None, next_open=None, gap_bp=None)
    if match and sig_batch is not None and sig_batch + 1 < len(day):
        cap = float(sig_rt['capture_price'])
        nxt = float(day['open'].iloc[sig_batch + 1])
        rec.update(capture_price=cap, next_open=nxt,
                   gap_bp=round((nxt / cap - 1.0) * 1e4, 2))
    return rec


def run(start, end):
    cfg = dict(E.DEFAULT_CFG)
    assert cfg['obs_start'] == GATE_DEFAULTS['obs_start']
    assert cfg['obs_end'] == GATE_DEFAULTS['obs_end']
    assert cfg['vwap_break_tol'] == GATE_DEFAULTS['vwap_break_tol']
    assert cfg['vwap_pullback_window'] == GATE_DEFAULTS['vwap_pullback_window']

    PR._load()
    days = [d for d in PR.trade_days() if start <= d <= end]
    print("[replay-check] days=%d (%s..%s)" % (len(days), days[0], days[-1]), flush=True)
    recs = []
    t0 = time.time()
    for k, d in enumerate(days):
        pool = PR.dragon_pool(d, PR.prev_trading_day(d))
        for p in pool:
            r = check_one(p['stock'], d, cfg)
            if r is not None:
                recs.append(r)
        if (k + 1) % 10 == 0:
            n = len(recs); ok = sum(x['match'] for x in recs)
            print("  %d/%d days  pairs=%d match=%d  %.0fs" % (
                k + 1, len(days), n, ok, time.time() - t0), flush=True)

    df = pd.DataFrame(recs)
    os.makedirs(OUT_DIR, exist_ok=True)
    tag = "%s_%s" % (start, end)
    df.to_csv(os.path.join(OUT_DIR, "paper_step2_replaycheck_%s.csv" % tag),
              index=False, encoding="utf-8-sig")

    n = len(df)
    n_match = int(df['match'].sum())
    n_sig = int(df['batch_i'].notna().sum())
    n_sig_rt = int(df['rt_i'].notna().sum())
    mism = df[df['match'] == 0]
    gaps = df['gap_bp'].dropna()

    print("\n" + "=" * 72)
    print("STEP2 回放等价验证:实时监测器 vs 批量find_signal(PhaseA已验证)")
    print("=" * 72)
    print(" 对拍样本 (code,day)     : %d" % n)
    print(" 逐bar对拍一致           : %d  (%.2f%%)" % (n_match, 100.0 * n_match / n if n else 0))
    print(" 有信号(批量/实时)       : %d / %d" % (n_sig, n_sig_rt))
    print(" 失配明细                : %d 条" % len(mism))
    if len(mism):
        print(mism.head(20).to_string(index=False))
    if len(gaps):
        print("-" * 72)
        print(" capture(信号bar close) vs 下一根open 间隙: mean=%+.1fbp median=%+.1fbp" % (
            gaps.mean(), gaps.median()))
        print("   |gap|分位 p50=%.1fbp p90=%.1fbp p99=%.1fbp (供成本模型校准,非对错)" % (
            gaps.abs().quantile(0.5), gaps.abs().quantile(0.9), gaps.abs().quantile(0.99)))
    print("=" * 72)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20230301")
    ap.add_argument("--end", default="20230331")
    args = ap.parse_args()
    run(args.start, args.end)
