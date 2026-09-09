# -*- coding: utf-8 -*-
"""Project1 Phase A —— 机械进场闸 + 机械出场引擎回测(摘掉AI选股层)。

口径严格遵循《战车A_趋势持有改造_Project1_交接文档_v0.2.1_完整版》:
  - 候选池:pool_repro.dragon_pool(date) = 战车A get_dragon_stock_list_A 等价 top12(零改动)
  - 进场:9:30-10:30 VWAP站稳+回踩不破,signal_time 下一根 open 买入(完整口径);top12 过闸票全进等权
  - T+1:day0(=买入当日)不卖,只记 day0_untradable_risk;卖出规则 day1 起生效
  - hold_days 从 day0 算起(day0=第1持仓交易日);20天天花板从 day0 计第1天
  - 触发看 minute_close,成交用触发后"下一根有效bar的 open";开盘跳空特例;停牌/涨停买不到/跌停卖不出全处理
  - MA5 用前一交易日已知 MA5_prev(禁用当日收盘后 MA5)
  - 成本定值:买卖滑点各0.08% / 佣金万2.5双边 / 印花税卖0.05%(实盘仅 FixedSlippage(0.02),口径不同已注明)

【AI选股层不在本回测内】只能 forward paper 验证;2026 仅本项目出场引擎授权回看。
本回测为单票等权模拟(读不到实盘仓位配置),不作实盘仓位结论。

只读 minute / cache,只写本研究目录。不碰实盘 / 不改候选池 / 不装包。
"""
import os
import sys
import time
import functools

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pool_repro as PR

MIN_BYCODE = "D:/data_warehouse/canonical/minute_1m/by_code/code={code}/year={year}.parquet"

# ----------------------------------------------------------------------------
# 默认参数(Phase A baseline)
# ----------------------------------------------------------------------------
DEFAULT_CFG = dict(
    # 进场闸
    entry_mode='full',          # 'full'=signal_time完整口径 / 'simple'=10:31
    obs_start='09:30', obs_end='10:30', buy_cutoff='10:45',
    vwap_pullback_window=15,    # 回踩拉回窗(分钟bar数)
    vwap_break_tol=0.005,       # 允许跌破 VWAP -0.5%
    # 出场
    hard_stop=-0.07,
    ma5_n=3, ma5_check_freq=5,  # 每5分钟一检查点,连续N点破MA5
    ma5_tail_confirm='14:50',
    trail_switch=0.25,
    trail_dd_seg1=0.15,
    trail_seg2=((0.25, 0.12), (0.40, 0.10), (0.60, 0.08)),
    time_cap_days=20,
    # 成本(定值)
    buy_slip=0.0008, sell_slip=0.0008,
    commission=0.00025, stamp=0.0005,
)

LIMIT_EPS = 1e-3   # 涨跌停价比较容差


# ----------------------------------------------------------------------------
# 分钟读取(duckdb 按日下推;strftime 在 SQL 内做,按 code,d8 缓存)
# ----------------------------------------------------------------------------
import duckdb  # noqa: E402

_MCON = duckdb.connect()
_MCON.execute("PRAGMA threads=4")


@functools.lru_cache(maxsize=60000)
def minute_day(code, d8):
    """某 code 某交易日的分钟 df(列 hm/open/high/low/close/volume/amount,时间升序)。
    无数据(停牌/缺失)返回 None。调用方只读 .values,勿原地修改(缓存共享对象)。"""
    path = MIN_BYCODE.format(code=code, year=d8[:4])
    if not os.path.exists(path):
        return None
    dd = "%s-%s-%s" % (d8[:4], d8[4:6], d8[6:8])
    df = _MCON.execute(
        "SELECT strftime(datetime,'%H:%M') AS hm, open, high, low, close, volume, amount "
        "FROM read_parquet(?) WHERE CAST(datetime AS DATE)=DATE '" + dd + "' "
        "AND open IS NOT NULL ORDER BY datetime", [path]).df()
    if df is None or len(df) == 0:
        return None
    return df


