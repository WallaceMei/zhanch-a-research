# -*- coding: utf-8 -*-
"""Project1 Phase A —— Step 0 baseline 运行器(全默认参数,跑 IS 2020-2023)。

流程(摘掉AI层,top12 全进等权):
  每交易日 → dragon_pool(date) top12 → 逐只 try_entry(完整signal_time口径)
          → 过闸票 simulate_exit(机械出场) → 记 trade
输出 P0 四文件 + 重点成交可得性统计(buy_unfilled/limit_up、sell_blocked、price_proxy)。

用法:
  py -3.10 run_step0.py --start 20200101 --end 20231231 --tag IS_2020_2023
  py -3.10 run_step0.py --start 20230101 --end 20230331 --tag SMOKE   # 小样本烟测

只读 minute/cache,只写本研究目录 out/。不碰实盘/不改候选池/不装包。
"""
import os
import sys
import time
import argparse
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_repro as PR
import engine_phaseA as E

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def run(start, end, tag, cfg=None, log_every=40):
    cfg = cfg or dict(E.DEFAULT_CFG)
    PR._load()
    all_days = [d for d in PR.trade_days() if start <= d <= end]
    print("[run] tag=%s days=%d (%s..%s) entry_mode=%s" % (
        tag, len(all_days), all_days[0] if all_days else '-',
        all_days[-1] if all_days else '-', cfg['entry_mode']), flush=True)

    trades = []
    entry_reasons = Counter()      # 全部进场尝试的归类(含未成交)
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
            e = E.try_entry(code, d, ctx['prev_close'], cfg)
            entry_reasons[e['buy_reason']] += 1
            if not e['filled']:
                continue
            x = E.simulate_exit(code, d, e['buy_price'], e['buy_hm'], cfg)
            ret = E.trade_return(e['buy_price'], x['sell_price'], cfg)
            trades.append(dict(
                date=d, code=code, name=p.get('name', ''), tpl=p['tpl'],
                dragon_score=round(p['dragon_score'], 4), open_ratio=round(p['open_ratio'], 4),
                signal_hm=e['signal_hm'], buy_hm=e['buy_hm'],
                buy_open_raw=round(e.get('buy_open_raw', 0), 3), buy_price=round(e['buy_price'], 4),
                sell_d8=x['sell_d8'], sell_hm=x['sell_hm'],
                sell_price=round(x['sell_price'], 4) if x['sell_price'] else None,
                exit_reason=x['exit_reason'], hold_days=x['hold_days'],
                net_return=round(ret, 5) if ret is not None else None,
                peak_return=round(x['peak_return'], 5),
                day0_untradable_risk=int(x['day0_untradable_risk']),
                sell_blocked_count=x['sell_blocked_count'],
                price_proxy_flag=int(e['price_proxy_flag'] or x['sell_proxy_flag']),
            ))
        if (k + 1) % log_every == 0:
            print("  %d/%d days  trades=%d  cand=%d  %.0fs" % (
                k + 1, len(all_days), len(trades), n_candidates, time.time() - t0), flush=True)

    tdf = pd.DataFrame(trades)
    os.makedirs(OUT_DIR, exist_ok=True)
    _write_outputs(tdf, entry_reasons, n_candidates, tag, cfg, all_days)
    return tdf, entry_reasons, n_candidates


# ----------------------------------------------------------------------------
# 指标 + 输出
# ----------------------------------------------------------------------------
def _equity_curve(tdf):
    """单票等权日内MTM篮子(日度再平衡,等权持有当日所有在仓票)。返回 (equity_df, daily_ret)。
    每笔:day0 成本=buy_price,其后用日线 close MTM,sell日用 sell_price。日收益=等权均值。"""
    panel = PR.panel()
    per_trade_daily = []   # (d8, trade_id, daily_ret)
    for tid, r in tdf.iterrows():
        code = r['code']; bd = r['date']; sd = r['sell_d8']
        if sd is None or r['sell_price'] is None:
            continue
        p = panel.get(code)
        if p is None:
            continue
        hold_days = [d for d in PR.trade_days() if bd <= d <= sd]
        prev_val = r['buy_price']
        for d in hold_days:
            if d == sd:
                val = r['sell_price']
            else:
                if d in p.index:
                    val = float(p.loc[d, 'close'])
                else:
                    val = prev_val   # 停牌:平值
            dr = val / prev_val - 1.0 if prev_val else 0.0
            per_trade_daily.append((d, tid, dr))
            prev_val = val
    if not per_trade_daily:
        return pd.DataFrame(), pd.Series(dtype=float)
    dd = pd.DataFrame(per_trade_daily, columns=['d8', 'tid', 'ret'])
    port = dd.groupby('d8')['ret'].mean().sort_index()
    equity = (1 + port).cumprod()
    return equity, port


