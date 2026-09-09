# -*- coding: utf-8 -*-
"""Project1 Paper — 盘后结算(18:30 跑,或演习中逐日跑)。

方法 = "重放已验证引擎":每晚对每个未平仓位从买入日起用 simulate_exit 重放
(days_override 限到今天 + no_proxy_close),触发即平、未触发如实持仓 —— 确定性,
出场逻辑与 Phase A 回测 100% 同一份代码。

流程(live):① update_daily_cache 补日线尾巴 ② 持仓票当日分钟兜底(xtdata,若canonical断档)
           ③ 逐组重放结算 ④ MTM 记净值 ⑤ 留痕。
用法:
  演习: py -3.10 run_paper_settle.py --mode drill --d8 20231204 --state drill
  live: py -3.10 run_paper_settle.py --mode live --state real
"""
import os
import sys
import subprocess
import argparse
import datetime as dt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_config as C        # noqa: E402
import paper_state as S         # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=['live', 'drill'], required=True)
    ap.add_argument("--d8", default=None, help="结算日(drill必填;live默认今天)")
    ap.add_argument("--state", choices=['real', 'drill'], required=True)
    args = ap.parse_args()
    asof = args.d8 or dt.datetime.now().strftime("%Y%m%d")

    if args.mode == 'live':
        # ① 日线尾巴(独立进程,完成后本进程再懒加载 PR → 能看到新尾巴)
        r = subprocess.run(["py", "-3.10", os.path.join(_HERE, "update_daily_cache.py"),
                            "--asof", asof], capture_output=True, text=True, timeout=900)
        print(r.stdout[-800:] if r.stdout else r.stderr[-400:])

    import pool_repro as PR      # noqa: E402  (此时加载,吃到新尾巴)
    import engine_phaseA as E    # noqa: E402
    import paper_engine as PE    # noqa: E402
    PE.install()                 # 分钟兜底(canonical 优先)
    cfg = C.engine_cfg()
    PR._load()

    st = S.load_state(args.state)
    open_codes = sorted({c for g in C.GROUPS for c in st['groups'][g]['positions']})
    if args.mode == 'live' and open_codes:
        # ② 持仓票当日分钟兜底
        stat = PE.ensure_minute_live(open_codes, asof)
        print("[settle] 分钟数据: %s" % stat)

    trades_rows, equity_rows = [], []
    for g in C.GROUPS:
        gs = st['groups'][g]
        for code in list(gs['positions'].keys()):
            pos = gs['positions'][code]
            days_avail = [d for d in PR.forward_trading_days(pos['buy_d8'],
                                                             cfg['time_cap_days'] + 6)
                          if d <= asof]
            out = E.simulate_exit(code, pos['buy_d8'], pos['buy_price'], pos['buy_hm'],
                                  cfg, days_override=days_avail, no_proxy_close=True)
            if out['sell_price'] is not None:
                net = E.trade_return(pos['buy_price'], out['sell_price'], cfg)
                cost_frac = cfg['commission'] * 2 + cfg['stamp']
                final_val = pos['entry_cost'] * (out['sell_price'] / pos['buy_price'] - cost_frac)
                gs['cash'] += final_val
                trades_rows.append(dict(
                    group=g, code=code, name=pos.get('name', ''),
                    buy_d8=pos['buy_d8'], buy_hm=pos['buy_hm'],
                    buy_price=round(pos['buy_price'], 4),
                    sell_d8=out['sell_d8'], sell_hm=out['sell_hm'],
                    sell_price=round(out['sell_price'], 4),
                    exit_reason=out['exit_reason'], hold_days=out['hold_days'],
                    net_return=round(net, 5) if net is not None else None,
                    peak_return=round(out['peak_return'], 5),
                    entry_cost=round(pos['entry_cost'], 5),
                    pnl_frac=round(final_val - pos['entry_cost'], 6)))
                del gs['positions'][code]
            else:
                # 仍持仓:MTM(asof 收盘;停牌/缺价平值)
                p = PR.panel().get(code)
                if p is not None and asof in p.index:
                    px = float(p.loc[asof, 'close'])
                    pos['value'] = pos['entry_cost'] * (px / pos['buy_price'])
                    pos['last_px'] = px
                pos['peak_return_sofar'] = round(out['peak_return'], 5)
                pos['pending_exit'] = out.get('pending_exit')
        eq = S.group_equity(gs)
        equity_rows.append(dict(d8=asof, group=g, equity=round(eq, 6),
                                cash=round(gs['cash'], 6), n_pos=len(gs['positions'])))

    st['last_settle'] = asof
    S.save_state(args.state, st)
    S.append_csv(args.state, "trades.csv", trades_rows, S.TRADES_HEADER)
    S.append_csv(args.state, "equity.csv", equity_rows, S.EQUITY_HEADER)
    S.write_day(args.state, asof, "settle", dict(
        d8=asof, closed=len(trades_rows),
        equity={r['group']: r['equity'] for r in equity_rows},
        open_positions={g: list(st['groups'][g]['positions'].keys()) for g in C.GROUPS}))
    print("[settle] %s 平仓=%d | " % (asof, len(trades_rows)) +
          " ".join("%s=%.4f(%d仓)" % (r['group'][:6], r['equity'], r['n_pos'])
                   for r in equity_rows))


if __name__ == "__main__":
    main()