# ----------------------------------------------------------------------------
# 日线派生:prev_close / MA5_prev / 涨跌停价
# ----------------------------------------------------------------------------
def daily_ctx(code, d8):
    """返回截至 d8(含)的日线上下文:prev_close(d8前一交易日close)、ma5_prev(前一交易日已知MA5)、
    atr14_frac(前14交易日 (high-low)/close 均值,波动率代理,供ATR自适应回撤用)。
    全部用 d8 之前的已知数据(不偷看 d8 当日收盘)。"""
    p = PR.panel().get(code)
    if p is None:
        return None
    prior = p[p.index < d8]
    if len(prior) < 1:
        return None
    prev_close = float(prior['close'].iloc[-1])
    ma5_prev = float(prior['close'].iloc[-5:].mean()) if len(prior) >= 5 else None
    atr14_frac = None
    if len(prior) >= 5:
        tail = prior.iloc[-14:]
        rng = ((tail['high'] - tail['low']) / tail['close']).replace([np.inf, -np.inf], np.nan).dropna()
        if len(rng) >= 5:
            atr14_frac = float(rng.mean())
    return dict(prev_close=prev_close, ma5_prev=ma5_prev, atr14_frac=atr14_frac)


def limits(prev_close):
    return round(prev_close * 1.10, 2), round(prev_close * 0.90, 2)


# ----------------------------------------------------------------------------
# 进场闸
# ----------------------------------------------------------------------------
def _vwap_series(day_df):
    cum_amt = day_df['amount'].cumsum().values
    cum_vol = (day_df['volume'].cumsum().values * 100.0)   # 手->股
    vwap = np.where(cum_vol > 0, cum_amt / cum_vol, np.nan)
    return vwap


def find_signal(day_df, cfg):
    """完整口径:返回 signal 行索引(在 day_df 中),无信号返回 None。
    signal = 观察窗[obs_start,obs_end]内第一根 close>=VWAP 且满足回踩不破 的bar:
       (a) 未有效跌破: min(low[首次站稳..i]) >= VWAP_i*(1-tol)  或
       (b) 回踩拉回:  [首次站稳..i] 内 window 根之内出现过 close<VWAP(回踩),且 close_i>=VWAP_i(站回)
    简化口径 simple:obs_end(10:30)那根 close>=VWAP 即 signal。"""
    vwap = _vwap_series(day_df)        # VWAP 累计含 09:30 竞价根
    hm = day_df['hm'].values
    close = day_df['close'].values
    low = day_df['low'].values
    # 信号检测跳过 09:30 集合竞价根(其 VWAP=自身价,close>=VWAP 恒真→闸失效);
    # 从首根连续交易bar(>=09:31)起判,VWAP 是真正的日内成交量加权均价。
    obs_lo = max(cfg['obs_start'], '09:31')
    obs_mask = (hm >= obs_lo) & (hm <= cfg['obs_end'])
    idxs = np.where(obs_mask)[0]
    if len(idxs) == 0:
        return None

    if cfg['entry_mode'] == 'simple':
        # 10:30(或<=obs_end最后一根)判断
        i = idxs[-1]
        if not np.isnan(vwap[i]) and close[i] >= vwap[i]:
            return i
        return None

    tol = cfg['vwap_break_tol']
    win = cfg['vwap_pullback_window']
    stand_idx = None
    last_dip_idx = None
    run_min_low = np.inf
    for i in idxs:
        v = vwap[i]
        if np.isnan(v):
            continue
        c = close[i]
        if stand_idx is None:
            if c >= v:
                stand_idx = i
                run_min_low = low[i]
                # 站稳当根即判定
                if low[i] >= v * (1 - tol):
                    return i
            continue
        # 已首次站稳
        run_min_low = min(run_min_low, low[i])
        if c < v:
            last_dip_idx = i
            continue
        # close 站回 VWAP 上方
        if run_min_low >= v * (1 - tol):
            return i
        if last_dip_idx is not None and (i - last_dip_idx) <= win:
            return i
    return None


def try_entry(code, d8, prev_close, cfg):
    """返回 dict(filled, buy_price, buy_hm, flags...)。买入价含滑点。"""
    res = dict(code=code, d8=d8, filled=False, buy_reason=None,
               buy_price=None, buy_hm=None, signal_hm=None, price_proxy_flag=False)
    day = minute_day(code, d8)
    if day is None:
        res['buy_reason'] = 'buy_skip_suspended'      # 停牌/无分钟
        return res
    sig = find_signal(day, cfg)
    if sig is None:
        res['buy_reason'] = 'buy_skip_no_signal'
        return res
    res['signal_hm'] = day['hm'].iloc[sig]
    # buy bar = signal 下一根
    if sig + 1 >= len(day):
        res['buy_reason'] = 'buy_late_unfilled'        # 信号在收盘根,无下一根
        return res
    buy_bar = day.iloc[sig + 1]
    if buy_bar['hm'] > cfg['buy_cutoff']:
        res['buy_reason'] = 'buy_late_unfilled'
        return res
    lim_up, _ = limits(prev_close)
    o = float(buy_bar['open'])
    # 涨停买不到:买入根 open 已达涨停(含一字)
    if o >= lim_up - LIMIT_EPS:
        res['buy_reason'] = 'buy_skip_limit_up'
        return res
    res['filled'] = True
    res['buy_reason'] = 'filled'
    res['buy_hm'] = buy_bar['hm']
    res['buy_price'] = o * (1 + cfg['buy_slip'])
    res['buy_open_raw'] = o
    return res


