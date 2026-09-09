# =========================================================
# Strategy Version: v1.5.0
# Updated: 2026-07-06
# Status: research/backtest — UNVERIFIED, 必须在聚宽回测验证后才可考虑实盘
# Main File: 战车A龙头3_v1.5.0.py
# Source From: 战车A龙头3_v1.4.0D_observer.py
#
# === V1.5.0 改动(基于 V1.1.0 日志复盘结论,3 处) ===
# 结论来源: 66交易日回测(3/30~7/6)+ skill 量价/周期知识
#   痛点1: 退潮期把主升利润吐回一大半(净值 1.32→1.12),因只有 bear 降仓、无空仓闸
#   痛点2: 硬止损设 -3.5% 实际砍在 -6.39%(最差 -12.44%),大跳空傻等 09:35 确认穿透止损
#   痛点3: bear 下 deep_water 减半,方向反了(skill 验证退潮日 deep_water 抗跌)
#   注: 250 预筛已在 v1.4.0D 内置(_prefilter_dragon_auction_candidates),本版沿用
#
# [改动1] 退潮/冰点空仓闸(EBB_CASH_GATE) —— 治痛点1
#   - get_A_mode 里加闸: 冰点(大盘3日急跌) 或 退潮(bear+龙头竞价分弱) → 强制 idle 不新开仓
#   - 只挡"新开仓",不强平持仓(持仓仍按各自止损管理)
#   - 参数在 make_global_config 的 ebb_* ,全部 TUNABLE,回测需校准
# [改动2] 灾难性跳空立即止损(catastrophic_gap) —— 治痛点2
#   - gap_down_stop_loss 里: 开盘跌幅 <= -catastrophic_gap(默认-6%) 直接立即止损
#   - 不进 09:35 延迟确认队列(延迟确认只留给小跳空),防 -3.5% 拖成 -12%
# [改动3] deep_water 退潮偏向 —— 治痛点3
#   - dragon_bear_allow_deep_water: 'half' → True(bear 下 deep_water 给足仓位)
#
# 诚实标注: 以上参数默认值是"结论方向"的合理起点,非最优;阈值(空仓闸的分数线/
#   急跌幅度、灾难跳空幅度)必须由 Wallace 在聚宽回测中校准。本版未做任何回测。
# =========================================================

# =========================================================
# Strategy Version: v1.4.0D_observer (base)
# Updated: 2026-06-21
# Status: research-only observer branch
# Source From: 战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py
# Research Target: strategy-implementation approximation of D3_no_promotion_take_profit_plus_cap_fixed
# Note: v1.4.0C is represented by research_role_rotation_direct_sim_v1.py and role_rotation_result_bundle V140C; no standalone v1.4.0C strategy py was found.
# Note: 当前 no_promotion 是 observer proxy，不是 D3 replay 的严格 ROLE_PROMOTION_EXECUTE 等价实现。
# Change Type:
# - D3_no_promotion_take_profit_plus_cap_fixed
# - cap-fixed-order-trim
# - no-promotion-take-profit-observer
# - entry-exit-outcome-logging
# Notes:
# - Based on D3_no_promotion_take_profit_plus_cap_fixed.
# - Research-only observer branch; not mainline.
# - Not live trading.
# - No deep_water relaxation.
# - No position expansion.
# - No auto parameter search.
# =========================================================

# =========================================================
# Strategy Version: v1.4.0B-shadow-rotation-original-core
# Updated: 2026-06-15
# Status: 独立控制变量实验版
# Main File: 战车A龙头3_v1.4.0B_shadow_rotation_original_core.py
# Source From: 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py
# Change Type:
# - shadow-rotation-original-core
# - single-watch-pool-satellite
# - independent-experiment
# Notes:
# - 恢复原核心仓：Top1 35%、Top2 25%、初始上限 60%、总仓 75%
# - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1
# - 不做卫星替换，用于验证原核心 + 小卫星仓是否增厚收益
# - 不修改原策略文件，不绕开 v1.1.3 交易账本
# - 卫星仓使用独立 slot_type/strategy_tag 标记
# =========================================================

# =========================================================
# 战车A BigMeat Simple
# 聚宽网页版回测专用
# =========================================================
#
# 当前策略：
# - 新开仓仅允许 Dragon + deep_water
# - 核心仓 Top1 35%，Top2 25%，核心初始上限 60%
# - 新增 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1
# - 实验版总仓位上限 75%，单股上限 50%
# - 尾盘只向盈利赢家加仓 15%，不向亏损仓加仓，不在买入当天加仓
# - Dragon -3.5% 预警，-5% 确认止损
# - 10:00 后弱势跌破 MA5 才执行失败退出
# - 盈利 >=10% 后跌破 MA5 卖半仓
# - 半仓后跌破 max(prev_close, MA5) 清仓
# - Dragon 连续硬亏 2 笔暂停 2 个交易日
#
# 工程约束：
# - 仅面向聚宽网页版回测
# - 不启用 QMT、TickEngine、L2、ATR、OBV、竞价评分或本地报告
# - 不接入 firstboard_lowopen、firstboard、weak_to_strong、DPM 或统一评分
# - FAST_MODE 每日保留 10 个止损检查点
#
# 2026-06-12：日志结构化、股票中文名缓存、删除旧实验与死代码。
# =========================================================

from jqdata import *
import numpy as np
import pandas as pd
import datetime


EXPERIMENT_NAME = 'BIGMEAT_SIMPLE'

EXPERIMENTS = {
    'BIGMEAT_SIMPLE': {
        'global': {},
        'A': {},
    },
}


def apply_experiment_overrides(global_cfg, strategy_a_cfg):
    exp = EXPERIMENTS.get(EXPERIMENT_NAME)
    if exp is None:
        raise ValueError("Unknown EXPERIMENT_NAME={}".format(EXPERIMENT_NAME))

    global_overrides = exp.get('global', {})
    a_overrides = exp.get('A', {})

    global_cfg.update(global_overrides)
    strategy_a_cfg.update(a_overrides)

    log.info("EXPERIMENT|name={}".format(EXPERIMENT_NAME))

    return global_cfg, strategy_a_cfg


# =============================================================================
# 第一层: 配置 (Config)
# =============================================================================

def make_global_config():
    """全局配置：环境判定、风控、仓位管理等，与具体策略无关"""
    return {
        # --- 市场状态雷达 ---
        'regime_index': '000852.XSHG',
        'regime_secondary_index': '000300.XSHG',
        'regime_dual_enable': True,
        'regime_dual_override_bear_to_neutral': True,
        'regime_dual_upgrade_neutral_to_bull': False,
        'regime_lookback': 20,
        'regime_bull_ma_fast': 5,
        'regime_bull_ma_mid': 10,
        'regime_bull_ma_slow': 20,
        'regime_confirm_days': 2,
        'regime_crash_3d_threshold': -0.05,

        # --- [V1.5.0 改动1] 退潮/冰点空仓闸 (EBB_CASH_GATE) ---
        # 目的: 退潮/冰点期强制空仓(不新开仓),把主升期利润守住,别再吐回去。
        #       只挡"新开仓",持仓仍由各自止损管理。触发即在 get_A_mode 返回 idle。
        # 全部 TUNABLE —— 阈值必须在聚宽回测中校准(下面是结论方向的保守起点)。
        'ebb_cash_gate_enable': True,
        # 冰点闸: 大盘(regime_index)近3日累计跌幅 <= 此值 → 冰点, 空仓(接飞刀最危险)
        'ebb_ice_crash_3d': -0.05,
        # 退潮闸: regime==bear 且 当日龙头竞价最高分 < 此值 → 无强势龙头的弱市, 空仓
        # (主升期日志 top_score 常 0.78~0.85; 退潮期龙头分走弱, 0.72 为保守分界)
        'ebb_bear_top_score_floor': 0.72,
        # 退潮闸加强: dragon_score_ema 衰减到峰值的此比例以下 且 regime!=bull → 情绪退潮, 空仓
        'ebb_ema_peak_decay': 0.55,

        # --- Dragon / Crowding ---
        'dragon_score_ema_alpha': 0.3,
        'crowding_max_consecutive_days': 10,
        'crowding_cooldown_days': 3,

        # --- Dragon 连亏保护 ---
        'dragon_loss_pause_after': 2,        # 连亏2笔暂停Dragon
        'dragon_loss_pause_days': 2,         # 暂停天数

        # --- 全局风控 ---
        'max_total_positions': 3,
        'max_portfolio_position_ratio': 0.75,
        'max_daily_new_positions': 3,

        # --- Dragon选股参数 ---
        'dragon_auc_top_n': 80,
        'dragon_cluster_top2_avg': 0.080,
        'dragon_min_auction_amount': 8.0e6,
        'dragon_min_auction_ratio': 0.006,
        'dragon_min_prev_money': 1.5e8,
        'dragon_money_top_pct': 0.20,
        'dragon_panic_override_score': 0.100,
        'dragon_prev_auction_mult': 0.50,
        'dragon_ret3_top_n': 160,
        'dragon_strong_single_score': 0.120,
        'dragon_top_score_trigger': 0.090,

        # --- Dragon评分体系选择 ---
        # 'v1' = 原始评分(追涨型: 竞价越强+涨幅越大=分越高)
        # 'v2' = 优化评分(回调型: 涨过但回调过的票得分更高)
        # 'v3' = Dragon预测评分(基于1150条V4全量因子分析)
        #        核心: 反转收高比+振幅+低换手率 → 精准筛选Dragon潜力股
        #        回测: Top3 f1日均+1.25%(当前+0.31%), 累计+361%(当前+90%)
        'dragon_score_mode': 'v3',

        # --- [v9.0.25] 缺口止损延迟确认 ---
        # 09:31标记预警 → 09:35确认, 期间价格恢复到-2%以上则取消止损
        'gap_down_recovery_ratio': 0.02,     # 恢复阈值: pnl > -2%视为恢复


        'backtest_fast_mode': True,
        'bigmeat_pool_log_top_n': 3,
        'bigmeat_verbose_pool_log': False,
        'position_log_interval_days': 5,

        # --- 杂项 ---
        'exclude_prefixes': ('30', '688', '689', '8', '4', '9'),
        'market_panic_drop': -0.02,
        'new_stock_days': 50,
        'dragon_enable': True,
        'dragon_max_avg_daily_range': 0.08,
        'cooldown_days_after_sell': 3,
        'cooldown_days_after_sell_dragon': 4,
        'crowding_exit_pool_min': 3,
        'crowding_exit_score_decay_ratio': 0.60,
        'dragon_crowding_confirm_days': 2,

        # --- 趋势过滤系统 ---
        # 大盘趋势: 用regime_index的均线判断
        'trend_market_ma_fast': 5,               # 短期均线
        'trend_market_ma_mid': 10,                # 中期均线
        'trend_market_ma_slow': 20,               # 长期均线
        'trend_market_lookback': 25,              # 取数天数(需>ma_slow+5)
        # 个股趋势
        'trend_stock_ma_fast': 5,
        'trend_stock_ma_mid': 10,
        'trend_stock_ma_slow': 20,
        'trend_stock_lookback': 30,               # 取数天数
        'trend_higher_low_tolerance': 0.02,       # 低点抬升容忍度(2%)
    }


def make_strategy_A_config():
    """BigMeat Dragon-only 私有配置。"""
    return {
        'name': 'A',
        'open_time': '09:32',
        'max_hold': 2,
        'pos_ratio': 0.35,

        # --- Dragon模式 ---
        'dragon_max_hold': 2,
        'dragon_warn_stop': 0.035,
        'dragon_confirm_stop': 0.05,
        # [V1.5.0 改动2] 灾难性跳空: 开盘跌幅 <= -此值 → 立即止损, 不进09:35延迟确认。
        # 延迟确认(09:31预警→09:35恢复取消)只适合小跳空; 大跳空傻等会把-3.5%拖成-12%。
        'dragon_catastrophic_gap': 0.06,  # TUNABLE: 回测校准(-6% 起步)
        'dragon_profit_protect': 0.10,
        'livermore_add_pos_ratio': 0.15,
        'winner_add_pos_ratio': 0.15,
        'winner_add_pos_ratio_market_down': 0.10,
        'winner_add_pnl_threshold': 0.10,
        'winner_add_pnl_threshold_market_down': 0.15,
        'top1_pos_ratio': 0.35,
        'top2_pos_ratio': 0.25,
        'max_single_stock_ratio': 0.50,
        'max_total_position_ratio': 0.75,
        'max_initial_position_ratio': 0.60,
        'dragon_max_open_ratio': 0.055,

        # --- 兼容止损 ---
        'abs_stop_loss': 0.05,

        # --- 回撤保护 ---
        'deep_dd_trigger_level': 0.15,
        'deep_dd_cooldown_days': 3,
        'dd_pause_days': 3,
        'dd_rearm_recovery': 0.03,
        'dd_rearm_level': 0.13,
        'deadlock_flat_days': 10,

        # --- 选股参数 ---
        'min_prev_money': 5.5e8,
        'max_prev_money': 20e8,
        'min_auction_volume_ratio': 0.028,
        'dragon_min_ret_3d': 0.03,
        'dragon_partial_take_profit': 0.20,
        # --- 选股/打分门槛 ---
        'limit_up_buffer': 0.995,
        'dragon_min_score': 0.70,
        'dragon_min_open_ratio': 0.015,
        # [V1.5.0 改动3] deep_water 退潮偏向: 'half' → True。
        # skill 验证退潮日 deep_water(深水低吸)抗跌、trend_core 被杀, 所以 bear 下不该砍
        # deep_water 反而该给足仓位。(可选: True/False/'half')
        'dragon_bear_allow_deep_water': True,
        'dragon_deep_water_max_open_ratio': 0.055,
    }


# ================== 分钟级统一止损 ==================

def _get_stop_level(strategy, entry_type):
    """止损阈值查找(仅A策略)"""
    if strategy == 'A':
        if entry_type == 'dragon_follow':
            return g.cfg.get('A_dragon_confirm_stop', 0.05)
        return g.cfg.get('A_abs_stop_loss', 0.05)
    else:
        return 0.05


def _get_ma5_base_sum(stock, context):
    """缓存前4个日收盘价之和，同一天同一只股票只查询一次。"""
    today = context.current_dt.date()
    if getattr(g, 'ma5_base_cache_date', None) != today:
        g.ma5_base_cache = {}
        g.ma5_base_cache_date = today
    if stock in g.ma5_base_cache:
        return g.ma5_base_cache[stock]
    try:
        h = attribute_history(stock, 4, '1d', ['close'], skip_paused=True)
        if h is None or len(h) < 4:
            return None
        base_sum = float(h['close'].iloc[-4:].sum())
        g.ma5_base_cache[stock] = base_sum
        return base_sum
    except Exception:
        return None


def _estimate_intraday_ma5(stock, curr_price, context):
    """用缓存的前4日收盘价和当前价估算当日MA5。"""
    base_sum = _get_ma5_base_sum(stock, context)
    if base_sum is None:
        return None
    return (base_sum + float(curr_price)) / 5.0


def get_stock_name_cached(stock):
    """获取股票中文名，并在策略生命周期内缓存。"""
    if not hasattr(g, 'stock_name_cache'):
        g.stock_name_cache = {}
    if stock in g.stock_name_cache:
        return g.stock_name_cache[stock]

    name = None
    try:
        current_data = get_current_data()
        item = current_data[stock]
        name = getattr(item, 'name', None)
    except Exception:
        pass

    if not name:
        static_info = get_security_static_info_cached(stock)
        name = static_info.get('display_name') or static_info.get('name')

    name = str(name).strip() if name else stock
    g.stock_name_cache[stock] = name
    return name


def get_security_static_info_cached(stock):
    """缓存证券名称和上市日期等静态字段，不缓存任何实时行情。"""
    if not hasattr(g, 'security_info_cache'):
        g.security_info_cache = {}
    if not hasattr(g, 'security_start_date_cache'):
        g.security_start_date_cache = {}
    if stock in g.security_info_cache and stock in g.security_start_date_cache:
        cached = dict(g.security_info_cache[stock])
        cached['start_date'] = g.security_start_date_cache[stock]
        return cached

    try:
        info = get_security_info(stock)
        static_info = {
            'display_name': getattr(info, 'display_name', None),
            'name': getattr(info, 'name', None),
        }
        start_date = getattr(info, 'start_date', None)
        g.security_info_cache[stock] = static_info
        g.security_start_date_cache[stock] = start_date
        result = dict(static_info)
        result['start_date'] = start_date
        return result
    except Exception:
        return {}


def _set_dragon_stop_warning(stock, meta, pnl, source):
    if meta.get('dragon_stop_warning', False) or meta.get('stop_warning', False):
        return
    meta['dragon_stop_warning'] = True
    meta['stop_warning'] = True
    diag_add('dragon_stop_warnings')
    log.info(
        "DRAGON_STOP|stock={}|name={}|reason=dragon_stop_warning|source={}|pnl={:.2f}%".format(
            stock, get_stock_name_cached(stock), source, pnl * 100
        )
    )


def _clear_dragon_stop_warning(stock, meta, pnl, source):
    if not meta.get('dragon_stop_warning', False) \
            and not meta.get('stop_warning', False):
        return
    meta['dragon_stop_warning'] = False
    meta['stop_warning'] = False
    log.info(
        "DRAGON_STOP|stock={}|name={}|reason=warning_recovered|source={}|pnl={:.2f}%".format(
            stock, get_stock_name_cached(stock), source, pnl * 100
        )
    )


def _evaluate_dragon_intraday_stop(stock, meta, pnl, curr_price, ma5, current_dt, source):
    """返回Dragon盘中清仓原因；-3.5%仅预警，-5%始终确认止损。"""
    cfg_a = g.strategies['A']['config']
    warn_stop = cfg_a.get('dragon_warn_stop', 0.035)
    confirm_stop = cfg_a.get('dragon_confirm_stop', 0.05)
    now_hm = current_dt.strftime('%H:%M') if hasattr(current_dt, 'strftime') else '10:00'

    if pnl > -g.cfg.get('gap_down_recovery_ratio', 0.02):
        _clear_dragon_stop_warning(stock, meta, pnl, source)

    if pnl <= -confirm_stop:
        _set_dragon_stop_warning(stock, meta, pnl, source)
        return 'dragon_confirm_stop'

    if now_hm < '10:00':
        if pnl <= -warn_stop:
            _set_dragon_stop_warning(stock, meta, pnl, source)
        return None

    below_ma5 = ma5 is not None and curr_price < ma5
    if below_ma5:
        meta['below_ma5_count'] = int(meta.get('below_ma5_count', 0) or 0) + 1
    else:
        meta['below_ma5_count'] = 0

    if pnl <= -warn_stop:
        _set_dragon_stop_warning(stock, meta, pnl, source)
        if below_ma5:
            return 'dragon_delayed_stop'

    failfast_reason = None
    if pnl <= -0.015 and below_ma5:
        failfast_reason = 'dragon_fail_fast'
    elif pnl <= 0 and meta['below_ma5_count'] >= 2:
        failfast_reason = 'dragon_fail_fast_confirmed'

    # [LOG OPT] Track failfast state transitions to reduce noise
    prev_failfast = meta.get('_prev_failfast_reason')
    if failfast_reason != prev_failfast:
        if failfast_reason:
            log.info(
                "DRAGON_FAILFAST|stock={}|name={}|pnl={:.2f}%|below_ma5_count={}|"
                "reason={}|source={}".format(
                    stock, get_stock_name_cached(stock), pnl * 100, meta['below_ma5_count'],
                    failfast_reason, source
                )
            )
        elif prev_failfast:
            log.info(
                "DRAGON_FAILFAST_RECOVER|stock={}|name={}|pnl={:.2f}%|below_ma5_count={}|"
                "source={}".format(
                    stock, get_stock_name_cached(stock), pnl * 100, meta['below_ma5_count'],
                    source
                )
            )
    meta['_prev_failfast_reason'] = failfast_reason
    if failfast_reason:
        return failfast_reason

    return None


def minute_stop_loss_all(context):
    """聚宽分钟止损检查，并重试尚未完成的退出委托。"""
    try:
        sync_position_meta_with_real_positions(context)
        positions = context.portfolio.positions
        if not positions:
            return

        # Step0: pending_exit重试 — 对已标记待退出但仍有持仓的股票重新下单
        pending_retry_stocks = []
        for stock in list(positions.keys()):
            meta = g.positions_meta.get(stock)
            if not meta or not meta.get('pending_exit', False):
                continue
            pos = positions[stock]
            if pos.closeable_amount <= 0:
                continue
            pending_retry_stocks.append(stock)

        # Step1: 预筛有效持仓(纯状态过滤,不需要tick)
        candidate_stocks = []
        for stock in list(positions.keys()):
            try:
                pos = positions[stock]
                if pos.total_amount <= 0 or pos.closeable_amount <= 0:
                    continue
                meta = g.positions_meta.get(stock, {})
                if meta.get('pending_exit', False):
                    continue
                if meta.get('pending_stage_change'):
                    continue
                avg_cost = getattr(pos, 'avg_cost', 0)
                if avg_cost is None or avg_cost <= 0:
                    continue
                strategy = meta.get('strategy', '')
                if strategy != 'A':
                    continue
                candidate_stocks.append(stock)
            except Exception as e:
                log.warning(
                    "MINUTE_STOP_ERROR|stock={}|name={}|stage=filter|error={}".format(
                        stock, get_stock_name_cached(stock), e
                    )
                )

        # 聚宽对象支持批量预取时使用，失败则静默回退到逐票读取。
        all_need_tick = list(set(pending_retry_stocks + candidate_stocks))
        current_data = get_current_data()
        if all_need_tick and hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(all_need_tick)
            except Exception:
                pass  # 静默降级, 不刷屏

        # Step2.5: 执行pending_exit重试(跌停跳过, 每天最多5次)
        for stock in pending_retry_stocks:
            try:
                meta = g.positions_meta.get(stock, {})
                retry_count = meta.get('_exit_retry_count', 0)
                retry_date = meta.get('_exit_retry_date', None)
                today = context.current_dt.date()
                if retry_date != today:
                    retry_count = 0
                if retry_count >= 5:
                    continue
                curr_price = current_data[stock].last_price
                if curr_price is None or curr_price <= 0:
                    continue
                low_limit = current_data[stock].low_limit
                if low_limit and curr_price <= low_limit * 1.001:
                    if retry_count == 0:
                        log.info(
                            "PENDING_EXIT_SKIP|stock={}|name={}|reason=limit_down".format(
                                stock, get_stock_name_cached(stock)
                            )
                        )
                    meta['_exit_retry_count'] = 5
                    meta['_exit_retry_date'] = today
                    continue
                if order_target_value(stock, 0) is not None:
                    meta['_exit_retry_count'] = retry_count + 1
                    meta['_exit_retry_date'] = today
                    log.info(
                        "PENDING_EXIT_RETRY|stock={}|name={}|retry_count={}".format(
                            stock, get_stock_name_cached(stock), retry_count + 1
                        )
                    )
                    diag_add('retry_pending_exit')
            except Exception as e:
                log.warning(
                    "PENDING_EXIT_ERROR|stock={}|name={}|error={}".format(
                        stock, get_stock_name_cached(stock), e
                    )
                )

        # Step3: 在内存中逐票判断，不执行 Tick/L2/ATR/量能实验路径。
        for stock in candidate_stocks:
            try:
                pos = positions.get(stock)
                if pos is None:
                    continue

                meta = g.positions_meta.get(stock, {})
                strategy = meta.get('strategy', '')
                entry_type = meta.get('entry_type', '')

                cd_item = current_data[stock]
                curr_price = cd_item.last_price
                if curr_price is None or curr_price <= 0:
                    continue

                avg_cost = pos.avg_cost
                if avg_cost is None or avg_cost <= 0:
                    continue

                pnl = curr_price / avg_cost - 1
                exit_reason = None

                # [V1.0.0] 缺口预警期间跳过分钟止损，等09:35确认
                if hasattr(g, 'gap_down_alerts') and stock in g.gap_down_alerts:
                    continue

                # 检查1: Dragon使用BigMeat延迟确认；兼容持仓保留原固定止损。
                if entry_type == 'dragon_follow':
                    ma5 = _estimate_intraday_ma5(stock, curr_price, context)
                    exit_reason = _evaluate_dragon_intraday_stop(
                        stock, meta, pnl, curr_price, ma5, context.current_dt, 'minute'
                    )
                    if exit_reason:
                        _hold_days_dragon = (context.current_dt.date() - meta['buy_date']).days \
                            if meta.get('buy_date') else '?'
                        log.info(
                            "DRAGON_SELL|stock={}|name={}|reason={}|pnl={:.2f}%|stage={}|"
                            "curr_price={:.3f}|ma5={}|hold_days={}|avg_cost={:.3f}|"
                            "warning_stop={}|delayed_stop={}|"
                            "confirm_stop={}".format(
                                stock, get_stock_name_cached(stock), exit_reason,
                                pnl * 100, meta.get('stage', 'full'),
                                curr_price, '{:.3f}'.format(ma5) if ma5 is not None else 'NA',
                                _hold_days_dragon,
                                float(avg_cost) if avg_cost else 0,
                                int(meta.get('dragon_stop_warning', False)),
                                int(exit_reason == 'dragon_delayed_stop'),
                                int(exit_reason == 'dragon_confirm_stop')
                            )
                        )
                else:
                    stop_pct = _get_stop_level(strategy, entry_type)
                    if pnl <= -stop_pct:
                        exit_reason = 'minute_stop_loss'
                        log.info(
                            "MINUTE_STOP|stock={}|name={}|strategy={}|entry_type={}|"
                            "pnl={:.2f}%|stop={:.2f}%".format(
                                stock, get_stock_name_cached(stock), strategy,
                                entry_type, pnl * 100, stop_pct * 100
                            )
                        )

                # 执行退出
                if exit_reason:
                    if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=pnl):
                        diag_add('{}_sell_all'.format(strategy))
                        if entry_type == 'dragon_follow':
                            diag_add('dragon_sell_orders')
                        if exit_reason in (
                                'minute_stop_loss', 'dragon_confirm_stop',
                                'dragon_delayed_stop', 'dragon_fail_fast',
                                'dragon_fail_fast_confirmed'):
                            diag_add('stop_loss_triggered')
            except Exception as e:
                log.error(
                    "MINUTE_STOP_ERROR|stock={}|name={}|stage=evaluate|error={}".format(
                        stock, get_stock_name_cached(stock), e
                    )
                )

    except Exception as e:
        log.error("MINUTE_STOP_ERROR|stage=global|error={}".format(e))


# =============================================================================
# 第二层: 框架核心 (Framework)
# =============================================================================

