# =========================================================
# V1.2.0-预筛版 战车A — 独立A策略(趋势过滤版 + Dragon 6因子预筛)
# =========================================================
#
# ⚠️ 这是 V1.1.0 的派生版，唯一改动：Dragon 选股在 seed 后加「6因子预筛 top250」
#    (与 skill jq_screener 逐位一致)。原文件 archive/strategy_versions/strategy_A_v1_1_0.py 未改动。
#
# 【为什么加预筛 — 数据依据】
#   20 交易日 eod 回测(D1, T开盘买入→当日收盘):
#     - 被 250 预筛砍掉、原版留着的尾部票: 次日均 -0.91% / 胜率40% / 0涨停 (垃圾票)
#     - 预筛保留顶替的票: +0.81% / 61%
#     - 池整体: +0.64%(原版) → +1.14%(预筛版), 胜率 56% → 62%
#   改动位置: _get_dragon_stock_list_A_impl —— price_df count 4→25(+low)，per_stock 加 6 因子，
#            seed 后插入「硬门槛 + 6因子综合排名取 top(dragon_star_prefilter_n, 默认250)」。
#
# ⚠️ 未做长周期(D5/D10/D20)聚宽实盘回测验证；上实盘前请 Wallace 在聚宽自行回测确认。
#
# ---------------------------------------------------------
# V1.1.0 战车A — 独立A策略(趋势过滤版)  [以下为原始头注]
# ---------------------------------------------------------
#
# 从 全天候战车 v9.0.25 提取，仅保留A策略(早盘先手/Dragon龙头)
# 移除了 B(午后突破)、C(ETF动量轮动)、D(大小盘择时) 策略
#
# 【A策略特性】
#   - 趋势过滤系统: 大盘趋势(MA多头排列) + 个股趋势(均线+低点抬升)
#   - Dragon龙头追涨 + 首板低开(T+1) + 首板高开 + 弱转强
#   - 只做趋势向上的个股(无论大盘涨跌)
#   - 大盘下跌时: 做逆势强势股(相对强度>0 + 个股趋势向上) + 缩仓
#   - Dragon: 趋势过滤替代unified_score阈值拦截, 选股通过即可买入
#   - Lowopen: 保持unified_score评分(统计套利型,评分有效)
#   - 首板低开: 昨日涨停+非连板+60d低位+低开3-4%+动态阈值
#   - T+1卖出: 11:20盈利止盈, 14:50强制清仓(涨停除外)
#   - 缺口止损延迟确认: 09:31预警→09:35确认(恢复-2%以上取消)
#
# 【版本迭代记录】
#
#   V1.1.0 (2026-03-29) — 趋势过滤系统 + 风控简化
#     - 新增趋势过滤: 大盘MA5>MA10>MA20=上涨, 个股均线多头+低点抬升
#     - 新增逆势强势股: 大盘跌时只做相对强度>0且趋势向上的个股
#     - 简化风控: 移除6道环境拦截,改为1道趋势过滤器
#     - Dragon: unified_score不再拦截,改为仓位调节(q×env控制仓位大小)
#     - 移除: panic_scout模式、strict_bear封锁、盘中熔断全面禁买
#     - 保留: Dragon断路器(连亏保护)、深回撤冷却(组合保护)
#
#   v9.0.25 (2026-03-28) — 统一评分系统(期望收益率锚定)
#     - 新增统一评分: final_score = base_edge[type][regime] × quality_mult × env_weight
#     - 新增首板低开(firstboard_lowopen)选股: 昨日涨停+非连板+60d低位+低开3-4%
#     - 新增2D环境模型: CSI1000三年分位值(长期位置) × 5日波动率(短期波动)
#     - 新增动态阈值: 相对位置阈值 = 0.30 + 0.60 × csi1000_percentile
#     - 新增T+1卖出规则: 11:20盈利止盈, 14:50强制清仓(涨停除外)
#     - 新增空仓阈值: 统一得分低于阈值不开仓(自适应bull/neutral/bear)
#     - 修改select_candidates_A: 不再Dragon-first, 统一评分排序
#     - 修改score_candidates_A: 新增firstboard_lowopen通道+统一评分路径
#     - sell_ctx增加current_dt/high_limit字段(T+1卖出需要)
#     - 修复Dragon quality_multiplier零区分度: 改用百分位排名(Top→2.0, Bottom→0.5)
#     - 优化缺口止损: 09:31标记预警→09:35确认, 价格恢复到-2%以上则取消止损
#
#   v9.0.17 (2026-03-27) — 补仓窗口+竞价序列
#     - 二段补仓从固定09:35改为09:33~09:45窗口(每分钟检查)
#     - 满足条件立刻补仓, 09:45仍不满足→half_final
#     - 竞价缓存从单快照改为序列存储(每只股票20+个快照)
#     - 为后续竞价强度因子做数据准备(先存不用)
#
#   v9.0.17 (2026-03-27) — CQTO五轮裁决版(环境分离定稿)
#     - 聚宽回测: 关闭二次确认+二段买入, 直接满仓(恢复+30.9%基准)
#     - QMT实盘: 保留确认但放宽(confirm>=2满仓, =1半仓, =0放弃)
#     - QMT实盘: 保留二段买入(50%+50%)
#     - 补仓失败标记half_final(区分主动vs被动半仓)
#
#   v9.0.17 (2026-03-27) — CQTO四轮裁决版
#     - 修正聚宽环境日志(二次确认已启用而非已跳过)
#     - pending_stage2_confirm_date在下单时设置(非sync时)
#     - on_order_error扩展: 覆盖partial/stage2委托被拒
#
#   v9.0.17 (2026-03-27) — CQTO三轮裁决版 + 环境分离
#     - ST识别: 从股票名称检测ST/退市
#     - A二段状态机: 成交确认后推进stage
#     - on_order_error补充partial_order_id清理
#     - 环境检测: g.is_qmt区分QMT实盘vs聚宽回测
#     - 二次确认/二段买入/get_batch仅QMT实盘启用
#     - 聚宽回测也启用二次确认+二段买入(可回测验证效果)
#     - 聚宽: 09:35即时成交直接写full; QMT: 等成交回调确认
#     - get_batch用hasattr检测, 聚宽无此方法自动跳过不报错
#     - ST识别: 从股票名称检测ST/退市(不再hardcode false)
#     - A二段状态机: 委托成功不直接写full, 等成交确认后推进
#     - on_order_error补充partial_order_id清理
#
#   v9.0.17 (2026-03-27) — CQTO二轮裁决版(6个补丁)
#     - 删除after_market_close重复注册(trade_days不再+2)
#     - partial_order_id取值修复(兼容int返回)
#     - 删除涨停卖出限制(涨停是最佳卖出时机,3处)
#     - minute_stop_loss接入get_batch批量取价
#     - history()支持high_limit字段(B策略star_pool)
#     - _do_order删除涨停封板检查(保留跌停价兜底)
#     - ST识别: 从股票名称检测ST/退市(不再hardcode false)
#     - A二段状态机: 委托成功不直接写full, 等成交确认后推进
#
#   v9.0.17 (2026-03-26) — CQTO终极融合版
#     兼容层v2.2: T+1 closeable保护/对手价滑点/TTL缓存/卖出取整
#     竞价口径安全: 09:26后无缓存返回空(禁止tick冒充竞价)
#     新增history()兼容(补齐B策略依赖)
#     统一止损阈值_get_stop_level(消除重复代码)
#     minute_stop_loss增强(涨跌停保护/多层过滤/每2分钟)
#     gap_down_stop_loss增强(涨跌停保护/异常捕获)
#     submit_exit_order修复(closeable检查/exit_order_id取值)
#     schedule_all精简(230+任务→约120个)
#     on_order_error清除pending_exit(委托被拒可重试)
#
#   v9.0.17 (2026-03-26) — 加auction_price观察日志(不参与决策)
#
#   v9.0.17 (2026-03-26) — 工程师审核修复
#     - 二次确认/二段买入范围从('A','B')收缩为仅'A'
#     - 回撤判断从get_price(1m)(兼容层不支持)改为open_price估算
#     - B策略完全不受冲高回落防护影响
#
#   v9.0.6 (2026-03-26) — 冲高回落防护三层
#     - 买入前二次确认(3条: 不破开盘价/回撤/不低于竞价价)
#     - 仓位分层(满仓/半仓/放弃)
#     - 二段买入(09:32先50%, 09:35补仓确认)
#     - 竞价缓存系统(09:15~09:26自动采集)
#
#   v9.0.5 (2026-03-26) — 纯A+C实盘准备
#     - D配置保留但函数未注册, 调度全注释
#     - manage_idle_cash关闭(不买货基)
#     - 货基511880→159001(未使用)
#     - 全部pandas负数索引改为.iloc(14处)
#     - 兼容层v2.1: get_all_securities date兼容/previous_date交易日历
#       get_call_auction竞价缓存/get_valuation市值计算/sync_after_trade
#       ETF subtype含16前缀/成交回报状态同步
#     - 补跑逻辑收紧至09:28前
#
#   v9.0.4 (2026-03-25) — D关闭(max_hold=0), 纯A+C对照
#     回测: +30.9%(2026年1-3月), 比有D版+3.4%, 回撤改善1.8%
#
#   v9.0.3 (2026-03-25) — A+C参数优化(9个参数微调)
#     回测: +27.5%(2026年1-3月), 比v9.0.2提升2.6%
#
#   v9.0.2 (2026-03-25) — 回测日志分析修复
#     P0: sync时序修正(解决85次unknown误标)
#     P1: datetime修复 / RSI NaN清洗
#
#   v9.0.1 (2026-03-25) — 第三轮工程师审核修复
#     unknown统一/防重复加仓/pending保护/月初保护/score_map
#
#   v9.0.0 — D策略升级为大小盘择时轮动
#   v8.0   — 新增D策略(小市值趋势)
#   v7.0   — 模块化重构, 新增C策略ETF轮动, Dragon补位/连亏保护
#
# 【架构】策略即插件 / 配置分层 / A+C双核 / D保留配置未注册
# =========================================================
#
# 【架构】策略即插件 / 配置分层 / select+score+sell_rules+get_mode
# =========================================================

from jqdata import *
import numpy as np
import pandas as pd
import math
import time
import datetime


EXPERIMENT_NAME = 'A0_BASE'

EXPERIMENTS = {
    'A0_BASE': {
        'global': {},
        'A': {},
    },

    'A1_DPM_CONSERVE': {
        'global': {
            'max_total_positions': 3,
            'max_total_positions_expanded': 4,
            'max_portfolio_position_ratio': 0.60,
            'max_portfolio_position_ratio_bull': 0.75,
            'dpm_expand_min_A_profit': 0.08,
            'dpm_expand_in_neutral_trend': False,
        },
        'A': {},
    },

    'A2_TRENDCORE_FILTER': {
        'global': {
            'dragon_trend_core_policy': 'bull_up_only',
        },
        'A': {},
    },

    'A3_DRAGON_RISK_FAST': {
        'global': {
            'dragon_circuit_breaker_max_consecutive_losses': 2,
            'dragon_circuit_breaker_min_avg_loss': 0.03,
            'dragon_circuit_breaker_pause_days': 1,
            'dragon_loss_reduce_after': 2,
            'dragon_loss_reduced_pos_ratio': 0.12,
            'dragon_loss_pause_after': 3,
            'dragon_loss_pause_days': 2,
            'dragon_open_tier_enable': True,
            'dragon_open_tier_mid': 0.03,
            'dragon_open_tier_high': 0.04,
            'dragon_open_tier_mid_mult': 0.5,
        },
        'A': {
            'dragon_max_open_ratio': 0.04,
            'dragon_deep_water_max_open_ratio': 0.04,
        },
    },

    'A4_COMBO': {
        'global': {
            'max_total_positions': 3,
            'max_total_positions_expanded': 4,
            'max_portfolio_position_ratio': 0.60,
            'max_portfolio_position_ratio_bull': 0.75,
            'dpm_expand_min_A_profit': 0.08,
            'dpm_expand_in_neutral_trend': False,

            'dragon_trend_core_policy': 'bull_up_only',

            'dragon_circuit_breaker_max_consecutive_losses': 2,
            'dragon_circuit_breaker_min_avg_loss': 0.03,
            'dragon_circuit_breaker_pause_days': 1,
            'dragon_loss_reduce_after': 2,
            'dragon_loss_reduced_pos_ratio': 0.12,
            'dragon_loss_pause_after': 3,
            'dragon_loss_pause_days': 2,
            'dragon_open_tier_enable': True,
            'dragon_open_tier_mid': 0.03,
            'dragon_open_tier_high': 0.04,
            'dragon_open_tier_mid_mult': 0.5,
        },
        'A': {
            'dragon_max_open_ratio': 0.04,
            'dragon_deep_water_max_open_ratio': 0.04,
        },
    },
}


def apply_experiment_overrides(global_cfg, strategy_a_cfg):
    exp = EXPERIMENTS.get(EXPERIMENT_NAME)
    if exp is None:
        raise ValueError("未知实验组 EXPERIMENT_NAME={}".format(EXPERIMENT_NAME))

    global_overrides = exp.get('global', {})
    a_overrides = exp.get('A', {})

    global_cfg.update(global_overrides)
    strategy_a_cfg.update(a_overrides)

    try:
        log.info("🧪【实验组】EXPERIMENT_NAME={}".format(EXPERIMENT_NAME))
        log.info("🧪【实验配置】global_overrides={}".format(global_overrides))
        log.info("🧪【实验配置】strategy_A_overrides={}".format(a_overrides))
    except Exception:
        print("🧪【实验组】EXPERIMENT_NAME={}".format(EXPERIMENT_NAME))
        print("🧪【实验配置】global_overrides={}".format(global_overrides))
        print("🧪【实验配置】strategy_A_overrides={}".format(a_overrides))

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

        # --- Dragon / Crowding ---
        'dragon_score_ema_alpha': 0.3,
        'dragon_pool_min_threshold': 5,
        'dragon_pool_max': 12,
        'dragon_pool_score_min': 0.10,
        'dragon_score_top_n': 12,
        'crowding_confirm_threshold': 4,
        'crowding_max_consecutive_days': 10,
        'crowding_cooldown_days': 3,
        'crowding_ema_exit_threshold': 0.15,

        # --- Dragon 断路器 ---
        'dragon_circuit_breaker_enable': True,
        'dragon_circuit_breaker_max_consecutive_losses': 3,
        'dragon_circuit_breaker_pause_days': 1,
        'dragon_circuit_breaker_min_avg_loss': 0.05,  # 连亏平均须>5%才触发
        'dragon_bear_max_weekly_trades': 2,
        'dragon_bear_weekly_counter_reset_days': 5,

        # --- 连续止损保护(改进2) ---
        'dragon_loss_reduce_after': 3,       # 连亏N笔后自动降仓
        'dragon_loss_reduced_pos_ratio': 0.15, # 降仓后的仓位比例(默认25%→15%)
        'dragon_loss_pause_after': 5,        # 连亏N笔后暂停Dragon
        'dragon_loss_pause_days': 2,         # 暂停天数

        # --- 全局风控 ---
        # [v9.0.25] 参数调整: 10万资金4只持仓(25%/只)是合理平衡点
        # v7.0=3太集中(单只33%), v9.0.25=6太分散(单只17%)
        'max_total_positions': 4,
        'max_total_positions_expanded': 5,
        'max_portfolio_position_ratio': 0.85,
        'max_portfolio_position_ratio_bull': 0.90,
        'max_daily_new_positions': 3,
        'intraday_panic_threshold': -0.02,
        'intraday_panic_index': '000852.XSHG',

        # --- DPM 动态仓位 ---
        'dpm_enable': True,
        'dpm_expand_when_A_profitable': True,
        'dpm_expand_min_A_profit': 0.03,
        'dpm_expand_in_bull': True,
        'dpm_expand_in_neutral_trend': True,
        # --- Panic Scout ---
        'panic_scout_enable': True,
        'panic_mild_threshold': -0.02,
        'panic_medium_threshold': -0.03,
        'panic_severe_threshold': -0.04,

        # --- 选股宇宙 ---
        'universe_index': '000852.XSHG',
        'star_stock_count': 250,
        'limit_up_lookback': 60,
        'limit_up_min_count': 1,

        # --- 冷却 ---
        'cooldown_normal_days': 5,
        'cooldown_dragon_days': 10,

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


        # --- [v9.0.25] TickSignalEngine 高级止损开关 ---
        # 回测证实这两个机制会过早卖出大牛股(002131错过+42%, 002716错过+74%)
        # 默认关闭, 与v7.0.0行为一致; 未来调优后可重新启用
        'enable_atr_trailing_stop': False,
        'enable_volume_exhaustion': False,

        # --- 杂项 ---
        'exclude_prefixes': ('30', '688', '689', '8', '4', '9'),
        'market_panic_drop': -0.02,
        'new_stock_days': 50,
        'dragon_enable': True,
        'dragon_max_avg_daily_range': 0.08,
        'panic_allow_A_scout': True,
        'panic_block_in_bear': False,
        'cooldown_days_after_sell': 3,
        'cooldown_days_after_sell_dragon': 4,
        'crowding_exit_pool_min': 3,
        'crowding_exit_score_decay_ratio': 0.60,
        'dragon_crowding_confirm_days': 2,

        # --- Panic Scout 参数 ---
        'panic_A_max_hold': 1,
        'panic_A_min_open_ratio_medium': 0.008,
        'panic_A_min_open_ratio_mild': 0.004,
        'panic_A_min_open_ratio_severe': 0.012,
        'panic_A_pos_ratio_medium': 0.06,
        'panic_A_pos_ratio_mild': 0.05,
        'panic_A_pos_ratio_severe': 0.08,
        'panic_drop_level_medium': -0.03,
        'panic_drop_level_severe': -0.04,

        # --- 趋势过滤系统 ---
        'trend_filter_enable': True,
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
        # 相对强度(大盘下跌时用)
        'trend_relative_strength_days': 5,        # 相对强度计算天数
        'trend_relative_strength_min': 0.0,       # 最小超额收益(大盘跌时个股需跑赢)
        # 趋势过滤的应用范围
        'trend_filter_dragon': True,              # dragon是否用趋势过滤
        'trend_filter_normal': True,              # firstboard/weak_to_strong是否用趋势过滤
        'trend_filter_lowopen': False,            # lowopen不用趋势过滤(它自己有低位筛选)
        # 大盘下跌时的仓位缩减
        'trend_downtrend_pos_ratio_mult': 0.5,    # 大盘下跌趋势时仓位乘数

        # --- 统一评分系统(期望收益率锚定 + 2D环境模型) ---
        'unified_scoring_enable': True,
        'unified_csi1000_lookback': 730,         # 约3年交易日
        'unified_volatility_lookback': 5,         # 短期波动窗口(天)
        'unified_volatility_high': 0.025,         # 高波动阈值
        'unified_volatility_low': 0.010,          # 低波动阈值
        # base_edge: 各type在不同regime下的历史平均每笔收益率
        'unified_base_edge': {
            'dragon_follow':      {'bull': 0.0025, 'neutral': -0.005, 'bear': -0.0269},
            'firstboard_lowopen': {'bull': 0.0091, 'neutral': 0.0091, 'bear': 0.0091},
            'firstboard':         {'bull': 0.005,  'neutral': 0.003,  'bear': -0.005},
            'weak_to_strong':     {'bull': 0.003,  'neutral': 0.001,  'bear': -0.008},
        },
        # 空仓阈值: 统一得分低于此值则不开仓
        'unified_empty_threshold': {'bull': 0.002, 'neutral': 0.003, 'bear': 0.005},
        # quality_multiplier范围
        'unified_quality_mult_min': 0.5,
        'unified_quality_mult_max': 2.0,
    }


def make_strategy_A_config():
    """A策略(早盘先手/Dragon龙头)私有配置"""
    return {
        'name': 'A',
        'open_time': '09:32',
        'sell_times': ['11:20', '14:50'],
        'max_hold': 2,
        'pos_ratio': 0.25,

        # --- Dragon模式 ---
        'dragon_max_hold': 2,
        'dragon_pos_ratio': 0.25,
        'dragon_bear_pos_ratio': 0.10,
        'dragon_abs_stop_loss': 0.035,
        'dragon_min_profit_protect': 0.10,
        'dragon_max_open_ratio': 0.065,

        # --- Normal模式 ---
        'abs_stop_loss': 0.05,
        'lowopen_abs_stop_loss': 0.08,  # 低开策略宽止损(入场已亏3~4%，需更多空间)
        'stop_by_ma': True,
        'partial_tp_threshold': 0.18,
        'partial_tp_lock_ratio': 0.40,

        # --- Strict Bear ---
        'strict_max_hold': 1,
        'strict_pos_ratio': 0.25,
        'neutral_recover_max_hold': 2,
        'neutral_recover_pos_ratio': 0.12,

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
        'partial_take_profit_firstboard': 0.12,
        'partial_take_profit_weak': 0.08,

        # --- Bear+Crowding ---
        'bear_crowding_max_hold': 1,
        'bear_crowding_pos_ratio': 0.15,

        # --- 首板低开(firstboard_lowopen) T+1 ---
        'lowopen_gap_min': 0.96,              # 低开下限(开盘/昨收)
        'lowopen_gap_max': 0.97,              # 低开上限
        'lowopen_rp_fixed': 0.50,             # 固定相对位置阈值(fallback)
        'lowopen_rp_dynamic_base': 0.30,      # 动态阈值 = base + scale * csi1000_pct
        'lowopen_rp_dynamic_scale': 0.60,
        'lowopen_min_money': 1e8,             # 最低成交额
        'lowopen_consecutive_days': 10,       # 连板检测窗口
        'lowopen_pos_ratio': 0.25,            # 首板低开仓位
        'lowopen_strong_tp_threshold': 0.05,  # 强势止盈阈值: >5%卖半仓持到14:50

        # --- 选股/打分门槛 ---
        'limit_up_buffer': 0.995,
        'dragon_min_score': 0.045,
        'dragon_min_open_ratio': 0.005,
        'dragon_bear_allow_deep_water': 'half',  # bear下deep_water仓位减半(可选: True/False/'half')
        'dragon_deep_water_max_open_ratio': 0.05,
        'normal_min_score': 0.022,
        'normal_min_open_ratio': -0.001,
        'normal_firstboard_bonus': 0.012,
        'normal_weak_bonus': 0.002,
        'strict_min_score': 0.035,
        'strict_min_open_ratio': 0.03,
        'strict_firstboard_bonus': 0.014,
        'strict_weak_bonus': 0.006,
    }


# ================== 分钟级统一止损 ==================

def _get_stop_level(strategy, entry_type):
    """止损阈值查找(仅A策略)"""
    if strategy == 'A':
        if entry_type == 'dragon_follow':
            return g.cfg.get('A_dragon_abs_stop_loss', 0.035)
        elif entry_type == 'firstboard_lowopen':
            return g.cfg.get('A_lowopen_abs_stop_loss', 0.08)
        else:
            return g.cfg.get('A_abs_stop_loss', 0.05)
    else:
        return 0.05


