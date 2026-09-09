# -*- coding: utf-8 -*-
"""Project1 Phase A —— Step 0.5 出场哲学对比(3组,护栏版)。

同一批 top12 全进票(候选池/进场闸/成交口径/成本 完全不变),只换出场规则:
  组1 trend_hold   趋势持有(当前默认:硬止损-7% / MA5破位N=3 / 两段式移动止盈 / 20天天花板)
  组2 v35_short    V3.5短打(实盘参数只读提取:TP1+9%卖1/3 / TP2+16%卖1/2 / 7%移动止损 / 20天封顶)
  组3 fixed_hold   基准(固定持有5天,无止损止盈,纯对照)

比:大肉捕获率 / 盈亏比 / 收益右偏 / 平均持仓 / 出场原因分布 / 成交可得性 / 贡献集中度。

★护栏:结论只写"参数敏感性 + 出场哲学对比",禁写"最优参数""收益改善有效"。
        贡献集中度:少数票撑起收益 → 标红。
效率:池+进场只算一次,3组共用,仅出场分3引擎跑。

只读 minute/cache/V3.5参数;只写 research/project1_phaseA/out。不碰实盘代码/候选池/不装包。
用法:py -3.10 run_step05.py --start 20200101 --end 20231231 --tag IS_2020_2023
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
GROUPS = [('trend_hold', '组1趋势持有'), ('v35_short', '组2_V3.5短打'), ('fixed_hold', '组3固定持有5天')]


def run(start, end, tag, log_every=80):
    PR._load()
    all_days = [d for d in PR.trade_days() if start <= d <= end]
    print("[step0.5] tag=%s days=%d (%s..%s)" % (tag, len(all_days), all_days[0], all_days[-1]), flush=True)

    base_cfg = dict(E.DEFAULT_CFG)
    trades = {g: [] for g, _ in GROUPS}
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
            for style, _name in GROUPS:
                cfg = dict(base_cfg); cfg['exit_style'] = style
                if style == 'fixed_hold':
                    cfg['fixed_hold_days'] = 5
                x = E.simulate_exit_dispatch(code, d, e['buy_price'], e['buy_hm'], cfg)
                net = E.trade_return_from_gross(x.get('gross'), cfg)
                trades[style].append(dict(
                    date=d, code=code, name=p.get('name', ''), tpl=p['tpl'],
                    buy_price=round(e['buy_price'], 4),
                    sell_d8=x['sell_d8'], exit_reason=x['exit_reason'], hold_days=x['hold_days'],
                    net_return=round(net, 5) if net is not None else None,
                    peak_return=round(x['peak_return'], 5),
                    tp1_hit=x.get('tp1_hit', 0), tp2_hit=x.get('tp2_hit', 0),
                    day0_untradable_risk=int(x['day0_untradable_risk']),
                    sell_blocked_count=x['sell_blocked_count'],
                ))
        if (k + 1) % log_every == 0:
            print("  %d/%d days  cand=%d  %.0fs" % (k + 1, len(all_days), n_candidates, time.time() - t0), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    _write_compare(trades, entry_reasons, n_candidates, tag, all_days)


def _concentration(net):
    """贡献集中度:top10 盈利票占总盈利% / top10 亏损票占总亏损%。"""
    pos = np.sort(net[net > 0])[::-1]
    neg = np.sort(net[net < 0])   # 最负在前
    tot_pos = pos.sum() if len(pos) else 0.0
    tot_neg = neg.sum() if len(neg) else 0.0
    top10_pos = pos[:10].sum() if len(pos) else 0.0
    top10_neg = neg[:10].sum() if len(neg) else 0.0
    return dict(
        top10_win_share=(top10_pos / tot_pos) if tot_pos > 0 else 0.0,
        top10_loss_share=(top10_neg / tot_neg) if tot_neg < 0 else 0.0,
        n_win=int((net > 0).sum()), n_loss=int((net < 0).sum()),
    )


def _metrics(tdf):
    r = tdf['net_return'].dropna().values
    if len(r) == 0:
        return {}
    wins = r[r > 0]; losses = r[r <= 0]
    pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float('inf')
    mu, sd = r.mean(), r.std()
    skew = float((((r - mu) / sd) ** 3).mean()) if sd > 0 else 0.0
    cap = []
    for _, row in tdf.iterrows():
        if row['peak_return'] and row['peak_return'] > 0 and row['net_return'] is not None:
            cap.append(max(0.0, row['net_return']) / row['peak_return'])
    conc = _concentration(r)
    return dict(
        n_trades=len(r), win_rate=round((r > 0).mean(), 4),
        mean_ret=round(float(mu), 5), median_ret=round(float(np.median(r)), 5),
        profit_factor=(round(pf, 3) if pf != float('inf') else 'inf'),
        avg_win=round(float(wins.mean()), 5) if len(wins) else 0.0,
        avg_loss=round(float(losses.mean()), 5) if len(losses) else 0.0,
        skew=round(skew, 3), max_win=round(float(r.max()), 4), min_ret=round(float(r.min()), 4),
        bigmeat_capture=round(float(np.mean(cap)), 4) if cap else 0.0,
        avg_hold=round(float(tdf['hold_days'].mean()), 2),
        median_hold=int(tdf['hold_days'].median()),
        top10_win_share=round(conc['top10_win_share'], 4),
        top10_loss_share=round(conc['top10_loss_share'], 4),
        sell_blocked_days=int(tdf['sell_blocked_count'].sum()),
        day0_untradable_risk=int(tdf['day0_untradable_risk'].sum()),
    )


def _write_compare(trades, entry_reasons, n_candidates, tag, all_days):
    pre = os.path.join(OUT_DIR, "project1_phaseA_step05_%s" % tag)
    rows = []
    exit_dist = {}
    for style, name in GROUPS:
        tdf = pd.DataFrame(trades[style])
        tdf.to_csv(pre + "_%s_trades.csv" % style, index=False, encoding="utf-8-sig")
        m = _metrics(tdf); m['group'] = name; m['style'] = style
        rows.append(m)
        ed = (tdf.groupby('exit_reason').size() / len(tdf)).round(3).to_dict() if len(tdf) else {}
        exit_dist[style] = ed
    cmp = pd.DataFrame(rows).set_index('style')
    cols = ['group', 'n_trades', 'win_rate', 'mean_ret', 'median_ret', 'profit_factor',
            'avg_win', 'avg_loss', 'skew', 'max_win', 'bigmeat_capture', 'avg_hold', 'median_hold',
            'top10_win_share', 'top10_loss_share', 'sell_blocked_days', 'day0_untradable_risk']
    cmp = cmp[cols]
    cmp.to_csv(pre + "_compare.csv", encoding="utf-8-sig")

    # 成交可得性(三组共用进场)
    er_total = sum(entry_reasons.values())
    filled = entry_reasons.get('filled', 0)
    def pct(x): return round(x / er_total, 4) if er_total else 0.0
    avail = dict(candidates=n_candidates, filled=filled, fill_rate=pct(filled),
                 buy_skip_limit_up=entry_reasons.get('buy_skip_limit_up', 0),
                 buy_skip_limit_up_rate=pct(entry_reasons.get('buy_skip_limit_up', 0)),
                 buy_skip_no_signal=entry_reasons.get('buy_skip_no_signal', 0),
                 buy_skip_suspended=entry_reasons.get('buy_skip_suspended', 0))

    _write_report(pre + "_report.md", tag, cmp, exit_dist, avail, all_days)

    # 控制台对比
    print("\n" + "=" * 78)
    print("STEP0.5 出场哲学对比 (%s)  [同批全进票,只换出场;禁写'最优参数']" % tag)
    print("=" * 78)
    print(" 进场共用: 候选%d filled=%d(%.1f%%) 涨停买不到%.1f%% no_signal=%d" % (
        n_candidates, filled, avail['fill_rate'] * 100,
        avail['buy_skip_limit_up_rate'] * 100, avail['buy_skip_no_signal']))
    print("-" * 78)
    hdr = "%-16s %6s %6s %7s %6s %7s %7s %6s %6s %6s" % (
        "组", "n", "胜率", "均收益", "PF", "大肉捕", "右偏skew", "均持", "top10盈", "top10亏")
    print(hdr)
    for style, name in GROUPS:
        m = cmp.loc[style]
        print("%-16s %6d %5.1f%% %6.2f%% %6s %6.2f %7.2f %5.1f %5.0f%% %5.0f%%" % (
            name, m['n_trades'], m['win_rate'] * 100, m['mean_ret'] * 100, str(m['profit_factor']),
            m['bigmeat_capture'], m['skew'], m['avg_hold'],
            m['top10_win_share'] * 100, m['top10_loss_share'] * 100))
    print("-" * 78)
    for style, name in GROUPS:
        top = sorted(exit_dist[style].items(), key=lambda kv: -kv[1])[:4]
        print(" %-16s 出场: %s" % (name, ' '.join("%s=%.0f%%" % (k, v * 100) for k, v in top)))
    print("=" * 78)
    print("输出: %s_{compare,report,<style>_trades}.*" % pre)


def _write_report(path, tag, cmp, exit_dist, avail, all_days):
    L = []; A = L.append
    A("# Project1 Phase A — Step0.5 出场哲学对比 (%s)\n" % tag)
    A("> 同一批 top12 全进票(候选池/进场闸/成交口径/成本 完全不变),只换出场规则,对比出场哲学。")
    A("> **护栏:本文只回答'趋势持有方向对不对 + 出场哲学差异',禁止写'最优参数'/'收益改善有效'。**")
    A("> 不含AI选股层(只能forward paper验);单票等权模拟,非实盘仓位结论;2026未回看(Step7才碰)。\n")
    A("## 三组定义")
    A("- **组1 趋势持有**(当前默认):硬止损-7% / MA5破位N=3 / 两段式移动止盈(切换+25%,回撤15%→12/10/8%) / 20天天花板。")
    A("- **组2 V3.5短打**:参数只读提取自 `C:\\quant_project\\QMT_clean\\archive\\archive_xtquant_v35\\qmt_v35_final.py` "
      "(TP1=+9%卖1/3 / TP2=+16%卖1/2 / 7%移动止损 / 20天封顶;TP1后重置peak)。"
      "**注:实盘V3.5用intraday high触发TP、另有Dragon 3.5%硬止损;本组用close口径、只含7%移动止损,"
      "是'V3.5短打哲学的保守下界',非tick级精确复现。TP2实盘=+16%(Wallace口述+15%,以代码为准)。**")
    A("- **组3 固定持有5天**:买入后固定持有5个交易日收盘卖出,无止损止盈(纯对照基准)。\n")
    A("## 成交可得性(三组共用进场)")
    A("- 候选 %d / filled %d (%.1f%%) / 涨停买不到 %.1f%% / no_signal %d / 停牌 %d" % (
        avail['candidates'], avail['filled'], avail['fill_rate'] * 100,
        avail['buy_skip_limit_up_rate'] * 100, avail['buy_skip_no_signal'], avail['buy_skip_suspended']))
    A("- 跌停卖不出(天)按组见下表 sell_blocked_days 列。\n")
    A("## 对比主表")
    A("| 组 | 笔数 | 胜率 | 均收益/笔 | 中位 | PF | 平均盈 | 平均亏 | 右偏skew | 最大单笔 | 大肉捕获 | 均持天 | top10盈占 | top10亏占 | 卖阻天 |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for style, name in GROUPS:
        m = cmp.loc[style]
        flag = " 🔴" if float(m['top10_win_share']) >= 0.5 else ""
        A("| %s | %d | %.1f%% | %.2f%% | %.2f%% | %s | %.2f%% | %.2f%% | %.2f | %.1f%% | %.2f | %.1f | %.0f%%%s | %.0f%% | %d |" % (
            name, m['n_trades'], m['win_rate'] * 100, m['mean_ret'] * 100, m['median_ret'] * 100,
            str(m['profit_factor']), m['avg_win'] * 100, m['avg_loss'] * 100, m['skew'],
            m['max_win'] * 100, m['bigmeat_capture'], m['avg_hold'],
            m['top10_win_share'] * 100, flag, m['top10_loss_share'] * 100, m['sell_blocked_days']))
    A("")
    A("## 出场原因分布")
    for style, name in GROUPS:
        ed = sorted(exit_dist[style].items(), key=lambda kv: -kv[1])
        A("- **%s**:%s" % (name, ' / '.join("%s %.0f%%" % (k, v * 100) for k, v in ed)))
    A("")
    A("## 贡献集中度(护栏第4条:少数票撑起收益要标红)")
    A("- top10盈占 ≥50% 标 🔴(收益由极少数票撑起,不稳健)。三组对比见主表 top10盈占列。\n")
    A("## 判读框架(留给 Wallace 定'趋势持有方向站不站得住')")
    A("- 若组1 大肉捕获率/右偏/最大单笔 明显高于组2/组3,而胜率不必更高 → 趋势持有在'赔率端'方向成立(让肉签跑)。")
    A("- 若组2 短打 胜率更高但大肉捕获低、最大单笔被+16%封顶 → 短打把肉签过早了结,右偏被削平。")
    A("- 若组3 固定持有 与两者接近 → 出场规则整体贡献有限,方向要重新想。")
    A("- **三组都在负基座上(全进无选股),看的是相对结构差异,不是谁把-90%调正。**")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20200101")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--tag", default="IS_2020_2023")
    args = ap.parse_args()
    run(args.start, args.end, args.tag)