def initialize(context):
    log.info("BIGMEAT_SIMPLE|platform=joinquant_web|status=starting")
    log.info("RUN_ENV|platform=joinquant_web|qmt=0|local=0|tick_engine=disabled")
    set_benchmark('000852.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_slippage(FixedSlippage(0.02))

    # 本版本只面向聚宽网页版回测，QMT/Tick 二次确认不参与运行。
    g.is_qmt = False

    # 配置初始化
    g.cfg = make_global_config()
    g.strategies = {}

    # 仅注册A策略
    a_cfg = make_strategy_A_config()
    g.cfg, a_cfg = apply_experiment_overrides(g.cfg, a_cfg)
    register_strategy('A', a_cfg, {
        'select': select_candidates_A,
        'score': score_candidates_A,
        'sell_rules': evaluate_sell_signal_A,
        'get_mode': get_A_mode,
    })

    # 状态初始化
    init_framework_state()

    # 兼容层: 将策略配置合并到g.cfg
    _merge_strategy_configs_to_global()

    # 调度注册
    schedule_all(context)

    # 回测统计
    g.bt = {
        'version': '2026-06-11_BigMeat_Simple', 'start_cash': context.portfolio.starting_cash,
        'trade_days': 0, 'closed_trades': 0, 'wins': 0, 'losses': 0, 'flats': 0,
        'win_ret_sum': 0.0, 'loss_ret_sum': 0.0,
        'nav_history': [], 'peak_nav': 1.0, 'current_dd': 0.0,
        'max_drawdown': 0.0, 'start_date': '',
    }


def register_strategy(name, config, handlers):
    """注册一个策略模块"""
    g.strategies[name] = {
        'config': config,
        'handlers': handlers,
        'budget': {'max_hold': config['max_hold'], 'pos_ratio': config['pos_ratio']},
    }


def _merge_strategy_configs_to_global():
    """兼容层：将策略私有配置以 A_xxx / B_xxx 前缀合并到 g.cfg
    使得迁移自v5.9.0的函数可以继续用 g.cfg['A_xxx'] 访问策略参数"""
    key_map = {
        'A': {
            'abs_stop_loss': 'A_abs_stop_loss',
            'dragon_warn_stop': 'A_dragon_warn_stop',
            'dragon_confirm_stop': 'A_dragon_confirm_stop',
            'dragon_profit_protect': 'A_dragon_profit_protect',
            'livermore_add_pos_ratio': 'A_livermore_add_pos_ratio',
            'winner_add_pos_ratio': 'A_winner_add_pos_ratio',
            'winner_add_pos_ratio_market_down': 'A_winner_add_pos_ratio_market_down',
            'winner_add_pnl_threshold': 'A_winner_add_pnl_threshold',
            'winner_add_pnl_threshold_market_down': 'A_winner_add_pnl_threshold_market_down',
            'top1_pos_ratio': 'A_top1_pos_ratio',
            'top2_pos_ratio': 'A_top2_pos_ratio',
            'max_single_stock_ratio': 'A_max_single_stock_ratio',
            'max_total_position_ratio': 'A_max_total_position_ratio',
            'max_initial_position_ratio': 'A_max_initial_position_ratio',
            'dragon_max_hold': 'A_dragon_max_hold',
            'dragon_max_open_ratio': 'A_dragon_max_open_ratio',
            'deep_dd_trigger_level': 'A_deep_dd_trigger_level',
            'dd_pause_days': 'A_dd_pause_days',
            'dd_rearm_recovery': 'A_dd_rearm_recovery',
            'deadlock_flat_days': 'A_deadlock_flat_days',
            'open_time': 'A_open_time',
            'dd_rearm_level': 'A_dd_rearm_level',
            'deep_dd_cooldown_days': 'A_deep_dd_cooldown_days',
            'dragon_min_ret_3d': 'A_dragon_min_ret_3d',
            'dragon_partial_take_profit': 'A_dragon_partial_take_profit',
            'max_prev_money': 'A_max_prev_money',
            'min_auction_volume_ratio': 'A_min_auction_volume_ratio',
            'min_prev_money': 'A_min_prev_money',
            'limit_up_buffer': 'A_limit_up_buffer',
            'dragon_min_score': 'A_dragon_min_score',
            'dragon_min_open_ratio': 'A_dragon_min_open_ratio',
            'dragon_bear_allow_deep_water': 'A_dragon_bear_allow_deep_water',
            'dragon_deep_water_max_open_ratio': 'A_dragon_deep_water_max_open_ratio',
        },
    }
    for strat_name, mapping in key_map.items():
        strat_cfg = g.strategies[strat_name]['config']
        for local_key, global_key in mapping.items():
            if local_key in strat_cfg:
                g.cfg[global_key] = strat_cfg[local_key]


def schedule_all(context):
    """聚宽网页版统一调度注册。"""
    cfg = g.cfg

    run_daily(morning_prepare, '09:00')
    run_daily(post_auction_prepare, '09:28')
    run_daily(gap_down_stop_loss, '09:31')
    run_daily(gap_down_confirm, '09:35')
    run_daily(_trade_A, '09:32')

    run_daily(orphan_sweeper_execute, '11:26')
    run_daily(_sell_A_1, '11:20')
    run_daily(check_livermore_tail_add, '14:40')
    run_daily(shadow_rotation_exit_check, '14:43')
    run_daily(shadow_rotation_confirm_check, '14:45')
    run_daily(_sell_A_2, '14:50')

    if cfg.get('backtest_fast_mode', True):
        fast_stop_times = [
            '09:40', '09:50', '10:00', '10:15', '10:30',
            '11:00', '13:30', '14:00', '14:30', '14:50',
        ]
        for t in fast_stop_times:
            run_daily(minute_stop_loss_all, t)
        log.info("FAST_MODE|minute_stop_schedule=10_points")
    else:
        for hour in range(9, 15):
            for minute in range(0, 60, 2):
                t = '%02d:%02d' % (hour, minute)
                if ('09:32' <= t <= '11:28') or ('13:00' <= t <= '14:56'):
                    run_daily(minute_stop_loss_all, t)

    run_daily(after_market_close, '15:10')


# --- 聚宽 run_daily 不支持 lambda，用具名函数包装 ---
def _trade_A(context):
    try:
        strategy_trade(context, 'A')
    except Exception as e:
        log.error("TASK_ERROR|task=trade_A|error={}".format(e))


def _sell_A_1(context):
    try:
        strategy_sell_only(context, 'A')
    except Exception as e:
        log.error("TASK_ERROR|task=sell_A_1|error={}".format(e))

def _sell_A_2(context):
    try:
        strategy_sell_only(context, 'A')
    except Exception as e:
        log.error("TASK_ERROR|task=sell_A_2|error={}".format(e))


# =============================================================================
# 第三层: 状态管理 (State)
# =============================================================================

def init_framework_state():
    """初始化所有框架级状态"""
    # --- Regime ---
    g.market_regime = 'neutral'
    g.micro_regime = 'neutral_trend'
    g.pending_regime = None
    g.pending_regime_days = 0
    g.regime_secondary_raw = 'neutral'
    g.regime_dual_override_active = False

    g.stock_name_cache = {}
    g.security_info_cache = {}
    g.security_start_date_cache = {}
    g.dragon_pause_last_log_key = None

    g.gap_down_alerts = {}  # 缺口止损延迟确认预警列表

    # --- Dragon / Crowding ---
    g.dragon_mode = False
    g.dragon_pool_size = 0
    g.dragon_top_score = 0.0
    g.dragon_candidates_today = []
    g.dragon_signal_reason = 'none'
    g.dragon_evaluated_today = False
    g.dragon_score_ema = 0.0
    g.crowding_confirm_days = 0
    g.crowding_consecutive_days = 0
    g.crowding_cooldown_left = 0
    g.crowding_signal_raw = False
    g.crowding_peak_score = 0.0
    g.prev_micro_regime = 'neutral_trend'

    # --- Dragon 断路器 ---
    g.dragon_consecutive_losses = 0
    g.dragon_soft_losses = 0
    g.dragon_circuit_breaker_pause_left = 0
    g.dragon_loss_history = []              # 追踪连亏幅度，用于平均亏损门槛
    g.dragon_reduced_pos_active = False     # BigMeat兼容字段，不启用降仓
    g.dragon_pause_just_triggered = False
    g.dragon_bear_weekly_count = 0
    g.dragon_bear_weekly_reset_countdown = 0

    # --- 持仓管理 ---
    g.positions_meta = {}
    g.pending_buys = {}
    g.cooldown = {}
    g.strategy_budget = {'A': {}}

    # --- 全局控制 ---
    g.no_new_position_today = False
    g.daily_new_position_count = 0

    # --- A策略状态 ---
    g.A_dd_cooldown_active = False
    g.A_pause_days_left = 0
    g.A_dd_rearm_ready = True
    g.A_rearm_grace_days_left = 0
    g.A_flat_days = 0

    # --- 趋势过滤系统 ---
    g.market_trend = 'sideways'          # 大盘趋势: up/down/sideways
    g.intraday_panic_active = False      # 盘中大跌标记(不再拦截,由趋势过滤器处理)

    g.panic_yesterday_ret = 0.0

    # --- 诊断 ---
    g.diag = {}
    g.ma5_base_cache = {}
    g.ma5_base_cache_date = None

    # --- v1.4.0A Shadow Rotation Full-B ---
    g.shadow_rotation_enabled = True
    g.core_slots = 2
    g.core_target_total_ratio = 0.60
    g.core_slot_ratio = 0.35
    g.shadow_satellite_slots = 1
    g.shadow_satellite_slot_ratio = 0.15
    g.max_total_position_ratio = 0.75
    g.shadow_watch_pool = {}
    g.shadow_daily = {}
    g.shadow_confirmed_today = set()
    g.shadow_satellite_submitted_today = set()


# =============================================================================
# 第四层: 通用引擎 (Common Engine)
# =============================================================================

# ---------- 通用卖出引擎 ----------

def strategy_sell_only(context, strategy_name):
    """通用卖出流程：遍历该策略持仓，调用策略的sell_rules"""
    sync_position_meta_with_real_positions(context)
    strat = g.strategies[strategy_name]
    sell_rules = strat['handlers']['sell_rules']
    current_data = get_current_data()

    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta or meta.get('strategy') != strategy_name:
            continue
        if meta.get('pending_exit', False):
            continue
        if meta.get('pending_stage_change'):
            continue

        pos = context.portfolio.positions[stock]
        if pos.closeable_amount <= 0:
            continue

        curr_price = current_data[stock].last_price
        if curr_price is None or curr_price <= 0:
            continue

        avg_cost = pos.avg_cost
        pnl = curr_price / avg_cost - 1 if avg_cost > 0 else 0.0

        # 获取MA数据
        h = attribute_history(stock, 20, '1d', ['close', 'high'])
        if len(h) < 5:
            continue

        ma5_est = _estimate_intraday_ma5(stock, curr_price, context)
        if ma5_est is None:
            base_sum = float(h['close'].iloc[-4:].sum())
            g.ma5_base_cache[stock] = base_sum
            ma5_est = (base_sum + curr_price) / 5.0

        # 构建卖出信号上下文
        sell_ctx = {
            'stock': stock, 'curr_price': curr_price, 'avg_cost': avg_cost,
            'pnl': pnl, 'stage': meta.get('stage', 'full'),
            'entry_type': meta.get('entry_type', ''),
            'meta': meta,
            'prev_close': h['close'].iloc[-1],
            'ma5_est': ma5_est,
            'ma10_est': (h['close'].iloc[-9:].sum() + curr_price) / 10.0 if len(h) >= 10 else None,
            'ma20_est': (h['close'].iloc[-19:].sum() + curr_price) / 20.0 if len(h) >= 20 else None,
            'high_since_entry': max(h['high'].iloc[-5:].max(), curr_price),
            'current_dt': context.current_dt,
            'high_limit': current_data[stock].high_limit if stock in current_data else 0,
        }

        signal = sell_rules(sell_ctx, strat['config'])
        if signal is None:
            continue

        execute_sell_signal(stock, signal, meta, context, pnl)


def execute_sell_signal(stock, signal, meta, context, pnl):
    """执行卖出信号（通用）"""
    action = signal['action']
    reason = signal['reason']

    if action == 'sell_all':
        if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl):
            diag_add('{}_sell_all'.format(meta.get('strategy', '?')))
            if meta.get('entry_type') == 'dragon_follow':
                diag_add('dragon_sell_orders')
                _hold_days_dragon = (context.current_dt.date() - meta['buy_date']).days \
                    if meta.get('buy_date') else '?'
                log.info(
                    "DRAGON_SELL|stock={}|name={}|reason={}|pnl={:.2f}%|stage={}|"
                    "curr_price={}|ma5={}|hold_days={}|"
                    "warning_stop={}|delayed_stop={}|"
                    "confirm_stop={}".format(
                        stock, get_stock_name_cached(stock), reason,
                        pnl * 100, meta.get('stage', 'full'),
                        signal.get('curr_price', 'NA'), signal.get('ma5', 'NA'),
                        _hold_days_dragon,
                        int(meta.get('dragon_stop_warning', False)),
                        int(reason == 'dragon_delayed_stop'),
                        int(reason == 'dragon_confirm_stop')
                    )
                )
            else:
                log.info(
                    "SELL_SUBMIT|stock={}|name={}|action=sell_all|reason={}|pnl={:.2f}%".format(
                        stock, get_stock_name_cached(stock), reason, pnl * 100
                    )
                )

    elif action == 'sell_half':
        pos = context.portfolio.positions[stock]
        closeable = pos.closeable_amount
        half_amount = closeable // 2
        # 聚宽规则: 可平仓数量≤100时必须一次性平仓，不能拆分
        # 如果卖出一半后剩余<100股，或者可平仓本身≤100，直接全卖
        remaining_after_half = closeable - half_amount
        if closeable <= 100 or remaining_after_half < 100:
            # 降级为sell_all
            if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl):
                diag_add('{}_sell_all'.format(meta.get('strategy', '?')))
                if meta.get('entry_type') == 'dragon_follow':
                    diag_add('dragon_sell_orders')
                    _hold_days_dragon = (context.current_dt.date() - meta['buy_date']).days \
                        if meta.get('buy_date') else '?'
                    log.info(
                        "DRAGON_SELL|stock={}|name={}|reason={}|pnl={:.2f}%|stage={}|"
                        "curr_price={}|ma5={}|hold_days={}|warning_stop={}|delayed_stop=0|"
                        "confirm_stop=0|half_degraded_to_full=1".format(
                            stock, get_stock_name_cached(stock), reason,
                            pnl * 100, meta.get('stage', 'full'),
                            signal.get('curr_price', 'NA'), signal.get('ma5', 'NA'),
                            _hold_days_dragon,
                            int(meta.get('dragon_stop_warning', False))
                        )
                    )
                else:
                    log.info(
                        "SELL_SUBMIT|stock={}|name={}|action=sell_all|reason={}|"
                        "pnl={:.2f}%|adjust=half_to_full".format(
                            stock, get_stock_name_cached(stock), reason, pnl * 100
                        )
                    )
        else:
            next_stage = signal.get('next_stage', 'half')
            if half_amount > 0:
                if submit_partial_stage_change(
                        stock, half_amount, next_stage, context,
                        reason=reason, ret_snapshot=pnl):
                    diag_add('{}_sell_partial'.format(meta.get('strategy', '?')))
                    diag_add('{}_sell_half'.format(meta.get('strategy', '?')))
                    if meta.get('entry_type') == 'dragon_follow':
                        diag_add('dragon_sell_orders')
                        _hold_days_dragon = (context.current_dt.date() - meta['buy_date']).days \
                            if meta.get('buy_date') else '?'
                        log.info(
                            "DRAGON_SELL|stock={}|name={}|reason={}|pnl={:.2f}%|stage={}|"
                            "curr_price={}|ma5={}|hold_days={}|warning_stop={}|delayed_stop=0|"
                            "confirm_stop=0".format(
                                stock, get_stock_name_cached(stock), reason,
                                pnl * 100, meta.get('stage', 'full'),
                                signal.get('curr_price', 'NA'), signal.get('ma5', 'NA'),
                                _hold_days_dragon,
                                int(meta.get('dragon_stop_warning', False))
                            )
                        )
                    else:
                        log.info(
                            "SELL_SUBMIT|stock={}|name={}|action=sell_half|"
                            "reason={}|pnl={:.2f}%".format(
                                stock, get_stock_name_cached(stock), reason, pnl * 100
                            )
                        )


# ---------- 通用买入引擎 ----------

def strategy_trade(context, strategy_name):
    """通用交易入口：先卖后买"""
    strategy_sell_only(context, strategy_name)
    strategy_buy_only(context, strategy_name)


def strategy_buy_only(context, strategy_name):
    """通用买入流程"""
    strat = g.strategies[strategy_name]
    handlers = strat['handlers']
    config = strat['config']

    # 获取当前模式和预算调整
    mode, mode_overrides = handlers['get_mode'](context)
    budget = compute_buy_budget(strategy_name, mode, mode_overrides, context)

    if budget is None:
        return

    # 全局检查
    if g.daily_new_position_count >= g.cfg['max_daily_new_positions']:
        return
    if check_intraday_open_risk(context):
        return

    # 槽位检查
    current_hold = get_open_slot_hold_count(context, strategy_name)
    strategy_slots = budget['max_hold'] - current_hold
    global_slots = get_global_slots_left(context)
    slots_left = min(strategy_slots, global_slots)
    if slots_left <= 0:
        return

    # 选股
    candidates = handlers['select'](context, config, mode)
    if not candidates:
        return

    # 打分
    scored = handlers['score'](context, candidates, mode=mode, pos_ratio=budget['pos_ratio'])
    if not scored:
        return

    # 策略特有的打分后过滤（如B的min_score门槛）
    post_filter = handlers.get('post_score_filter')
    if post_filter:
        scored = post_filter(scored, context)
        if not scored:
            return

    # 下单
    execute_buy_orders(context, scored, strategy_name, budget, slots_left)


def _observer_float(value, default=np.nan):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def log_entry_feature_observer(context, stock, name, entry_type,
                               price=None, item=None, snapshot=None):
    """Research-only entry feature logging. It does not affect trading."""
    item = item or {}
    snapshot = snapshot or {}
    entry_price = _observer_float(price, _observer_float(snapshot.get('current_price'), 0.0))
    ma5 = _observer_float(snapshot.get('ma5'), np.nan)
    if (ma5 is None or np.isnan(ma5) or ma5 <= 0) and entry_price > 0:
        ma5 = _observer_float(_estimate_intraday_ma5(stock, entry_price, context), np.nan)
    ma10 = np.nan
    try:
        dh = attribute_history(stock, 10, '1d', ['close'], skip_paused=False)
        if dh is not None and len(dh) > 0:
            ma10 = float(dh['close'].tail(10).mean())
    except Exception:
        ma10 = np.nan
    ma5_distance = (
        entry_price / ma5 - 1.0
        if entry_price > 0 and ma5 is not None and not np.isnan(ma5) and ma5 > 0
        else _observer_float(snapshot.get('ma5_distance'), np.nan)
    )
    ma10_distance = (
        entry_price / ma10 - 1.0
        if entry_price > 0 and ma10 is not None and not np.isnan(ma10) and ma10 > 0
        else np.nan
    )
    log.info(
        "ENTRY_FEATURE_LOG|stock={}|name={}|date={}|entry_type={}|"
        "entry_open_ratio={:.4f}|entry_day_ret={:.4f}|"
        "entry_close_to_high={:.4f}|entry_volume_ratio={:.4f}|"
        "entry_auc_ratio={:.4f}|entry_ma5_distance={:.4f}|"
        "entry_ma10_distance={:.4f}|breadth_up_ratio={:.4f}|"
        "entry_score={:.4f}|log_stage=order_submitted|filled_confirmed=0".format(
            stock, name, context.current_dt.date(), entry_type,
            _observer_float(item.get('open_ratio'), np.nan),
            _observer_float(snapshot.get('day_ret', item.get('day_ret')), np.nan),
            _observer_float(snapshot.get('close_to_day_high'), np.nan),
            _observer_float(snapshot.get('volume_ratio_vs_prev'), np.nan),
            _observer_float(item.get('auction_ratio', item.get('auc_ratio')), np.nan),
            _observer_float(ma5_distance, np.nan),
            _observer_float(ma10_distance, np.nan),
            _observer_float(g.diag.get('breadth_up_ratio', np.nan), np.nan),
            _observer_float(
                snapshot.get('signal_score', item.get('dragon_score', item.get('score'))),
                np.nan
            )
        )
    )


def execute_buy_orders(context, scored, strategy_name, budget, slots_left):
    """BigMeat固定仓位下单：最多2只，初始总仓不超过60%。"""
    cfg_a = g.strategies['A']['config']
    total_value = context.portfolio.total_value
    if total_value is None or total_value <= 0:
        return

    planned_position_value = sum(
        float(getattr(pos, 'value', 0) or 0)
        for pos in context.portfolio.positions.values()
    )
    planned_cash = float(context.portfolio.available_cash)
    initial_cap = cfg_a.get('max_initial_position_ratio', 0.60)
    total_cap = cfg_a.get('max_total_position_ratio', 0.75)
    single_cap = cfg_a.get('max_single_stock_ratio', 0.50)
    planned_dragon_count = sum(
        1 for stock in context.portfolio.positions
        if g.positions_meta.get(stock, {}).get('strategy') == 'A'
        and g.positions_meta.get(stock, {}).get('entry_type') == 'dragon_follow'
    )

    for item in scored[:2]:
        if slots_left <= 0 or g.daily_new_position_count >= g.cfg['max_daily_new_positions']:
            break

        stock = item['stock']
        curr_price = item['curr_price']
        if item.get('entry_type') != 'dragon_follow' or item.get('tpl') != 'deep_water':
            continue
        if stock in context.portfolio.positions or stock in g.pending_buys \
                or in_cooldown(stock, context) or not can_open_position(context, curr_price):
            continue

        current_position_ratio = planned_position_value / total_value
        remaining_initial = max(initial_cap - current_position_ratio, 0.0)
        if remaining_initial < 0.15 - 1e-8:
            log.info(
                "BIGMEAT_BUY_SKIP|stock={}|name={}|reason=initial_position_cap|"
                "current_position_ratio={:.2f}%|remaining_initial={:.2f}%".format(
                    stock, get_stock_name_cached(stock),
                    current_position_ratio * 100, remaining_initial * 100
                )
            )
            continue

        candidate_default_pos_ratio = float(item.get('pos_ratio', budget['pos_ratio']))
        if planned_dragon_count >= 1:
            candidate_default_pos_ratio = min(
                candidate_default_pos_ratio, cfg_a.get('top2_pos_ratio', 0.25)
            )
        remaining_total = max(total_cap - current_position_ratio, 0.0)
        remaining_cash_ratio = max(planned_cash / total_value, 0.0)
        pos_ratio = min(
            candidate_default_pos_ratio,
            remaining_initial,
            remaining_total,
            remaining_cash_ratio,
            single_cap,
        )
        if pos_ratio < 0.15 - 1e-8:
            log.info(
                "BIGMEAT_BUY_SKIP|stock={}|name={}|reason=total_position_cap".format(
                    stock, get_stock_name_cached(stock)
                )
            )
            continue

        target_value = total_value * pos_ratio
        cap_limit = total_cap
        current_total_ratio = planned_position_value / total_value
        available_cap_value = max(cap_limit - current_total_ratio, 0.0) * total_value
        buy_value = min(target_value, available_cap_value, planned_cash)
        trim_reason = 'none'
        if buy_value < target_value - 1e-6:
            trim_reason = 'cap_fixed_trim'
            log.info(
                "CAP_FIXED_TRIM|date={}|stock={}|name={}|target_value={:.2f}|"
                "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
                "post_total_ratio={:.2f}%|trim_reason={}".format(
                    context.current_dt.date(), stock, get_stock_name_cached(stock),
                    target_value, buy_value, cap_limit * 100,
                    current_total_ratio * 100,
                    (planned_position_value + buy_value) / total_value * 100,
                    trim_reason
                )
            )

        lot_amount = int(buy_value / curr_price / 100) * 100 if curr_price > 0 else 0
        actual_value = lot_amount * curr_price
        if buy_value <= 0 or lot_amount < 100:
            log.info(
                "CAP_FIXED_SKIP_NO_CAPACITY|date={}|stock={}|name={}|target_value={:.2f}|"
                "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
                "post_total_ratio={:.2f}%|trim_reason={}".format(
                    context.current_dt.date(), stock, get_stock_name_cached(stock),
                    target_value, actual_value, cap_limit * 100,
                    current_total_ratio * 100, current_total_ratio * 100,
                    'no_capacity_or_lot'
                )
            )
            continue
        buy_value = actual_value
        pos_ratio = buy_value / total_value

        if buy_value > planned_cash or buy_value / curr_price < 100:
            log.info(
                "BIGMEAT_BUY_SKIP|stock={}|name={}|reason=insufficient_cash_or_lot".format(
                    stock, get_stock_name_cached(stock)
                )
            )
            continue

        if order_value(stock, buy_value) is not None:
            order_item = dict(item)
            order_item['pos_ratio'] = pos_ratio
            order_item['entry_value'] = buy_value
            mark_pending_buy(
                stock, strategy_name, item['entry_type'], 'full', context, item=order_item
            )
            g.daily_new_position_count += 1
            slots_left -= 1
            planned_position_value += buy_value
            planned_cash -= buy_value
            planned_dragon_count += 1
            diag_add('{}_buys_orders'.format(strategy_name))
            diag_add('dragon_buy_orders')
            log_entry_feature_observer(
                context, stock, get_stock_name_cached(stock),
                item.get('entry_type', 'dragon_follow'),
                price=curr_price, item=item
            )
            log.info(
                "CAP_FIXED_BUY_OK|date={}|stock={}|name={}|target_value={:.2f}|"
                "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
                "post_total_ratio={:.2f}%|trim_reason={}".format(
                    context.current_dt.date(), stock, get_stock_name_cached(stock),
                    target_value, buy_value, cap_limit * 100,
                    current_total_ratio * 100,
                    planned_position_value / total_value * 100,
                    trim_reason
                )
            )
            log.info(
                "BIGMEAT_BUY|stock={}|name={}|dragon_score={:.4f}|open_ratio={:.2f}%|"
                "tpl={}|rank={}|current_position_ratio={:.2f}%|"
                "remaining_initial={:.2f}%|actual_pos_ratio={:.2f}%|"
                "market_trend={}|micro_regime={}|"
                "stage=initial_buy|order_value={:.2f}|"
                "reason=dragon_bigmeat_buy".format(
                    stock, get_stock_name_cached(stock),
                    item.get('dragon_score', item.get('score', 0.0)),
                    item.get('open_ratio', 0.0) * 100, item.get('tpl', ''),
                    item.get('rank', 0), current_position_ratio * 100,
                    remaining_initial * 100, pos_ratio * 100,
                    getattr(g, 'market_trend', 'sideways'),
                    getattr(g, 'micro_regime', 'unknown'),
                    buy_value
                )
            )


def compute_buy_budget(strategy_name, mode, mode_overrides, context):
    """计算买入预算（包含模式覆盖）"""
    strat = g.strategies[strategy_name]
    budget = dict(strat['budget'])

    # 应用刷新后的strategy_budget
    if strategy_name in g.strategy_budget:
        sb = g.strategy_budget[strategy_name]
        budget['max_hold'] = sb.get('max_hold', budget['max_hold'])
        budget['pos_ratio'] = sb.get('pos_ratio', budget['pos_ratio'])

    # 应用模式覆盖
    for k, v in mode_overrides.items():
        budget[k] = v

    if budget['max_hold'] <= 0:
        return None
    return budget


