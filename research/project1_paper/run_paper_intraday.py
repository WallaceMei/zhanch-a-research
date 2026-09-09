# -*- coding: utf-8 -*-
"""Project1 Paper — 盘中进场监测(09:29-10:33)。三组共用监测,唯一变量=谁在监测池。

⚠️⚠️ 护栏1:实时链路(xtdata live bar)未经实盘验证 —— 2026-07-06 周一小样本实测
   通过前,--mode live 只能带 --ack-unverified 跑"观察演练"(照常记录但产物目录
   须为 drill state),不得写真实 paper state。代码强拦:live+state=real 需两个显式旗标。
⚠️ 护栏3:只 import xtquant.xtdata(只读),不发交易指令。
⚠️ 护栏4:同票同日只有一个监测器/一个信号,买价跨组必然一致(结构公平,同Step1)。

用法:
  演习: py -3.10 run_paper_intraday.py --mode drill --d8 20231204 --state drill
  live: py -3.10 run_paper_intraday.py --mode live --state drill --ack-unverified  (周一)
"""
import os
import sys
import json
import time
import argparse
import datetime as dt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_config as C        # noqa: E402
import paper_state as S         # noqa: E402
from rt_monitor import PoolMonitor   # noqa: E402

LIMIT_EPS = 1e-3


class BuyBook:
    """三组各自的当日买入执行(slot/现金/涨停买不到;共享同一 signal)。"""

    def __init__(self, st, decisions, cfg):
        self.st = st
        self.cfg = cfg
        self.decisions = decisions      # {group: [picks]}
        self.results = []               # 逐事件记录

    def on_signal(self, sig, prev_close_map):
        code = sig['code']
        cap = float(sig['capture_price'])
        prev_close = prev_close_map.get(code)
        for g in C.GROUPS:
            if code not in {p['code'] for p in self.decisions.get(g, [])}:
                continue
            gs = self.st['groups'][g]
            status = None
            if prev_close and cap >= round(prev_close * 1.10, 2) - LIMIT_EPS:
                status = 'buy_skip_limit_up'
            elif code in gs['positions']:
                status = 'skip_already_held'
            elif len(gs['positions']) >= C.N_SLOTS:
                status = 'skip_slots_full'
            else:
                eq = S.group_equity(gs)
                cost = min(C.POS_FRAC * eq, gs['cash'])
                if cost <= 1e-9:
                    status = 'skip_no_cash'
                else:
                    buy_price = cap * (1 + self.cfg['buy_slip'])
                    gs['cash'] -= cost
                    gs['positions'][code] = dict(
                        buy_d8=sig['d8'], buy_hm=sig['signal_hm'], buy_price=buy_price,
                        capture_price=cap, tick_price=sig.get('tick_price_at_capture'),
                        entry_cost=cost, value=cost, last_px=buy_price,
                        name=sig.get('name', ''))
                    status = 'bought'
            self.results.append(dict(group=g, code=code, hm=sig['signal_hm'],
                                     capture_price=cap, status=status))


def _prev_close_map(codes, d8):
    import engine_phaseA as E
    out = {}
    for c in codes:
        ctx = E.daily_ctx(c, d8)
        if ctx:
            out[c] = ctx['prev_close']
    return out


def run_drill(d8, state_kind):
    """回放演习:union 票的当日历史bar按时间归并逐根喂(信号跨票按时序竞争slot)。"""
    import engine_phaseA as E
    morning = S.read_day(state_kind, d8, "morning")
    if not morning or not morning['union']:
        print("[intraday] %s 无监测池,跳过" % d8)
        return
    union = morning['union']
    cfg = C.engine_cfg()
    st = S.load_state(state_kind)
    book = BuyBook(st, morning['decisions'], cfg)
    prev_close_map = _prev_close_map(union, d8)
    name_map = {p['code']: p['name'] for p in morning['pool']}

    mon = PoolMonitor(union)
    streams = {}
    for c in union:
        day = E.minute_day(c, d8)
        if day is not None:
            streams[c] = day[['hm', 'open', 'high', 'low', 'close', 'volume', 'amount']].values
    pos = {c: 0 for c in streams}
    while True:                       # 按 hm 归并推进(跨票时序公平)
        nxt = None
        for c, arr in streams.items():
            if pos[c] < len(arr):
                hm = arr[pos[c]][0]
                if nxt is None or hm < nxt[1]:
                    nxt = (c, hm)
        if nxt is None:
            break
        c = nxt[0]
        r = streams[c][pos[c]]
        pos[c] += 1
        sig = mon.push_bar(c, r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                           extra=dict(d8=d8, name=name_map.get(c, '')))
        if sig is not None:
            book.on_signal(sig, prev_close_map)
    _finish(d8, state_kind, st, mon, book, mode='drill')