def _max_drawdown(equity):
    if len(equity) == 0:
        return 0.0
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def _write_outputs(tdf, entry_reasons, n_candidates, tag, cfg, all_days):
    pre = os.path.join(OUT_DIR, "project1_phaseA_%s" % tag)

    # ---- trades.csv ----
    tdf.to_csv(pre + "_trades.csv", index=False, encoding="utf-8-sig")

    n_trades = len(tdf)
    rets = tdf['net_return'].dropna().values if n_trades else np.array([])
    wins = rets[rets > 0]; losses = rets[rets <= 0]
    win_rate = len(wins) / len(rets) if len(rets) else 0.0
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0
    pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float('inf')
    # 大肉捕获率 = captured_R/maxR (maxR>0 时);captured_R≈net_return,maxR≈peak_return
    cap = []
    for _, r in tdf.iterrows():
        if r['peak_return'] and r['peak_return'] > 0 and r['net_return'] is not None:
            cap.append(max(0.0, r['net_return']) / r['peak_return'])
    bigmeat_capture = float(np.mean(cap)) if cap else 0.0

    equity, port = _equity_curve(tdf)
    total_ret = float(equity.iloc[-1] - 1.0) if len(equity) else 0.0
    mdd = _max_drawdown(equity)
    sharpe = float(port.mean() / port.std() * np.sqrt(252)) if len(port) > 1 and port.std() > 0 else 0.0

    # ---- exit_reason_stats.csv ----
    er_rows = []
    if n_trades:
        for reason, g in tdf.groupby('exit_reason'):
            er_rows.append(dict(exit_reason=reason, n=len(g),
                                pct=round(len(g) / n_trades, 4),
                                avg_net_return=round(g['net_return'].mean(), 5),
                                avg_hold_days=round(g['hold_days'].mean(), 2),
                                avg_peak_return=round(g['peak_return'].mean(), 5)))
    er = pd.DataFrame(er_rows).sort_values('n', ascending=False) if er_rows else pd.DataFrame()
    er.to_csv(pre + "_exit_reason_stats.csv", index=False, encoding="utf-8-sig")

    # ---- 成交可得性(重点)----
    filled = int(entry_reasons.get('filled', 0))
    er_total = sum(entry_reasons.values())
    def pct(x): return round(x / er_total, 4) if er_total else 0.0
    n_skip_limit_up = entry_reasons.get('buy_skip_limit_up', 0)
    n_no_signal = entry_reasons.get('buy_skip_no_signal', 0)
    n_suspended = entry_reasons.get('buy_skip_suspended', 0)
    n_late = entry_reasons.get('buy_late_unfilled', 0)
    n_sell_blocked = int(tdf['sell_blocked_count'].sum()) if n_trades else 0
    n_sell_blocked_trades = int((tdf['sell_blocked_count'] > 0).sum()) if n_trades else 0
    n_proxy = int(tdf['price_proxy_flag'].sum()) if n_trades else 0
    n_day0risk = int(tdf['day0_untradable_risk'].sum()) if n_trades else 0

    avail = dict(
        candidates=n_candidates, entry_attempts=er_total, filled=filled,
        fill_rate=pct(filled),
        buy_skip_limit_up=n_skip_limit_up, buy_skip_limit_up_rate=pct(n_skip_limit_up),
        buy_skip_no_signal=n_no_signal, buy_skip_no_signal_rate=pct(n_no_signal),
        buy_skip_suspended=n_suspended, buy_late_unfilled=n_late,
        sell_blocked_limit_down_days=n_sell_blocked,
        sell_blocked_trades=n_sell_blocked_trades,
        price_proxy_flag=n_proxy,
        price_proxy_rate=round(n_proxy / n_trades, 4) if n_trades else 0.0,
        day0_untradable_risk=n_day0risk,
    )

    # ---- summary.csv ----
    summ = dict(
        tag=tag, entry_mode=cfg['entry_mode'],
        period="%s..%s" % (all_days[0], all_days[-1]) if all_days else '-',
        n_trading_days=len(all_days),
        total_return=round(total_ret, 4), max_drawdown=round(mdd, 4), sharpe=round(sharpe, 3),
        n_trades=n_trades, win_rate=round(win_rate, 4),
        avg_win=round(avg_win, 5), avg_loss=round(avg_loss, 5),
        profit_factor=round(pf, 3) if pf != float('inf') else 'inf',
        bigmeat_capture=round(bigmeat_capture, 4),
        avg_hold_days=round(float(tdf['hold_days'].mean()), 2) if n_trades else 0,
        median_hold_days=int(tdf['hold_days'].median()) if n_trades else 0,
        **avail,
    )
    pd.DataFrame([summ]).to_csv(pre + "_summary.csv", index=False, encoding="utf-8-sig")

    # ---- report.md ----
    _write_report(pre + "_report.md", tag, cfg, summ, er, avail, all_days)

    # ---- 控制台重点三数 ----
    print("\n" + "=" * 64)
    print("STEP0 成交可得性(决定引擎跑不跑得通,重于调参)")
    print("=" * 64)
    print(" 候选(top12累计)        : %d" % n_candidates)
    print(" 进场尝试               : %d" % er_total)
    print(" 成交 filled            : %d  (fill_rate=%.1f%%)" % (filled, avail['fill_rate'] * 100))
    print(" 1) 涨停买不到 limit_up  : %d  (%.1f%% of 尝试)" % (n_skip_limit_up, avail['buy_skip_limit_up_rate'] * 100))
    print("    未触发信号 no_signal : %d  (%.1f%%)" % (n_no_signal, avail['buy_skip_no_signal_rate'] * 100))
    print("    停牌 suspended       : %d   买入超时 late: %d" % (n_suspended, n_late))
    print(" 2) 跌停卖不出(天数)     : %d   (涉及 %d 笔)" % (n_sell_blocked, n_sell_blocked_trades))
    print(" 3) price_proxy_flag     : %d  (%.1f%% of 成交)" % (n_proxy, avail['price_proxy_rate'] * 100))
    print("    day0_untradable_risk : %d" % n_day0risk)
    print("-" * 64)
    print(" P0: 总收益=%.1f%% 回撤=%.1f%% Sharpe=%.2f 交易=%d 胜率=%.1f%% 盈亏比=%s 大肉捕获=%.2f 持仓均%.1f天" % (
        total_ret * 100, mdd * 100, sharpe, n_trades, win_rate * 100,
        summ['profit_factor'], bigmeat_capture, summ['avg_hold_days']))
    print("=" * 64)
    print("输出: %s_{summary,trades,exit_reason_stats,report}.* " % pre)