# =============================================================================
# 第五层: 策略实现 (Strategy Plugins)
# =============================================================================

# ================== 策略A: 早盘先手/Dragon ==================

def _evaluate_ebb_cash_gate(context):
    """[V1.5.0 改动1] 退潮/冰点空仓闸。返回 (is_ebb, reason)。
    触发条件(任一即空仓,只挡新开仓):
      A. 冰点: 大盘近3日累计跌幅 <= ebb_ice_crash_3d(接飞刀最危险)
      B. 退潮弱市: regime==bear 且 当日龙头竞价最高分 < ebb_bear_top_score_floor
      C. 情绪退潮: dragon_score_ema 衰减到峰值*ebb_ema_peak_decay 以下 且 regime!=bull
    只用策略已有信号(regime/龙头分/EMA),不需全市场涨跌停数据,适配聚宽回测。
    """
    cfg = g.cfg
    if not cfg.get('ebb_cash_gate_enable', True):
        return False, ''

    # A. 冰点: 大盘3日急跌
    try:
        crash_th = cfg.get('ebb_ice_crash_3d', -0.05)
        h = attribute_history(cfg['regime_index'], 4, '1d', ['close'], skip_paused=True)
        if h is not None and len(h) >= 4:
            ret3 = float(h['close'].iloc[-1]) / float(h['close'].iloc[-4]) - 1
            if ret3 <= crash_th:
                return True, 'ice_crash_3d({:.1f}%)'.format(ret3 * 100)
    except Exception as e:
        log.warning("EBB_GATE_ICE_ERROR|error={}".format(e))

    # B. 退潮弱市: bear + 龙头竞价分弱(无强势龙头的下跌市)
    top_score = float(getattr(g, 'dragon_top_score', 0.0) or 0.0)
    if g.market_regime == 'bear' and top_score < cfg.get('ebb_bear_top_score_floor', 0.72):
        return True, 'ebb_bear_weak_leader(top={:.3f})'.format(top_score)

    # C. 情绪退潮: EMA 从峰值大幅衰减 且 非牛市
    peak = float(getattr(g, 'crowding_peak_score', 0.0) or 0.0)
    ema = float(getattr(g, 'dragon_score_ema', 0.0) or 0.0)
    if peak > 0 and g.market_regime != 'bull':
        if ema < peak * cfg.get('ebb_ema_peak_decay', 0.55):
            return True, 'ebb_ema_decay(ema={:.3f}/peak={:.3f})'.format(ema, peak)

    return False, ''


def get_A_mode(context):
    """BigMeat只保留Dragon/idle两种开仓状态。"""
    cfg_a = g.strategies['A']['config']
    if g.dragon_circuit_breaker_pause_left > 0:
        g.diag['dragon_circuit_breaker_active'] = 1
        pause_log_key = (
            context.current_dt.date(),
            g.dragon_consecutive_losses,
            g.dragon_circuit_breaker_pause_left,
        )
        if pause_log_key != g.dragon_pause_last_log_key:
            log.info(
                "DRAGON_PAUSE|stock=ALL|name=ALL|dragon_consecutive_losses={}|"
                "dragon_pause_days_left={}|pause_active=1".format(
                    g.dragon_consecutive_losses,
                    g.dragon_circuit_breaker_pause_left
                )
            )
            g.dragon_pause_last_log_key = pause_log_key
        return 'paused', {'max_hold': 0}

    if g.dragon_pool_size <= 0:
        return 'idle', {'max_hold': 0}

    # [V1.5.0 改动1] 退潮/冰点空仓闸: 触发则不新开仓(持仓仍按各自止损管理)
    ebb, ebb_reason = _evaluate_ebb_cash_gate(context)
    if ebb:
        g.diag['ebb_cash_gate'] = 1
        log.info(
            "EBB_CASH_GATE|active=1|reason={}|regime={}|top_score={:.3f}|"
            "ema={:.3f}|peak={:.3f}".format(
                ebb_reason, g.market_regime,
                float(getattr(g, 'dragon_top_score', 0.0) or 0.0),
                float(getattr(g, 'dragon_score_ema', 0.0) or 0.0),
                float(getattr(g, 'crowding_peak_score', 0.0) or 0.0)
            )
        )
        return 'idle', {'max_hold': 0}
    g.diag['ebb_cash_gate'] = 0

    g.diag['A_dragon_mode'] = 1
    return 'dragon', {
        'max_hold': min(2, cfg_a['max_hold'], cfg_a['dragon_max_hold']),
        'pos_ratio': cfg_a['pos_ratio'],
    }


def select_candidates_A(context, config, mode):
    """BigMeat实盘候选只来自Dragon池，普通入口保留但不接入。"""
    if mode != 'dragon':
        return []
    return [
        item for item in list(g.dragon_candidates_today or [])
        if item.get('entry_type') == 'dragon_follow'
    ]


def evaluate_sell_signal_A(sell_ctx, config):
    """BigMeat 卖出规则：Dragon 核心逻辑加最小历史持仓兼容。"""
    pnl = sell_ctx['pnl']
    curr_p = sell_ctx['curr_price']
    stage = sell_ctx['stage']
    if stage == 'half_final':
        stage = 'half'
    entry_type = sell_ctx['entry_type']
    ma5 = sell_ctx['ma5_est']
    prev_close = sell_ctx['prev_close']

    if entry_type != 'dragon_follow':
        if pnl <= -config.get('abs_stop_loss', 0.05):
            return {'action': 'sell_all', 'reason': 'legacy_hard_stop'}
        return None

    if stage == 'pending':
        return None

    meta = sell_ctx.get('meta', {})
    reason = _evaluate_dragon_intraday_stop(
        sell_ctx['stock'], meta, pnl, curr_p, ma5,
        sell_ctx.get('current_dt'), 'scheduled_sell'
    )
    if reason:
        return {
            'action': 'sell_all', 'reason': reason,
            'curr_price': curr_p, 'ma5': ma5,
        }

    if stage == 'full':
        profit_protect = config.get('dragon_profit_protect', 0.10)
        if pnl >= profit_protect and curr_p < ma5:
            return {
                'action': 'sell_half', 'reason': 'dragon_profit_protect',
                'next_stage': 'half', 'curr_price': curr_p, 'ma5': ma5,
            }

    if stage == 'half':
        protect_line = max(prev_close, ma5)
        if curr_p < protect_line:
            return {
                'action': 'sell_all', 'reason': 'dragon_half_protect',
                'curr_price': curr_p, 'ma5': ma5,
            }

    return None


def get_market_trend(context):
    """判断大盘趋势方向
    返回: 'up'(上涨趋势), 'down'(下跌趋势), 'sideways'(震荡)

    判断标准(日线级别):
    - MA5 > MA10 > MA20 且价格在MA5之上 → up
    - MA5 < MA10 < MA20 且价格在MA5之下 → down
    - 其他 → sideways
    """
    cfg = g.cfg
    idx = cfg['regime_index']
    lookback = cfg.get('trend_market_lookback', 25)
    ma_f = cfg.get('trend_market_ma_fast', 5)
    ma_m = cfg.get('trend_market_ma_mid', 10)
    ma_s = cfg.get('trend_market_ma_slow', 20)

    try:
        h = attribute_history(idx, lookback, '1d', ['close'], skip_paused=True)
        if len(h) < ma_s + 1:
            return 'sideways'
        closes = h['close']
        current = closes.iloc[-1]
        avg_fast = float(closes.iloc[-ma_f:].mean())
        avg_mid = float(closes.iloc[-ma_m:].mean())
        avg_slow = float(closes.iloc[-ma_s:].mean())

        if avg_fast > avg_mid > avg_slow and current >= avg_fast:
            return 'up'
        elif avg_fast < avg_mid < avg_slow and current <= avg_fast:
            return 'down'
        else:
            return 'sideways'
    except Exception as e:
        log.warning("MARKET_TREND_ERROR|fallback=sideways|error={}".format(e))
        return 'sideways'


def is_stock_uptrend(stock, context):
    """判断个股是否处于上升趋势

    三个条件全部满足才算上升趋势:
    1. 均线多头排列: MA5 > MA10 > MA20
    2. 收盘价站在MA20之上
    3. 近期低点在抬升(近10日最低 >= 前10日最低 × (1-容忍度))

    对于龙头股(已涨停)用涨停前一日的数据判断
    """
    cfg = g.cfg
    lookback = cfg.get('trend_stock_lookback', 30)
    ma_f = cfg.get('trend_stock_ma_fast', 5)
    ma_m = cfg.get('trend_stock_ma_mid', 10)
    ma_s = cfg.get('trend_stock_ma_slow', 20)
    tol = cfg.get('trend_higher_low_tolerance', 0.02)

    try:
        h = attribute_history(stock, lookback, '1d', ['close', 'low'], skip_paused=True)
        if len(h) < ma_s + 1:
            return False

        closes = h['close']
        lows = h['low']

        # 用倒数第二天(涨停前一天)的数据,避免涨停当天distortion
        ref_close = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]

        # 条件1: 均线多头排列
        avg_fast = float(closes.iloc[-ma_f - 1:-1].mean())
        avg_mid = float(closes.iloc[-ma_m - 1:-1].mean())
        avg_slow = float(closes.iloc[-ma_s - 1:-1].mean())
        ma_aligned = avg_fast > avg_mid > avg_slow

        # 条件2: 价格在MA20之上
        price_above = ref_close > avg_slow

        # 条件3: 低点抬升 - 近10日低点 >= 前10日低点 × (1-tol)
        if len(lows) >= 20:
            recent_low = float(lows.iloc[-10:].min())
            prev_low = float(lows.iloc[-20:-10].min())
            higher_lows = recent_low >= prev_low * (1 - tol)
        else:
            higher_lows = True  # 数据不足时不做此项过滤

        return ma_aligned and price_above and higher_lows
    except Exception as e:
        log.warning(
            "STOCK_TREND_ERROR|stock={}|name={}|error={}".format(
                stock, get_stock_name_cached(stock), e
            )
        )
        return False


def get_single_index_regime(context, index_code):
    """对单个指数进行 bull/bear/neutral 判定"""
    cfg = g.cfg
    h = attribute_history(index_code, cfg['regime_lookback'], '1d', ['close'])
    if len(h) < cfg['regime_lookback']:
        return 'neutral'
    close_s = h['close']
    ma_fast = close_s.iloc[-cfg['regime_bull_ma_fast']:].mean()
    ma_mid = close_s.iloc[-cfg['regime_bull_ma_mid']:].mean()
    ma_slow = close_s.iloc[-cfg['regime_bull_ma_slow']:].mean()
    curr_close = close_s.iloc[-1]
    if len(close_s) >= 4:
        ret_3d = close_s.iloc[-1] / close_s.iloc[-4] - 1
        if ret_3d <= cfg.get('regime_crash_3d_threshold', -0.05):
            return 'bear'
    if curr_close >= ma_slow and ma_fast >= ma_mid:
        return 'bull'
    elif curr_close < ma_slow and ma_fast < ma_mid:
        return 'bear'
    return 'neutral'


def update_market_regime(context):
    """更新市场Regime（含双指数修正）"""
    cfg = g.cfg
    raw = get_single_index_regime(context, cfg['regime_index'])
    cd = cfg['regime_confirm_days']

    if raw == 'neutral':
        g.market_regime = 'neutral'
        g.pending_regime = None
        g.pending_regime_days = 0
    elif raw == g.market_regime:
        g.pending_regime = None
        g.pending_regime_days = 0
    else:
        if raw == g.pending_regime:
            g.pending_regime_days += 1
        else:
            g.pending_regime = raw
            g.pending_regime_days = 1
        if g.pending_regime_days >= cd:
            g.market_regime = g.pending_regime
            g.pending_regime = None
            g.pending_regime_days = 0

    # 双指数修正
    g.regime_dual_override_active = False
    g.regime_secondary_raw = 'neutral'
    if cfg.get('regime_dual_enable', False):
        g.regime_secondary_raw = get_single_index_regime(
            context, cfg.get('regime_secondary_index', '000300.XSHG'))
        if (cfg.get('regime_dual_override_bear_to_neutral', True)
                and g.market_regime == 'bear'
                and g.regime_secondary_raw in ('bull', 'neutral')):
            g.market_regime = 'neutral'
            g.regime_dual_override_active = True
            log.info(
                "REGIME_OVERRIDE|primary=bear|secondary={}|result=neutral".format(
                    g.regime_secondary_raw
                )
            )
        if (cfg.get('regime_dual_upgrade_neutral_to_bull', False)
                and g.market_regime == 'neutral'
                and g.regime_secondary_raw == 'bull'):
            g.market_regime = 'bull'
            g.regime_dual_override_active = True

    g.diag['regime_secondary'] = g.regime_secondary_raw
    g.diag['regime_dual_override'] = 1 if g.regime_dual_override_active else 0


# ---------- 以下为框架支撑函数，从v5.9.0直接迁移 ----------
# (为节省篇幅，这些函数保持v5.9.0原有实现，仅做命名规范化)
# 完整实现见 strategy_v6.0.0_full.py

def refresh_strategy_budget():
    """BigMeat预算固定为2核心，不再按环境切换。"""
    cfg_a = g.strategies['A']['config']
    g.strategy_budget['A'] = {
        'max_hold': min(2, cfg_a['max_hold']),
        'pos_ratio': cfg_a['pos_ratio'],
    }


# =============================================================================
# 第六层-续: 从v5.9.0迁移的完整实现
# =============================================================================


def update_micro_regime_without_dragon(context):
    if g.market_regime == 'bull':
        g.micro_regime = 'bull'
    elif g.market_regime == 'bear':
        g.micro_regime = 'bear'
    else:
        g.micro_regime = 'neutral_trend'


# =========================================================
# [P0-FIX-1] 带衰减退出 + 最大持续天数的 micro_regime 更新
# =========================================================


def update_micro_regime(context):
    cfg = g.cfg
    scores = [x.get('dragon_score', 0.0) for x in g.dragon_candidates_today[:3]] \
        if g.dragon_candidates_today else []
    top1 = scores[0] if scores else g.dragon_top_score
    top2_avg = float(np.mean(scores[:2])) if len(scores) >= 2 else top1

    # 更新 EMA
    alpha = cfg.get('dragon_score_ema_alpha', 0.3)
    if g.dragon_score_ema <= 0:
        g.dragon_score_ema = top1
    else:
        g.dragon_score_ema = alpha * top1 + (1 - alpha) * g.dragon_score_ema

    crowding_signal_raw = (
        g.dragon_pool_size >= cfg.get('crowding_exit_pool_min', 3) and (
            top1 >= cfg['dragon_top_score_trigger']
            or (len(scores) >= 2 and top2_avg >= cfg['dragon_cluster_top2_avg'])
        )
    )

    # [P0-FIX-1] 冷却期内强制禁止 crowding
    if g.crowding_cooldown_left > 0:
        crowding_signal_raw = False

    # [P0-FIX-1] pool_size 不足时强制退出
    if g.dragon_pool_size < cfg.get('crowding_exit_pool_min', 3):
        crowding_signal_raw = False

    # [P0-FIX-1] top_score EMA 衰减到峰值的 60% 以下时退出
    if g.crowding_peak_score > 0:
        decay_ratio = cfg.get('crowding_exit_score_decay_ratio', 0.60)
        if g.dragon_score_ema < g.crowding_peak_score * decay_ratio:
            crowding_signal_raw = False
            log.info(
                "CROWDING_EXIT|reason=score_decay|ema={:.3f}|peak={:.3f}|"
                "decay_ratio={:.0f}%".format(
                    g.dragon_score_ema, g.crowding_peak_score,
                    decay_ratio * 100
                )
            )

    # 连续确认计数
    confirm_days = cfg.get('dragon_crowding_confirm_days', 2)
    if crowding_signal_raw:
        g.crowding_confirm_days = min(g.crowding_confirm_days + 1, confirm_days + 2)
    else:
        g.crowding_confirm_days = 0

    crowding_confirmed = (g.crowding_confirm_days >= confirm_days)

    # [P0-FIX-1] 最大持续天数限制
    max_consec = cfg.get('crowding_max_consecutive_days', 10)
    if crowding_confirmed:
        g.crowding_consecutive_days += 1
        # 更新峰值
        if g.dragon_score_ema > g.crowding_peak_score:
            g.crowding_peak_score = g.dragon_score_ema
        # 超过最大天数，强制退出并进入冷却
        if g.crowding_consecutive_days > max_consec:
            crowding_confirmed = False
            g.crowding_confirm_days = 0
            g.crowding_cooldown_left = cfg.get('crowding_cooldown_days', 3)
            log.info(
                "CROWDING_EXIT|reason=timeout|consecutive_days={}|"
                "cooldown_days={}".format(
                    g.crowding_consecutive_days, g.crowding_cooldown_left
                )
            )
            g.crowding_consecutive_days = 0
            g.crowding_peak_score = 0.0
    else:
        # 非 crowding 时重置
        if g.crowding_consecutive_days > 0:
            g.crowding_consecutive_days = 0
            g.crowding_peak_score = 0.0

    # 记录上一个 micro_regime
    g.prev_micro_regime = g.micro_regime

    if g.market_regime == 'bull':
        if crowding_confirmed:
            new_micro = 'neutral_crowding'         # bull+crowding 仍可触发
        else:
            new_micro = 'bull'
    elif crowding_confirmed and (g.market_regime in ('neutral', 'bear')):
        new_micro = 'neutral_crowding'
    elif g.market_regime == 'bear':
        new_micro = 'bear'
    else:
        new_micro = 'neutral_trend'

    # crowding 退出日志
    if g.micro_regime == 'neutral_crowding' and new_micro != 'neutral_crowding':
        log.info("CROWDING_EXIT|reason=regime_change|result={}".format(new_micro))

    g.micro_regime = new_micro
    g.diag['crowding_confirm_days'] = g.crowding_confirm_days
    g.diag['crowding_signal_raw'] = 1 if crowding_signal_raw else 0
    g.diag['crowding_consecutive_days'] = g.crowding_consecutive_days
    g.diag['crowding_cooldown_left'] = g.crowding_cooldown_left
    g.diag['dragon_score_ema'] = round(g.dragon_score_ema, 4)


# =========================================================
# 盘中止损
# =========================================================


# [Claude Opt: 批量预取持仓tick + 顶层防崩溃]
def gap_down_stop_loss(context):
    """缺口止损(阶段1) — 标记预警, 不立即卖出, 等待09:35确认
    [v9.0.25-fix] 延迟止损 + 恢复等待: 解决"止损后又涨回来"的问题
    流程: 09:31标记 → 09:35确认 → 未恢复才执行卖出
    """
    try:
        current_data = get_current_data()
        today = context.current_dt.date()
        stocks = list(context.portfolio.positions.keys())
        if not stocks:
            return
        if hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(stocks)
            except Exception:
                pass
    except Exception as e:
        log.error("GAP_STOP_ERROR|stage=initialize_warning|error={}".format(e))
        return

    # 初始化当日缺口预警列表
    if not hasattr(g, 'gap_down_alerts'):
        g.gap_down_alerts = {}

    for stock in stocks:
        try:
            meta = g.positions_meta.get(stock)
            if not meta or meta.get('pending_exit', False) or meta.get('last_exit_date') == today:
                continue

            pos = context.portfolio.positions[stock]
            if pos.closeable_amount <= 0:
                continue

            cd_item = current_data[stock]
            open_price = cd_item.day_open
            if open_price is None or open_price <= 0:
                continue

            pnl = open_price / pos.avg_cost - 1
            strategy = meta.get('strategy', 'A')
            entry_type = meta.get('entry_type', '')
            if entry_type == 'dragon_follow':
                stop_level = g.strategies['A']['config'].get('dragon_warn_stop', 0.035)
            else:
                stop_level = _get_stop_level(strategy, entry_type)

            if pnl <= -stop_level:
                # [V1.5.0 改动2] 灾难性跳空: 开盘跌幅过大直接立即止损, 不进09:35延迟确认队列。
                # 延迟确认只适合小跳空(有恢复可能); 大跳空傻等会把 -3.5% 拖成 -12%。
                catastrophic_gap = g.strategies['A']['config'].get(
                    'dragon_catastrophic_gap', 0.06)
                if pnl <= -catastrophic_gap:
                    if submit_exit_order(stock, context,
                                         reason='catastrophic_gap_stop', ret_snapshot=pnl):
                        diag_add('{}_sell_all'.format(strategy))
                        if entry_type == 'dragon_follow':
                            diag_add('dragon_sell_orders')
                        log.info(
                            "GAP_STOP|stock={}|name={}|reason=catastrophic_gap_stop|"
                            "strategy={}|entry={}|open_pnl={:.2f}%|action=immediate_exit".format(
                                stock, get_stock_name_cached(stock),
                                strategy, entry_type, pnl * 100
                            )
                        )
                    continue
                # 标记预警, 记录开盘亏损幅度, 等待confirm确认
                if entry_type == 'dragon_follow':
                    _set_dragon_stop_warning(stock, meta, pnl, 'gap_warning')
                g.gap_down_alerts[stock] = {
                    'strategy': strategy,
                    'entry_type': entry_type,
                    'open_pnl': pnl,
                    'stop_level': stop_level,
                    'avg_cost': pos.avg_cost,
                }
                log.info(
                    "GAP_STOP|stock={}|name={}|reason=gap_warning|strategy={}|entry={}|"
                    "open_pnl={:.2f}%|dragon_stop_warning={}".format(
                        stock, get_stock_name_cached(stock),
                        strategy, entry_type, pnl * 100,
                        int(entry_type == 'dragon_follow')
                    )
                )
        except Exception as e:
            log.error(
                "GAP_STOP_ERROR|stock={}|name={}|stage=warning|error={}".format(
                    stock, get_stock_name_cached(stock), e
                )
            )


def gap_down_confirm(context):
    """缺口止损(阶段2) — 09:35确认: 价格未恢复则执行, 已恢复则取消
    [v9.0.25-fix] recovery_ratio: 恢复到 avg_cost×(1 - recovery_ratio) 以上则取消止损
    """
    if not hasattr(g, 'gap_down_alerts') or not g.gap_down_alerts:
        return

    try:
        current_data = get_current_data()
        stocks = list(g.gap_down_alerts.keys())
        if hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(stocks)
            except Exception:
                pass
    except Exception as e:
        log.error("GAP_STOP_ERROR|stage=initialize_confirm|error={}".format(e))
        return

    cfg = g.cfg
    # 恢复阈值: 当前价 > avg_cost × (1 - recovery_ratio) 则视为恢复
    recovery_ratio = cfg.get('gap_down_recovery_ratio', 0.02)

    confirmed = []
    cancelled = []

    for stock in list(g.gap_down_alerts.keys()):
        alert = g.gap_down_alerts[stock]
        try:
            if stock not in context.portfolio.positions:
                cancelled.append(stock)
                continue

            pos = context.portfolio.positions[stock]
            if pos.closeable_amount <= 0:
                cancelled.append(stock)
                continue

            cd_item = current_data[stock]
            curr_price = cd_item.last_price
            if curr_price is None or curr_price <= 0:
                # Dragon取不到价格时不把预警升级为卖出；兼容持仓保留旧行为。
                if alert.get('entry_type') == 'dragon_follow':
                    cancelled.append(stock)
                else:
                    confirmed.append(stock)
                continue

            avg_cost = alert['avg_cost']
            current_pnl = curr_price / avg_cost - 1
            recovery_line = -recovery_ratio  # 默认-2%

            if current_pnl > recovery_line:
                # 价格已恢复, 取消止损
                meta = g.positions_meta.get(stock, {})
                if alert.get('entry_type') == 'dragon_follow':
                    _clear_dragon_stop_warning(stock, meta, current_pnl, 'gap_recovered')
                log.info(
                    "GAP_STOP|stock={}|name={}|reason=gap_recovered|pnl={:.2f}%|"
                    "recovery_line={:.2f}%".format(
                        stock, get_stock_name_cached(stock),
                        current_pnl * 100, recovery_line * 100
                    )
                )
                cancelled.append(stock)
            elif alert.get('entry_type') == 'dragon_follow':
                meta = g.positions_meta.get(stock, {})
                ma5 = _estimate_intraday_ma5(stock, curr_price, context)
                exit_reason = _evaluate_dragon_intraday_stop(
                    stock, meta, current_pnl, curr_price, ma5,
                    context.current_dt, 'gap_confirm'
                )
                if exit_reason in ('dragon_confirm_stop', 'dragon_delayed_stop'):
                    alert['exit_reason'] = exit_reason
                    confirmed.append(stock)
                else:
                    _set_dragon_stop_warning(stock, meta, current_pnl, 'gap_confirm')
                    log.info(
                        "GAP_STOP|stock={}|name={}|reason=dragon_stop_warning|pnl={:.2f}%|"
                        "action=hold".format(
                            stock, get_stock_name_cached(stock), current_pnl * 100
                        )
                    )
                    cancelled.append(stock)
            else:
                # 未恢复, 确认执行止损
                confirmed.append(stock)

        except Exception as e:
            log.error(
                "GAP_STOP_ERROR|stock={}|name={}|stage=confirm|error={}".format(
                    stock, get_stock_name_cached(stock), e
                )
            )
            if alert.get('entry_type') == 'dragon_follow':
                cancelled.append(stock)
            else:
                confirmed.append(stock)

    # 执行确认的止损
    for stock in confirmed:
        alert = g.gap_down_alerts.pop(stock, None)
        if not alert:
            continue
        try:
            current_pnl = current_data[stock].last_price / alert['avg_cost'] - 1
        except Exception:
            current_pnl = alert['open_pnl']

        exit_reason = alert.get('exit_reason', 'dragon_confirm_stop') \
            if alert['entry_type'] == 'dragon_follow' else 'gap_down_stop'
        if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=current_pnl):
            strategy = alert['strategy']
            entry_type = alert['entry_type']
            diag_add('{}_sell_all'.format(strategy))
            if entry_type == 'dragon_follow':
                diag_add('dragon_sell_orders')
            log.info(
                "GAP_STOP|stock={}|name={}|reason=gap_confirm_stop|sell_reason={}|"
                "strategy={}|entry={}|open_pnl={:.2f}%|confirm_pnl={:.2f}%".format(
                    stock, get_stock_name_cached(stock),
                    exit_reason, strategy, entry_type,
                    alert['open_pnl'] * 100, current_pnl * 100
                )
            )

    # 清理已取消的
    for stock in cancelled:
        g.gap_down_alerts.pop(stock, None)


# =========================================================
# Panic Scout
# =========================================================


def get_total_slot_hold_count(context):
    """计算A策略总槽位数"""
    count = 0
    for stock in context.portfolio.positions:
        meta = g.positions_meta.get(stock, {})
        strat = meta.get('strategy', '')
        if strat != 'A':
            continue
        count += 1
    pending_new = len([s for s in g.pending_buys.keys()
                       if s not in context.portfolio.positions
                       and g.pending_buys[s].get('strategy') == 'A'])
    return count + pending_new


