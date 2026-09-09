# 战车A v1.4.0B shadow rotation original core 工作记录

## 当前实验文件

* 实验策略文件：战车A龙头3_v1.4.0B_shadow_rotation_original_core.py
* 来源实验文件：战车A龙头3_v1.4.0A_shadow_rotation_fullB.py
* 当前版本：v1.4.0B-shadow-rotation-original-core
* 修改类型：独立控制变量实验版

## 版本定位

v1.4.0B 是“原核心策略 + 小卫星仓影子轮动”实验版。

本版目的不是追求满仓复利，而是验证：

1. 恢复原核心仓参数后，核心策略是否回到原风险暴露。
2. 单个 Rule D deep_water 卫星仓是否能给原策略增厚收益。
3. 卫星仓是否会带来明显回撤、超仓、重复持仓或账本异常。

## 相比 v1.4.0A 的回滚

核心仓参数恢复为：

* Top1：35%
* Top2：25%
* 核心初始上限：60%
* 总仓位上限：75%
* 最大持仓数：3

不再使用 v1.4.0A 的：

* Top1 35% + Top2 35%
* 核心仓 70%
* 卫星仓 15% x 2
* 总仓 100%
* 卫星仓替换逻辑

## 卫星仓结构

本版只启用 1 个卫星仓：

* shadow_satellite_slots = 1
* shadow_satellite_slot_ratio = 0.15
* max_total_position_ratio = 0.75

已有卫星仓时，不做替换，只记录：

* SHADOW_BUY_SKIP|reason=satellite_slot_full

## WATCH_POOL

保留 v1.4.0A 的 WATCH_POOL 框架，但只跟踪 deep_water 候选。

字段包括：

* stock
* name
* signal_date
* signal_price
* signal_rank
* signal_score
* signal_source
* signal_entry_type
* expire_days = 3
* watch_reason

## Rule D deep_water 确认

确认时间：14:45。

确认条件：

* signal_date 后 1-3 个交易日
* ret_from_signal >= 5%
* day_ret >= 5%
* 1.0 <= volume_ratio_vs_prev <= 2.0
* ma5_distance <= 10%
* close_to_day_high >= 0.97
* signal_entry_type == deep_water
* 非涨停
* 非停牌 / 非 ST
* 未持仓
* 未触发原策略暂停买入状态

## 账本安全

卫星仓买入复用：

* order_value
* mark_pending_buy
* sync_position_meta_with_real_positions

卫星仓退出复用：

* submit_exit_order
* finalize_exited_position
* TRADE_CLOSE
* accounting_error 保护

不新写账本，不绕开 v1.1.3 partial sell 实际成交数量账本修复。

## 新增和保留日志

* WATCH_POOL_ADD
* WATCH_POOL_EXPIRE
* WATCH_POOL_REMOVE
* SHADOW_CONFIRM_CHECK
* SHADOW_CONFIRM_PASS
* SHADOW_CONFIRM_SKIP
* SHADOW_BUY_SUBMIT
* SHADOW_BUY_CONFIRMED
* SHADOW_BUY_SKIP
* SHADOW_EXIT_SIGNAL
* SHADOW_EXIT_SUBMIT
* SHADOW_EXIT_CONFIRMED
* SHADOW_DAILY_SUMMARY

## 待验证事项

1. 核心仓是否恢复到原策略风险暴露。
2. 卫星仓是否只开 1 个。
3. 总仓位是否不超过 75%。
4. 已有卫星仓时是否只输出 SHADOW_BUY_SKIP，不做替换。
5. 是否没有 TRADE_ACCOUNTING_WARN。
6. 是否没有 accounting_error=1。
7. 卫星仓独立收益是否为正。
8. 卫星仓最大单笔亏损是否可控。

## 建议回测区间

先跑：

* 2026-01-01 至 2026-06-14

再跑：

* 2025-07-01 至 2026-06-14

对比对象：

* 原策略 / v1.3.0A
* v1.4.0A fullB
* v1.4.0B original core + single satellite