# ----------------------------------------------------------------------------
# 出场引擎
# ----------------------------------------------------------------------------
def _trail_threshold(peak_return, cfg):
    # trail_mode='single':单段固定回撤(如 dd10=0.10,Phase A 收紧发现的整机版);默认=两段式
    if cfg.get('trail_mode') == 'single':
        return cfg.get('trail_single', 0.10)
    if peak_return < cfg['trail_switch']:
        return cfg['trail_dd_seg1']
    thr = cfg['trail_seg2'][0][1]
    for lvl, dd in cfg['trail_seg2']:
        if peak_return >= lvl:
            thr = dd
    return thr


PRIORITY = {'hard_stop_7': 1, 'ma5_break': 2, 'trailing_stop': 3, 'time_cap_20': 4}


def simulate_exit(code, buy_d8, buy_price, buy_hm, cfg, days_override=None, no_proxy_close=False):
    """从 day0(buy_d8)起模拟出场。挂单模型(standing order):
      - 触发判定用 minute_close,按优先级 硬止损>MA5>移动止盈>天花板。
      - 触发后在"其后第一根可成交bar"用 open*(1-slip) 卖出;跌停一字顺延(跨bar/跨日持续尝试)。
      - day0(买入当日)不卖,只在买入根之后记 day0_untradable_risk(触发了但T+1卖不了)。
      - hold_days 从 day0 算第1天;20天天花板日尾盘兜底。MA5 用 ma5_prev(不偷看当日)。
    paper 盘后结算用(默认关,行为与 Phase A 完全一致):
      - days_override:限定可用交易日(如只到"今天"),供逐日重放结算。
      - no_proxy_close=True:数据尽头仍未触发出场 → 不做末日强平兜底,返回"仍持仓"
        (sell_price=None),次日结算从头重放自然续上(确定性)。
    返回 dict(...)。"""
    days = days_override if days_override is not None else \
        PR.forward_trading_days(buy_d8, cfg['time_cap_days'] + 6)  # 多取几天供"下一根"成交
    peak = buy_price            # 峰值=最高 minute_close,从买入起
    day0_risk = False
    pending = None              # 已触发未成交的最高优先级原因(standing order)
    fill_armed = False          # 是否进入"可成交"状态(触发根之后)
    blocked = 0                 # 卖不出的"天数"(整日跌停一字无法成交)
    out = dict(code=code, buy_d8=buy_d8, sell_price=None, sell_d8=None, sell_hm=None,
               exit_reason=None, hold_days=0, peak_return=0.0,
               day0_untradable_risk=False, sell_blocked_count=0, sell_proxy_flag=False)

    for di, d8 in enumerate(days):
        is_day0 = (di == 0)
        hold_day_no = di + 1
        day = minute_day(code, d8)
        ctx = daily_ctx(code, d8)
        ma5_prev = ctx['ma5_prev'] if ctx else None
        lim_dn = limits(ctx['prev_close'])[1] if ctx else None

        if day is None:            # 停牌:不可成交,pending 顺延,持仓日仍推进
            out['hold_days'] = hold_day_no
            continue

        close = day['close'].values
        opn = day['open'].values
        high = day['high'].values
        hm = day['hm'].values
        n = len(day)
        ma5_consec = 0             # 每日 MA5 连续检查点计数(日内收回即 reset)
        ma5_seqpeak = 0.0          # 变体E:破位序列内的最高收盘(判"不创反弹新高")
        blocked_today = False      # 本日是否出现"想卖却一字跌停卖不出"

        start_i = 0
        if is_day0:                # day0 只监控买入根之后
            after = np.where(hm > buy_hm)[0]
            if len(after) == 0:
                out['hold_days'] = hold_day_no
                continue
            start_i = int(after[0])

        for i in range(start_i, n):
            c = close[i]
            t = hm[i]
            if c > peak:
                peak = c
            peak_return = peak / buy_price - 1.0

            # ---- 已挂单:尝试在本根(触发根之后)open 成交 ----
            if fill_armed and not is_day0:
                o = float(opn[i])
                is_oneword_dn = (lim_dn is not None and o <= lim_dn + LIMIT_EPS
                                 and float(high[i]) <= lim_dn + LIMIT_EPS)
                if not is_oneword_dn:
                    out.update(sell_price=o * (1 - cfg['sell_slip']), sell_d8=d8, sell_hm=t,
                               exit_reason=pending, hold_days=hold_day_no,
                               peak_return=peak_return, day0_untradable_risk=day0_risk,
                               sell_blocked_count=blocked, sell_proxy_flag=False)
                    return out
                blocked_today = True
                continue  # 一字跌停卖不出 / 挂单状态下不再判新触发

            # ---- 未挂单:判触发(minute_close)----
            trig = None
            if c <= buy_price * (1 + cfg['hard_stop']):
                trig = 'hard_stop_7'
            if trig is None and ma5_prev is not None:
                # MA5 变体参数(Step1):
                #   ma5_break_mult: 破位幅度门槛(默认1.0=触及即算;变体D=0.98 需跌破2%)
                #   ma5_no_rebound: 变体E,连续N根跌破 且 期间不创反弹新高(收盘更高则中止计数)
                ma5_thr = ma5_prev * cfg.get('ma5_break_mult', 1.0)
                if (i % cfg['ma5_check_freq']) == 0:           # 每5分钟检查点
                    below = c < ma5_thr
                    if cfg.get('ma5_no_rebound', False):
                        if below:
                            if ma5_consec == 0:
                                ma5_seqpeak = c; ma5_consec = 1
                            elif c > ma5_seqpeak:              # 破位途中创反弹新高 → 中止,重计
                                ma5_seqpeak = c; ma5_consec = 1
                            else:
                                ma5_consec += 1
                        else:
                            ma5_consec = 0
                    else:
                        ma5_consec = ma5_consec + 1 if below else 0
                    if ma5_consec >= cfg['ma5_n']:
                        trig = 'ma5_break'
                if trig is None and t >= cfg['ma5_tail_confirm'] and c < ma5_thr:
                    trig = 'ma5_break'                          # 尾盘确认
            if trig is None:
                thr = _trail_threshold(peak_return, cfg)
                if (c / peak - 1.0) <= -thr:
                    trig = 'trailing_stop'
            if trig is None and hold_day_no >= cfg['time_cap_days'] and t >= cfg['ma5_tail_confirm']:
                trig = 'time_cap_20'

            if trig is None:
                continue
            if is_day0:
                day0_risk = True       # T+1:记风险不成交
                continue
            pending = trig
            fill_armed = True          # 触发根之后开始尝试成交

        if blocked_today:          # 本日有成交机会但全是一字跌停 → 卖不出的一天
            blocked += 1
        out['hold_days'] = hold_day_no

    # 跑满仍未成交(数据不足/持续跌停):末日收盘强制平仓兜底
    # (no_proxy_close=True 时跳过:paper 结算把"未触发"如实报为仍持仓,不合成假平仓)
    if out['exit_reason'] is None and no_proxy_close:
        out['peak_return'] = peak / buy_price - 1.0
        out['day0_untradable_risk'] = day0_risk
        out['sell_blocked_count'] = blocked
        out['pending_exit'] = pending          # 已触发未成交的挂单(明日续)
        return out
    if out['exit_reason'] is None:
        for d8 in reversed(days):
            lday = minute_day(code, d8)
            if lday is not None:
                out.update(sell_price=float(lday['close'].iloc[-1]) * (1 - cfg['sell_slip']),
                           sell_d8=d8, sell_hm=lday['hm'].iloc[-1],
                           exit_reason=(pending or 'time_cap_20'), hold_days=len(days),
                           peak_return=peak / buy_price - 1.0, day0_untradable_risk=day0_risk,
                           sell_blocked_count=blocked, sell_proxy_flag=True)
                break
    return out


