# -*- coding: utf-8 -*-
"""Project1 Paper — Step1 三组对照框架 + 盘后结算(不含实时、不含真AI)。

spec: docs/specs/战车A_Project1_AI选股层Paper设计_spec_v0.1.md(§9 已定配置)
目的:先验"三组对照框架"跑通、逻辑对、对照公平(唯一变量在选股)。
本步不接QMT实时、不接MiniMax、不搭web看板(Step2-4)。

框架:
  每交易日 → dragon_pool top12(repro_core零改动)
          → 三组决策器各自出"监测池"(deciders.py,唯一变量)
          → 共用进场闸(Phase A 默认 VWAP 口径,engine_phaseA.try_entry)
          → 共用出场引擎(Phase A 整机 dd10:硬止损-7%/MA5 N=3/移动止盈dd10/20天)
          → 组合记账:每只25%、最多3 slot(75%上限)、留25%现金,三组一致

对照公平保证(结构性,非事后核对):
  同一 (code, date) 的进场/出场只计算一次(共享缓存),被多组选中时引用同一结果
  → 同票同日 进场时刻/价格/出场路径 跨组必然一致,唯一差别=谁把它选进监测池。

口径备注(盘后结算版近似,接实时后消失/替换):
  - 仓位 = 买入时点组合权益(前收盘 mark)×25%;现金不足25%时用剩余现金。
  - slot 占用:买入日起到卖出日(含)整日占用,次日释放(保守;不做日内slot翻转)。
  - 同组同票在持仓期内再次被选中 → 跳过(already_held),不加仓。
  - 停牌日按平值 mark(同 Phase A)。

用法:
  py -3.10 run_step1_compare.py --start 20230101 --end 20231231 --tag IS2023
  py -3.10 run_step1_compare.py --start 20230101 --end 20230331 --tag SMOKE

只读 minute/cache,只写本目录 out/。不碰实盘/不改候选池/不装包。
"""
import os
import sys
import time
import argparse
from collections import Counter

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import pool_repro as PR          # noqa: E402
import engine_phaseA as E        # noqa: E402
from deciders import DECIDERS    # noqa: E402

OUT_DIR = os.path.join(_HERE, "out")

GROUPS = ('ai_placeholder', 'random3', 'all_in')
N_SLOTS = 3          # spec §9.2: 25%×3 = 75% 持仓上限
POS_FRAC = 0.25      # 每只 25%


def paper_cfg():
    """三组共用配置:Phase A 默认进场闸 + 整机 dd10 出场(spec §5/§9.4)。"""
    cfg = dict(E.DEFAULT_CFG)
    cfg['trail_mode'] = 'single'
    cfg['trail_single'] = 0.10
    return cfg


# ----------------------------------------------------------------------------
# 共享进出场缓存(对照公平的结构保证)
# ----------------------------------------------------------------------------
class TradeCache:
    """(code, d8) → 唯一的 entry/exit 结果。多组共选同票时引用同一份。"""

    def __init__(self, cfg):
        self.cfg = cfg
        self._cache = {}
        self.entry_reasons = Counter()

    def get(self, code, d8):
        key = (code, d8)
        if key in self._cache:
            return self._cache[key]
        ctx = E.daily_ctx(code, d8)
        if ctx is None or ctx['prev_close'] is None:
            rec = dict(filled=False, buy_reason='buy_skip_no_dailyctx')
            self.entry_reasons['buy_skip_no_dailyctx'] += 1
            self._cache[key] = rec
            return rec
        e = E.try_entry(code, d8, ctx['prev_close'], self.cfg)
        self.entry_reasons[e['buy_reason']] += 1
        if not e['filled']:
            rec = dict(filled=False, buy_reason=e['buy_reason'])
            self._cache[key] = rec
            return rec
        x = E.simulate_exit(code, d8, e['buy_price'], e['buy_hm'], self.cfg)
        net = E.trade_return(e['buy_price'], x['sell_price'], self.cfg)
        rec = dict(filled=True, buy_reason='filled',
                   signal_hm=e['signal_hm'], buy_hm=e['buy_hm'],
                   buy_price=e['buy_price'], buy_open_raw=e.get('buy_open_raw'),
                   sell_d8=x['sell_d8'], sell_hm=x['sell_hm'], sell_price=x['sell_price'],
                   exit_reason=x['exit_reason'], hold_days=x['hold_days'],
                   peak_return=x['peak_return'], net_return=net,
                   day0_untradable_risk=int(x['day0_untradable_risk']),
                   sell_blocked_count=x['sell_blocked_count'],
                   price_proxy_flag=int(x['sell_proxy_flag']))
        self._cache[key] = rec
        return rec


