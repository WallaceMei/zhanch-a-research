# -*- coding: utf-8 -*-
"""Project1 Paper Step2 — QMT/xtdata 实时进场监测(live 小样本版)。

★ 只读红线:仅 import xtquant.xtdata(行情只读)。全文件不 import xttrader、
  不创建任何交易连接、不发任何交易指令。paper 纯观察。

用法(交易日早盘,QMT/miniQMT 客户端需在运行):
  py -3.10 run_step2_live.py --check                       # 连通性冒烟(随时可跑)
  py -3.10 run_step2_live.py --codes 000001.SZ,600519.SH   # 小样本实时监测
  py -3.10 run_step2_live.py --codes ... --until 10:33     # 默认到10:33(信号窗10:30止)

流程:
  subscribe_quote(period='1m') → 每 poll 秒拉当日1m bar → 只推**已完结**bar
  → GateMonitor(与批量版对拍100%等价) → 命中那一刻:记 signal_hm/capture_price(bar close)
    + get_full_tick 瞬时 lastPrice + 本机时钟 → JSONL 逐事件留痕 + bars 全量落盘。

口径:信号判定窗到 10:30(Phase A 默认 obs_end;10:45 是回测"下一根open买入"的截止,
live 口径=命中那一刻即记进场,10:45 不再起作用)。09:30 首根=竞价(QMT约定)。
bar 完结判定:bar标签时刻 <= 当前时刻-safety(默认2s;QMT 1m 标签=bar结束分钟,
首日实测若发现为bar起始标签,用 --label_mode start 切换,bars 落盘可事后核对)。

产物:out/rt_live/rtlive_<date>_{events.jsonl, bars.csv, summary.csv}
"""
import os
import sys
import json
import time
import argparse
import datetime as dt

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from rt_monitor import PoolMonitor   # noqa: E402  (纯python,无第三方依赖)

OUT_DIR = os.path.join(_HERE, "out", "rt_live")


def _now_hms():
    return dt.datetime.now().strftime("%H:%M:%S")


def connectivity_check(codes):
    """连通性冒烟:full tick + 近一日1m标签口径观察。QMT客户端未开则此处报错。"""
    from xtquant import xtdata
    print("[check] xtdata import OK: %s" % os.path.dirname(xtdata.__file__))
    codes = codes or ["600519.SH", "000001.SZ"]
    try:
        tick = xtdata.get_full_tick(codes)
        for c in codes:
            t = tick.get(c) or {}
            print("[check] full_tick %s: lastPrice=%s time=%s volume=%s amount=%s" % (
                c, t.get('lastPrice'), t.get('timetag') or t.get('time'),
                t.get('volume'), t.get('amount')))
    except Exception as ex:
        print("[check] get_full_tick 失败(QMT客户端未运行?): %r" % ex)
        return False
    # 观察本地已有 1m 数据的标签口径(若本地无数据仅提示,不下载)
    try:
        md = xtdata.get_market_data_ex([], codes[:1], period='1m',
                                       start_time='', end_time='', count=8)
        df = md.get(codes[0])
        if df is not None and len(df):
            print("[check] 近8根本地1m标签: %s" % list(df.index[-8:]))
        else:
            print("[check] 本地无1m缓存(不影响live订阅;live当日bar由订阅产生)")
    except Exception as ex:
        print("[check] 1m标签观察失败: %r" % ex)
    return True