# ============================================================================
# 组2:V3.5 短打出场(部分止盈 + 7%移动止损 + 20天封顶)
#   参数只读提取自 C:\quant_project\QMT_clean\archive\archive_xtquant_v35\qmt_v35_final.py:
#     TP1_PCT=0.09(卖1/3)/ TP2_PCT=0.16(卖剩余1/2)/ TRAIL_A=TRAIL_B=0.07 / MAX_HOLD_DAYS=20
#     P1修复:TP1后重置peak为当前价(给尾仓趋势空间)。V3.5另有Dragon TRAIL_D_HARD=3.5%,
#     本组按 Wallace Step0.5 指定只用7%移动止损,未含3.5%硬止损(报告注明)。
#   口径:与组1一致(minute_close触发/下一根open成交/同T+1/成交可得性/成本)——
#         非V3.5 tick级精确复现(V3.5用intraday high触发TP),close口径下TP触发略少,
#         组2表现是"V3.5短打哲学的保守下界"。实盘代码零改动,仅只读提参数。
# ============================================================================
V35 = dict(tp1=0.09, tp1_frac=1.0 / 3.0, tp2=0.16, tp2_frac_of_rest=0.5,
           trail=0.07, max_hold=20)


def simulate_exit_v35(code, buy_d8, buy_price, buy_hm, cfg):
    days = PR.forward_trading_days(buy_d8, V35['max_hold'] + 6)
    remaining = 1.0
    realized_gross = 0.0        # Σ frac*(sell/buy-1) 已了结分批
    true_peak = buy_price       # 全程最高 close(供大肉捕获指标)
    trail_peak = buy_price      # 移动止损用峰值(TP1后重置)
    tp1 = tp2 = False
    day0_risk = False
    blocked = 0
    pending = None              # {'type':'partial'/'full','frac','reason','anchor':(di,i)}
    last_leg = None
    out = dict(code=code, buy_d8=buy_d8, sell_price=None, sell_d8=None, sell_hm=None,
               exit_reason=None, hold_days=0, peak_return=0.0, gross=0.0,
               day0_untradable_risk=False, sell_blocked_count=0, sell_proxy_flag=False,
               tp1_hit=0, tp2_hit=0)
    slip = cfg['sell_slip']

    def _close_leg(frac, price, d8, hm, reason):
        nonlocal remaining, realized_gross, last_leg
        realized_gross += frac * (price / buy_price - 1.0)
        remaining -= frac
        last_leg = (price, d8, hm, reason)

    for di, d8 in enumerate(days):
        is_day0 = (di == 0)
        hold_day_no = di + 1
        day = minute_day(code, d8)
        ctx = daily_ctx(code, d8)
        lim_dn = limits(ctx['prev_close'])[1] if ctx else None
        if day is None:
            out['hold_days'] = hold_day_no
            continue
        close = day['close'].values; opn = day['open'].values
        high = day['high'].values; hm = day['hm'].values
        n = len(day)
        blocked_today = False
        start_i = 0
        if is_day0:
            after = np.where(hm > buy_hm)[0]
            if len(after) == 0:
                out['hold_days'] = hold_day_no
                continue
            start_i = int(after[0])

        for i in range(start_i, n):
            c = close[i]; t = hm[i]
            if c > true_peak:
                true_peak = c
            if c > trail_peak:
                trail_peak = c
            # 成交挂单(触发根之后)
            if pending is not None and not is_day0 and (di, i) > pending['anchor']:
                o = float(opn[i])
                oneword = (lim_dn is not None and o <= lim_dn + LIMIT_EPS and float(high[i]) <= lim_dn + LIMIT_EPS)
                if oneword:
                    blocked_today = True
                else:
                    frac = pending['frac'] if pending['type'] == 'partial' else remaining
                    _close_leg(frac, o * (1 - slip), d8, t, pending['reason'])
                    if pending['reason'] == 'tp1_9':
                        tp1 = True; out['tp1_hit'] = 1; trail_peak = c   # V3.5 P1:TP1后重置peak
                    elif pending['reason'] == 'tp2_16':
                        tp2 = True; out['tp2_hit'] = 1
                    pending = None
                    if remaining <= 1e-9:
                        return _finalize_v35(out, realized_gross, true_peak, buy_price,
                                             last_leg, hold_day_no, day0_risk, blocked)
                continue
            if is_day0:
                if c <= buy_price * 0.93 or (c / trail_peak - 1.0) <= -V35['trail']:
                    day0_risk = True
                continue
            if pending is not None:
                continue
            # 判规则(close),排下一根成交
            if (not tp1) and c >= buy_price * (1 + V35['tp1']):
                pending = dict(type='partial', frac=V35['tp1_frac'], reason='tp1_9', anchor=(di, i))
            elif tp1 and (not tp2) and c >= buy_price * (1 + V35['tp2']):
                pending = dict(type='partial', frac=remaining * V35['tp2_frac_of_rest'], reason='tp2_16', anchor=(di, i))
            elif (c / trail_peak - 1.0) <= -V35['trail']:
                pending = dict(type='full', frac=remaining, reason='trail_7', anchor=(di, i))
            elif hold_day_no >= V35['max_hold'] and t >= cfg['ma5_tail_confirm']:
                pending = dict(type='full', frac=remaining, reason='max_hold_20', anchor=(di, i))

        if blocked_today:
            blocked += 1
        out['hold_days'] = hold_day_no

    # 兜底:剩余仓末日收盘平掉
    if remaining > 1e-9:
        for d8 in reversed(days):
            lday = minute_day(code, d8)
            if lday is not None:
                _close_leg(remaining, float(lday['close'].iloc[-1]) * (1 - slip),
                           d8, lday['hm'].iloc[-1], 'max_hold_20')
                out['sell_proxy_flag'] = True
                break
    return _finalize_v35(out, realized_gross, true_peak, buy_price, last_leg,
                         out['hold_days'], day0_risk, blocked)


