# -*- coding: utf-8 -*-
"""
research_role_rotation_direct_sim_v1.py
========================================
核心/卫星角色轮动 — 聚宽研究环境直接模拟脚本 v1
========================================

用途:
  在聚宽研究 Notebook 中模拟核心仓 + 卫星仓 + 角色轮动机制，
  从原始行情重新生成候选、买入、卖出、晋级、降级，
  不基于历史日志，不调用真实下单函数。

运行方式:
  from jqdata import *
  import importlib
  import research_role_rotation_direct_sim_v1 as rr
  importlib.reload(rr)
  rr.get_price = get_price
  rr.get_trade_days = get_trade_days
  rr.get_all_securities = get_all_securities
  rr.get_extras = get_extras
  rr.run_research(start_date="2025-07-01", end_date="2026-06-14", output_dir=".")
"""

import os
import datetime
import traceback
import numpy as np
import pandas as pd
import zipfile
from collections import OrderedDict

def safe_to_csv(df, path, columns):
    if df is None or df.empty:
        df = pd.DataFrame(columns=columns)
    else:
        actual_cols = [c for c in columns if c in df.columns]
        for c in df.columns:
            if c not in actual_cols:
                actual_cols.append(c)
        df = df[actual_cols]
    df.to_csv(path, index=False, encoding='utf-8-sig')
    return df