def _write_report(path, tag, cfg, summ, er, avail, all_days):
    lines = []
    A = lines.append
    A("# Project1 Phase A — Step0 baseline 报告 (%s)\n" % tag)
    A("> 自动生成。本回测**不含 AI 选股层**,验证的是 战车A打板候选池 + 机械VWAP进场闸 + 机械出场引擎。")
    A("> AI 主管选股层只能在 forward paper trading 阶段验证(本回测内不可声称已验证)。")
    A("> 2026 已被授权用于本项目出场引擎回看,不再是本项目干净 holdout;Step0 仅跑 IS(2020-2023)。")
    A("> 单票等权模拟(未读到实盘仓位配置),不作实盘仓位结论。\n")

    A("## 关键口径与已知偏差")
    A("- **数据源偏差**:warehouse 日线/竞价元库已被瘦身到只剩 600519.SH,无法用作候选池复现。"
      "本回测的**全量日线+竞价由本地 canonical/minute_1m 聚合而来**(竞价=09:30首根,正是原 warehouse auction 衍生源;"
      "日线为分钟标准聚合、不复权同 QMT 口径)。候选池打分逻辑(repro_core 的 L5/L6)零改动。"
      "代价:'15/15 对聚宽日志'那次校验无法在当前环境重放。")
    A("- **成本(定值)**:买卖滑点各 0.08%、佣金万2.5双边、印花税卖 0.05%。"
      "实盘主策略仅 `set_slippage(FixedSlippage(0.02))`(2分钱定值滑点),两者口径不同——"
      "定值滑点对低价股更贵、高价股更便宜;此偏差作已知项记录,paper 阶段再校准成本模型。")
    A("- **进场**:完整 signal_time 口径(9:30-10:30 首次 VWAP站稳+回踩不破,下一根 open 买入,10:45 截止);top12 过闸票全进等权。")
    A("- **涨跌停价**:`round(prev_close×1.1/0.9, 2)` 主板10%近似;ST(5%) 未单列(打板池含ST极少),作已知近似。")
    A("- **MA5**:用前一交易日已知 MA5_prev,不偷看当日收盘。\n")

    A("## P0 指标")
    A("| 指标 | 值 |")
    A("|---|---|")
    A("| 期间 | %s (%d 交易日) |" % (summ['period'], summ['n_trading_days']))
    A("| 总收益 | %.1f%% |" % (summ['total_return'] * 100))
    A("| 最大回撤 | %.1f%% |" % (summ['max_drawdown'] * 100))
    A("| Sharpe | %.2f |" % summ['sharpe'])
    A("| 交易次数 | %d |" % summ['n_trades'])
    A("| 胜率 | %.1f%% |" % (summ['win_rate'] * 100))
    A("| 盈亏比(PF) | %s |" % summ['profit_factor'])
    A("| 平均盈/亏 | +%.2f%% / %.2f%% |" % (summ['avg_win'] * 100, summ['avg_loss'] * 100))
    A("| 大肉捕获率 | %.2f |" % summ['bigmeat_capture'])
    A("| 平均/中位持仓天数 | %.1f / %d |" % (summ['avg_hold_days'], summ['median_hold_days']))
    A("")

    A("## 成交可得性(Step0 重点 — 决定引擎在打板池上跑不跑得通)")
    A("| 项 | 数 | 占比 |")
    A("|---|---:|---:|")
    A("| 候选(top12累计) | %d | — |" % avail['candidates'])
    A("| 进场尝试 | %d | — |" % avail['entry_attempts'])
    A("| **成交 filled** | %d | %.1f%% |" % (avail['filled'], avail['fill_rate'] * 100))
    A("| ① 涨停买不到 buy_skip_limit_up | %d | %.1f%% |" % (avail['buy_skip_limit_up'], avail['buy_skip_limit_up_rate'] * 100))
    A("| 未触发信号 buy_skip_no_signal | %d | %.1f%% |" % (avail['buy_skip_no_signal'], avail['buy_skip_no_signal_rate'] * 100))
    A("| 停牌 buy_skip_suspended | %d | — |" % avail['buy_skip_suspended'])
    A("| 买入超时 buy_late_unfilled | %d | — |" % avail['buy_late_unfilled'])
    A("| ② 跌停卖不出(天数 / 涉及笔数) | %d / %d | — |" % (avail['sell_blocked_limit_down_days'], avail['sell_blocked_trades']))
    A("| ③ price_proxy_flag(用close替代open) | %d | %.1f%% of成交 |" % (avail['price_proxy_flag'], avail['price_proxy_rate'] * 100))
    A("| day0_untradable_risk(T+1当日触发未卖) | %d | — |" % avail['day0_untradable_risk'])
    A("")

    if len(er):
        A("## 出场原因占比")
        A("| 原因 | 笔数 | 占比 | 平均净收益 | 平均持仓 | 平均峰值 |")
        A("|---|---:|---:|---:|---:|---:|")
        for _, r in er.iterrows():
            A("| %s | %d | %.1f%% | %.2f%% | %.1f | %.2f%% |" % (
                r['exit_reason'], r['n'], r['pct'] * 100, r['avg_net_return'] * 100,
                r['avg_hold_days'], r['avg_peak_return'] * 100))
        A("")

    A("## Step0 判读提示")
    A("- buy_skip_limit_up 畸高(打板池次日高开/一字常见)→ 进场闸在打板池上结构性买不到 → 先修/重审进场,不进调参。")
    A("- sell_blocked 频繁 → 出场在跌停板上系统性卖不出 → 赔率端统计失真。")
    A("- price_proxy 高 → 分钟数据缺口多,成交价不可靠。")
    A("- 以上数字合理后,才进入 Step1~7 出场参数敏感性扫描。\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20200101")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--tag", default="IS_2020_2023")
    ap.add_argument("--entry_mode", default="full", choices=["full", "simple"])
    ap.add_argument("--trail_mode", default="two_stage", choices=["two_stage", "single"])
    ap.add_argument("--trail_single", type=float, default=0.10)
    args = ap.parse_args()
    cfg = dict(E.DEFAULT_CFG)
    cfg['entry_mode'] = args.entry_mode
    if args.trail_mode == "single":
        cfg['trail_mode'] = 'single'
        cfg['trail_single'] = args.trail_single
    run(args.start, args.end, args.tag, cfg=cfg)