def _finalize_v35(out, realized_gross, true_peak, buy_price, last_leg, hold_days, day0_risk, blocked):
    out['gross'] = realized_gross
    out['peak_return'] = true_peak / buy_price - 1.0
    out['hold_days'] = hold_days
    out['day0_untradable_risk'] = day0_risk
    out['sell_blocked_count'] = blocked
    if last_leg is not None:
        out['sell_price'] = last_leg[0]; out['sell_d8'] = last_leg[1]
        out['sell_hm'] = last_leg[2]; out['exit_reason'] = last_leg[3]
    return out


# ============================================================================
# 组3:基准 —— 固定持有 N 天,无止损止盈(纯对照)
# ============================================================================
def simulate_exit_fixed(code, buy_d8, buy_price, buy_hm, cfg):
    n_hold = cfg.get('fixed_hold_days', 5)
    days = PR.forward_trading_days(buy_d8, n_hold + 6)
    true_peak = buy_price
    day0_risk = False
    out = dict(code=code, buy_d8=buy_d8, sell_price=None, sell_d8=None, sell_hm=None,
               exit_reason='fixed_hold_%d' % n_hold, hold_days=0, peak_return=0.0, gross=0.0,
               day0_untradable_risk=False, sell_blocked_count=0, sell_proxy_flag=False,
               tp1_hit=0, tp2_hit=0)
    # 更新峰值(全程,供大肉指标)+ 到第 n_hold 个持仓交易日尾盘平仓
    for di, d8 in enumerate(days):
        hold_day_no = di + 1
        day = minute_day(code, d8)
        if day is None:
            out['hold_days'] = hold_day_no
            continue
        cmax = float(day['close'].max())
        if cmax > true_peak:
            true_peak = cmax
        out['hold_days'] = hold_day_no
        if hold_day_no >= n_hold:
            # 第 n_hold 个交易日收盘卖出(无规则,纯持有)
            out['sell_price'] = float(day['close'].iloc[-1]) * (1 - cfg['sell_slip'])
            out['sell_d8'] = d8; out['sell_hm'] = day['hm'].iloc[-1]
            out['gross'] = out['sell_price'] / buy_price - 1.0
            out['peak_return'] = true_peak / buy_price - 1.0
            out['day0_untradable_risk'] = day0_risk
            return out
    # 数据不足兜底
    for d8 in reversed(days):
        lday = minute_day(code, d8)
        if lday is not None:
            out['sell_price'] = float(lday['close'].iloc[-1]) * (1 - cfg['sell_slip'])
            out['sell_d8'] = d8; out['sell_hm'] = lday['hm'].iloc[-1]
            out['gross'] = out['sell_price'] / buy_price - 1.0
            out['peak_return'] = true_peak / buy_price - 1.0
            out['sell_proxy_flag'] = True
            break
    return out


