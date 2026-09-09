# -*- coding: utf-8 -*-
"""Project1 Phase A —— Step 2:回吐侧专项(移动止盈,事前浮盈门槛筛样本)。

★命门(违反则结果作废):样本只用"事前可判定"的浮盈门槛筛 —— 一只票 close/buy-1 首次达到
  profit_gate(默认+15%)的那一刻当场可知,从此刻起测不同移动止盈规则。严禁用"事后峰值>40%"
  之类未来信息筛样本。

设计:候选池/进场闸/T+1/成交/成本 全不变;前段(gate前)出场不变=硬止损-7% + MA5破位N=3;
     gate 后 MA5 关、切到被测移动止盈变体(+硬止损floor + 20天封顶)。
     ★同一批"触及gate"的样本对所有变体完全相同(前段规则一致),干净对比 gate 后的回撤松紧。

移动止盈变体(gate 后启用):
  v1_dd15   峰值回撤15%(第一段默认)
  v2_dd10   峰值回撤10%(更紧锁利)
  v3_dd20   峰值回撤20%(更松让跑)
  v4_two    两段式(峰值<25%用15%,≥25%转12/10/8;当前spec默认)
  v5_atr    ATR自适应(回撤阈值=k×近期ATR,clamp[5%,30%],k=3)

只在"触及gate样本"上统计:大肉捕获率(gate价→卖价 占 gate价→峰值 的比例)/均收益·中位·PF/
  回吐幅度(峰值→卖出)/触及gate占比/gate后持仓天数。护栏:禁写"最优参数";逐年拆解防假平台;
  每变体出成交可得性+贡献集中度;负基座提醒(这是"已涨到gate子样本"的赔率结构,非整体盈利)。

只读 minute/cache;只写 out/。不碰实盘/候选池/不装包。
用法:py -3.10 run_step2_trailing.py --gate 0.15 --start 20200101 --end 20231231 --tag IS_2020_2023
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
VARIANTS = [
    ('v1_dd15', '回撤15%(默认)', dict(pg_variant='dd15')),
    ('v2_dd10', '回撤10%(紧)', dict(pg_variant='dd10')),
    ('v3_dd20', '回撤20%(松)', dict(pg_variant='dd20')),
    ('v4_two', '两段式', dict(pg_variant='two_stage')),
    ('v5_atr', 'ATR自适应k3', dict(pg_variant='atr', pg_atr_k=3.0)),
]


def run(gate, start, end, tag, log_every=120):
    PR._load()
    all_days = [d for d in PR.trade_days() if start <= d <= end]
    print("[step2-trailing] tag=%s gate=+%.0f%% days=%d (%s..%s)" % (
        tag, gate * 100, len(all_days), all_days[0], all_days[-1]), flush=True)
    base_cfg = dict(E.DEFAULT_CFG); base_cfg['exit_style'] = 'profit_gate'; base_cfg['profit_gate'] = gate

    gated_trades = {k: [] for k, _, _ in VARIANTS}
    entry_reasons = Counter()
    n_candidates = 0; n_filled = 0; n_gated = 0
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
            n_filled += 1
            gated_this = False
            for vkey, _vn, vover in VARIANTS:
                cfg = dict(base_cfg); cfg.update(vover)
                x = E.simulate_exit_profitgate(code, d, e['buy_price'], e['buy_hm'], cfg)
                if not x['in_sample']:
                    continue
                gated_this = True
                net = E.trade_return_from_gross(x.get('gross'), cfg)
                gated_trades[vkey].append(dict(
                    date=d, code=code, name=p.get('name', ''),
                    gate_d8=x['gate_d8'], gate_price=round(x['gate_price'], 4),
                    sell_d8=x['sell_d8'], exit_reason=x['exit_reason'],
                    hold_days=x['hold_days'], hold_days_after_gate=x['hold_days_after_gate'],
                    net_return=round(net, 5) if net is not None else None,
                    peak_return=round(x['peak_return'], 5),
                    gate_capture=round(x['gate_capture'], 5) if x['gate_capture'] is not None else None,
                    giveback=round(x['giveback'], 5) if x['giveback'] is not None else None,
                    sell_blocked_count=x['sell_blocked_count'],
                ))
            if gated_this:
                n_gated += 1
        if (k + 1) % log_every == 0:
            print("  %d/%d days cand=%d filled=%d gated=%d %.0fs" % (
                k + 1, len(all_days), n_candidates, n_filled, n_gated, time.time() - t0), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    _write(gated_trades, entry_reasons, n_candidates, n_filled, n_gated, gate, tag, all_days)


def _conc(net):
    pos = np.sort(net[net > 0])[::-1]; tp = pos.sum() if len(pos) else 0.0
    return round((pos[:10].sum() / tp) if tp > 0 else 0.0, 4)


def _metrics(tdf):
    r = tdf['net_return'].dropna().values
    if len(r) == 0:
        return {}
    wins = r[r > 0]; losses = r[r <= 0]
    pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float('inf')
    cap = tdf['gate_capture'].dropna().values
    gb = tdf['giveback'].dropna().values
    return dict(
        n=len(r), win_rate=round((r > 0).mean(), 4),
        mean_ret=round(float(r.mean()), 5), median_ret=round(float(np.median(r)), 5),
        profit_factor=(round(pf, 3) if pf != float('inf') else 'inf'),
        gate_capture=round(float(np.mean(cap)), 4) if len(cap) else 0.0,
        gate_capture_med=round(float(np.median(cap)), 4) if len(cap) else 0.0,
        giveback_mean=round(float(np.mean(gb)), 4) if len(gb) else 0.0,
        giveback_med=round(float(np.median(gb)), 4) if len(gb) else 0.0,
        avg_hold_after_gate=round(float(tdf['hold_days_after_gate'].mean()), 2),
        max_win=round(float(r.max()), 4), skew=round(float((((r - r.mean()) / r.std()) ** 3).mean()), 3) if r.std() > 0 else 0.0,
        top10_win_share=_conc(r),
        sell_blocked_days=int(tdf['sell_blocked_count'].sum()),
    )


def _write(gated_trades, entry_reasons, n_candidates, n_filled, n_gated, gate, tag, all_days):
    pre = os.path.join(OUT_DIR, "project1_phaseA_step2pg%d_%s" % (int(gate * 100), tag))
    rows = []; exit_dist = {}
    for vkey, vname, _ in VARIANTS:
        tdf = pd.DataFrame(gated_trades[vkey])
        tdf.to_csv(pre + "_%s_trades.csv" % vkey, index=False, encoding="utf-8-sig")
        m = _metrics(tdf); m['variant'] = vname; m['vkey'] = vkey; rows.append(m)
        exit_dist[vkey] = (tdf.groupby('exit_reason').size() / len(tdf)).round(3).to_dict() if len(tdf) else {}
    cmp = pd.DataFrame(rows).set_index('vkey')
    cols = ['variant', 'n', 'gate_capture', 'gate_capture_med', 'giveback_mean', 'giveback_med',
            'mean_ret', 'median_ret', 'profit_factor', 'win_rate', 'max_win', 'skew',
            'avg_hold_after_gate', 'top10_win_share', 'sell_blocked_days']
    cmp[cols].to_csv(pre + "_compare.csv", encoding="utf-8-sig")

    er_total = sum(entry_reasons.values()); filled = entry_reasons.get('filled', 0)
    gate_rate = round(n_gated / n_filled, 4) if n_filled else 0.0
    avail = dict(candidates=n_candidates, filled=filled,
                 fill_rate=round(filled / er_total, 4) if er_total else 0,
                 buy_skip_limit_up_rate=round(entry_reasons.get('buy_skip_limit_up', 0) / er_total, 4) if er_total else 0,
                 n_gated=n_gated, gate_rate=gate_rate)
    _report(pre + "_report.md", tag, gate, cmp, exit_dist, avail, all_days)

    print("\n" + "=" * 96)
    print("STEP2 回吐侧 移动止盈敏感性 gate=+%.0f%% (%s)  [事前门槛筛样本;禁写'最优参数';负基座不转正]" % (gate * 100, tag))
    print("=" * 96)
    print(" 进场共用: 候选%d filled=%d(%.1f%%) | 触及gate样本=%d (占filled %.1f%%)" % (
        n_candidates, filled, avail['fill_rate'] * 100, n_gated, gate_rate * 100))
    print("-" * 96)
    print("%-16s %5s %8s %8s %8s %7s %6s %8s %7s" % (
        "变体", "n", "大肉捕获", "捕获中位", "回吐均", "均收益", "PF", "gate后持", "skew"))
    for vkey, vname, _ in VARIANTS:
        m = cmp.loc[vkey]
        print("%-16s %5d %7.1f%% %7.1f%% %7.1f%% %6.2f%% %6s %7.1f %7.2f" % (
            vname, m['n'], m['gate_capture'] * 100, m['gate_capture_med'] * 100, m['giveback_mean'] * 100,
            m['mean_ret'] * 100, str(m['profit_factor']), m['avg_hold_after_gate'], m['skew']))
    print("-" * 96)
    print(" 核心:在'已证明能涨(触及+%.0f%%)'的票上,哪个变体 大肉捕获↑ + 回吐↓。禁写最优参数。" % (gate * 100))
    print("=" * 96)
    print("输出: %s_{compare,report,<variant>_trades}.*" % pre)


def _report(path, tag, gate, cmp, exit_dist, avail, all_days):
    L = []; A = L.append
    A("# Project1 Phase A — Step2 回吐侧 移动止盈敏感性 (gate=+%.0f%%, %s)\n" % (gate * 100, tag))
    A("> **★命门:样本用事前浮盈门槛筛(close/buy-1 首次≥+%.0f%%,当场可知),严禁用事后峰值筛。**" % (gate * 100))
    A("> 前段(gate前)出场不变=硬止损-7%%+MA5破位N=3;gate后MA5关、切被测移动止盈变体(+硬止损floor+20天封顶)。")
    A("> **护栏:只写'回撤松紧对大肉捕获的敏感性',禁写'最优参数'。这是'已涨到+%.0f%%子样本'的赔率结构,"
      "不代表整体盈利——整体正收益仍需选股(负基座)。**" % (gate * 100))
    A("> 同一批'触及gate'样本对所有变体完全相同(前段规则一致),干净对比 gate 后回撤松紧。\n")
    A("## 样本与成交可得性")
    A("- 候选 %d / filled %d (%.1f%%) / 涨停买不到 %.1f%%" % (
        avail['candidates'], avail['filled'], avail['fill_rate'] * 100, avail['buy_skip_limit_up_rate'] * 100))
    A("- **触及 gate(+%.0f%%)样本 = %d 只,占 filled 的 %.1f%%**(所有变体共用此样本)\n" % (
        gate * 100, avail['n_gated'], avail['gate_rate'] * 100))
    A("## 移动止盈变体对比(仅触及gate样本)")
    A("| 变体 | n | 大肉捕获率 | 捕获中位 | 回吐均 | 回吐中位 | 均收益 | 中位 | PF | 胜率 | 最大单笔 | skew | gate后持天 | top10盈 |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for vkey, vname, _ in VARIANTS:
        m = cmp.loc[vkey]
        flag = " 🔴" if float(m['top10_win_share']) >= 0.5 else ""
        A("| %s | %d | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.2f%% | %.2f%% | %s | %.1f%% | %.1f%% | %.2f | %.1f | %.0f%%%s |" % (
            vname, m['n'], m['gate_capture'] * 100, m['gate_capture_med'] * 100,
            m['giveback_mean'] * 100, m['giveback_med'] * 100, m['mean_ret'] * 100, m['median_ret'] * 100,
            str(m['profit_factor']), m['win_rate'] * 100, m['max_win'] * 100, m['skew'],
            m['avg_hold_after_gate'], m['top10_win_share'] * 100, flag))
    A("\n> 大肉捕获率 = (卖价 - gate价)/(峰值 - gate价):gate 之后这段可得涨幅,吃到多少。回吐 = (峰值-卖价)/峰值。")
    A("> 核心权衡:更松(dd20)大肉捕获↑但回吐也↑、遇假突破亏更多;更紧(dd10)回吐↓但常被小回撤震出、捕获↓。\n")
    A("## gate 后出场原因分布")
    for vkey, vname, _ in VARIANTS:
        ed = sorted(exit_dist[vkey].items(), key=lambda kv: -kv[1])
        A("- **%s**:%s" % (vname, ' / '.join("%s %.0f%%" % (k, v * 100) for k, v in ed)))
    A("\n## 判读留给 Wallace(逐年稳健性见 compare 交叉核对)")
    A("- 看哪个变体在'已证明能涨的票'上 大肉捕获最高 + 回吐最小,且逐年不塌(防像Step1-D那样单一regime假平台)。")
    A("- 有候选 → 冻结跑 OOS(2024-2025)验:捕获率明显恶化=过拟合,作废不回头调。")
    A("- 提醒:本表是子样本赔率结构,均收益即便转正也不代表整体策略盈利(整体仍-90%负基座,需选股)。\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", type=float, default=0.15)
    ap.add_argument("--start", default="20200101")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--tag", default="IS_2020_2023")
    args = ap.parse_args()
    run(args.gate, args.start, args.end, args.tag)