def run_live(codes, until, poll, label_mode, safety_sec):
    from xtquant import xtdata     # 行情只读;绝不 import xttrader
    today = dt.datetime.now().strftime("%Y%m%d")
    os.makedirs(OUT_DIR, exist_ok=True)
    pre = os.path.join(OUT_DIR, "rtlive_%s" % today)
    ev_path = pre + "_events.jsonl"
    ev_f = open(ev_path, "a", encoding="utf-8")

    def log_ev(kind, **kw):
        rec = dict(ts=dt.datetime.now().isoformat(timespec='milliseconds'), kind=kind, **kw)
        ev_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ev_f.flush()
        print("[%s] %s %s" % (_now_hms(), kind,
                              " ".join("%s=%s" % (k, v) for k, v in kw.items())), flush=True)

    log_ev("start", codes=codes, until=until, poll=poll, label_mode=label_mode)
    for c in codes:
        xtdata.subscribe_quote(c, period='1m', count=-1)
    log_ev("subscribed", n=len(codes))

    mon = PoolMonitor(codes)
    pushed = {c: 0 for c in codes}        # 每票已推入的bar数(严格顺序推进)
    bars_dump = []

    while True:
        now = dt.datetime.now()
        now_hm = now.strftime("%H:%M")
        if now_hm >= until:
            log_ev("cutoff_reached", until=until)
            break
        if not mon.pending():
            log_ev("all_resolved")
            break
        try:
            md = xtdata.get_market_data_ex([], codes, period='1m',
                                           start_time=today, end_time='', count=-1)
        except Exception as ex:
            log_ev("poll_error", err=repr(ex))
            time.sleep(poll)
            continue
        for c in codes:
            df = md.get(c)
            if df is None or len(df) <= pushed[c]:
                continue
            for ts_label, row in df.iloc[pushed[c]:].iterrows():
                s = str(ts_label)
                hm = "%s:%s" % (s[8:10], s[10:12])
                # bar完结判定:end标签=该分钟即bar结束;start标签=结束还要+1分钟
                end_hm = hm if label_mode == 'end' else _plus1min(hm)
                bar_end = now.replace(hour=int(end_hm[:2]), minute=int(end_hm[3:5]),
                                      second=0, microsecond=0)
                if (now - bar_end).total_seconds() < safety_sec:
                    break                                  # 本根未完结,后面的更未完结
                pushed[c] += 1
                bars_dump.append(dict(code=c, label=s, hm=hm, open=row['open'],
                                      high=row['high'], low=row['low'], close=row['close'],
                                      volume=row['volume'], amount=row['amount'],
                                      recv_ts=now.isoformat(timespec='milliseconds')))
                sig = mon.push_bar(c, hm, row['open'], row['high'], row['low'],
                                   row['close'], row['volume'], row['amount'])
                if sig is not None:
                    tick_px = None
                    try:
                        tk = xtdata.get_full_tick([c]).get(c) or {}
                        tick_px = tk.get('lastPrice')
                    except Exception:
                        pass
                    sig['tick_price_at_capture'] = tick_px
                    sig['capture_wallclock'] = dt.datetime.now().isoformat(timespec='milliseconds')
                    log_ev("SIGNAL", **sig)
        time.sleep(poll)

    # 落盘
    pd.DataFrame(bars_dump).to_csv(pre + "_bars.csv", index=False, encoding="utf-8-sig")
    rows = []
    for c in codes:
        m = mon.mons[c]
        sig = m.signal or {}
        rows.append(dict(code=c, got_signal=int(m.signal is not None),
                         signal_hm=sig.get('signal_hm'), vwap=sig.get('vwap'),
                         capture_price=sig.get('capture_price'),
                         tick_price_at_capture=sig.get('tick_price_at_capture'),
                         capture_wallclock=sig.get('capture_wallclock'),
                         bars_pushed=pushed[c], expired=int(m.expired)))
    pd.DataFrame(rows).to_csv(pre + "_summary.csv", index=False, encoding="utf-8-sig")
    log_ev("done", out=pre)
    ev_f.close()
    print("\n产物: %s_{events.jsonl, bars.csv, summary.csv}" % pre)


def _plus1min(hm):
    h, m = int(hm[:2]), int(hm[3:5])
    m += 1
    if m == 60:
        h += 1; m = 0
    return "%02d:%02d" % (h, m)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="连通性冒烟(不进监测循环)")
    ap.add_argument("--codes", default="", help="逗号分隔,如 000001.SZ,600519.SH")
    ap.add_argument("--until", default="10:33", help="轮询截止(信号窗本身到10:30)")
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--label_mode", default="end", choices=["end", "start"],
                    help="1m bar标签=bar结束分钟(end,QMT历史canonical口径)或起始分钟(start)")
    ap.add_argument("--safety_sec", type=float, default=2.0)
    args = ap.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if args.check:
        connectivity_check(codes)
    else:
        if not codes:
            ap.error("--codes 必填(小样本,如 000001.SZ,600519.SH)")
        run_live(codes, args.until, args.poll, args.label_mode, args.safety_sec)