# ============================================================================
# 回吐侧专项(Step2):事前浮盈门槛 profit_gate → 之后切换测试移动止盈变体
#   ★命门:样本只用"事前可判定"的浮盈门槛筛(close/buy-1 首次 >= gate),
#     严禁用事后峰值筛。前段(gate前)出场不变=硬止损-7% + MA5破位N=3;
#     gate 后 MA5 关、切到被测的移动止盈变体(+硬止损floor + 20天封顶)。
#   in_sample=True 仅当该票曾触及 gate;未触及的票不进 gated 样本统计。
# ============================================================================
def _pg_threshold(variant, peak_return, cfg, atr_frac):
    if variant == 'dd10':
        return 0.10
    if variant == 'dd15':
        return 0.15
    if variant == 'dd20':
        return 0.20
    if variant == 'two_stage':
        return _trail_threshold(peak_return, cfg)
    if variant == 'atr':
        if atr_frac is None:
            return 0.15
        return min(0.30, max(0.05, cfg.get('pg_atr_k', 3.0) * atr_frac))
    return 0.15


def simulate_exit_profitgate(code, buy_d8, buy_price, buy_hm, cfg):
    gate = cfg.get('profit_gate', 0.15)
    variant = cfg.get('pg_variant', 'dd15')
    ma5_n = cfg.get('ma5_n', 3)
    days = PR.forward_trading_days(buy_d8, cfg['time_cap_days'] + 6)
    peak = buy_price
    gated = False
    gate_price = None; gate_d8 = None; gate_hm = None
    pending = None; fill_armed = False
    day0_risk = False; blocked = 0
    out = dict(code=code, buy_d8=buy_d8, in_sample=False,
               gate_price=None, gate_d8=None, gate_hm=None,
               sell_price=None, sell_d8=None, sell_hm=None, exit_reason=None,
               hold_days=0, hold_days_after_gate=0, peak_return=0.0, peak_price=buy_price,
               gate_capture=None, giveback=None, gross=0.0,
               day0_untradable_risk=False, sell_blocked_count=0, sell_proxy_flag=False)

    def _finish(sell_price, sd8, shm, reason, hold_day_no):
        out['sell_price'] = sell_price; out['sell_d8'] = sd8; out['sell_hm'] = shm
        out['exit_reason'] = reason; out['hold_days'] = hold_day_no
        out['peak_price'] = peak; out['peak_return'] = peak / buy_price - 1.0
        out['gross'] = sell_price / buy_price - 1.0
        out['day0_untradable_risk'] = day0_risk; out['sell_blocked_count'] = blocked
        if gated:
            out['in_sample'] = True
            out['gate_price'] = gate_price; out['gate_d8'] = gate_d8; out['gate_hm'] = gate_hm
            # 大肉捕获率:用"买入→峰值"做分母(gated票峰值≥+gate,分母恒稳);
            # 表达"整段可得涨幅(买到峰值)吃到多少"。不用"gate→峰值"分母:票刚过gate即见顶时
            # 分母趋零会使比率爆炸(均值失真),from-buy 稳定且同义。
            denom = peak - buy_price
            out['gate_capture'] = (sell_price - buy_price) / denom if denom > 1e-9 else 1.0
            out['giveback'] = (peak - sell_price) / peak if peak > 0 else 0.0
            gdays = [d for d in days if gate_d8 <= d <= sd8]
            out['hold_days_after_gate'] = len(gdays)
        return out

    for di, d8 in enumerate(days):
        is_day0 = (di == 0)
        hold_day_no = di + 1
        day = minute_day(code, d8)
        ctx = daily_ctx(code, d8)
        ma5_prev = ctx['ma5_prev'] if ctx else None
        atr_frac = ctx['atr14_frac'] if ctx else None
        lim_dn = limits(ctx['prev_close'])[1] if ctx else None
        if day is None:
            out['hold_days'] = hold_day_no
            continue
        close = day['close'].values; opn = day['open'].values
        high = day['high'].values; hm = day['hm'].values
        n = len(day)
        ma5_consec = 0; blocked_today = False
        start_i = 0
        if is_day0:
            after = np.where(hm > buy_hm)[0]
            if len(after) == 0:
                out['hold_days'] = hold_day_no
                continue
            start_i = int(after[0])

        for i in range(start_i, n):
            c = close[i]; t = hm[i]
            if c > peak:
                peak = c
            peak_return = peak / buy_price - 1.0
            # 成交挂单
            if fill_armed and not is_day0:
                o = float(opn[i])
                oneword = (lim_dn is not None and o <= lim_dn + LIMIT_EPS and float(high[i]) <= lim_dn + LIMIT_EPS)
                if not oneword:
                    return _finish(o * (1 - cfg['sell_slip']), d8, t, pending, hold_day_no)
                blocked_today = True
                continue
            # 事前浮盈门槛检测(可在day0置位,只是状态,不成交)
            if not gated and (c / buy_price - 1.0) >= gate:
                gated = True; gate_price = c; gate_d8 = d8; gate_hm = t
            # 触发判定
            trig = None
            if c <= buy_price * (1 + cfg['hard_stop']):
                trig = 'hard_stop_7'
            if trig is None and not gated and ma5_prev is not None:   # gate前:MA5(N)
                if (i % cfg['ma5_check_freq']) == 0:
                    ma5_consec = ma5_consec + 1 if c < ma5_prev else 0
                    if ma5_consec >= ma5_n:
                        trig = 'ma5_break'
                if trig is None and t >= cfg['ma5_tail_confirm'] and c < ma5_prev:
                    trig = 'ma5_break'
            if trig is None and gated:                                # gate后:移动止盈变体
                thr = _pg_threshold(variant, peak_return, cfg, atr_frac)
                if (c / peak - 1.0) <= -thr:
                    trig = 'trailing_%s' % variant
            if trig is None and hold_day_no >= cfg['time_cap_days'] and t >= cfg['ma5_tail_confirm']:
                trig = 'time_cap_20'
            if trig is None:
                continue
            if is_day0:
                day0_risk = True
                continue
            pending = trig; fill_armed = True

        if blocked_today:
            blocked += 1
        out['hold_days'] = hold_day_no

    # 兜底:末日收盘平仓
    for d8 in reversed(days):
        lday = minute_day(code, d8)
        if lday is not None:
            out['sell_proxy_flag'] = True
            return _finish(float(lday['close'].iloc[-1]) * (1 - cfg['sell_slip']),
                           d8, lday['hm'].iloc[-1], (pending or 'time_cap_20'), out['hold_days'])
    return out