# ----------------------------------------------------------------------------
# 组合记账(每组一本账:现金 + 持仓,25%/slot,最多3 slot)
# ----------------------------------------------------------------------------
class Portfolio:
    def __init__(self, name):
        self.name = name
        self.cash = 1.0
        self.positions = {}     # code -> dict(value, last_px, buy_d8, sell_d8, sell_price, rec)
        self.equity_hist = []   # (d8, equity)
        self.trades = []        # 平仓记录(含权重口径)
        self.skip_log = Counter()

    def equity(self):
        return self.cash + sum(p['value'] for p in self.positions.values())

    def try_buy(self, d8, code, rec):
        """rec = TradeCache 成交记录。返回 buy 状态字符串(记入决策留痕)。"""
        if code in self.positions:
            self.skip_log['already_held'] += 1
            return 'skip_already_held'
        if len(self.positions) >= N_SLOTS:
            self.skip_log['slots_full'] += 1
            return 'skip_slots_full'
        eq = self.equity()
        cost = min(POS_FRAC * eq, self.cash)
        if cost <= 1e-9:
            self.skip_log['no_cash'] += 1
            return 'skip_no_cash'
        self.cash -= cost
        self.positions[code] = dict(
            value=cost, last_px=rec['buy_price'], buy_d8=d8, entry_cost=cost,
            sell_d8=rec['sell_d8'], sell_price=rec['sell_price'], rec=rec)
        return 'bought'

    def mark_and_settle(self, d8, panel):
        """收盘结算:先按当日价格 mark 全部持仓;sell_d8==d8 的按 sell_price 平仓回现金。"""
        closed = []
        for code, pos in list(self.positions.items()):
            if pos['sell_d8'] == d8 and pos['sell_price'] is not None:
                px = pos['sell_price']
            else:
                p = panel.get(code)
                if p is not None and d8 in p.index:
                    px = float(p.loc[d8, 'close'])
                else:
                    px = pos['last_px']          # 停牌/缺bar:平值
            pos['value'] *= px / pos['last_px'] if pos['last_px'] else 1.0
            pos['last_px'] = px
            if pos['sell_d8'] == d8 and pos['sell_price'] is not None:
                self.cash += pos['value']
                rec = pos['rec']
                self.trades.append(dict(
                    group=self.name, code=code, buy_d8=pos['buy_d8'],
                    sell_d8=d8, hold_days=rec['hold_days'],
                    buy_price=round(rec['buy_price'], 4), sell_price=round(px, 4),
                    exit_reason=rec['exit_reason'],
                    net_return=round(rec['net_return'], 5) if rec['net_return'] is not None else None,
                    peak_return=round(rec['peak_return'], 5),
                    entry_cost_frac=round(pos['entry_cost'], 5),
                    pnl_frac=round(pos['value'] - pos['entry_cost'], 6)))
                closed.append(code)
                del self.positions[code]
        self.equity_hist.append((d8, self.equity()))
        return closed