def minute_stop_loss_all(context):
    """分钟级统一止损: 检查A+B+C所有持仓
    [v9.0.17] 批量取价: 先筛候选 → get_batch一次性拉tick → 内存判断
    [v9.0.17-opt2] 同时处理pending_exit重试(每2分钟自动重试未成交的卖出)
    [v9.0.21] 聚宽: 调用_jq_tick_engine_update + ATR移动止损 + 量能衰竭检测
    """
    try:
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
                log.warning("分钟止损筛选异常 {}: {}".format(stock, e))

        # Step2: 批量预取tick(QMT实盘用get_batch, 聚宽回测无此方法自动跳过)
        all_need_tick = list(set(pending_retry_stocks + candidate_stocks))
        current_data = get_current_data()
        if all_need_tick and hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(all_need_tick)
            except Exception:
                pass  # 静默降级, 不刷屏

        # Step2.3: [v9.0.21] 聚宽Tick引擎更新(取get_ticks做OIR/OBV/轨迹)
        # [v9.0.25] ATR止盈和量能衰竭都关闭时跳过引擎更新, 省去每2分钟×N只持仓×2次get_ticks()
        # 每个回测日从~180次get_ticks()降到0次(止损路径), 大幅提速
        _need_engine = g.cfg.get('enable_atr_trailing_stop', False) or g.cfg.get('enable_volume_exhaustion', False)
        if _need_engine:
            _jq_tick_engine_update(context)

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
                        log.info("🔁【待退出跳过】{} 跌停中，明天再试".format(stock))
                    meta['_exit_retry_count'] = 5
                    meta['_exit_retry_date'] = today
                    continue
                if order_target_value(stock, 0) is not None:
                    meta['_exit_retry_count'] = retry_count + 1
                    meta['_exit_retry_date'] = today
                    log.info("🔁【待退出重试】{} 第{}次尝试清仓".format(stock, retry_count + 1))
                    diag_add('retry_pending_exit')
            except Exception as e:
                log.warning("pending_exit重试异常 {}: {}".format(stock, e))

        # Step3: 在内存中逐票判断(不再发起新的RPC)
        # [v9.0.21] 聚宽: 增加ATR移动止损 + 量能衰竭检测(与QMT tick_monitor一致)
        engine = get_tick_engine()
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
                stop_pct = _get_stop_level(strategy, entry_type)
                exit_reason = None

                # [V1.0.0] 缺口预警期间跳过分钟止损，等09:35确认
                if hasattr(g, 'gap_down_alerts') and stock in g.gap_down_alerts:
                    continue

                # 检查1: 固定止损(原逻辑)
                if pnl <= -stop_pct:
                    exit_reason = 'minute_stop_loss'
                    security_name = getattr(cd_item, 'name', stock)
                    log.info("🚨【分钟止损】{} {} strategy={} entry={} pnl={:.2f}% stop={:.2f}%".format(
                        stock, security_name, strategy, entry_type, pnl * 100, stop_pct * 100))

                # [v9.0.25] ATR移动止盈和量能衰竭由配置开关控制
                # 回测证实会过早卖出大牛股(002131错过+42%, 002716错过+74%)
                # 默认关闭(enable_atr_trailing_stop/enable_volume_exhaustion=False)

                # [v9.0.25] 检查2: ATR移动止损(带趋势加速保护+时段过滤)
                if exit_reason is None and engine.enabled and g.cfg.get('enable_atr_trailing_stop', False):
                    trailing_price = engine.get_trailing_stop_price(stock, strategy, avg_cost)
                    if trailing_price and curr_price < trailing_price:
                        # [v9.0.25] 趋势加速保护: 如果最近价格在加速上涨, 暂缓止盈
                        suppress = False
                        track = engine.tick_tracks.get(stock, {})
                        if track and len(track.get('prices', [])) >= 30:
                            recent = track['prices'][-30:]
                            mid = len(recent) // 2
                            first_half_chg = (recent[mid] - recent[0]) / recent[0] if recent[0] > 0 else 0
                            second_half_chg = (recent[-1] - recent[mid]) / recent[mid] if recent[mid] > 0 else 0
                            if second_half_chg > first_half_chg and second_half_chg > 0.002:
                                suppress = True
                                log.debug("🔥【趋势加速】{} 二段涨幅{:.2f}%>一段{:.2f}%, 暂缓止盈".format(
                                    stock, second_half_chg * 100, first_half_chg * 100))
                        # [v9.0.25] 开盘30分钟内不启动止盈(龙头股开盘波动大)
                        now_hm = context.current_dt.strftime('%H:%M') if hasattr(context.current_dt, 'strftime') else '10:00'
                        if now_hm < '10:00' and strategy == 'A':
                            suppress = True

                        if not suppress:
                            atr = engine.atr_cache.get(stock, 0)
                            exit_reason = 'trailing_stop'
                            log.info("📉【ATR移动止盈】{} strategy={} 高点={:.2f} 止盈线={:.2f} 现价={:.2f} ATR={:.3f} pnl={:+.2f}%".format(
                                stock, strategy, track.get('high', 0), trailing_price, curr_price, atr, pnl * 100))

                # [v9.0.25] 检查3: 量能衰竭+OBV背离 (提高盈利门槛4%, 加冷却)
                if exit_reason is None and engine.enabled and g.cfg.get('enable_volume_exhaustion', False) and pnl > 0.04:
                    cooldown_ok = True
                    last_trigger = engine.vol_exhaust_cooldown.get(stock, 0)
                    if time.time() - last_trigger < engine.vol_exhaust_cooldown_sec:
                        cooldown_ok = False
                    if cooldown_ok and engine.check_volume_exhaustion(stock):
                        decay = engine.get_volume_decay_ratio(stock)
                        obv_info = engine.get_obv_divergence_info(stock)
                        exit_reason = 'volume_exhaustion'
                        engine.vol_exhaust_cooldown[stock] = time.time()
                        log.info("📊【量能衰竭】{} strategy={} 量比={:.1f}% OBV背离={} pnl={:+.2f}%".format(
                            stock, strategy, decay * 100, obv_info.get('divergence', False), pnl * 100))

                # 执行退出
                if exit_reason:
                    if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=pnl):
                        diag_add('{}_sell_all'.format(strategy))
                        if exit_reason == 'minute_stop_loss':
                            diag_add('stop_loss_triggered')
                        elif exit_reason == 'trailing_stop':
                            diag_add('trailing_stop_triggered')
                        elif exit_reason == 'volume_exhaustion':
                            diag_add('volume_exhaust_triggered')

            except Exception as e:
                log.error("分钟止损处理异常 {}: {}".format(stock, e))

    except Exception as e:
        log.error("minute_stop_loss_all 总体异常: {}".format(e))