def simulate_exit_dispatch(code, buy_d8, buy_price, buy_hm, cfg):
    """按 cfg['exit_style'] 选出场引擎。返回统一 out(含 gross 供成本核算)。"""
    style = cfg.get('exit_style', 'trend_hold')
    if style == 'v35_short':
        return simulate_exit_v35(code, buy_d8, buy_price, buy_hm, cfg)
    if style == 'fixed_hold':
        return simulate_exit_fixed(code, buy_d8, buy_price, buy_hm, cfg)
    out = simulate_exit(code, buy_d8, buy_price, buy_hm, cfg)   # 组1 趋势持有(已验证)
    if out.get('sell_price') and buy_price:
        out['gross'] = out['sell_price'] / buy_price - 1.0
    out.setdefault('tp1_hit', 0); out.setdefault('tp2_hit', 0)
    return out


# ----------------------------------------------------------------------------
# 单笔交易净收益(含成本)
# ----------------------------------------------------------------------------
def trade_return(buy_price, sell_price, cfg):
    """买卖价已含滑点。再扣佣金(双边)+印花税(卖)。返回净收益率。"""
    if buy_price is None or sell_price is None or buy_price <= 0:
        return None
    gross = sell_price / buy_price - 1.0
    cost = cfg['commission'] * 2 + cfg['stamp']     # 佣金双边 + 印花税卖单边
    return gross - cost