# ----------------------------------------------------------------------------
# 主循环
# ----------------------------------------------------------------------------
def run(start, end, tag, log_every=40):
    cfg = paper_cfg()
    PR._load()
    panel = PR.panel()
    all_days = [d for d in PR.trade_days() if start <= d <= end]
    print("[run] tag=%s days=%d (%s..%s) groups=%s exit=dd10" % (
        tag, len(all_days), all_days[0] if all_days else '-',
        all_days[-1] if all_days else '-', ','.join(GROUPS)), flush=True)

    cache = TradeCache(cfg)
    ports = {g: Portfolio(g) for g in GROUPS}
    decision_rows = []       # 决策留痕(spec §6.1-5 的盘后版雏形)
    overlap_pairs = 0        # 同票同日被>=2组买入的次数(公平性核对样本)
    t0 = time.time()

    for k, d in enumerate(all_days):
        prev = PR.prev_trading_day(d)
        pool = PR.dragon_pool(d, prev)

        # 1) 三组决策(唯一变量)
        day_picks = {g: DECIDERS[g](d, pool) for g in GROUPS}

        # 2) 共用进场闸:union(picks) 只算一次
        union_codes = []
        for g in GROUPS:
            for pk in day_picks[g]:
                if pk['code'] not in union_codes:
                    union_codes.append(pk['code'])
        recs = {c: cache.get(c, d) for c in union_codes}

        # 3) 各组独立组合记账:按 buy_hm 升序买入(全进组打满3slot的机械顺序)
        bought_by = {c: [] for c in union_codes}
        for g in GROUPS:
            filled_picks = [pk for pk in day_picks[g] if recs[pk['code']]['filled']]
            filled_picks.sort(key=lambda pk: (recs[pk['code']]['buy_hm'], pk['code']))
            status = {}
            for pk in filled_picks:
                st = ports[g].try_buy(d, pk['code'], recs[pk['code']])
                status[pk['code']] = st
                if st == 'bought':
                    bought_by[pk['code']].append(g)
            for pk in day_picks[g]:
                rec = recs[pk['code']]
                decision_rows.append(dict(
                    date=d, group=g, rank=pk['rank'], code=pk['code'], name=pk['name'],
                    pick_reason=pk['reason'], buy_reason=rec.get('buy_reason'),
                    buy_status=status.get(pk['code'],
                                          '-' if not rec['filled'] else 'n/a'),
                    buy_hm=rec.get('buy_hm'), buy_price=round(rec['buy_price'], 4) if rec.get('buy_price') else None,
                    sell_d8=rec.get('sell_d8'), exit_reason=rec.get('exit_reason'),
                    net_return=round(rec['net_return'], 5) if rec.get('net_return') is not None else None))
        overlap_pairs += sum(1 for c in union_codes if len(bought_by[c]) >= 2)

        # 4) 收盘结算(mark + 平仓)
        for g in GROUPS:
            ports[g].mark_and_settle(d, panel)

        if (k + 1) % log_every == 0:
            eqs = " ".join("%s=%.3f" % (g[:4], ports[g].equity()) for g in GROUPS)
            print("  %d/%d days  cache=%d  %s  %.0fs" % (
                k + 1, len(all_days), len(cache._cache), eqs, time.time() - t0), flush=True)

    # 期末未平仓:按最后 equity(已含 mark)自然计入净值,交易表只含已平仓
    _write_outputs(tag, cfg, ports, decision_rows, cache, all_days, overlap_pairs)
    return ports