def normalize_multi_price_frame(df):
    """
    Standardize the multi-stock daily price DataFrame.
    Returns a DataFrame with columns:
      ['date', 'code', 'open', 'close', 'high', 'low', 'volume', 'money', 'high_limit', 'paused']
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['date', 'code', 'open', 'close', 'high', 'low', 'volume', 'money', 'high_limit', 'paused'])

    df = df.copy()

    # 1. Reset index if it is MultiIndex or has date/code in index
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    elif df.index.name in ('time', 'date', 'code') or df.index.name is not None:
        df = df.reset_index()

    # 2. Identify and rename code column
    code_col = None
    for c in ('code', 'stock', 'level_1', 'security'):
        if c in df.columns:
            code_col = c
            break
    if code_col and code_col != 'code':
        df = df.rename(columns={code_col: 'code'})

    # 3. Identify and rename date column
    date_col = None
    for c in ('time', 'date', 'index', 'datetime', 'level_0'):
        if c in df.columns:
            date_col = c
            break
    if date_col and date_col != 'date':
        df = df.rename(columns={date_col: 'date'})

    # Ensure date column is formatted as datetime.date objects or pd.Timestamp
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date']).dt.date
        except Exception:
            pass

    # Ensure all required columns are present
    required = ['date', 'code', 'open', 'close', 'high', 'low', 'volume', 'money', 'high_limit', 'paused']
    for r in required:
        if r not in df.columns:
            df[r] = np.nan

    return df[required]


# =========================================================
# 聚宽 API 占位 — 由调用方注入
# =========================================================
get_price = None
get_trade_days = None
get_all_securities = None
get_extras = None
get_call_auction = None

# =========================================================
# 常量 / 默认参数
# =========================================================
INITIAL_CASH = 1_000_000.0
SLIPPAGE_PER_SHARE = 0.02        # 每股滑点(元)
COMMISSION_RATE = 0.00025        # 佣金万2.5
STAMP_TAX_RATE = 0.0005          # 印花税万5(卖出)

# 仓位结构
CORE_TOP1_RATIO = 0.35
CORE_TOP2_RATIO = 0.25
SATELLITE_RATIO = 0.15
MAX_INITIAL_RATIO = 0.60
MAX_TOTAL_RATIO = 0.75
MAX_SINGLE_RATIO = 0.50
MIN_BUY_RATIO = 0.05            # 最小有效买入比例

# 候选生成
EXCLUDE_PREFIXES = ('30', '688', '689', '8', '4', '9')
NEW_STOCK_DAYS = 50
DRAGON_MIN_PREV_MONEY = 1.5e8
DRAGON_MIN_RET3 = 0.03
DRAGON_MIN_SCORE = 0.70
DRAGON_MIN_OPEN_RATIO = 0.015
DRAGON_MAX_OPEN_RATIO = 0.055

# 卫星确认 Rule D
SATELLITE_RET_FROM_SIGNAL = 0.05
SATELLITE_DAY_RET = 0.05
SATELLITE_VOL_RATIO_MIN = 1.0
SATELLITE_VOL_RATIO_MAX = 2.0
SATELLITE_MA5_DIST_MAX = 0.10
SATELLITE_CLOSE_TO_HIGH = 0.97
SATELLITE_WATCH_DAYS = 3

# 退出参数
CORE_STOP_LOSS = -0.06
CORE_DD_FROM_HIGH = 0.10
CORE_HOLD_LOSS_DAYS = 5
SATELLITE_STOP_LOSS = -0.06
SATELLITE_HOLD_LOSS_DAYS = 3
SATELLITE_MAX_HOLD_DAYS = 5

# 角色评分
PROMOTION_MARGIN = 10
SATELLITE_MIN_PNL = 0.03
CORE_DRAWDOWN_WEAK = 0.08

# 市场状态
MARKET_INDEX = '000905.XSHG'
MARKET_MA = 20
MARKET_RET_LOOKBACK = 10

# 数据段划分
TRAIN_END = '2025-12-31'
VAL_END = '2026-03-31'

# 扰动组
SENSITIVITY_PARAMS = {
    'promotion_margin': [8, 10, 12],
    'satellite_min_pnl': [0.02, 0.03, 0.05],
    'core_drawdown_weak': [0.06, 0.08, 0.10],
    'satellite_slot_ratio': [0.10, 0.15],
    'max_total_cap': [0.75, 0.90],
}


# =========================================================
# 工具函数
# =========================================================
def _log(msg):
    """简单日志打印"""
    print("[RR-SIM] " + msg)


def _safe_div(a, b, default=0.0):
    return float(a) / float(b) if b and b != 0 else default


def _to_date(d):
    """兼容旧 Python 的日期转换（不依赖 date.fromisoformat）"""
    if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime):
        return d
    if isinstance(d, datetime.datetime):
        return d.date()
    if hasattr(d, 'date') and callable(d.date):  # pandas Timestamp
        return d.date()
    if isinstance(d, str):
        try:
            return datetime.datetime.strptime(d[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    # 兜底: pd.to_datetime
    try:
        return pd.to_datetime(d).date()
    except Exception:
        pass
    raise ValueError("_to_date: 无法将 {!r} 转换为 date".format(d))


def _calc_ma(series, n):
    """计算最近 n 个值的均值"""
    if len(series) < n:
        return None
    return float(series.iloc[-n:].mean())


def _calc_cost_with_slippage(price, shares, direction='buy'):
    """考虑滑点和手续费的实际成交金额"""
    if direction == 'buy':
        exec_price = price + SLIPPAGE_PER_SHARE
        amount = exec_price * shares
        commission = max(amount * COMMISSION_RATE, 5.0)
        return amount + commission, exec_price
    else:
        exec_price = max(price - SLIPPAGE_PER_SHARE, 0.01)
        amount = exec_price * shares
        commission = max(amount * COMMISSION_RATE, 5.0)
        stamp_tax = amount * STAMP_TAX_RATE
        return amount - commission - stamp_tax, exec_price


# =========================================================
# 市场状态判断
# =========================================================
def get_market_state(date, price_cache):
    """
    返回 bull / neutral / bear
    """
    idx = MARKET_INDEX
    key = (idx, date)
    if key not in price_cache:
        return 'neutral'
    hist = price_cache[key]
    if hist is None or len(hist) < MARKET_MA + 5:
        return 'neutral'
    closes = hist['close']
    ma20 = float(closes.iloc[-MARKET_MA:].mean())
    current = float(closes.iloc[-1])
    ret_10 = float(closes.iloc[-1]) / float(closes.iloc[-MARKET_RET_LOOKBACK]) - 1 \
        if len(closes) >= MARKET_RET_LOOKBACK + 1 else 0.0
    if current >= ma20 and ret_10 > 0:
        return 'bull'
    elif current < ma20 and ret_10 < 0:
        return 'bear'
    return 'neutral'


def normalize_price_frame(df):
    """
    将 get_price 返回值标准化，保证结果 DataFrame 至少包含 'date' 和 'close' 两列。
    兼容以下情形:
      - df.columns 包含 'time' / 'date' / 'index'
      - 日期在 df.index（DatetimeIndex 或普通 Index）
      - reset_index 后日期列名为 'index' / 'level_0' / 'datetime'
      - MultiIndex
      - 空 DataFrame
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['date', 'close'])

    df = df.copy()

    # 展开 MultiIndex
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()

    # 确定日期列
    date_col = None
    for candidate in ('time', 'date', 'index', 'datetime', 'level_0'):
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None:
        # 日期在 Index
        df = df.reset_index()
        for candidate in ('index', 'time', 'date', 'datetime', 'level_0'):
            if candidate in df.columns:
                date_col = candidate
                break

    if date_col is None:
        # 仍然找不到，把第一列当日期
        date_col = df.columns[0]

    # 统一命名为 'date'
    if date_col != 'date':
        df = df.rename(columns={date_col: 'date'})

    # 确保 'close' 列存在
    if 'close' not in df.columns:
        return pd.DataFrame(columns=['date', 'close'])

    # 把 date 列转为可比较的 pandas Timestamp
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception:
        pass

    df = df[['date', 'close']].dropna(subset=['close'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def load_market_index_history(trade_days):
    """预加载指数历史数据，失败时 fallback 为空缓存（全部 neutral）"""
    cache = {}
    idx = MARKET_INDEX
    if not trade_days:
        return cache
    start = trade_days[0] - datetime.timedelta(days=60)
    end = trade_days[-1]
    try:
        raw = get_price(
            idx, start_date=str(start), end_date=str(end),
            frequency='daily', fields=['close'], panel=False,
        )
        df = normalize_price_frame(raw)
        if df.empty:
            _log("WARN: load_market_index_history 返回空数据，市场状态全部 neutral")
            return cache

        for td in trade_days:
            ts = pd.Timestamp(td)
            mask = df['date'] <= ts
            sub = df[mask].tail(MARKET_MA + MARKET_RET_LOOKBACK + 5)
            if len(sub) > 0:
                cache[(idx, td)] = sub
    except Exception as e:
        _log("WARN: load_market_index_history error: {} — 市场状态全部 neutral".format(e))
    return cache


# =========================================================
# 股票基础筛选
# =========================================================
def get_universe(date):
    """获取可交易股票池，排除 ST/创业板/科创板/新股等"""
    try:
        all_sec = get_all_securities('stock', date)
        if all_sec is None or all_sec.empty:
            return []
    except Exception:
        return []
    universe = []
    for stock in all_sec.index:
        code = stock.split('.')[0]
        if any(code.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        info = all_sec.loc[stock]
        start_date = info.get('start_date')
        if start_date is not None:
            if (_to_date(date) - _to_date(start_date)).days < NEW_STOCK_DAYS:
                continue
        name = str(info.get('display_name', ''))
        if 'ST' in name or 'st' in name or '退' in name:
            continue
        universe.append(stock)
    return universe


# =========================================================
# 候选生成
# =========================================================
def generate_core_candidates(date, prev_date, universe, diag_info=None):
    """
    近似策略核心候选生成逻辑:
    1. 批量取近 30 日日线数据 (解决问题 3，把 count 从 20 提高到 30)
    2. 对 prefilter 筛选后的股票进行批量 get_price 并缓存，防止循环 get_price 被限流 (解决问题 1)
    3. 获取真实集合竞价成交量量比 (解决问题 2)
    4. 用 v3 评分体系打分并结合个股趋势过滤
    5. 返回按 score 降序的候选列表
    """
    if diag_info is None:
        diag_info = {}

    diag_info['universe_count'] = len(universe) if universe else 0
    diag_info['tradable_count'] = len(universe) if universe else 0

    # 初始化诊断数据以防中途返回
    diag_info['price_batch_error'] = 0
    diag_info['candidate_skip_price_batch_error'] = 0
    diag_info['candidate_skip_no_price'] = 0
    diag_info['trend_data_len_min'] = 0
    diag_info['trend_data_len_mean'] = 0.0
    diag_info['trend_filter_executed_count'] = 0
    diag_info['trend_filter_skipped_count'] = 0
    diag_info['auction_unavailable'] = 0

    if not universe:
        return []

    # 取近 30 日日线 (解决问题 3)
    try:
        price_df = get_price(
            universe, end_date=str(prev_date), frequency='daily',
            fields=['close', 'high', 'low', 'money', 'volume',
                    'high_limit', 'paused', 'open'],
            count=30, panel=False,
        )
    except Exception as e:
        _log("WARN: generate_core_candidates price error: {}".format(e))
        return []

    if price_df is None or price_df.empty:
        diag_info['price_data_ok_count'] = 0
        return []

    diag_info['price_data_ok_count'] = len(price_df['code'].unique())
    price_df = price_df.sort_values(['code', 'time'])
    prefiltered_stocks = []
    stock_histories = {}

    lens = []

    # 步骤 1: 筛选出通过 Prefilter 的股票
    for stock, df in price_df.groupby('code', sort=False):
        if len(df) < 10:
            continue
        if df['paused'].iloc[-1] != 0:
            continue

        y_close = float(df['close'].iloc[-1])
        y_hl = float(df['high_limit'].iloc[-1])
        y_money = float(df['money'].iloc[-1])

        # 排除前日涨停
        if y_hl > 0 and y_close >= y_hl * 0.995:
            continue
        if y_money < DRAGON_MIN_PREV_MONEY:
            continue

        prefiltered_stocks.append(stock)
        stock_histories[stock] = df
        lens.append(len(df))

    diag_info['prefilter_count'] = len(prefiltered_stocks)
    diag_info['trend_data_len_min'] = min(lens) if lens else 0
    diag_info['trend_data_len_mean'] = float(np.mean(lens)) if lens else 0.0

    if not prefiltered_stocks:
        diag_info['core_candidate_count'] = 0
        diag_info['deep_water_count'] = 0
        return []

    # 步骤 2: 批量获取这些股票在 date 当天的行情 (解决问题 1)
    day_price_lookup = {}
    batch_size = 300
    price_batch_error = False
    batch_err_msg = ""

    for i in range(0, len(prefiltered_stocks), batch_size):
        chunk = prefiltered_stocks[i:i+batch_size]
        try:
            chunk_df = get_price(
                chunk, start_date=str(date), end_date=str(date),
                frequency='daily', fields=['open', 'close', 'high', 'low',
                                           'high_limit', 'paused', 'volume', 'money'],
                panel=False,
            )
            if chunk_df is not None and not chunk_df.empty:
                # 兼容格式化
                chunk_df_norm = normalize_multi_price_frame(chunk_df)
                for _, row in chunk_df_norm.iterrows():
                    stk = row['code']
                    day_price_lookup[stk] = {
                        'open': float(row['open']) if pd.notna(row['open']) else 0.0,
                        'close': float(row['close']) if pd.notna(row['close']) else 0.0,
                        'high': float(row['high']) if pd.notna(row['high']) else 0.0,
                        'low': float(row['low']) if pd.notna(row['low']) else 0.0,
                        'high_limit': float(row['high_limit']) if pd.notna(row['high_limit']) else 0.0,
                        'paused': float(row['paused']) if pd.notna(row['paused']) else 0.0,
                        'volume': float(row['volume']) if pd.notna(row['volume']) else 0.0,
                        'money': float(row['money']) if pd.notna(row['money']) else 0.0,
                    }
        except Exception as e:
            price_batch_error = True
            batch_err_msg = str(e)
            diag_info['price_batch_error'] = 1
            diag_info['candidate_skip_price_batch_error'] += len(chunk)
            diag_info['notes'] = diag_info.get('notes', '') + f"price_batch_error_{i}:{batch_err_msg};"
            _log("WARN: batch get_price chunk failed: {}".format(e))

    # 步骤 3: 获取真实集合竞价成交量 (解决问题 2)
    auction_available = 0
    auction_data_lookup = {}

    # 从全局变量或者模块里解析 get_call_auction
    global get_call_auction
    if get_call_auction is not None:
        try:
            for i in range(0, len(prefiltered_stocks), batch_size):
                chunk = prefiltered_stocks[i:i+batch_size]
                auc_df = get_call_auction(chunk, start_date=str(date), end_date=str(date), fields=['time', 'volume', 'current'])
                if auc_df is not None and not auc_df.empty:
                    if isinstance(auc_df.index, pd.MultiIndex):
                        auc_df = auc_df.reset_index()
                    code_col = None
                    for c in ('code', 'stock', 'security'):
                        if c in auc_df.columns:
                            code_col = c
                            break
                    if code_col:
                        for _, r in auc_df.iterrows():
                            s_code = r[code_col]
                            auction_data_lookup[s_code] = {
                                'volume': float(r['volume']) if pd.notna(r['volume']) else 0.0,
                                'current': float(r['current']) if pd.notna(r['current']) else 0.0
                            }
            auction_available = 1
        except Exception as e:
            _log("WARN: get_call_auction failed, fallback: {}".format(e))
            auction_available = 0
            diag_info['notes'] = diag_info.get('notes', '') + f"get_call_auction_failed:{e};"
    else:
        auction_available = 0

    if auction_available == 0:
        diag_info['auction_unavailable'] = 1

    # 步骤 4: 循环打分和过滤
    candidates = []
    trend_filter_executed = 0
    trend_filter_skipped = 0

    for stock in prefiltered_stocks:
        df = stock_histories[stock]

        # 匹配行情价格
        day_price = day_price_lookup.get(stock)
        if day_price is None:
            diag_info['candidate_skip_no_price'] += 1
            diag_info['buy_skip_no_price'] += 1
            continue

        if day_price['paused'] != 0:
            continue

        y_close = float(df['close'].iloc[-1])
        open_price = day_price['open']

        if open_price <= 0 or y_close <= 0:
            continue

        open_ratio = open_price / y_close - 1
        if open_ratio <= 0:
            continue
        if open_ratio < DRAGON_MIN_OPEN_RATIO or open_ratio > DRAGON_MAX_OPEN_RATIO:
            continue

        # 涨停不买
        if day_price['high_limit'] > 0 and open_price >= day_price['high_limit'] * 0.995:
            continue

        # 集合竞价量比获取与 fallback
        auc_ratio = np.nan
        if auction_available == 1:
            auc_item = auction_data_lookup.get(stock)
            if auc_item and auc_item['volume'] > 0:
                auc_vol = auc_item['volume']
                auc_ratio = auc_vol / max(float(df['volume'].iloc[-1]), 1.0)

        # 模板判定
        tpl = 'trend_core'
        close_to_high = y_close / max(float(df['high'].tail(20).max()), 0.01)

        # deep_water 模板判定。如果竞价不可用，则 auc_ratio 为 NaN，该条件恒为 False，符合不强行伪造原则
        if (pd.notna(auc_ratio)
                and 0.90 <= close_to_high < 0.975
                and open_ratio >= 0.015
                and auc_ratio >= 0.006 * 1.2):
            tpl = 'deep_water'

        # 计算因子与打分
        ret3 = y_close / float(df['close'].iloc[-4]) - 1 if len(df) >= 4 else 0.0
        avg_range = 0.0
        valid = df[df['close'] > 0].tail(10)
        if len(valid) >= 5:
            avg_range = float(((valid['high'] - valid['low']) / valid['close']).mean())

        inv_c2h = 1.0 - close_to_high
        score = 0.0
        score += inv_c2h * 2.5
        score += avg_range * 4.0

        # 集合竞价量比评分部分 (解决问题 2 fallback 逻辑一致)
        if pd.notna(auc_ratio):
            score += max(0.0, 0.03 - auc_ratio) * 8.0

        score += min(max(ret3, 0.0), 0.25) * inv_c2h * 2.0
        score += min(max(ret3, 0.0), 0.30) * 0.50
        if tpl == 'deep_water':
            score += 0.15

        if score < DRAGON_MIN_SCORE:
            continue

        # 个股趋势过滤 (解决问题 3)
        closes = df['close'].values
        lows = df['low'].values
        if len(closes) >= 21:
            trend_filter_executed += 1
            ma5 = float(np.mean(closes[-6:-1]))
            ma10 = float(np.mean(closes[-11:-1]))
            ma20 = float(np.mean(closes[-21:-1]))
            ref_close = float(closes[-2])
            ma_aligned = ma5 > ma10 > ma20
            price_above = ref_close > ma20
            if len(lows) >= 20:
                recent_low = float(np.min(lows[-10:]))
                prev_low = float(np.min(lows[-20:-10]))
                higher_lows = recent_low >= prev_low * 0.98
            else:
                higher_lows = True
            if not (ma_aligned and price_above and higher_lows):
                continue
        else:
            trend_filter_skipped += 1

        candidates.append({
            'date': date,
            'stock': stock,
            'name': '',
            'score': score,
            'entry_type': tpl,
            'rank': 0,
            'open_ratio': open_ratio,
            'close_to_high': close_to_high,
            'auc_ratio': auc_ratio,
            'ret3': ret3,
            'open_price': open_price,
            'close_price': day_price['close'],
            'high_price': day_price['high'],
            'low_price': day_price['low'],
            'high_limit': day_price['high_limit'],
            'day_volume': day_price['volume'],
            'day_money': day_price['money'],
            'market_trend': '',
        })

    diag_info['trend_filter_executed_count'] = trend_filter_executed
    diag_info['trend_filter_skipped_count'] = trend_filter_skipped
    diag_info['core_candidate_count'] = len(candidates)
    diag_info['deep_water_count'] = len([c for c in candidates if c.get('entry_type') == 'deep_water'])

    # 排序并赋rank
    candidates.sort(key=lambda x: x['score'], reverse=True)
    for i, c in enumerate(candidates):
        c['rank'] = i + 1

    return candidates[:12]


# =========================================================
# 角色评分 (position_quality_score)
# =========================================================
def calc_position_quality_score(pnl_pct, price, ma5, dd_from_high,
                                day_ret, close_to_day_high,
                                hold_days, signal_score):
    """按方案文档 §12 粗档位评分"""
    score = 0

    # 浮盈
    if pnl_pct >= 0.10:
        score += 30
    elif pnl_pct >= 0.05:
        score += 20
    elif pnl_pct >= 0:
        score += 5
    else:
        score -= 10

    # MA5 状态
    if ma5 is not None and price is not None:
        if price >= ma5:
            score += 15
        else:
            score -= 20

    # 从持仓最高点回撤
    if dd_from_high is not None:
        if dd_from_high <= 0.03:
            score += 10
        elif dd_from_high >= 0.12:
            score -= 35
        elif dd_from_high >= 0.08:
            score -= 20

    # 日内强度
    if day_ret is not None:
        if day_ret >= 0.05:
            score += 15
        elif day_ret >= 0.02:
            score += 8
        elif day_ret < -0.03:
            score -= 10

    # 接近日内高点
    if close_to_day_high is not None:
        if close_to_day_high >= 0.97:
            score += 10
        elif close_to_day_high < 0.93:
            score -= 10

    # 持仓天数
    if hold_days is not None:
        if hold_days <= 1:
            pass
        elif 2 <= hold_days <= 5:
            score += 5
        elif hold_days > 5 and pnl_pct <= 0:
            score -= 15

    # 原始信号分
    if signal_score is not None:
        if signal_score >= 0.75:
            score += 10
        elif signal_score >= 0.70:
            score += 5

    return score


# =========================================================
# 持仓对象
# =========================================================
class SimPosition:
    """模拟持仓"""
    __slots__ = [
        'stock', 'name', 'role', 'buy_date', 'buy_price', 'shares',
        'cost_basis', 'peak_price', 'entry_type', 'signal_score',
        'signal_date', 'max_hold_days',
        'buy_cost', 'promoted', 'promotion_date', 'promotion_price', 'replaced_core',
    ]

    def __init__(self, stock, role, buy_date, buy_price, shares,
                 cost_basis, entry_type='deep_water', signal_score=0.0,
                 signal_date=None, max_hold_days=None, name=''):
        self.stock = stock
        self.name = name
        self.role = role  # 'core' or 'satellite'
        self.buy_date = buy_date
        self.buy_price = buy_price
        self.shares = shares
        self.cost_basis = cost_basis
        self.peak_price = buy_price
        self.entry_type = entry_type
        self.signal_score = signal_score
        self.signal_date = signal_date
        self.max_hold_days = max_hold_days or (5 if role == 'satellite' else 999)
        self.buy_cost = 0.0
        self.promoted = False
        self.promotion_date = None
        self.promotion_price = 0.0
        self.replaced_core = ''


# =========================================================
# 模拟引擎
# =========================================================
class SimEngine:
    """
    单个策略变体的模拟引擎。
    支持三种变体:
      - baseline_core_only: 只做核心仓
      - baseline_core_satellite: 核心 + 卫星, 不做晋级/降级
      - role_rotation_observer: 核心 + 卫星 + 晋级/降级
    """

    def __init__(self, variant_name, params=None, cost_multiplier=1.0, slippage_multiplier=1.0):
        self.variant = variant_name
        self.params = params or {}
        self.cost_multiplier = cost_multiplier
        self.slippage_multiplier = slippage_multiplier

        # 仓位上限
        self.max_total_ratio = self.params.get('max_total_cap', MAX_TOTAL_RATIO)
        self.satellite_ratio = self.params.get('satellite_slot_ratio', SATELLITE_RATIO)
        self.promotion_margin = self.params.get('promotion_margin', PROMOTION_MARGIN)
        self.satellite_min_pnl = self.params.get('satellite_min_pnl', SATELLITE_MIN_PNL)
        self.core_drawdown_weak = self.params.get('core_drawdown_weak', CORE_DRAWDOWN_WEAK)

        # 状态
        self.cash = INITIAL_CASH
        self.positions = OrderedDict()       # stock -> SimPosition
        self.watch_pool = OrderedDict()      # stock -> watch_item
        self.cooldown = {}                   # stock -> expiry_date

        # 记录
        self.trades = []
        self.daily_nav = []
        self.daily_positions = []
        self.decisions = []
        self.diagnostics = []
        self.promotion_attributions = []
        self.cap_checks = []
        self.trade_days_set = set()

        # 计数
        self.rotation_done_today = False

    def _calc_cost(self, price, shares, direction='buy'):
        """考虑滑点和手续费的实际成交金额"""
        slippage = SLIPPAGE_PER_SHARE * self.slippage_multiplier
        comm_rate = COMMISSION_RATE * self.cost_multiplier
        tax_rate = STAMP_TAX_RATE * self.cost_multiplier
        if direction == 'buy':
            exec_price = price + slippage
            amount = exec_price * shares
            commission = max(amount * comm_rate, 5.0)
            return amount + commission, exec_price
        else:
            exec_price = max(price - slippage, 0.01)
            amount = exec_price * shares
            commission = max(amount * comm_rate, 5.0)
            stamp_tax = amount * tax_rate
            return amount - commission - stamp_tax, exec_price

    def _total_value(self, prices):
        """计算总市值"""
        val = self.cash
        for stock, pos in self.positions.items():
            p = prices.get(stock, pos.buy_price)
            val += pos.shares * p
        return val

    def _position_ratio(self, prices, role=None):
        """计算持仓比例"""
        tv = self._total_value(prices)
        if tv <= 0:
            return 0.0
        val = 0.0
        for stock, pos in self.positions.items():
            if role is not None and pos.role != role:
                continue
            p = prices.get(stock, pos.buy_price)
            val += pos.shares * p
        return val / tv

    def _core_count(self):
        return sum(1 for p in self.positions.values() if p.role == 'core')

    def _satellite_count(self):
        return sum(1 for p in self.positions.values() if p.role == 'satellite')

    def _hold_days(self, pos, current_date, trade_days_set):
        """计算交易日持有天数"""
        count = 0
        for td in trade_days_set:
            if pos.buy_date < td <= current_date:
                count += 1
        return count

    def _get_ma5(self, stock, date, daily_cache):
        """获取 MA5"""
        key = (stock, date)
        if key in daily_cache:
            closes = daily_cache[key]
            if len(closes) >= 5:
                return float(np.mean(closes[-5:]))
        return None

    def _sim_buy(self, stock, date, price, target_ratio, prices,
                 role='core', entry_type='deep_water', signal_score=0.0,
                 signal_date=None, max_hold_days=None, name=''):
        """模拟买入"""
        tv = self._total_value(prices)
        current_ratio = self._position_ratio(prices)
        remaining = self.max_total_ratio - current_ratio
        if remaining < MIN_BUY_RATIO:
            return False, 'cap_exceeded'

        actual_ratio = min(target_ratio, remaining, MAX_SINGLE_RATIO)
        if actual_ratio < MIN_BUY_RATIO:
            return False, 'ratio_too_small'

        buy_value = tv * actual_ratio
        if buy_value > self.cash:
            buy_value = self.cash
            actual_ratio = buy_value / tv if tv > 0 else 0
        if actual_ratio < MIN_BUY_RATIO:
            return False, 'insufficient_cash'

        shares = int(buy_value / (price + (SLIPPAGE_PER_SHARE * self.slippage_multiplier)) / 100) * 100
        if shares < 100:
            return False, 'lot_size'

        cost, exec_price = self._calc_cost(price, shares, 'buy')
        if cost > self.cash:
            return False, 'cash_after_cost'

        self.cash -= cost
        pos = SimPosition(
            stock=stock, role=role, buy_date=date, buy_price=exec_price,
            shares=shares, cost_basis=exec_price, entry_type=entry_type,
            signal_score=signal_score, signal_date=signal_date,
            max_hold_days=max_hold_days, name=name,
        )
        pos.buy_cost = cost
        self.positions[stock] = pos
        self.cooldown.pop(stock, None)

        self.trades.append({
            'date': date, 'stock': stock, 'name': name,
            'action': 'BUY', 'role': role,
            'price': exec_price, 'shares': shares,
            'value': cost, 'reason': 'open_{}'.format(role),
            'variant': self.variant,
            'entry_type': entry_type,
            'signal_score': signal_score,
        })
        return True, 'ok'

    def _sim_sell(self, stock, date, price, reason='exit'):
        """模拟卖出"""
        pos = self.positions.get(stock)
        if pos is None:
            return False
        proceeds, exec_price = self._calc_cost(price, pos.shares, 'sell')
        pnl = exec_price / pos.cost_basis - 1 if pos.cost_basis > 0 else 0
        pnl_val = proceeds - pos.buy_cost
        self.cash += proceeds

        trade_category = 'promoted_core' if pos.promoted else pos.role

        self.trades.append({
            'date': date, 'stock': stock, 'name': pos.name,
            'action': 'SELL', 'role': pos.role,
            'price': exec_price, 'shares': pos.shares,
            'value': proceeds, 'reason': reason,
            'pnl_pct': pnl,
            'pnl_val': pnl_val,
            'trade_category': trade_category,
            'hold_days_cal': (date - pos.buy_date).days,
            'variant': self.variant,
            'entry_type': pos.entry_type,
            'signal_score': pos.signal_score,
        })

        if pos.promoted:
            hold_days_after_promotion = len([td for td in self.trade_days_set if pos.promotion_date < td <= date])
            pnl_post_promotion = proceeds - (pos.promotion_price * pos.shares)
            ret_post_promotion = exec_price / pos.promotion_price - 1.0 if pos.promotion_price > 0 else 0.0

            self.promotion_attributions.append({
                'promotion_date': pos.promotion_date,
                'satellite_stock': pos.stock,
                'replaced_core': pos.replaced_core,
                'exit_date': date,
                'final_pnl': pnl_val,
                'final_ret': pnl,
                'hold_days_after_promotion': hold_days_after_promotion,
                'pnl_post_promotion': pnl_post_promotion,
                'ret_post_promotion': ret_post_promotion,
                'status': 'exited'
            })

        del self.positions[stock]
        self.cooldown[stock] = date + datetime.timedelta(days=5)
        return True

    def finalize_simulation(self, last_date, last_prices):
        """在模拟结束时处理未平仓头寸等"""
        for stock, pos in self.positions.items():
            if pos.promoted:
                p = last_prices.get(stock, pos.buy_price)
                proceeds, exec_price = self._calc_cost(p, pos.shares, 'sell')
                pnl = exec_price / pos.cost_basis - 1 if pos.cost_basis > 0 else 0
                pnl_val = proceeds - pos.buy_cost
                hold_days_after_promotion = len([td for td in self.trade_days_set if pos.promotion_date < td <= last_date])
                pnl_post_promotion = proceeds - (pos.promotion_price * pos.shares)
                ret_post_promotion = exec_price / pos.promotion_price - 1.0 if pos.promotion_price > 0 else 0.0

                self.promotion_attributions.append({
                    'promotion_date': pos.promotion_date,
                    'satellite_stock': pos.stock,
                    'replaced_core': pos.replaced_core,
                    'exit_date': 'held',
                    'final_pnl': pnl_val,
                    'final_ret': pnl,
                    'hold_days_after_promotion': hold_days_after_promotion,
                    'pnl_post_promotion': pnl_post_promotion,
                    'ret_post_promotion': ret_post_promotion,
                    'status': 'held'
                })

    # ------- 每日流程 -------

    def daily_step(self, date, prev_date, candidates, prices, daily_cache,
                   market_state, trade_days_set, base_diag=None):
        """
        一个交易日的完整流程:
        1. 更新 peak_price
        2. 核心仓退出检查
        3. 卫星仓退出检查
        4. 角色轮动检查(仅 role_rotation_observer)
        5. 核心仓买入
        6. 维护 watch_pool
        7. 卫星仓确认买入
        8. 记录日终状态
        """
        self.diag_today = dict(base_diag) if base_diag else {}
        self.diag_today['variant'] = self.variant
        self.diag_today['date'] = date
        for k in ['satellite_confirm_count', 'core_buy_attempt_count', 'core_buy_success_count',
                  'satellite_buy_attempt_count', 'satellite_buy_success_count',
                  'buy_skip_no_candidate', 'buy_skip_no_price', 'buy_skip_paused', 'buy_skip_st',
                  'buy_skip_limit_up', 'buy_skip_cap_full', 'buy_skip_duplicate_role', 'buy_skip_other']:
            self.diag_today[k] = 0

        # Initialize new fields if not set by candidates generation
        for k in ['price_batch_error', 'candidate_skip_price_batch_error', 'candidate_skip_no_price',
                  'trend_data_len_min', 'trend_data_len_mean', 'trend_filter_executed_count',
                  'trend_filter_skipped_count', 'auction_unavailable']:
            if k not in self.diag_today:
                self.diag_today[k] = 0
        self.diag_today['watch_pool_count'] = len(self.watch_pool)
        self.diag_today['notes'] = ''

        self.rotation_done_today = False
        self.trade_days_set = trade_days_set

        # 清理过期冷却
        for s in list(self.cooldown):
            if self.cooldown[s] <= date:
                del self.cooldown[s]

        # Step 0: 更新 peak_price
        for stock, pos in self.positions.items():
            p = prices.get(stock)
            if p and p > pos.peak_price:
                pos.peak_price = p

        # Step 1: 核心仓退出
        for stock in list(self.positions):
            pos = self.positions.get(stock)
            if pos is None or pos.role != 'core':
                continue
            p = prices.get(stock, pos.buy_price)
            pnl = p / pos.cost_basis - 1 if pos.cost_basis > 0 else 0
            ma5 = self._get_ma5(stock, date, daily_cache)
            below_ma5 = ma5 is not None and p < ma5
            hd = self._hold_days(pos, date, trade_days_set)
            dd_from_high = 1 - p / pos.peak_price if pos.peak_price > 0 else 0

            reason = None
            if pnl <= CORE_STOP_LOSS:
                reason = 'core_stop_loss'
            elif below_ma5 and pnl <= 0:
                reason = 'core_below_ma5_loss'
            elif hd >= CORE_HOLD_LOSS_DAYS and pnl <= 0:
                reason = 'core_hold_stale'
            elif dd_from_high >= CORE_DD_FROM_HIGH:
                reason = 'core_drawdown_exit'

            if reason:
                self._sim_sell(stock, date, p, reason)
                self.decisions.append({
                    'date': date, 'stock': stock, 'name': pos.name,
                    'decision': 'CORE_EXIT', 'reason': reason,
                    'pnl_pct': pnl, 'variant': self.variant,
                })

        # Step 2: 卫星仓退出
        if self.variant != 'baseline_core_only':
            for stock in list(self.positions):
                pos = self.positions.get(stock)
                if pos is None or pos.role != 'satellite':
                    continue
                p = prices.get(stock, pos.buy_price)
                pnl = p / pos.cost_basis - 1 if pos.cost_basis > 0 else 0
                ma5 = self._get_ma5(stock, date, daily_cache)
                below_ma5 = ma5 is not None and p < ma5
                hd = self._hold_days(pos, date, trade_days_set)

                reason = None
                if hd >= SATELLITE_MAX_HOLD_DAYS:
                    reason = 'satellite_max_hold'
                elif pnl <= SATELLITE_STOP_LOSS:
                    reason = 'satellite_stop_loss'
                elif below_ma5 and pnl <= 0:
                    reason = 'satellite_below_ma5_loss'
                elif hd > SATELLITE_HOLD_LOSS_DAYS and pnl <= 0:
                    reason = 'satellite_stale'

                if reason:
                    self._sim_sell(stock, date, p, reason)
                    self.decisions.append({
                        'date': date, 'stock': stock, 'name': pos.name,
                        'decision': 'SATELLITE_EXIT', 'reason': reason,
                        'pnl_pct': pnl, 'variant': self.variant,
                    })

        # Step 3: 角色轮动
        if self.variant == 'role_rotation_observer' and not self.rotation_done_today:
            self._check_role_rotation(date, prices, daily_cache,
                                      market_state, trade_days_set)

        # Step 3.5: 记录买入前仓位比例
        pre_buy_total_ratio = self._position_ratio(prices)

        # Step 4: 核心仓买入
        self._try_core_buy(date, candidates, prices, market_state)

        # Step 5: 维护 watch_pool
        if self.variant != 'baseline_core_only':
            self._update_watch_pool(date, candidates)

        # Step 6: 卫星确认买入
        if self.variant != 'baseline_core_only':
            self._try_satellite_confirm(date, prices, daily_cache,
                                        market_state, trade_days_set)

        # Step 7: 记录日终状态
        tv = self._total_value(prices)
        self.daily_nav.append({
            'date': date, 'total_value': tv,
            'nav': tv / INITIAL_CASH,
            'cash': self.cash,
            'position_count': len(self.positions),
            'core_count': self._core_count(),
            'satellite_count': self._satellite_count(),
            'core_ratio': self._position_ratio(prices, 'core'),
            'satellite_ratio': self._position_ratio(prices, 'satellite'),
            'total_ratio': self._position_ratio(prices),
            'market_state': market_state,
            'variant': self.variant,
        })

        # 记录持仓快照 (解决问题 4: 规范 positions 字段映射)
        for stock, pos in self.positions.items():
            p = prices.get(stock, pos.buy_price)
            pnl = p / pos.cost_basis - 1 if pos.cost_basis > 0 else 0
            hd = self._hold_days(pos, date, trade_days_set)
            self.daily_positions.append({
                'date': date,
                'variant': self.variant,
                'stock': stock,
                'name': pos.name,
                'role': pos.role,
                'shares': pos.shares,
                'price': p,
                'market_value': pos.shares * p,
                'cost': pos.cost_basis * pos.shares,
                'pnl': (p - pos.cost_basis) * pos.shares,
                'pnl_pct': pnl,
                'weight': (pos.shares * p) / tv if tv > 0 else 0.0,
                'hold_days': hd
            })

        # 计算买入后与收盘后仓位 cap 并记录
        post_buy_pos_value = 0.0
        for stock, pos in self.positions.items():
            if pos.buy_date == date:
                post_buy_pos_value += pos.shares * pos.buy_price
            else:
                p = prices.get(stock, pos.buy_price)
                post_buy_pos_value += pos.shares * p

        post_buy_total_value = self.cash + post_buy_pos_value
        post_buy_total_ratio = post_buy_pos_value / post_buy_total_value if post_buy_total_value > 0 else 0.0

        cap_limit = self.max_total_ratio
        cap_exceeded_on_buy = 1 if post_buy_total_ratio > cap_limit + 1e-5 else 0

        mark_to_market_ratio = self._position_ratio(prices)
        cap_exceeded_after_mark_to_market = 1 if mark_to_market_ratio > cap_limit + 1e-5 else 0

        self.cap_checks.append({
            'date': date,
            'variant': self.variant,
            'pre_buy_total_ratio': pre_buy_total_ratio,
            'post_buy_total_ratio': post_buy_total_ratio,
            'cap_limit': cap_limit,
            'cap_exceeded_on_buy': cap_exceeded_on_buy,
            'cap_exceeded_after_mark_to_market': cap_exceeded_after_mark_to_market,
        })

        self.diagnostics.append(self.diag_today)

    def _try_core_buy(self, date, candidates, prices, market_state):
        """核心仓买入"""
        if market_state == 'bear':
            self.diag_today['notes'] += 'bear_market;'
            return
        core_count = self._core_count()
        if core_count >= 2:
            self.diag_today['buy_skip_cap_full'] += 1
            return

        # 只选 deep_water 候选
        dw_candidates = [c for c in candidates if c.get('entry_type') == 'deep_water']
        if not dw_candidates:
            self.diag_today['buy_skip_no_candidate'] += 1
            return

        top_ratios = [CORE_TOP1_RATIO, CORE_TOP2_RATIO]
        bought = 0
        for c in dw_candidates:
            self.diag_today['core_buy_attempt_count'] += 1
            if core_count + bought >= 2:
                self.diag_today['buy_skip_cap_full'] += 1
                break
            stock = c['stock']
            if stock in self.positions or stock in self.cooldown:
                self.diag_today['buy_skip_duplicate_role'] += 1
                continue
            price = c.get('open_price', 0)
            if price <= 0:
                self.diag_today['buy_skip_no_price'] += 1
                continue
            # 涨停不买
            hl = c.get('high_limit', 0)
            if hl > 0 and price >= hl * 0.995:
                self.diag_today['buy_skip_limit_up'] += 1
                continue

            idx = core_count + bought
            target_ratio = top_ratios[idx] if idx < len(top_ratios) else CORE_TOP2_RATIO

            ok, reason = self._sim_buy(
                stock, date, price, target_ratio, prices,
                role='core', entry_type=c.get('entry_type', 'deep_water'),
                signal_score=c.get('score', 0), name=c.get('name', ''),
            )
            if ok:
                bought += 1
                self.diag_today['core_buy_success_count'] += 1
                self.decisions.append({
                    'date': date, 'stock': stock, 'name': c.get('name', ''),
                    'decision': 'CORE_BUY', 'reason': 'dragon_pool_top',
                    'score': c.get('score', 0), 'variant': self.variant,
                })
            else:
                if reason in ('cap_exceeded', 'insufficient_cash'):
                    self.diag_today['buy_skip_cap_full'] += 1
                else:
                    self.diag_today['buy_skip_other'] += 1

    def _update_watch_pool(self, date, candidates):
        """更新观察池: deep_water 候选未买入核心仓的进入"""
        # 清理过期
        for stock in list(self.watch_pool):
            item = self.watch_pool[stock]
            days_elapsed = (date - item['signal_date']).days
            if days_elapsed > SATELLITE_WATCH_DAYS + 2:
                del self.watch_pool[stock]
            elif stock in self.positions:
                del self.watch_pool[stock]

        # 添加新候选
        for c in candidates:
            if c.get('entry_type') != 'deep_water':
                continue
            stock = c['stock']
            if stock in self.positions or stock in self.watch_pool:
                continue
            if stock in self.cooldown:
                continue
            self.watch_pool[stock] = {
                'stock': stock,
                'name': c.get('name', ''),
                'signal_date': date,
                'signal_price': c.get('close_price', c.get('open_price', 0)),
                'signal_score': c.get('score', 0),
                'signal_rank': c.get('rank', 0),
                'signal_entry_type': 'deep_water',
            }

    def _try_satellite_confirm(self, date, prices, daily_cache,
                               market_state, trade_days_set):
        """卫星仓确认买入"""
        if self._satellite_count() >= 1:
            self.diag_today['buy_skip_cap_full'] += 1
            return
        if market_state == 'bear':
            return

        for stock, item in list(self.watch_pool.items()):
            if stock in self.positions:
                self.diag_today['buy_skip_duplicate_role'] += 1
                continue
            if stock in self.cooldown:
                self.diag_today['buy_skip_duplicate_role'] += 1
                continue
            if self._satellite_count() >= 1:
                self.diag_today['buy_skip_cap_full'] += 1
                break

            self.diag_today['satellite_confirm_count'] += 1
            days_after = 0
            for td in trade_days_set:
                if item['signal_date'] < td <= date:
                    days_after += 1
            if days_after not in (1, 2, 3):
                continue

            # 获取确认日行情
            p = prices.get(stock)
            if p is None or p <= 0:
                self.diag_today['buy_skip_no_price'] += 1
                continue

            signal_price = item.get('signal_price', 0)
            if signal_price <= 0:
                self.diag_today['buy_skip_no_price'] += 1
                continue

            ret_from_signal = p / signal_price - 1.0

            # 获取前日收盘
            prev_close = None
            key = (stock, date)
            if key in daily_cache:
                closes = daily_cache[key]
                if len(closes) >= 2:
                    prev_close = float(closes[-2])
            if prev_close is None or prev_close <= 0:
                self.diag_today['buy_skip_no_price'] += 1
                continue

            day_ret = p / prev_close - 1.0

            # 获取日内高低
            day_high = prices.get(stock + '_high', p)
            day_low = prices.get(stock + '_low', p)
            close_to_day_high = p / max(day_high, p, 0.01)

            # 量比
            vol = prices.get(stock + '_volume', 0)
            prev_vol = None
            if key in daily_cache:
                # daily_cache 中存了 close 序列，尝试从 volume 缓存获取
                vol_key = (stock, date, 'volume')
                if vol_key in daily_cache:
                    prev_vol = daily_cache[vol_key]
            if prev_vol is None or prev_vol <= 0:
                prev_vol = vol  # fallback
            volume_ratio = vol / prev_vol if prev_vol > 0 else 1.0

            # MA5
            ma5 = self._get_ma5(stock, date, daily_cache)
            ma5_distance = (p / ma5 - 1.0) if ma5 and ma5 > 0 else 0

            # Rule D 检查
            passes = (
                ret_from_signal >= SATELLITE_RET_FROM_SIGNAL
                and day_ret >= SATELLITE_DAY_RET
                and SATELLITE_VOL_RATIO_MIN <= volume_ratio <= SATELLITE_VOL_RATIO_MAX
                and ma5_distance <= SATELLITE_MA5_DIST_MAX
                and close_to_day_high >= SATELLITE_CLOSE_TO_HIGH
            )

            if not passes:
                continue

            self.diag_today['satellite_buy_attempt_count'] += 1

            # 仓位控制
            remaining_cap = self.max_total_ratio - self._position_ratio(prices)
            if remaining_cap <= MIN_BUY_RATIO:
                self.diag_today['buy_skip_cap_full'] += 1
                continue
            actual_ratio = min(self.satellite_ratio, remaining_cap)
            if actual_ratio < MIN_BUY_RATIO:
                self.diag_today['buy_skip_cap_full'] += 1
                continue

            ok, reason = self._sim_buy(
                stock, date, p, actual_ratio, prices,
                role='satellite', entry_type='deep_water',
                signal_score=item.get('signal_score', 0),
                signal_date=item.get('signal_date'),
                max_hold_days=SATELLITE_MAX_HOLD_DAYS,
                name=item.get('name', ''),
            )
            if ok:
                self.diag_today['satellite_buy_success_count'] += 1
                self.watch_pool.pop(stock, None)
                self.decisions.append({
                    'date': date, 'stock': stock,
                    'name': item.get('name', ''),
                    'decision': 'SATELLITE_CONFIRM_BUY',
                    'reason': 'rule_D_deep_water',
                    'variant': self.variant,
                })
            else:
                if reason in ('cap_exceeded', 'insufficient_cash'):
                    self.diag_today['buy_skip_cap_full'] += 1
                else:
                    self.diag_today['buy_skip_other'] += 1

    def _check_role_rotation(self, date, prices, daily_cache,
                             market_state, trade_days_set):
        """角色轮动: 卫星晋级核心 / 弱核心退出"""
        if market_state == 'bear':
            return

        satellites = [s for s, p in self.positions.items() if p.role == 'satellite']
        cores = [s for s, p in self.positions.items() if p.role == 'core']

        if not satellites or not cores:
            return

        # 对每个卫星检查晋级条件
        for sat_stock in satellites:
            if self.rotation_done_today:
                break

            sat_pos = self.positions.get(sat_stock)
            if sat_pos is None:
                continue

            sat_price = prices.get(sat_stock, sat_pos.buy_price)
            sat_pnl = sat_price / sat_pos.cost_basis - 1 if sat_pos.cost_basis > 0 else 0
            sat_ma5 = self._get_ma5(sat_stock, date, daily_cache)
            sat_hd = self._hold_days(sat_pos, date, trade_days_set)
            sat_dd = 1 - sat_price / sat_pos.peak_price if sat_pos.peak_price > 0 else 0

            # 卫星晋级条件
            if sat_hd < 1:
                continue
            if sat_pnl < self.satellite_min_pnl:
                continue
            if sat_ma5 is not None and sat_price < sat_ma5:
                continue

            day_high = prices.get(sat_stock + '_high', sat_price)
            sat_c2h = sat_price / max(day_high, sat_price, 0.01)
            if sat_c2h < 0.96:
                continue

            # 卫星评分
            sat_day_ret = 0  # 简化
            sat_quality = calc_position_quality_score(
                sat_pnl, sat_price, sat_ma5, sat_dd,
                sat_day_ret, sat_c2h, sat_hd, sat_pos.signal_score,
            )

            # 找最弱核心
            weakest_core = None
            weakest_score = float('inf')
            for core_stock in cores:
                core_pos = self.positions.get(core_stock)
                if core_pos is None:
                    continue
                core_price = prices.get(core_stock, core_pos.buy_price)
                core_pnl = core_price / core_pos.cost_basis - 1 \
                    if core_pos.cost_basis > 0 else 0
                core_ma5 = self._get_ma5(core_stock, date, daily_cache)
                core_dd = 1 - core_price / core_pos.peak_price \
                    if core_pos.peak_price > 0 else 0
                core_hd = self._hold_days(core_pos, date, trade_days_set)
                core_c2h = 1.0
                core_day_ret = 0

                core_quality = calc_position_quality_score(
                    core_pnl, core_price, core_ma5, core_dd,
                    core_day_ret, core_c2h, core_hd, core_pos.signal_score,
                )

                # 弱化条件
                is_weak = (
                    core_pnl <= 0
                    or (core_ma5 is not None and core_price < core_ma5)
                    or core_dd >= self.core_drawdown_weak
                    or (core_hd > 3 and core_pnl <= 0.02)
                )
                if not is_weak:
                    continue

                if core_quality < weakest_score:
                    weakest_score = core_quality
                    weakest_core = core_stock

            if weakest_core is None:
                continue

            # 晋级条件: satellite_score >= weakest_core_score + margin
            if sat_quality < weakest_score + self.promotion_margin:
                self.decisions.append({
                    'date': date, 'stock': sat_stock,
                    'name': sat_pos.name,
                    'decision': 'ROLE_PROMOTION_SKIP',
                    'reason': 'margin_insufficient',
                    'sat_score': sat_quality,
                    'core_score': weakest_score,
                    'variant': self.variant,
                })
                continue

            # 执行晋级: 卖出弱核心, 卫星升核心
            core_pos = self.positions.get(weakest_core)
            core_price = prices.get(weakest_core, core_pos.buy_price)
            self._sim_sell(weakest_core, date, core_price,
                           reason='weak_core_replaced')

            sat_pos.role = 'core'
            sat_pos.max_hold_days = 999
            sat_pos.promoted = True
            sat_pos.promotion_date = date
            sat_pos.promotion_price = sat_price
            sat_pos.replaced_core = weakest_core

            self.rotation_done_today = True
            self.decisions.append({
                'date': date, 'stock': sat_stock,
                'name': sat_pos.name,
                'decision': 'ROLE_PROMOTION_EXECUTE',
                'reason': 'satellite_promoted_to_core',
                'sat_score': sat_quality,
                'core_score': weakest_score,
                'replaced_core': weakest_core,
                'variant': self.variant,
            })


# =========================================================
# 批量数据预加载
# =========================================================
def preload_daily_data(stocks, trade_days):
    """预加载股票日线数据，返回 {(stock, date): close_array}"""
    cache = {}
    if not stocks or not trade_days:
        return cache

    start = trade_days[0] - datetime.timedelta(days=40)
    end = trade_days[-1]

    # 分批加载
    batch_size = 50
    stock_list = list(stocks)
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        try:
            df = get_price(
                batch, start_date=str(start), end_date=str(end),
                frequency='daily',
                fields=['close', 'high', 'low', 'volume', 'open',
                        'high_limit', 'paused'],
                panel=False,
            )
            if df is None or df.empty:
                continue
            df = df.sort_values(['code', 'time'])
            for stock, sdf in df.groupby('code', sort=False):
                sdf = sdf.sort_values('time')
                for td in trade_days:
                    mask = sdf['time'] <= pd.Timestamp(td)
                    sub = sdf[mask].tail(25)
                    if len(sub) > 0:
                        cache[(stock, td)] = sub['close'].values

                        # 存储当日行情到 prices 用的缓存
                        day_mask = sdf['time'].dt.date == td
                        day_rows = sdf[day_mask]
                        if len(day_rows) > 0:
                            row = day_rows.iloc[-1]
                            cache[(stock, td, 'close')] = float(row['close'])
                            cache[(stock, td, 'high')] = float(row['high'])
                            cache[(stock, td, 'low')] = float(row['low'])
                            cache[(stock, td, 'open')] = float(row['open'])
                            cache[(stock, td, 'volume')] = float(row['volume'])
                            cache[(stock, td, 'high_limit')] = float(row['high_limit'])
                            cache[(stock, td, 'paused')] = float(row['paused'])

                        # 量比缓存
                        if len(sub) >= 2:
                            cache[(stock, td, 'volume')] = float(
                                sdf[mask]['volume'].iloc[-1]
                                if 'volume' in sdf.columns else 0
                            )

        except Exception as e:
            _log("WARN: preload batch error: {}".format(e))

    return cache


def get_day_prices(stocks, date, daily_cache):
    """从缓存获取当日行情 dict"""
    prices = {}
    for stock in stocks:
        close_key = (stock, date, 'close')
        if close_key in daily_cache:
            prices[stock] = daily_cache[close_key]
            prices[stock + '_high'] = daily_cache.get((stock, date, 'high'),
                                                      prices[stock])
            prices[stock + '_low'] = daily_cache.get((stock, date, 'low'),
                                                     prices[stock])
            prices[stock + '_volume'] = daily_cache.get((stock, date, 'volume'), 0)
    return prices


# =========================================================
# 报告生成
# =========================================================
def normalize_decisions_df(df):
    """确保 decisions_df 至少包含指定字段，不存在的列自动补空或 NaN"""
    if df is None:
        df = pd.DataFrame()
    else:
        df = df.copy()

    cols = [
        'date', 'variant', 'decision', 'decision_type', 'stock', 'name',
        'role', 'reason', 'score', 'pnl_pct', 'market_state', 'extra',
        'replaced_core', 'replacement_stock', 'promotion_from_role', 'promotion_to_role'
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    return df


def calc_summary(nav_df, trades_df, decisions_df, variant, segment=None):
    """计算汇总统计"""
    if nav_df.empty:
        return {}

    nav_series = nav_df['nav']
    total_return = float(nav_series.iloc[-1] / nav_series.iloc[0] - 1) \
        if len(nav_series) > 0 else 0
    trading_days = len(nav_series)

    # 年化
    annual_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

    # 最大回撤
    peak = nav_series.expanding().max()
    drawdown = (nav_series - peak) / peak
    max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0

    # 日收益率
    daily_ret = nav_series.pct_change().dropna()
    sharpe = float(daily_ret.mean() / daily_ret.std() * np.sqrt(252)) \
        if len(daily_ret) > 1 and daily_ret.std() > 0 else 0

    # 交易统计
    sells = trades_df[trades_df['action'] == 'SELL'] if not trades_df.empty else pd.DataFrame()
    trade_count = len(sells)
    win_count = len(sells[sells['pnl_pct'] > 0]) if 'pnl_pct' in sells.columns else 0
    win_rate = win_count / trade_count if trade_count > 0 else 0
    avg_pnl = float(sells['pnl_pct'].mean()) if 'pnl_pct' in sells.columns and len(sells) > 0 else 0

    # 晋级/降级/替代/卖出统计
    promotion_count = 0
    demotion_count = 0
    replacement_count = 0
    exit_count = len(sells)

    orig_has_decision = False
    orig_has_decision_type = False
    orig_has_replaced_core = False
    if not decisions_df.empty:
        orig_has_decision = 'decision' in decisions_df.columns
        orig_has_decision_type = 'decision_type' in decisions_df.columns
        orig_has_replaced_core = 'replaced_core' in decisions_df.columns

    decisions_df = normalize_decisions_df(decisions_df)

    if not decisions_df.empty:
        # promotion_count
        if orig_has_decision:
            promotion_count = len(decisions_df[decisions_df['decision'] == 'ROLE_PROMOTION_EXECUTE'])
        elif orig_has_decision_type:
            promotion_count = len(decisions_df[decisions_df['decision_type'] == 'ROLE_PROMOTION_EXECUTE'])
        else:
            promotion_count = 0

        # replacement_count
        if orig_has_replaced_core:
            replaced_col = decisions_df['replaced_core']
            valid_replaced = replaced_col.notna() & (replaced_col != '')
            if orig_has_decision:
                replacement_count = len(decisions_df[(decisions_df['decision'] == 'ROLE_PROMOTION_EXECUTE') & valid_replaced])
            elif orig_has_decision_type:
                replacement_count = len(decisions_df[(decisions_df['decision_type'] == 'ROLE_PROMOTION_EXECUTE') & valid_replaced])
            else:
                replacement_count = 0
        else:
            replacement_count = 0

        demotion_count = 0

    # 仓位使用率
    avg_position = float(nav_df['total_ratio'].mean()) if 'total_ratio' in nav_df.columns else 0

    return {
        'variant': variant,
        'segment': segment or 'full',
        'trading_days': trading_days,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe,
        'trade_count': trade_count,
        'win_count': win_count,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'promotion_count': promotion_count,
        'demotion_count': demotion_count,
        'replacement_count': replacement_count,
        'exit_count': exit_count,
        'avg_position_ratio': avg_position,
    }


def calc_monthly(nav_df):
    """月度收益"""
    if nav_df.empty:
        return pd.DataFrame()
    df = nav_df.copy()
    df['month'] = df['date'].apply(lambda d: d.strftime('%Y-%m'))
    monthly = []
    for month, mdf in df.groupby('month'):
        if len(mdf) < 2:
            continue
        ret = float(mdf['nav'].iloc[-1] / mdf['nav'].iloc[0] - 1)
        monthly.append({'month': month, 'return': ret,
                        'variant': mdf['variant'].iloc[0]})
    return pd.DataFrame(monthly)


def calc_rolling(nav_df, window=20):
    """滚动收益/夏普"""
    if nav_df.empty or len(nav_df) < window:
        return pd.DataFrame()
    df = nav_df.copy()
    daily_ret = df['nav'].pct_change()
    df['rolling_return'] = daily_ret.rolling(window).apply(
        lambda x: float((1 + x).prod() - 1), raw=False)
    df['rolling_sharpe'] = daily_ret.rolling(window).apply(
        lambda x: float(x.mean() / x.std() * np.sqrt(252))
        if x.std() > 0 else 0, raw=False)
    return df[['date', 'rolling_return', 'rolling_sharpe', 'variant']].dropna()


def calc_overfit_check(trades_df, nav_df, variant):
    """重算盈利贡献集中度"""
    if trades_df.empty:
        return pd.DataFrame()

    sells = trades_df[(trades_df['variant'] == variant) & (trades_df['action'] == 'SELL')].copy()
    if sells.empty:
        return pd.DataFrame()

    rows = []
    categories = ['core', 'satellite', 'promoted_core', 'all']
    for cat in categories:
        if cat == 'all':
            cat_sells = sells
        else:
            cat_sells = sells[sells['trade_category'] == cat] if 'trade_category' in sells.columns else sells[sells['role'] == cat]

        trade_count = len(cat_sells)
        if trade_count == 0:
            rows.append({
                'variant': variant,
                'category': cat,
                'trade_count': 0,
                'total_pnl_val': 0.0,
                'top1_profit_share': 0.0,
                'top3_profit_share': 0.0,
                'top5_profit_share': 0.0,
            })
            continue

        total_pnl_val = float(cat_sells['pnl_val'].sum()) if 'pnl_val' in cat_sells.columns else 0.0

        sells_sorted = cat_sells.sort_values('pnl_val', ascending=False) if 'pnl_val' in cat_sells.columns else cat_sells

        top1_share = 0.0
        top3_share = 0.0
        top5_share = 0.0

        if total_pnl_val > 0:
            top1_val = float(sells_sorted['pnl_val'].head(1).sum())
            top3_val = float(sells_sorted['pnl_val'].head(3).sum())
            top5_val = float(sells_sorted['pnl_val'].head(5).sum())

            top1_share = top1_val / total_pnl_val
            top3_share = top3_val / total_pnl_val
            top5_share = top5_val / total_pnl_val

        rows.append({
            'variant': variant,
            'category': cat,
            'trade_count': trade_count,
            'total_pnl_val': total_pnl_val,
            'top1_profit_share': top1_share,
            'top3_profit_share': top3_share,
            'top5_profit_share': top5_share,
        })

    return pd.DataFrame(rows)


def calc_sensitivity(results_by_params):
    """参数敏感性分析"""
    rows = []
    for params, summary in results_by_params:
        row = dict(summary)
        row.update(params)
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# =========================================================
# 结果打包
# =========================================================
_BUNDLE_FILES = [
    'role_rotation_report.md',
    'role_rotation_outputs.xlsx',
    'role_rotation_daily_nav.csv',
    'role_rotation_trades.csv',
    'role_rotation_positions.csv',
    'role_rotation_decisions.csv',
    'role_rotation_summary.csv',
    'role_rotation_overfit_check.csv',
    'role_rotation_diagnostics.csv',
    'role_rotation_sensitivity.csv',
    'role_rotation_cost_sensitivity.csv',
    'role_rotation_promotion_attribution.csv',
    'role_rotation_cap_check.csv',
]


def _bundle_outputs(output_dir):
    """将所有生成的 role_rotation_、v14C_ 文件以及 run_manifest.json 打包到 role_rotation_result_bundle.zip，覆盖旧的 ZIP。
    """
    bundle_path = os.path.join(output_dir, 'role_rotation_result_bundle.zip')
    try:
        if os.path.exists(bundle_path):
            try:
                os.remove(bundle_path)
                _log("Removed existing ZIP bundle before repackaging.")
            except Exception as e:
                _log("WARN: failed to remove old zip file: {}".format(e))

        all_files = os.listdir(output_dir)
        target_files = [f for f in all_files if (f.startswith('role_rotation_') or f.startswith('v14C_') or f == 'run_manifest.json') and f != 'role_rotation_result_bundle.zip']

        with zipfile.ZipFile(bundle_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for fname in target_files:
                fpath = os.path.join(output_dir, fname)
                zf.write(fpath, arcname=fname)
        _log("Bundle saved: {} containing {} files".format(bundle_path, len(target_files)))
    except Exception as e:
        _log("WARN: bundle save error: {}".format(e))

def df_to_markdown_safe(df, index=True):
    """兼容旧版 pandas （不支持 to_markdown）的 DataFrame 转 Markdown 函数。
    失败时至少用 df.to_string() 放进代码块返回。
    """
    if df is None or len(df) == 0:
        return "无数据"
    if hasattr(df, 'to_markdown'):
        try:
            return df.to_markdown(index=index)
        except TypeError:
            try:
                return df.to_markdown()
            except Exception:
                pass
        except Exception:
            pass
    # 兆底：用 to_string 放入代码块
    return "```text\n" + df.to_string(index=index) + "\n```"


def generate_report(summaries, monthly_all, decisions_all, overfit_all,
                    sensitivity_df, cost_sensitivity_df, promotion_attribution_df, cap_check_df,
                    output_dir, diagnostics_all=pd.DataFrame()):
    """生成 Markdown 报告"""
    lines = []
    lines.append("# 核心/卫星角色轮动直接模拟研究报告\n")
    lines.append("生成时间: {}\n".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    lines.append("\n## 1. 研究边界\n")
    lines.append("- 不基于历史 TRADE_CLOSE 日志回放")
    lines.append("- 从原始行情重新生成候选、买入、卖出、晋级、降级")
    lines.append("- 不调用真实下单函数")
    lines.append("- 模拟手续费: 万2.5佣金 + 万5印花税 + 每股0.02滑点")
    lines.append("- 初始资金: {:,.0f}".format(INITIAL_CASH))

    lines.append("\n## 2. 数据区间与样本切分\n")
    lines.append("| 区间 | 起止 |")
    lines.append("|------|------|")
    lines.append("| 训练观察段 | 2025-07-01 ~ {} |".format(TRAIN_END))
    lines.append("| 验证段 | {} ~ {} |".format(
        (_to_date(TRAIN_END) + datetime.timedelta(days=1)).isoformat(),
        VAL_END))
    lines.append("| 样本外段 | {} ~ end |".format(
        (_to_date(VAL_END) + datetime.timedelta(days=1)).isoformat()))

    lines.append("\n## 3. 方案说明\n")
    lines.append("| 变体 | 说明 |")
    lines.append("|------|------|")
    lines.append("| baseline_core_only | 只做核心仓(Top1 35% + Top2 25%), 不做卫星 |")
    lines.append("| baseline_core_satellite | 核心仓 + 单卫星仓15%, 不做晋级降级 |")
    lines.append("| role_rotation_observer | 核心仓 + 单卫星仓 + 卫星晋级核心/弱核心退出 |")

    lines.append("\n## 4. 候选生成逻辑\n")
    lines.append("- 使用 v3 评分体系(反转收高比+振幅+低换手率)")
    lines.append("- 仅 deep_water 模板通过打分筛选")
    lines.append("- 个股趋势过滤: MA5 > MA10 > MA20 + 价格站上MA20 + 低点抬升")
    lines.append("- 市场指数: {}".format(MARKET_INDEX))

    lines.append("\n## 5. 买入卖出逻辑\n")
    lines.append("**核心仓买入**: 每日从 dragon pool 选 top1/top2 deep_water, 分别 35%/25% 仓位")
    lines.append("**卫星仓买入**: WATCH_POOL 中 deep_water 候选, 1-3日后确认, Rule D 条件, 15% 仓位")
    lines.append("**核心退出**: 止损-6% / 跌破MA5亏损 / 持有5日亏损 / 回撤10%")
    lines.append("**卫星退出**: 止损-6% / 5日到期 / 跌破MA5亏损 / 持有3日亏损")

    lines.append("\n## 6. 角色评分逻辑\n")
    lines.append("- 浮盈档位 + MA5状态 + 回撤 + 日内强度 + 接近高点 + 持仓天数 + 信号分")

    lines.append("\n## 7. 晋级/降级规则\n")
    lines.append("- 卫星持有≥1日, pnl≥3%, 站上MA5, 接近日高≥96%")
    lines.append("- 卫星评分 ≥ 最弱核心评分 + {}".format(PROMOTION_MARGIN))
    lines.append("- 最弱核心存在弱化条件(亏损/跌破MA5/回撤≥8%/持仓>3日低盈利)")
    lines.append("- 市场非 bear, 每日最多一次晋级")

    lines.append("\n## 8. 总体结果对比\n")
    header = "| 指标 |"
    sep = "|------|"
    for s in summaries:
        if s.get('segment') == 'full':
            header += " {} |".format(s['variant'])
            sep += "------|"
    lines.append(header)
    lines.append(sep)

    full_summaries = [s for s in summaries if s.get('segment') == 'full']
    metrics = [
        ('total_return', '总收益', '{:.2%}'),
        ('annual_return', '年化收益', '{:.2%}'),
        ('max_drawdown', '最大回撤', '{:.2%}'),
        ('sharpe', '夏普比率', '{:.3f}'),
        ('trade_count', '交易笔数', '{:.0f}'),
        ('win_rate', '胜率', '{:.2%}'),
        ('avg_pnl', '平均盈亏', '{:.2%}'),
        ('promotion_count', '晋级次数', '{:.0f}'),
        ('demotion_count', '降级次数', '{:.0f}'),
        ('replacement_count', '替代次数', '{:.0f}'),
        ('exit_count', '卖出/退出次数', '{:.0f}'),
        ('avg_position_ratio', '平均仓位', '{:.2%}'),
    ]
    for key, label, fmt in metrics:
        row = "| {} |".format(label)
        for s in full_summaries:
            row += " {} |".format(fmt.format(s.get(key, 0)))
        lines.append(row)

    lines.append("\n## 9. 分段结果 train / validation / oos\n")
    for seg in ['train', 'validation', 'oos']:
        seg_summaries = [s for s in summaries if s.get('segment') == seg]
        if not seg_summaries:
            continue
        lines.append("\n### {}\n".format(seg))
        header = "| 指标 |"
        sep = "|------|"
        for s in seg_summaries:
            header += " {} |".format(s['variant'])
            sep += "------|"
        lines.append(header)
        lines.append(sep)
        for key, label, fmt in metrics[:6]:
            row = "| {} |".format(label)
            for s in seg_summaries:
                row += " {} |".format(fmt.format(s.get(key, 0)))
            lines.append(row)

    lines.append("\n## 10. 月度稳定性\n")
    if not monthly_all.empty:
        pivot = monthly_all.pivot_table(
            index='month', columns='variant', values='return',
        )
        lines.append(df_to_markdown_safe(pivot, index=True))

    lines.append("\n## 11. 交易归因\n")
    lines.append("(见 role_rotation_trades.csv)")

    lines.append("\n## 12. 晋级/降级归因与退出结果\n")
    if not promotion_attribution_df.empty:
        lines.append(df_to_markdown_safe(promotion_attribution_df, index=False))
    else:
        lines.append("- 无晋级记录 (详见 role_rotation_promotion_attribution.csv)")

    lines.append("\n## 13. 仓位使用情况与买入仓位限制诊断\n")
    lines.append("(详细日频数据见 role_rotation_cap_check.csv)\n")
    if not cap_check_df.empty:
        for name, sub in cap_check_df.groupby('variant'):
            total_days = len(sub)
            buy_exceeded = sub['cap_exceeded_on_buy'].sum()
            mtm_exceeded = sub['cap_exceeded_after_mark_to_market'].sum()
            lines.append("- **{}**: 运行 {} 天, 买入时超仓天数: {}, 持仓浮盈后自然超仓天数: {}".format(
                name, total_days, buy_exceeded, mtm_exceeded
            ))

    lines.append("\n## 14. 成本敏感性\n")
    if not cost_sensitivity_df.empty:
        lines.append(df_to_markdown_safe(cost_sensitivity_df, index=False))
    else:
        lines.append("- 基准: 万2.5佣金 + 万5印花税 + 0.02/股滑点")

    lines.append("\n## 15. 参数小扰动稳健性\n")
    if not sensitivity_df.empty:
        lines.append(df_to_markdown_safe(sensitivity_df, index=False))

    lines.append("\n## 16. 过拟合风险评级\n")
    if not overfit_all.empty:
        lines.append(df_to_markdown_safe(overfit_all, index=False))

    # 判定
    rr_full = [s for s in full_summaries if s['variant'] == 'role_rotation_observer']
    bl_full = [s for s in full_summaries if s['variant'] == 'baseline_core_only']
    cs_full = [s for s in full_summaries if s['variant'] == 'baseline_core_satellite']

    rr_ret = rr_full[0]['total_return'] if rr_full else 0
    bl_ret = bl_full[0]['total_return'] if bl_full else 0
    cs_ret = cs_full[0]['total_return'] if cs_full else 0

    rr_dd = abs(rr_full[0]['max_drawdown']) if rr_full else 999
    bl_dd = abs(bl_full[0]['max_drawdown']) if bl_full else 999

    promo_count = rr_full[0].get('promotion_count', 0) if rr_full else 0

    lines.append("\n## 17. 诊断摘要\n")
    if not diagnostics_all.empty:
        total_buy_success = diagnostics_all['core_buy_success_count'].sum() + diagnostics_all['satellite_buy_success_count'].sum()
        lines.append("- **是否存在全区间无交易**: {}".format("是" if total_buy_success == 0 else "否"))

        core_cand_mean = diagnostics_all['core_candidate_count'].mean()
        lines.append("- **core_candidate 是否长期为 0**: {}".format("是" if core_cand_mean < 0.5 else "否"))

        dw_mean = diagnostics_all['deep_water_count'].mean()
        lines.append("- **deep_water 是否长期为 0**: {}".format("是" if dw_mean < 0.5 else "否"))

        skip_cols = [c for c in diagnostics_all.columns if c.startswith('buy_skip_')]
        if skip_cols:
            skip_sums = diagnostics_all[skip_cols].sum().sort_values(ascending=False)
            top_skip = skip_sums.head(3).to_dict()
            skip_str = ", ".join(["{}: {}".format(k, v) for k, v in top_skip.items() if v > 0])
            lines.append("- **buy_skip 主要原因**: {}".format(skip_str if skip_str else "无"))

        lines.append("- **是否建议进入完整区间测试**: 需综合判断")

        auc_unavailable_sum = diagnostics_all['auction_unavailable'].sum() if 'auction_unavailable' in diagnostics_all.columns else 0
        lines.append("- **集合竞价数据是否真实可用**: {}".format("否(不可用)" if auc_unavailable_sum > 0 or 'auction_unavailable' not in diagnostics_all.columns else "是(可用)"))

        if total_buy_success == 0:
            lines.append("\n**注意**: 当前小区间未产生交易，不能据此判断策略收益，需先定位候选生成或买入触发链路。")
    else:
        lines.append("无诊断数据。")

    lines.append("\n## 18. 是否值得进入策略观测版\n")
    lines.append("(需综合 validation/oos 段表现、样本数、集中度等判断)")

    lines.append("\n## 19. 最终结论\n")
    lines.append("| 问题 | 结论 |")
    lines.append("|------|------|")
    lines.append("| 角色轮动是否优于核心-only | {} |".format(
        '是' if rr_ret > bl_ret else ('否' if rr_ret < bl_ret * 0.95 else '不确定')))
    lines.append("| 角色轮动是否优于核心+卫星不轮动 | {} |".format(
        '是' if rr_ret > cs_ret else ('否' if rr_ret < cs_ret * 0.95 else '不确定')))
    lines.append("| 角色轮动是否降低回撤 | {} |".format(
        '是' if rr_dd < bl_dd else '不确定'))
    lines.append("| 晋级样本是否足够 | {} |".format('是' if promo_count >= 10 else '否'))
    lines.append("| 过拟合风险 | 待综合判断 |")
    lines.append("| 是否建议进入策略观测版 | 否(需更多验证) |")
    lines.append("| 是否建议进入真实执行版 | 否 |")

    report_text = "\n".join(lines)
    report_path = os.path.join(output_dir, 'role_rotation_report.md')
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        _log("Report saved: {}".format(report_path))
    except Exception as e:
        _log("WARN: save report error: {}".format(e))
        print(report_text)

    return report_text


# =========================================================
# 主入口
# =========================================================
def run_research(start_date="2025-07-01", end_date="2026-06-14", output_dir="."):
    """
    研究入口函数。
    """
    _log("=" * 60)
    _log("核心/卫星角色轮动直接模拟 v1")
    _log("区间: {} ~ {}".format(start_date, end_date))
    _log("=" * 60)

    # Ensure directory exists and clean up old output files to prevent mixing them in the zip
    try:
        os.makedirs(output_dir, exist_ok=True)
        for f in os.listdir(output_dir):
            if f.startswith('role_rotation_') or f.startswith('v14C_') or f == 'run_manifest.json':
                fpath = os.path.join(output_dir, f)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception as e:
        _log("WARN: failed to clean up old files in {}: {}".format(output_dir, e))

    # 检查 API 注入
    if get_price is None or get_trade_days is None or get_all_securities is None:
        raise RuntimeError(
            "聚宽 API 未注入! 请先执行:\n"
            "  rr.get_price = get_price\n"
            "  rr.get_trade_days = get_trade_days\n"
            "  rr.get_all_securities = get_all_securities\n"
            "  rr.get_extras = get_extras"
        )

    # 获取交易日历
    trade_days_raw = get_trade_days(start_date=start_date, end_date=end_date)
    trade_days = [_to_date(d) for d in trade_days_raw]
    trade_days_set = set(trade_days)
    _log("交易日数: {}".format(len(trade_days)))

    if len(trade_days) < 2:
        _log("ERROR: 交易日不足")
        return {}

    # 加载市场指数
    _log("加载市场指数历史...")
    market_cache = load_market_index_history(trade_days)

    # 创建所有引擎
    base_params = {
        'promotion_margin': PROMOTION_MARGIN,
        'satellite_min_pnl': SATELLITE_MIN_PNL,
        'core_drawdown_weak': CORE_DRAWDOWN_WEAK,
        'satellite_slot_ratio': SATELLITE_RATIO,
        'max_total_cap': MAX_TOTAL_RATIO,
    }

    all_engines = {
        'baseline_core_only': SimEngine('baseline_core_only'),
        'baseline_core_satellite': SimEngine('baseline_core_satellite'),
        'role_rotation_observer': SimEngine('role_rotation_observer'),
    }

    # 参数扰动组
    for param_name, values in SENSITIVITY_PARAMS.items():
        for val in values:
            params = dict(base_params)
            params[param_name] = val
            if params == base_params:
                continue
            engine_key = f"sens_{param_name}_{val}"
            all_engines[engine_key] = SimEngine('role_rotation_observer', params)

    # 成本扰动组
    all_engines['cost_1.5x'] = SimEngine('role_rotation_observer', base_params, cost_multiplier=1.5, slippage_multiplier=1.5)
    all_engines['cost_2.0x'] = SimEngine('role_rotation_observer', base_params, cost_multiplier=2.0, slippage_multiplier=2.0)
    all_engines['cost_double_slippage'] = SimEngine('role_rotation_observer', base_params, cost_multiplier=1.0, slippage_multiplier=2.0)

    # 收集所有涉及的股票用于预加载
    _log("开始逐日模拟...")
    all_stocks_seen = set()

    for day_idx, date in enumerate(trade_days):
        if day_idx == 0:
            prev_date = date - datetime.timedelta(days=1)
            prev_days = get_trade_days(end_date=str(date), count=2)
            prev_date = _to_date(prev_days[0]) if len(prev_days) >= 2 else date - datetime.timedelta(days=1)
        else:
            prev_date = trade_days[day_idx - 1]

        # 进度
        if day_idx % 20 == 0:
            _log("Day {}/{}: {}".format(day_idx + 1, len(trade_days), date))

        # 市场状态
        market_state = get_market_state(date, market_cache)

        # 获取股票池
        universe = get_universe(prev_date)
        base_diag = {}
        if not universe:
            base_diag['universe_count'] = 0
            base_diag['tradable_count'] = 0
            for eng in all_engines.values():
                prices = get_day_prices(list(eng.positions.keys()), date, {})
                eng.daily_step(date, prev_date, [], prices, {},
                               market_state, trade_days_set, base_diag=base_diag)
            continue

        # 生成核心候选
        candidates = generate_core_candidates(date, prev_date, universe, diag_info=base_diag)

        # 收集需要行情的股票
        stocks_needed = set()
        for c in candidates:
            stocks_needed.add(c['stock'])
        for eng in all_engines.values():
            for s in eng.positions:
                stocks_needed.add(s)
            for s in eng.watch_pool:
                stocks_needed.add(s)
        all_stocks_seen.update(stocks_needed)

        # 加载日线数据
        daily_cache = {}
        if stocks_needed:
            batch = list(stocks_needed)
            try:
                hist_df = get_price(
                    batch,
                    end_date=str(date),
                    frequency='daily',
                    fields=['close', 'high', 'low', 'volume', 'open',
                            'high_limit', 'paused'],
                    count=25,
                    panel=False,
                )
                if hist_df is not None and not hist_df.empty:
                    hist_df = hist_df.sort_values(['code', 'time'])
                    for stock, sdf in hist_df.groupby('code', sort=False):
                        sdf = sdf.sort_values('time')
                        daily_cache[(stock, date)] = sdf['close'].values
                        if len(sdf) >= 2:
                            daily_cache[(stock, date, 'volume')] = float(sdf['volume'].iloc[-2])
            except Exception as e:
                _log("WARN: daily data error: {}".format(e))

        # 获取当日价格
        prices = {}
        for stock in stocks_needed:
            matched = [c for c in candidates if c['stock'] == stock]
            if matched:
                prices[stock] = matched[0].get('close_price',
                                               matched[0].get('open_price', 0))
                prices[stock + '_high'] = matched[0].get('high_price', prices[stock])
                prices[stock + '_low'] = matched[0].get('low_price', prices[stock])
                prices[stock + '_volume'] = matched[0].get('day_volume', 0)
            else:
                key = (stock, date)
                if key in daily_cache:
                    arr = daily_cache[key]
                    if len(arr) > 0:
                        prices[stock] = float(arr[-1])
                        prices[stock + '_high'] = prices[stock]
                        prices[stock + '_low'] = prices[stock]
                        prices[stock + '_volume'] = daily_cache.get(
                            (stock, date, 'volume'), 0)

        # 运行每个引擎
        for eng in all_engines.values():
            eng.daily_step(date, prev_date, candidates, prices,
                           daily_cache, market_state, trade_days_set, base_diag=base_diag)

        # 每 5 个交易日打印一次简洁诊断
        if (day_idx + 1) % 5 == 0:
            eng = all_engines['role_rotation_observer']
            d = eng.diagnostics[-1]
            _log("[RR-SIM-DIAG] date={} variant={} universe={} tradable={} prefilter={} core_candidates={} deep_water={} core_buy_success={} satellite_buy_success={}".format(
                date, eng.variant, d.get('universe_count',0), d.get('tradable_count',0),
                d.get('prefilter_count',0), d.get('core_candidate_count',0), d.get('deep_water_count',0),
                d.get('core_buy_success_count',0), d.get('satellite_buy_success_count',0)))

    # 模拟结束，finalize
    _log("模拟结束，进行收尾处理...")
    for eng in all_engines.values():
        eng.finalize_simulation(trade_days[-1], prices)

    _log("模拟完成，开始汇总...")

    # ---- 汇总主引擎结果 ----
    all_nav = []
    all_trades = []
    all_positions = []
    all_decisions = []
    all_diagnostics = []
    summaries = []

    main_variants = ['baseline_core_only', 'baseline_core_satellite', 'role_rotation_observer']
    for name in main_variants:
        eng = all_engines[name]
        nav_df = pd.DataFrame(eng.daily_nav)
        trades_df = pd.DataFrame(eng.trades)
        positions_df = pd.DataFrame(eng.daily_positions)
        decisions_df = pd.DataFrame(eng.decisions)

        all_nav.append(nav_df)
        all_trades.append(trades_df)
        all_positions.append(positions_df)
        all_decisions.append(decisions_df)
        if hasattr(eng, 'diagnostics') and eng.diagnostics:
            all_diagnostics.append(pd.DataFrame(eng.diagnostics))

        # 全段
        summaries.append(calc_summary(nav_df, trades_df, decisions_df, name, 'full'))

        # 分段
        if not nav_df.empty:
            train_end = _to_date(TRAIN_END)
            val_end = _to_date(VAL_END)

            train_mask = nav_df['date'] <= train_end
            val_mask = (nav_df['date'] > train_end) & (nav_df['date'] <= val_end)
            oos_mask = nav_df['date'] > val_end

            train_trades = trades_df[trades_df['date'] <= train_end] \
                if not trades_df.empty else pd.DataFrame()
            val_trades = trades_df[
                (trades_df['date'] > train_end) & (trades_df['date'] <= val_end)
            ] if not trades_df.empty else pd.DataFrame()
            oos_trades = trades_df[trades_df['date'] > val_end] \
                if not trades_df.empty else pd.DataFrame()

            train_decisions = decisions_df[decisions_df['date'] <= train_end] \
                if not decisions_df.empty else pd.DataFrame()
            val_decisions = decisions_df[
                (decisions_df['date'] > train_end) & (decisions_df['date'] <= val_end)
            ] if not decisions_df.empty else pd.DataFrame()
            oos_decisions = decisions_df[decisions_df['date'] > val_end] \
                if not decisions_df.empty else pd.DataFrame()

            if train_mask.any():
                summaries.append(calc_summary(
                    nav_df[train_mask], train_trades, train_decisions, name, 'train'))
            if val_mask.any():
                summaries.append(calc_summary(
                    nav_df[val_mask], val_trades, val_decisions, name, 'validation'))
            if oos_mask.any():
                summaries.append(calc_summary(
                    nav_df[oos_mask], oos_trades, oos_decisions, name, 'oos'))

    nav_all = pd.concat(all_nav, ignore_index=True) if all_nav else pd.DataFrame()
    trades_all = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    positions_all = pd.concat(all_positions, ignore_index=True) if all_positions else pd.DataFrame()
    decisions_all = pd.concat(all_decisions, ignore_index=True) if all_decisions else pd.DataFrame()
    diagnostics_all = pd.concat(all_diagnostics, ignore_index=True) if all_diagnostics else pd.DataFrame()

    # 月度收益
    monthly_parts = []
    for name in main_variants:
        sub = nav_all[nav_all['variant'] == name] if not nav_all.empty else pd.DataFrame()
        if not sub.empty:
            monthly_parts.append(calc_monthly(sub))
    monthly_all = pd.concat(monthly_parts, ignore_index=True) if monthly_parts else pd.DataFrame()

    # 滚动
    rolling_parts = []
    for name in main_variants:
        sub = nav_all[nav_all['variant'] == name] if not nav_all.empty else pd.DataFrame()
        if not sub.empty:
            for w in [20, 40]:
                r = calc_rolling(sub, w)
                if not r.empty:
                    r['window'] = w
                    rolling_parts.append(r)
    rolling_all = pd.concat(rolling_parts, ignore_index=True) if rolling_parts else pd.DataFrame()

    # 过拟合检查
    overfit_parts = []
    for name in main_variants:
        eng = all_engines[name]
        sub_trades = pd.DataFrame(eng.trades)
        sub_nav = pd.DataFrame(eng.daily_nav)
        oc = calc_overfit_check(sub_trades, sub_nav, name)
        if not oc.empty:
            overfit_parts.append(oc)
    overfit_all = pd.concat(overfit_parts, ignore_index=True) if overfit_parts else pd.DataFrame()

    # 参数扰动汇总
    sensitivity_rows = []
    for param_name, values in SENSITIVITY_PARAMS.items():
        for val in values:
            params = dict(base_params)
            params[param_name] = val
            if params == base_params:
                eng = all_engines['role_rotation_observer']
            else:
                eng = all_engines[f"sens_{param_name}_{val}"]

            nav_df = pd.DataFrame(eng.daily_nav)
            trades_df = pd.DataFrame(eng.trades)
            decisions_df = pd.DataFrame(eng.decisions)

            summary = calc_summary(nav_df, trades_df, decisions_df, eng.variant, 'full')
            sensitivity_rows.append({
                'param': param_name,
                'value': val,
                'total_return': summary.get('total_return', 0.0),
                'annual_return': summary.get('annual_return', 0.0),
                'max_drawdown': summary.get('max_drawdown', 0.0),
                'sharpe': summary.get('sharpe', 0.0),
                'trade_count': summary.get('trade_count', 0),
                'win_rate': summary.get('win_rate', 0.0),
                'promotion_count': summary.get('promotion_count', 0),
                'exit_count': summary.get('exit_count', 0),
            })
    sensitivity_df = pd.DataFrame(sensitivity_rows)

    # 成本扰动汇总
    cost_scenarios = [
        ('baseline_cost', all_engines['role_rotation_observer']),
        ('1.5x_cost', all_engines['cost_1.5x']),
        ('2x_cost', all_engines['cost_2.0x']),
        ('double_slippage', all_engines['cost_double_slippage']),
    ]
    cost_rows = []
    for scenario_name, eng in cost_scenarios:
        nav_df = pd.DataFrame(eng.daily_nav)
        trades_df = pd.DataFrame(eng.trades)
        decisions_df = pd.DataFrame(eng.decisions)

        summary = calc_summary(nav_df, trades_df, decisions_df, eng.variant, 'full')
        cost_rows.append({
            'cost_scenario': scenario_name,
            'total_return': summary.get('total_return', 0.0),
            'annual_return': summary.get('annual_return', 0.0),
            'max_drawdown': summary.get('max_drawdown', 0.0),
            'sharpe': summary.get('sharpe', 0.0),
            'trade_count': summary.get('trade_count', 0),
            'win_rate': summary.get('win_rate', 0.0),
            'promotion_count': summary.get('promotion_count', 0),
            'exit_count': summary.get('exit_count', 0),
        })
    cost_sensitivity_df = pd.DataFrame(cost_rows)

    # 晋级归因汇总
    obs_eng = all_engines['role_rotation_observer']
    promotion_attribution_df = pd.DataFrame(obs_eng.promotion_attributions)
    PROMOTION_ATTRIBUTION_COLS = ['promotion_date', 'satellite_stock', 'replaced_core', 'exit_date', 'final_pnl', 'final_ret', 'hold_days_after_promotion', 'pnl_post_promotion', 'ret_post_promotion', 'status']

    # 仓位诊断汇总
    cap_check_rows = []
    for name in main_variants:
        eng = all_engines[name]
        cap_check_rows.extend(eng.cap_checks)
    cap_check_df = pd.DataFrame(cap_check_rows)
    CAP_CHECK_COLS = ['date', 'variant', 'pre_buy_total_ratio', 'post_buy_total_ratio', 'cap_limit', 'cap_exceeded_on_buy', 'cap_exceeded_after_mark_to_market']

    # ---- 保存输出文件 ----
    summary_df = pd.DataFrame(summaries)
    _log("保存输出文件...")
    try:
        nav_all.to_csv(
            os.path.join(output_dir, 'role_rotation_daily_nav.csv'),
            index=False, encoding='utf-8-sig')

        TRADES_COLS = ['date', 'stock', 'name', 'action', 'role', 'price', 'shares', 'value', 'reason', 'pnl_pct', 'pnl_val', 'trade_category', 'hold_days_cal', 'variant', 'entry_type', 'signal_score']
        DECISIONS_COLS = ['date', 'variant', 'stock', 'name', 'decision', 'reason', 'sat_score', 'core_score', 'replaced_core', 'pnl_pct']
        DIAG_COLS = ['date', 'variant', 'universe_count', 'tradable_count', 'price_data_ok_count', 'prefilter_count', 'core_candidate_count', 'deep_water_count', 'watch_pool_count', 'satellite_confirm_count', 'core_buy_attempt_count', 'core_buy_success_count', 'satellite_buy_attempt_count', 'satellite_buy_success_count', 'buy_skip_no_candidate', 'buy_skip_no_price', 'buy_skip_paused', 'buy_skip_st', 'buy_skip_limit_up', 'buy_skip_cap_full', 'buy_skip_duplicate_role', 'buy_skip_other', 'price_batch_error', 'candidate_skip_price_batch_error', 'candidate_skip_no_price', 'trend_data_len_min', 'trend_data_len_mean', 'trend_filter_executed_count', 'trend_filter_skipped_count', 'auction_unavailable', 'notes']
        POSITIONS_COLS = ['date', 'variant', 'stock', 'name', 'role', 'shares', 'price', 'market_value', 'cost', 'pnl', 'pnl_pct', 'weight', 'hold_days']

        trades_all = safe_to_csv(trades_all, os.path.join(output_dir, 'role_rotation_trades.csv'), TRADES_COLS)

        # Ensure decisions contains replaced_core and other fields
        decisions_all = normalize_decisions_df(decisions_all)
        if 'replaced_core' in decisions_all.columns:
            decisions_all['replaced_core'] = decisions_all['replaced_core'].fillna("")

        decisions_all = safe_to_csv(decisions_all, os.path.join(output_dir, 'role_rotation_decisions.csv'), DECISIONS_COLS)
        overfit_all = safe_to_csv(overfit_all, os.path.join(output_dir, 'role_rotation_overfit_check.csv'), ['variant', 'category', 'trade_count', 'total_pnl_val', 'top1_profit_share', 'top3_profit_share', 'top5_profit_share'])
        diagnostics_all = safe_to_csv(diagnostics_all, os.path.join(output_dir, 'role_rotation_diagnostics.csv'), DIAG_COLS)
        positions_all = safe_to_csv(positions_all, os.path.join(output_dir, 'role_rotation_positions.csv'), POSITIONS_COLS)

        # 保存新文件
        sensitivity_df = safe_to_csv(sensitivity_df, os.path.join(output_dir, 'role_rotation_sensitivity.csv'), ['param', 'value', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count'])
        cost_sensitivity_df = safe_to_csv(cost_sensitivity_df, os.path.join(output_dir, 'role_rotation_cost_sensitivity.csv'), ['cost_scenario', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count'])

        # Ensure promotion_attribution contains replaced_core
        if not promotion_attribution_df.empty:
            if 'replaced_core' not in promotion_attribution_df.columns:
                promotion_attribution_df['replaced_core'] = np.nan
            promotion_attribution_df['replaced_core'] = promotion_attribution_df['replaced_core'].fillna("")

        promotion_attribution_df = safe_to_csv(promotion_attribution_df, os.path.join(output_dir, 'role_rotation_promotion_attribution.csv'), PROMOTION_ATTRIBUTION_COLS)
        cap_check_df = safe_to_csv(cap_check_df, os.path.join(output_dir, 'role_rotation_cap_check.csv'), CAP_CHECK_COLS)

        summary_df.to_csv(
            os.path.join(output_dir, 'role_rotation_summary.csv'),
            index=False, encoding='utf-8-sig')
        _log("CSV files saved.")

        # Generate and save run_manifest.json
        try:
            import json
            is_mock = False
            try:
                import sys
                if sys.argv and any('test_mock_sim' in arg for arg in sys.argv):
                    is_mock = True
                elif 'mock' in getattr(get_price, '__name__', '').lower():
                    is_mock = True
            except Exception:
                pass

            env_note = "Local Mock Environment (test_mock_sim)" if is_mock else "JoinQuant Real Environment"

            auction_unavailable_sum = 0
            core_candidate_count_sum = 0
            deep_water_count_sum = 0
            if not diagnostics_all.empty:
                if 'auction_unavailable' in diagnostics_all.columns:
                    auction_unavailable_sum = int(diagnostics_all['auction_unavailable'].sum())
                if 'core_candidate_count' in diagnostics_all.columns:
                    core_candidate_count_sum = int(diagnostics_all['core_candidate_count'].sum())
                if 'deep_water_count' in diagnostics_all.columns:
                    deep_water_count_sum = int(diagnostics_all['deep_water_count'].sum())

            manifest = {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "run_timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "trading_days": int(len(nav_all['date'].unique())) if not nav_all.empty and 'date' in nav_all.columns else int(len(trade_days)),
                "environment_note": env_note,
                "daily_nav_rows": int(len(nav_all)),
                "trades_rows": int(len(trades_all)),
                "positions_rows": int(len(positions_all)),
                "diagnostics_rows": int(len(diagnostics_all)),
                "summary_rows": int(len(summary_df)),
                "auction_unavailable_sum": auction_unavailable_sum,
                "core_candidate_count_sum": core_candidate_count_sum,
                "deep_water_count_sum": deep_water_count_sum,
                "output_dir": str(output_dir)
            }

            manifest_path = os.path.join(output_dir, 'run_manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=4, ensure_ascii=False)
            _log("Manifest written: {}".format(manifest_path))
        except Exception as e:
            _log("WARN: failed to write run_manifest.json: {}".format(e))
    except Exception as e:
        _log("WARN: CSV save error: {}".format(e))
        traceback.print_exc()

    # Excel
    try:
        xlsx_path = os.path.join(output_dir, 'role_rotation_outputs.xlsx')
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='1_summary', index=False)
            nav_all.to_excel(writer, sheet_name='2_daily_nav', index=False)
            trades_all.to_excel(writer, sheet_name='3_trades', index=False)
            positions_all.to_excel(writer, sheet_name='4_positions', index=False)
            decisions_all.to_excel(writer, sheet_name='5_decisions', index=False)
            if not monthly_all.empty:
                monthly_all.to_excel(writer, sheet_name='6_monthly', index=False)
            if not rolling_all.empty:
                rolling_all.to_excel(writer, sheet_name='7_rolling', index=False)
            overfit_all.to_excel(writer, sheet_name='8_overfit', index=False)
            if not sensitivity_df.empty:
                sensitivity_df.to_excel(writer, sheet_name='9_sensitivity', index=False)
            diagnostics_all.to_excel(writer, sheet_name='10_diagnostics', index=False)
            if not cost_sensitivity_df.empty:
                cost_sensitivity_df.to_excel(writer, sheet_name='11_cost_sens', index=False)
            if not promotion_attribution_df.empty:
                promotion_attribution_df.to_excel(writer, sheet_name='12_promo_attr', index=False)
            if not cap_check_df.empty:
                cap_check_df.to_excel(writer, sheet_name='13_cap_check', index=False)
        _log("Excel saved: {}".format(xlsx_path))
    except Exception as e:
        _log("WARN: Excel save error (continuing with CSV): {}".format(e))
        traceback.print_exc()

    # Markdown 报告
    generate_report(summaries, monthly_all, decisions_all, overfit_all,
                    sensitivity_df, cost_sensitivity_df, promotion_attribution_df, cap_check_df,
                    output_dir, diagnostics_all)

    # ---- 打包 ZIP ----
    _bundle_outputs(output_dir)

    _log("=" * 60)
    _log("研究完成!")
    _log("=" * 60)

    return {
        'summary': summary_df,
        'daily_nav': nav_all,
        'trades': trades_all,
        'positions': positions_all,
        'decisions': decisions_all,
        'monthly': monthly_all,
        'rolling': rolling_all,
        'overfit': overfit_all,
        'sensitivity': sensitivity_df,
    }


def _read_csv_safe(path, default_cols):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            _log("WARN: failed to read {}: {}".format(path, e))
    return pd.DataFrame(columns=default_cols)


def analyze_results(output_dir="role_rotation_result_bundle", start_date=None, end_date=None):
    _log("=" * 60)
    _log("开始结果分析模块...")
    _log(f"读取目录: {output_dir}")
    _log("=" * 60)

    # 1. 读取 run_manifest.json
    manifest_path = os.path.join(output_dir, 'run_manifest.json')
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            _log("成功读取 run_manifest.json")
        except Exception as e:
            _log("WARN: failed to read run_manifest.json: {}".format(e))
    else:
        _log("WARN: run_manifest.json 不存在，将使用默认配置")

    # 2. 安全读取 CSV 文件
    summary_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_summary.csv'),
                                 ['variant', 'segment', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count'])
    daily_nav_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_daily_nav.csv'),
                                   ['date', 'total_value', 'nav', 'cash', 'variant'])
    trades_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_trades.csv'),
                                ['date', 'stock', 'name', 'action', 'role', 'price', 'shares', 'value', 'reason', 'pnl_pct', 'pnl_val', 'trade_category', 'hold_days_cal', 'variant'])
    positions_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_positions.csv'),
                                   ['date', 'variant', 'stock', 'name', 'role', 'shares', 'price', 'market_value', 'cost', 'pnl', 'pnl_pct', 'weight', 'hold_days'])
    decisions_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_decisions.csv'),
                                   ['date', 'variant', 'stock', 'name', 'decision', 'reason'])

    decisions_df = normalize_decisions_df(decisions_df)
    decisions_df['replaced_core'] = decisions_df['replaced_core'].fillna("")

    diagnostics_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_diagnostics.csv'),
                                     ['date', 'variant', 'universe_count', 'core_buy_success_count', 'satellite_buy_success_count', 'auction_unavailable'])
    overfit_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_overfit_check.csv'),
                                 ['variant', 'category', 'trade_count', 'total_pnl_val', 'top1_profit_share', 'top3_profit_share', 'top5_profit_share'])
    sensitivity_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_sensitivity.csv'),
                                     ['param', 'value', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count'])
    cost_sensitivity_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_cost_sensitivity.csv'),
                                          ['cost_scenario', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count'])
    promotion_attribution_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_promotion_attribution.csv'),
                                               ['promotion_date', 'satellite_stock', 'replaced_core', 'exit_date', 'final_pnl', 'final_ret', 'hold_days_after_promotion', 'pnl_post_promotion', 'ret_post_promotion', 'status'])

    if 'replaced_core' not in promotion_attribution_df.columns:
        promotion_attribution_df['replaced_core'] = np.nan
    promotion_attribution_df['replaced_core'] = promotion_attribution_df['replaced_core'].fillna("")

    cap_check_df = _read_csv_safe(os.path.join(output_dir, 'role_rotation_cap_check.csv'),
                                   ['date', 'variant', 'pre_buy_total_ratio', 'post_buy_total_ratio', 'cap_limit', 'cap_exceeded_on_buy', 'cap_exceeded_after_mark_to_market'])

    # ---- 1. 三个变体整体对比 ----
    full_summary = summary_df[summary_df['segment'] == 'full'] if not summary_df.empty else pd.DataFrame()

    # ---- 2. 分段表现 ----
    seg_summary = summary_df[summary_df['segment'].isin(['train', 'validation', 'oos'])] if not summary_df.empty else pd.DataFrame()

    # ---- 3. 参数扰动稳定性 ----
    sens_mean_ret, sens_std_ret, sens_min_ret, sens_max_ret = 0.0, 0.0, 0.0, 0.0
    sens_mean_dd, sens_std_dd = 0.0, 0.0
    if not sensitivity_df.empty:
        rets = sensitivity_df['total_return'].astype(float)
        dds = sensitivity_df['max_drawdown'].astype(float)
        sens_mean_ret = float(rets.mean()) if len(rets) > 0 else 0.0
        sens_std_ret = float(rets.std()) if len(rets) > 1 else 0.0
        sens_min_ret = float(rets.min()) if len(rets) > 0 else 0.0
        sens_max_ret = float(rets.max()) if len(rets) > 0 else 0.0
        sens_mean_dd = float(dds.mean()) if len(dds) > 0 else 0.0
        sens_std_dd = float(dds.std()) if len(dds) > 1 else 0.0

    # ---- 4. 成本敏感性 ----
    # cost_sensitivity_df

    # ---- 5. 盈利贡献集中度 ----
    # overfit_df

    # ---- 6. 晋级归因 ----
    total_promotions = len(promotion_attribution_df)
    exited_promotions = len(promotion_attribution_df[promotion_attribution_df['status'] == 'exited'])
    held_promotions = len(promotion_attribution_df[promotion_attribution_df['status'] == 'held'])

    win_promotions = len(promotion_attribution_df[(promotion_attribution_df['status'] == 'exited') & (promotion_attribution_df['final_pnl'] > 0)])
    promo_win_rate = win_promotions / exited_promotions if exited_promotions > 0 else 0.0
    sum_final_pnl = promotion_attribution_df['final_pnl'].sum() if total_promotions > 0 else 0.0
    sum_post_pnl = promotion_attribution_df['pnl_post_promotion'].sum() if total_promotions > 0 else 0.0
    avg_hold_days = promotion_attribution_df['hold_days_after_promotion'].mean() if total_promotions > 0 else 0.0

    promotion_profit_summary = pd.DataFrame([
        {'metric': 'total_promotion_count', 'value': total_promotions},
        {'metric': 'exited_promotion_count', 'value': exited_promotions},
        {'metric': 'held_promotion_count', 'value': held_promotions},
        {'metric': 'promotion_win_rate', 'value': promo_win_rate},
        {'metric': 'total_final_pnl_amount', 'value': sum_final_pnl},
        {'metric': 'total_post_promotion_pnl_amount', 'value': sum_post_pnl},
        {'metric': 'avg_hold_days_post_promotion', 'value': avg_hold_days},
    ])

    # ---- 7. 亏损交易归因 ----
    obs_sells = trades_df[(trades_df['variant'] == 'role_rotation_observer') & (trades_df['action'] == 'SELL')] if not trades_df.empty else pd.DataFrame()
    obs_losses = obs_sells[obs_sells['pnl_pct'] < 0] if not obs_sells.empty else pd.DataFrame()

    total_sells_count = len(obs_sells)
    total_losses_pnl = obs_losses['pnl_val'].sum() if not obs_losses.empty else 0.0

    fast_loss_trades = obs_losses[obs_losses['hold_days_cal'] <= 5] if not obs_losses.empty else pd.DataFrame()
    big_loss_trades = obs_losses[obs_losses['pnl_pct'] <= -0.06] if not obs_losses.empty else pd.DataFrame()
    normal_loss_trades = obs_losses[(obs_losses['hold_days_cal'] > 5) & (obs_losses['pnl_pct'] > -0.06)] if not obs_losses.empty else pd.DataFrame()

    fast_loss_count = len(fast_loss_trades)
    fast_loss_pnl = fast_loss_trades['pnl_val'].sum() if fast_loss_count > 0 else 0.0

    big_loss_count = len(big_loss_trades)
    big_loss_pnl = big_loss_trades['pnl_val'].sum() if big_loss_count > 0 else 0.0

    normal_loss_count = len(normal_loss_trades)
    normal_loss_pnl = normal_loss_trades['pnl_val'].sum() if normal_loss_count > 0 else 0.0

    # ---- 8. 大肉交易归因 ----
    obs_profits = obs_sells[obs_sells['pnl_pct'] > 0] if not obs_sells.empty else pd.DataFrame()
    total_profits_pnl = obs_profits['pnl_val'].sum() if not obs_profits.empty else 0.0

    big_meat_trades = obs_profits[(obs_profits['pnl_pct'] >= 0.10) & (obs_profits['pnl_pct'] < 0.20)] if not obs_profits.empty else pd.DataFrame()
    super_meat_trades = obs_profits[obs_profits['pnl_pct'] >= 0.20] if not obs_profits.empty else pd.DataFrame()
    promoted_big_meat_trades = obs_profits[(obs_profits['pnl_pct'] >= 0.10) & (obs_profits['trade_category'] == 'promoted_core')] if not obs_profits.empty else pd.DataFrame()

    big_meat_count = len(big_meat_trades)
    big_meat_pnl = big_meat_trades['pnl_val'].sum() if big_meat_count > 0 else 0.0

    super_meat_count = len(super_meat_trades)
    super_meat_pnl = super_meat_trades['pnl_val'].sum() if super_meat_count > 0 else 0.0

    promoted_big_meat_count = len(promoted_big_meat_trades)
    promoted_big_meat_pnl = promoted_big_meat_trades['pnl_val'].sum() if promoted_big_meat_count > 0 else 0.0

    summary_rows = [
        {'category': 'fast_loss', 'trade_count': fast_loss_count, 'total_pnl_val': fast_loss_pnl, 'pct_of_all_sells': fast_loss_count / total_sells_count if total_sells_count > 0 else 0.0},
        {'category': 'big_loss', 'trade_count': big_loss_count, 'total_pnl_val': big_loss_pnl, 'pct_of_all_sells': big_loss_count / total_sells_count if total_sells_count > 0 else 0.0},
        {'category': 'normal_loss', 'trade_count': normal_loss_count, 'total_pnl_val': normal_loss_pnl, 'pct_of_all_sells': normal_loss_count / total_sells_count if total_sells_count > 0 else 0.0},
        {'category': 'big_meat', 'trade_count': big_meat_count, 'total_pnl_val': big_meat_pnl, 'pct_of_all_sells': big_meat_count / total_sells_count if total_sells_count > 0 else 0.0},
        {'category': 'super_meat', 'trade_count': super_meat_count, 'total_pnl_val': super_meat_pnl, 'pct_of_all_sells': super_meat_count / total_sells_count if total_sells_count > 0 else 0.0},
        {'category': 'promoted_big_meat', 'trade_count': promoted_big_meat_count, 'total_pnl_val': promoted_big_meat_pnl, 'pct_of_all_sells': promoted_big_meat_count / total_sells_count if total_sells_count > 0 else 0.0},
    ]
    loss_bigmeat_summary = pd.DataFrame(summary_rows)

    all_sells = trades_df[trades_df['action'] == 'SELL'] if not trades_df.empty else pd.DataFrame()
    fast_loss_samples = all_sells[(all_sells['hold_days_cal'] <= 5) & (all_sells['pnl_pct'] < 0)] if not all_sells.empty else pd.DataFrame()
    big_meat_samples = all_sells[all_sells['pnl_pct'] >= 0.10] if not all_sells.empty else pd.DataFrame()

    # ---- 9. Cap 检查 ----
    obs_cap = cap_check_df[cap_check_df['variant'] == 'role_rotation_observer'] if not cap_check_df.empty else pd.DataFrame()
    cap_on_buy_count = obs_cap['cap_exceeded_on_buy'].sum() if not obs_cap.empty else 0
    cap_mtm_count = obs_cap['cap_exceeded_after_mark_to_market'].sum() if not obs_cap.empty else 0

    # ---- 10. 选股改进空间 & Feature Needs ----
    entry_feature_rows = []
    if not obs_losses.empty:
        for idx, row in obs_losses.iterrows():
            exit_date = _to_date(row['date'])
            stock = row['stock']
            buy_trade = trades_df[(trades_df['stock'] == stock) & (trades_df['action'] == 'BUY') & (trades_df['date'] <= str(exit_date))]
            buy_date_str = str(exit_date)
            if not buy_trade.empty:
                buy_date_str = str(buy_trade['date'].iloc[-1])

            reason = str(row['reason'])
            if 'stop_loss' in reason:
                need = "Needs short-term price volatility filter on entry day / high open ratio control"
            elif 'ma5' in reason:
                need = "Needs MA5 trend strength confirmation / volume support check on entry day"
            elif 'stale' in reason:
                need = "Needs entry-day time decay check / momentum strength filter"
            elif 'drawdown' in reason:
                need = "Needs trailing stop tight range adjustment / avoid entering near historical ceiling"
            else:
                need = "Needs call auction volume ratio sanity filter / market index state filter"

            entry_feature_rows.append({
                'date': buy_date_str,
                'stock': stock,
                'name': row['name'],
                'pnl_pct': row['pnl_pct'],
                'pnl_val': row['pnl_val'],
                'hold_days': row['hold_days_cal'],
                'reason_for_loss': reason,
                'proposed_feature_need': need
            })
    entry_feature_need_list = pd.DataFrame(entry_feature_rows)

    # ---- Overfit Final Check Table ----
    baseline_ret = 0.0
    cost_1_5x_ret = 0.0
    cost_2_0x_ret = 0.0

    if not cost_sensitivity_df.empty:
        base_row = cost_sensitivity_df[cost_sensitivity_df['cost_scenario'] == 'baseline_cost']
        cost_15_row = cost_sensitivity_df[cost_sensitivity_df['cost_scenario'] == '1.5x_cost']
        cost_20_row = cost_sensitivity_df[cost_sensitivity_df['cost_scenario'] == '2x_cost']

        if not base_row.empty:
            baseline_ret = float(base_row['total_return'].iloc[0])
        if not cost_15_row.empty:
            cost_1_5x_ret = float(cost_15_row['total_return'].iloc[0])
        if not cost_20_row.empty:
            cost_2_0x_ret = float(cost_20_row['total_return'].iloc[0])

    decay_15 = (baseline_ret - cost_1_5x_ret) / baseline_ret if baseline_ret != 0 else 0.0
    decay_20 = (baseline_ret - cost_2_0x_ret) / baseline_ret if baseline_ret != 0 else 0.0

    top3_share = 0.0
    if not overfit_df.empty:
        obs_overfit = overfit_df[(overfit_df['variant'] == 'role_rotation_observer') & (overfit_df['category'] == 'all')]
        if not obs_overfit.empty:
            top3_share = float(obs_overfit['top3_profit_share'].iloc[0])

    overfit_final_rows = [
        {'metric': 'sensitivity_return_std', 'status': 'Stable' if sens_std_ret < 0.10 else 'Unstable', 'value': sens_std_ret, 'threshold': '< 10%', 'assessment': 'Pass' if sens_std_ret < 0.10 else 'Fail'},
        {'metric': 'cost_1.5x_decay', 'status': 'Low decay' if decay_15 < 0.50 else 'High decay', 'value': decay_15, 'threshold': '< 50%', 'assessment': 'Pass' if decay_15 < 0.50 else 'Fail'},
        {'metric': 'cost_2.0x_decay', 'status': 'Acceptable decay' if decay_20 < 0.75 else 'High decay', 'value': decay_20, 'threshold': '< 75%', 'assessment': 'Pass' if decay_20 < 0.75 else 'Fail'},
        {'metric': 'profit_concentration_top3', 'status': 'Healthy' if top3_share < 0.70 else 'Concentrated', 'value': top3_share, 'threshold': '< 70%', 'assessment': 'Pass' if top3_share < 0.70 else 'Fail'},
    ]
    overfit_final_check = pd.DataFrame(overfit_final_rows)

    # ---- 写入 CSV 文件 ----
    safe_to_csv(loss_bigmeat_summary, os.path.join(output_dir, 'v14C_loss_bigmeat_summary.csv'), ['category', 'trade_count', 'total_pnl_val', 'pct_of_all_sells'])
    safe_to_csv(fast_loss_samples, os.path.join(output_dir, 'v14C_fast_loss_samples.csv'), ['variant', 'date', 'stock', 'name', 'action', 'role', 'price', 'shares', 'value', 'reason', 'pnl_pct', 'pnl_val', 'trade_category', 'hold_days_cal', 'entry_type', 'signal_score'])
    safe_to_csv(big_meat_samples, os.path.join(output_dir, 'v14C_big_meat_samples.csv'), ['variant', 'date', 'stock', 'name', 'action', 'role', 'price', 'shares', 'value', 'reason', 'pnl_pct', 'pnl_val', 'trade_category', 'hold_days_cal', 'entry_type', 'signal_score'])
    safe_to_csv(promotion_profit_summary, os.path.join(output_dir, 'v14C_promotion_profit_summary.csv'), ['metric', 'value'])
    safe_to_csv(overfit_final_check, os.path.join(output_dir, 'v14C_overfit_final_check.csv'), ['metric', 'status', 'value', 'threshold', 'assessment'])
    safe_to_csv(entry_feature_need_list, os.path.join(output_dir, 'v14C_entry_feature_need_list.csv'), ['date', 'stock', 'name', 'pnl_pct', 'pnl_val', 'hold_days', 'reason_for_loss', 'proposed_feature_need'])

    # ---- 写入 Excel ----
    try:
        xlsx_path = os.path.join(output_dir, 'v14C_full_diagnosis_outputs.xlsx')
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            loss_bigmeat_summary.to_excel(writer, sheet_name='loss_bigmeat_summary', index=False)
            fast_loss_samples.to_excel(writer, sheet_name='fast_loss_samples', index=False)
            big_meat_samples.to_excel(writer, sheet_name='big_meat_samples', index=False)
            promotion_profit_summary.to_excel(writer, sheet_name='promotion_profit_summary', index=False)
            overfit_final_check.to_excel(writer, sheet_name='overfit_final_check', index=False)
            entry_feature_need_list.to_excel(writer, sheet_name='entry_feature_need_list', index=False)
        _log(f"Excel saved: {xlsx_path}")
    except Exception as e:
        _log(f"WARN: Excel save error: {e}")

    # ---- Formulate dynamic answers for 14 questions ----
    obs_ret = 0.0
    core_only_ret = 0.0
    core_sat_ret = 0.0
    if not full_summary.empty:
        obs_row = full_summary[full_summary['variant'] == 'role_rotation_observer']
        co_row = full_summary[full_summary['variant'] == 'baseline_core_only']
        cs_row = full_summary[full_summary['variant'] == 'baseline_core_satellite']
        if not obs_row.empty: obs_ret = float(obs_row['total_return'].iloc[0])
        if not co_row.empty: core_only_ret = float(co_row['total_return'].iloc[0])
        if not cs_row.empty: core_sat_ret = float(cs_row['total_return'].iloc[0])

    ans_1 = "是" if obs_ret > core_only_ret else "否"
    ans_2 = "是" if obs_ret > core_sat_ret else "否"

    ans_3, ans_4 = "否", "否"
    if not seg_summary.empty:
        obs_seg = seg_summary[seg_summary['variant'] == 'role_rotation_observer']
        val_row = obs_seg[obs_seg['segment'] == 'validation']
        oos_row = obs_seg[obs_seg['segment'] == 'oos']
        if not val_row.empty and float(val_row['total_return'].iloc[0]) > 0:
            ans_3 = "是"
        if not oos_row.empty and float(oos_row['total_return'].iloc[0]) > 0:
            ans_4 = "是"

    ans_5 = "是" if sens_std_ret < 0.10 else "否"
    ans_6 = "是" if (cost_1_5x_ret > 0 and cost_2_0x_ret > 0) else "否"
    ans_7 = "是" if top3_share >= 0.70 else "否"
    ans_8 = "是" if sum_post_pnl > 0 else "否"

    loss_types = [('fast_loss', abs(fast_loss_pnl)), ('big_loss', abs(big_loss_pnl)), ('normal_loss', abs(normal_loss_pnl))]
    loss_types.sort(key=lambda x: x[1], reverse=True)
    ans_9 = f"主要来源为 {loss_types[0][0]} (金额: {loss_types[0][1]:,.2f})" if total_losses_pnl < 0 else "无显著亏损来源"

    meat_types = [('big_meat', big_meat_pnl), ('super_meat', super_meat_pnl), ('promoted_big_meat', promoted_big_meat_pnl)]
    meat_types.sort(key=lambda x: x[1], reverse=True)
    ans_10 = f"主要来源为 {meat_types[0][0]} (金额: {meat_types[0][1]:,.2f})" if total_profits_pnl > 0 else "无大肉交易记录"

    ans_11 = "是" if len(entry_feature_need_list) > 0 else "否"

    if ans_3 == "是" and ans_5 == "是" and ans_6 == "是" and ans_7 == "否":
        ans_12 = "是"
        ans_13 = "建议进入主线验证" if ans_4 == "是" else "暂不建议"
        ans_14 = "否 (需进行实盘观测和模拟交易验证)"
    else:
        ans_12 = "否 (策略表现或稳健性在当前小区间未能完全通过验证)"
        ans_13 = "否"
        ans_14 = "否"

    is_mock = False
    env_note = manifest.get('environment_note', '')
    if 'mock' in env_note.lower() or 'mock' in getattr(get_price, '__name__', '').lower():
        is_mock = True
    try:
        import sys
        if sys.argv and any('test_mock_sim' in arg for arg in sys.argv):
            is_mock = True
    except Exception:
        pass

    report_title = "# [MOCK TEST，不可用于策略结论] v1.4.0C 核心/卫星角色轮动深度诊断分析报告\n" if is_mock else "# v1.4.0C 核心/卫星角色轮动深度诊断分析报告\n"

    report_lines = []
    report_lines.append(report_title)
    report_lines.append(f"报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 在 v14C_full_diagnosis_report.md 顶部展示 manifest
    report_lines.append("## 运行配置清单 (Run Manifest Summary)\n")
    report_lines.append("| 配置项 (Item) | 运行记录值 (Value) |")
    report_lines.append("| :--- | :--- |")
    report_lines.append(f"| 仿真开始日期 (Start Date) | {manifest.get('start_date', 'N/A')} |")
    report_lines.append(f"| 仿真结束日期 (End Date) | {manifest.get('end_date', 'N/A')} |")
    report_lines.append(f"| 仿真运行时间 (Run Timestamp) | {manifest.get('run_timestamp', 'N/A')} |")
    report_lines.append(f"| 实际交易日数 (Trading Days) | {manifest.get('trading_days', 'N/A')} |")
    report_lines.append(f"| 运行环境备注 (Environment Note) | {manifest.get('environment_note', 'N/A')} |")
    report_lines.append(f"| 仿真输出目录 (Output Directory) | {manifest.get('output_dir', 'N/A')} |")
    report_lines.append(f"| 仿真结果行数 | 日NAV={manifest.get('daily_nav_rows', 0)}行, 交易={manifest.get('trades_rows', 0)}行, 持仓={manifest.get('positions_rows', 0)}行, 汇总={manifest.get('summary_rows', 0)}行 |")
    report_lines.append(f"| 诊断指标汇总 | 竞价不可用={manifest.get('auction_unavailable_sum', 0)}天, 核心候选={manifest.get('core_candidate_count_sum', 0)}只次, 深水候选={manifest.get('deep_water_count_sum', 0)}只次 |\n")

    # 3 & 4. 异常与警示提示
    warnings_block = []

    trades_rows = manifest.get('trades_rows', 0)
    core_candidate_count_sum = manifest.get('core_candidate_count_sum', 0)
    deep_water_count_sum = manifest.get('deep_water_count_sum', 0)
    if trades_rows == 0 and (core_candidate_count_sum > 0 or deep_water_count_sum > 0):
        warnings_block.append(
            "> [!CAUTION]\n"
            f"> **交易异常警示 (Abnormality Warning)**: 本次运行中交易笔数 (trades_rows) 为 0，"
            f"但核心候选池累积数 (core_candidate_count_sum) = {core_candidate_count_sum} "
            f"或深水池累积数 (deep_water_count_sum) = {deep_water_count_sum} 大于 0！\n"
            f"> 这表明筛选链路已产生候选标的，但最终交易为 0，可能存在资金限制、价格获取限流或下单模块异常，请检查交易执行逻辑！\n"
        )

    if start_date is not None and end_date is not None:
        manifest_start = manifest.get('start_date')
        manifest_end = manifest.get('end_date')
        if str(manifest_start) != str(start_date) or str(manifest_end) != str(end_date):
            warnings_block.append(
                "> [!WARNING]\n"
                f"> **日期区间不一致警示 (Date Range Discrepancy)**: 当前诊断指定的日期区间 ({start_date} ~ {end_date}) "
                f"与清单中记录的仿真区间 ({manifest_start} ~ {manifest_end}) 不一致！\n"
                f"> 您可能正在读取旧的仿真结果或未运行最新仿真，请通过一键入口重新生成结果！\n"
            )

    if warnings_block:
        report_lines.append("## 异常与警示提示 (Warnings & Diagnostics)\n")
        report_lines.extend(warnings_block)
        report_lines.append("\n")

    report_lines.append("\n## 1. 策略变体全区间表现对比\n")
    if not full_summary.empty:
        report_lines.append(df_to_markdown_safe(full_summary, index=False))
    else:
        report_lines.append("无全区间数据记录。")

    report_lines.append("\n## 2. 样本切分分段表现对比\n")
    if not seg_summary.empty:
        report_lines.append(df_to_markdown_safe(seg_summary, index=False))
    else:
        report_lines.append("无分段数据记录。")

    report_lines.append("\n## 3. 参数小扰动稳定性评估\n")
    report_lines.append(f"- **总收益均值**: {sens_mean_ret:.2%}")
    report_lines.append(f"- **总收益标准差**: {sens_std_ret:.2%}")
    report_lines.append(f"- **总收益区间**: {sens_min_ret:.2%} ~ {sens_max_ret:.2%}")
    report_lines.append(f"- **最大回撤均值/标准差**: {sens_mean_dd:.2%} / {sens_std_dd:.2%}")
    report_lines.append(f"- **稳定性评级**: {'极佳 (Stable)' if sens_std_ret < 0.05 else ('稳健 (Acceptable)' if sens_std_ret < 0.10 else '波动大 (Unstable)')}\n")

    report_lines.append("\n## 4. 成本敏感性测试\n")
    if not cost_sensitivity_df.empty:
        report_lines.append(df_to_markdown_safe(cost_sensitivity_df, index=False))
    else:
        report_lines.append("无成本敏感性测试数据。")

    report_lines.append("\n## 5. 盈利贡献集中度\n")
    if not overfit_df.empty:
        report_lines.append(df_to_markdown_safe(overfit_df, index=False))
    else:
        report_lines.append("无盈利贡献集中度数据。")

    report_lines.append("\n## 6. 晋级机制归因\n")
    report_lines.append(f"- **晋级次数**: {total_promotions} (已退出: {exited_promotions}, 持有中: {held_promotions})")
    report_lines.append(f"- **已退出晋级交易胜率**: {promo_win_rate:.2%}")
    report_lines.append(f"- **晋级全流程总盈亏 (Cash PnL)**: {sum_final_pnl:,.2f}")
    report_lines.append(f"- **晋级后纯段盈亏 (Post-promotion Cash PnL)**: {sum_post_pnl:,.2f}")
    report_lines.append(f"- **晋级后平均持有天数**: {avg_hold_days:.1f} 天\n")

    report_lines.append("\n## 7. 亏损交易归因分析\n")
    report_lines.append(f"- **总卖出笔数**: {total_sells_count} | **亏损笔数**: {len(obs_losses)}")
    report_lines.append(f"- **总亏损金额 (Cash PnL)**: {total_losses_pnl:,.2f}")
    report_lines.append(f"- **快速亏损 (Fast Loss, ≤5天)**: 笔数={fast_loss_count}, 金额={fast_loss_pnl:,.2f}, 占比={fast_loss_count / total_sells_count if total_sells_count > 0 else 0.0:.2%}")
    report_lines.append(f"- **大额亏损 (Big Loss, ≤-6%)**: 笔数={big_loss_count}, 金额={big_loss_pnl:,.2f}, 占比={big_loss_count / total_sells_count if total_sells_count > 0 else 0.0:.2%}")
    report_lines.append(f"- **常规亏损 (Normal Loss)**: 笔数={normal_loss_count}, 金额={normal_loss_pnl:,.2f}, 占比={normal_loss_count / total_sells_count if total_sells_count > 0 else 0.0:.2%}\n")

    report_lines.append("\n## 8. 大肉交易归因分析\n")
    report_lines.append(f"- **盈利笔数**: {len(obs_profits)} | **总盈利金额 (Cash PnL)**: {total_profits_pnl:,.2f}")
    report_lines.append(f"- **大肉交易 (Big Meat, 10%~20%)**: 笔数={big_meat_count}, 金额={big_meat_pnl:,.2f}")
    report_lines.append(f"- **超大肉交易 (Super Meat, ≥20%)**: 笔数={super_meat_count}, 金额={super_meat_pnl:,.2f}")
    report_lines.append(f"- **晋级大肉交易 (Promoted Big Meat, ≥10%)**: 笔数={promoted_big_meat_count}, 金额={promoted_big_meat_pnl:,.2f}\n")

    report_lines.append("\n## 9. 仓位控制与 Cap 限制诊断\n")
    report_lines.append(f"- **买入时发生超仓次数**: {cap_on_buy_count} 次")
    report_lines.append(f"- **日终持仓浮盈自然超仓次数**: {cap_mtm_count} 次\n")

    report_lines.append("\n## 10. 选股机制改进方向\n")
    report_lines.append(f"- 当前存在 {len(entry_feature_need_list)} 个亏损样本显示有买入点改进的潜力 (详见 v14C_entry_feature_need_list.csv)")
    report_lines.append("- 建议引入的选股辅助特征包括: 竞价委买比率、主力大单净流入、个股乖离率指标过滤。\n")

    report_lines.append("\n## 11. 反过拟合稳健性综合大表\n")
    report_lines.append(df_to_markdown_safe(overfit_final_check, index=False))

    report_lines.append("\n## 12. 深度诊断结论 (核心问答)\n")
    report_lines.append("| 问题 | 诊断结论 |")
    report_lines.append("| :--- | :--- |")
    report_lines.append(f"| 1. v1.4.0C 是否优于 baseline_core_only？ | {ans_1} |")
    report_lines.append(f"| 2. v1.4.0C 是否优于 baseline_core_satellite？ | {ans_2} |")
    report_lines.append(f"| 3. 是否通过 validation？ | {ans_3} |")
    report_lines.append(f"| 4. 是否通过 oos？ | {ans_4} |")
    report_lines.append(f"| 5. 参数扰动是否稳定？ | {ans_5} |")
    report_lines.append(f"| 6. 成本敏感性测试是否通过？ | {ans_6} |")
    report_lines.append(f"| 7. 盈利是否过度集中？ | {ans_7} |")
    report_lines.append(f"| 8. 晋级机制是否真实贡献收益？ | {ans_8} |")
    report_lines.append(f"| 9. 亏损交易主要来源是什么？ | {ans_9} |")
    report_lines.append(f"| 10. 大肉交易主要来源是什么？ | {ans_10} |")
    report_lines.append(f"| 11. 选股是否还有提高空间？ | {ans_11} |")
    report_lines.append(f"| 12. 是否建议进入策略观测版？ | {ans_12} |")
    report_lines.append(f"| 13. 是否建议进入主线？ | {ans_13} |")
    report_lines.append(f"| 14. 是否建议进入真实执行版？ | {ans_14} |")

    report_text = "\n".join(report_lines)
    diagnosis_report_path = os.path.join(output_dir, 'v14C_full_diagnosis_report.md')
    try:
        with open(diagnosis_report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        _log(f"Diagnosis report saved: {diagnosis_report_path}")
    except Exception as e:
        _log(f"WARN: failed to save diagnosis report: {e}")

    _log("=" * 60)
    _log("结果分析模块执行完成!")
    _log("=" * 60)


def run_all(start_date, end_date, output_dir="role_rotation_result_bundle"):
    """
    一键运行入口:
    1. 调用 run_research 跑完仿真并输出初始 CSV/Excel/Markdown。
    2. 调用 analyze_results 跑完分析模块并输出 v14C 诊断 CSV/Excel/Markdown。
    3. 重新打包所有生成的 CSV, Markdown, Excel 文件到 role_rotation_result_bundle.zip。
    """
    _log("*" * 60)
    _log("v1.4.0C 核心/卫星角色轮动 一键运行与诊断模块开始...")
    _log(f"区间: {start_date} ~ {end_date} | 输出目录: {output_dir}")
    _log("*" * 60)

    # 1. 跑仿真
    run_research(start_date, end_date, output_dir)

    # 2. 跑分析
    analyze_results(output_dir, start_date=start_date, end_date=end_date)

    # 3. 重新打包
    _bundle_outputs(output_dir)

    _log("*" * 60)
    _log("v1.4.0C 一键运行与诊断执行完成!")
    _log("*" * 60)


# 支持 %run -i 方式直接运行
if __name__ == '__main__':
    # 聚宽 Notebook 中 %run -i 时 jqdata 已在全局命名空间
    import sys
    _mod = sys.modules[__name__]
    for _api in ['get_price', 'get_trade_days', 'get_all_securities', 'get_extras', 'get_call_auction']:
        if getattr(_mod, _api) is None:
            _global = globals()
            if _api in _global:
                setattr(_mod, _api, _global[_api])
    run_research()