def get_real_strategy_hold_count(context, strategy_name):
    return sum([
        1 for stock in context.portfolio.positions.keys()
        if g.positions_meta.get(stock, {}).get('strategy') == strategy_name
        and not g.positions_meta.get(stock, {}).get('pending_exit', False)
    ])



# =========================================================
# 昨日预警
# =========================================================


def check_intraday_position_limit(context):
    max_pos = g.cfg.get('max_total_positions', 2)
    if get_total_slot_hold_count(context) >= max_pos:
        g.diag['intraday_pos_cap'] = 1
        log.info("POSITION_CAP|reason=slot_limit|max_positions={}".format(max_pos))
        return True
    if context.portfolio.total_value <= 0:
        return False
    # 计算A仓位比
    a_value = sum(
        pos.value for stock, pos in context.portfolio.positions.items()
        if g.positions_meta.get(stock, {}).get('strategy', '') == 'A'
    )
    pos_ratio = a_value / context.portfolio.total_value
    max_ratio = g.cfg['max_portfolio_position_ratio']
    if pos_ratio >= max_ratio:
        g.diag['intraday_pos_cap'] = 1
        log.info(
            "POSITION_CAP|reason=value_limit|position_ratio={:.2f}%|"
            "max_ratio={:.0f}%".format(pos_ratio * 100, max_ratio * 100)
        )
        return True
    return False


def check_intraday_market_panic(context):
    """检测盘中指数大跌，设置标记(不再直接拦截买入)
    [V1.1.0] 改为标记模式: 只设g.intraday_panic_active=True,
    由趋势过滤器决定是否放行逆势强势股
    """
    current_data = get_current_data()
    idx = g.cfg['regime_index']
    try:
        idx_last = current_data[idx].last_price
    except Exception:
        return False
    if idx_last is None or idx_last <= 0:
        return False
    h = attribute_history(idx, 1, '1d', ['close'])
    if len(h) < 1:
        return False
    prev_close = h['close'][0]
    if prev_close is None or prev_close <= 0:
        return False
    intraday_ret = idx_last / prev_close - 1
    if intraday_ret <= g.cfg['market_panic_drop']:
        g.diag['intraday_panic'] = 1
        g.intraday_panic_active = True
        log.info(
            "MARKET_PANIC|period=intraday|index_ret={:.2f}%|"
            "action=trend_filter".format(intraday_ret * 100)
        )
        return True
    return False


def check_intraday_open_risk(context):
    """盘中开仓风险检查 — 仅检查仓位上限,不再因指数下跌一刀切拦截"""
    if check_intraday_position_limit(context):
        return True
    # [V1.1.0] 盘中恐慌不再拦截,改为设置标记由趋势过滤器处理
    check_intraday_market_panic(context)
    return False



def update_daily_risk_switch_yesterday(context):
    """[V1.1.0] 昨日恐慌检测 — 不再禁止买入,改为记录信息供趋势过滤器使用
    旧逻辑: 昨日跌>2% → 全面禁买 或 侦察仓模式
    新逻辑: 昨日跌>2% → 记录标记,由趋势过滤器+仓位缩减自动处理
    """
    h = attribute_history(g.cfg['regime_index'], 2, '1d', ['close'])
    if len(h) < 2:
        return

    y_ret = h['close'].iloc[-1] / h['close'].iloc[-2] - 1
    g.panic_yesterday_ret = y_ret

    if y_ret > g.cfg['market_panic_drop']:
        return

    diag_add('risk_panic_yesterday')
    g.diag['panic_yesterday_ret'] = round(y_ret, 4)

    # [V1.1.0] 不再设置 g.no_new_position_today = True
    # 趋势过滤器会自动处理: 大盘下跌趋势中只放行逆势强势股+缩仓
    log.info(
        "MARKET_PANIC|period=previous_day|index_ret={:.2f}%|"
        "action=trend_filter".format(y_ret * 100)
    )


def update_portfolio_nav_and_brake(context):
    """NAV跟踪 + A策略回撤保护(B相关逻辑已移除)"""
    nav = context.portfolio.total_value / g.bt['start_cash'] if g.bt['start_cash'] else 1.0
    eps = 1e-6

    if nav >= g.bt['peak_nav']:
        new_high = nav > g.bt['peak_nav']
        g.bt['peak_nav'] = nav

        if new_high:
            if g.A_dd_cooldown_active or not g.A_dd_rearm_ready or g.A_pause_days_left > 0:
                log.info("PORTFOLIO_GUARD|event=new_high|action=reset")
            g.A_dd_cooldown_active = False
            g.A_pause_days_left = 0
            g.A_dd_rearm_ready = True
            g.A_rearm_grace_days_left = 0

    current_dd = nav / g.bt['peak_nav'] - 1 if g.bt['peak_nav'] > 0 else 0.0
    g.bt['current_dd'] = current_dd
    g.bt['max_drawdown'] = min(g.bt['max_drawdown'], current_dd)

    g.diag['portfolio_dd'] = round(current_dd, 4)
    g.diag['portfolio_peak_nav'] = round(g.bt['peak_nav'], 4)

    has_a_position = get_real_strategy_hold_count(context, 'A') > 0
    g.A_flat_days = 0 if has_a_position else (g.A_flat_days + 1)
    g.diag['A_flat_days'] = g.A_flat_days
    g.diag['A_deadlock_scout_mode'] = 0

    # A 恢复
    if current_dd >= -g.cfg['A_dd_rearm_level'] - eps and not g.A_dd_rearm_ready:
        g.A_dd_rearm_ready = True
        g.A_rearm_grace_days_left = 1
        g.diag['A_rearm_level_hit'] = 1
        log.info("PORTFOLIO_GUARD|event=rearm|grace_days=1")

    if g.A_dd_cooldown_active and g.A_pause_days_left > 0:
        g.A_pause_days_left -= 1
        if g.A_pause_days_left == 0:
            g.A_dd_cooldown_active = False
            log.info("PORTFOLIO_GUARD|event=cooldown_released")

    if (
        (not g.A_dd_rearm_ready)
        and (not g.A_dd_cooldown_active)
        and g.A_pause_days_left == 0
        and (not has_a_position)
        and g.A_flat_days >= g.cfg['A_deadlock_flat_days']
        and g.diag.get('risk_panic_yesterday', 0) == 0
        and g.market_regime == 'bull'
    ):
        g.diag['A_deadlock_scout_mode'] = 1

    if (
        current_dd <= -g.cfg['A_deep_dd_trigger_level']
        and (not g.A_dd_cooldown_active)
        and g.A_dd_rearm_ready
    ):
        g.A_dd_cooldown_active = True
        g.A_pause_days_left = g.cfg['A_deep_dd_cooldown_days']
        g.A_dd_rearm_ready = False
        g.A_rearm_grace_days_left = 0
        log.info(
            "PORTFOLIO_GUARD|event=deep_drawdown|drawdown={:.2f}%|"
            "pause_days={}".format(current_dd * 100, g.A_pause_days_left)
        )

    g.diag['A_pause_days_left'] = g.A_pause_days_left
    g.diag['A_dd_cooldown_active'] = 1 if g.A_dd_cooldown_active else 0
    g.diag['A_dd_rearm_ready'] = 1 if g.A_dd_rearm_ready else 0
    g.diag['A_rearm_grace_days_left'] = g.A_rearm_grace_days_left


def _ensure_trade_accounting_fields(meta, pos=None):
    """补齐交易账本字段，并兼容旧版 total_* / partial_sell_records。"""
    records = meta.setdefault('partial_sell_records', [])
    partial_records = [
        record for record in records
        if record.get('type', 'partial') != 'final'
    ]
    recorded_sell_amount = sum(
        float(record.get('amount', 0) or 0) for record in partial_records
    )
    recorded_sell_value = sum(
        float(record.get('sell_value', 0) or 0) for record in partial_records
    )
    recorded_pnl_value = sum(
        float(record.get('pnl_value', 0) or 0) for record in partial_records
    )

    if 'buy_amount_accum' not in meta:
        buy_amount = float(meta.get('entry_amount', 0) or 0)
        if buy_amount <= 0 and pos is not None:
            buy_amount = float(getattr(pos, 'total_amount', 0) or 0)
        meta['buy_amount_accum'] = buy_amount
    if 'sell_amount_accum' not in meta:
        meta['sell_amount_accum'] = recorded_sell_amount
    if 'sell_value_accum' not in meta:
        legacy_sell_value = float(meta.get('total_sell_value', 0) or 0)
        meta['sell_value_accum'] = (
            legacy_sell_value if legacy_sell_value > 0 else recorded_sell_value
        )
    if 'realized_pnl_accum' not in meta:
        legacy_pnl_value = float(meta.get('realized_pnl_value', 0) or 0)
        meta['realized_pnl_accum'] = (
            legacy_pnl_value if legacy_pnl_value != 0 else recorded_pnl_value
        )
    meta['accounting_error'] = int(meta.get('accounting_error', 0) or 0)


def _build_partial_sell_unique_key(
        stock, amount, reason, current_dt, order_id=None):
    if order_id is not None and str(order_id) != '':
        return 'order:{}'.format(order_id)
    trade_date = (
        current_dt.date() if hasattr(current_dt, 'date') else current_dt
    )
    return 'fallback:{}|{}|{:.4f}|{}'.format(
        trade_date, stock, float(amount or 0), reason or ''
    )


def _valid_partial_order_amount(value, requested_amount, amount_before):
    try:
        value = abs(float(value or 0))
    except Exception:
        return None
    upper_bound = min(
        float(requested_amount or 0), float(amount_before or 0)
    )
    if value <= 0 or upper_bound <= 0 or value > upper_bound + 1e-8:
        return None
    return value


def _extract_partial_order_amounts(
        order_obj, requested_amount, amount_before):
    """提取真实成交量与调整后委托量；委托量本身不作为成交入账。"""
    result = {
        'actual_filled_amount': None,
        'actual_source': None,
        'adjusted_order_amount': None,
        'adjusted_source': None,
    }
    if order_obj is None or isinstance(order_obj, int):
        return result

    for field in (
            'filled', 'filled_amount', 'deal_amount', 'traded_amount'):
        value = _valid_partial_order_amount(
            getattr(order_obj, field, None),
            requested_amount,
            amount_before,
        )
        if value is not None:
            result['actual_filled_amount'] = value
            result['actual_source'] = 'order_actual'
            break

    order_amount = _valid_partial_order_amount(
        getattr(order_obj, 'amount', None),
        requested_amount,
        amount_before,
    )
    if (order_amount is not None
            and (
                abs(order_amount - float(requested_amount or 0)) > 1e-8
                or abs(order_amount % 100) <= 1e-8
                or abs(order_amount - float(amount_before or 0)) <= 1e-8
            )):
        result['adjusted_order_amount'] = order_amount
        result['adjusted_source'] = 'order_adjusted'

    try:
        import re
        order_text = '{} {}'.format(
            getattr(order_obj, 'error', '') or '',
            str(order_obj),
        )
        match = re.search(
            r'(?:调整为|adjust(?:ed)?\s*(?:to)?)\D*([0-9]+(?:\.[0-9]+)?)',
            order_text,
            flags=re.IGNORECASE,
        )
        if match:
            adjusted = _valid_partial_order_amount(
                match.group(1), requested_amount, amount_before
            )
            if adjusted is not None:
                result['adjusted_order_amount'] = adjusted
                result['adjusted_source'] = 'order_adjusted'
    except Exception:
        pass

    status_text = str(getattr(order_obj, 'status', '') or '').lower()
    if (result['actual_filled_amount'] is None
            and result['adjusted_order_amount'] is not None
            and 'filled' in status_text):
        result['actual_filled_amount'] = result['adjusted_order_amount']
        result['actual_source'] = 'order_actual'
    return result