# ----------------------------------------------------------------------------
# 指标 + 输出
# ----------------------------------------------------------------------------
def _metrics(port):
    eq = pd.Series(dict(port.equity_hist)).sort_index()
    ret = eq.pct_change().dropna()
    total = float(eq.iloc[-1] - 1.0) if len(eq) else 0.0
    mdd = float((eq / eq.cummax() - 1.0).min()) if len(eq) else 0.0
    sharpe = float(ret.mean() / ret.std() * np.sqrt(252)) if len(ret) > 1 and ret.std() > 0 else 0.0
    td = pd.DataFrame(port.trades)
    n = len(td)
    if n:
        rets = td['net_return'].dropna().values
        wins = rets[rets > 0]; losses = rets[rets <= 0]
        win_rate = len(wins) / len(rets) if len(rets) else 0.0
        pf = (wins.sum() / -losses.sum()) if losses.sum() < 0 else float('inf')
        cap = [max(0.0, r['net_return']) / r['peak_return']
               for _, r in td.iterrows()
               if r['peak_return'] and r['peak_return'] > 0 and r['net_return'] is not None]
        bigmeat = float(np.mean(cap)) if cap else 0.0
        open_end = 0
    else:
        win_rate = pf = bigmeat = 0.0
    return dict(total_return=round(total, 4), max_drawdown=round(mdd, 4),
                sharpe=round(sharpe, 3), n_closed_trades=n,
                win_rate=round(win_rate, 4),
                profit_factor=round(pf, 3) if pf != float('inf') else 'inf',
                bigmeat_capture=round(bigmeat, 4),
                open_positions_end=len(port.positions),
                skip_already_held=port.skip_log.get('already_held', 0),
                skip_slots_full=port.skip_log.get('slots_full', 0),
                skip_no_cash=port.skip_log.get('no_cash', 0)), eq


