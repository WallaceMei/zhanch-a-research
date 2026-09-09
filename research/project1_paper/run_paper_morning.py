# -*- coding: utf-8 -*-
"""Project1 Paper — 盘前决策(09:26-09:28 跑)。三组决策 → 监测池落盘。

⚠️ 护栏1:live 模式依赖的 xtdata 竞价取数未经实盘验证(周一实测项)。
⚠️ 护栏2:--ai real 只允许"今天"(ai_selector 内 assert 强拦);历史日期只能 --ai mock。
⚠️ 护栏4:三组唯一变量=选股;仓位/进出场全一致(闸/引擎在 intraday/settle,共用)。

用法:
  演习: py -3.10 run_paper_morning.py --mode drill --d8 20231204 --ai mock --state drill
  live: py -3.10 run_paper_morning.py --mode live --ai real --state real   (周一实测通过后)
"""
import os
import sys
import json
import random
import argparse
import datetime as dt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_config as C        # noqa: E402
import paper_state as S         # noqa: E402
import pool_repro as PR         # noqa: E402
import snapshot as SNAP         # noqa: E402
import ai_selector as AI        # noqa: E402


def decide_random3(d8, pool):
    rng = random.Random(int(d8))
    n = min(C.N_PICK, len(pool))
    idx = sorted(rng.sample(range(len(pool)), n)) if len(pool) else []
    return [dict(code=pool[i]['stock'], name=pool[i].get('name', ''), rank=j + 1,
                 reason='random_seed_%s' % d8) for j, i in enumerate(idx)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=['live', 'drill'], required=True)
    ap.add_argument("--d8", default=None, help="drill 模式必填;live 默认今天")
    ap.add_argument("--ai", choices=['real', 'mock', 'off'], required=True)
    ap.add_argument("--state", choices=['real', 'drill'], required=True)
    args = ap.parse_args()

    d8 = args.d8 or dt.datetime.now().strftime("%Y%m%d")
    if args.mode == 'drill' and args.ai == 'real':
        raise SystemExit("护栏2:drill(历史)禁用真AI,只能 --ai mock/off")
    if args.mode == 'live':
        print("⚠️ 护栏1:实时链路未经实盘验证(周一小样本实测通过前不得开真实paper)")

    # 1) 当日池
    if args.mode == 'drill':
        PR._load()
        pool = PR.dragon_pool(d8, PR.prev_trading_day(d8))
        today_auc_map = None            # snapshot 从缓存取竞价
        diag = dict(mode='drill', pool=len(pool))
    else:
        import live_pool as LP
        pool, diag = LP.build_pool_live(d8)
        today_auc_map = None            # live_pool 已注入 rc 打分;快照竞价字段用 pool.open_ratio
    pool = pool[:12]
    print("[morning] %s pool=%d diag=%s" % (d8, len(pool), diag))
    if not pool:
        S.write_day(args.state, d8, "morning",
                    dict(d8=d8, pool=[], decisions={}, union=[], note="empty_pool"))
        print("[morning] 空池,今日三组均不参与")
        return

    # 2) 快照(护栏2:只含历史表现+今日竞价)
    snaps = SNAP.build_snapshots(d8, pool)
    # 3) 三组决策(唯一变量)
    ai_log = os.path.join(S.state_dir(args.state), 'ai_log')
    ai_res = AI.select(d8, snaps, args.ai, ai_log)
    ai_picks = [dict(code=pk['code'], name=pk.get('name', ''), rank=i + 1,
                     reason=pk.get('reason', ''), confidence=pk.get('confidence'))
                for i, pk in enumerate(ai_res['picks'])]
    if not ai_res['ok']:
        print("[morning] AI组今日空仓(%s)—— 按spec§3.4不fallback" % ai_res['error'])
    decisions = dict(
        ai_minimax=ai_picks,
        random3=decide_random3(d8, pool),
        all_in=[dict(code=p['stock'], name=p.get('name', ''), rank=i + 1, reason='all_in')
                for i, p in enumerate(pool)],
    )
    union = []
    for g in C.GROUPS:
        for pk in decisions[g]:
            if pk['code'] not in union:
                union.append(pk['code'])

    # 4) 落盘:监测池 + 决策留痕
    S.write_day(args.state, d8, "morning", dict(
        d8=d8, mode=args.mode, ai_mode=args.ai, ai_model=ai_res['model_version'],
        ai_ok=ai_res['ok'], ai_error=ai_res['error'], market_note=ai_res['market_note'],
        pool=[dict(code=p['stock'], name=p.get('name', ''), tpl=p['tpl'],
                   dragon_score=round(p['dragon_score'], 4),
                   open_ratio=round(p.get('open_ratio', 0), 4)) for p in pool],
        snapshots=snaps, decisions=decisions, union=union, diag=diag))
    rows = []
    for g in C.GROUPS:
        for pk in decisions[g]:
            rows.append(dict(d8=d8, group=g, rank=pk['rank'], code=pk['code'],
                             name=pk['name'], pick_reason=pk['reason'],
                             confidence=pk.get('confidence'),
                             model_version=ai_res['model_version'] if g == 'ai_minimax' else '',
                             buy_status='pending'))
    S.append_csv(args.state, "decisions.csv", rows, S.DECISIONS_HEADER)
    print("[morning] 决策落盘: ai=%d only random=%d all=%d union=%d → days/%s_morning.json" % (
        len(decisions['ai_minimax']), len(decisions['random3']),
        len(decisions['all_in']), len(union), d8))


if __name__ == "__main__":
    main()
