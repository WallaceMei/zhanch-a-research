# -*- coding: utf-8 -*-
"""Project1 Phase A —— Step 1:MA5 破位止损松紧敏感性(护栏版,只调 MA5 这一刀)。

背景(Step0.5 指认):MA5(N=3)占组1趋势持有出场 84%,疑似把"身体"砍废、也让大肉回吐
过大才被扫出。本步专验:放宽 MA5 破位确认,能否少砍身体、同时保住尾部大肉。

同一批 top12 全进票(候选池/进场闸/成本/T+1/成交可得性 全不变),只换 MA5 破位规则:
  A  N=2                          更勤快(对照)
  B  N=3                          当前默认(基线)
  C  N=5                          更宽容(少砍身体)
  D  N=3 + 破位幅度门槛 close<MA5_prev*0.98   单纯触及不算破位
  E  N=3 + 不创反弹新高            连续N根跌破 且 期间不创反弹新高(更严格)
其余出场(硬止损-7% / 两段式移动止盈 / 20天天花板)三方向都不动。

重点看:大肉捕获率 / 出场原因分布 / 身体被砍(小亏MA5出场) / 峰值>40%留存(基线136) / PF·skew·均收益。

★护栏:看 MA5 松紧对"砍身体 vs 保尾部"的敏感性,不是找最优 N。报告禁写"最优参数"。
        任何变体都不会转正(负基座还在)。每变体出成交可得性 + 贡献集中度。
只读 minute/cache;只写 out/。不碰实盘/候选池/不装包。
用法:py -3.10 run_step1_ma5.py --start 20200101 --end 20231231 --tag IS_2020_2023
"""
import os
import sys
import time
import argparse
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_repro as PR
import engine_phaseA as E

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# MA5 变体(在组1趋势持有 DEFAULT_CFG 基础上只改 MA5 相关键)
VARIANTS = [
    ('A_N2', 'A:N=2更勤快', dict(ma5_n=2)),
    ('B_N3', 'B:N=3基线', dict(ma5_n=3)),
    ('C_N5', 'C:N=5更宽容', dict(ma5_n=5)),
    ('D_mult098', 'D:N=3+幅度<0.98', dict(ma5_n=3, ma5_break_mult=0.98)),
    ('E_norebound', 'E:N=3+不创反弹新高', dict(ma5_n=3, ma5_no_rebound=True)),
]