# =============================================================================
# [v9.0.19] TickSignalEngine — 统一信号引擎
# [v9.0.20] 全面升级:
#   1. L2大单: +主动买卖判定 +VOI/OIR多维度订单流
#   2. 移动止损: ATR自适应(替代固定百分比) +多周期协调
#   3. 竞价因子: 3因子→7因子(phase分离+9:24冲刺+量比+撤单比+振幅)
#   4. 量能衰竭: +OBV背离确认(减少误判)
#
# QMT实盘: L2逐笔 + Tick实时 + 竞价序列 → 精确信号
# 聚宽回测: 竞价API + 分钟线近似 → 近似信号(保持一致性)
# =============================================================================
class TickSignalEngine:
    """Tick信号引擎 — 统一接口，环境自适应"""

    def __init__(self):
        self.enabled = False          # initialize()中设置
        self.is_qmt = False
        # === L2大单流向 ===
        self.l2_flow = {}             # {stock: {'big_buy': 0, 'big_sell': 0, ...}}
        self.l2_orderbook_prev = {}   # {stock: prev_orderbook} — VOI计算用
        # === Tick轨迹 ===
        self.tick_tracks = {}         # {stock: {'high': 0, 'prices': [], 'volumes': [], ...}}
        # === 竞价评分 ===
        self.auction_scores = {}      # {stock: float 0~1}
        # === 量能基准 ===
        self.opening_volume_base = {} # {stock: 前3分钟平均每tick成交量}
        # === ATR缓存 ===
        self.atr_cache = {}           # {stock: atr_value} — 每日计算一次
        # === 配置 ===
        self.big_order_threshold = 500000   # 50万算大单
        # [v9.0.20] ATR自适应止损(替代固定百分比)
        # [v9.0.25] 参数优化: 放宽止盈触发, 增大波动空间
        self.trail_atr_multiplier = 2.5     # 止损距离 = 2.5倍ATR (v9.0.20: 2.0)
        self.trail_pct_fallback = {'A': 0.025, 'B': 0.030, 'C': 0.020}  # ATR不可用时回退
        self.trail_activate_pnl = 0.03      # 盈利3%后启动移动止损 (v9.0.20: 1.5%)
        self.volume_exhaust_ratio = 0.20    # 当前量/开盘量 < 20% = 衰竭 (v9.0.20: 30%)
        self.volume_exhaust_window = 30     # 最近30个tick(约90秒)的均量, 平滑噪声
        self.quality_block = 0.25           # quality < 0.25 → 放弃 (v9.0.20: 0.30)
        self.quality_reduce = 0.50          # quality < 0.50 → 降仓 (v9.0.20: 0.60)
        # [v9.0.25] 盈利分档止盈: 盈利越高,给越多空间(低盈利宽松,高盈利锁利)
        self.trail_tiers = [
            # (盈利门槛, ATR乘数, 最小回撤容忍)
            (0.03, 2.5, 0.015),  # 盈利3%~5%: 2.5倍ATR, 最少容忍1.5%回撤
            (0.05, 2.0, 0.020),  # 盈利5%~8%: 2.0倍ATR, 锁定更多利润
            (0.08, 1.5, 0.025),  # 盈利>8%: 1.5倍ATR, 积极保护利润
        ]
        # [v9.0.25] 量价背离冷却: 触发后N分钟内不重复触发
        self.vol_exhaust_cooldown = {}      # {stock: last_trigger_time}
        self.vol_exhaust_cooldown_sec = 600 # 10分钟冷却

    def reset_daily(self):
        """每日重置(morning_prepare调用)"""
        self.l2_flow.clear()
        self.l2_orderbook_prev.clear()
        self.tick_tracks.clear()
        self.auction_scores.clear()
        self.opening_volume_base.clear()
        self.atr_cache.clear()

    # -----------------------------------------------------------------
    # 模块1: L2大单净流入 + 主动买卖判定 + VOI/OIR
    # [v9.0.20] 升级: 主动买卖分类 + Volume Order Imbalance + Order Imbalance Ratio
    # -----------------------------------------------------------------
    def update_l2_flow(self, stock, context):
        """更新单只股票的L2大单流向 + 订单流因子(QMT每15秒调用)"""
        if not self.is_qmt:
            return
        try:
            transactions = get_l2_transactions(stock, count=500)
            if not transactions:
                return

            big_buy = 0.0
            big_sell = 0.0
            active_buy_amt = 0.0   # 所有主动买入金额
            active_sell_amt = 0.0  # 所有主动卖出金额
            for t in transactions:
                amt = t.get('amount', 0)
                price = t.get('price', 0)
                direction = t.get('direction', 0)

                # [v9.0.20] 主动买卖分类: direction由L2逐笔的bs_flag决定
                # direction=1: tick价>=卖一价(主动买) direction=2: tick价<=买一价(主动卖)
                if direction == 1:
                    active_buy_amt += amt
                    if amt >= self.big_order_threshold:
                        big_buy += amt
                elif direction == 2:
                    active_sell_amt += amt
                    if amt >= self.big_order_threshold:
                        big_sell += amt

            # [v9.0.20] VOI (Volume Order Imbalance) — 盘口变化因子
            voi = 0.0
            oir = 0.0
            try:
                orderbook = get_l2_orderbook(stock)
                if orderbook:
                    prev = self.l2_orderbook_prev.get(stock)
                    if prev:
                        # VOI: 买盘增量 - 卖盘增量(正=买盘增强)
                        bid_vol_now = sum(orderbook.get('bid_volumes', [])[:5])
                        bid_vol_prev = sum(prev.get('bid_volumes', [])[:5])
                        ask_vol_now = sum(orderbook.get('ask_volumes', [])[:5])
                        ask_vol_prev = sum(prev.get('ask_volumes', [])[:5])
                        voi = (bid_vol_now - bid_vol_prev) - (ask_vol_now - ask_vol_prev)

                    # OIR: (买盘总量 - 卖盘总量) / (买盘总量 + 卖盘总量)
                    bid_total = sum(orderbook.get('bid_volumes', [])[:5])
                    ask_total = sum(orderbook.get('ask_volumes', [])[:5])
                    if bid_total + ask_total > 0:
                        oir = (bid_total - ask_total) / (bid_total + ask_total)

                    self.l2_orderbook_prev[stock] = orderbook
            except Exception:
                pass

            total_active = active_buy_amt + active_sell_amt
            active_ratio = active_buy_amt / total_active if total_active > 0 else 0.5

            self.l2_flow[stock] = {
                'big_buy': big_buy,
                'big_sell': big_sell,
                'net_flow': big_buy - big_sell,
                'active_buy': active_buy_amt,
                'active_sell': active_sell_amt,
                'active_ratio': active_ratio,   # [v9.0.20] 主动买入占比
                'voi': voi,                      # [v9.0.20] 盘口增量差
                'oir': oir,                      # [v9.0.20] 盘口静态失衡
                'total_count': len(transactions),
                'last_update': time.time(),
            }
        except Exception as e:
            log.debug("L2 flow update failed {}: {}".format(stock, e))

    def get_l2_score(self, stock):
        """获取L2综合评分 0~1
        [v9.0.20] 多维度加权: 大单流向(40%) + 主动买卖(30%) + 盘口失衡OIR(30%)
        1.0 = 强看多, 0.5 = 中性, 0.0 = 强看空
        """
        flow = self.l2_flow.get(stock)
        if not flow:
            return 0.5  # 无数据 → 中性

        # 维度1: 大单流向(原逻辑)
        big_buy = flow['big_buy']
        big_sell = flow['big_sell']
        big_total = big_buy + big_sell
        if big_total >= self.big_order_threshold:
            big_score = big_buy / big_total
        else:
            big_score = 0.5  # 大单太少

        # 维度2: 主动买卖比 [v9.0.20]
        active_score = flow.get('active_ratio', 0.5)

        # 维度3: OIR盘口失衡 [v9.0.20] — 映射到0~1
        oir = flow.get('oir', 0.0)  # -1~+1
        oir_score = (oir + 1.0) / 2.0  # 映射到0~1

        # 加权合成
        score = big_score * 0.40 + active_score * 0.30 + oir_score * 0.30
        return min(max(score, 0.0), 1.0)

    def update_l2_flow_jq(self, stock, context):
        """[v9.0.21] 聚宽版L2流向更新 — 用get_ticks的5档盘口近似计算
        无逐笔成交,但可用tick快照的盘口做OIR和主动买卖判定
        """
        try:
            ticks = get_ticks(stock, count=60, end_dt=context.current_dt,
                              fields=['time', 'current', 'volume', 'money',
                                      'a1_p', 'a1_v', 'b1_p', 'b1_v',
                                      'a2_p', 'a2_v', 'b2_p', 'b2_v',
                                      'a3_p', 'a3_v', 'b3_p', 'b3_v',
                                      'a4_p', 'a4_v', 'b4_p', 'b4_v',
                                      'a5_p', 'a5_v', 'b5_p', 'b5_v'],
                              df=True)
            if ticks is None or len(ticks) < 5:
                return

            # 主动买卖判定: tick价 >= 卖一价 → 主动买, tick价 <= 买一价 → 主动卖
            active_buy_amt = 0.0
            active_sell_amt = 0.0
            big_buy = 0.0
            big_sell = 0.0
            prev_money = 0.0

            for i in range(len(ticks)):
                row = ticks.iloc[i]
                curr_money = row.get('money', 0)
                tick_amt = curr_money - prev_money if prev_money > 0 else 0
                prev_money = curr_money
                if tick_amt <= 0:
                    continue

                price = row.get('current', 0)
                a1_p = row.get('a1_p', 0)
                b1_p = row.get('b1_p', 0)

                if price > 0 and a1_p > 0 and price >= a1_p:
                    active_buy_amt += tick_amt
                    if tick_amt >= self.big_order_threshold:
                        big_buy += tick_amt
                elif price > 0 and b1_p > 0 and price <= b1_p:
                    active_sell_amt += tick_amt
                    if tick_amt >= self.big_order_threshold:
                        big_sell += tick_amt

            # OIR: 盘口静态失衡(用最新tick的5档)
            last = ticks.iloc[-1]
            bid_total = sum(last.get('b{}_v'.format(i), 0) for i in range(1, 6))
            ask_total = sum(last.get('a{}_v'.format(i), 0) for i in range(1, 6))
            oir = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0.0

            total_active = active_buy_amt + active_sell_amt
            active_ratio = active_buy_amt / total_active if total_active > 0 else 0.5

            self.l2_flow[stock] = {
                'big_buy': big_buy,
                'big_sell': big_sell,
                'net_flow': big_buy - big_sell,
                'active_buy': active_buy_amt,
                'active_sell': active_sell_amt,
                'active_ratio': active_ratio,
                'voi': 0.0,   # JQ无前一次盘口快照做差分,简化为0
                'oir': oir,
                'total_count': len(ticks),
                'last_update': time.time(),
            }
        except Exception as e:
            log.debug("JQ L2 flow update failed {}: {}".format(stock, e))

    def update_tick_track_jq(self, stock, context):
        """[v9.0.21] 聚宽版tick轨迹更新 — 用get_ticks获取最近tick序列
        每2分钟调一次,取最近120条tick(约10分钟)
        """
        try:
            ticks = get_ticks(stock, count=120, end_dt=context.current_dt,
                              fields=['time', 'current', 'volume'],
                              df=True)
            if ticks is None or len(ticks) < 5:
                return

            prices = ticks['current'].tolist()
            # volume是累计量,需要差分得到每tick成交量
            cum_vols = ticks['volume'].tolist()
            tick_vols = [0]
            for i in range(1, len(cum_vols)):
                dv = cum_vols[i] - cum_vols[i - 1]
                tick_vols.append(max(dv, 0))

            if stock not in self.tick_tracks:
                self.tick_tracks[stock] = {
                    'high': max(prices),
                    'prices': prices,
                    'volumes': tick_vols,
                    'first_price': prices[0],
                    'open_vol_avg': 0,
                    'tick_count': len(prices),
                    'obv': 0.0,
                    'obv_high': 0.0,
                    'price_high_at_obv_high': prices[0],
                }
            track = self.tick_tracks[stock]

            # 用完整tick序列覆盖更新
            track['prices'] = prices
            track['volumes'] = tick_vols
            track['high'] = max(track.get('high', 0), max(prices))
            track['tick_count'] = max(track['tick_count'], len(prices))

            # 前20个tick的均量作为开盘量基准(仅首次设置)
            if track['open_vol_avg'] <= 0 and len(tick_vols) >= 20:
                first_20 = tick_vols[:20]
                avg = sum(first_20) / 20.0
                if avg > 0:
                    track['open_vol_avg'] = avg

            # 重算OBV
            obv = 0.0
            obv_high = 0.0
            price_at_obv_high = prices[0]
            for i in range(1, len(prices)):
                if prices[i] > prices[i - 1]:
                    obv += tick_vols[i]
                elif prices[i] < prices[i - 1]:
                    obv -= tick_vols[i]
                if obv > obv_high:
                    obv_high = obv
                    price_at_obv_high = prices[i]
            track['obv'] = obv
            track['obv_high'] = obv_high
            track['price_high_at_obv_high'] = price_at_obv_high

        except Exception as e:
            log.debug("JQ tick track update failed {}: {}".format(stock, e))

    # -----------------------------------------------------------------
    # 模块2: ATR自适应移动止损 + 多周期协调
    # [v9.0.20] 升级: 固定百分比→ATR自适应, 加入短周期止损协调
    # -----------------------------------------------------------------
    def update_tick_track(self, stock, curr_price, volume):
        """更新股票的tick轨迹(每3秒调用)"""
        if stock not in self.tick_tracks:
            self.tick_tracks[stock] = {
                'high': curr_price,
                'prices': [],
                'volumes': [],
                'first_price': curr_price,
                'open_vol_avg': 0,
                'tick_count': 0,
                'obv': 0.0,           # [v9.0.20] OBV累计
                'obv_high': 0.0,      # [v9.0.20] OBV历史最高
                'price_high_at_obv_high': curr_price,  # [v9.0.20] OBV最高时对应的价格
            }
        track = self.tick_tracks[stock]
        track['high'] = max(track['high'], curr_price)
        track['prices'].append(curr_price)
        track['volumes'].append(volume)
        track['tick_count'] += 1

        # [v9.0.20] 更新OBV (On-Balance Volume)
        if len(track['prices']) >= 2:
            prev_price = track['prices'][-2]
            if curr_price > prev_price:
                track['obv'] += volume
            elif curr_price < prev_price:
                track['obv'] -= volume
            # curr_price == prev_price: OBV不变

        if track['obv'] > track['obv_high']:
            track['obv_high'] = track['obv']
            track['price_high_at_obv_high'] = curr_price

        # 保留最近200个tick(约10分钟)
        if len(track['prices']) > 200:
            track['prices'] = track['prices'][-200:]
            track['volumes'] = track['volumes'][-200:]

        # 前60秒(20个tick)的均量作为开盘量基准
        if track['tick_count'] == 20:
            track['open_vol_avg'] = sum(track['volumes'][:20]) / 20.0

    def compute_atr(self, stock, period=14):
        """计算ATR(Average True Range), 每日调用一次并缓存
        返回: ATR值(价格单位) 或 None
        """
        if stock in self.atr_cache:
            return self.atr_cache[stock]
        try:
            h = attribute_history(stock, period + 1, '1d', ['high', 'low', 'close'])
            if h is None or len(h) < period + 1:
                return None
            highs = h['high'].values
            lows = h['low'].values
            closes = h['close'].values
            tr_list = []
            for i in range(1, len(highs)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                )
                tr_list.append(tr)
            if not tr_list:
                return None
            atr = sum(tr_list[-period:]) / min(period, len(tr_list))
            self.atr_cache[stock] = atr
            return atr
        except Exception:
            return None

    def get_trailing_stop_price(self, stock, strategy, avg_cost):
        """获取ATR自适应移动止损价格
        [v9.0.20] 升级: trail_distance = max(2*ATR, 固定百分比回退)
        [v9.0.25] 升级: 分档止盈 + 去掉短周期过紧止损 + 扩大ATR范围
        返回: 止损价 或 None(不启用)
        """
        track = self.tick_tracks.get(stock)
        if not track:
            return None

        intraday_high = track['high']
        if avg_cost <= 0 or intraday_high <= 0:
            return None

        # 从高点算盈利
        pnl_from_cost = intraday_high / avg_cost - 1
        if pnl_from_cost < self.trail_activate_pnl:
            return None

        # [v9.0.25] 分档止盈: 根据盈利幅度选择不同ATR乘数
        tier_multiplier = self.trail_atr_multiplier  # 默认
        min_trail = 0.015
        for tier_pnl, tier_mult, tier_min in self.trail_tiers:
            if pnl_from_cost >= tier_pnl:
                tier_multiplier = tier_mult
                min_trail = tier_min

        # ATR自适应止损距离
        atr = self.compute_atr(stock)
        if atr and atr > 0 and intraday_high > 0:
            atr_trail_pct = (tier_multiplier * atr) / intraday_high
            # [v9.0.25] 扩大合理范围: 1.5%~6% (v9.0.20: 1%~5%)
            atr_trail_pct = min(max(atr_trail_pct, min_trail), 0.06)
            trail = atr_trail_pct
        else:
            trail = self.trail_pct_fallback.get(strategy, 0.025)

        # [v9.0.25] 简化: 只用日内高点做止损, 去掉短周期(过紧导致甩出)
        trailing_stop = intraday_high * (1 - trail)

        # 移动止损价必须高于成本价(不能比固定止损更差)
        if trailing_stop <= avg_cost:
            return None

        return trailing_stop

    # -----------------------------------------------------------------
    # 模块3: 竞价强度因子 — 7因子模型
    # [v9.0.20] 升级: 3因子→7因子
    #   F1: 价格趋势斜率(稳步上升=好)
    #   F2: Phase1 vs Phase2分离(可撤单虚假 vs 不可撤单真实)
    #   F3: 9:24冲刺方向(最后1分钟价格变化)
    #   F4: 量价齐升(后半段成交量趋势)
    #   F5: 竞价量比(竞价量/5日均量)
    #   F6: 振幅稳定性(竞价价格振幅越小越稳)
    #   F7: 尾盘突变检测(涨幅集中在最后→可疑)
    # -----------------------------------------------------------------
    def compute_auction_score(self, stock, auction_snapshots):
        """从竞价序列计算7因子竞价强度评分 0~1
        auction_snapshots: [{'time': t, 'price': p, 'volume': v, 'money': m}, ...]
        时间覆盖09:15~09:25, 约每15秒一个快照(~40个点)
        """
        if not auction_snapshots or len(auction_snapshots) < 4:
            self.auction_scores[stock] = 0.5
            return 0.5

        prices = [s['price'] for s in auction_snapshots if s.get('price', 0) > 0]
        volumes = [s['volume'] for s in auction_snapshots if s.get('volume', 0) > 0]

        if len(prices) < 4:
            self.auction_scores[stock] = 0.5
            return 0.5

        n = len(prices)
        scores = {}  # 各因子得分, 最后加权

        # ---- F1: 价格趋势斜率 (权重15%) ----
        x = np.arange(n, dtype=float)
        y = np.array(prices, dtype=float)
        if y[0] > 0:
            y_norm = y / y[0] - 1
            slope = np.polyfit(x, y_norm, 1)[0] if n >= 2 else 0
            # slope正=上升, 映射到0~1: slope=+0.003→1.0, 0→0.5, -0.003→0.0
            scores['F1'] = min(max(slope * 100 / 0.3 * 0.5 + 0.5, 0.0), 1.0)
        else:
            scores['F1'] = 0.5

        # ---- F2: Phase1 vs Phase2分离 (权重15%) ----
        # 09:15~09:20(前1/3)可撤单 vs 09:20~09:25(后2/3)不可撤单
        phase1_end = n // 3  # 大约前1/3是Phase1
        if phase1_end >= 2 and n - phase1_end >= 2:
            p1_prices = prices[:phase1_end]
            p2_prices = prices[phase1_end:]
            p1_trend = (p1_prices[-1] - p1_prices[0]) / p1_prices[0] if p1_prices[0] > 0 else 0
            p2_trend = (p2_prices[-1] - p2_prices[0]) / p2_prices[0] if p2_prices[0] > 0 else 0

            # Phase1涨+Phase2跌 = 虚假强势(0.0分)
            # Phase1平+Phase2涨 = 真实强势(1.0分)
            # 两阶段同向 = 正常(0.5~0.7)
            if p1_trend > 0.005 and p2_trend < -0.002:
                scores['F2'] = 0.15  # 虚假强势
            elif p1_trend < 0.002 and p2_trend > 0.003:
                scores['F2'] = 0.85  # 真实强势(Phase2确认)
            elif p2_trend > 0:
                scores['F2'] = 0.65  # Phase2正向
            else:
                scores['F2'] = 0.35  # Phase2负向
        else:
            scores['F2'] = 0.5

        # ---- F3: 9:24冲刺方向 (权重20%) ----
        # 最后2~3个快照的方向是最强信号(09:24~09:25不可撤单的最终博弈)
        sprint_n = min(3, n - 1)
        if sprint_n >= 1 and prices[-sprint_n - 1] > 0:
            sprint_change = (prices[-1] - prices[-sprint_n - 1]) / prices[-sprint_n - 1]
            # sprint_change > 0 = 冲刺向上(好), 映射到0~1
            scores['F3'] = min(max(sprint_change * 50 + 0.5, 0.0), 1.0)
        else:
            scores['F3'] = 0.5

        # ---- F4: 量价齐升 (权重15%) ----
        if len(volumes) >= 4:
            first_half_vol = sum(volumes[:n//2])
            second_half_vol = sum(volumes[n//2:])
            if first_half_vol > 0:
                vol_growth = second_half_vol / first_half_vol
                # vol_growth>1.5=强放量, 1.0=平, <0.5=缩量
                scores['F4'] = min(max((vol_growth - 0.5) / 1.5, 0.0), 1.0)
            else:
                scores['F4'] = 0.5
        else:
            scores['F4'] = 0.5

        # ---- F5: 竞价量比 (权重10%) ----
        # 竞价总量 vs 5日均量, 量越大参与度越高
        total_auction_vol = sum(volumes) if volumes else 0
        try:
            h = attribute_history(stock, 5, '1d', ['volume'])
            if h is not None and len(h) > 0:
                avg_daily_vol = h['volume'].mean()
                if avg_daily_vol > 0:
                    vol_pct = total_auction_vol / avg_daily_vol
                    # 竞价量占日均量 2%=正常, 5%+=强参与
                    scores['F5'] = min(max(vol_pct / 0.05, 0.0), 1.0)
                else:
                    scores['F5'] = 0.5
            else:
                scores['F5'] = 0.5
        except Exception:
            scores['F5'] = 0.5

        # ---- F6: 振幅稳定性 (权重10%) ----
        # 竞价期间价格振幅越小越稳定(异常大振幅=操纵嫌疑)
        if prices[0] > 0:
            price_range = (max(prices) - min(prices)) / prices[0]
            # range < 1% = 非常稳(1.0), 1~3% = 正常(0.5~0.7), > 5% = 可疑(0.2)
            if price_range < 0.01:
                scores['F6'] = 0.9
            elif price_range < 0.03:
                scores['F6'] = 0.7
            elif price_range < 0.05:
                scores['F6'] = 0.4
            else:
                scores['F6'] = 0.2
        else:
            scores['F6'] = 0.5

        # ---- F7: 尾盘突变检测 (权重15%) ----
        total_change = abs(prices[-1] - prices[0]) if prices[0] > 0 else 0
        late_change = abs(prices[-1] - prices[-3]) if len(prices) >= 3 and prices[-3] > 0 else 0
        if total_change > 0:
            late_ratio = late_change / total_change
            # late_ratio < 0.4 = 涨幅均匀(好), > 0.7 = 尾盘突变(可疑)
            if late_ratio < 0.40:
                scores['F7'] = 0.85  # 均匀分布
            elif late_ratio < 0.60:
                scores['F7'] = 0.55  # 略集中
            elif late_ratio < 0.80:
                scores['F7'] = 0.30  # 明显尾盘突变
            else:
                scores['F7'] = 0.10  # 严重尾盘突变
        else:
            scores['F7'] = 0.5

        # ---- 加权合成 ----
        weights = {'F1': 0.15, 'F2': 0.15, 'F3': 0.20, 'F4': 0.15,
                   'F5': 0.10, 'F6': 0.10, 'F7': 0.15}
        final_score = sum(scores.get(k, 0.5) * w for k, w in weights.items())
        final_score = min(max(final_score, 0.0), 1.0)
        self.auction_scores[stock] = final_score
        return final_score

    def compute_auction_score_jq(self, stock, context):
        """聚宽回测版: 竞价强度评分
        [v9.0.21] 升级: 优先用get_ticks取09:15~09:25的tick序列做完整7因子
        回退: get_call_auction单行数据 → 简化评分
        """
        try:
            today = context.current_dt.date()

            # [v9.0.21] 优先用get_ticks取竞价期间tick序列
            try:
                auction_ticks = get_ticks(stock, count=200,
                                          end_dt='{} 09:25:05'.format(today),
                                          fields=['time', 'current', 'volume', 'money'],
                                          skip=False, df=True)
                if auction_ticks is not None and len(auction_ticks) >= 4:
                    # 过滤09:15~09:25的tick
                    snapshots = []
                    for _, row in auction_ticks.iterrows():
                        p = row.get('current', 0)
                        v = row.get('volume', 0)
                        if p > 0:
                            snapshots.append({
                                'price': p,
                                'volume': v,
                                'money': row.get('money', 0),
                            })
                    if len(snapshots) >= 4:
                        return self.compute_auction_score(stock, snapshots)
            except Exception:
                pass  # get_ticks不可用,回退到get_call_auction

            # 回退: get_call_auction
            ad = get_call_auction(stock,
                                  start_date='{} 09:15:00'.format(today),
                                  end_date='{} 09:26:00'.format(today),
                                  fields=['time', 'current', 'volume', 'money'])
            if ad is None or ad.empty:
                self.auction_scores[stock] = 0.5
                return 0.5

            # 如果返回多行, 做序列分析
            if len(ad) >= 4 and 'current' in ad.columns:
                snapshots = []
                for _, row in ad.iterrows():
                    snapshots.append({
                        'price': row.get('current', 0),
                        'volume': row.get('volume', 0),
                        'money': row.get('money', 0),
                    })
                return self.compute_auction_score(stock, snapshots)

            # 单行数据: 简化评分
            auction_price = ad['current'].iloc[-1] if 'current' in ad.columns else 0
            auction_vol = ad['volume'].iloc[-1] if 'volume' in ad.columns else 0

            if auction_price <= 0:
                self.auction_scores[stock] = 0.5
                return 0.5

            score = 0.5
            h = attribute_history(stock, 5, '1d', ['volume', 'close'])
            if h is not None and len(h) > 0:
                avg_vol = h['volume'].mean()
                if avg_vol > 0:
                    vol_ratio = auction_vol / avg_vol
                    if vol_ratio >= 0.05:
                        score = 0.70
                    elif vol_ratio >= 0.03:
                        score = 0.60
                    elif vol_ratio >= 0.01:
                        score = 0.45
                    else:
                        score = 0.30

                last_close = h['close'].iloc[-1] if 'close' in h.columns else 0
                if last_close > 0:
                    gap = auction_price / last_close - 1
                    if gap > 0.02:
                        score = min(score + 0.1, 1.0)
                    elif gap < -0.01:
                        score = max(score - 0.1, 0.0)

            self.auction_scores[stock] = score
            return score
        except Exception:
            self.auction_scores[stock] = 0.5
            return 0.5

    def get_auction_score(self, stock):
        """获取竞价强度评分(统一接口)"""
        return self.auction_scores.get(stock, 0.5)

    # -----------------------------------------------------------------
    # 模块4: 量能衰竭检测 + OBV背离确认
    # [v9.0.20] 升级: 单一量比→量比+OBV双重确认, 减少误判
    # -----------------------------------------------------------------
    def check_volume_exhaustion(self, stock):
        """检测量能是否衰竭(双重确认)
        [v9.0.20] 条件: 量比衰竭 AND (OBV背离 OR 量比极端)
        [v9.0.25] 优化: 提高tick_count门槛, 降低极端阈值, 缩窄中间带
        返回: True=量能衰竭(应退出), False=量能正常
        """
        track = self.tick_tracks.get(stock)
        if not track or track['tick_count'] < 60:   # v9.0.25: 60 (was 30), 至少2分钟数据
            return False

        open_vol_avg = track.get('open_vol_avg', 0)
        if open_vol_avg <= 0:
            return False

        window = min(self.volume_exhaust_window, len(track['volumes']))
        recent_vols = track['volumes'][-window:]
        recent_avg = sum(recent_vols) / len(recent_vols) if recent_vols else 0
        if recent_avg <= 0:
            return False

        decay_ratio = recent_avg / open_vol_avg

        # [v9.0.25] 量比极端 (<10%) → 直接判定衰竭 (v9.0.20: 15%)
        if decay_ratio < 0.10:
            return True

        # 量比不算衰竭 → 正常
        if decay_ratio >= self.volume_exhaust_ratio:
            return False

        # [v9.0.25] 量比在10%~20%之间 → 必须OBV背离确认
        obv_divergence = self._check_obv_divergence(stock)
        return obv_divergence

    def _check_obv_divergence(self, stock):
        """检测OBV背离: 价格接近/创新高但OBV远低于最高值
        [v9.0.20] 新增
        返回: True=OBV背离(量能虚弱), False=无背离
        """
        track = self.tick_tracks.get(stock)
        if not track:
            return False

        curr_price = track['prices'][-1] if track['prices'] else 0
        intraday_high = track['high']
        obv = track.get('obv', 0)
        obv_high = track.get('obv_high', 0)

        if intraday_high <= 0 or obv_high <= 0:
            return False

        # 价格接近高点(回撤<1.5%)
        price_near_high = (intraday_high - curr_price) / intraday_high < 0.015

        # OBV远低于最高值(低于70%)
        obv_weak = obv < obv_high * 0.70

        return price_near_high and obv_weak

    def get_volume_decay_ratio(self, stock):
        """获取量能衰减比 (当前/开盘)"""
        track = self.tick_tracks.get(stock)
        if not track or track.get('open_vol_avg', 0) <= 0:
            return 1.0
        window = min(self.volume_exhaust_window, len(track['volumes']))
        recent_vols = track['volumes'][-window:]
        recent_avg = sum(recent_vols) / len(recent_vols) if recent_vols else 0
        return recent_avg / track['open_vol_avg'] if track['open_vol_avg'] > 0 else 1.0

    def get_obv_divergence_info(self, stock):
        """获取OBV背离信息(用于日志)"""
        track = self.tick_tracks.get(stock)
        if not track:
            return {'divergence': False}
        obv_high = track.get('obv_high', 0)
        obv = track.get('obv', 0)
        obv_ratio = obv / obv_high if obv_high > 0 else 1.0
        return {
            'divergence': self._check_obv_divergence(stock),
            'obv': obv,
            'obv_high': obv_high,
            'obv_ratio': obv_ratio,
        }

    # -----------------------------------------------------------------
    # 综合质量评分
    # -----------------------------------------------------------------
    def get_quality_score(self, stock):
        """综合质量评分 0~1
        [v9.0.20] 4维度加权: L2流向 + 竞价强度 + Tick回撤 + OBV健康
        [v9.0.25] 优化: L2无数据时降权重给竞价, 加价格动量加分, 放宽回撤惩罚
        无数据的维度用0.5(中性)填充
        """
        l2_score = self.get_l2_score(stock)
        auction_score = self.get_auction_score(stock)

        # 判断L2数据是否真实(非默认0.5)
        l2_data = self.l2_flow.get(stock)
        has_l2 = l2_data is not None and l2_data.get('last_update', 0) > 0

        # Tick回撤评分: 从高点回撤越少分越高
        track = self.tick_tracks.get(stock)
        if track and track['high'] > 0 and track.get('first_price', 0) > 0:
            drawdown = 1.0 - (track['prices'][-1] / track['high']) if track['prices'] else 0
            # [v9.0.25] 放宽回撤惩罚: 5%回撤才归零 (v9.0.20: 3%)
            dd_score = max(1.0 - drawdown / 0.05, 0.0)
        else:
            dd_score = 0.5

        # OBV健康度: OBV越接近最高值越健康
        if track and track.get('obv_high', 0) > 0:
            obv_ratio = track['obv'] / track['obv_high']
            obv_score = min(max(obv_ratio, 0.0), 1.0)
        else:
            obv_score = 0.5

        # [v9.0.25] 价格动量加分: 开盘以来涨幅越大,质量越好
        momentum_bonus = 0.0
        if track and track.get('first_price', 0) > 0 and track['prices']:
            intraday_return = track['prices'][-1] / track['first_price'] - 1
            if intraday_return > 0.02:
                momentum_bonus = min(intraday_return * 2, 0.15)  # 最多加0.15

        # [v9.0.25] 动态权重: L2数据可用时35%, 不可用时降到15%,多出的20%给竞价
        if has_l2:
            quality = l2_score * 0.35 + auction_score * 0.30 + dd_score * 0.20 + obv_score * 0.15
        else:
            quality = l2_score * 0.15 + auction_score * 0.50 + dd_score * 0.20 + obv_score * 0.15

        quality = min(quality + momentum_bonus, 1.0)
        return quality

    def should_block_buy(self, stock):
        """是否应阻止买入(quality太低)"""
        return self.get_quality_score(stock) < self.quality_block

    def should_reduce_position(self, stock):
        """是否应降低仓位(quality偏低)"""
        q = self.get_quality_score(stock)
        return q < self.quality_reduce and q >= self.quality_block


# 全局实例(在initialize中初始化)
_tick_engine = None

def get_tick_engine():
    """获取TickSignalEngine实例"""
    global _tick_engine
    if _tick_engine is None:
        _tick_engine = TickSignalEngine()
    return _tick_engine


# =============================================================================
# [v9.0.21] 聚宽版Tick引擎更新 — 分钟调度中按需调get_ticks
#
# 保持frequency='minute', 在止损/补仓节点用get_ticks取tick数据
# 每次调用get_ticks取最近60~120条(约5~10分钟), 内存友好
# =============================================================================

def _jq_tick_engine_update(context):
    """[v9.0.21] 聚宽回测: 用get_ticks更新TickSignalEngine
    在minute_stop_loss_all和_trade_A_stage2中调用
    """
    engine = get_tick_engine()
    if not engine.enabled or engine.is_qmt:
        return  # QMT走tick_monitor, 不走这里

    try:
        positions = context.portfolio.positions
        stocks_to_track = list(positions.keys()) if positions else []

        # 也追踪pending_stage2的候选
        if hasattr(g, 'pending_stage2_buys'):
            stocks_to_track.extend(g.pending_stage2_buys.keys())
        stocks_to_track = list(set(stocks_to_track))

        if not stocks_to_track:
            return

        for stock in stocks_to_track:
            try:
                # 更新tick轨迹(价格+成交量+OBV)
                engine.update_tick_track_jq(stock, context)
                # 更新L2流向(盘口OIR+主动买卖)
                engine.update_l2_flow_jq(stock, context)
            except Exception:
                pass
    except Exception as e:
        log.debug("_jq_tick_engine_update异常: {}".format(e))


# =============================================================================
# [v9.0.19] Tick级监控 — QMT实盘专用(3秒级)
#
# 替代: minute_stop_loss_all(每2分钟) + _trade_A_stage2(每1分钟)
# 聚宽回测仍走原来的schedule调度，不受影响
# =============================================================================
_tick_last_check_time = 0.0     # 上次tick检查时间戳
_tick_last_prices = {}          # {stock: last_price} 用于价格变化检测
_tick_check_count = 0           # tick检查计数器(日志限频)

def tick_monitor(context):
    """QMT实盘tick级监控入口 — 由qmt_main.py主循环每3秒调用
    功能: 止损检查 + A补仓确认 + pending_exit重试 + 信号引擎更新
    """
    global _tick_last_check_time, _tick_check_count

    try:
        now = time.time()
        # 防重入: 距离上次检查不足2秒则跳过
        if now - _tick_last_check_time < 2.0:
            return
        _tick_last_check_time = now

        dt_now = context.current_dt
        hour = dt_now.hour
        minute = dt_now.minute

        # 仅在交易时段运行: 09:30~11:30, 13:00~15:00
        in_morning = (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30)
        in_afternoon = (hour == 13) or (hour == 14) or (hour == 15 and minute == 0)
        if not in_morning and not in_afternoon:
            return

        _tick_check_count += 1

        # --- [v9.0.19] 信号引擎更新: L2流向 + Tick轨迹 ---
        _tick_engine_update(context)

        # --- 止损(含移动止损+量能衰竭) + pending_exit重试 ---
        if hour == 9 and minute >= 32 or hour >= 10:
            _tick_stop_loss_check(context)

        # --- A补仓确认(仅09:33~09:45窗口, 含quality_score) ---
        if hour == 9 and 33 <= minute <= 45:
            _tick_stage2_check(context)

    except Exception as e:
        log.error("tick_monitor异常: {}".format(e))


def _tick_engine_update(context):
    """更新TickSignalEngine的L2流向和Tick轨迹"""
    engine = get_tick_engine()
    if not engine.enabled:
        return

    try:
        positions = context.portfolio.positions
        if not positions:
            return

        current_data = get_current_data()
        stocks_to_track = list(positions.keys())

        # 也追踪pending_stage2的候选
        if hasattr(g, 'pending_stage2_buys'):
            stocks_to_track.extend(g.pending_stage2_buys.keys())
        stocks_to_track = list(set(stocks_to_track))

        # 批量取tick
        if hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(stocks_to_track)
            except Exception:
                pass

        for stock in stocks_to_track:
            try:
                cd_item = current_data[stock]
                curr_price = cd_item.last_price
                if curr_price is None or curr_price <= 0:
                    continue

                # 更新Tick轨迹(价格+成交量)
                # 用day volume差值估算本tick成交量
                tick_snap = get_tick_snapshot([stock])
                tick_vol = tick_snap.get(stock, {}).get('volume', 0) if tick_snap else 0
                engine.update_tick_track(stock, curr_price, tick_vol)

                # 更新L2大单流向(仅QMT且L2可用)
                if engine.is_qmt and _tick_check_count % 5 == 0:
                    # L2查询较重，每15秒更新一次(每5个tick)
                    engine.update_l2_flow(stock, context)

            except Exception:
                pass
    except Exception as e:
        log.debug("_tick_engine_update异常: {}".format(e))


def _tick_stop_loss_check(context):
    """Tick级止损检查 — 从minute_stop_loss_all提取，每3秒执行"""
    global _tick_last_prices

    try:
        positions = context.portfolio.positions
        if not positions:
            return

        # Step0: pending_exit重试
        pending_retry_stocks = []
        for stock in list(positions.keys()):
            meta = g.positions_meta.get(stock)
            if not meta or not meta.get('pending_exit', False):
                continue
            pos = positions[stock]
            if pos.closeable_amount <= 0:
                continue
            pending_retry_stocks.append(stock)

        # Step1: 预筛有效止损候选
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
            except Exception:
                pass

        all_need_tick = list(set(pending_retry_stocks + candidate_stocks))
        if not all_need_tick:
            return

        # Step2: 批量取tick
        current_data = get_current_data()
        if hasattr(current_data, 'get_batch'):
            try:
                current_data.get_batch(all_need_tick)
            except Exception:
                pass

        # Step2.5: pending_exit重试(跌停跳过, 每天最多5次, 10秒限频)
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
                        log.info("🔁【Tick待退出跳过】{} 跌停中，明天再试".format(stock))
                    meta['_exit_retry_count'] = 5
                    meta['_exit_retry_date'] = today
                    continue
                # 限频: 同一只股票10秒内不重复下单
                last_retry_time = meta.get('_last_retry_time', 0)
                if time.time() - last_retry_time < 10:
                    continue
                if order_target_value(stock, 0) is not None:
                    meta['_last_retry_time'] = time.time()
                    meta['_exit_retry_count'] = retry_count + 1
                    meta['_exit_retry_date'] = today
                    log.info("🔁【Tick待退出重试】{} 第{}次尝试清仓".format(stock, retry_count + 1))
                    diag_add('retry_pending_exit')
            except Exception as e:
                log.warning("Tick pending_exit重试异常 {}: {}".format(stock, e))

        # Step3: 止损判断 — 仅在价格有变化时触发(避免重复日志)
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

                # 价格无变化跳过(减少重复计算)
                prev_price = _tick_last_prices.get(stock, 0)
                if curr_price == prev_price:
                    continue
                _tick_last_prices[stock] = curr_price

                avg_cost = pos.avg_cost
                if avg_cost is None or avg_cost <= 0:
                    continue

                pnl = curr_price / avg_cost - 1
                stop_pct = _get_stop_level(strategy, entry_type)
                engine = get_tick_engine()
                exit_reason = None

                # 检查1: 固定止损(原逻辑)
                if pnl <= -stop_pct:
                    exit_reason = 'tick_stop_loss'
                    log.info("🚨【Tick止损】{} strategy={} pnl={:.2f}% stop={:.2f}%".format(
                        stock, strategy, pnl * 100, stop_pct * 100))

                # [v9.0.25] 检查2: ATR自适应移动止损(带趋势加速保护+时段过滤)
                # [v9.0.25] 由配置开关控制, 默认关闭
                if exit_reason is None and engine.enabled and g.cfg.get('enable_atr_trailing_stop', False):
                    trailing_price = engine.get_trailing_stop_price(stock, strategy, avg_cost)
                    if trailing_price and curr_price < trailing_price:
                        suppress = False
                        track = engine.tick_tracks.get(stock, {})
                        if track and len(track.get('prices', [])) >= 30:
                            recent = track['prices'][-30:]
                            mid = len(recent) // 2
                            first_half_chg = (recent[mid] - recent[0]) / recent[0] if recent[0] > 0 else 0
                            second_half_chg = (recent[-1] - recent[mid]) / recent[mid] if recent[mid] > 0 else 0
                            if second_half_chg > first_half_chg and second_half_chg > 0.002:
                                suppress = True
                        now_hm = context.current_dt.strftime('%H:%M') if hasattr(context.current_dt, 'strftime') else '10:00'
                        if now_hm < '10:00' and strategy == 'A':
                            suppress = True
                        if not suppress:
                            atr = engine.atr_cache.get(stock, 0)
                            exit_reason = 'trailing_stop'
                            log.info("📉【ATR移动止盈】{} strategy={} 高点={:.2f} 止盈线={:.2f} 现价={:.2f} ATR={:.3f} pnl={:+.2f}%".format(
                                stock, strategy, track.get('high', 0), trailing_price, curr_price, atr, pnl * 100))

                # [v9.0.25] 检查3: 量能衰竭+OBV背离(主动退出, 提高盈利门槛+冷却)
                # [v9.0.25] 由配置开关控制, 默认关闭
                if exit_reason is None and engine.enabled and g.cfg.get('enable_volume_exhaustion', False) and pnl > 0.04:
                    cooldown_ok = True
                    last_trigger = engine.vol_exhaust_cooldown.get(stock, 0)
                    if time.time() - last_trigger < engine.vol_exhaust_cooldown_sec:
                        cooldown_ok = False
                    if cooldown_ok and engine.check_volume_exhaustion(stock):
                        decay = engine.get_volume_decay_ratio(stock)
                        obv_info = engine.get_obv_divergence_info(stock)
                        exit_reason = 'volume_exhaustion'
                        engine.vol_exhaust_cooldown[stock] = time.time()
                        log.info("📊【量能衰竭】{} strategy={} 量比={:.1f}% OBV背离={} OBV比={:.1f}% pnl={:+.2f}% 主动退出".format(
                            stock, strategy, decay * 100,
                            obv_info.get('divergence', False),
                            obv_info.get('obv_ratio', 1.0) * 100,
                            pnl * 100))

                # 执行退出
                if exit_reason:
                    security_name = getattr(cd_item, 'name', stock)
                    if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=pnl):
                        diag_add('{}_sell_all'.format(strategy))
                        if exit_reason in ('tick_stop_loss', 'minute_stop_loss'):
                            diag_add('stop_loss_triggered')
                        elif exit_reason == 'trailing_stop':
                            diag_add('trailing_stop_triggered')
                        elif exit_reason == 'volume_exhaustion':
                            diag_add('volume_exhaust_triggered')

            except Exception as e:
                log.error("Tick止损处理异常 {}: {}".format(stock, e))

    except Exception as e:
        log.error("_tick_stop_loss_check异常: {}".format(e))


def _tick_stage2_check(context):
    """Tick级A补仓确认 — 从_trade_A_stage2_impl提取，09:33~09:45每3秒检查"""
    try:
        if not hasattr(g, 'pending_stage2_buys') or not g.pending_stage2_buys:
            return

        cd = get_current_data()
        now_minute = context.current_dt.minute if hasattr(context.current_dt, 'minute') else 35
        is_last_check = (now_minute >= 45)

        # 批量预取
        stage2_stocks = list(g.pending_stage2_buys.keys())
        if hasattr(cd, 'get_batch'):
            try:
                cd.get_batch(stage2_stocks)
            except Exception:
                pass

        for stock in list(g.pending_stage2_buys.keys()):
            info = g.pending_stage2_buys[stock]

            if stock not in context.portfolio.positions:
                del g.pending_stage2_buys[stock]
                continue

            curr_price = cd[stock].last_price
            if curr_price <= 0:
                del g.pending_stage2_buys[stock]
                continue

            first_price = info['first_price']
            open_price = info['open_price']

            # 二段确认条件: 3条中满足2条即补仓
            confirm = 0
            if curr_price >= first_price * 0.998:
                confirm += 1
            if open_price > 0 and curr_price >= open_price * 0.998:
                confirm += 1
            if open_price > 0:
                intraday_high_est = max(open_price, first_price, curr_price)
                if intraday_high_est > 0 and curr_price / intraday_high_est >= 0.99:
                    confirm += 1
            else:
                confirm += 1

            # [v9.0.19] quality_score作为第4维度
            engine = get_tick_engine()
            quality = engine.get_quality_score(stock) if engine.enabled else 1.0

            # 质量太低 → 直接放弃补仓(保持半仓)
            if engine.enabled and engine.should_block_buy(stock):
                meta = g.positions_meta.get(stock, {})
                if meta:
                    meta['stage'] = 'half_final'
                log.info("❌【质量拦截补仓】{} quality={:.2f} 虚假强势, 放弃补仓→half_final".format(
                    stock, quality))
                del g.pending_stage2_buys[stock]
                continue

            if confirm >= 2:
                remaining = info['target_value'] - info['bought_value']
                # [v9.0.19] quality偏低时补仓金额减半
                if engine.enabled and engine.should_reduce_position(stock):
                    remaining = remaining * 0.5
                    log.info("⚠️【质量降仓补仓】{} quality={:.2f} 补仓减半".format(stock, quality))

                buy_value = min(context.portfolio.available_cash, remaining)
                if buy_value > 0 and buy_value / curr_price >= 100:
                    od = order_value(stock, buy_value)
                    if od is not None:
                        meta = g.positions_meta.get(stock, {})
                        if meta:
                            meta['pending_stage2_confirm'] = True
                            meta['pending_stage2_confirm_date'] = context.current_dt.date()
                            meta['stage2_order_id'] = od if isinstance(od, int) else getattr(od, 'order_id', None)
                            meta['stage2_target_value'] = info['target_value']
                            log.info("✅【Tick A补仓】{} 09:{:02d}确认仍强({}/3 q={:.2f}), 补买{:.0f}元".format(
                                stock, now_minute, confirm, quality, buy_value))
                        del g.pending_stage2_buys[stock]
                    else:
                        meta = g.positions_meta.get(stock, {})
                        if meta:
                            meta['stage'] = 'half_final'
                        log.info("⚠️【Tick A补仓】{} 09:{:02d}下单失败, stage→half_final".format(stock, now_minute))
                        del g.pending_stage2_buys[stock]
                else:
                    meta = g.positions_meta.get(stock, {})
                    if meta:
                        meta['stage'] = 'half_final'
                    log.info("⚠️【Tick A补仓】{} 09:{:02d}资金不足, stage→half_final".format(stock, now_minute))
                    del g.pending_stage2_buys[stock]
            elif is_last_check:
                meta = g.positions_meta.get(stock, {})
                if meta:
                    meta['stage'] = 'half_final'
                log.info("❌【Tick A超时】{} 09:45仍不满足({}/3), stage→half_final".format(stock, confirm))
                del g.pending_stage2_buys[stock]
            # tick模式下不打印"等待"日志(3秒一次太刷屏), 每分钟打一次
            elif _tick_check_count % 20 == 0:
                log.info("⏳【Tick A等待】{} 09:{:02d}确认不足({}/3), 继续观察".format(stock, now_minute, confirm))

    except Exception as e:
        log.error("_tick_stage2_check异常: {}".format(e))


# =============================================================================
# 第二层: 框架核心 (Framework)
# =============================================================================

def initialize(context):
    log.info("=== V1.0.0 战车A 启动 ===")
    set_benchmark('000852.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_slippage(FixedSlippage(0.02))

    # [v9.0.17] 环境检测: QMT实盘 vs 聚宽回测
    try:
        from xtquant import xtdata
        g.is_qmt = True
        log.info("运行环境: QMT实盘 (二次确认+二段买入已启用)")
    except ImportError:
        g.is_qmt = False
        log.info("运行环境: 聚宽回测 (二次确认已关闭, 直接满仓; 二段买入已跳过)")

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

    # [v9.0.19] Tick信号引擎初始化
    engine = get_tick_engine()
    engine.is_qmt = g.is_qmt
    engine.enabled = True
    if g.is_qmt:
        log.info("[TickEngine] QMT模式: L2大单+Tick移动止损+竞价强度+量能衰竭")
    else:
        log.info("[TickEngine] 聚宽模式: 竞价近似+分钟线降级(L2/Tick不可用)")

    # 调度注册
    schedule_all(context)

    # 回测统计
    g.bt = {
        'version': 'V1.0.0_A', 'start_cash': context.portfolio.starting_cash,
        'trade_days': 0, 'closed_trades': 0, 'wins': 0, 'losses': 0,
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
            'dragon_abs_stop_loss': 'A_dragon_abs_stop_loss',
            'dragon_max_hold': 'A_dragon_max_hold',
            'dragon_pos_ratio': 'A_dragon_pos_ratio',
            'dragon_bear_pos_ratio': 'A_dragon_bear_pos_ratio',
            'dragon_min_profit_protect': 'A_dragon_min_profit_protect',
            'dragon_max_open_ratio': 'A_dragon_max_open_ratio',
            'stop_by_ma': 'A_stop_by_ma',
            'partial_tp_threshold': 'A_partial_tp_threshold',
            'partial_tp_lock_ratio': 'A_partial_tp_lock_ratio',
            'strict_max_hold': 'A_strict_max_hold',
            'strict_pos_ratio': 'A_strict_pos_ratio',
            'neutral_recover_max_hold': 'A_neutral_recover_max_hold',
            'neutral_recover_pos_ratio': 'A_neutral_recover_pos_ratio',
            'deep_dd_trigger_level': 'A_deep_dd_trigger_level',
            'dd_pause_days': 'A_dd_pause_days',
            'dd_rearm_recovery': 'A_dd_rearm_recovery',
            'deadlock_flat_days': 'A_deadlock_flat_days',
            'bear_crowding_max_hold': 'A_bear_crowding_max_hold',
            'bear_crowding_pos_ratio': 'A_bear_crowding_pos_ratio',
            'open_time': 'A_open_time',
            'dd_rearm_level': 'A_dd_rearm_level',
            'deep_dd_cooldown_days': 'A_deep_dd_cooldown_days',
            'dragon_min_ret_3d': 'A_dragon_min_ret_3d',
            'dragon_partial_take_profit': 'A_dragon_partial_take_profit',
            'max_prev_money': 'A_max_prev_money',
            'min_auction_volume_ratio': 'A_min_auction_volume_ratio',
            'min_prev_money': 'A_min_prev_money',
            'partial_take_profit_firstboard': 'A_partial_take_profit_firstboard',
            'partial_take_profit_weak': 'A_partial_take_profit_weak',
            'limit_up_buffer': 'A_limit_up_buffer',
            'dragon_min_score': 'A_dragon_min_score',
            'dragon_min_open_ratio': 'A_dragon_min_open_ratio',
            'dragon_bear_allow_deep_water': 'A_dragon_bear_allow_deep_water',
            'dragon_deep_water_max_open_ratio': 'A_dragon_deep_water_max_open_ratio',
            'normal_min_score': 'A_normal_min_score',
            'normal_min_open_ratio': 'A_normal_min_open_ratio',
            'normal_firstboard_bonus': 'A_normal_firstboard_bonus',
            'normal_weak_bonus': 'A_normal_weak_bonus',
            'strict_min_score': 'A_strict_min_score',
            'strict_min_open_ratio': 'A_strict_min_open_ratio',
            'strict_firstboard_bonus': 'A_strict_firstboard_bonus',
            'strict_weak_bonus': 'A_strict_weak_bonus',
        },
    }
    for strat_name, mapping in key_map.items():
        strat_cfg = g.strategies[strat_name]['config']
        for local_key, global_key in mapping.items():
            if local_key in strat_cfg:
                g.cfg[global_key] = strat_cfg[local_key]


def schedule_all(context):
    """统一调度注册
    [v9.0.19] QMT实盘: 止损+补仓+重试由tick_monitor接管(3秒级)
              聚宽回测: 保持分钟级schedule调度(无tick订阅)
    """
    cfg = g.cfg
    is_tick_mode = getattr(g, 'is_qmt', False)  # QMT实盘用tick, 聚宽用schedule

    run_daily(morning_prepare, '09:00')
    run_daily(post_auction_prepare, '09:28')
    run_daily(gap_down_stop_loss, '09:31')
    run_daily(gap_down_confirm, '09:35')
    run_daily(_trade_A, '09:32')

    # A补仓窗口
    if not is_tick_mode:
        for minute in range(33, 46):
            run_daily(_trade_A_stage2, '09:%02d' % minute)
    else:
        run_daily(_trade_A_stage2, '09:45')
        log.info("[TickMode] A补仓窗口: tick模式(3秒级), 09:45兜底")

    run_daily(orphan_sweeper_execute, '11:26')
    run_daily(_sell_A_1, '11:20')
    run_daily(_sell_A_2, '14:50')

    # 止损: QMT由tick_monitor接管, 聚宽保留每2分钟schedule
    if not is_tick_mode:
        for hour in range(9, 15):
            for minute in range(0, 60, 2):
                t = '%02d:%02d' % (hour, minute)
                if ('09:32' <= t <= '11:28') or ('13:00' <= t <= '14:56'):
                    run_daily(minute_stop_loss_all, t)
    else:
        log.info("[TickMode] 止损: tick模式(3秒级), 替代每2分钟schedule")

    run_daily(after_market_close, '15:10')


# --- 聚宽 run_daily 不支持 lambda，用具名函数包装 ---
def _trade_A(context):
    try:
        strategy_trade(context, 'A')
    except Exception as e:
        log.error("_trade_A异常: {}".format(e))


def _trade_A_stage2(context):
    """A策略二段补仓: 09:33~09:45窗口内每分钟检查
    [v9.0.17] 满足条件立刻补仓并移除; 不满足则等下一分钟;
    09:45仍未补仓→标记half_final并移除
    """
    try:
        _trade_A_stage2_impl(context)
    except Exception as e:
        log.error("_trade_A_stage2异常: {}".format(e))

def _trade_A_stage2_impl(context):
    if not hasattr(g, 'pending_stage2_buys') or not g.pending_stage2_buys:
        return

    # [v9.0.21] 聚宽: 更新tick引擎(为quality_score提供实时数据)
    # [v9.0.25] stage2确认逻辑只用价格对比, 不需要quality_score, 跳过引擎更新
    # 每个回测日省去09:33-09:45共13次×N只×2次get_ticks()调用

    cd = get_current_data()
    now_minute = context.current_dt.minute if hasattr(context.current_dt, 'minute') else 35
    is_last_check = (now_minute >= 45)  # 09:45是最后一次检查

    for stock in list(g.pending_stage2_buys.keys()):
        info = g.pending_stage2_buys[stock]

        if stock not in context.portfolio.positions:
            del g.pending_stage2_buys[stock]
            continue

        curr_price = cd[stock].last_price
        if curr_price <= 0:
            del g.pending_stage2_buys[stock]
            continue

        first_price = info['first_price']
        open_price = info['open_price']

        # 二段确认条件: 3条中满足2条即补仓
        confirm = 0
        if curr_price >= first_price * 0.998:
            confirm += 1
        if open_price > 0 and curr_price >= open_price * 0.998:
            confirm += 1
        if open_price > 0:
            intraday_high_est = max(open_price, first_price, curr_price)
            if intraday_high_est > 0 and curr_price / intraday_high_est >= 0.99:
                confirm += 1
        else:
            confirm += 1

        if confirm >= 2:
            # 满足条件 → 立刻补仓
            remaining = info['target_value'] - info['bought_value']
            buy_value = min(context.portfolio.available_cash, remaining)
            if buy_value > 0 and buy_value / curr_price >= 100:
                od = order_value(stock, buy_value)
                if od is not None:
                    meta = g.positions_meta.get(stock, {})
                    if meta:
                        if getattr(g, 'is_qmt', False):
                            meta['pending_stage2_confirm'] = True
                            meta['pending_stage2_confirm_date'] = context.current_dt.date()
                            meta['stage2_order_id'] = od if isinstance(od, int) else getattr(od, 'order_id', None)
                            meta['stage2_target_value'] = info['target_value']
                            log.info("✅【A二段补仓】{} 09:{:02d}确认仍强({}/3), 补买{:.0f}元 (待成交确认)".format(
                                stock, now_minute, confirm, buy_value))
                        else:
                            meta['stage'] = 'full'
                            log.info("✅【A二段补仓】{} 09:{:02d}确认仍强({}/3), 补买{:.0f}元, stage→full".format(
                                stock, now_minute, confirm, buy_value))
                    del g.pending_stage2_buys[stock]
                else:
                    meta = g.positions_meta.get(stock, {})
                    if meta:
                        meta['stage'] = 'half_final'
                    log.info("⚠️【A二段补仓】{} 09:{:02d}下单失败, stage→half_final".format(stock, now_minute))
                    del g.pending_stage2_buys[stock]
            else:
                meta = g.positions_meta.get(stock, {})
                if meta:
                    meta['stage'] = 'half_final'
                log.info("⚠️【A二段补仓】{} 09:{:02d}资金不足, stage→half_final".format(stock, now_minute))
                del g.pending_stage2_buys[stock]
        elif is_last_check:
            # 09:45最后一次检查仍不满足 → 放弃
            meta = g.positions_meta.get(stock, {})
            if meta:
                meta['stage'] = 'half_final'
            log.info("❌【A二段超时】{} 09:45仍不满足({}/3), stage→half_final".format(stock, confirm))
            del g.pending_stage2_buys[stock]
        else:
            # 未满足但还没到最后 → 继续等下一分钟
            log.info("⏳【A二段等待】{} 09:{:02d}确认不足({}/3), 继续观察".format(stock, now_minute, confirm))


def _sell_A_1(context):
    try:
        strategy_sell_only(context, 'A')
    except Exception as e:
        log.error("_sell_A_1异常: {}".format(e))

def _sell_A_2(context):
    try:
        strategy_sell_only(context, 'A')
    except Exception as e:
        log.error("_sell_A_2异常: {}".format(e))


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

    # --- 统一评分系统 ---
    g.csi1000_percentile = 0.5
    g.recent_volatility = 0.015
    g.env_weights = {
        'dragon_follow': 1.0, 'firstboard_lowopen': 1.0,
        'firstboard': 1.0, 'weak_to_strong': 1.0,
    }
    g.unified_min_threshold = 0.003
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
    g.dragon_circuit_breaker_pause_left = 0
    g.dragon_loss_history = []              # 追踪连亏幅度，用于平均亏损门槛
    g.dragon_reduced_pos_active = False     # [改进2] 连亏降仓标记
    g.dragon_bear_weekly_count = 0
    g.dragon_bear_weekly_reset_countdown = 0

    # --- DPM ---
    g.dpm_expanded_today = False
    g.dpm_current_max_positions = g.cfg['max_total_positions']
    g.dpm_current_max_pos_ratio = g.cfg['max_portfolio_position_ratio']
    g.dpm_A_avg_profit = 0.0

    # --- 持仓管理 ---
    g.positions_meta = {}
    g.pending_buys = {}
    g.pending_stage2_buys = {}  # 二段买入待确认列表
    g.cooldown = {}
    g.strategy_budget = {'A': {}}

    # --- 全局控制 ---
    g.no_new_position_today = False
    g.daily_new_position_count = 0
    g.limit_up_cache = []
    g.limit_up_cache_date = None

    # --- A策略状态 ---
    g.A_dd_cooldown_active = False
    g.A_pause_days_left = 0
    g.A_dd_rearm_ready = True
    g.A_rearm_grace_days_left = 0
    g.A_flat_days = 0

    # --- 趋势过滤系统 ---
    g.market_trend = 'sideways'          # 大盘趋势: up/down/sideways
    g.intraday_panic_active = False      # 盘中大跌标记(不再拦截,由趋势过滤器处理)

    # --- Panic状态(保留兼容,简化) ---
    g.panic_scout_active = False
    g.panic_scout_enabled_today = False
    g.panic_scout_level = 'none'
    g.panic_scout_max_hold = 0
    g.panic_scout_pos_ratio = 0.0
    g.panic_scout_min_open_ratio = 0.0
    g.panic_yesterday_ret = 0.0

    # --- 诊断 ---
    g.diag = {}


# =============================================================================
# 第四层: 通用引擎 (Common Engine)
# =============================================================================

# ---------- 通用卖出引擎 ----------

def strategy_sell_only(context, strategy_name):
    """通用卖出流程：遍历该策略持仓，调用策略的sell_rules"""
    strat = g.strategies[strategy_name]
    sell_rules = strat['handlers']['sell_rules']
    current_data = get_current_data()

    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta or meta.get('strategy') != strategy_name:
            continue
        if meta.get('pending_exit', False):
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

        # 构建卖出信号上下文
        sell_ctx = {
            'stock': stock, 'curr_price': curr_price, 'avg_cost': avg_cost,
            'pnl': pnl, 'stage': meta.get('stage', 'full'),
            'entry_type': meta.get('entry_type', ''),
            'prev_close': h['close'].iloc[-1],
            'ma5_est': (h['close'].iloc[-4:].sum() + curr_price) / 5.0,
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
            log.info("{} reason={} ret={:.2f}%".format(stock, reason, pnl * 100))

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
                log.info("{} reason={} ret={:.2f}% (半仓→全仓:剩余不足100股)".format(
                    stock, reason, pnl * 100))
        else:
            next_stage = signal.get('next_stage', 'half')
            if half_amount > 0:
                if submit_partial_stage_change(stock, half_amount, next_stage, context, reason=reason):
                    diag_add('{}_sell_partial'.format(meta.get('strategy', '?')))
                    log.info("{} reason={} ret={:.2f}%".format(stock, reason, pnl * 100))


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


def execute_buy_orders(context, scored, strategy_name, budget, slots_left):
    """通用下单执行"""
    for item in scored:
        if slots_left <= 0 or g.daily_new_position_count >= g.cfg['max_daily_new_positions']:
            break

        # 仓位上限检查
        if context.portfolio.total_value > 0:
            a_value = sum(
                pos.value for stock, pos in context.portfolio.positions.items()
                if g.positions_meta.get(stock, {}).get('strategy', '') == 'A'
            )
            if a_value / context.portfolio.total_value >= g.dpm_current_max_pos_ratio:
                log.info("⚠️【{}中止买入】A仓位上限 {:.0f}%".format(
                    strategy_name, g.dpm_current_max_pos_ratio * 100))
                break

        stock = item['stock']
        curr_price = item['curr_price']
        if stock in context.portfolio.positions or stock in g.pending_buys \
                or in_cooldown(stock, context) or not can_open_position(context, curr_price):
            continue

        # ============================================================
        # [v9.0.17] 买入前二次确认 (仅A策略, 环境分离)
        # 聚宽回测: 关闭确认, 直接满仓(回测不存在冲高回落风险)
        # QMT实盘: 保留确认, confirm>=2满仓, =1半仓, =0放弃
        # ============================================================
        if strategy_name == 'A':
            if getattr(g, 'is_qmt', False):
                # QMT实盘: 执行二次确认
                cd = get_current_data()
                open_price = cd[stock].day_open
                confirm_score = 0

                # 条件1: 不破开盘价
                if open_price > 0 and curr_price >= open_price * 0.998:
                    confirm_score += 1

                # 条件2: 从开盘价回撤不超过1.2%
                if open_price > 0:
                    intraday_high_est = max(open_price, curr_price)
                    if intraday_high_est > 0 and curr_price / intraday_high_est >= 0.988:
                        confirm_score += 1
                else:
                    confirm_score += 1

                # 条件3: 不低于竞价价
                auction_price = item.get('auction_price', 0)
                if auction_price > 0:
                    if curr_price >= auction_price * 0.995:
                        confirm_score += 1
                else:
                    confirm_score += 1

                # [v9.0.19] 竞价+L2质量评分
                engine = get_tick_engine()
                quality = engine.get_quality_score(stock) if engine.enabled else 1.0
                auction_q = engine.get_auction_score(stock) if engine.enabled else 0.5
                l2_q = engine.get_l2_score(stock) if engine.enabled else 0.5

                log.info("🔍【A确认观察】{} confirm={}/3 quality={:.2f}(竞价={:.2f} L2={:.2f}) "
                         "open={:.2f} curr={:.2f} auction={:.2f} curr/open={:+.1%}".format(
                    stock, confirm_score, quality, auction_q, l2_q,
                    open_price, curr_price,
                    auction_price, curr_price/open_price - 1 if open_price > 0 else 0))

                # [v9.0.19] quality_score过低 → 阻止/降级(无论confirm多高)
                if engine.enabled and engine.should_block_buy(stock):
                    log.info("❌【质量拦截】{} quality={:.2f}<{:.2f} 虚假强势, 放弃买入".format(
                        stock, quality, engine.quality_block))
                    continue

                # [CQTO五轮] 放宽: confirm>=2满仓, =1半仓, =0放弃
                if confirm_score >= 2:
                    pos_scale = 1.0
                    # [v9.0.19] quality偏低时降为半仓
                    if engine.enabled and engine.should_reduce_position(stock):
                        pos_scale = 0.5
                        log.info("⚠️【质量降仓】{} quality={:.2f} confirm=2但质量偏低, 降为半仓".format(
                            stock, quality))
                elif confirm_score == 1:
                    pos_scale = 0.5
                    log.info("⚠️【A二次确认】{} confirm={}/3, 降为半仓".format(stock, confirm_score))
                else:
                    log.info("❌【A二次确认】{} confirm=0/3, 放弃买入".format(stock))
                    continue
            else:
                # 聚宽回测: 跳过确认, 直接满仓
                pos_scale = 1.0
        else:
            pos_scale = 1.0

        # ============================================================
        # [v9.0.17] 二段买入 (环境分离)
        # 聚宽回测: 一次满仓(即时成交, 无冲高回落风险)
        # QMT实盘: 先50%→09:35补仓(防冲高回落)
        # ============================================================
        if strategy_name == 'A' and pos_scale >= 1.0 and getattr(g, 'is_qmt', False):
            first_stage_ratio = 0.5
        else:
            first_stage_ratio = pos_scale

        target_value = context.portfolio.total_value * item.get('pos_ratio', budget['pos_ratio'])
        actual_value = target_value * first_stage_ratio
        if actual_value / curr_price < 100:
            continue

        buy_value = min(context.portfolio.available_cash, actual_value)
        if buy_value > 0 and order_value(stock, buy_value) is not None:
            stage = 'half' if first_stage_ratio < 1.0 and strategy_name == 'A' else 'full'
            mark_pending_buy(stock, strategy_name, item['entry_type'], stage, context)
            g.daily_new_position_count += 1
            slots_left -= 1
            diag_add('{}_buys_orders'.format(strategy_name))

            # 记录二段买入信息(供09:35补仓使用)
            if stage == 'half':
                if not hasattr(g, 'pending_stage2_buys'):
                    g.pending_stage2_buys = {}
                g.pending_stage2_buys[stock] = {
                    'entry_type': item['entry_type'],
                    'first_price': curr_price,
                    'open_price': open_price if strategy_name == 'A' else 0,
                    'target_value': target_value,
                    'bought_value': buy_value,
                    'pos_ratio': item.get('pos_ratio', budget['pos_ratio']),
                }

            # Dragon Bear 周频率计数
            if item.get('entry_type') == 'dragon_follow' and g.market_regime == 'bear':
                g.dragon_bear_weekly_count += 1
                if g.dragon_bear_weekly_reset_countdown <= 0:
                    g.dragon_bear_weekly_reset_countdown = g.cfg.get(
                        'dragon_bear_weekly_counter_reset_days', 5)

            log.info("{} type={} tpl={} mode={} score={:.3f} open_ratio={:.2f}% stage={}".format(
                stock, item['entry_type'], item.get('tpl', 'base'),
                item.get('mode', 'normal'), item['score'], item.get('open_ratio', 0) * 100, stage))


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

def get_A_mode(context):
    """A策略模式判定，返回 (mode_name, budget_overrides)

    [V1.1.0] 大幅简化:
    - 移除panic_scout模式(由趋势过滤器替代)
    - 移除strict_bear全面封锁(由趋势过滤器+仓位缩减替代)
    - 保留: Dragon断路器(自身连亏保护)、深回撤冷却(组合保护)
    - 新增: 大盘下跌趋势时自动缩减仓位
    """
    cfg_a = g.strategies['A']['config']

    # Dragon模式判定 — 不再受panic_scout限制
    dragon_ready = (
        g.A_pause_days_left == 0
        and g.dragon_pool_size > 0
        and (g.micro_regime == 'neutral_crowding'
             or g.diag.get('dragon_panic_override', 0) == 1)
    )

    # Dragon断路器(保留: 自身连亏保护)
    if dragon_ready and g.dragon_circuit_breaker_pause_left > 0:
        dragon_ready = False
        g.diag['dragon_circuit_breaker_active'] = 1
        log.info("🔌【Dragon断路器】暂停中(剩余{}天)，降级为normal模式".format(
            g.dragon_circuit_breaker_pause_left))

    overrides = {}

    if dragon_ready:
        overrides['max_hold'] = min(cfg_a['max_hold'], cfg_a['dragon_max_hold'])
        overrides['pos_ratio'] = cfg_a['dragon_pos_ratio']
        # 大盘下跌趋势时Dragon仓位缩减(但不拦截)
        if g.market_trend == 'down':
            mult = g.cfg.get('trend_downtrend_pos_ratio_mult', 0.5)
            overrides['pos_ratio'] = overrides['pos_ratio'] * mult
            log.info("🐉【A抱团模式-趋势缩仓】pool={} score={:.3f} pos={:.2f}(×{})".format(
                g.dragon_pool_size, g.dragon_top_score, overrides['pos_ratio'], mult))
        else:
            log.info("🐉【A抱团模式】pool={} score={:.3f} trend={}".format(
                g.dragon_pool_size, g.dragon_top_score, g.market_trend))
        g.diag['A_dragon_mode'] = 1
        return 'dragon', overrides

    # 深回撤冷却(保留: 组合保护)
    if g.A_pause_days_left > 0:
        log.info("⏸️【A暂停】冷却期内禁止开仓(剩余{}天)".format(g.A_pause_days_left))
        return 'paused', {'max_hold': 0}

    if (not g.A_dd_rearm_ready) and g.market_regime != 'neutral':
        log.info("⛔【A禁开】回撤未修复")
        return 'blocked', {'max_hold': 0}

    # Normal模式 — 仓位由趋势过滤器在选股阶段动态调整
    if g.A_rearm_grace_days_left > 0:
        overrides['max_hold'] = min(cfg_a['max_hold'], 1)
        overrides['pos_ratio'] = min(cfg_a['pos_ratio'], 0.12)

    return 'normal', overrides


def select_candidates_A(context, config, mode):
    """A策略选股 — 统一评分系统下不再Dragon-first, 而是合并后统一排序"""
    if mode == 'dragon':
        dragon_list = list(g.dragon_candidates_today) if g.dragon_candidates_today else []
        normal_list = get_stock_list_A(context)
        if normal_list:
            normal_types = [x.get('entry_type', '?') for x in normal_list]
            log.info("🔀【统一选股】Dragon{}只 + 普通{}只: {}".format(
                len(dragon_list), len(normal_list), normal_types))
        # 合并去重(统一评分模式下不区分优先级, 由score_candidates_A统一排序)
        seen = set()
        merged = []
        for item in dragon_list + normal_list:
            if item['stock'] not in seen:
                seen.add(item['stock'])
                merged.append(item)
        return merged
    else:
        return get_stock_list_A(context)


def evaluate_sell_signal_A(sell_ctx, config):
    """A策略卖出规则
    [v9.0.25] 还原v7.0核心逻辑 + 保留break_ma5_partial(>5%半仓)
    修复: profit_protect使用config值而非hardcoded
    """
    pnl = sell_ctx['pnl']
    curr_p = sell_ctx['curr_price']
    stage = sell_ctx['stage']
    if stage == 'half_final':
        stage = 'half'
    entry_type = sell_ctx['entry_type']
    ma5 = sell_ctx['ma5_est']
    prev_close = sell_ctx['prev_close']

    # 硬止损(低开策略用宽止损)
    if entry_type == 'dragon_follow':
        stop = config['dragon_abs_stop_loss']
    elif entry_type == 'firstboard_lowopen':
        stop = config.get('lowopen_abs_stop_loss', 0.08)
    else:
        stop = config['abs_stop_loss']
    if pnl <= -stop:
        return {'action': 'sell_all', 'reason': 'hard_stop_loss'}

    if stage == 'pending':
        return None

    # 首板低开(T+1)卖出逻辑: 分档止盈 + 14:50强制清仓
    if entry_type == 'firstboard_lowopen':
        current_time = str(sell_ctx.get('current_dt', ''))[-8:]
        high_limit = sell_ctx.get('high_limit', 0)
        # 涨停不卖
        if high_limit > 0 and curr_p >= high_limit * 0.995:
            return None
        # 11:20 分档止盈: 强势半仓持有, 弱势全卖
        if current_time >= '11:20:00' and current_time < '14:50:00':
            lowopen_strong_tp = config.get('lowopen_strong_tp_threshold', 0.05)
            if pnl >= lowopen_strong_tp and stage == 'full':
                # 强势(>5%): 卖半仓, 剩余持到14:50
                return {'action': 'sell_half', 'reason': 'lowopen_strong_tp', 'next_stage': 'half'}
            elif pnl > 0:
                # 弱复苏(0~5%): 全卖锁利
                return {'action': 'sell_all', 'reason': 'lowopen_profit_tp'}
        # 14:50 强制清仓(T+1不隔夜)
        if current_time >= '14:50:00':
            return {'action': 'sell_all', 'reason': 'lowopen_force_close'}
        # 半仓保护: 跌破开盘价则清剩余
        if stage == 'half':
            if current_time >= '13:00:00' and pnl <= 0:
                return {'action': 'sell_all', 'reason': 'lowopen_half_protect'}
        return None

    # Dragon逻辑
    if entry_type == 'dragon_follow':
        if stage == 'full':
            # 盈利超过保护阈值且破MA5 → 半仓保护(用config值)
            profit_protect = config.get('dragon_min_profit_protect', 0.08)
            if pnl >= profit_protect and curr_p < ma5:
                return {'action': 'sell_half', 'reason': 'dragon_profit_protect', 'next_stage': 'half'}
            # [v9.0.25还原] 不赚钱且破MA5 → 快速退出(v7.0: pnl<=0)
            if curr_p < ma5 and pnl <= 0:
                return {'action': 'sell_all', 'reason': 'dragon_fail_fast'}
            # [v9.0.25保留] 盈利丰厚(>5%)破MA5 → 先半仓(合理的新增保护)
            if curr_p < ma5 and pnl > 0.05:
                return {'action': 'sell_half', 'reason': 'dragon_break_ma5_partial', 'next_stage': 'half'}
        if stage == 'half':
            # [v9.0.25还原] 半仓保护用MA5(v7.0逻辑, 紧保护)
            protect_line = max(prev_close, ma5)
            if curr_p < protect_line:
                return {'action': 'sell_all', 'reason': 'dragon_half_protect'}
        return None

    # Normal逻辑
    if stage == 'full':
        # [v9.0.25还原] 不赚钱且破MA5 → 快速退出(v7.0: pnl<=0)
        if curr_p < ma5 and pnl <= 0:
            return {'action': 'sell_all', 'reason': 'fast_fail_ma5'}
        if pnl >= config['partial_tp_threshold']:
            return {'action': 'sell_half', 'reason': 'partial_tp_lock', 'next_stage': 'half'}
        if config['stop_by_ma'] and curr_p < ma5:
            # [v9.0.25还原] 破MA5且盈利>3% → 半仓(v7.0阈值)
            if pnl > 0.03:
                return {'action': 'sell_half', 'reason': 'break_intraday_ma5_partial', 'next_stage': 'half'}
            # [v9.0.25删除MA5容忍区] 破就是破, 直接卖
            return {'action': 'sell_all', 'reason': 'break_intraday_ma5'}
    if stage == 'half':
        # [v9.0.25还原] 半仓保护用prev_close+MA5(v7.0逻辑)
        protect_line = max(prev_close, ma5)
        if curr_p < protect_line:
            return {'action': 'sell_all', 'reason': 'half_protect_break'}

    return None


# ================== 统一评分系统(期望收益率锚定) ==================

def calculate_csi1000_3yr_percentile(context):
    """计算中证1000近3年价格区间分位值(0=3年最低, 1=3年最高)"""
    try:
        cfg = g.cfg
        lookback = cfg.get('unified_csi1000_lookback', 730)
        h = attribute_history('000852.XSHG', lookback, '1d', ['close'], skip_paused=True)
        if len(h) < 60:
            return 0.5
        highest = h['close'].max()
        lowest = h['close'].min()
        current = h['close'].iloc[-1]
        if highest <= lowest:
            return 0.5
        return float((current - lowest) / (highest - lowest))
    except Exception as e:
        log.warning("calculate_csi1000_3yr_percentile异常: {}, 使用默认0.5".format(e))
        return 0.5


def calculate_recent_volatility(context):
    """计算中证1000近N日收益率标准差(短期波动维度)"""
    try:
        cfg = g.cfg
        vol_days = cfg.get('unified_volatility_lookback', 5)
        h = attribute_history('000852.XSHG', vol_days + 5, '1d', ['close'], skip_paused=True)
        if len(h) < vol_days + 1:
            return 0.015
        returns = h['close'].pct_change().dropna()
        return float(returns.iloc[-vol_days:].std())
    except Exception as e:
        log.warning("calculate_recent_volatility异常: {}, 使用默认0.015".format(e))
        return 0.015


def compute_env_weights(csi1000_pct, volatility):
    """根据长期位置×短期波动计算各entry_type的环境权重

    设计思路:
    - 高波动 → 压低dragon(追涨易亏), 抬高firstboard_lowopen(低开反弹稳)
    - 低波动 → dragon表现正常, firstboard_lowopen机会少
    - 高分位(牛市区) → dragon适合, 低开机会少
    - 低分位(熊市区) → dragon危险, 低开策略穿越牛熊
    """
    cfg = g.cfg
    vol_high = cfg.get('unified_volatility_high', 0.025)
    vol_low = cfg.get('unified_volatility_low', 0.010)

    # 波动度标准化到[0,1]: 0=低波, 1=高波
    vol_norm = max(0.0, min(1.0, (volatility - vol_low) / (vol_high - vol_low))) if vol_high > vol_low else 0.5

    # Dragon权重: 低分位+高波动 → 压低; 高分位+低波动 → 正常
    # [V1.0.0调参] vol惩罚0.4→0.25, csi惩罚0.3→0.15 (原参数在中等波动市完全过滤dragon)
    w_dragon = 1.0 - 0.25 * vol_norm - 0.15 * (1.0 - csi1000_pct)
    w_dragon = max(0.5, min(1.5, w_dragon))

    # 首板低开权重: 穿越牛熊但高波动时更优
    w_lowopen = 1.0 + 0.3 * vol_norm
    w_lowopen = max(0.7, min(1.5, w_lowopen))

    # 首板(高开型)权重: 跟dragon类似但温和
    w_firstboard = 1.0 - 0.2 * vol_norm - 0.15 * (1.0 - csi1000_pct)
    w_firstboard = max(0.5, min(1.3, w_firstboard))

    # 弱转强权重: 中性偏保守
    w_weak = 1.0 - 0.15 * vol_norm
    w_weak = max(0.6, min(1.2, w_weak))

    return {
        'dragon_follow': round(w_dragon, 3),
        'firstboard_lowopen': round(w_lowopen, 3),
        'firstboard': round(w_firstboard, 3),
        'weak_to_strong': round(w_weak, 3),
    }


# ================== 趋势过滤系统 ==================

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
        log.warning("get_market_trend异常: {}, 返回sideways".format(e))
        return 'sideways'


def get_market_short_return(context, days=5):
    """获取大盘近N日涨跌幅"""
    try:
        idx = g.cfg['regime_index']
        h = attribute_history(idx, days + 1, '1d', ['close'], skip_paused=True)
        if len(h) < days + 1:
            return 0.0
        return float(h['close'].iloc[-1] / h['close'].iloc[0] - 1)
    except Exception:
        return 0.0


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
        log.warning("is_stock_uptrend({})异常: {}".format(stock, e))
        return False


def get_stock_relative_strength(stock, context, days=None):
    """计算个股相对大盘的超额收益(近N日)
    返回: 个股N日收益 - 大盘N日收益
    """
    if days is None:
        days = g.cfg.get('trend_relative_strength_days', 5)
    try:
        idx = g.cfg['regime_index']
        h_stock = attribute_history(stock, days + 1, '1d', ['close'], skip_paused=True)
        h_idx = attribute_history(idx, days + 1, '1d', ['close'], skip_paused=True)
        if len(h_stock) < days + 1 or len(h_idx) < days + 1:
            return 0.0
        stock_ret = h_stock['close'].iloc[-1] / h_stock['close'].iloc[0] - 1
        idx_ret = h_idx['close'].iloc[-1] / h_idx['close'].iloc[0] - 1
        return float(stock_ret - idx_ret)
    except Exception:
        return 0.0


def check_stock_trend_filter(stock, entry_type, context):
    """趋势过滤器: 综合大盘趋势和个股趋势决定是否放行

    返回: (pass, pos_mult, reason)
        pass: True=放行, False=拦截
        pos_mult: 仓位乘数(1.0=正常, 0.5=缩仓)
        reason: 过滤原因(用于日志)
    """
    cfg = g.cfg
    if not cfg.get('trend_filter_enable', True):
        return True, 1.0, 'filter_disabled'

    # 按entry_type决定是否启用趋势过滤
    if entry_type == 'firstboard_lowopen' and not cfg.get('trend_filter_lowopen', False):
        return True, 1.0, 'lowopen_exempt'
    if entry_type == 'dragon_follow' and not cfg.get('trend_filter_dragon', True):
        return True, 1.0, 'dragon_exempt'
    if entry_type in ('firstboard', 'weak_to_strong') and not cfg.get('trend_filter_normal', True):
        return True, 1.0, 'normal_exempt'

    market_trend = g.market_trend
    pos_mult = 1.0

    if market_trend == 'up':
        # 大盘上涨趋势: 放行所有,正常仓位
        # 但仍检查个股趋势(避免买逆势下跌的票)
        if is_stock_uptrend(stock, context):
            return True, 1.0, 'market_up_stock_up'
        else:
            # 大盘涨但个股跌 — 不做(除非是lowopen已豁免)
            return False, 0.0, 'market_up_stock_down'

    elif market_trend == 'down':
        # 大盘下跌趋势: 只做逆势强势股
        rs = get_stock_relative_strength(stock, context)
        rs_min = cfg.get('trend_relative_strength_min', 0.0)
        if rs >= rs_min and is_stock_uptrend(stock, context):
            # 逆势走强 + 趋势向上 → 放行但缩仓
            pos_mult = cfg.get('trend_downtrend_pos_ratio_mult', 0.5)
            return True, pos_mult, 'downtrend_relative_strong'
        else:
            return False, 0.0, 'downtrend_no_strength'

    else:
        # 震荡市: 要求个股趋势向上
        if is_stock_uptrend(stock, context):
            return True, 1.0, 'sideways_stock_up'
        else:
            return False, 0.0, 'sideways_stock_down'


def compute_quality_multiplier(entry_type, item, context):
    """根据entry_type和个股因子计算质量乘数(0.5~2.0)

    每种type用各自最相关的因子:
    - dragon_follow: inv_c2h, avg_rng, 低换手, rp_60d
    - firstboard_lowopen: rp_60d, open_gap贴合度, 非连板纯度
    - firstboard: rp_60d, 竞价强度, 放量程度
    - weak_to_strong: 竞价涨幅, 突破新高程度
    """
    cfg = g.cfg
    q_min = cfg.get('unified_quality_mult_min', 0.5)
    q_max = cfg.get('unified_quality_mult_max', 2.0)
    q = 1.0  # 基础值

    if entry_type == 'dragon_follow':
        # [v9.0.25-fix] 百分位排名区分度: 用当日候选排名而非固定阈值
        # 修复: v3评分范围0.15~1.0+, 原cap=0.40导致所有候选q=2.0零区分
        dragon_score = item.get('dragon_score', 0.0)
        all_scores = [c.get('dragon_score', 0.0)
                      for c in getattr(g, 'dragon_candidates_today', [])]
        if len(all_scores) >= 2:
            s_min, s_max = min(all_scores), max(all_scores)
            if s_max > s_min:
                pct = (dragon_score - s_min) / (s_max - s_min)
                q = q_min + pct * (q_max - q_min)  # Top→2.0, Bottom→0.5
            else:
                q = (q_min + q_max) / 2  # 所有候选同分, 取中间值
        else:
            q = 1.0  # 仅1个候选, 中性

    elif entry_type == 'firstboard_lowopen':
        rp = item.get('rp_60d', 0.5)
        open_gap = item.get('open_gap', 0.965)
        # rp越低越好(低位), open_gap在0.965附近最优
        rp_score = max(0, 1.0 - rp / 0.5) * 0.8     # rp=0→0.8, rp=0.5→0
        gap_fit = max(0, 1.0 - abs(open_gap - 0.965) / 0.01) * 0.6  # 最优gap=0.965
        q = 0.8 + rp_score + gap_fit

    elif entry_type == 'firstboard':
        open_ratio = item.get('open_ratio', 0.0)
        q = 0.8 + min(max(open_ratio, 0), 0.06) / 0.06 * 1.0

    elif entry_type == 'weak_to_strong':
        open_ratio = item.get('open_ratio', 0.0)
        q = 0.7 + min(max(open_ratio, 0), 0.05) / 0.05 * 0.8

    return max(q_min, min(q_max, q))


def compute_unified_score(entry_type, item, context):
    """统一评分 = base_edge × quality_multiplier × env_weight

    输出单位: 预期收益率(%), 所有type可直接比较
    """
    cfg = g.cfg
    regime = g.market_regime

    base_edges = cfg.get('unified_base_edge', {})
    type_edges = base_edges.get(entry_type, {'bull': 0, 'neutral': 0, 'bear': 0})
    base_edge = type_edges.get(regime, 0.0)

    quality_mult = compute_quality_multiplier(entry_type, item, context)
    env_weight = g.env_weights.get(entry_type, 1.0)

    unified = base_edge * quality_mult * env_weight
    return unified, base_edge, quality_mult, env_weight


def update_unified_scoring_env(context):
    """每日更新统一评分系统的环境变量(在morning_prepare中调用)"""
    cfg = g.cfg
    if not cfg.get('unified_scoring_enable', False):
        return

    g.csi1000_percentile = calculate_csi1000_3yr_percentile(context)
    g.recent_volatility = calculate_recent_volatility(context)
    g.env_weights = compute_env_weights(g.csi1000_percentile, g.recent_volatility)

    # 根据regime设置空仓阈值
    thresholds = cfg.get('unified_empty_threshold', {})
    g.unified_min_threshold = thresholds.get(g.market_regime, 0.003)

    log.info("📊【统一评分】CSI1000分位={:.3f} 波动率={:.4f} 权重={}  阈值={:.4f}".format(
        g.csi1000_percentile, g.recent_volatility,
        g.env_weights, g.unified_min_threshold))


def is_consecutive_limit_up(stock, date, watch_days=10):
    """检测股票是否为连板(连续2天以上涨停)"""
    try:
        df = get_price([stock], end_date=date, frequency='daily',
                       fields=['close', 'high_limit'], count=watch_days,
                       panel=False, fill_paused=False, skip_paused=False)
        if df is None or df.empty:
            return False
        df = df.dropna()
        # 从最近一天往前数连续涨停天数
        consecutive = 0
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]['close'] == df.iloc[i]['high_limit']:
                consecutive += 1
            else:
                break
        return consecutive >= 2
    except Exception:
        return False


# =============================================================================
# 第六层: 环境引擎 (Regime / Dragon / Risk)
# 以下函数与v5.9.0完全相同，只做了命名规范化
# =============================================================================

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
            log.info("🔀【双指数修正】主=bear 副={} → 降级为neutral".format(g.regime_secondary_raw))
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
    """根据环境刷新A策略预算"""
    cfg_a = g.strategies['A']['config']

    if g.micro_regime == 'neutral_crowding' and g.market_regime == 'bear':
        g.strategy_budget['A'] = {
            'max_hold': cfg_a['bear_crowding_max_hold'],
            'pos_ratio': cfg_a['bear_crowding_pos_ratio']
        }
    elif g.micro_regime == 'neutral_crowding':
        g.strategy_budget['A'] = {
            'max_hold': cfg_a['max_hold'], 'pos_ratio': cfg_a['pos_ratio']
        }
    elif g.market_regime == 'bull':
        g.strategy_budget['A'] = {
            'max_hold': cfg_a['max_hold'], 'pos_ratio': cfg_a['pos_ratio']
        }
    elif g.market_regime == 'bear':
        g.strategy_budget['A'] = {
            'max_hold': 1, 'pos_ratio': cfg_a['pos_ratio']
        }
    else:
        # neutral_trend
        g.strategy_budget['A'] = {
            'max_hold': cfg_a['max_hold'], 'pos_ratio': cfg_a['pos_ratio']
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
            log.info("📉【Crowding衰减退出】EMA={:.3f} < 峰值{:.3f}×{:.0f}%".format(
                g.dragon_score_ema, g.crowding_peak_score, decay_ratio * 100))

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
            log.info("⏰【Crowding超时】连续{}天，强制退出，冷却{}天".format(
                g.crowding_consecutive_days, g.crowding_cooldown_left))
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
        log.info("🔄【Crowding退出】→ {}".format(new_micro))

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
        log.error("gap_down_stop_loss 初始化异常: {}".format(e))
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
            stop_level = _get_stop_level(strategy, entry_type)

            if pnl <= -stop_level:
                # 标记预警, 记录开盘亏损幅度, 等待confirm确认
                g.gap_down_alerts[stock] = {
                    'strategy': strategy,
                    'entry_type': entry_type,
                    'open_pnl': pnl,
                    'stop_level': stop_level,
                    'avg_cost': pos.avg_cost,
                }
                log.info("⏳【缺口预警】{} strategy={} entry={} open_pnl={:.2f}% → 等待09:35确认".format(
                    stock, strategy, entry_type, pnl * 100))
        except Exception as e:
            log.error("gap_down_stop_loss {} 异常: {}".format(stock, e))


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
        log.error("gap_down_confirm 初始化异常: {}".format(e))
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
                # 取不到价格, 保守执行止损
                confirmed.append(stock)
                continue

            avg_cost = alert['avg_cost']
            current_pnl = curr_price / avg_cost - 1
            recovery_line = -recovery_ratio  # 默认-2%

            if current_pnl > recovery_line:
                # 价格已恢复, 取消止损
                log.info("✅【缺口恢复】{} 当前pnl={:.2f}% > 恢复线{:.2f}%, 取消止损".format(
                    stock, current_pnl * 100, recovery_line * 100))
                cancelled.append(stock)
            else:
                # 未恢复, 确认执行止损
                confirmed.append(stock)

        except Exception as e:
            log.error("gap_down_confirm {} 异常: {}".format(stock, e))
            confirmed.append(stock)  # 异常时保守执行

    # 执行确认的止损
    for stock in confirmed:
        alert = g.gap_down_alerts.pop(stock, None)
        if not alert:
            continue
        try:
            current_pnl = current_data[stock].last_price / alert['avg_cost'] - 1
        except Exception:
            current_pnl = alert['open_pnl']

        if submit_exit_order(stock, context, reason='gap_down_stop', ret_snapshot=current_pnl):
            strategy = alert['strategy']
            entry_type = alert['entry_type']
            diag_add('{}_sell_all'.format(strategy))
            log.info("🚨【缺口止损确认】{} strategy={} entry={} open_pnl={:.2f}% confirm_pnl={:.2f}%".format(
                stock, strategy, entry_type, alert['open_pnl'] * 100, current_pnl * 100))

    # 清理已取消的
    for stock in cancelled:
        g.gap_down_alerts.pop(stock, None)


# =========================================================
# Panic Scout
# =========================================================


def intraday_stop_loss_check(context):
    current_data = get_current_data()
    today = context.current_dt.date()

    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta or meta.get('pending_exit', False) or meta.get('last_exit_date') == today:
            continue
        if meta.get('pending_stage_change'):
            continue

        pos = context.portfolio.positions[stock]
        if pos.closeable_amount <= 0:
            continue

        curr_p = current_data[stock].last_price
        if curr_p is None or curr_p <= 0:
            continue

        pnl = curr_p / pos.avg_cost - 1
        strategy = meta.get('strategy', 'A')
        entry_type = meta.get('entry_type', '')

        if strategy == 'A' and entry_type == 'dragon_follow':
            stop_level = g.cfg['A_dragon_abs_stop_loss']
        else:
            stop_level = g.cfg['A_abs_stop_loss']

        if pnl <= -stop_level:
            if submit_exit_order(stock, context, reason='intraday_hard_stop', ret_snapshot=pnl):
                diag_add('{}_sell_all'.format(strategy))
                log.info("🚨【盘中紧急止损】{} strategy={} entry={} ret={:.2f}%".format(
                    stock, strategy, entry_type, pnl * 100))


def get_dynamic_panic_scout_settings(y_ret):
    cfg = g.cfg
    if y_ret <= cfg['panic_drop_level_severe']:
        return {'level': 'severe', 'max_hold': cfg['panic_A_max_hold'],
                'pos_ratio': cfg['panic_A_pos_ratio_severe'],
                'min_open_ratio': cfg['panic_A_min_open_ratio_severe']}
    elif y_ret <= cfg['panic_drop_level_medium']:
        return {'level': 'medium', 'max_hold': cfg['panic_A_max_hold'],
                'pos_ratio': cfg['panic_A_pos_ratio_medium'],
                'min_open_ratio': cfg['panic_A_min_open_ratio_medium']}
    else:
        return {'level': 'mild', 'max_hold': cfg['panic_A_max_hold'],
                'pos_ratio': cfg['panic_A_pos_ratio_mild'],
                'min_open_ratio': cfg['panic_A_min_open_ratio_mild']}


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
    # [DPM] 使用动态仓位上限
    max_pos = g.dpm_current_max_positions if hasattr(g, 'dpm_current_max_positions') \
        else g.cfg.get('max_total_positions', 999)
    if get_total_slot_hold_count(context) >= max_pos:
        g.diag['intraday_pos_cap'] = 1
        log.info("⚠️【盘中持仓上限】当前槽位已达 {}，停止开新仓".format(max_pos))
        return True
    if context.portfolio.total_value <= 0:
        return False
    # 计算A仓位比
    a_value = sum(
        pos.value for stock, pos in context.portfolio.positions.items()
        if g.positions_meta.get(stock, {}).get('strategy', '') == 'A'
    )
    pos_ratio = a_value / context.portfolio.total_value
    max_ratio = g.dpm_current_max_pos_ratio if hasattr(g, 'dpm_current_max_pos_ratio') \
        else g.cfg['max_portfolio_position_ratio']
    if pos_ratio >= max_ratio:
        g.diag['intraday_pos_cap'] = 1
        log.info("⚠️【盘中仓位上限】A+B仓位 {:.2f}% 达上限 {:.0f}%".format(
            pos_ratio * 100, max_ratio * 100))
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
        log.info("🚨【盘中大跌】指数实时跌幅 {:.2f}%，启用趋势过滤(只做逆势强势股)".format(
            intraday_ret * 100))
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
    log.info("📉【昨日大跌】指数跌 %.2f%%，趋势过滤器生效(只做趋势向上个股+缩仓)" % (y_ret * 100))


def update_portfolio_nav_and_brake(context):
    """NAV跟踪 + A策略回撤保护(B相关逻辑已移除)"""
    nav = context.portfolio.total_value / g.bt['start_cash'] if g.bt['start_cash'] else 1.0
    eps = 1e-6

    if nav >= g.bt['peak_nav']:
        new_high = nav > g.bt['peak_nav']
        g.bt['peak_nav'] = nav

        if new_high:
            if g.A_dd_cooldown_active or not g.A_dd_rearm_ready or g.A_pause_days_left > 0:
                log.info("🌟 净值创新高，A保护复位。")
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
        log.info("🛡 A安全区修复，A保护重新武装。")

    if g.A_dd_cooldown_active and g.A_pause_days_left > 0:
        g.A_pause_days_left -= 1
        if g.A_pause_days_left == 0:
            g.A_dd_cooldown_active = False
            log.info("🔓 A冷却期结束。")

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
        log.info("🛡 组合深回撤 {:.2f}%，A暂停 {} 天。".format(
            current_dd * 100, g.A_pause_days_left))

    g.diag['A_pause_days_left'] = g.A_pause_days_left
    g.diag['A_dd_cooldown_active'] = 1 if g.A_dd_cooldown_active else 0
    g.diag['A_dd_rearm_ready'] = 1 if g.A_dd_rearm_ready else 0
    g.diag['A_rearm_grace_days_left'] = g.A_rearm_grace_days_left



def sync_position_meta_with_real_positions(context):
    real_positions = set(context.portfolio.positions.keys())

    for stock in list(g.positions_meta.keys()):
        if stock not in real_positions:
            meta = g.positions_meta[stock]
            finalize_exited_position(stock, meta)
            del g.positions_meta[stock]

    for stock in list(g.pending_buys.keys()):
        if stock in real_positions:
            pb = g.pending_buys[stock]
            pos = context.portfolio.positions[stock]

            g.positions_meta[stock] = {
                'strategy': pb['strategy'],
                'entry_type': pb['entry_type'],
                'stage': pb['stage'],
                'pending_exit': False,
                'last_exit_date': None,
                'last_exit_reason': '',
                'pending_exit_ret_snapshot': None,
                'exit_order_id': None,
                'last_amount': getattr(pos, 'total_amount', None),
                'pending_stage_change': None,
                'pending_stage_change_date': None,
                'pending_stage_change_reason': '',
                'partial_order_id': None,
                'rebuild_scout': pb.get('rebuild_scout', False),
            }

            del g.pending_buys[stock]

    today = context.current_dt.date()
    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta:
            continue
        pos = context.portfolio.positions[stock]
        prev_amount = meta.get('last_amount')
        curr_amount = getattr(pos, 'total_amount', None)

        if (meta.get('pending_stage_change')
                and prev_amount is not None and curr_amount is not None
                and curr_amount < prev_amount):
            meta['stage'] = meta['pending_stage_change']
            meta['pending_stage_change'] = None
            meta['pending_stage_change_date'] = None
            meta['pending_stage_change_reason'] = ''
            meta['partial_order_id'] = None
        elif (meta.get('pending_stage_change')
              and meta.get('pending_stage_change_date') is not None
              and meta.get('pending_stage_change_date') < today
              and prev_amount is not None and curr_amount is not None
              and curr_amount >= prev_amount):
            meta['pending_stage_change'] = None
            meta['pending_stage_change_date'] = None
            meta['pending_stage_change_reason'] = ''
            meta['partial_order_id'] = None

        meta['last_amount'] = curr_amount

        # [v9.0.17] A二段买入成交确认: 委托成功后检查持仓是否增加
        if meta.get('pending_stage2_confirm'):
            if (prev_amount is not None and curr_amount is not None
                    and curr_amount > prev_amount):
                # 持仓增加 → 成交确认 → 推进stage
                meta['stage'] = 'full'
                meta['pending_stage2_confirm'] = False
                meta['stage2_order_id'] = None
                log.info("✅【A二段成交确认】{} 持仓{}→{}, stage→full".format(
                    stock, prev_amount, curr_amount))
            elif meta.get('pending_stage2_confirm_date') is None:
                # 首次检查,记录日期
                meta['pending_stage2_confirm_date'] = today
            elif meta.get('pending_stage2_confirm_date', today) < today:
                # 跨日仍未成交 → 放弃确认,保持half
                meta['pending_stage2_confirm'] = False
                meta['stage2_order_id'] = None
                log.warning("⚠️【A二段超时】{} 跨日未成交, 保持stage={}".format(
                    stock, meta.get('stage', 'half')))

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
                log.info("⚠️【孤儿警报】{} 将于11:26清理".format(stock))
        elif g.positions_meta[stock].get('pending_exit', False):
            pending_exit_count += 1
    g.diag['unknown_positions'] = unknown_count
    g.diag['pending_exit_positions'] = pending_exit_count
    g.diag['pending_buy_positions'] = len(g.pending_buys)


def retry_pending_exit_positions(context):
    try:
        _retry_pending_exit_positions_impl(context)
    except Exception as e:
        log.error("retry_pending_exit_positions异常: {}".format(e))

def _retry_pending_exit_positions_impl(context):
    current_data = get_current_data()
    today = context.current_dt.date()
    for stock in list(context.portfolio.positions.keys()):
        meta = g.positions_meta.get(stock)
        if not meta or not meta.get('pending_exit', False):
            continue
        pos = context.portfolio.positions[stock]
        if pos.closeable_amount <= 0:
            continue
        if meta.get('last_exit_date') == today:
            continue
        curr_price = current_data[stock].last_price
        if curr_price is None or curr_price <= 0:
            continue
        if order_target_value(stock, 0) is not None:
            meta['last_exit_date'] = today
            meta['last_exit_reason'] = 'retry_pending_exit'
            diag_add('retry_pending_exit')
            log.info("🔁【待退出重试】{} 再次尝试清仓".format(stock))


def orphan_sweeper_execute(context):
    try:
        _orphan_sweeper_execute_impl(context)
    except Exception as e:
        log.error("orphan_sweeper_execute异常: {}".format(e))

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
            log.info("🧹【清道夫】强平 {}".format(stock))


# =========================================================
# Regime - [OPT-2] 双指数雷达
# =========================================================


def get_A_position_avg_profit(context):
    """计算 A 策略所有持仓的平均盈利"""
    profits = []
    for stock in context.portfolio.positions:
        meta = g.positions_meta.get(stock, {})
        if meta.get('strategy') == 'A' and not meta.get('pending_exit', False):
            pos = context.portfolio.positions[stock]
            if pos.avg_cost > 0:
                profits.append(pos.value / (pos.avg_cost * pos.total_amount) - 1)
    if not profits:
        return 0.0
    return float(np.mean(profits))


def update_dynamic_position_limits(context):
    """[DPM] 根据环境和持仓状态动态调整全局仓位限制"""
    cfg = g.cfg
    if not cfg.get('dpm_enable', False):
        g.dpm_current_max_positions = cfg['max_total_positions']
        g.dpm_current_max_pos_ratio = cfg['max_portfolio_position_ratio']
        return

    base_max = cfg['max_total_positions']
    expanded_max = cfg.get('max_total_positions_expanded', 4)
    base_pos_ratio = cfg['max_portfolio_position_ratio']
    bull_pos_ratio = cfg.get('max_portfolio_position_ratio_bull', 0.85)

    # 计算 A 的平均盈利
    g.dpm_A_avg_profit = get_A_position_avg_profit(context)
    a_hold = get_real_strategy_hold_count(context, 'A')

    should_expand = False
    expand_reason = ''

    # 条件1：A 有盈利持仓时扩展
    if (cfg.get('dpm_expand_when_A_profitable', True)
            and a_hold > 0
            and g.dpm_A_avg_profit >= cfg.get('dpm_expand_min_A_profit', 0.03)):
        should_expand = True
        expand_reason = 'A_profitable({:.1f}%)'.format(g.dpm_A_avg_profit * 100)

    # 条件2：bull 环境自动扩展
    if cfg.get('dpm_expand_in_bull', True) and g.micro_regime == 'bull':
        should_expand = True
        expand_reason = 'bull_regime'

    # bear 下不扩展
    if g.market_regime == 'bear':
        should_expand = False
        expand_reason = ''

    if should_expand:
        g.dpm_current_max_positions = expanded_max
        g.dpm_expanded_today = True
    else:
        g.dpm_current_max_positions = base_max
        g.dpm_expanded_today = False

    # 仓位比例调整
    if g.micro_regime == 'bull':
        g.dpm_current_max_pos_ratio = bull_pos_ratio
    elif g.market_regime == 'bear':
        g.dpm_current_max_pos_ratio = base_pos_ratio * 0.85
    else:
        g.dpm_current_max_pos_ratio = base_pos_ratio

    g.diag['dpm_expanded'] = 1 if g.dpm_expanded_today else 0
    g.diag['dpm_max_pos'] = g.dpm_current_max_positions
    g.diag['dpm_max_ratio'] = round(g.dpm_current_max_pos_ratio, 3)
    g.diag['dpm_A_avg_profit'] = round(g.dpm_A_avg_profit, 4)

    if should_expand:
        log.info("📐【DPM】扩展模式: max_pos={}, reason={}, A_profit={:.1f}%".format(
            g.dpm_current_max_positions, expand_reason,
            g.dpm_A_avg_profit * 100))


# =========================================================
# 策略 A
# =========================================================


def get_A_partial_take_profit(entry_type):
    if entry_type == 'firstboard':
        return g.cfg['A_partial_take_profit_firstboard']
    if entry_type == 'dragon_follow':
        return g.cfg['A_dragon_partial_take_profit']
    return g.cfg['A_partial_take_profit_weak']


def get_intraday_high_price(stock):
    try:
        minute_high_df = history(240, '1m', 'high', [stock])
        if minute_high_df is None or minute_high_df.empty:
            return None
        if isinstance(minute_high_df, pd.DataFrame):
            series = minute_high_df[stock].dropna() if stock in minute_high_df.columns \
                else minute_high_df.iloc[:, 0].dropna()
        else:
            series = minute_high_df.dropna()
        if len(series) == 0:
            return None
        return float(series.max())
    except Exception:
        return None


# [Claude Opt: S-1b 顶层try-except防崩溃 + 批量预取tick]
def get_stock_list_A(context):
    try:
        return _get_stock_list_A_impl(context)
    except Exception as e:
        log.error("get_stock_list_A 总体异常(A选股跳过): {}".format(e))
        return []

def _get_stock_list_A_impl(context):
    target_list, target_list2 = prepare_A_stock_lists(context)
    firstboard_stocks, weak_to_strong_stocks = [], []
    current_data = get_current_data()
    cfg_a = g.strategies['A']['config']

    # [P-1] 批量预取tick, 避免循环内逐只high_limit RPC
    all_candidates = list(set(target_list + target_list2))
    if all_candidates and hasattr(current_data, 'get_batch'):
        try:
            current_data.get_batch(all_candidates)
        except Exception:
            pass

    start = context.current_dt.strftime("%Y-%m-%d") + ' 09:15:00'
    end   = context.current_dt.strftime("%Y-%m-%d") + ' 09:26:00'

    # 首板低开动态阈值 = base + scale * csi1000_percentile
    lowopen_rp_threshold = cfg_a.get('lowopen_rp_dynamic_base', 0.30) \
        + cfg_a.get('lowopen_rp_dynamic_scale', 0.60) * g.csi1000_percentile
    lowopen_gap_min = cfg_a.get('lowopen_gap_min', 0.96)
    lowopen_gap_max = cfg_a.get('lowopen_gap_max', 0.97)
    lowopen_min_money = cfg_a.get('lowopen_min_money', 1e8)
    lowopen_consec_days = cfg_a.get('lowopen_consecutive_days', 10)
    str_date = context.previous_date.strftime('%Y-%m-%d') if hasattr(context.previous_date, 'strftime') else str(context.previous_date)

    for stock in target_list:
        try:
            hd = attribute_history(stock, 60, '1d',
                                   fields=['close', 'high', 'low', 'money'],
                                   skip_paused=True)
            if len(hd) < 60:
                continue
            close  = hd['close'].iloc[-1]
            high   = hd['high'].max()
            low    = hd['low'].min()
            money  = hd['money'].iloc[-1]
            if high == low:
                continue

            rp_60d = (close - low) / (high - low)

            # === 首板低开(firstboard_lowopen)检测 ===
            # 条件: 60d相对位置≤动态阈值 + 成交额≥门槛 + 低开3-4% + 非连板
            lowopen_hit = False
            if rp_60d <= lowopen_rp_threshold and money >= lowopen_min_money:
                ad = get_call_auction(stock, start_date=start, end_date=end,
                                      fields=['time', 'current'])
                if not ad.empty:
                    open_gap = ad['current'].iloc[-1] / close
                    if lowopen_gap_min <= open_gap <= lowopen_gap_max:
                        if not is_consecutive_limit_up(stock, str_date, lowopen_consec_days):
                            lowopen_hit = True
                            firstboard_stocks.append({
                                'stock': stock, 'entry_type': 'firstboard_lowopen',
                                'rp_60d': rp_60d, 'open_gap': open_gap,
                            })

            # === 原有首板(firstboard)检测 ===
            firstboard_hit = False
            if not lowopen_hit:
                if rp_60d <= 0.5 and money >= 1e8:
                    ad = get_call_auction(stock, start_date=start, end_date=end,
                                          fields=['time', 'current'])
                    if not ad.empty and 0.955 <= ad['current'].iloc[-1] / close <= 0.97:
                        firstboard_hit = True

            pd_df = attribute_history(stock, 1, '1d',
                                      fields=['close', 'volume', 'money'],
                                      skip_paused=True)
            if len(pd_df) < 1 or pd_df['volume'][0] <= 0 or pd_df['close'][0] <= 0:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue

            if pd_df['money'][0] / pd_df['volume'][0] / pd_df['close'][0] * 1.1 - 1 < 0.07:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue
            if pd_df['money'][0] < g.cfg['A_min_prev_money'] \
                    or pd_df['money'][0] > g.cfg['A_max_prev_money']:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue

            val = get_valuation(
                stock,
                start_date=context.previous_date,
                end_date=context.previous_date,
                fields=['turnover_ratio', 'market_cap', 'circulating_market_cap']
            )
            if val.empty or val['market_cap'][0] < 70 or val['circulating_market_cap'][0] > 520:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue

            ad = get_call_auction(stock, start_date=start, end_date=end,
                                  fields=['time', 'volume', 'current'])
            if ad.empty or ad['volume'].iloc[-1] / pd_df['volume'][-1] \
                    < g.cfg['A_min_auction_volume_ratio']:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue
            if not (1 < ad['current'].iloc[-1] / pd_df['close'].iloc[-1] < 1.06):
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue

            hst = attribute_history(stock, 101, '1d',
                                    fields=['high', 'volume'], skip_paused=True)
            if len(hst) < 101:
                if firstboard_hit:
                    firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
                continue

            prev_high = hst['high'].iloc[-1]
            zyts_0 = next(
                (i - 1 for i, hv in enumerate(hst['high'][-3::-1], 2) if hv >= prev_high), 100)
            slice_start = max(0, len(hst) - (zyts_0 + 5))
            vol_slice   = hst['volume'].iloc[slice_start:]
            if len(vol_slice) >= 2 and vol_slice.iloc[-1] > max(vol_slice.iloc[:-1]) * 0.9:
                firstboard_hit = True

            if firstboard_hit:
                firstboard_stocks.append({'stock': stock, 'entry_type': 'firstboard'})
        except Exception as e:
            log.error("{} {}".format(stock, e))

    for stock in target_list2:
        try:
            pd_df = attribute_history(stock, 4, '1d',
                                      fields=['open', 'close', 'volume', 'money'],
                                      skip_paused=True)
            if len(pd_df) < 4:
                continue
            if (pd_df['close'].iloc[-1] - pd_df['close'].iloc[0]) / pd_df['close'].iloc[0] > 0.28:
                continue
            if (pd_df['close'].iloc[-1] - pd_df['open'].iloc[-1]) / pd_df['open'].iloc[-1] < -0.05:
                continue
            if pd_df['volume'].iloc[-1] <= 0 or pd_df['close'].iloc[-1] <= 0:
                continue
            if pd_df['money'].iloc[-1] / pd_df['volume'].iloc[-1] / pd_df['close'].iloc[-1] - 1 < -0.04:
                continue
            if pd_df['money'].iloc[-1] < 3e8 or pd_df['money'].iloc[-1] > 19e8:
                continue

            val = get_valuation(
                stock,
                start_date=context.previous_date,
                end_date=context.previous_date,
                fields=['turnover_ratio', 'market_cap', 'circulating_market_cap']
            )
            if val.empty or val['market_cap'][0] < 70 or val['circulating_market_cap'][0] > 520:
                continue

            ad = get_call_auction(stock, start_date=start, end_date=end,
                                  fields=['time', 'volume', 'current'])
            if ad.empty or ad['volume'].iloc[-1] / pd_df['volume'][-1] \
                    < g.cfg['A_min_auction_volume_ratio']:
                continue
            if not (0.98 < ad['current'].iloc[-1] / (current_data[stock].high_limit / 1.1) < 1.09):
                continue

            hst = attribute_history(stock, 101, '1d',
                                    fields=['high', 'volume'], skip_paused=True)
            if len(hst) < 101:
                continue

            prev_high = hst['high'].iloc[-1]
            zyts_0 = next(
                (i - 1 for i, hv in enumerate(hst['high'][-3::-1], 2) if hv >= prev_high), 100)
            slice_start = max(0, len(hst) - (zyts_0 + 5))
            vol_slice   = hst['volume'].iloc[slice_start:]
            if len(vol_slice) < 2 or vol_slice.iloc[-1] <= max(vol_slice.iloc[:-1]) * 0.9:
                continue

            weak_to_strong_stocks.append({'stock': stock, 'entry_type': 'weak_to_strong'})
        except Exception as e:
            log.error("{} {}".format(stock, e))

    uniq, seen = [], set()
    for item in firstboard_stocks + weak_to_strong_stocks:
        if item['stock'] in seen:
            continue
        uniq.append(item)
        seen.add(item['stock'])
    return uniq


# [Claude Opt: S-1a 顶层try-except防崩溃 + 关键API空值防护 + seed批量预取tick]
def get_dragon_stock_list_A(context):
    try:
        return _get_dragon_stock_list_A_impl(context)
    except Exception as e:
        log.error("get_dragon_stock_list_A 总体异常(Dragon选股跳过): {}".format(e))
        return []

def _get_dragon_stock_list_A_impl(context):
    universe = get_base_stock_universe(context, include_new=False)
    if not universe:
        return []

    current_data = get_current_data()
    prev_date = context.previous_date
    if prev_date is None:
        log.warning("get_dragon_stock_list_A: previous_date为None, 跳过")
        return []
    prev_trade_days = get_trade_days(end_date=prev_date, count=2)
    prev_prev_date = prev_trade_days[0] if len(prev_trade_days) >= 2 else None

    start_today = context.current_dt.strftime("%Y-%m-%d") + ' 09:15:00'
    end_today   = context.current_dt.strftime("%Y-%m-%d") + ' 09:26:00'
    start_prev  = str(prev_date) + ' 09:15:00'
    end_prev    = str(prev_date) + ' 09:26:00'

    # [预筛版] count 4→25：为 6 因子(avg_money5/10, ret5/10, close_to_20d_high, range_10)取足够历史；新增 'low'
    price_df = get_price(
        universe, end_date=prev_date, frequency='daily',
        fields=['close', 'high', 'low', 'high_limit', 'money', 'volume', 'paused'],
        count=25, panel=False
    )
    if price_df is None or price_df.empty:
        return []

    per_stock, ret3_list, money_list = {}, [], []
    for stock, df in price_df.groupby('code'):
        df = df.sort_values('time')
        if len(df) < 4:
            continue
        if df['paused'].iloc[-1] != 0:
            continue
        cl = [float(x) for x in df['close'].values]
        hi = [float(x) for x in df['high'].values]
        lo = [float(x) for x in df['low'].values]
        mo = [float(x) for x in df['money'].values]
        y_close  = cl[-1]
        y_high   = hi[-1]
        y_hl     = float(df['high_limit'].iloc[-1])
        y_money  = mo[-1]
        y_vol    = float(df['volume'].iloc[-1])
        # ret3 保持"3日"语义(原 count=4 时 iloc[0]==cl[-4])
        ret3     = y_close / cl[-4] - 1 if len(cl) >= 4 and cl[-4] > 0 else 0
        ret1     = y_close / cl[-2] - 1 if len(cl) >= 2 and cl[-2] > 0 else 0
        # [预筛版] 6 因子(与 skill jq_screener 完全一致)
        def _mean(a, n):
            a = a[-n:]
            return sum(a) / len(a) if a else 0.0
        avg_money5  = _mean(mo, 5)
        avg_money10 = _mean(mo, 10)
        ret5  = y_close / cl[-6] - 1 if len(cl) >= 6 and cl[-6] > 0 else 0
        ret10 = y_close / cl[-11] - 1 if len(cl) >= 11 and cl[-11] > 0 else 0
        rng = [(hi[i] - lo[i]) / cl[i] for i in range(len(cl)) if cl[i] > 0]
        range_10 = _mean(rng, 10)
        hi20 = max(cl[-20:]) if len(cl) >= 20 else max(cl)
        close_to_20d_high = y_close / hi20 if hi20 > 0 else 0
        per_stock[stock] = {
            'y_close': y_close, 'y_high': y_high, 'y_hl': y_hl,
            'y_money': y_money, 'y_vol': y_vol, 'ret3': ret3, 'ret1': ret1,
            'avg_money5': avg_money5, 'avg_money10': avg_money10, 'ret5': ret5, 'ret10': ret10,
            'range_10': range_10, 'avg_range': range_10, 'close_to_20d_high': close_to_20d_high,
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

    # ==========================================================
    # [预筛版 V1.2.0] 6 因子预筛 top-N —— 与 skill jq_screener 逐位一致
    #   20 交易日 eod 回测(D1): 被砍尾部票次日 -0.91%/胜率40%/0涨停;
    #   保留票 +0.81%/61%; 池整体 +0.64% → +1.14%, 胜率 56% → 62%.
    #   步骤: 硬门槛(昨非涨停 + y_money≥门槛 + avg_range≤上限) → 6 因子综合排名取前 N.
    # ==========================================================
    STAR_N = g.cfg.get('dragon_star_prefilter_n', 250)
    _pre = []
    for s in seed:
        m = per_stock.get(s)
        if not m:
            continue
        if m['y_close'] >= m['y_hl'] * 0.995:
            continue
        if m['y_money'] < g.cfg['dragon_min_prev_money']:
            continue
        if m['avg_range'] > g.cfg.get('dragon_max_avg_daily_range', 0.08):
            continue
        _pre.append(s)
    if _pre:
        def _rank(key, rev=True):
            order = sorted(_pre, key=lambda s: per_stock[s][key], reverse=rev)
            return {s: i for i, s in enumerate(order)}
        r_am5 = _rank('avg_money5'); r_am10 = _rank('avg_money10')
        r_r5 = _rank('ret5'); r_r10 = _rank('ret10')
        r_c2h20 = _rank('close_to_20d_high'); r_rng = _rank('range_10')
        _comp = {s: (r_am5[s] * 0.25 + r_am10[s] * 0.15 + r_r5[s] * 0.20 +
                     r_r10[s] * 0.10 + r_c2h20[s] * 0.15 + r_rng[s] * 0.15) for s in _pre}
        _pre = sorted(_pre, key=lambda s: _comp[s])[:STAR_N]
    seed = set(_pre)
    if not seed:
        return []

    # [Claude Opt: P-1 seed批量预取tick, 避免循环内逐只high_limit RPC]
    if hasattr(current_data, 'get_batch'):
        try:
            current_data.get_batch(list(seed))
        except Exception:
            pass

    auc_data = []
    for stock in seed:
        meta = per_stock.get(stock)
        if not meta:
            continue
        try:
            if meta['y_close'] >= meta['y_hl'] * 0.995:
                continue
            if meta['y_money'] < g.cfg['dragon_min_prev_money']:
                continue

            # 日均振幅过滤 & 记录(v3评分使用)
            avg_range = 0.0
            try:
                h_vol = attribute_history(stock, 10, '1d',
                                          ['high', 'low', 'close'], skip_paused=True)
                if len(h_vol) >= 5:
                    avg_range = ((h_vol['high'] - h_vol['low']) / h_vol['close']).mean()
                    if avg_range > g.cfg.get('dragon_max_avg_daily_range', 0.08):
                        continue
            except Exception:
                pass
            meta['avg_range'] = avg_range

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
            if prev_prev_date is not None:
                prev_ad = get_call_auction(stock, start_date=start_prev, end_date=end_prev,
                                           fields=['time', 'volume', 'current'])
                if prev_ad is not None and not prev_ad.empty:
                    prev_auc_vol = float(prev_ad['volume'].iloc[-1])

            auc_data.append({
                'stock': stock, 'open_ratio': open_ratio, 'auc_ratio': auc_ratio,
                'auc_amount': auc_amount, 'prev_auc_vol': prev_auc_vol,
            })
        except Exception as e:
            log.error("{} {}".format(stock, e))

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
    if not dragon_candidates:
        return

    # 打印Dragon候选池明细
    detail_parts = []
    for i, item in enumerate(dragon_candidates[:12]):
        detail_parts.append("{}:{} s={:.3f} tpl={} or={:.1f}%".format(
            i + 1, item.get('stock', '?'), item.get('dragon_score', 0),
            item.get('tpl', '?'), item.get('open_ratio', 0) * 100))
    log.info("🐉【Dragon候选池】共{}只: {}".format(len(dragon_candidates), ' | '.join(detail_parts)))

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
def score_candidates_A(context, candidates, mode='normal', pos_ratio=None):
    """A策略打分 — 趋势过滤系统

    [V1.1.0] 核心改动:
    1. Dragon: 趋势过滤器替代unified_score阈值拦截
       - 选股逻辑通过即可买入,不再被base_edge为负一票否决
       - 趋势过滤器决定放行/拦截, unified_score只调仓位
    2. Lowopen: 保持unified_score评分(统计套利型,评分有效)
    3. Normal: 趋势过滤器 + 基础评分
    4. 移除panic_scout模式(由趋势过滤器自动处理)
    """
    current_data = get_current_data()
    # [P-1] 批量预取候选股tick, 避免循环内逐只RPC
    if candidates and hasattr(current_data, 'get_batch'):
        try:
            current_data.get_batch([item['stock'] for item in candidates])
        except Exception:
            pass
    scored = []
    base_pos_ratio = pos_ratio if pos_ratio is not None else g.strategy_budget['A']['pos_ratio']
    cfg = g.cfg
    cfg_a = g.strategies['A']['config']
    unified_enable = cfg.get('unified_scoring_enable', False)
    trend_enable = cfg.get('trend_filter_enable', True)

    for item in candidates:
        stock      = item['stock']
        entry_type = item['entry_type']
        try:
            curr_price = current_data[stock].last_price
            if curr_price <= 0 or curr_price >= current_data[stock].high_limit * cfg['A_limit_up_buffer']:
                continue
            h = attribute_history(stock, 2, '1d', ['close'])
            if len(h) < 2:
                continue
            open_ratio = current_data[stock].day_open / h['close'].iloc[-1] - 1

            # ===== 趋势过滤(所有entry_type统一入口) =====
            trend_pos_mult = 1.0
            if trend_enable:
                trend_pass, trend_pos_mult, trend_reason = check_stock_trend_filter(
                    stock, entry_type, context)
                if not trend_pass:
                    log.info("📉{}({}) 趋势过滤拦截: {}".format(stock, entry_type, trend_reason))
                    continue
                if trend_pos_mult < 1.0:
                    log.info("📊{}({}) 趋势缩仓: ×{:.1f} ({})".format(
                        stock, entry_type, trend_pos_mult, trend_reason))

            if entry_type == 'firstboard_lowopen':
                # 首板低开: 保持unified_score评分(统计套利型)
                item['open_ratio'] = open_ratio
                item_pos_ratio = min(base_pos_ratio, cfg_a.get('lowopen_pos_ratio', 0.25))

                if unified_enable:
                    u_score, base_edge, q_mult, env_w = compute_unified_score(
                        entry_type, item, context)
                    if u_score < g.unified_min_threshold:
                        log.info("{}({}) 统一评分{:.4f}<阈值{:.4f}, 跳过".format(
                            stock, entry_type, u_score, g.unified_min_threshold))
                        continue
                    score = u_score
                    log.info("📊{}({}) unified={:.4f} base={:.4f} q={:.2f} env={:.3f}".format(
                        stock, entry_type, u_score, base_edge, q_mult, env_w))
                else:
                    score = 0.05 + (0.5 - item.get('rp_60d', 0.5)) * 0.1

            elif entry_type == 'dragon_follow' or mode == 'dragon':
                # Dragon: 趋势过滤通过即可买入, unified_score只调仓位不拦截
                if open_ratio < cfg['A_dragon_min_open_ratio']:
                    continue

                # deep_water 限制
                tpl = item.get('tpl', 'base')
                if (tpl == 'trend_core'
                        and cfg.get('dragon_trend_core_policy') == 'bull_up_only'
                        and not (g.market_regime == 'bull'
                                 and getattr(g, 'market_trend', 'sideways') == 'up')):
                    log.info("📉{} trend_core 拦截: policy=bull_up_only regime={} trend={}".format(
                        stock, g.market_regime, getattr(g, 'market_trend', 'sideways')))
                    continue

                if cfg.get('dragon_open_tier_enable', False) and entry_type == 'dragon_follow':
                    mid = cfg.get('dragon_open_tier_mid', 0.03)
                    high = cfg.get('dragon_open_tier_high', 0.04)
                    if open_ratio > high:
                        log.info("{} Dragon高开超限跳过: open_ratio={:.2%} high={:.2%}".format(
                            stock, open_ratio, high))
                        continue

                if open_ratio > cfg['A_dragon_max_open_ratio']:
                    continue

                bear_dw_flag = False
                if tpl == 'deep_water':
                    max_dw = cfg.get('A_dragon_deep_water_max_open_ratio', 0.05)
                    if open_ratio > max_dw:
                        log.info("{} deep_water 高开{:.1f}%超限，跳过".format(
                            stock, open_ratio * 100))
                        continue
                    if g.market_regime == 'bear':
                        bear_dw_policy = cfg.get('A_dragon_bear_allow_deep_water', 'half')
                        if bear_dw_policy is False:
                            log.info("{} bear市禁止deep_water，跳过".format(stock))
                            continue
                        elif bear_dw_policy == 'half':
                            bear_dw_flag = True

                tpl_bonus = 0.020 if tpl == 'deep_water' else 0.010
                score = item.get('dragon_score', 0.0) + open_ratio + tpl_bonus

                # [V1.1.0] unified_score用于排序和仓位调节,不再做阈值拦截
                if unified_enable:
                    item['open_ratio'] = open_ratio
                    u_score, base_edge, q_mult, env_w = compute_unified_score(
                        entry_type, item, context)
                    # 用quality和env_weight调仓位,不再拦截
                    score_pos_mult = max(0.5, min(1.5, q_mult * env_w))
                    log.info("📊{}({}) dragon_score={:.3f} q={:.2f} env={:.3f} pos_mult={:.2f}".format(
                        stock, entry_type, score, q_mult, env_w, score_pos_mult))
                else:
                    score_pos_mult = 1.0
                    if score < cfg['A_dragon_min_score']:
                        continue

                item_pos_ratio = min(base_pos_ratio, cfg['A_dragon_pos_ratio'])
                # unified_score仓位调节
                item_pos_ratio = item_pos_ratio * score_pos_mult
                if cfg.get('dragon_open_tier_enable', False) and entry_type == 'dragon_follow':
                    mid = cfg.get('dragon_open_tier_mid', 0.03)
                    mid_mult = cfg.get('dragon_open_tier_mid_mult', 0.5)
                    if open_ratio > mid:
                        item_pos_ratio = item_pos_ratio * mid_mult
                        log.info("⚠️{} Dragon高开分层: open_ratio={:.2%}, pos_mult*={:.2f}".format(
                            stock, open_ratio, mid_mult))

                # bear下deep_water减半
                if bear_dw_flag:
                    item_pos_ratio = item_pos_ratio * 0.5
                    log.info("{} bear市deep_water仓位减半→{:.2f}".format(stock, item_pos_ratio))

                # 连亏保护: 降低Dragon仓位
                if getattr(g, 'dragon_reduced_pos_active', False):
                    reduced = g.cfg.get('dragon_loss_reduced_pos_ratio', 0.15)
                    item_pos_ratio = min(item_pos_ratio, reduced)

            else:
                # Normal模式(firstboard / weak_to_strong)
                if open_ratio < cfg['A_normal_min_open_ratio']:
                    continue
                bonus = cfg['A_normal_firstboard_bonus'] if entry_type == 'firstboard' \
                    else cfg['A_normal_weak_bonus']
                score = open_ratio + bonus

                if unified_enable:
                    item['open_ratio'] = open_ratio
                    u_score, base_edge, q_mult, env_w = compute_unified_score(
                        entry_type, item, context)
                    if u_score < g.unified_min_threshold:
                        continue
                    score = u_score
                elif score < cfg['A_normal_min_score']:
                    continue

                item_pos_ratio = base_pos_ratio

            # 趋势缩仓乘数(大盘下跌时自动缩仓)
            item_pos_ratio = item_pos_ratio * trend_pos_mult

            scored.append({
                'stock': stock, 'entry_type': entry_type,
                'open_ratio': open_ratio, 'score': score,
                'curr_price': curr_price, 'pos_ratio': item_pos_ratio,
                'tpl': item.get('tpl', 'base'),
                'rp_60d': item.get('rp_60d'),
                'open_gap': item.get('open_gap'),
                'trend_reason': trend_reason if trend_enable else 'disabled',
            })
        except Exception as e:
            log.error("{} {}".format(stock, e))

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored



def prepare_A_stock_lists(context):
    yesterday = context.previous_date
    universe  = get_base_stock_universe(context, include_new=False)
    hl1_list  = set(g.limit_up_cache[-2]) if len(g.limit_up_cache) >= 2 else set()
    hl_list   = [s for s in get_limit_up_stocks(universe, yesterday, 1) if s not in hl1_list]
    hl_list2  = [s for s in get_touch_limit_up_stocks(universe, yesterday) if s not in hl1_list]
    return hl_list, hl_list2


# [Claude Opt: P-3 批量预取tick减少3000+次逐只RPC; S-2 tick全空安全校验]
def get_base_stock_universe(context, include_new=False):
    try:
        all_sec = get_all_securities('stock', context.previous_date)
        if all_sec is None or all_sec.empty:
            log.warning("get_base_stock_universe: get_all_securities返回空, 返回空列表")
            return []
        initial_list = all_sec.index.tolist()
    except Exception as e:
        log.warning("get_base_stock_universe: get_all_securities异常: {}, 返回空列表".format(e))
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

    # [S-2] 安全校验: tick全空说明数据源异常, 记日志警告
    if len(initial_list) > 100 and valid_tick_count == 0:
        log.warning("⚠️ get_base_stock_universe: {}只股票tick全部无效, 数据源可能异常".format(len(initial_list)))

    if not include_new:
        cutoff_date = context.current_dt.date() - timedelta(days=g.cfg['new_stock_days'])
        new_filtered = []
        for s in filtered:
            try:
                info = get_security_info(s)
                if info.start_date and info.start_date < cutoff_date:
                    new_filtered.append(s)
            except Exception:
                continue
        filtered = new_filtered
    return filtered


def refresh_limit_up_cache(context):
    yesterday = context.previous_date
    universe  = get_base_stock_universe(context, include_new=False)
    if not g.limit_up_cache:
        for day in get_trade_days(end_date=yesterday, count=3)[:-1]:
            g.limit_up_cache.append(get_limit_up_stocks(universe, day, 1))
    g.limit_up_cache.append(get_limit_up_stocks(universe, yesterday, 1))
    if len(g.limit_up_cache) > 3:
        g.limit_up_cache.pop(0)


def get_limit_up_stocks(sl, d, days):
    if not sl:
        return []
    df = get_price(sl, end_date=d, frequency='daily',
                   fields=['close', 'high_limit', 'paused'],
                   count=days, panel=False)
    if df is None or df.empty:
        return []
    mask = (df['close'] == df['high_limit']) & (df['paused'] == 0)
    return df.loc[mask, 'code'].drop_duplicates().tolist()


def get_touch_limit_up_stocks(sl, d):
    if not sl:
        return []
    df = get_price(sl, end_date=d, frequency='daily',
                   fields=['close', 'high', 'high_limit', 'paused'],
                   count=1, panel=False)
    if df is None or df.empty:
        return []
    mask = (df['close'] != df['high_limit']) \
           & (df['high'] == df['high_limit']) \
           & (df['paused'] == 0)
    return df.loc[mask, 'code'].drop_duplicates().tolist()


# =========================================================
# 底层工具
# =========================================================


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
        'intraday_panic': 0,
        'intraday_pos_cap': 0,
        'risk_panic_yesterday': 0,
        'orphan_sell': 0,
        'regime': 'neutral',
        'micro_regime': 'neutral_trend',
        'market_trend': 'sideways',
        'no_new': 0,
        # [DPM] 动态仓位管理诊断
        'dpm_expanded': 0,
        'dpm_max_pos': 3,
        'dpm_max_ratio': 0.75,
        'dpm_A_avg_profit': 0.0,
        # [OPT] 优化诊断
        'regime_secondary': 'neutral',
        'regime_dual_override': 0,
        'dragon_circuit_breaker_active': 0,
        'dragon_bear_freq_limit': 0,
        'dragon_consecutive_losses': 0,
        'dragon_cb_pause_left': 0,
        'dragon_bear_weekly_count': 0,
    }


# --- Migrated core functions ---

def morning_prepare(context):
    try:
        _morning_prepare_impl(context)
    except Exception as e:
        log.error("morning_prepare异常: {}".format(e))

def _morning_prepare_impl(context):
    if g.bt['start_cash'] is None:
        g.bt['start_cash'] = context.portfolio.total_value
        g.bt['start_date'] = str(context.current_dt.date())

    g.daily_new_position_count = 0
    g.no_new_position_today = False

    g.panic_scout_enabled_today = False
    g.panic_yesterday_ret = 0.0
    g.panic_scout_pos_ratio = 0.0
    g.panic_scout_max_hold = 0
    g.panic_scout_min_open_ratio = 0.0
    g.panic_scout_level = 'none'

    g.dragon_mode = False
    g.dragon_pool_size = 0
    g.dragon_top_score = 0.0
    g.dragon_candidates_today = []
    g.dragon_signal_reason = 'none'
    g.dragon_evaluated_today = False

    # [v9.0.19] TickSignalEngine每日重置
    get_tick_engine().reset_daily()

    # 【关键】先同步pending_buys→positions_meta，再做D恢复
    # 否则昨天买的D持仓在sync之前meta还是空的，会被误标unknown
    reset_daily_diag(context)
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
            log.warning("⚠️【重启恢复】{} 无法确定策略归属, 标记为unknown(5%止损)".format(stock))

    if g.A_rearm_grace_days_left > 0:
        g.A_rearm_grace_days_left -= 1

    # [P0-FIX-1] crowding 冷却倒计时
    if g.crowding_cooldown_left > 0:
        g.crowding_cooldown_left -= 1

    # [OPT-1] Dragon 断路器冷却倒计时
    if g.dragon_circuit_breaker_pause_left > 0:
        g.dragon_circuit_breaker_pause_left -= 1
        if g.dragon_circuit_breaker_pause_left == 0:
            g.dragon_consecutive_losses = 0
            g.dragon_loss_history = []
            g.dragon_reduced_pos_active = False  # [改进2] 恢复仓位
            log.info("🔓【Dragon断路器】冷却结束，连亏计数清零，仓位恢复")

    # [OPT-3] Bear Dragon 周频率计数重置
    if g.dragon_bear_weekly_reset_countdown > 0:
        g.dragon_bear_weekly_reset_countdown -= 1
        if g.dragon_bear_weekly_reset_countdown == 0:
            g.dragon_bear_weekly_count = 0

    check_orphan_positions(context)

    update_market_regime(context)
    g.market_trend = get_market_trend(context)       # [V1.1.0] 大盘趋势判断
    g.intraday_panic_active = False                  # 重置盘中恐慌标记
    update_unified_scoring_env(context)              # 统一评分系统环境更新(依赖regime)
    update_daily_risk_switch_yesterday(context)
    update_micro_regime_without_dragon(context)
    refresh_strategy_budget()
    update_dynamic_position_limits(context)         # [DPM] 动态仓位更新

    update_portfolio_nav_and_brake(context)
    refresh_limit_up_cache(context)

    g.diag['regime'] = g.market_regime
    g.diag['micro_regime'] = g.micro_regime
    g.diag['market_trend'] = g.market_trend
    g.diag['no_new'] = 0  # [V1.1.0] 不再全面禁买

    log.info("Pre: R={}(2nd={}{}) M={} T={} A={} | A_cool={}/{}/{} AG={} DCB={}/{}".format(
        g.market_regime,
        g.regime_secondary_raw,
        ' OVR' if g.regime_dual_override_active else '',
        g.micro_regime,
        g.market_trend,
        g.strategy_budget.get('A', {}),
        int(g.A_dd_cooldown_active), g.A_pause_days_left, int(g.A_dd_rearm_ready),
        g.A_rearm_grace_days_left,
        g.dragon_consecutive_losses, g.dragon_circuit_breaker_pause_left
    ))

def post_auction_prepare(context):
    try:
        _post_auction_prepare_impl(context)
    except Exception as e:
        log.error("post_auction_prepare异常: {}".format(e))

def _post_auction_prepare_impl(context):
    update_dragon_mode(context)
    update_micro_regime(context)
    refresh_strategy_budget()
    g.dragon_evaluated_today = True

    g.diag['dragon_mode'] = 1 if g.dragon_mode else 0
    g.diag['dragon_pool_size'] = g.dragon_pool_size
    g.diag['dragon_top_score'] = g.dragon_top_score
    g.diag['micro_regime'] = g.micro_regime

    log.info("Post-Auction: Micro={}, Dragon={}, pool={}, top_score={:.3f}, "
             "score_ema={:.3f}, crowding_confirm={}, crowding_consec={}, crowding_cd={}, "
             "A={}".format(
        g.micro_regime,
        1 if g.dragon_mode else 0,
        g.dragon_pool_size,
        g.dragon_top_score,
        g.dragon_score_ema,
        g.crowding_confirm_days,
        g.crowding_consecutive_days,
        g.crowding_cooldown_left,
        g.strategy_budget['A']
    ))

    # [v9.0.19] 竞价强度因子: 从竞价序列计算auction_score
    engine = get_tick_engine()
    if engine.enabled:
        try:
            scored_count = 0

            # QMT实盘: 从竞价缓存计算
            if getattr(g, 'is_qmt', False):
                auction_cache = get_auction_cache()
                for qmt_code, cache_data in auction_cache.items():
                    snapshots = cache_data.get('snapshots', [])
                    if not snapshots:
                        continue
                    # qmt_code转jq_code
                    jq_code = qmt_code
                    if '.SH' in qmt_code:
                        jq_code = qmt_code.replace('.SH', '.XSHG')
                    elif '.SZ' in qmt_code:
                        jq_code = qmt_code.replace('.SZ', '.XSHE')
                    score = engine.compute_auction_score(jq_code, snapshots)
                    scored_count += 1

            # 聚宽回测: 用get_ticks/get_call_auction近似
            if not getattr(g, 'is_qmt', False) and hasattr(g, 'dragon_candidates_today'):
                for item in g.dragon_candidates_today:
                    stock = item if isinstance(item, str) else item.get('stock', '')
                    if stock:
                        engine.compute_auction_score_jq(stock, context)
                        scored_count += 1

            if scored_count > 0:
                log.info("[TickEngine] 竞价评分: {}只 (异常={})".format(
                    scored_count,
                    sum(1 for s in engine.auction_scores.values() if s < 0.4)))
        except Exception as e:
            log.warning("[TickEngine] 竞价评分异常: {}".format(e))

def after_market_close(context):
    try:
        _after_market_close_impl(context)
    except Exception as e:
        log.error("after_market_close异常: {}".format(e))
    # [v9.0.25] 生成每日MD报告
    try:
        _generate_daily_report(context)
    except Exception as e:
        log.error("每日报告生成异常: {}".format(e))


def _generate_daily_report(context):
    """[v9.0.25] 生成每日实盘数据报告(MD格式), 用于debug和参数调优"""
    import os
    today = context.current_dt.date() if hasattr(context.current_dt, 'date') else context.current_dt
    today_str = str(today)

    # 报告目录
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_reports')
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    report_path = os.path.join(report_dir, '{}.md'.format(today_str))

    lines = []
    lines.append('# 全天候战车 每日实盘报告')
    lines.append('')
    lines.append('**日期**: {}  **版本**: v9.0.25'.format(today_str))
    lines.append('')

    # ── 1. 账户概览 ──
    lines.append('## 1. 账户概览')
    lines.append('')
    total_value = context.portfolio.total_value
    available = context.portfolio.available_cash
    positions_value = total_value - available
    start_cash = g.bt.get('start_cash', total_value) or total_value
    nav = total_value / start_cash if start_cash > 0 else 1.0
    total_return = (nav - 1) * 100
    trade_days = g.bt.get('trade_days', 0)
    current_dd = g.bt.get('current_dd', 0)
    wins = g.bt.get('wins', 0)
    losses = g.bt.get('losses', 0)
    closed = g.bt.get('closed_trades', 0)
    win_rate = wins / closed * 100 if closed > 0 else 0
    avg_win = g.bt.get('win_ret_sum', 0) / wins * 100 if wins > 0 else 0
    avg_loss = g.bt.get('loss_ret_sum', 0) / losses * 100 if losses > 0 else 0
    pf = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    lines.append('| 指标 | 值 |')
    lines.append('|------|-----|')
    lines.append('| 总资产 | {:.2f} |'.format(total_value))
    lines.append('| 可用资金 | {:.2f} |'.format(available))
    lines.append('| 持仓市值 | {:.2f} |'.format(positions_value))
    lines.append('| 仓位比例 | {:.1f}% |'.format(positions_value / total_value * 100 if total_value > 0 else 0))
    lines.append('| 净值 | {:.4f} |'.format(nav))
    lines.append('| 累计收益 | {:+.2f}% |'.format(total_return))
    lines.append('| 当前回撤 | {:.2f}% |'.format(current_dd * 100))
    lines.append('| 交易天数 | {} |'.format(trade_days))
    lines.append('| 总交易笔数 | {} |'.format(closed))
    lines.append('| 胜率 | {:.1f}% ({}/{}) |'.format(win_rate, wins, closed))
    lines.append('| 盈亏比 | {:.2f} |'.format(pf))
    lines.append('| 平均盈利 | {:+.2f}% |'.format(avg_win))
    lines.append('| 平均亏损 | {:.2f}% |'.format(avg_loss))
    lines.append('')

    # ── 2. 当前持仓 ──
    lines.append('## 2. 当前持仓')
    lines.append('')
    positions = context.portfolio.positions
    if positions:
        lines.append('| 股票 | 策略 | 入场类型 | 阶段 | 成本 | 现价 | 盈亏 | 持仓量 | 市值 |')
        lines.append('|------|------|----------|------|------|------|------|--------|------|')
        for stock, pos in positions.items():
            meta = g.positions_meta.get(stock, {})
            strategy = meta.get('strategy', '?')
            entry_type = meta.get('entry_type', '?')
            stage = meta.get('stage', '?')
            avg_cost = pos.avg_cost
            curr_price = pos.price if hasattr(pos, 'price') else pos.last_sale_price if hasattr(pos, 'last_sale_price') else 0
            pnl = (curr_price / avg_cost - 1) * 100 if avg_cost > 0 and curr_price > 0 else 0
            value = pos.value if hasattr(pos, 'value') else pos.total_amount * curr_price if hasattr(pos, 'total_amount') else 0
            amount = pos.total_amount if hasattr(pos, 'total_amount') else 0
            lines.append('| {} | {} | {} | {} | {:.3f} | {:.3f} | {:+.2f}% | {} | {:.0f} |'.format(
                stock, strategy, entry_type, stage, avg_cost, curr_price, pnl, amount, value))
    else:
        lines.append('*空仓*')
    lines.append('')

    # ── 3. 今日交易记录 ──
    lines.append('## 3. 今日交易')
    lines.append('')
    lines.append('| 指标 | A策略 |')
    lines.append('|------|-------|')
    lines.append('| 买入笔数 | {} |'.format(g.diag.get('A_buys_orders', 0)))
    lines.append('| 卖出(全) | {} |'.format(g.diag.get('A_sell_all', 0)))
    lines.append('| 卖出(半) | {} |'.format(g.diag.get('A_sell_half', 0)))
    lines.append('')

    # ── 4. 市场状态 ──
    lines.append('## 4. 市场状态')
    lines.append('')
    lines.append('| 指标 | 值 | 说明 |')
    lines.append('|------|-----|------|')
    lines.append('| 主线regime | {} | 主指数趋势 |'.format(g.market_regime))
    lines.append('| 副线regime | {} | 副指数趋势 |'.format(g.diag.get('regime_secondary', 'N')))
    lines.append('| 双线覆写 | {} | 副线是否覆写主线 |'.format(g.diag.get('regime_dual_override', 0)))
    lines.append('| micro_regime | {} | 微观状态 |'.format(g.micro_regime))
    lines.append('| 日内panic | {} | 盘中恐慌触发 |'.format(g.diag.get('intraday_panic', 0)))
    lines.append('')

    # ── 5. Dragon龙头模式 ──
    lines.append('## 5. Dragon龙头模式')
    lines.append('')
    lines.append('| 指标 | 值 |')
    lines.append('|------|-----|')
    lines.append('| 激活 | {} |'.format('是' if g.dragon_mode else '否'))
    lines.append('| 候选池大小 | {} |'.format(g.dragon_pool_size))
    lines.append('| 最高得分 | {:.3f} |'.format(g.dragon_top_score))
    lines.append('| 得分EMA | {:.3f} |'.format(g.dragon_score_ema))
    lines.append('| 信号原因 | {} |'.format(getattr(g, 'dragon_signal_reason', 'none')))
    lines.append('| 连续亏损 | {} |'.format(g.dragon_consecutive_losses))
    lines.append('| 断路器暂停 | {}天 |'.format(g.dragon_circuit_breaker_pause_left))
    lines.append('| 熊市周交易数 | {} |'.format(g.dragon_bear_weekly_count))
    lines.append('')

    # 候选列表
    if g.dragon_candidates_today:
        lines.append('### Dragon候选列表')
        lines.append('')
        lines.append('| 排名 | 股票 | 得分 | 入场类型 | 模板 |')
        lines.append('|------|------|------|----------|------|')
        for i, item in enumerate(g.dragon_candidates_today[:10]):
            lines.append('| {} | {} | {:.4f} | {} | {} |'.format(
                i + 1,
                item.get('stock', '?'),
                item.get('dragon_score', 0),
                item.get('entry_type', '?'),
                item.get('template', '?')))
        lines.append('')

    # ── 6. 策略状态 ──
    lines.append('## 6. 策略状态')
    lines.append('')

    # A策略
    lines.append('### A策略 (龙头追涨)')
    lines.append('')
    lines.append('| 指标 | 值 |')
    lines.append('|------|-----|')
    lines.append('| 模式 | {} |'.format(
        'dragon' if g.diag.get('A_dragon_mode') else 'normal'))
    lines.append('| 暂停天数 | {} |'.format(g.diag.get('A_pause_days_left', 0)))
    lines.append('| 回撤冷却 | {} |'.format(g.diag.get('A_dd_cooldown_active', 0)))
    lines.append('| 修复就绪 | {} |'.format(g.diag.get('A_dd_rearm_ready', 0)))
    lines.append('| Grace天数 | {} |'.format(g.diag.get('A_rearm_grace_days_left', 0)))
    lines.append('| 空仓天数 | {} |'.format(g.diag.get('A_flat_days', 0)))
    lines.append('| 预算 | max_hold={} pos_ratio={} |'.format(
        g.strategy_budget.get('A', {}).get('max_hold', '?') if hasattr(g, 'strategy_budget') else '?',
        g.strategy_budget.get('A', {}).get('pos_ratio', '?') if hasattr(g, 'strategy_budget') else '?'))
    lines.append('')

    # B策略
    # Crowding
    lines.append('### Crowding拥挤度')
    lines.append('')
    lines.append('| 指标 | 值 |')
    lines.append('|------|-----|')
    lines.append('| 确认天数 | {} |'.format(g.crowding_confirm_days))
    lines.append('| 原始信号 | {} |'.format(g.diag.get('crowding_signal_raw', 0)))
    lines.append('| 连续天数 | {} |'.format(g.crowding_consecutive_days))
    lines.append('| 冷却剩余 | {} |'.format(g.crowding_cooldown_left))
    lines.append('')

    # ── 7. 风控指标 ──
    lines.append('## 7. 风控指标')
    lines.append('')
    lines.append('| 指标 | 值 |')
    lines.append('|------|-----|')
    lines.append('| 大盘趋势 | {} |'.format(g.diag.get('market_trend', 'N/A')))
    lines.append('| 盘中大跌 | {} |'.format(g.diag.get('intraday_panic', 0)))
    lines.append('| 仓位上限触发 | {} |'.format(g.diag.get('intraday_pos_cap', 0)))
    lines.append('| Unknown持仓 | {} |'.format(g.diag.get('unknown_positions', 0)))
    lines.append('| Pending退出 | {} |'.format(g.diag.get('pending_exit_positions', 0)))
    lines.append('| DPM扩容 | {} (max={}, ratio={:.0f}%) |'.format(
        g.diag.get('dpm_expanded', 0),
        g.diag.get('dpm_max_pos', 3),
        g.diag.get('dpm_max_ratio', 0.75) * 100))
    lines.append('')

    # ── 8. TickSignalEngine ──
    lines.append('## 8. TickSignalEngine')
    lines.append('')
    engine = get_tick_engine()
    if engine.enabled:
        # 竞价评分
        if engine.auction_scores:
            lines.append('### 竞价评分')
            lines.append('')
            lines.append('| 股票 | 得分 |')
            lines.append('|------|------|')
            for stock, score in sorted(engine.auction_scores.items(), key=lambda x: -x[1]):
                lines.append('| {} | {:.3f} |'.format(stock, score))
            lines.append('')

        # ATR缓存
        if engine.atr_cache:
            lines.append('### ATR值')
            lines.append('')
            lines.append('| 股票 | ATR |')
            lines.append('|------|-----|')
            for stock, atr in engine.atr_cache.items():
                lines.append('| {} | {:.3f} |'.format(stock, atr))
            lines.append('')

        # L2流向
        if engine.l2_flow:
            lines.append('### L2大单流向')
            lines.append('')
            lines.append('| 股票 | 大买 | 大卖 | 净流 | 主买比 | OIR |')
            lines.append('|------|------|------|------|--------|-----|')
            for stock, flow in engine.l2_flow.items():
                lines.append('| {} | {:.0f} | {:.0f} | {:.0f} | {:.1f}% | {:.3f} |'.format(
                    stock,
                    flow.get('big_buy', 0),
                    flow.get('big_sell', 0),
                    flow.get('net_flow', 0),
                    flow.get('active_ratio', 0.5) * 100,
                    flow.get('oir', 0)))
            lines.append('')
    else:
        lines.append('*引擎未启用*')
        lines.append('')

    # ── 9. 完整配置快照 ──
    lines.append('## 9. 策略预算')
    lines.append('')
    if hasattr(g, 'strategy_budget'):
        lines.append('```')
        for k, v in g.strategy_budget.items():
            lines.append('{}: {}'.format(k, v))
        lines.append('```')
    lines.append('')

    # ── 写入MD文件 ──
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    log.info("[v9.0.25] 每日报告已生成: {}".format(report_path))

    # ── 写入CSV盈亏记录 ──
    try:
        import csv
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '每日盈亏记录.csv')
        # 计算日收益(需要昨日净值)
        nav_history = g.bt.get('nav_history', [])
        if len(nav_history) >= 2:
            daily_return = (nav_history[-1] / nav_history[-2] - 1) * 100
        else:
            daily_return = total_return
        daily_pnl = total_value - (total_value / (1 + daily_return / 100)) if daily_return != 0 else 0

        buy_count = g.diag.get('A_buys_orders', 0)
        sell_count = g.diag.get('A_sell_all', 0) + g.diag.get('A_sell_half', 0)
        stop_loss_count = g.diag.get('stop_loss_triggered', 0)
        take_profit_count = g.diag.get('trailing_stop_triggered', 0)
        pos_count = len(positions)
        regime = g.market_regime
        note = ''
        if g.dragon_mode:
            note = 'Dragon激活'
        if g.diag.get('intraday_panic', 0):
            note = (note + '+' if note else '') + 'Panic'

        file_exists = os.path.exists(csv_path)
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['日期', '总资产', '日收益', '日收益率', '累计收益率',
                                 '持仓数', '买入', '卖出', '止损', '止盈', '最大回撤', 'regime', '备注'])
            writer.writerow([
                today_str,
                '{:.2f}'.format(total_value),
                '{:.2f}'.format(daily_pnl),
                '{:+.2f}%'.format(daily_return),
                '{:+.2f}%'.format(total_return),
                pos_count,
                buy_count,
                sell_count,
                stop_loss_count,
                take_profit_count,
                '{:.2f}%'.format(current_dd * 100),
                regime,
                note,
            ])
        log.info("[v9.0.25] 盈亏记录已追加: {}".format(csv_path))
    except Exception as e:
        log.warning("CSV盈亏记录写入失败(不影响策略): {}".format(e))

def _after_market_close_impl(context):
    if g.bt['start_cash']:
        nav = context.portfolio.total_value / g.bt['start_cash']
        g.bt['trade_days'] += 1
        g.bt['nav_history'].append(nav)

        win_rate = g.bt['wins'] / g.bt['closed_trades'] if g.bt['closed_trades'] > 0 else 0.0
        avg_win  = g.bt['win_ret_sum'] / g.bt['wins']   if g.bt['wins']   > 0 else 0.0
        avg_loss = g.bt['loss_ret_sum'] / g.bt['losses'] if g.bt['losses'] > 0 else 0.0

        log.info(
            "持仓数={} 净值={:.4f} 回撤={:.2f}% "
            "胜率={:.1f}% 盈亏比={:.2f} 总交易={}".format(
                len(context.portfolio.positions),
                nav,
                g.bt['current_dd'] * 100,
                win_rate * 100,
                abs(avg_win / avg_loss) if avg_loss != 0 else 0.0,
                g.bt['closed_trades']
            )
        )

    log.info(
        "DIAG|exp={}|regime={}|micro={}|trend={}|"
        "A_flat={}|A_pause={}|A_cooldown={}|A_rearm={}|A_grace={}|"
        "A_dragon={}|"
        "dragon={}|pool={}|score={:.3f}|ema={:.3f}|"
        "crowding_confirm={}|crowding_raw={}|crowding_consec={}|crowding_cd={}|"
        "A_buys={}|A_sell={}|"
        "intraday_panic={}|pos_cap={}|unknown={}|pending_exit={}|"
        "dpm_exp={}|dpm_max={}|dpm_ratio={:.0f}%|dpm_Apft={:.1f}%|"
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
            g.diag.get('crowding_confirm_days', 0),
            g.diag.get('crowding_signal_raw', 0),
            g.diag.get('crowding_consecutive_days', 0),
            g.diag.get('crowding_cooldown_left', 0),
            g.diag.get('A_buys_orders', 0),
            g.diag.get('A_sell_all', 0),
            g.diag.get('intraday_panic', 0),
            g.diag.get('intraday_pos_cap', 0),
            g.diag.get('unknown_positions', 0),
            g.diag.get('pending_exit_positions', 0),
            g.diag.get('dpm_expanded', 0),
            g.diag.get('dpm_max_pos', 3),
            g.diag.get('dpm_max_ratio', 0.75) * 100,
            g.diag.get('dpm_A_avg_profit', 0.0) * 100,
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
    exit_date = meta.get('last_exit_date')
    entry_type = meta.get('entry_type', '')
    strategy = meta.get('strategy', '')
    if exit_date is not None:
        if entry_type == 'dragon_follow':
            g.cooldown[stock] = (exit_date, 'dragon')
        else:
            g.cooldown[stock] = (exit_date, 'normal')
    ret_snapshot = meta.get('pending_exit_ret_snapshot')
    if ret_snapshot is not None:
        record_closed_trade(ret_snapshot)

        # [OPT-1] Dragon 连续亏损断路器追踪
        if entry_type == 'dragon_follow' and strategy == 'A':
            if ret_snapshot < 0:
                g.dragon_consecutive_losses += 1
                g.dragon_loss_history.append(abs(ret_snapshot))
                cfg = g.cfg
                max_losses = cfg.get('dragon_circuit_breaker_max_consecutive_losses', 3)
                min_avg_loss = cfg.get('dragon_circuit_breaker_min_avg_loss', 0.05)

                # [改进2] 连续止损保护: 连亏N笔后降仓位
                reduce_after = cfg.get('dragon_loss_reduce_after', 3)
                if g.dragon_consecutive_losses >= reduce_after:
                    reduced_ratio = cfg.get('dragon_loss_reduced_pos_ratio', 0.15)
                    if not getattr(g, 'dragon_reduced_pos_active', False):
                        g.dragon_reduced_pos_active = True
                        log.info("⚠️【连亏保护】Dragon连亏{}笔，仓位降至{:.0f}%".format(
                            g.dragon_consecutive_losses, reduced_ratio * 100))

                # [改进2] 连续止损保护: 连亏N笔后暂停Dragon
                pause_after = cfg.get('dragon_loss_pause_after', 5)
                pause_days_new = cfg.get('dragon_loss_pause_days', 2)
                if (g.dragon_consecutive_losses >= pause_after
                        and g.dragon_circuit_breaker_pause_left == 0):
                    g.dragon_circuit_breaker_pause_left = pause_days_new
                    log.info("🛑【连亏暂停】Dragon连亏{}笔，暂停Dragon{}天".format(
                        g.dragon_consecutive_losses, pause_days_new))

                # 原有断路器逻辑(连亏3笔+平均亏>5%才触发)
                elif (cfg.get('dragon_circuit_breaker_enable', False)
                        and g.dragon_consecutive_losses >= max_losses
                        and g.dragon_circuit_breaker_pause_left == 0):
                    recent_losses = g.dragon_loss_history[-max_losses:]
                    avg_loss = sum(recent_losses) / len(recent_losses) if recent_losses else 0
                    if avg_loss >= min_avg_loss:
                        pause_days = cfg.get('dragon_circuit_breaker_pause_days', 1)
                        g.dragon_circuit_breaker_pause_left = pause_days
                        log.info("🔌【Dragon断路器】连续{}笔亏损(平均{:.1f}%)，暂停Dragon{}天".format(
                            g.dragon_consecutive_losses, avg_loss * 100, pause_days))
                    else:
                        log.info("🔌【Dragon连亏{}笔】平均亏{:.1f}%未达{:.0f}%门槛，继续".format(
                            g.dragon_consecutive_losses, avg_loss * 100, min_avg_loss * 100))
            else:
                # 盈利则重置连亏计数 + 恢复仓位
                g.dragon_consecutive_losses = 0
                g.dragon_loss_history = []
                if getattr(g, 'dragon_reduced_pos_active', False):
                    g.dragon_reduced_pos_active = False
                    log.info("✅【连亏恢复】Dragon盈利，仓位恢复正常")

        # [OPT-3] Bear Dragon 周频率计数
        if entry_type == 'dragon_follow' and strategy == 'A' and g.market_regime == 'bear':
            pass  # 计数在买入时做

def mark_pending_buy(stock, strategy, entry_type, stage, context):
    g.pending_buys[stock] = {
        'strategy': strategy,
        'entry_type': entry_type,
        'stage': stage,
        'create_date': context.current_dt.date()
    }

def submit_exit_order(stock, context, reason='', ret_snapshot=None):
    """[CQTO] 修复: 1.卖出前检查closeable 2.exit_order_id正确取值"""
    pos = context.portfolio.positions.get(stock)
    if pos and pos.closeable_amount <= 0:
        log.warning("submit_exit_order({}): closeable=0(T+1), 跳过 reason={}".format(stock, reason))
        return False

    od = order_target_value(stock, 0)
    if od is None:
        return False
    meta = g.positions_meta.setdefault(stock, {})
    meta['pending_exit'] = True
    meta['last_exit_date'] = context.current_dt.date()
    meta['last_exit_reason'] = reason
    meta['pending_exit_ret_snapshot'] = ret_snapshot
    # [CQTO修复] 兼容层返回int(order_id), 不是带.order_id属性的对象
    meta['exit_order_id'] = od if isinstance(od, int) else getattr(od, 'order_id', None)
    return True

def submit_partial_stage_change(stock, amount, next_stage, context, reason=''):
    # 安全检查: 聚宽要求可平仓≤100时必须一次性平仓
    pos = context.portfolio.positions.get(stock)
    if pos and pos.closeable_amount > 0:
        remaining = pos.closeable_amount - amount
        if remaining > 0 and remaining < 100:
            # 剩余不足100股，改为全部卖出
            amount = pos.closeable_amount
            log.info("⚠️ {} 分批卖出调整: 剩余{}股不足100，改为全卖{}股".format(
                stock, remaining, amount))
    od = order(stock, -amount)
    if od is None:
        return False
    meta = g.positions_meta.setdefault(stock, {})
    meta['pending_stage_change'] = next_stage
    meta['pending_stage_change_date'] = context.current_dt.date()
    meta['pending_stage_change_reason'] = reason
    meta['partial_order_id'] = od if isinstance(od, int) else getattr(od, 'order_id', None)
    return True

# --- Missing utility functions from v5.9.0 ---


def is_panic_scout_mode():
    return (
        g.diag.get('risk_panic_yesterday', 0) == 1
        and g.diag.get('panic_scout_mode', 0) == 1
        and g.panic_scout_enabled_today
    )


# =========================================================
# 持仓 Helper
# =========================================================

def get_open_slot_hold_count(context, strategy_name):
    return sum([
        1 for stock in context.portfolio.positions.keys()
        if g.positions_meta.get(stock, {}).get('strategy') == strategy_name
    ])

def get_global_slots_left(context):
    # [DPM] 使用动态仓位上限
    max_pos = g.dpm_current_max_positions if hasattr(g, 'dpm_current_max_positions') \
        else g.cfg.get('max_total_positions', 999)
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
    else:
        g.bt['losses'] += 1
        g.bt['loss_ret_sum'] += ret

def diag_add(key, val=1):
    g.diag[key] = g.diag.get(key, 0) + val