def _write_outputs(tag, cfg, ports, decision_rows, cache, all_days, overlap_pairs):
    os.makedirs(OUT_DIR, exist_ok=True)
    pre = os.path.join(OUT_DIR, "paper_step1_%s" % tag)

    summ_rows = {}
    eq_all = {}
    for g in GROUPS:
        m, eq = _metrics(ports[g])
        summ_rows[g] = m
        eq_all[g] = eq
        pd.DataFrame(ports[g].trades).to_csv(
            pre + "_%s_trades.csv" % g, index=False, encoding="utf-8-sig")

    sdf = pd.DataFrame(summ_rows).T
    sdf.index.name = 'group'
    sdf.to_csv(pre + "_compare.csv", encoding="utf-8-sig")

    eqdf = pd.DataFrame(eq_all)
    eqdf.index.name = 'd8'
    # 相对表现(spec §6.1-2):AI减全进 / AI减随机(把regime消掉)
    eqdf['rel_ai_minus_allin'] = eqdf['ai_placeholder'] - eqdf['all_in']
    eqdf['rel_ai_minus_random'] = eqdf['ai_placeholder'] - eqdf['random3']
    eqdf.to_csv(pre + "_equity.csv", encoding="utf-8-sig")

    pd.DataFrame(decision_rows).to_csv(
        pre + "_daily_decisions.csv", index=False, encoding="utf-8-sig")

    # ---- report.md ----
    lines = []
    A = lines.append
    A("# Project1 Paper — Step1 三组对照框架 + 盘后结算(框架验证,%s)\n" % tag)
    A("> spec: docs/specs/战车A_Project1_AI选股层Paper设计_spec_v0.1.md(§9 已定配置)。")
    A("> **本步只验框架逻辑/对照公平,不判任何选股价值**:'AI组'为占位(dragon_score top3,")
    A("> 已知样本外无alpha,仅作管线占位,Step4 换 MiniMax);验证期=IS 2023(已烧样本),")
    A("> 不动 2026(其授权仅限 Phase A 出场引擎回看)。真AI价值只能 forward paper 攒样本判(spec §7)。\n")

    A("## 三组对照结果(同池/同进场闸/同出场引擎/同仓位口径,唯一变量=选股)")
    A("| 指标 | AI占位(score top3) | 随机3(seed=日期) | 机械全进(≤3slot) |")
    A("|---|---:|---:|---:|")
    keys = [('total_return', '总收益', '%'), ('max_drawdown', '最大回撤', '%'),
            ('sharpe', 'Sharpe', ''), ('n_closed_trades', '已平仓笔数', ''),
            ('win_rate', '胜率', '%'), ('profit_factor', '盈亏比PF', ''),
            ('bigmeat_capture', '大肉捕获', ''), ('open_positions_end', '期末未平仓', ''),
            ('skip_slots_full', 'slot满跳过', ''), ('skip_already_held', '持仓中重选跳过', '')]
    for k, label, unit in keys:
        vals = []
        for g in GROUPS:
            v = summ_rows[g][k]
            if unit == '%' and isinstance(v, (int, float)):
                vals.append("%.1f%%" % (v * 100))
            else:
                vals.append(str(v))
        A("| %s | %s |" % (label, " | ".join(vals)))
    A("")

    A("## 对照公平性(框架验证重点)")
    A("- **结构保证**:同一 (code,date) 进出场只算一次(共享缓存),被多组选中引用同一结果 → 同票同日跨组进场时刻/价格/出场路径必然一致。")
    A("- 同票同日被 ≥2 组买入(公平性核对样本):**%d 次** —— 这些票在各组账本中买价/卖价完全相同,组间差异只来自'选了谁'。" % overlap_pairs)
    A("- 三组共用:进场闸(Phase A 默认 VWAP 完整口径)/ 出场(硬止损-7% + MA5 N=3 + 移动止盈 dd10 + 20天)/ 仓位(25%×≤3slot,留25%现金)/ 成本(滑点0.08%×2+佣金万2.5双边+印花税0.05%)。")
    A("- 随机组种子=交易日期(int(d8)),固定可复现、每日不同。")
    A("")

    er = cache.entry_reasons
    tot = sum(er.values())
    A("## 共用进场闸统计(union 监测池,%d 次尝试)" % tot)
    for r, n in er.most_common():
        A("- %s: %d (%.1f%%)" % (r, n, 100.0 * n / tot if tot else 0))
    A("")

    A("## 口径备注(盘后结算版近似,Step2 接实时后替换)")
    A("- 进场判定用盘后分钟数据复算(非实时逐tick);仓位=买入时组合权益×25%(现金不足取剩余现金)。")
    A("- slot 买入日至卖出日整日占用、次日释放(保守,不做日内slot翻转)。持仓中同票再被选中不加仓。")
    A("- 停牌日平值 mark;期末未平仓按末日 mark 计入净值(交易表只含已平仓)。")
    A("- 全进组在 3slot 上限下 ≠ Phase A 全进等权基座(那是单票等权无仓位上限),数字不可直接对表。")
    A("")

    A("## Step1 判读(只判框架,不判价值)")
    A("- 框架验收点:三组跑通、决策/成交/平仓全落盘、同票跨组一致、slot/现金约束生效、相对表现曲线可算。")
    A("- 组间数字差异在本步**没有任何选股价值含义**(占位AI≠真AI;单年regime主导)。")
    A("- 通过后进 Step2(QMT实时进场监测)→ Step3(只读看板)→ Step4(接MiniMax)。\n")

    with open(pre + "_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---- 控制台 ----
    print("\n" + "=" * 78)
    print("STEP1 三组对照(框架验证,唯一变量=选股;不判价值)  tag=%s" % tag)
    print("=" * 78)
    hdr = "%-22s %10s %10s %8s %8s %8s %8s %8s" % (
        "group", "total_ret", "mdd", "sharpe", "trades", "win", "PF", "bigmeat")
    print(hdr)
    for g in GROUPS:
        m = summ_rows[g]
        print("%-22s %9.1f%% %9.1f%% %8.2f %8d %7.1f%% %8s %8.2f" % (
            g, m['total_return'] * 100, m['max_drawdown'] * 100, m['sharpe'],
            m['n_closed_trades'], m['win_rate'] * 100, m['profit_factor'],
            m['bigmeat_capture']))
    print("-" * 78)
    print(" 同票同日被>=2组买入(公平核对样本): %d 次(共享缓存→跨组进出场必然一致)" % overlap_pairs)
    print(" 决策留痕: %d 行 → %s_daily_decisions.csv" % (len(decision_rows), os.path.basename(pre)))
    print("=" * 78)
    print("输出: %s_{compare,equity,daily_decisions,report,<group>_trades}.*" % pre)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20230101")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--tag", default="IS2023")
    args = ap.parse_args()
    run(args.start, args.end, args.tag)