def run_live(d8, state_kind):
    from xtquant import xtdata        # 行情只读;绝不 import xttrader
    morning = S.read_day(state_kind, d8, "morning")
    if not morning or not morning['union']:
        print("[intraday] %s 无监测池,退出" % d8)
        return
    union = morning['union']
    cfg = C.engine_cfg()
    st = S.load_state(state_kind)
    book = BuyBook(st, morning['decisions'], cfg)
    prev_close_map = _prev_close_map(union, d8)
    name_map = {p['code']: p['name'] for p in morning['pool']}
    mon = PoolMonitor(union)
    pushed = {c: 0 for c in union}
    for c in union:
        xtdata.subscribe_quote(c, period='1m', count=-1)
    print("[intraday-live] 监测 %d 只,到 %s 截止" % (len(union), C.LIVE_UNTIL), flush=True)
    while True:
        now = dt.datetime.now()
        if now.strftime("%H:%M") >= C.LIVE_UNTIL or not mon.pending():
            break
        try:
            md = xtdata.get_market_data_ex([], union, period='1m',
                                           start_time=d8, end_time='', count=-1)
        except Exception as ex:
            print("[intraday-live] poll_error %r" % ex, flush=True)
            time.sleep(C.LIVE_POLL_SEC)
            continue
        for c in union:
            df = md.get(c)
            if df is None or len(df) <= pushed[c]:
                continue
            for ts_label, row in df.iloc[pushed[c]:].iterrows():
                s = str(ts_label)
                hm = "%s:%s" % (s[8:10], s[10:12])
                bar_end = now.replace(hour=int(hm[:2]), minute=int(hm[3:5]),
                                      second=0, microsecond=0)
                if (now - bar_end).total_seconds() < 2.0:   # end标签:未完结
                    break
                pushed[c] += 1
                tick_px = None
                sig = mon.push_bar(c, hm, row['open'], row['high'], row['low'],
                                   row['close'], row['volume'], row['amount'],
                                   extra=dict(d8=d8, name=name_map.get(c, '')))
                if sig is not None:
                    try:
                        tk = xtdata.get_full_tick([c]).get(c) or {}
                        tick_px = tk.get('lastPrice')
                    except Exception:
                        pass
                    sig['tick_price_at_capture'] = tick_px
                    print("[%s] SIGNAL %s @%s cap=%.3f tick=%s" % (
                        now.strftime("%H:%M:%S"), c, sig['signal_hm'],
                        sig['capture_price'], tick_px), flush=True)
                    book.on_signal(sig, prev_close_map)
        time.sleep(C.LIVE_POLL_SEC)
    _finish(d8, state_kind, st, mon, book, mode='live')


def _finish(d8, state_kind, st, mon, book, mode):
    S.save_state(state_kind, st)
    S.write_day(state_kind, d8, "intraday", dict(
        d8=d8, mode=mode, signals={c: s for c, s in mon.signals.items()},
        buy_events=book.results,
        no_signal=[c for c, m in mon.mons.items() if m.signal is None]))
    n_buy = sum(1 for r in book.results if r['status'] == 'bought')
    print("[intraday] %s 信号=%d 买入事件=%d(bought=%d) → days/%s_intraday.json" % (
        d8, len(mon.signals), len(book.results), n_buy, d8))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=['live', 'drill'], required=True)
    ap.add_argument("--d8", default=None)
    ap.add_argument("--state", choices=['real', 'drill'], required=True)
    ap.add_argument("--ack-unverified", action="store_true",
                    help="护栏1:live模式必须显式承认'实时链路未经实盘验证'")
    ap.add_argument("--live-verified", action="store_true",
                    help="周一实测通过后,由Wallace确认才允许 live+state=real")
    args = ap.parse_args()
    d8 = args.d8 or dt.datetime.now().strftime("%Y%m%d")
    if args.mode == 'live':
        print("⚠️⚠️ 护栏1:实时链路未经实盘验证(周一小样本实测通过前不得开真实paper)")
        if not args.ack_unverified:
            raise SystemExit("live 模式需 --ack-unverified(且实测通过前 state 必须=drill)")
        if args.state == 'real' and not args.live_verified:
            raise SystemExit("护栏1强拦:live+state=real 需 --live-verified(周一实测通过+Wallace确认后)")
        run_live(d8, args.state)
    else:
        run_drill(d8, args.state)