def _get_lot_adjusted_partial_amount(requested_amount, amount_before):
    requested_amount = min(
        max(float(requested_amount or 0), 0.0),
        max(float(amount_before or 0), 0.0),
    )
    if requested_amount <= 0:
        return 0.0
    if requested_amount >= float(amount_before or 0) - 1e-8:
        return requested_amount
    return float(int(requested_amount // 100) * 100)


def _record_partial_sell_accounting(
        meta, stock, target_amount, price, cost_price, reason,
        current_dt, order_id, unique_key, source,
        requested_amount=None, previous_amount=None, current_amount=None):
    """按订单唯一键幂等记录已确认的部分卖出数量。"""
    _ensure_trade_accounting_fields(meta)
    target_amount = float(target_amount or 0)
    price = float(price or 0)
    cost_price = float(cost_price or 0)
    if target_amount <= 0 or price <= 0:
        raise ValueError(
            'invalid_partial_accounting_snapshot amount={} price={}'.format(
                target_amount, price
            )
        )

    records = meta.setdefault('partial_sell_records', [])
    existing = next(
        (
            record for record in records
            if record.get('type', 'partial') != 'final'
            and record.get('unique_key') == unique_key
        ),
        None,
    )
    existing_amount = float(existing.get('amount', 0) or 0) if existing else 0.0
    delta_amount = max(target_amount - existing_amount, 0.0)
    buy_amount_accum = float(meta.get('buy_amount_accum', 0.0) or 0.0)
    sell_amount_accum = float(meta.get('sell_amount_accum', 0.0) or 0.0)
    remaining_to_account = max(buy_amount_accum - sell_amount_accum, 0.0)
    if buy_amount_accum > 0:
        delta_amount = min(delta_amount, remaining_to_account)
    if delta_amount <= 1e-8:
        return 0.0, 0.0, 0.0
    accounted_target_amount = existing_amount + delta_amount

    delta_value = price * delta_amount
    delta_pnl = delta_value - cost_price * delta_amount
    meta['sell_amount_accum'] = (
        float(meta.get('sell_amount_accum', 0.0) or 0.0) + delta_amount
    )
    meta['sell_value_accum'] = (
        float(meta.get('sell_value_accum', 0.0) or 0.0) + delta_value
    )
    meta['realized_pnl_accum'] = (
        float(meta.get('realized_pnl_accum', 0.0) or 0.0) + delta_pnl
    )
    meta['total_sell_value'] = meta['sell_value_accum']
    meta['realized_pnl_value'] = meta['realized_pnl_accum']

    if existing is None:
        time_text = (
            current_dt.strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(current_dt, 'strftime') else str(current_dt)
        )
        records.append({
            'time': time_text,
            'date': time_text[:10],
            'stock': stock,
            'type': 'partial',
            'amount': accounted_target_amount,
            'price': price,
            'value': delta_value,
            'sell_value': delta_value,
            'pnl_value': delta_pnl,
            'source': source,
            'reason': reason,
            'order_id': order_id,
            'unique_key': unique_key,
            'requested_amount': float(requested_amount or target_amount),
            'actual_filled_amount': accounted_target_amount,
            'previous_amount': previous_amount,
            'current_amount': current_amount,
        })
    else:
        existing['amount'] = existing_amount + delta_amount
        existing['price'] = price
        existing['value'] = (
            float(existing.get('value', existing.get('sell_value', 0)) or 0)
            + delta_value
        )
        existing['sell_value'] = (
            float(existing.get('sell_value', 0) or 0) + delta_value
        )
        existing['pnl_value'] = (
            float(existing.get('pnl_value', 0) or 0) + delta_pnl
        )
        existing['actual_filled_amount'] = existing['amount']
        existing['previous_amount'] = previous_amount
        existing['current_amount'] = current_amount
        existing['source'] = source
    return delta_amount, delta_value, delta_pnl


def _clear_pending_livermore_add(meta):
    meta['pending_add'] = False
    meta['pending_add_amount_before'] = 0
    meta['pending_add_price'] = None
    meta['pending_add_cost_before'] = 0.0
    meta['pending_add_target_value'] = 0.0
    meta['pending_add_date'] = None
    meta['pending_add_order_id'] = None
    meta['pending_add_confirmed'] = False
    meta['pending_add_recorded_amount'] = 0.0
    meta['pending_add_recorded_value'] = 0.0


def _sync_pending_livermore_add(stock, meta, curr_amount, curr_avg_cost, current_dt):
    """根据持仓数量和成本变化确认加仓，不把委托提交当成成交。"""
    _ensure_trade_accounting_fields(meta)
    amount_before = float(meta.get('pending_add_amount_before', 0) or 0)
    cost_before = float(meta.get('pending_add_cost_before', 0) or 0)
    total_added_amount = max(float(curr_amount) - amount_before, 0.0)
    recorded_amount = float(meta.get('pending_add_recorded_amount', 0) or 0)
    recorded_value = float(meta.get('pending_add_recorded_value', 0) or 0)

    total_added_value = max(
        float(curr_avg_cost or 0) * float(curr_amount)
        - cost_before * amount_before,
        0.0,
    )
    if total_added_amount > 0 and total_added_value <= 0:
        total_added_value = (
            float(meta.get('pending_add_price', 0) or 0) * total_added_amount
        )

    newly_added_amount = max(total_added_amount - recorded_amount, 0.0)
    newly_added_value = max(total_added_value - recorded_value, 0.0)
    if newly_added_amount > 0:
        meta['total_buy_value'] = (
            float(meta.get('total_buy_value', 0.0) or 0.0)
            + newly_added_value
        )
        meta['buy_amount_accum'] = (
            float(meta.get('buy_amount_accum', 0.0) or 0.0)
            + newly_added_amount
        )
        meta['pending_add_recorded_amount'] = total_added_amount
        meta['pending_add_recorded_value'] = total_added_value

        if not meta.get('pending_add_confirmed', False):
            meta['pending_add_confirmed'] = True
            meta['livermore_added'] = True
            meta['winner_added'] = True
            meta['winner_add_date'] = current_dt.date()
            meta['added_times'] = int(meta.get('added_times', 0) or 0) + 1
            diag_add('livermore_add_confirmed')
            log.info(
                "LIVERMORE_ADD_CONFIRMED|stock={}|name={}|added_amount={:.0f}|"
                "added_value={:.2f}|added_times={}".format(
                    stock, get_stock_name_cached(stock),
                    total_added_amount, total_added_value,
                    meta['added_times']
                )
            )

    pending_date = meta.get('pending_add_date')
    today = current_dt.date()
    now_hm = current_dt.strftime('%H:%M') if hasattr(current_dt, 'strftime') else ''
    expired = (
        pending_date is not None
        and (pending_date < today or (pending_date == today and now_hm >= '15:00'))
    )
    if expired:
        if not meta.get('pending_add_confirmed', False):
            diag_add('livermore_add_cancelled')
            log.info(
                "LIVERMORE_ADD_CANCELLED|stock={}|name={}|"
                "reason=no_position_increase_or_order_cancelled".format(
                    stock, get_stock_name_cached(stock)
                )
            )
        _clear_pending_livermore_add(meta)


def sync_position_meta_with_real_positions(context):
    real_positions = set(context.portfolio.positions.keys())

    for stock in list(g.positions_meta.keys()):
        if stock not in real_positions:
            meta = g.positions_meta[stock]
            if meta.get('slot_type') == 'satellite':
                log.info(
                    "SHADOW_EXIT_CONFIRMED|date={}|stock={}|name={}|"
                    "entry_date={}|exit_reason={}|pending_exit={}|"
                    "sell_amount_accum={:.0f}|buy_amount_accum={:.0f}".format(
                        context.current_dt.date(), stock,
                        get_stock_name_cached(stock),
                        meta.get('confirm_date') or meta.get('buy_date'),
                        meta.get('last_exit_reason', ''),
                        int(meta.get('pending_exit', False)),
                        float(meta.get('sell_amount_accum', 0.0) or 0.0),
                        float(meta.get('buy_amount_accum', 0.0) or 0.0),
                    )
                )
            finalize_exited_position(stock, meta)
            del g.positions_meta[stock]

    for stock in list(g.pending_buys.keys()):
        if stock in real_positions:
            pb = g.pending_buys[stock]
            pos = context.portfolio.positions[stock]

            g.positions_meta[stock] = {
                'strategy': pb['strategy'],
                'entry_type': pb['entry_type'],
                'tpl': pb.get('tpl', ''),
                'buy_date': pb.get('buy_date', pb.get('create_date')),
                'entry_date': pb.get('create_date'),
                'initial_rank': pb.get('rank', 0),
                'initial_pos_ratio': pb.get('pos_ratio', 0.0),
                'livermore_added': pb.get('livermore_added', False),
                'winner_added': pb.get('livermore_added', False),
                'stop_warning': pb.get('stop_warning', False),
                'dragon_stop_warning': pb.get('stop_warning', False),
                'stage': pb['stage'],
                'slot_type': pb.get(
                    'slot_type',
                    'core' if pb.get('entry_type') == 'dragon_follow' else ''
                ),
                'strategy_tag': pb.get(
                    'strategy_tag',
                    'original_core' if pb.get('entry_type') == 'dragon_follow'
                    else ''
                ),
                'entry_rule': pb.get('entry_rule', ''),
                'signal_date': pb.get('signal_date'),
                'confirm_date': pb.get('confirm_date'),
                'entry_price': pb.get('entry_price'),
                'satellite_slot_ratio': pb.get('satellite_slot_ratio', 0.0),
                'max_hold_days': pb.get('max_hold_days', 0),
                'pending_exit': False,
                'last_exit_date': None,
                'last_exit_reason': '',
                'pending_exit_ret_snapshot': None,
                'pending_exit_amount_before': 0,
                'pending_exit_closeable_amount_before': 0,
                'pending_exit_requested_amount': 0,
                'pending_exit_sell_price': None,
                'pending_exit_cost_price': None,
                'exit_order_id': None,
                'last_amount': getattr(pos, 'total_amount', None),
                'pending_stage_change': None,
                'pending_stage_change_date': None,
                'pending_stage_change_reason': '',
                'pending_partial_ret_snapshot': None,
                'pending_partial_requested_amount': 0,
                'pending_partial_position_amount_before': 0,
                'pending_partial_filled_amount': 0,
                'pending_partial_sell_price': None,
                'pending_partial_cost_price': None,
                'pending_partial_price_source': None,
                'pending_partial_actual_order_amount': 0,
                'pending_partial_lot_adjusted_amount': 0,
                'pending_partial_expected_amount': 0,
                'pending_partial_expected_after_amount': None,
                'pending_partial_unique_key': None,
                'partial_order_id': None,
                'dragon_realized_return_weighted': 0.0,
                'dragon_realized_amount': 0,
                'below_ma5_count': 0,
                'entry_value': float(
                    getattr(pos, 'avg_cost', 0) or 0
                ) * float(getattr(pos, 'total_amount', 0) or 0),
                'entry_amount': float(getattr(pos, 'total_amount', 0) or 0),
                'buy_amount_accum': float(
                    getattr(pos, 'total_amount', 0) or 0
                ),
                'sell_amount_accum': 0.0,
                'sell_value_accum': 0.0,
                'realized_pnl_accum': 0.0,
                'accounting_error': 0,
                'total_buy_value': float(
                    getattr(pos, 'avg_cost', 0) or 0
                ) * float(getattr(pos, 'total_amount', 0) or 0),
                'total_sell_value': 0.0,
                'realized_pnl_value': 0.0,
                'added_times': 0,
                'partial_sell_records': [],
                'pending_add': False,
                'pending_add_amount_before': 0,
                'pending_add_price': None,
                'pending_add_cost_before': 0.0,
                'pending_add_target_value': 0.0,
                'pending_add_date': None,
                'pending_add_order_id': None,
                'pending_add_confirmed': False,
                'pending_add_recorded_amount': 0.0,
                'pending_add_recorded_value': 0.0,
                'rebuild_scout': pb.get('rebuild_scout', False),
            }

            if pb.get('entry_type') == 'shadow_satellite':
                log.info(
                    "SHADOW_BUY_CONFIRMED|date={}|stock={}|name={}|"
                    "signal_date={}|confirm_date={}|entry_price={:.3f}|"
                    "amount={:.0f}|satellite_slot_ratio={:.2f}%|"
                    "entry_rule={}".format(
                        context.current_dt.date(), stock,
                        get_stock_name_cached(stock), pb.get('signal_date'),
                        pb.get('confirm_date'), float(pb.get('entry_price') or 0),
                        float(getattr(pos, 'total_amount', 0) or 0),
                        float(pb.get('satellite_slot_ratio', 0.0) or 0.0) * 100,
                        pb.get('entry_rule', ''),
                    )
                )

            del g.pending_buys[stock]

    today = context.current_dt.date()
    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta:
            continue
        pos = context.portfolio.positions[stock]
        _ensure_trade_accounting_fields(meta, pos)
        prev_amount = meta.get('last_amount')
        curr_amount = getattr(pos, 'total_amount', None)
        pending_amount_before = meta.get(
            'pending_partial_position_amount_before', prev_amount
        )

        if (meta.get('pending_stage_change')
                and pending_amount_before is not None and curr_amount is not None):
            previous_amount = float(pending_amount_before)
            current_amount = float(curr_amount)
            actual_sold_total = max(previous_amount - current_amount, 0)
            previous_filled = float(
                meta.get('pending_partial_filled_amount', 0) or 0
            )
            newly_filled = max(actual_sold_total - previous_filled, 0)
            buy_amount_accum = float(
                meta.get('buy_amount_accum', 0.0) or 0.0
            )
            remaining_before = max(
                buy_amount_accum
                - float(meta.get('sell_amount_accum', 0.0) or 0.0),
                0.0,
            )
            unique_key = meta.get('pending_partial_unique_key')
            if not unique_key:
                unique_key = _build_partial_sell_unique_key(
                    stock,
                    meta.get('pending_partial_requested_amount', 0),
                    meta.get('pending_stage_change_reason', ''),
                    meta.get('pending_stage_change_date', today),
                    meta.get('partial_order_id'),
                )
                meta['pending_partial_unique_key'] = unique_key
            recorded_for_order = 0.0
            for record in meta.get('partial_sell_records', []):
                if (record.get('type', 'partial') != 'final'
                        and record.get('unique_key') == unique_key):
                    recorded_for_order = float(
                        record.get('amount', 0) or 0
                    )
                    break
            confirmed_newly_filled = min(
                newly_filled, remaining_before + recorded_for_order
            )
            partial_ret = meta.get('pending_partial_ret_snapshot')
            if (meta.get('entry_type') == 'dragon_follow'
                    and partial_ret is not None
                    and confirmed_newly_filled > 0):
                meta['dragon_realized_return_weighted'] = (
                    meta.get('dragon_realized_return_weighted', 0.0)
                    + float(partial_ret) * confirmed_newly_filled
                )
                meta['dragon_realized_amount'] = (
                    meta.get('dragon_realized_amount', 0)
                    + confirmed_newly_filled
                )
            if newly_filled > 0:
                sell_price = meta.get('pending_partial_sell_price')
                cost_price = meta.get('pending_partial_cost_price')
                price_source = meta.get(
                    'pending_partial_price_source', 'estimated'
                )
                sell_value = 0.0
                pnl_value = 0.0
                if sell_price is None and partial_ret is not None and cost_price:
                    sell_price = float(cost_price) * (1.0 + float(partial_ret))
                    price_source = 'estimated'
                if sell_price is not None:
                    sell_value = float(sell_price) * confirmed_newly_filled
                    cost_value = (
                        float(cost_price or 0) * confirmed_newly_filled
                    )
                    pnl_value = sell_value - cost_value
                    try:
                        _record_partial_sell_accounting(
                            meta, stock, actual_sold_total, sell_price,
                            cost_price,
                            meta.get('pending_stage_change_reason', ''),
                            context.current_dt,
                            meta.get('partial_order_id'),
                            unique_key,
                            'position_sync',
                            requested_amount=meta.get(
                                'pending_partial_requested_amount', 0
                            ),
                            previous_amount=previous_amount,
                            current_amount=current_amount,
                        )
                    except Exception as e:
                        accounted_amount = 0.0
                        meta['accounting_error'] = 1
                        log.warning(
                            "TRADE_ACCOUNTING_WARN|stock={}|name={}|"
                            "reason=partial_sync_record_failed|error={}".format(
                                stock, get_stock_name_cached(stock), e
                            )
                        )
                else:
                    meta['accounting_error'] = 1
                    log.warning(
                        "TRADE_ACCOUNTING_WARN|stock={}|name={}|"
                        "reason=partial_sell_price_missing|amount={:.0f}".format(
                            stock, get_stock_name_cached(stock), newly_filled
                        )
                    )
                diag_add('partial_sell_confirmed')
                remaining_to_account = max(
                    buy_amount_accum
                    - float(meta.get('sell_amount_accum', 0.0) or 0.0),
                    0.0,
                )
                log.info(
                    "PARTIAL_SELL_CONFIRMED|stock={}|name={}|"
                    "requested_amount={:.0f}|actual_filled_amount={:.0f}|"
                    "previous_amount={:.0f}|current_amount={:.0f}|"
                    "sell_amount_accum={:.0f}|buy_amount_accum={:.0f}|"
                    "remaining_to_account={:.0f}|sell_value={:.2f}|"
                    "pnl_value={:.2f}|source={}|reason={}".format(
                        stock, get_stock_name_cached(stock),
                        float(meta.get(
                            'pending_partial_requested_amount', 0
                        ) or 0),
                        confirmed_newly_filled,
                        previous_amount, current_amount,
                        float(meta.get('sell_amount_accum', 0.0) or 0.0),
                        buy_amount_accum, remaining_to_account,
                        sell_value, pnl_value, 'position_sync',
                        meta.get('pending_stage_change_reason', '')
                    )
                )
            meta['pending_partial_filled_amount'] = actual_sold_total

            expected_amount = float(
                meta.get('pending_partial_expected_amount', 0) or 0
            )
            if expected_amount <= 0:
                expected_amount = float(
                    meta.get('pending_partial_lot_adjusted_amount', 0) or 0
                )
            if expected_amount <= 0:
                expected_amount = float(
                    meta.get('pending_partial_requested_amount', 0) or 0
                )
            expected_after_amount = meta.get(
                'pending_partial_expected_after_amount'
            )
            request_filled = (
                expected_amount <= 0
                or actual_sold_total + 1e-8 >= expected_amount
                or (
                    expected_after_amount is not None
                    and current_amount <= float(expected_after_amount) + 1e-8
                )
            )
            timed_out = (
                meta.get('pending_stage_change_date') is not None
                and meta.get('pending_stage_change_date') < today
            )
            if request_filled or timed_out:
                if actual_sold_total > 0:
                    next_stage = meta['pending_stage_change']
                    stage_reason = meta.get('pending_stage_change_reason', '')
                    meta['stage'] = next_stage
                    diag_add('stage_change_confirmed')
                    log.info(
                        "STAGE_CHANGE_CONFIRMED|stock={}|name={}|stage={}|"
                        "filled_amount={:.0f}|reason={}".format(
                            stock, get_stock_name_cached(stock), next_stage,
                            actual_sold_total, stage_reason
                        )
                    )
                meta['pending_stage_change'] = None
                meta['pending_stage_change_date'] = None
                meta['pending_stage_change_reason'] = ''
                meta['pending_partial_ret_snapshot'] = None
                meta['pending_partial_requested_amount'] = 0
                meta['pending_partial_position_amount_before'] = 0
                meta['pending_partial_filled_amount'] = 0
                meta['pending_partial_sell_price'] = None
                meta['pending_partial_cost_price'] = None
                meta['pending_partial_price_source'] = None
                meta['pending_partial_actual_order_amount'] = 0
                meta['pending_partial_lot_adjusted_amount'] = 0
                meta['pending_partial_expected_amount'] = 0
                meta['pending_partial_expected_after_amount'] = None
                meta['pending_partial_unique_key'] = None
                meta['partial_order_id'] = None

        if meta.get('pending_add') and curr_amount is not None:
            _sync_pending_livermore_add(
                stock, meta, curr_amount,
                float(getattr(pos, 'avg_cost', 0) or 0),
                context.current_dt,
            )

        meta['last_amount'] = curr_amount

    for stock in list(g.pending_buys.keys()):
        create_date = g.pending_buys[stock].get('create_date')
        if create_date is not None and create_date < today \
                and stock not in real_positions:
            del g.pending_buys[stock]


def check_orphan_positions(context):
    real_positions = set(context.portfolio.positions.keys())
    unknown_count = 0
    pending_exit_count = 0
    for stock in real_positions:
        if stock not in g.positions_meta:
            if stock not in g.pending_buys:
                g.positions_meta[stock] = {
                    'strategy': 'unknown', 'entry_type': 'orphan',
                    'stage': 'full', 'pending_exit': False,
                    'last_exit_date': None, 'last_exit_reason': ''
                }
                unknown_count += 1
                log.info(
                    "ORPHAN_POSITION|stock={}|name={}|action=schedule_exit|time=11:26".format(
                        stock, get_stock_name_cached(stock)
                    )
                )
        elif g.positions_meta[stock].get('pending_exit', False):
            pending_exit_count += 1
    g.diag['unknown_positions'] = unknown_count
    g.diag['pending_exit_positions'] = pending_exit_count
    g.diag['pending_buy_positions'] = len(g.pending_buys)


def orphan_sweeper_execute(context):
    try:
        _orphan_sweeper_execute_impl(context)
    except Exception as e:
        log.error("TASK_ERROR|task=orphan_sweeper|error={}".format(e))

def _orphan_sweeper_execute_impl(context):
    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta or meta.get('strategy') != 'unknown':
            continue
        pos = context.portfolio.positions[stock]
        if pos.closeable_amount <= 0:
            continue
        curr_price = get_current_data()[stock].last_price
        ret = curr_price / pos.avg_cost - 1 if pos.avg_cost > 0 else 0.0
        if submit_exit_order(stock, context, reason='orphan_sweeper', ret_snapshot=ret):
            diag_add('orphan_sell')
            log.info(
                "ORPHAN_EXIT|stock={}|name={}|reason=orphan_sweeper".format(
                    stock, get_stock_name_cached(stock)
                )
            )


# =========================================================
# Regime - [OPT-2] 双指数雷达
# =========================================================


def get_intraday_high_price(stock, context):
    """只取当前交易日截至当前时刻的分钟最高价。"""
    try:
        minute_high_df = get_price(
            stock,
            start_date=context.current_dt.date(),
            end_date=context.current_dt,
            frequency='minute',
            fields=['high'],
            skip_paused=True,
            panel=False,
        )
        if minute_high_df is None or minute_high_df.empty:
            return None
        if isinstance(minute_high_df, pd.DataFrame):
            series = minute_high_df['high'].dropna() if 'high' in minute_high_df.columns \
                else minute_high_df.iloc[:, 0].dropna()
        else:
            series = minute_high_df.dropna()
        if len(series) == 0:
            return None
        return float(series.max())
    except Exception:
        return None


def _log_livermore_add_skip(stock, reason, pnl=None):
    # 普通跳过只进入本轮摘要，避免逐票重复日志。
    g.diag['livermore_skip_' + reason] = g.diag.get('livermore_skip_' + reason, 0) + 1


def _order_is_cancelled_or_rejected(order_result):
    status = getattr(order_result, 'status', None)
    if status is None:
        return False
    status_text = str(status).lower()
    return (
        'cancel' in status_text
        or 'reject' in status_text
        or 'error' in status_text
    )


def check_livermore_tail_add(context):
    """14:40仅向已盈利的Dragon deep_water持仓加仓一次15%。"""
    try:
        positions = context.portfolio.positions
        if not positions or context.portfolio.total_value <= 0:
            return

        cfg_a = g.strategies['A']['config']
        single_cap = cfg_a.get('max_single_stock_ratio', 0.50)
        total_cap = cfg_a.get('max_total_position_ratio', 0.75)
        market_trend = getattr(g, 'market_trend', 'sideways')
        market_down = market_trend == 'down'
        add_ratio = cfg_a.get(
            'winner_add_pos_ratio_market_down' if market_down
            else 'winner_add_pos_ratio',
            0.10 if market_down else 0.15,
        )
        pnl_threshold = cfg_a.get(
            'winner_add_pnl_threshold_market_down' if market_down
            else 'winner_add_pnl_threshold',
            0.15 if market_down else 0.10,
        )
        total_value = float(context.portfolio.total_value)
        total_position_ratio = sum(
            float(getattr(pos, 'value', 0) or 0) for pos in positions.values()
        ) / total_value
        current_data = get_current_data()
        stocks = list(positions.keys())
        if hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(stocks)
            except Exception:
                pass

        for stock in stocks:
            meta = g.positions_meta.get(stock, {})
            if meta.get('strategy') != 'A' \
                    or meta.get('entry_type') != 'dragon_follow' \
                    or meta.get('tpl') != 'deep_water':
                continue

            pos = positions[stock]
            curr_price = float(current_data[stock].last_price or 0)
            avg_cost = float(getattr(pos, 'avg_cost', 0) or 0)
            if curr_price <= 0 or avg_cost <= 0:
                continue
            pnl = curr_price / avg_cost - 1

            entry_date = meta.get('buy_date', meta.get('entry_date'))
            today = context.current_dt.date()
            if entry_date is None or entry_date >= today:
                _log_livermore_add_skip(stock, 'same_day_no_add', pnl)
                continue
            if pnl < pnl_threshold:
                _log_livermore_add_skip(
                    stock,
                    'market_down_weak_winner' if market_down else 'pnl_not_enough',
                    pnl,
                )
                continue

            ma5 = _estimate_intraday_ma5(stock, curr_price, context)
            if ma5 is None or curr_price <= ma5:
                _log_livermore_add_skip(stock, 'below_ma5', pnl)
                continue

            if meta.get('pending_add', False):
                _log_livermore_add_skip(stock, 'pending_add_waiting', pnl)
                continue
            if meta.get('livermore_added', meta.get('winner_added', False)):
                _log_livermore_add_skip(stock, 'already_added', pnl)
                continue
            if meta.get('stop_warning', meta.get('dragon_stop_warning', False)):
                _log_livermore_add_skip(stock, 'stop_warning_active', pnl)
                continue
            if g.dragon_circuit_breaker_pause_left > 0:
                _log_livermore_add_skip(stock, 'pause_active', pnl)
                continue

            day_high = get_intraday_high_price(stock, context)
            if day_high is None or day_high <= 0:
                _log_livermore_add_skip(stock, 'intraday_high_unavailable', pnl)
                continue
            intraday_drawdown = (day_high - curr_price) / day_high
            if intraday_drawdown > 0.05:
                _log_livermore_add_skip(stock, 'intraday_pullback_too_large', pnl)
                continue

            current_position_ratio = float(getattr(pos, 'value', 0) or 0) / total_value
            after_position_ratio = current_position_ratio + add_ratio
            if after_position_ratio > single_cap + 1e-8:
                _log_livermore_add_skip(stock, 'single_stock_cap', pnl)
                continue

            # Original target value and target ratio
            original_add_value = total_value * add_ratio
            original_target_ratio = add_ratio

            # Calculate remaining total capacity
            cap_limit = total_cap
            current_total_ratio = total_position_ratio
            available_cap_ratio = max(cap_limit - current_total_ratio, 0.0)

            # Trim target ratio and value by capacity
            actual_ratio = min(original_target_ratio, available_cap_ratio)
            buy_value = total_value * actual_ratio

            # Trim by available cash
            available_cash = float(context.portfolio.available_cash)
            buy_value = min(buy_value, available_cash)

            trim_reason = 'none'
            if buy_value < original_add_value - 1e-6:
                trim_reason = 'cap_fixed_trim'
                log.info(
                    "CAP_FIXED_TRIM|date={}|stock={}|name={}|path=tail_add|"
                    "original_target_value={:.2f}|actual_value={:.2f}|"
                    "original_target_ratio={:.4f}|actual_ratio={:.4f}|"
                    "cap_limit={:.4f}|current_total_ratio={:.4f}|"
                    "post_total_ratio={:.4f}|trim_reason={}".format(
                        context.current_dt.date(), stock, get_stock_name_cached(stock),
                        original_add_value, buy_value,
                        original_target_ratio, buy_value / total_value,
                        cap_limit, current_total_ratio,
                        (current_total_ratio + buy_value / total_value),
                        trim_reason
                    )
                )

            # Round to 100 shares integer multiples
            lot_amount = int(buy_value / curr_price / 100) * 100 if curr_price > 0 else 0
            actual_value = lot_amount * curr_price

            # Check capacity, invalid price, cash or lot size
            if buy_value <= 0 or lot_amount < 100 or actual_value <= 0:
                log.info(
                    "CAP_FIXED_SKIP_NO_CAPACITY|date={}|stock={}|name={}|path=tail_add|"
                    "original_target_value={:.2f}|actual_value={:.2f}|"
                    "original_target_ratio={:.4f}|actual_ratio={:.4f}|"
                    "cap_limit={:.4f}|current_total_ratio={:.4f}|"
                    "post_total_ratio={:.4f}|trim_reason={}".format(
                        context.current_dt.date(), stock, get_stock_name_cached(stock),
                        original_add_value, actual_value,
                        original_target_ratio, actual_value / total_value,
                        cap_limit, current_total_ratio, current_total_ratio,
                        'no_capacity_or_lot'
                    )
                )
                continue

            add_value = actual_value
            actual_ratio = add_value / total_value
            after_total_ratio = current_total_ratio + actual_ratio

            amount_before_add = float(getattr(pos, 'total_amount', 0) or 0)
            cost_before_add = float(getattr(pos, 'avg_cost', 0) or 0)
            od = order_value(stock, add_value)
            if od is None:
                _log_livermore_add_skip(stock, 'order_failed', pnl)
                continue
            if _order_is_cancelled_or_rejected(od):
                diag_add('livermore_add_cancelled')
                log.info(
                    "LIVERMORE_ADD_CANCELLED|stock={}|name={}|"
                    "reason=order_cancelled_or_rejected".format(
                        stock, get_stock_name_cached(stock)
                    )
                )
                continue

            meta['pending_add'] = True
            meta['pending_add_amount_before'] = amount_before_add
            meta['pending_add_price'] = curr_price
            meta['pending_add_cost_before'] = cost_before_add
            meta['pending_add_target_value'] = add_value
            meta['pending_add_date'] = today
            meta['pending_add_order_id'] = (
                od if isinstance(od, int) else getattr(od, 'order_id', None)
            )
            meta['pending_add_confirmed'] = False
            meta['pending_add_recorded_amount'] = 0.0
            meta['pending_add_recorded_value'] = 0.0
            total_position_ratio = after_total_ratio
            diag_add('dragon_add_orders')

            # Log CAP_FIXED_BUY_OK
            log.info(
                "CAP_FIXED_BUY_OK|date={}|stock={}|name={}|path=tail_add|"
                "original_target_value={:.2f}|actual_value={:.2f}|"
                "original_target_ratio={:.4f}|actual_ratio={:.4f}|"
                "cap_limit={:.4f}|current_total_ratio={:.4f}|"
                "post_total_ratio={:.4f}|trim_reason={}".format(
                    context.current_dt.date(), stock, get_stock_name_cached(stock),
                    original_add_value, add_value,
                    original_target_ratio, actual_ratio,
                    cap_limit, current_total_ratio,
                    after_total_ratio,
                    trim_reason
                )
            )

            log.info(
                "LIVERMORE_ADD_SUBMIT|stock={}|name={}|current_pnl={:.2f}%|curr_price={:.3f}|"
                "ma5={:.3f}|day_high={:.3f}|market_trend={}|"
                "intraday_drawdown={:.2f}%|current_position_ratio={:.2f}%|"
                "add_ratio={:.2f}%|after_position_ratio={:.2f}%|"
                "total_position_ratio={:.2f}%|reason=livermore_tail_add".format(
                    stock, get_stock_name_cached(stock),
                    pnl * 100, curr_price, ma5, day_high, market_trend,
                    intraday_drawdown * 100, current_position_ratio * 100,
                    actual_ratio * 100, (current_position_ratio + actual_ratio) * 100,
                    after_total_ratio * 100
                )
            )
        # [LOG OPT] Aggregated skip summary at end of check_livermore_tail_add
        skip_reasons = []
        total_skips = 0
        for k, v in sorted(g.diag.items()):
            if k.startswith('livermore_skip_') and v > 0:
                reason_name = k[len('livermore_skip_'):]
                skip_reasons.append('{}={}'.format(reason_name, v))
                total_skips += v
        if skip_reasons:
            log.info(
                "LIVERMORE_ADD_SKIP_SUMMARY|total={}|{}".format(
                    total_skips, '|'.join(skip_reasons)
                )
            )
    except Exception as e:
        log.error("TASK_ERROR|task=livermore_tail_add|error={}".format(e))


# =============================================================================
# v1.4.0A Shadow Rotation Full-B satellite module
# =============================================================================

def reset_shadow_daily_stats(context):
    g.shadow_daily = {
        'confirm_checked': 0,
        'confirm_passed': 0,
        'satellite_buys': 0,
        'satellite_sells': 0,
        'replace_count': 0,
        'expired_count': 0,
    }


def _shadow_stat(key, val=1):
    if not hasattr(g, 'shadow_daily') or not g.shadow_daily:
        g.shadow_daily = {}
    g.shadow_daily[key] = g.shadow_daily.get(key, 0) + val


def _shadow_to_date(value):
    if value is None:
        return None
    if hasattr(value, 'date'):
        return value.date()
    return value


def _shadow_trade_days_elapsed(start_date, end_date):
    start_date = _shadow_to_date(start_date)
    end_date = _shadow_to_date(end_date)
    if start_date is None or end_date is None:
        return 999
    try:
        days = get_trade_days(start_date=start_date, end_date=end_date)
        return max(0, len(days) - 1)
    except Exception:
        return max(0, (end_date - start_date).days)


def _shadow_is_paused_for_new_buy(context):
    if getattr(g, 'no_new_position_today', False):
        return True, 'no_new_position_today'
    if getattr(g, 'dragon_circuit_breaker_pause_left', 0) > 0:
        return True, 'dragon_pause'
    if getattr(g, 'A_pause_days_left', 0) > 0:
        return True, 'A_pause'
    if getattr(g, 'A_dd_cooldown_active', False):
        return True, 'A_dd_cooldown'
    if getattr(g, 'market_trend', 'sideways') == 'down':
        return True, 'market_down'
    return False, ''


def _shadow_get_position_ratio(context, slot_type=None):
    total_value = float(context.portfolio.total_value or 0)
    if total_value <= 0:
        return 0.0
    value = 0.0
    for stock, pos in context.portfolio.positions.items():
        meta = g.positions_meta.get(stock, {})
        if slot_type is not None and meta.get('slot_type') != slot_type:
            continue
        value += float(getattr(pos, 'value', 0) or 0)
    return value / total_value


def _shadow_satellite_stocks(context):
    return [
        stock for stock in context.portfolio.positions
        if g.positions_meta.get(stock, {}).get('slot_type') == 'satellite'
        or g.positions_meta.get(stock, {}).get('strategy_tag') == 'shadow_rotation'
    ]


def _shadow_is_satellite_pending_buy(pb):
    if not pb:
        return False
    return (
        pb.get('entry_type') == 'shadow_satellite'
        or pb.get('slot_type') == 'satellite'
        or pb.get('strategy_tag') == 'shadow_rotation'
    )


def _shadow_pending_satellite_stocks():
    pending = []
    for stock, pb in getattr(g, 'pending_buys', {}).items():
        if _shadow_is_satellite_pending_buy(pb):
            pending.append(stock)
    return pending


def _shadow_submitted_satellite_stocks_today():
    submitted = getattr(g, 'shadow_satellite_submitted_today', set()) or set()
    try:
        return list(submitted)
    except Exception:
        return []


def _shadow_satellite_slot_state(context):
    slots = int(getattr(g, 'shadow_satellite_slots', 1) or 1)
    held = set(_shadow_satellite_stocks(context))
    pending = set(_shadow_pending_satellite_stocks())
    submitted_today = set(_shadow_submitted_satellite_stocks_today())
    occupied = held | pending | submitted_today

    reason = ''
    allow_new = True
    if len(held) >= slots:
        allow_new = False
        reason = 'satellite_slot_full'
    elif len(pending) > 0 or len(submitted_today) > 0:
        allow_new = False
        reason = 'satellite_pending_buy'
    elif len(occupied) >= slots:
        allow_new = False
        reason = 'satellite_slot_full'

    return {
        'slots': slots,
        'held_satellite_count': len(held),
        'pending_satellite_count': len(pending),
        'submitted_satellite_today': len(submitted_today),
        'satellite_count': len(occupied),
        'allow_new_satellite': allow_new,
        'reason': reason or 'allow',
    }


def _shadow_log_slot_guard(context, state):
    log.info(
        "SHADOW_SLOT_GUARD|date={}|satellite_count={}|"
        "pending_satellite_count={}|submitted_satellite_today={}|"
        "allow_new_satellite={}|reason={}".format(
            context.current_dt.date(),
            int(state.get('satellite_count', 0)),
            int(state.get('pending_satellite_count', 0)),
            int(state.get('submitted_satellite_today', 0)),
            int(bool(state.get('allow_new_satellite', False))),
            state.get('reason', 'unknown')
        )
    )


def _shadow_log_buy_skip(context, stock, name, reason, state):
    log.info(
        "SHADOW_BUY_SKIP|date={}|stock={}|name={}|reason={}|"
        "satellite_count={}|pending_satellite_count={}|"
        "submitted_satellite_today={}|satellite_slots={}".format(
            context.current_dt.date(), stock, name, reason,
            int(state.get('satellite_count', 0)),
            int(state.get('pending_satellite_count', 0)),
            int(state.get('submitted_satellite_today', 0)),
            int(state.get('slots', getattr(g, 'shadow_satellite_slots', 1) or 1))
        )
    )


def _shadow_core_count(context):
    return sum(
        1 for stock in context.portfolio.positions
        if g.positions_meta.get(stock, {}).get('slot_type') == 'core'
        or g.positions_meta.get(stock, {}).get('entry_type') == 'dragon_follow'
    )


def _shadow_is_stock_blocked(stock, current_data):
    try:
        item = current_data[stock]
        name = item.name
        if item.paused:
            return True, 'paused'
        if item.is_st:
            return True, 'st'
        if name and '退' in name:
            return True, 'delisting'
        price = float(item.last_price or 0)
        high_limit = float(item.high_limit or 0)
        if high_limit > 0 and price >= high_limit * 0.999:
            return True, 'limit_up'
    except Exception:
        return True, 'current_data_unavailable'
    return False, ''


def shadow_cleanup_watch_pool(context, reason_prefix='daily'):
    if not hasattr(g, 'shadow_watch_pool'):
        g.shadow_watch_pool = {}
    today = context.current_dt.date()
    current_data = get_current_data()
    for stock in list(g.shadow_watch_pool.keys()):
        item = g.shadow_watch_pool.get(stock, {})
        reason = ''
        if stock in context.portfolio.positions:
            reason = 'already_position'
        elif _shadow_trade_days_elapsed(item.get('signal_date'), today) > 3:
            reason = 'expired'
            _shadow_stat('expired_count')
        else:
            blocked, block_reason = _shadow_is_stock_blocked(stock, current_data)
            if blocked:
                reason = block_reason
        if not reason:
            continue
        log_event = 'WATCH_POOL_EXPIRE' if reason == 'expired' else 'WATCH_POOL_REMOVE'
        log.info(
            "{}|date={}|stock={}|name={}|signal_date={}|signal_price={:.3f}|"
            "signal_rank={}|signal_score={:.4f}|signal_entry_type={}|reason={}".format(
                log_event, today, stock, get_stock_name_cached(stock),
                item.get('signal_date'), float(item.get('signal_price', 0) or 0),
                item.get('signal_rank', 0), float(item.get('signal_score', 0) or 0),
                item.get('signal_entry_type', ''), reason_prefix + '_' + reason
            )
        )
        del g.shadow_watch_pool[stock]


def shadow_after_market_update(context):
    try:
        if not getattr(g, 'shadow_rotation_enabled', False):
            return
        shadow_cleanup_watch_pool(context, reason_prefix='after_close')
        current_data = get_current_data()
        today = context.current_dt.date()
        for item in list(getattr(g, 'dragon_candidates_today', []) or []):
            stock = item.get('stock')
            if not stock or item.get('tpl') != 'deep_water':
                continue
            if item.get('entry_type') != 'dragon_follow':
                continue
            if stock in context.portfolio.positions or stock in g.pending_buys:
                continue
            if stock in g.shadow_watch_pool:
                continue
            blocked, reason = _shadow_is_stock_blocked(stock, current_data)
            if blocked:
                continue
            try:
                price = float(current_data[stock].last_price or 0)
            except Exception:
                price = 0.0
            if price <= 0:
                continue
            record = {
                'stock': stock,
                'name': get_stock_name_cached(stock),
                'signal_date': today,
                'signal_price': price,
                'signal_rank': item.get('rank', 0),
                'signal_score': float(item.get('dragon_score', item.get('score', 0)) or 0),
                'signal_source': 'BIGMEAT_POOL_TOP',
                'signal_entry_type': 'deep_water',
                'expire_days': 3,
                'watch_reason': 'core_candidate_not_bought',
            }
            g.shadow_watch_pool[stock] = record
            log.info(
                "WATCH_POOL_ADD|date={}|stock={}|name={}|signal_date={}|"
                "signal_price={:.3f}|signal_rank={}|signal_score={:.4f}|"
                "signal_entry_type={}|reason={}".format(
                    today, stock, record['name'], record['signal_date'],
                    record['signal_price'], record['signal_rank'],
                    record['signal_score'], record['signal_entry_type'],
                    record['watch_reason']
                )
            )
        shadow_log_daily_summary(context)
    except Exception as e:
        log.error("TASK_ERROR|task=shadow_after_market_update|error={}".format(e))


def _shadow_intraday_volume_high(stock):
    try:
        h = attribute_history(
            stock, 240, '1m', ['high', 'volume'], skip_paused=False
        )
        if h is None or len(h) == 0:
            return None, None
        return float(h['volume'].sum()), float(h['high'].max())
    except Exception:
        return None, None


def _shadow_get_confirm_snapshot(stock, watch_item, context, current_data):
    today = context.current_dt.date()
    days_after = _shadow_trade_days_elapsed(watch_item.get('signal_date'), today)
    try:
        cd_item = current_data[stock]
        current_price = float(cd_item.last_price or 0)
        high_limit = float(cd_item.high_limit or 0)
    except Exception:
        return None, 'current_data_unavailable'
    signal_price = float(watch_item.get('signal_price', 0) or 0)
    if signal_price <= 0 or current_price <= 0:
        return None, 'price_unavailable'
    if days_after not in (1, 2, 3):
        return None, 'days_after_signal_out_of_range'
    if high_limit > 0 and current_price >= high_limit * 0.999:
        return None, 'limit_up'
    try:
        dh = attribute_history(stock, 6, '1d', ['close', 'volume'], skip_paused=False)
        if dh is None or len(dh) < 5:
            return None, 'daily_history_unavailable'
        prev_close = float(dh['close'].iloc[-1])
        prev_volume = float(dh['volume'].iloc[-1])
    except Exception:
        return None, 'daily_history_error'
    if prev_close <= 0 or prev_volume <= 0:
        return None, 'prev_data_invalid'
    today_volume, day_high = _shadow_intraday_volume_high(stock)
    if today_volume is None or day_high is None or day_high <= 0:
        return None, 'intraday_data_unavailable'
    ma5 = _estimate_intraday_ma5(stock, current_price, context)
    if ma5 is None or ma5 <= 0:
        return None, 'ma5_unavailable'
    snapshot = {
        'stock': stock,
        'name': get_stock_name_cached(stock),
        'days_after_signal': days_after,
        'signal_price': signal_price,
        'current_price': current_price,
        'ret_from_signal': current_price / signal_price - 1.0,
        'day_ret': current_price / prev_close - 1.0,
        'volume_ratio_vs_prev': today_volume / prev_volume,
        'ma5': ma5,
        'ma5_distance': current_price / ma5 - 1.0,
        'close_to_day_high': current_price / max(day_high, current_price, 0.01),
        'high_limit': high_limit,
        'is_limit_up': int(high_limit > 0 and current_price >= high_limit * 0.999),
        'signal_rank': watch_item.get('signal_rank', 0),
        'signal_score': float(watch_item.get('signal_score', 0) or 0),
        'signal_date': watch_item.get('signal_date'),
    }
    return snapshot, ''


def _shadow_rule_d_deep_water_passes(snapshot):
    return (
        snapshot['ret_from_signal'] >= 0.05
        and snapshot['day_ret'] >= 0.05
        and 1.0 <= snapshot['volume_ratio_vs_prev'] <= 2.0
        and snapshot['ma5_distance'] <= 0.10
        and snapshot['close_to_day_high'] >= 0.97
        and snapshot['is_limit_up'] == 0
    )


def _shadow_log_confirm(event, snapshot, reason, current_date=None):
    log_date = current_date or datetime.datetime.now().date()
    log.info(
        "{}|date={}|stock={}|name={}|days_after_signal={}|"
        "signal_price={:.3f}|current_price={:.3f}|ret_from_signal={:.2f}%|"
        "day_ret={:.2f}%|volume_ratio_vs_prev={:.4f}|ma5_distance={:.2f}%|"
        "close_to_day_high={:.4f}|high_limit={:.3f}|is_limit_up={}|reason={}".format(
            event, log_date, snapshot['stock'], snapshot['name'],
            snapshot['days_after_signal'],
            snapshot['signal_price'], snapshot['current_price'],
            snapshot['ret_from_signal'] * 100,
            snapshot['day_ret'] * 100,
            snapshot['volume_ratio_vs_prev'],
            snapshot['ma5_distance'] * 100,
            snapshot['close_to_day_high'],
            snapshot['high_limit'], snapshot['is_limit_up'], reason
        )
    )


def _shadow_current_score(stock, context, current_data):
    pos = context.portfolio.positions.get(stock)
    meta = g.positions_meta.get(stock, {})
    if pos is None:
        return -999.0, 0.0, False
    try:
        price = float(current_data[stock].last_price or 0)
    except Exception:
        price = float(getattr(pos, 'price', 0) or 0)
    cost = float(getattr(pos, 'avg_cost', 0) or 0)
    pnl = price / cost - 1.0 if price > 0 and cost > 0 else 0.0
    ma5 = _estimate_intraday_ma5(stock, price, context)
    below_ma5 = bool(ma5 and price > 0 and price < ma5)
    hold_days = _shadow_trade_days_elapsed(meta.get('buy_date'), context.current_dt.date())
    score = pnl * 100.0
    if below_ma5:
        score -= 5.0
    if hold_days > 3 and pnl <= 0:
        score -= 3.0
    return score, pnl, below_ma5


def _shadow_pick_weakest_satellite(context, current_data):
    satellites = _shadow_satellite_stocks(context)
    if not satellites:
        return None, None, None
    scored = []
    for stock in satellites:
        score, pnl, below_ma5 = _shadow_current_score(stock, context, current_data)
        scored.append({
            'stock': stock,
            'score': score,
            'pnl': pnl,
            'below_ma5': below_ma5,
        })
    max_profit = max(item['pnl'] for item in scored)
    weakest = sorted(scored, key=lambda x: (x['score'], x['pnl']))[0]
    if weakest['pnl'] == max_profit and max_profit > 0:
        return None, weakest, 'weakest_is_best_profit'
    return weakest['stock'], weakest, ''


def _shadow_submit_satellite_buy(stock, snapshot, context, reason, slot_state=None):
    if slot_state is None:
        slot_state = _shadow_satellite_slot_state(context)
        _shadow_log_slot_guard(context, slot_state)
    if not slot_state.get('allow_new_satellite', False):
        _shadow_log_buy_skip(
            context, stock, snapshot['name'],
            slot_state.get('reason', 'satellite_slot_full'), slot_state
        )
        return False

    total_value = float(context.portfolio.total_value or 0)
    if total_value <= 0:
        return False
    current_position_ratio = _shadow_get_position_ratio(context)
    cap_limit = g.strategies['A']['config'].get('max_total_position_ratio', 0.75)
    remaining_total = max(cap_limit - current_position_ratio, 0.0)
    target_ratio = g.shadow_satellite_slot_ratio
    actual_ratio = min(target_ratio, remaining_total)
    target_value = total_value * target_ratio
    buy_value = min(total_value * actual_ratio, float(context.portfolio.available_cash or 0))
    trim_reason = 'none'
    if buy_value < target_value - 1e-6:
        trim_reason = 'cap_fixed_trim'
        log.info(
            "CAP_FIXED_TRIM|date={}|stock={}|name={}|target_value={:.2f}|"
            "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
            "post_total_ratio={:.2f}%|trim_reason={}".format(
                context.current_dt.date(), stock, snapshot['name'],
                target_value, buy_value, cap_limit * 100,
                current_position_ratio * 100,
                (current_position_ratio + buy_value / total_value) * 100,
                trim_reason
            )
        )
    lot_amount = int(buy_value / snapshot['current_price'] / 100) * 100 \
        if snapshot['current_price'] > 0 else 0
    actual_value = lot_amount * snapshot['current_price']
    if actual_ratio <= 0 or lot_amount < 100:
        log.info(
            "CAP_FIXED_SKIP_NO_CAPACITY|date={}|stock={}|name={}|target_value={:.2f}|"
            "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
            "post_total_ratio={:.2f}%|trim_reason={}".format(
                context.current_dt.date(), stock, snapshot['name'],
                target_value, actual_value, cap_limit * 100,
                current_position_ratio * 100, current_position_ratio * 100,
                'no_capacity_or_lot'
            )
        )
        return False
    buy_value = actual_value
    target_ratio = buy_value / total_value
    if buy_value <= 0 or buy_value / snapshot['current_price'] < 100:
        log.info(
            "SHADOW_CONFIRM_SKIP|date={}|stock={}|name={}|days_after_signal={}|"
            "signal_price={:.3f}|current_price={:.3f}|ret_from_signal={:.2f}%|"
            "day_ret={:.2f}%|volume_ratio_vs_prev={:.4f}|ma5_distance={:.2f}%|"
            "close_to_day_high={:.4f}|high_limit={:.3f}|is_limit_up={}|reason=cash_or_lot".format(
                context.current_dt.date(), stock, snapshot['name'],
                snapshot['days_after_signal'], snapshot['signal_price'],
                snapshot['current_price'], snapshot['ret_from_signal'] * 100,
                snapshot['day_ret'] * 100, snapshot['volume_ratio_vs_prev'],
                snapshot['ma5_distance'] * 100, snapshot['close_to_day_high'],
                snapshot['high_limit'], snapshot['is_limit_up']
            )
        )
        return False
    od = order_value(stock, buy_value)
    if od is None:
        return False
    mark_pending_buy(stock, 'A', 'shadow_satellite', 'satellite', context, item={
        'tpl': 'deep_water',
        'rank': snapshot.get('signal_rank', 0),
        'pos_ratio': target_ratio,
        'entry_value': buy_value,
        'slot_type': 'satellite',
        'strategy_tag': 'shadow_rotation',
        'entry_rule': 'rule_D_deep_water',
        'signal_date': snapshot.get('signal_date'),
        'confirm_date': context.current_dt.date(),
        'entry_price': snapshot['current_price'],
        'satellite_slot_ratio': target_ratio,
        'max_hold_days': 5,
    })
    if not hasattr(g, 'shadow_satellite_submitted_today'):
        g.shadow_satellite_submitted_today = set()
    g.shadow_satellite_submitted_today.add(stock)
    _shadow_stat('satellite_buys')
    log_entry_feature_observer(
        context, stock, snapshot['name'], 'shadow_satellite',
        price=snapshot['current_price'], snapshot=snapshot
    )
    log.info(
        "CAP_FIXED_BUY_OK|date={}|stock={}|name={}|target_value={:.2f}|"
        "actual_value={:.2f}|cap_limit={:.2f}%|current_total_ratio={:.2f}%|"
        "post_total_ratio={:.2f}%|trim_reason={}".format(
            context.current_dt.date(), stock, snapshot['name'],
            target_value, buy_value, cap_limit * 100,
            current_position_ratio * 100,
            (current_position_ratio + buy_value / total_value) * 100,
            trim_reason
        )
    )
    log.info(
        "SHADOW_BUY_SUBMIT|date={}|stock={}|name={}|target_ratio={:.2f}%|"
        "order_value={:.2f}|reason={}".format(
            context.current_dt.date(), stock, snapshot['name'],
            target_ratio * 100, buy_value, reason
        )
    )
    return True


def shadow_rotation_confirm_check(context):
    try:
        if not getattr(g, 'shadow_rotation_enabled', False):
            return
        paused, pause_reason = _shadow_is_paused_for_new_buy(context)
        shadow_cleanup_watch_pool(context, reason_prefix='confirm')
        if paused:
            return
        current_data = get_current_data()
        for stock, watch_item in list(getattr(g, 'shadow_watch_pool', {}).items()):
            if stock in context.portfolio.positions or stock in g.pending_buys:
                continue
            if watch_item.get('signal_entry_type') != 'deep_water':
                continue
            slot_state = _shadow_satellite_slot_state(context)
            if not slot_state.get('allow_new_satellite', False):
                _shadow_log_slot_guard(context, slot_state)
                _shadow_log_buy_skip(
                    context, stock, get_stock_name_cached(stock),
                    slot_state.get('reason', 'satellite_slot_full'), slot_state
                )
                continue
            snapshot, reason = _shadow_get_confirm_snapshot(stock, watch_item, context, current_data)
            if snapshot is None:
                minimal = {
                    'stock': stock, 'name': get_stock_name_cached(stock),
                    'days_after_signal': _shadow_trade_days_elapsed(
                        watch_item.get('signal_date'), context.current_dt.date()
                    ),
                    'signal_price': float(watch_item.get('signal_price', 0) or 0),
                    'current_price': 0.0, 'ret_from_signal': 0.0,
                    'day_ret': 0.0, 'volume_ratio_vs_prev': 0.0,
                    'ma5_distance': 0.0, 'close_to_day_high': 0.0,
                    'high_limit': 0.0, 'is_limit_up': 0,
                }
                _shadow_log_confirm(
                    'SHADOW_CONFIRM_SKIP', minimal, reason,
                    context.current_dt.date()
                )
                continue
            _shadow_stat('confirm_checked')
            _shadow_log_confirm(
                'SHADOW_CONFIRM_CHECK', snapshot, 'rule_D_deep_water',
                context.current_dt.date()
            )
            if not _shadow_rule_d_deep_water_passes(snapshot):
                _shadow_log_confirm(
                    'SHADOW_CONFIRM_SKIP', snapshot, 'rule_not_pass',
                    context.current_dt.date()
                )
                continue
            _shadow_stat('confirm_passed')
            _shadow_log_confirm(
                'SHADOW_CONFIRM_PASS', snapshot, 'rule_D_deep_water',
                context.current_dt.date()
            )
            slot_state = _shadow_satellite_slot_state(context)
            _shadow_log_slot_guard(context, slot_state)
            if not slot_state.get('allow_new_satellite', False):
                _shadow_log_buy_skip(
                    context, stock, snapshot['name'],
                    slot_state.get('reason', 'satellite_slot_full'), slot_state
                )
                continue
            if _shadow_submit_satellite_buy(
                    stock, snapshot, context, 'new_satellite', slot_state):
                g.shadow_watch_pool.pop(stock, None)
    except Exception as e:
        log.error("TASK_ERROR|task=shadow_rotation_confirm|error={}".format(e))


def should_block_promotion_take_profit(stock, meta, curr_price, context):
    """
    判断是否由于阻断晋级而触发止盈退出。

    注意：当前 no_promotion 是 observer proxy，不是 D3 replay 的严格 ROLE_PROMOTION_EXECUTE 等价实现。
    """
    pos = context.portfolio.positions.get(stock)
    if pos is None:
        return False
    avg_cost = float(getattr(pos, 'avg_cost', 0) or 0)
    if avg_cost <= 0 or curr_price <= 0:
        return False
    pnl = curr_price / avg_cost - 1.0
    ma5 = _estimate_intraday_ma5(stock, curr_price, context)
    below_ma5 = bool(ma5 and curr_price < ma5)

    # 现有简化条件
    if pnl >= 0.03 and not below_ma5:
        return True
    return False


def shadow_rotation_exit_check(context):
    try:
        if not getattr(g, 'shadow_rotation_enabled', False):
            return
        current_data = get_current_data()
        for stock in list(_shadow_satellite_stocks(context)):
            meta = g.positions_meta.get(stock, {})
            if meta.get('pending_exit', False):
                continue
            pos = context.portfolio.positions.get(stock)
            if pos is None or pos.closeable_amount <= 0:
                continue
            try:
                price = float(current_data[stock].last_price or 0)
            except Exception:
                price = float(getattr(pos, 'price', 0) or 0)
            cost = float(getattr(pos, 'avg_cost', 0) or 0)
            if price <= 0 or cost <= 0:
                continue
            pnl = price / cost - 1.0
            ma5 = _estimate_intraday_ma5(stock, price, context)
            below_ma5 = bool(ma5 and price < ma5)
            hold_days = _shadow_trade_days_elapsed(
                meta.get('confirm_date') or meta.get('buy_date'),
                context.current_dt.date()
            )
            reason = ''
            original_promotion_reason = 'observer_satellite_profit_ma5_strength'
            if should_block_promotion_take_profit(stock, meta, price, context):
                reason = 'shadow_no_promotion_take_profit'
                pnl_val = (
                    (price - cost)
                    * float(getattr(pos, 'total_amount', 0) or 0)
                )
                log.info(
                    "PROMOTION_BLOCK_TAKE_PROFIT_NOTE|当前 no_promotion 是 observer proxy，不是 D3 replay 的严格 ROLE_PROMOTION_EXECUTE 等价实现。"
                )
                log.info(
                    "PROMOTION_BLOCK_TAKE_PROFIT|date={}|stock={}|name={}|"
                    "promotion_logic_source={}|d3_equivalence={}|"
                    "pnl_pct={:.2f}%|below_ma5={}|"
                    "original_promotion_reason={}|exit_reason={}|"
                    "satellite_entry_date={}|satellite_entry_price={}|"
                    "exit_price={:.3f}|pnl_val={:.2f}|"
                    "hold_days={}".format(
                        context.current_dt.date(), stock,
                        get_stock_name_cached(stock),
                        'observer_proxy_condition',
                        'strict_no',
                        pnl * 100,
                        below_ma5,
                        original_promotion_reason,
                        reason,
                        meta.get('confirm_date') or meta.get('buy_date'),
                        meta.get('entry_price', cost), price,
                        pnl_val, hold_days
                    )
                )
            elif hold_days >= int(meta.get('max_hold_days', 5) or 5):
                reason = 'shadow_max_hold_5d'
            elif pnl <= -0.06:
                reason = 'shadow_stop_loss_6pct'
            elif below_ma5 and pnl <= 0:
                reason = 'shadow_below_ma5_loss'
            elif hold_days > 3 and pnl <= 0:
                reason = 'shadow_stale_no_profit'
            if not reason:
                continue
            log.info(
                "SHADOW_EXIT_SIGNAL|date={}|stock={}|name={}|entry_date={}|"
                "hold_days={}|entry_price={}|current_price={:.3f}|pnl={:.2f}%|"
                "ma5={}|below_ma5={}|reason={}".format(
                    context.current_dt.date(), stock, get_stock_name_cached(stock),
                    meta.get('confirm_date') or meta.get('buy_date'), hold_days,
                    meta.get('entry_price', cost), price, pnl * 100,
                    ma5 if ma5 is not None else 'NA', int(below_ma5), reason
                )
            )
            if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl):
                _shadow_stat('satellite_sells')
                log.info(
                    "SHADOW_EXIT_SUBMIT|date={}|stock={}|name={}|entry_date={}|"
                    "hold_days={}|entry_price={}|current_price={:.3f}|pnl={:.2f}%|"
                    "ma5={}|below_ma5={}|reason={}".format(
                        context.current_dt.date(), stock, get_stock_name_cached(stock),
                        meta.get('confirm_date') or meta.get('buy_date'), hold_days,
                        meta.get('entry_price', cost), price, pnl * 100,
                        ma5 if ma5 is not None else 'NA', int(below_ma5), reason
                    )
                )
    except Exception as e:
        log.error("TASK_ERROR|task=shadow_rotation_exit|error={}".format(e))


def shadow_log_daily_summary(context):
    total_ratio = _shadow_get_position_ratio(context)
    satellite_ratio = _shadow_get_position_ratio(context, 'satellite')
    core_ratio = _shadow_get_position_ratio(context, 'core')
    slot_state = _shadow_satellite_slot_state(context)
    log.info(
        "SHADOW_DAILY_SUMMARY|date={}|watch_pool_size={}|satellite_count={}|"
        "pending_satellite_count={}|submitted_satellite_today={}|"
        "core_count={}|total_position_ratio={:.2f}%|satellite_position_ratio={:.2f}%|"
        "core_position_ratio={:.2f}%|confirm_checked={}|confirm_passed={}|"
        "satellite_buys={}|satellite_sells={}|replace_count={}|expired_count={}".format(
            context.current_dt.date(),
            len(getattr(g, 'shadow_watch_pool', {}) or {}),
            int(slot_state.get('satellite_count', 0)),
            int(slot_state.get('pending_satellite_count', 0)),
            int(slot_state.get('submitted_satellite_today', 0)),
            _shadow_core_count(context),
            total_ratio * 100, satellite_ratio * 100, core_ratio * 100,
            g.shadow_daily.get('confirm_checked', 0),
            g.shadow_daily.get('confirm_passed', 0),
            g.shadow_daily.get('satellite_buys', 0),
            g.shadow_daily.get('satellite_sells', 0),
            g.shadow_daily.get('replace_count', 0),
            g.shadow_daily.get('expired_count', 0),
        )
    )


def get_stock_list_A(context):
    """兼容入口：普通首板、首板低开和弱转强买入路径已禁用。"""
    return []

def get_dragon_stock_list_A(context):
    try:
        return _get_dragon_stock_list_A_impl(context)
    except Exception as e:
        log.error("DRAGON_POOL_ERROR|stage=global|error={}".format(e))
        return []


def _prefilter_dragon_auction_candidates(
        context, raw_universe_count, seed, per_stock,
        max_auction_prefilter_count=250):
    """用竞价前日线数据限制 get_call_auction 调用范围。"""
    eligible = []
    for stock in sorted(seed):
        meta = per_stock.get(stock)
        if not meta:
            continue
        if meta['y_close'] >= meta['y_hl'] * 0.995:
            continue
        if meta['y_money'] < g.cfg['dragon_min_prev_money']:
            continue
        if meta.get('avg_range', 0.0) > g.cfg.get(
                'dragon_max_avg_daily_range', 0.08):
            continue
        eligible.append({
            'stock': stock,
            'avg_money_5': meta.get('avg_money_5', meta['y_money']),
            'avg_money_10': meta.get('avg_money_10', meta['y_money']),
            'ret_5': meta.get('ret_5', meta['ret3']),
            'ret_10': meta.get('ret_10', meta['ret3']),
            'close_to_20d_high': meta.get(
                'close_to_20d_high',
                meta['y_close'] / max(meta['y_high'], 0.01),
            ),
            'range_10': meta.get('range_10', meta.get('avg_range', 0.0)),
        })

    eligible_count = len(eligible)
    if eligible_count == 0:
        log.info(
            "AUCTION_PREFILTER_SUMMARY|date={}|raw_universe_count={}|"
            "eligible_before_prefilter=0|prefilter_count=0|"
            "auction_call_count_before_est=0|auction_call_count_after=0|"
            "reduction_ratio=0.00%|top_prefilter_score=0.0000|"
            "min_prefilter_score=0.0000".format(
                context.current_dt.date(), raw_universe_count
            )
        )
        return []

    factor_df = pd.DataFrame(eligible)
    factor_columns = [
        'avg_money_5', 'avg_money_10', 'ret_5', 'ret_10',
        'close_to_20d_high', 'range_10',
    ]
    for column in factor_columns:
        factor_df[column] = pd.to_numeric(
            factor_df[column], errors='coerce'
        ).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        factor_df[column + '_rank'] = factor_df[column].rank(
            method='average', pct=True
        )

    factor_df['prefilter_score'] = (
        factor_df['avg_money_5_rank'] * 0.25
        + factor_df['avg_money_10_rank'] * 0.15
        + factor_df['ret_5_rank'] * 0.20
        + factor_df['ret_10_rank'] * 0.10
        + factor_df['close_to_20d_high_rank'] * 0.15
        + factor_df['range_10_rank'] * 0.15
    )
    factor_df = factor_df.sort_values(
        ['prefilter_score', 'stock'],
        ascending=[False, True],
    ).reset_index(drop=True)

    max_count = max(1, int(max_auction_prefilter_count or 250))
    selected_df = factor_df.head(max_count)
    dropped_df = factor_df.iloc[max_count:max_count + 10]
    selected_count = len(selected_df)
    reduction_ratio = (
        float(eligible_count - selected_count) / eligible_count
        if eligible_count else 0.0
    )
    top_score = (
        float(selected_df['prefilter_score'].iloc[0])
        if selected_count else 0.0
    )
    min_score = (
        float(selected_df['prefilter_score'].iloc[-1])
        if selected_count else 0.0
    )

    log.info(
        "AUCTION_PREFILTER_SUMMARY|date={}|raw_universe_count={}|"
        "eligible_before_prefilter={}|prefilter_count={}|"
        "auction_call_count_before_est={}|auction_call_count_after={}|"
        "reduction_ratio={:.2f}%|top_prefilter_score={:.4f}|"
        "min_prefilter_score={:.4f}".format(
            context.current_dt.date(),
            raw_universe_count,
            eligible_count,
            selected_count,
            eligible_count,
            selected_count,
            reduction_ratio * 100,
            top_score,
            min_score,
        )
    )

    for rank, (_, row) in enumerate(selected_df.head(10).iterrows(), 1):
        stock = row['stock']
        log.info(
            "AUCTION_PREFILTER_TOP|rank={}|stock={}|name={}|"
            "prefilter_score={:.4f}|avg_money_5={:.0f}|"
            "avg_money_10={:.0f}|ret_5={:.2f}%|ret_10={:.2f}%|"
            "close_to_20d_high={:.4f}|range_10={:.4f}".format(
                rank,
                stock,
                get_stock_name_cached(stock),
                row['prefilter_score'],
                row['avg_money_5'],
                row['avg_money_10'],
                row['ret_5'] * 100,
                row['ret_10'] * 100,
                row['close_to_20d_high'],
                row['range_10'],
            )
        )

    for rank, (_, row) in enumerate(
            dropped_df.iterrows(), max_count + 1):
        stock = row['stock']
        log.info(
            "AUCTION_PREFILTER_DROPPED_SAMPLE|rank={}|stock={}|name={}|"
            "prefilter_score={:.4f}|avg_money_5={:.0f}|"
            "avg_money_10={:.0f}|ret_5={:.2f}%|ret_10={:.2f}%|"
            "close_to_20d_high={:.4f}|range_10={:.4f}|reason=max_count".format(
                rank,
                stock,
                get_stock_name_cached(stock),
                row['prefilter_score'],
                row['avg_money_5'],
                row['avg_money_10'],
                row['ret_5'] * 100,
                row['ret_10'] * 100,
                row['close_to_20d_high'],
                row['range_10'],
            )
        )

    return selected_df['stock'].tolist()


def _get_dragon_stock_list_A_impl(context):
    universe = get_base_stock_universe(context, include_new=False)
    if not universe:
        return []

    current_data = get_current_data()
    prev_date = context.previous_date
    if prev_date is None:
        log.warning("DRAGON_POOL_SKIP|reason=previous_date_missing")
        return []
    prev_trade_days = get_trade_days(end_date=prev_date, count=2)
    prev_prev_date = prev_trade_days[0] if len(prev_trade_days) >= 2 else None

    start_today = context.current_dt.strftime("%Y-%m-%d") + ' 09:15:00'
    end_today   = context.current_dt.strftime("%Y-%m-%d") + ' 09:26:00'
    start_prev  = str(prev_date) + ' 09:15:00'
    end_prev    = str(prev_date) + ' 09:26:00'

    price_df = get_price(
        universe, end_date=prev_date, frequency='daily',
        fields=['close', 'high', 'high_limit', 'money', 'volume', 'paused'],
        count=4, panel=False
    )
    if price_df is None or price_df.empty:
        return []

    per_stock, ret3_list, money_list = {}, [], []
    price_df = price_df.sort_values(['code', 'time'])
    for stock, df in price_df.groupby('code', sort=False):
        if len(df) < 4:
            continue
        if df['paused'].iloc[-1] != 0:
            continue
        y_close  = float(df['close'].iloc[-1])
        y_high   = float(df['high'].iloc[-1])
        y_hl     = float(df['high_limit'].iloc[-1])
        y_money  = float(df['money'].iloc[-1])
        y_vol    = float(df['volume'].iloc[-1])
        ret3     = y_close / float(df['close'].iloc[0]) - 1
        ret1     = y_close / float(df['close'].iloc[-2]) - 1 if len(df) >= 2 else 0
        per_stock[stock] = {
            'y_close': y_close, 'y_high': y_high, 'y_hl': y_hl,
            'y_money': y_money, 'y_vol': y_vol, 'ret3': ret3, 'ret1': ret1,
        }
        ret3_list.append((stock, ret3))
        money_list.append((stock, y_money))

    ret3_top = set([s for s, _ in
                    sorted(ret3_list, key=lambda x: x[1], reverse=True)[:g.cfg['dragon_ret3_top_n']]])
    money_sorted  = sorted(money_list, key=lambda x: x[1], reverse=True)
    money_top_n   = max(1, int(len(money_sorted) * g.cfg['dragon_money_top_pct']))
    money_top     = set([s for s, _ in money_sorted[:money_top_n]])
    seed = ret3_top | money_top
    if not seed:
        return []

    # 一次批量日线查询同时计算原有近10日日均振幅和竞价前预筛因子。
    for stock in seed:
        if stock in per_stock:
            meta = per_stock[stock]
            meta['avg_range'] = 0.0
            meta['avg_money_5'] = meta['y_money']
            meta['avg_money_10'] = meta['y_money']
            meta['ret_5'] = meta['ret3']
            meta['ret_10'] = meta['ret3']
            meta['close_to_20d_high'] = (
                meta['y_close'] / max(meta['y_high'], 0.01)
            )
            meta['range_10'] = 0.0
    try:
        range_df = get_price(
            list(seed),
            end_date=prev_date,
            frequency='daily',
            fields=['high', 'low', 'close', 'money'],
            count=20,
            panel=False,
        )
        if range_df is not None and not range_df.empty and 'code' in range_df.columns:
            range_df = range_df.sort_values(['code', 'time'])
            for stock, df in range_df.groupby('code', sort=False):
                meta = per_stock.get(stock)
                if not meta:
                    continue
                daily = df[['high', 'low', 'close', 'money']].copy()
                for column in ['high', 'low', 'close', 'money']:
                    daily[column] = pd.to_numeric(
                        daily[column], errors='coerce'
                    )

                money_values = daily['money'].dropna()
                if not money_values.empty:
                    meta['avg_money_5'] = float(
                        money_values.tail(5).mean()
                    )
                    meta['avg_money_10'] = float(
                        money_values.tail(10).mean()
                    )

                close_values = daily['close'].dropna()
                if len(close_values) >= 6 and close_values.iloc[-6] > 0:
                    meta['ret_5'] = (
                        float(close_values.iloc[-1])
                        / float(close_values.iloc[-6]) - 1
                    )
                if len(close_values) >= 11 and close_values.iloc[-11] > 0:
                    meta['ret_10'] = (
                        float(close_values.iloc[-1])
                        / float(close_values.iloc[-11]) - 1
                    )

                high_values = daily['high'].dropna().tail(20)
                if not high_values.empty:
                    high_20 = float(high_values.max())
                    if high_20 > 0:
                        meta['close_to_20d_high'] = (
                            meta['y_close'] / high_20
                        )

                valid_range = daily.dropna(
                    subset=['high', 'low', 'close']
                )
                valid_range = valid_range[
                    valid_range['close'] > 0
                ].tail(10)
                if len(valid_range) >= 5:
                    range_values = (
                        (valid_range['high'] - valid_range['low'])
                        / valid_range['close']
                    )
                    range_mean = range_values.mean()
                    if pd.notna(range_mean):
                        meta['avg_range'] = float(range_mean)
                        meta['range_10'] = float(range_mean)
    except Exception as e:
        log.warning(
            "DRAGON_POOL_ERROR|stage=avg_range_batch|error={}".format(e)
        )

    auction_seed = _prefilter_dragon_auction_candidates(
        context,
        len(universe),
        seed,
        per_stock,
        max_auction_prefilter_count=250,
    )
    if not auction_seed:
        return []

    # 批量预取预筛后的实时字段，避免循环内逐只 high_limit RPC。
    if hasattr(current_data, 'get_batch'):
        try:
            current_data.get_batch(auction_seed)
        except Exception:
            pass

    auc_data = []
    for stock in auction_seed:
        meta = per_stock.get(stock)
        if not meta:
            continue
        try:
            if meta['y_close'] >= meta['y_hl'] * 0.995:
                continue
            if meta['y_money'] < g.cfg['dragon_min_prev_money']:
                continue

            # 日均振幅过滤；批量数据缺失时保持0.0。
            avg_range = meta.get('avg_range', 0.0)
            if avg_range > g.cfg.get('dragon_max_avg_daily_range', 0.08):
                continue

            ad = get_call_auction(stock, start_date=start_today, end_date=end_today,
                                  fields=['time', 'volume', 'current'])
            if ad is None or ad.empty:
                continue
            curr    = float(ad['current'].iloc[-1])
            auc_vol = float(ad['volume'].iloc[-1])
            if curr <= 0 or meta['y_close'] <= 0 or auc_vol <= 0:
                continue

            open_ratio = curr / meta['y_close'] - 1
            if open_ratio <= 0:
                continue
            if curr >= current_data[stock].high_limit * 0.995:
                continue

            auc_ratio  = auc_vol / max(meta['y_vol'], 1)
            auc_amount = auc_vol * curr
            if auc_ratio  < g.cfg['dragon_min_auction_ratio']:
                continue
            if auc_amount < g.cfg['dragon_min_auction_amount']:
                continue

            prev_auc_vol = 0.0
            if (g.cfg.get('dragon_score_mode', 'v3') == 'v1'
                    and prev_prev_date is not None):
                prev_ad = get_call_auction(stock, start_date=start_prev, end_date=end_prev,
                                           fields=['time', 'volume', 'current'])
                if prev_ad is not None and not prev_ad.empty:
                    prev_auc_vol = float(prev_ad['volume'].iloc[-1])

            auc_data.append({
                'stock': stock, 'open_ratio': open_ratio, 'auc_ratio': auc_ratio,
                'auc_amount': auc_amount, 'prev_auc_vol': prev_auc_vol,
            })
        except Exception as e:
            log.error(
                "DRAGON_POOL_ERROR|stock={}|name={}|stage=auction|error={}".format(
                    stock, get_stock_name_cached(stock), e
                )
            )

    if not auc_data:
        return []

    auc_top = set([x['stock'] for x in
                   sorted(auc_data, key=lambda x: x['open_ratio'], reverse=True)
                   [:g.cfg['dragon_auc_top_n']]])

    out = []
    for info in auc_data:
        stock = info['stock']
        meta  = per_stock.get(stock)
        if not meta:
            continue
        if stock not in auc_top and stock not in ret3_top:
            continue

        close_to_high = meta['y_close'] / max(meta['y_high'], 0.01)
        ret3       = meta['ret3']
        ret1       = meta.get('ret1', 0.0)
        y_money    = meta['y_money']
        open_ratio = info['open_ratio']
        auc_ratio  = info['auc_ratio']
        auc_amount = info['auc_amount']
        prev_auc_vol = info['prev_auc_vol']

        # ── 模板判定(两套评分共用) ──
        tpl = 'trend_core'
        if (0.90 <= close_to_high < 0.975
                and open_ratio >= 0.015
                and auc_ratio >= g.cfg['dragon_min_auction_ratio'] * 1.2):
            tpl = 'deep_water'

        # ── 评分体系 ──
        score_mode = g.cfg.get('dragon_score_mode', 'v1')

        if score_mode == 'v2':
            # ============================================================
            # v2评分: 回调低吸型(基于1315条全量因子分析优化)
            # ============================================================
            # 核心思路: 买"涨过但回调过"的票，不追"正在疯涨"的票
            #
            # 与v1的区别:
            #   1. c2h(收高比)反转: 收盘越远离当日高点 → 加分越多
            #      v1: 收盘=最高价(c2h=1.0)得分最高 → 追涨
            #      v2: 收盘远离高点(c2h=0.93)得分最高 → 回调买入
            #      原因: c2h是最强反向因子(IC=-0.068), 高c2h的票冲高回落概率大
            #
            #   2. 竞价量比(ar)删除: IC=-0.032, 竞价放量≠后续会涨
            #      v1: ar权重0.95(第三大权重)
            #      v2: 完全不用
            #      原因: 竞价放量往往是主力出货，不是真正的买入信号
            #
            #   3. 竞价涨幅(or)大幅降权: 1.05 → 0.30
            #      v1: or是最大权重(1.05), 竞价涨得越多分越高
            #      v2: 降到0.30, 只作为辅助参考
            #      原因: or在Q4(3-5%)最佳, Q5(>5%)反而差, 非线性关系
            #
            #   4. deep_water模板大幅加分: 0.015 → 0.040
            #      v1: deep_water只+0.015(象征性)
            #      v2: 加到0.040(显著偏好)
            #      原因: deep_water avg_f3=+0.3%(S+A率25%) vs trend_core -0.2%(17%)
            #
            #   5. 新增ret1(昨日涨幅): 权重0.20
            #      v1: 不使用
            #      v2: 昨天涨的票有短期动量惯性
            #      注意: ret1的IC(f3)=-0.049是负向, 但配合c2h反转后有互补效果
            # ============================================================
            score  = 0.0
            score += min(max(ret3, 0.0), 0.35) * 0.80       # 3日涨幅(唯一正向因子, 略加权)
            score += min(max(open_ratio, 0.0), 0.10) * 0.30 # 竞价涨幅(大幅降权)
            score += (1.0 - close_to_high) * 0.15            # 收高比反转: 离高点越远越好
            score += min(max(ret1, 0.0), 0.10) * 0.20       # 昨日涨幅
            if tpl == 'deep_water':
                score += 0.040                                # deep_water大幅加分
            # ar(竞价量比)和y_money(成交额)不再参与评分

        elif score_mode == 'v3':
            # ============================================================
            # v3评分: Dragon预测型(基于1150条V4全量32字段因子分析)
            # ============================================================
            # 核心思路: 用可观测特征预测哪些票会成为Dragon(f3≥15%/f5≥20%/涨停)
            #
            # 与v2的区别:
            #   1. 新增avg_rng(振幅): Dragon的最强预测因子(效应值+0.261)
            #      高振幅 = 股性活跃 = 更容易爆发
            #
            #   2. 低换手率奖励: IC=-0.112(t=-4.06), 最强统计显著因子
            #      换手率<3%时给大额奖励, 低换手=筹码集中=拉升阻力小
            #
            #   3. inv_c2h权重大幅提升: 0.15→2.5(Dragon效应值+0.250)
            #      收盘远离高点 = 回调充分 = 再次爆发概率高
            #
            #   4. 成长×反转交互项: ret3正+inv_c2h高=最强组合
            #      涨过且回调过 = 主力洗盘完毕
            #
            # 回测对比(Top3, 96个交易日):
            #   v2: f1日均+0.84%, 累计+243%, 胜率49.7%
            #   v3: f1日均+1.25%, 累计+361%, 胜率51.4%
            #   Dragon选中率: v2=25.0% → v3=28.8%
            # ============================================================
            inv_c2h  = 1.0 - close_to_high
            avg_rng  = meta.get('avg_range', 0.0)
            score  = 0.0
            score += inv_c2h * 2.5                                # 反转收高比(Dragon效应+0.250)
            score += avg_rng * 4.0                                # 振幅(Dragon效应+0.261)
            score += max(0, 0.03 - auc_ratio) * 8.0              # 低换手率奖励(IC=-0.112)
            score += min(max(ret3, 0.0), 0.25) * inv_c2h * 2.0   # 成长×反转交互
            score += min(max(ret3, 0.0), 0.30) * 0.50            # 成长基础分
            if tpl == 'deep_water':
                score += 0.15                                     # deep_water偏好(显著优于trend_core)

        else:
            # ============================================================
            # v1评分: 原始追涨型(v9.0.25及之前版本)
            # ============================================================
            # 核心思路: 竞价最强+涨幅最大+量能最大 = 最好的票
            #
            # 问题(基于1315条因子分析):
            #   - 整体IC(f3)=-0.004, 评分与未来收益几乎无关
            #   - Top20%高分组胜率36.5%, 反而低于Mid60%的45%
            #   - ar(竞价量比)IC=-0.032是负向因子, 但权重0.95(第三大)
            #   - c2h(收高比)IC=-0.068是最强负向因子, 但给正向加分
            # ============================================================
            score  = 0.0
            score += min(max(ret3, 0.0), 0.35) * 0.70       # 3日涨幅
            score += min(max(open_ratio, 0.0), 0.10) * 1.05 # 竞价涨幅(最大权重)
            score += min(max(auc_ratio, 0.0), 0.08) * 0.95  # 竞价量比(负向因子!)
            score += min(y_money / 1e9, 10.0) * 0.006       # 成交额
            score += max(min(close_to_high, 1.0), 0.0) * 0.030  # 收高比(方向反了!)
            if prev_auc_vol > 0:
                prev_auc_amount = prev_auc_vol * meta['y_close']
                if prev_auc_amount > 0 and (auc_amount / prev_auc_amount) >= g.cfg['dragon_prev_auction_mult']:
                    score += 0.006                           # 竞价量倍数
            if tpl == 'deep_water':
                score += 0.015                               # deep_water加分(太少)
            elif close_to_high >= 0.955 and ret3 >= g.cfg['A_dragon_min_ret_3d']:
                score += 0.010                               # 强趋势加分

        out.append({
            'stock': stock, 'entry_type': 'dragon_follow', 'tpl': tpl,
            'dragon_score': score, 'ret3': ret3, 'open_ratio': open_ratio,
            'auction_ratio': auc_ratio, 'auction_amount': auc_amount,
            'close_to_high': close_to_high,
        })

    out.sort(key=lambda x: x.get('dragon_score', 0.0), reverse=True)
    uniq, seen = [], set()
    for item in out:
        if item['stock'] in seen:
            continue
        uniq.append(item)
        seen.add(item['stock'])
        if len(uniq) >= 12:
            break
    return uniq


def update_dragon_mode(context):
    g.dragon_mode = False
    g.dragon_pool_size = 0
    g.dragon_top_score = 0.0
    g.dragon_candidates_today = []
    g.dragon_signal_reason = 'none'
    g.diag['dragon_panic_override'] = 0

    if not g.cfg.get('dragon_enable', False):
        return

    dragon_candidates = get_dragon_stock_list_A(context)
    g.dragon_pool_size = len(dragon_candidates)
    g.dragon_candidates_today = dragon_candidates[:12]
    g.dragon_mode = bool(dragon_candidates)
    g.dragon_signal_reason = 'bigmeat_dragon_pool' if dragon_candidates else 'empty'
    log.info(
        "BIGMEAT_POOL|count={}|top_score={:.4f}|market_trend={}".format(
            g.dragon_pool_size,
            dragon_candidates[0].get('dragon_score', 0.0) if dragon_candidates else 0.0,
            getattr(g, 'market_trend', 'sideways')
        )
    )
    if not dragon_candidates:
        return

    top_n = int(g.cfg.get('bigmeat_pool_log_top_n', 3) or 3)
    if g.cfg.get('bigmeat_verbose_pool_log', False):
        top_n = len(dragon_candidates)
    for i, item in enumerate(dragon_candidates[:top_n]):
        stock = item.get('stock', '?')
        log.info(
            "BIGMEAT_POOL_TOP|rank={}|stock={}|name={}|score={:.4f}|"
            "tpl={}|open_ratio={:.2f}%|close_to_high={:.4f}|"
            "auc_ratio={:.4f}".format(
                i + 1, stock, get_stock_name_cached(stock),
                item.get('dragon_score', 0.0), item.get('tpl', ''),
                item.get('open_ratio', 0.0) * 100,
                item.get('close_to_high', 0.0),
                item.get('auction_ratio', 0.0)
            )
        )

    scores = [x.get('dragon_score', 0.0) for x in dragon_candidates[:3]]
    g.dragon_top_score = scores[0] if scores else 0.0
    top2_avg = float(np.mean(scores[:2])) if len(scores) >= 2 else g.dragon_top_score

    strong_single  = g.dragon_top_score >= g.cfg['dragon_strong_single_score']
    cluster_follow = len(scores) >= 2 and top2_avg >= g.cfg['dragon_cluster_top2_avg']
    concentrated   = g.dragon_top_score >= g.cfg['dragon_top_score_trigger']

    if strong_single or cluster_follow or concentrated:
        g.dragon_mode = True

    if g.diag.get('risk_panic_yesterday', 0) == 1 \
            and g.dragon_top_score >= g.cfg['dragon_panic_override_score']:
        g.diag['dragon_panic_override'] = 1


# =========================================================
# A 选股（不变，保持原有触发逻辑）
# =========================================================


# [V1.1.0] 趋势过滤 + 评分仓位调节(替代旧的一票否决)
def score_candidates_A(context, candidates, mode='dragon', pos_ratio=None):
    """BigMeat评分：仅Dragon + deep_water，按dragon_score降序。"""
    current_data = get_current_data()
    if candidates and hasattr(current_data, 'get_batch'):
        try:
            current_data.get_batch([item['stock'] for item in candidates])
        except Exception:
            pass

    eligible = []
    cfg_a = g.strategies['A']['config']
    min_score = cfg_a.get('dragon_min_score', 0.70)
    min_open = cfg_a.get('dragon_min_open_ratio', 0.015)
    max_open = cfg_a.get('dragon_max_open_ratio', 0.055)
    filter_counts = {
        'not_deep_water': 0,
        'score_below_0.70': 0,
        'open_ratio_out_of_range': 0,
        'stock_trend_down': 0,
        'market_down_block': 0,
    }

    for item in candidates:
        stock = item.get('stock', '')
        if item.get('entry_type') != 'dragon_follow':
            continue

        if getattr(g, 'market_trend', 'sideways') == 'down':
            filter_counts['market_down_block'] += 1
            continue

        if item.get('tpl') != 'deep_water':
            filter_counts['not_deep_water'] += 1
            continue

        dragon_score = float(item.get('dragon_score', 0.0) or 0.0)
        if dragon_score < min_score:
            filter_counts['score_below_0.70'] += 1
            continue

        try:
            cd_item = current_data[stock]
            curr_price = float(cd_item.last_price or 0)
            if curr_price <= 0:
                continue
            high_limit = float(cd_item.high_limit or 0)
            if high_limit > 0 and curr_price >= high_limit * g.cfg['A_limit_up_buffer']:
                continue

            h = attribute_history(stock, 2, '1d', ['close'])
            if h is None or len(h) < 1:
                continue
            prev_close = float(h['close'].iloc[-1])
            day_open = float(cd_item.day_open or 0)
            if prev_close <= 0 or day_open <= 0:
                continue
            open_ratio = day_open / prev_close - 1
        except Exception as e:
            log.warning(
                "BIGMEAT_SCORE_ERROR|stock={}|name={}|error={}".format(
                    stock, get_stock_name_cached(stock), e
                )
            )
            continue

        if open_ratio < min_open or open_ratio > max_open:
            filter_counts['open_ratio_out_of_range'] += 1
            continue

        if not is_stock_uptrend(stock, context):
            filter_counts['stock_trend_down'] += 1
            continue

        eligible.append({
            'stock': stock,
            'entry_type': 'dragon_follow',
            'tpl': 'deep_water',
            'dragon_score': dragon_score,
            'score': dragon_score,
            'open_ratio': open_ratio,
            'curr_price': curr_price,
            'auction_price': item.get('auction_price', 0),
        })

    eligible.sort(key=lambda x: x['dragon_score'], reverse=True)
    top_ratios = (
        cfg_a.get('top1_pos_ratio', 0.35),
        cfg_a.get('top2_pos_ratio', 0.25),
    )
    ranked = []
    for index, item in enumerate(eligible[:2]):
        item['rank'] = index + 1
        item['pos_ratio'] = top_ratios[index]
        ranked.append(item)
    if any(v > 0 for v in filter_counts.values()):
        log.info(
            "BIGMEAT_FILTER_SUMMARY|not_deep_water={}|score_below_0.70={}|"
            "open_ratio_out_of_range={}|stock_trend_down={}|"
            "market_down_block={}".format(
                filter_counts['not_deep_water'],
                filter_counts['score_below_0.70'],
                filter_counts['open_ratio_out_of_range'],
                filter_counts['stock_trend_down'],
                filter_counts['market_down_block'],
            )
        )
    return ranked



def get_base_stock_universe(context, include_new=False):
    if not hasattr(g, 'security_start_date_cache'):
        g.security_start_date_cache = {}
    try:
        all_sec = get_all_securities('stock', context.previous_date)
        if all_sec is None or all_sec.empty:
            log.warning("UNIVERSE_EMPTY|reason=get_all_securities_empty")
            return []
        initial_list = all_sec.index.tolist()
    except Exception as e:
        log.warning("UNIVERSE_ERROR|stage=get_all_securities|error={}".format(e))
        return []

    # 前缀过滤(纯字符串操作, 无需API)
    exclude_pf = g.cfg['exclude_prefixes']
    initial_list = [s for s in initial_list if not s.startswith(exclude_pf)]

    curr_data = get_current_data()
    # [P-3] 批量预取tick, 避免逐只触发get_full_tick RPC
    if hasattr(curr_data, 'get_batch'):
        try:
            curr_data.get_batch(initial_list)
        except Exception:
            pass  # 降级为逐只, 不中断

    # ST/停牌/退市过滤
    filtered = []
    valid_tick_count = 0
    for s in initial_list:
        try:
            cd_item = curr_data[s]
            if cd_item.last_price > 0:
                valid_tick_count += 1
            if cd_item.is_st or cd_item.paused or '退' in cd_item.name:
                continue
            filtered.append(s)
        except Exception:
            continue

    # 全部实时价格为空时保留一条摘要告警。
    if len(initial_list) > 100 and valid_tick_count == 0:
        log.warning(
            "UNIVERSE_ERROR|stage=current_data|reason=all_prices_invalid|count={}".format(
                len(initial_list)
            )
        )

    if not include_new:
        cutoff_date = (
            context.current_dt.date()
            - datetime.timedelta(days=g.cfg['new_stock_days'])
        )
        new_filtered = []
        for s in filtered:
            try:
                if s in g.security_start_date_cache:
                    start_date = g.security_start_date_cache[s]
                else:
                    start_date = None
                    if 'start_date' in all_sec.columns:
                        start_date = all_sec.at[s, 'start_date']
                        if pd.isna(start_date):
                            start_date = None
                        elif hasattr(start_date, 'date'):
                            start_date = start_date.date()
                    if start_date is None:
                        start_date = get_security_static_info_cached(s).get(
                            'start_date'
                        )
                    g.security_start_date_cache[s] = start_date
                if start_date and start_date < cutoff_date:
                    new_filtered.append(s)
            except Exception:
                continue
        filtered = new_filtered
    return filtered


def reset_daily_diag(context):
    g.diag = {
        'unknown_positions': 0,
        'pending_exit_positions': 0,
        'pending_buy_positions': 0,
        'retry_pending_exit': 0,
        'portfolio_dd': 0.0,
        'portfolio_peak_nav': 1.0,
        'A_pause_days_left': 0,
        'A_dd_cooldown_active': 0,
        'A_dd_rearm_ready': 0,
        'A_rearm_level_hit': 0,
        'A_deadlock_scout_mode': 0,
        'A_dragon_mode': 0,
        'A_rearm_grace_days_left': 0,
        'A_flat_days': 0,
        'dragon_mode': 0,
        'dragon_pool_size': 0,
        'dragon_top_score': 0.0,
        'dragon_score_ema': 0.0,
        'dragon_panic_override': 0,
        'dragon_signal_reason': 'none',
        'crowding_confirm_days': 0,
        'crowding_signal_raw': 0,
        'crowding_consecutive_days': 0,
        'crowding_cooldown_left': 0,
        'A_skip_pause': 0,
        'A_skip_rearm': 0,
        'A_sell_half': 0,
        'A_sell_all': 0,
        'A_buys_orders': 0,
        'bigmeat_mode': 1,
        'dragon_buy_orders': 0,
        'dragon_add_orders': 0,
        'livermore_add_confirmed': 0,
        'livermore_add_cancelled': 0,
        'dragon_sell_orders': 0,
        'dragon_stop_warnings': 0,
        'partial_sell_confirmed': 0,
        'stage_change_confirmed': 0,
        'dragon_pause_triggered': 0,
        'intraday_panic': 0,
        'intraday_pos_cap': 0,
        'risk_panic_yesterday': 0,
        'orphan_sell': 0,
        'regime': 'neutral',
        'micro_regime': 'neutral_trend',
        'market_trend': 'sideways',
        'no_new': 0,
        'regime_secondary': 'neutral',
        'regime_dual_override': 0,
        'dragon_circuit_breaker_active': 0,
        'dragon_bear_freq_limit': 0,
        'dragon_consecutive_losses': 0,
        'dragon_soft_losses': 0,
        'dragon_cb_pause_left': 0,
        'dragon_bear_weekly_count': 0,
    }


# --- Migrated core functions ---

def morning_prepare(context):
    try:
        _morning_prepare_impl(context)
    except Exception as e:
        log.error("TASK_ERROR|task=morning_prepare|error={}".format(e))

def _morning_prepare_impl(context):
    if g.bt['start_cash'] is None:
        g.bt['start_cash'] = context.portfolio.total_value
        g.bt['start_date'] = str(context.current_dt.date())

    g.daily_new_position_count = 0
    g.no_new_position_today = False
    g.ma5_base_cache = {}
    g.ma5_base_cache_date = context.current_dt.date()

    g.panic_yesterday_ret = 0.0

    g.dragon_mode = False
    g.dragon_pool_size = 0
    g.dragon_top_score = 0.0
    g.dragon_candidates_today = []
    g.dragon_signal_reason = 'none'
    g.dragon_evaluated_today = False
    g.shadow_confirmed_today = set()
    g.shadow_satellite_submitted_today = set()

    # 先同步成交状态，再恢复无法归属的历史持仓。
    reset_daily_diag(context)
    reset_shadow_daily_stats(context)
    sync_position_meta_with_real_positions(context)

    # 恢复未知持仓
    for stock in context.portfolio.positions:
        if context.portfolio.positions[stock].total_amount <= 0:
            continue
        meta = g.positions_meta.get(stock, {})
        if not meta:
            g.positions_meta[stock] = {
                'strategy': 'unknown', 'entry_type': 'orphan',
                'stage': 'full', 'pending_exit': False,
            }
            log.warning(
                "POSITION_RECOVER|stock={}|name={}|strategy=unknown|"
                "entry_type=orphan".format(stock, get_stock_name_cached(stock))
            )

    # [LOG OPT] Reset intraday failfast tracking for a new trading day
    for stock in list(g.positions_meta.keys()):
        meta = g.positions_meta.get(stock)
        if meta:
            meta.pop('_prev_failfast_reason', None)

    if g.A_rearm_grace_days_left > 0:
        g.A_rearm_grace_days_left -= 1

    # [P0-FIX-1] crowding 冷却倒计时
    if g.crowding_cooldown_left > 0:
        g.crowding_cooldown_left -= 1

    # [OPT-1] Dragon 断路器冷却倒计时
    if g.dragon_circuit_breaker_pause_left > 0:
        if getattr(g, 'dragon_pause_just_triggered', False):
            # 平仓结果在今早同步时刚触发，今天是暂停第1天，不立即扣减。
            g.dragon_pause_just_triggered = False
        else:
            g.dragon_circuit_breaker_pause_left -= 1
        if g.dragon_circuit_breaker_pause_left == 0:
            g.dragon_consecutive_losses = 0
            g.dragon_soft_losses = 0
            g.dragon_loss_history = []
            g.dragon_reduced_pos_active = False
            log.info(
                "DRAGON_PAUSE|stock=ALL|name=ALL|dragon_consecutive_losses=0|dragon_pause_days_left=0|"
                "pause_released=1"
            )
        else:
            log.info(
                "DRAGON_PAUSE|stock=ALL|name=ALL|dragon_consecutive_losses={}|dragon_pause_days_left={}|"
                "pause_released=0".format(
                    g.dragon_consecutive_losses, g.dragon_circuit_breaker_pause_left
                )
            )

    # [OPT-3] Bear Dragon 周频率计数重置
    if g.dragon_bear_weekly_reset_countdown > 0:
        g.dragon_bear_weekly_reset_countdown -= 1
        if g.dragon_bear_weekly_reset_countdown == 0:
            g.dragon_bear_weekly_count = 0

    check_orphan_positions(context)

    update_market_regime(context)
    g.market_trend = get_market_trend(context)       # [V1.1.0] 大盘趋势判断
    g.intraday_panic_active = False                  # 重置盘中恐慌标记
    update_daily_risk_switch_yesterday(context)
    update_micro_regime_without_dragon(context)
    refresh_strategy_budget()
    update_portfolio_nav_and_brake(context)

    g.diag['regime'] = g.market_regime
    g.diag['micro_regime'] = g.micro_regime
    g.diag['market_trend'] = g.market_trend
    g.diag['no_new'] = 0  # [V1.1.0] 不再全面禁买

def post_auction_prepare(context):
    try:
        _post_auction_prepare_impl(context)
    except Exception as e:
        log.error("TASK_ERROR|task=post_auction_prepare|error={}".format(e))

def _post_auction_prepare_impl(context):
    update_dragon_mode(context)
    update_micro_regime(context)
    refresh_strategy_budget()
    g.dragon_evaluated_today = True

    g.diag['dragon_mode'] = 1 if g.dragon_mode else 0
    g.diag['dragon_pool_size'] = g.dragon_pool_size
    g.diag['dragon_top_score'] = g.dragon_top_score
    g.diag['micro_regime'] = g.micro_regime

    log.info("FAST_MODE|skip_auction_score_jq=1")

def after_market_close(context):
    try:
        _after_market_close_impl(context)
    except Exception as e:
        log.error("TASK_ERROR|task=after_market_close|error={}".format(e))


def _after_market_close_impl(context):
    # 收盘后先同步成交：确认真实加仓，或清理当天未成交/被取消的加仓单。
    sync_position_meta_with_real_positions(context)

    if g.bt['start_cash']:
        previous_nav = (
            g.bt['nav_history'][-1] if g.bt['nav_history'] else 1.0
        )
        nav = context.portfolio.total_value / g.bt['start_cash']
        if nav > g.bt['peak_nav']:
            g.bt['peak_nav'] = nav
        current_dd = (
            nav / g.bt['peak_nav'] - 1 if g.bt['peak_nav'] > 0 else 0.0
        )
        g.bt['current_dd'] = current_dd
        g.bt['max_drawdown'] = min(g.bt['max_drawdown'], current_dd)
        g.bt['trade_days'] += 1
        g.bt['nav_history'].append(nav)
        daily_ret = nav / previous_nav - 1 if previous_nav > 0 else 0.0

        decisive_trades = g.bt['wins'] + g.bt['losses']
        win_rate = g.bt['wins'] / decisive_trades if decisive_trades > 0 else 0.0
        avg_win  = g.bt['win_ret_sum'] / g.bt['wins']   if g.bt['wins']   > 0 else 0.0
        avg_loss = g.bt['loss_ret_sum'] / g.bt['losses'] if g.bt['losses'] > 0 else 0.0
        payoff = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

        log.info(
            "DAILY_SUMMARY|date={}|nav={:.4f}|daily_ret={:.2f}%|"
            "max_drawdown={:.2f}%|positions={}|closed_trades={}|"
            "win_rate={:.1f}%|payoff={:.2f}".format(
                context.current_dt.date(), nav, daily_ret * 100,
                abs(g.bt['max_drawdown']) * 100,
                len(context.portfolio.positions), g.bt['closed_trades'],
                win_rate * 100, payoff
            )
        )

    current_data = get_current_data()
    position_log_interval = max(
        int(g.cfg.get('position_log_interval_days', 5) or 5), 1
    )
    regular_position_log_day = (
        int(g.bt.get('trade_days', 0) or 0) % position_log_interval == 0
    )
    for stock, pos in context.portfolio.positions.items():
        meta = g.positions_meta.get(stock, {})
        needs_position_diagnostic = (
            meta.get('pending_exit', False)
            or bool(meta.get('pending_stage_change'))
            or int(meta.get('accounting_error', 0) or 0) == 1
        )
        if not regular_position_log_day and not needs_position_diagnostic:
            continue
        cost = float(getattr(pos, 'avg_cost', 0) or 0)
        try:
            price = float(current_data[stock].last_price or 0)
        except Exception:
            price = float(
                getattr(pos, 'price', 0)
                or getattr(pos, 'last_sale_price', 0)
                or 0
            )
        pnl = price / cost - 1 if cost > 0 and price > 0 else 0.0
        amount = float(getattr(pos, 'total_amount', 0) or 0)
        log.info(
            "POSITION|stock={}|name={}|entry_type={}|amount={:.0f}|"
            "cost={:.3f}|price={:.3f}|pnl={:.2f}%|stage={}".format(
                stock, get_stock_name_cached(stock),
                meta.get('entry_type', 'unknown'), amount, cost, price,
                pnl * 100, meta.get('stage', 'unknown')
            )
        )

    shadow_after_market_update(context)

    log.info(
        "DIAG|exp={}|regime={}|micro={}|trend={}|"
        "A_flat={}|A_pause={}|A_cooldown={}|A_rearm={}|A_grace={}|"
        "A_dragon={}|"
        "dragon={}|pool={}|score={:.3f}|ema={:.3f}|"
        "A_buys={}|A_sell={}|add_ok={}|add_cancel={}|"
        "partial_ok={}|stage_ok={}|pause_count={}|"
        "intraday_panic={}|pos_cap={}|unknown={}|pending_exit={}|"
        "reg2={}|dual_ovr={}|dcb={}/{}|bear_wk={}".format(
            EXPERIMENT_NAME,
            g.diag.get('regime', 'N'),
            g.diag.get('micro_regime', 'N'),
            g.diag.get('market_trend', 'N'),
            g.diag.get('A_flat_days', 0),
            g.diag.get('A_pause_days_left', 0),
            g.diag.get('A_dd_cooldown_active', 0),
            g.diag.get('A_dd_rearm_ready', 0),
            g.diag.get('A_rearm_grace_days_left', 0),
            g.diag.get('A_dragon_mode', 0),
            g.diag.get('dragon_mode', 0),
            g.diag.get('dragon_pool_size', 0),
            g.diag.get('dragon_top_score', 0.0),
            g.diag.get('dragon_score_ema', 0.0),
            g.diag.get('A_buys_orders', 0),
            g.diag.get('A_sell_all', 0),
            g.diag.get('livermore_add_confirmed', 0),
            g.diag.get('livermore_add_cancelled', 0),
            g.diag.get('partial_sell_confirmed', 0),
            g.diag.get('stage_change_confirmed', 0),
            g.diag.get('dragon_pause_triggered', 0),
            g.diag.get('intraday_panic', 0),
            g.diag.get('intraday_pos_cap', 0),
            g.diag.get('unknown_positions', 0),
            g.diag.get('pending_exit_positions', 0),
            g.diag.get('regime_secondary', 'N'),
            g.diag.get('regime_dual_override', 0),
            g.dragon_consecutive_losses,
            g.dragon_circuit_breaker_pause_left,
            g.dragon_bear_weekly_count,
        )
    )

def finalize_exited_position(stock, meta):
    if not meta.get('pending_exit', False):
        return
    _ensure_trade_accounting_fields(meta)
    exit_date = meta.get('last_exit_date')
    entry_type = meta.get('entry_type', '')
    strategy = meta.get('strategy', '')
    if exit_date is not None:
        if entry_type == 'dragon_follow':
            g.cooldown[stock] = (exit_date, 'dragon')
        else:
            g.cooldown[stock] = (exit_date, 'normal')
    ret_snapshot = meta.get('pending_exit_ret_snapshot')
    requested_amount = float(meta.get('pending_exit_requested_amount', 0) or 0)
    amount_before = float(meta.get('pending_exit_amount_before', 0) or 0)
    closeable_before = float(
        meta.get('pending_exit_closeable_amount_before', 0) or 0
    )
    if requested_amount > 0:
        exit_amount = requested_amount
    elif amount_before > 0:
        exit_amount = amount_before
    elif closeable_before > 0:
        exit_amount = closeable_before
    else:
        exit_amount = float(meta.get('last_amount', 0) or 0)
    if exit_amount <= 0:
        exit_amount = float(meta.get('entry_amount', 0) or 0)
    exit_price = meta.get('pending_exit_sell_price')
    if exit_price is None:
        exit_cost = float(meta.get('pending_exit_cost_price', 0) or 0)
        exit_price = (
            exit_cost * (1.0 + float(ret_snapshot))
            if ret_snapshot is not None else exit_cost
        )
    if exit_amount <= 0 or float(exit_price or 0) <= 0:
        log.warning(
            "TRADE_CLOSE_SKIP|stock={}|name={}|reason=invalid_exit_snapshot|"
            "exit_amount={}|exit_price={}".format(
                stock, get_stock_name_cached(stock), exit_amount, exit_price
            )
        )
        return

    if meta.get('pending_add') and exit_amount > 0:
        exit_cost = float(meta.get('pending_exit_cost_price', 0) or 0)
        sync_dt = datetime.datetime.combine(
            exit_date or datetime.date.today(), datetime.time(15, 10)
        )
        _sync_pending_livermore_add(
            stock, meta, exit_amount, exit_cost, sync_dt
        )

    final_sell_amount = exit_amount
    final_sell_value = float(exit_price or 0) * final_sell_amount
    exit_cost = float(meta.get('pending_exit_cost_price', 0) or 0)
    final_pnl_value = final_sell_value - exit_cost * final_sell_amount
    buy_amount_accum = float(meta.get('buy_amount_accum', 0.0) or 0.0)
    sell_amount_accum = float(meta.get('sell_amount_accum', 0.0) or 0.0)
    sell_value_accum = float(meta.get('sell_value_accum', 0.0) or 0.0)
    total_sell_value = sell_value_accum + final_sell_value
    total_buy_value = float(meta.get('total_buy_value', 0.0) or 0.0)
    realized_pnl_value = total_sell_value - total_buy_value
    meta['total_sell_value'] = total_sell_value
    meta['realized_pnl_value'] = realized_pnl_value

    partial_records = [
        record for record in meta.get('partial_sell_records', [])
        if record.get('type', 'partial') != 'final'
    ]
    accounting_reasons = []
    amount_tolerance = max(0.5, buy_amount_accum * 0.001)
    accounted_sell_amount = sell_amount_accum + final_sell_amount
    if buy_amount_accum <= 0:
        accounting_reasons.append('buy_amount_missing')
    elif accounted_sell_amount + amount_tolerance < buy_amount_accum:
        accounting_reasons.append('sell_amount_short')
    elif accounted_sell_amount > buy_amount_accum + amount_tolerance:
        accounting_reasons.append('sell_amount_exceeds_buy')
    if total_buy_value <= 0:
        accounting_reasons.append('total_buy_value_missing')
    elif total_sell_value <= 0 or total_sell_value < total_buy_value * 0.50:
        accounting_reasons.append('total_sell_value_abnormally_low')
    if partial_records and sell_value_accum <= 0:
        accounting_reasons.append('partial_records_without_sell_value')
    if meta.get('stage') in ('half', 'half_final') and not partial_records:
        accounting_reasons.append('half_stage_without_partial_record')
    if int(meta.get('accounting_error', 0) or 0):
        accounting_reasons.append('prior_accounting_error')

    accounting_error = int(bool(accounting_reasons))
    meta['accounting_error'] = accounting_error
    if accounting_error:
        log.warning(
            "TRADE_ACCOUNTING_WARN|stock={}|name={}|reasons={}|"
            "buy_amount_accum={:.0f}|sell_amount_accum={:.0f}|"
            "final_sell_amount={:.0f}|sell_value_accum={:.2f}|"
            "final_sell_value={:.2f}|total_buy_value={:.2f}|"
            "total_sell_value={:.2f}".format(
                stock, get_stock_name_cached(stock),
                ','.join(accounting_reasons),
                buy_amount_accum, sell_amount_accum, final_sell_amount,
                sell_value_accum, final_sell_value,
                total_buy_value, total_sell_value
            )
        )

    meta.setdefault('partial_sell_records', []).append({
        'date': str(exit_date or ''),
        'type': 'final',
        'amount': final_sell_amount,
        'sell_value': final_sell_value,
        'pnl_value': final_pnl_value,
        'reason': meta.get('last_exit_reason', ''),
        'source': 'estimated',
    })

    if total_buy_value > 0:
        final_trade_ret = realized_pnl_value / total_buy_value
    elif ret_snapshot is not None:
        final_trade_ret = float(ret_snapshot)
    else:
        return

    if not accounting_error:
        record_closed_trade(final_trade_ret)
    _hold_days = (exit_date - meta['buy_date']).days \
        if meta.get('buy_date') and exit_date else '?'
    log.info(
        "TRADE_CLOSE|stock={}|name={}|entry_type={}|trade_ret={:.2f}%|"
        "buy_amount_accum={:.0f}|sell_amount_accum={:.0f}|"
        "final_sell_amount={:.0f}|sell_value_accum={:.2f}|"
        "final_sell_value={:.2f}|total_sell_value={:.2f}|"
        "total_buy_value={:.2f}|realized_pnl_value={:.2f}|"
        "accounting_error={}|hold_days={}|win={}".format(
            stock, get_stock_name_cached(stock), entry_type,
            final_trade_ret * 100,
            buy_amount_accum, sell_amount_accum, final_sell_amount,
            sell_value_accum, final_sell_value, total_sell_value,
            total_buy_value, realized_pnl_value, accounting_error,
            _hold_days, int(final_trade_ret > 0 and not accounting_error)
        )
    )

    hold_days_value = _hold_days if isinstance(_hold_days, int) else -1
    log.info(
        "EXIT_OUTCOME_LOG|stock={}|name={}|entry_date={}|exit_date={}|"
        "exit_reason={}|pnl_pct={:.2f}%|pnl_val={:.2f}|hold_days={}|"
        "is_fast_loss={}|is_big_meat_10={}|is_super_meat_20={}|"
        "entry_type={}|slot_type={}|stage={}".format(
            stock, get_stock_name_cached(stock),
            meta.get('buy_date'), exit_date,
            meta.get('last_exit_reason', ''),
            final_trade_ret * 100, realized_pnl_value,
            _hold_days,
            int(final_trade_ret < 0 and hold_days_value >= 0 and hold_days_value <= 5),
            int(final_trade_ret >= 0.10),
            int(final_trade_ret >= 0.20),
            meta.get('entry_type', ''),
            meta.get('slot_type', ''),
            meta.get('stage', '')
        )
    )

    # 只有整笔硬亏损计入连续亏损；轻微负收益只累计soft loss。
    if entry_type == 'dragon_follow' and strategy == 'A':
        final_reason = meta.get('last_exit_reason', '')
        if accounting_error:
            log.warning(
                "DRAGON_LOSS_CLASSIFY_SKIP|stock={}|name={}|"
                "reason=accounting_error|trade_ret={:.2f}%|"
                "final_reason={}|accounting_error=1".format(
                    stock, get_stock_name_cached(stock),
                    final_trade_ret * 100, final_reason
                )
            )
            return
        hard_loss = (
            final_trade_ret < 0
            and (
                final_trade_ret <= -0.015
                or final_reason in ('dragon_confirm_stop', 'dragon_delayed_stop')
            )
        )
        pause_triggered = False
        if hard_loss:
            g.dragon_consecutive_losses += 1
            g.dragon_loss_history.append(abs(final_trade_ret))
        elif final_trade_ret < 0:
            g.dragon_soft_losses += 1
        elif final_trade_ret > 0:
            g.dragon_consecutive_losses = 0
            g.dragon_soft_losses = 0
            g.dragon_loss_history = []
            g.dragon_reduced_pos_active = False

        pause_after = g.cfg.get('dragon_loss_pause_after', 2)
        pause_days = g.cfg.get('dragon_loss_pause_days', 2)
        if (hard_loss and g.dragon_consecutive_losses >= pause_after
                and g.dragon_circuit_breaker_pause_left == 0):
            g.dragon_circuit_breaker_pause_left = pause_days
            g.dragon_pause_just_triggered = True
            pause_triggered = True
            diag_add('dragon_pause_triggered')

        log.info(
            "DRAGON_LOSS_CLASSIFY|stock={}|name={}|trade_ret={:.2f}%|final_reason={}|"
            "hard_loss={}|soft_loss_count={}|consecutive_losses={}".format(
                stock, get_stock_name_cached(stock), final_trade_ret * 100,
                final_reason, int(hard_loss),
                g.dragon_soft_losses, g.dragon_consecutive_losses
            )
        )
        if pause_triggered:
            log.info(
                "DRAGON_PAUSE|stock={}|name={}|dragon_consecutive_losses={}|"
                "dragon_pause_days_left={}|pause_triggered=1|pause_released=0|"
                "ret={:.2f}%".format(
                    stock, get_stock_name_cached(stock),
                    g.dragon_consecutive_losses,
                    g.dragon_circuit_breaker_pause_left,
                    final_trade_ret * 100
                )
            )

def mark_pending_buy(stock, strategy, entry_type, stage, context, item=None):
    item = item or {}
    buy_date = context.current_dt.date()
    g.pending_buys[stock] = {
        'strategy': strategy,
        'entry_type': entry_type,
        'tpl': item.get('tpl', ''),
        'rank': item.get('rank', 0),
        'pos_ratio': item.get('pos_ratio', 0.0),
        'entry_value': item.get('entry_value', 0.0),
        'buy_date': buy_date,
        'livermore_added': False,
        'winner_added': False,
        'stop_warning': False,
        'stage': stage,
        'create_date': buy_date,
        'slot_type': item.get(
            'slot_type',
            'core' if entry_type == 'dragon_follow' else ''
        ),
        'strategy_tag': item.get(
            'strategy_tag',
            'original_core' if entry_type == 'dragon_follow' else ''
        ),
        'entry_rule': item.get('entry_rule', ''),
        'signal_date': item.get('signal_date'),
        'confirm_date': item.get('confirm_date'),
        'entry_price': item.get('entry_price'),
        'satellite_slot_ratio': item.get('satellite_slot_ratio', 0.0),
        'max_hold_days': item.get('max_hold_days', 0),
    }

def submit_exit_order(stock, context, reason='', ret_snapshot=None):
    """提交清仓委托，并保存整笔交易结算快照。"""
    pos = context.portfolio.positions.get(stock)
    if pos and pos.closeable_amount <= 0:
        log.warning(
            "EXIT_SKIP|stock={}|name={}|reason=closeable_zero|"
            "sell_reason={}".format(
                stock, get_stock_name_cached(stock), reason
            )
        )
        return False

    exit_amount_before = float(getattr(pos, 'total_amount', 0) or 0) if pos else 0.0
    exit_closeable_before = (
        float(getattr(pos, 'closeable_amount', 0) or 0) if pos else 0.0
    )
    exit_requested_amount = (
        min(exit_amount_before, exit_closeable_before)
        if exit_closeable_before > 0 else exit_amount_before
    )
    exit_cost = float(getattr(pos, 'avg_cost', 0) or 0) if pos else 0.0
    exit_price = (
        exit_cost * (1.0 + float(ret_snapshot))
        if ret_snapshot is not None else exit_cost
    )

    od = order_target_value(stock, 0)
    if od is None:
        return False
    meta = g.positions_meta.setdefault(stock, {})
    _ensure_trade_accounting_fields(meta, pos)
    meta['pending_exit'] = True
    meta['last_exit_date'] = context.current_dt.date()
    meta['last_exit_reason'] = reason
    meta['pending_exit_ret_snapshot'] = ret_snapshot
    if pos is not None:
        meta['pending_exit_amount_before'] = exit_amount_before
        meta['pending_exit_closeable_amount_before'] = exit_closeable_before
        meta['pending_exit_requested_amount'] = exit_requested_amount
        meta['pending_exit_sell_price'] = exit_price
        meta['pending_exit_cost_price'] = exit_cost
    # [CQTO修复] 兼容层返回int(order_id), 不是带.order_id属性的对象
    meta['exit_order_id'] = od if isinstance(od, int) else getattr(od, 'order_id', None)
    return True

def submit_partial_stage_change(
        stock, amount, next_stage, context, reason='', ret_snapshot=None):
    # 安全检查: 聚宽要求可平仓≤100时必须一次性平仓
    pos = context.portfolio.positions.get(stock)
    if pos and pos.closeable_amount > 0:
        remaining = pos.closeable_amount - amount
        if remaining > 0 and remaining < 100:
            # 剩余不足100股，改为全部卖出
            old_amount = amount
            amount = pos.closeable_amount
            log.info(
                "PARTIAL_SELL_ADJUST|stock={}|name={}|reason=lot_rounding|"
                "old_amount={}|remaining={}|new_amount={}".format(
                    stock, get_stock_name_cached(stock), old_amount,
                    remaining, amount
                )
            )
    requested_amount = float(amount or 0)
    amount_before = (
        float(getattr(pos, 'total_amount', 0) or 0)
        if pos is not None else 0.0
    )
    od = order(stock, -amount)
    if od is None:
        return False
    meta = g.positions_meta.setdefault(stock, {})
    _ensure_trade_accounting_fields(meta, pos)
    meta['pending_stage_change'] = next_stage
    meta['pending_stage_change_date'] = context.current_dt.date()
    meta['pending_stage_change_reason'] = reason
    meta['pending_partial_ret_snapshot'] = ret_snapshot
    meta['pending_partial_requested_amount'] = requested_amount
    meta['pending_partial_position_amount_before'] = amount_before
    meta['pending_partial_filled_amount'] = 0
    cost_price = float(getattr(pos, 'avg_cost', 0) or 0) if pos is not None else 0.0
    meta['pending_partial_cost_price'] = cost_price
    sell_price = (
        cost_price * (1.0 + float(ret_snapshot))
        if ret_snapshot is not None else cost_price
    )
    if sell_price <= 0:
        try:
            sell_price = float(get_current_data()[stock].last_price or 0)
        except Exception:
            sell_price = float(
                getattr(pos, 'price', 0)
                or getattr(pos, 'last_sale_price', 0)
                or 0
            ) if pos is not None else 0.0
    partial_order_id = (
        od if isinstance(od, int)
        else (
            getattr(od, 'order_id', None)
            or getattr(od, 'id', None)
        )
    )
    order_amounts = _extract_partial_order_amounts(
        od, requested_amount, amount_before
    )
    actual_order_amount = float(
        order_amounts.get('actual_filled_amount') or 0
    )
    adjusted_order_amount = float(
        order_amounts.get('adjusted_order_amount') or 0
    )
    lot_adjusted_amount = _get_lot_adjusted_partial_amount(
        requested_amount, amount_before
    )
    expected_amount = adjusted_order_amount or lot_adjusted_amount
    unique_key = _build_partial_sell_unique_key(
        stock, requested_amount, reason, context.current_dt, partial_order_id
    )
    meta['pending_partial_sell_price'] = sell_price
    meta['pending_partial_price_source'] = 'estimated'
    meta['pending_partial_actual_order_amount'] = actual_order_amount
    meta['pending_partial_lot_adjusted_amount'] = lot_adjusted_amount
    meta['pending_partial_expected_amount'] = expected_amount
    meta['pending_partial_expected_after_amount'] = max(
        amount_before - expected_amount, 0.0
    ) if expected_amount > 0 else None
    meta['pending_partial_unique_key'] = unique_key
    meta['partial_order_id'] = partial_order_id
    if actual_order_amount > 0:
        try:
            _record_partial_sell_accounting(
                meta, stock, actual_order_amount, sell_price,
                cost_price, reason, context.current_dt,
                partial_order_id, unique_key,
                order_amounts.get('actual_source') or 'order_actual',
                requested_amount=requested_amount,
                previous_amount=amount_before,
                current_amount=max(
                    amount_before - actual_order_amount, 0.0
                ),
            )
        except Exception as e:
            meta['accounting_error'] = 1
            log.warning(
                "TRADE_ACCOUNTING_WARN|stock={}|name={}|"
                "reason=partial_submit_record_failed|error={}".format(
                    stock, get_stock_name_cached(stock), e
                )
            )
    return True

# --- Missing utility functions from v5.9.0 ---


def get_open_slot_hold_count(context, strategy_name):
    return sum([
        1 for stock in context.portfolio.positions.keys()
        if g.positions_meta.get(stock, {}).get('strategy') == strategy_name
    ])

def get_global_slots_left(context):
    max_pos = g.cfg.get('max_total_positions', 2)
    return max(0, max_pos - get_total_slot_hold_count(context))


# =========================================================
# B 仓位回撤追踪
# =========================================================

def in_cooldown(stock, context):
    if stock not in g.cooldown:
        return False
    cooldown_info = g.cooldown[stock]
    today = context.current_dt.date()

    # [P2-FIX-2] 兼容新旧格式
    if isinstance(cooldown_info, tuple):
        sell_date, cd_type = cooldown_info
        if cd_type == 'dragon':
            cd_days = g.cfg.get('cooldown_days_after_sell_dragon', 4)
        else:
            cd_days = g.cfg['cooldown_days_after_sell']
    else:
        sell_date = cooldown_info
        cd_days = g.cfg['cooldown_days_after_sell']

    if sell_date >= today:
        return True
    try:
        trade_days_between = get_trade_days(start_date=sell_date, end_date=today)
        elapsed = max(0, len(trade_days_between) - 1)
        return elapsed < cd_days
    except Exception:
        return (today - sell_date).days < cd_days

def can_open_position(context, curr_price):
    return curr_price > 0 \
           and context.portfolio.available_cash >= curr_price * 100 * 1.002

def record_closed_trade(ret):
    g.bt['closed_trades'] += 1
    if ret > 0:
        g.bt['wins'] += 1
        g.bt['win_ret_sum'] += ret
    elif ret < 0:
        g.bt['losses'] += 1
        g.bt['loss_ret_sum'] += ret
    else:
        g.bt['flats'] = g.bt.get('flats', 0) + 1

def diag_add(key, val=1):
    g.diag[key] = g.diag.get(key, 0) + val