def run(start, end, tag, log_every=120):
    PR._load()
    all_days = [d for d in PR.trade_days() if start <= d <= end]
    print("[step1-ma5] tag=%s days=%d (%s..%s)" % (tag, len(all_days), all_days[0], all_days[-1]), flush=True)
    base_cfg = dict(E.DEFAULT_CFG)

    trades = {k: [] for k, _, _ in VARIANTS}
    entry_reasons = Counter()
    n_candidates = 0
    t0 = time.time()
    for k, d in enumerate(all_days):
        prev = PR.prev_trading_day(d)
        pool = PR.dragon_pool(d, prev)
        for p in pool:
            code = p['stock']
            n_candidates += 1
            ctx = E.daily_ctx(code, d)
            if ctx is None or ctx['prev_close'] is None:
                entry_reasons['buy_skip_no_dailyctx'] += 1
                continue
            e = E.try_entry(code, d, ctx['prev_close'], base_cfg)   # 进场共用
            entry_reasons[e['buy_reason']] += 1
            if not e['filled']:
                continue
            for vkey, _vname, vover in VARIANTS:
                cfg = dict(base_cfg); cfg['exit_style'] = 'trend_hold'; cfg.update(vover)
                x = E.simulate_exit_dispatch(code, d, e['buy_price'], e['buy_hm'], cfg)
                net = E.trade_return_from_gross(x.get('gross'), cfg)
                trades[vkey].append(dict(
                    date=d, code=code, name=p.get('name', ''), tpl=p['tpl'],
                    buy_price=round(e['buy_price'], 4), sell_d8=x['sell_d8'],
                    exit_reason=x['exit_reason'], hold_days=x['hold_days'],
                    net_return=round(net, 5) if net is not None else None,
                    peak_return=round(x['peak_return'], 5),
                    day0_untradable_risk=int(x['day0_untradable_risk']),
                    sell_blocked_count=x['sell_blocked_count'],
                ))
        if (k + 1) % log_every == 0:
            print("  %d/%d days cand=%d %.0fs" % (k + 1, len(all_days), n_candidates, time.time() - t0), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    _write(trades, entry_reasons, n_candidates, tag, all_days)


def _concentration(net):
    pos = np.sort(net[net > 0])[::-1]; neg = np.sort(net[net < 0])
    tp = pos.sum() if len(pos) else 0.0; tn = neg.sum() if len(neg) else 0.0
    return (round((pos[:10].sum() / tp) if tp > 0 else 0.0, 4),
            round((neg[:10].sum() / tn) if tn < 0 else 0.0, 4))


def _metrics(tdf):
    r = tdf['net_return'].dropna().values
    wins = r[r > 0]; losses = r[r <= 0]
    pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float('inf')
    mu, sd = r.mean(), r.std()
    skew = float((((r - mu) / sd) ** 3).mean()) if sd > 0 else 0.0
    cap = [max(0.0, rr['net_return']) / rr['peak_return']
           for _, rr in tdf.iterrows() if rr['peak_return'] and rr['peak_return'] > 0 and rr['net_return'] is not None]
    is_ma5 = tdf['exit_reason'] == 'ma5_break'
    # 身体被砍:MA5破位 且 亏损 且 峰值<10%(早早砍在小亏,没起来过)
    body_cut = tdf[is_ma5 & (tdf['net_return'] < 0) & (tdf['peak_return'] < 0.10)]
    ma5_loss = tdf[is_ma5 & (tdf['net_return'] < 0)]
    monster = tdf[tdf['peak_return'] > 0.40]
    tw, tl = _concentration(r)
    return dict(
        n_trades=len(r), win_rate=round((r > 0).mean(), 4),
        mean_ret=round(float(mu), 5), median_ret=round(float(np.median(r)), 5),
        profit_factor=(round(pf, 3) if pf != float('inf') else 'inf'),
        skew=round(skew, 3), max_win=round(float(r.max()), 4),
        bigmeat_capture=round(float(np.mean(cap)), 4) if cap else 0.0,
        avg_hold=round(float(tdf['hold_days'].mean()), 2),
        ma5_exit_share=round(float(is_ma5.mean()), 4),
        body_cut_n=len(body_cut), body_cut_share=round(len(body_cut) / len(tdf), 4),
        ma5_loss_n=len(ma5_loss),
        monster40_n=len(monster),
        top10_win_share=tw, top10_loss_share=tl,
        sell_blocked_days=int(tdf['sell_blocked_count'].sum()),
    )


def _write(trades, entry_reasons, n_candidates, tag, all_days):
    pre = os.path.join(OUT_DIR, "project1_phaseA_step1ma5_%s" % tag)
    rows = []; exit_dist = {}
    for vkey, vname, _ in VARIANTS:
        tdf = pd.DataFrame(trades[vkey])
        tdf.to_csv(pre + "_%s_trades.csv" % vkey, index=False, encoding="utf-8-sig")
        m = _metrics(tdf); m['variant'] = vname; m['vkey'] = vkey; rows.append(m)
        exit_dist[vkey] = (tdf.groupby('exit_reason').size() / len(tdf)).round(3).to_dict()
    cmp = pd.DataFrame(rows).set_index('vkey')
    cols = ['variant', 'n_trades', 'win_rate', 'mean_ret', 'median_ret', 'profit_factor', 'skew',
            'max_win', 'bigmeat_capture', 'avg_hold', 'ma5_exit_share', 'body_cut_n', 'body_cut_share',
            'ma5_loss_n', 'monster40_n', 'top10_win_share', 'top10_loss_share', 'sell_blocked_days']
    cmp[cols].to_csv(pre + "_compare.csv", encoding="utf-8-sig")

    er_total = sum(entry_reasons.values()); filled = entry_reasons.get('filled', 0)
    avail = dict(candidates=n_candidates, filled=filled,
                 fill_rate=round(filled / er_total, 4) if er_total else 0,
                 buy_skip_limit_up_rate=round(entry_reasons.get('buy_skip_limit_up', 0) / er_total, 4) if er_total else 0,
                 buy_skip_no_signal=entry_reasons.get('buy_skip_no_signal', 0))
    _report(pre + "_report.md", tag, cmp, exit_dist, avail, all_days)

    print("\n" + "=" * 92)
    print("STEP1 MA5松紧敏感性 (%s)  [同批全进票,只换MA5破位规则;禁写'最优参数';负基座不会转正]" % tag)
    print("=" * 92)
    print(" 进场共用: 候选%d filled=%d(%.1f%%) 涨停买不到%.1f%%" % (
        n_candidates, filled, avail['fill_rate'] * 100, avail['buy_skip_limit_up_rate'] * 100))
    print("-" * 92)
    print("%-20s %6s %6s %7s %6s %6s %7s %7s %8s %7s" % (
        "变体", "n", "胜率", "均收益", "PF", "大肉捕", "MA5占", "身体砍", "monster40", "skew"))
    for vkey, vname, _ in VARIANTS:
        m = cmp.loc[vkey]
        print("%-20s %6d %5.1f%% %6.2f%% %5s %6.2f %6.1f%% %6.1f%% %8d %7.2f" % (
            vname, m['n_trades'], m['win_rate'] * 100, m['mean_ret'] * 100, str(m['profit_factor']),
            m['bigmeat_capture'], m['ma5_exit_share'] * 100, m['body_cut_share'] * 100,
            m['monster40_n'], m['skew']))
    print("-" * 92)
    print(" 基线(Step0.5 组1)monster40=136。放宽MA5该↑;身体砍该↓;大肉捕获该↑ —— 看是否同向。")
    print("=" * 92)
    print("输出: %s_{compare,report,<variant>_trades}.*" % pre)


def _report(path, tag, cmp, exit_dist, avail, all_days):
    L = []; A = L.append
    A("# Project1 Phase A — Step1 MA5破位止损松紧敏感性 (%s)\n" % tag)
    A("> 只调 MA5 破位这一刀(其余出场/进场/成本/候选池全不变)。**护栏:只写 MA5 松紧对'砍身体 vs 保尾部'的敏感性,"
      "禁写'最优参数'/'收益改善有效'。任何变体都不会转正——负基座(全进无选股)还在,本步产出是'MA5松紧的赔率结构知识'。**")
    A("> 不含AI选股层(只能forward paper验);单票等权模拟;2026未回看(授权回看才碰)。\n")
    A("## 变体定义")
    A("- A N=2(更勤快对照) / B N=3(当前基线) / C N=5(更宽容) / "
      "D N=3+破位幅度门槛(close<MA5_prev×0.98) / E N=3+不创反弹新高(连续N根跌破且期间收盘不创新高)。")
    A("- MA5_prev=前一交易日已知MA5(不偷看当日);检查点每5分钟一次;尾盘14:50确认。\n")
    A("## 成交可得性(五变体共用进场)")
    A("- 候选 %d / filled %d (%.1f%%) / 涨停买不到 %.1f%% / no_signal %d\n" % (
        avail['candidates'], avail['filled'], avail['fill_rate'] * 100,
        avail['buy_skip_limit_up_rate'] * 100, avail['buy_skip_no_signal']))
    A("## 敏感性主表")
    A("| 变体 | 笔数 | 胜率 | 均收益 | PF | 大肉捕获 | MA5出场占 | 身体砍笔 | 身体砍率 | MA5亏损笔 | monster>40% | skew | 均持 | top10盈 |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for vkey, vname, _ in VARIANTS:
        m = cmp.loc[vkey]
        flag = " 🔴" if float(m['top10_win_share']) >= 0.5 else ""
        A("| %s | %d | %.1f%% | %.2f%% | %s | %.2f | %.0f%% | %d | %.1f%% | %d | %d | %.2f | %.1f | %.0f%%%s |" % (
            vname, m['n_trades'], m['win_rate'] * 100, m['mean_ret'] * 100, str(m['profit_factor']),
            m['bigmeat_capture'], m['ma5_exit_share'] * 100, m['body_cut_n'], m['body_cut_share'] * 100,
            m['ma5_loss_n'], m['monster40_n'], m['skew'], m['avg_hold'], m['top10_win_share'] * 100, flag))
    A("\n> 基线参照:Step0.5 组1(=本表 B)monster>40% 为 136 只。")
    A("> 放宽 MA5(C/D/E)若同时:身体砍率↓ + monster留存↑ + 大肉捕获↑ → 说明'MA5太勤快砍废身体'的判断成立。")
    A("> 若放宽后身体砍↓但 monster/大肉没↑、反而均收益更差 → 说明砍身体的同时也砍掉了本该止损的真亏损,松紧是双刃。\n")
    A("## 出场原因分布(看 MA5 占比下降后谁接管)")
    for vkey, vname, _ in VARIANTS:
        ed = sorted(exit_dist[vkey].items(), key=lambda kv: -kv[1])
        A("- **%s**:%s" % (vname, ' / '.join("%s %.0f%%" % (k, v * 100) for k, v in ed)))
    A("\n## 判读留给 Wallace")
    A("- 看哪个变体在'少砍身体(body_cut↓)+ 保尾部(monster↑/大肉捕获↑)'上最平衡,且赔率结构(PF/skew)不塌。")
    A("- 选变体看稳健(不选IS单点最好);有候选 → 冻结跑 OOS(2024-2025)验:大肉捕获/赔率结构明显恶化=过拟合,作废不回头调。")
    A("- 提醒:均收益仍全负,本步不产出可盈利策略,只产出 MA5 松紧的赔率结构知识。\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20200101")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--tag", default="IS_2020_2023")
    args = ap.parse_args()
    run(args.start, args.end, args.tag)