def trade_return_from_gross(gross, cfg):
    """从已算好的 position-weighted gross(组2部分止盈用)扣成本。
    成本恒等式:分批多次卖,佣金(买1+卖各leg)+印花税(卖各leg)按frac加权 Σ=comm*2+stamp,与单笔同。"""
    if gross is None:
        return None
    return gross - (cfg['commission'] * 2 + cfg['stamp'])


if __name__ == "__main__":
    # 单日烟测:跑一天看进场/出场链路
    cfg = dict(DEFAULT_CFG)
    PR._load()
    d = "20230301"
    prev = PR.prev_trading_day(d)
    pool = PR.dragon_pool(d, prev)
    print("date=%s prev=%s pool=%d" % (d, prev, len(pool)))
    for p in pool[:12]:
        code = p['stock']
        ctx = daily_ctx(code, d)
        if ctx is None:
            print("  %s no daily ctx" % code); continue
        e = try_entry(code, d, ctx['prev_close'], cfg)
        line = "  %s tpl=%s score=%.3f entry=%s" % (code, p['tpl'], p['dragon_score'], e['buy_reason'])
        if e['filled']:
            x = simulate_exit(code, d, e['buy_price'], e['buy_hm'], cfg)
            r = trade_return(e['buy_price'], x['sell_price'], cfg)
            line += " sig=%s buy=%s@%.3f -> exit=%s d%d sell@%.3f ret=%.2f%% peakR=%.1f%%" % (
                e['signal_hm'], e['buy_hm'], e['buy_price'], x['exit_reason'], x['hold_days'],
                x['sell_price'] or 0, (r or 0) * 100, x['peak_return'] * 100)
        print(line)
