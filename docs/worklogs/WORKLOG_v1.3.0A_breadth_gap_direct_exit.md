# v1.3.0A-breadth-gap-direct-exit

## 背景

本版本基于 `v1.3.0-breadth-gap-risk-control` 独立复制，只验证“普涨低开直接清仓”。

`breadth_gap_full_vs_half_summary.csv` 的研究结果：

- sample_count = 13
- full_better_count = 12
- half_better_count = 1
- avg_full_exit_ret = 19.16
- avg_half_hold_ret = 16.7281
- avg_full_minus_half = 2.4319
- sum_full_minus_half = 31.615

市场条件对比显示，收紧为主市场 `prev_regime == bull` 后：

- sample_count = 12
- full_better_count = 12
- half_better_count = 0
- full_better_rate = 100%
- avg_full_minus_half = 3.2708
- sum_full_minus_half = 39.25

`prev_reg2 == bull` 单独触发的唯一案例中，半仓持有优于直接清仓，因此
`prev_reg2` 在本版本中只记录日志，不参与独立触发。

## 本版目标

将 v1.3.0 的“MA5 上方先卖半仓”改成满足条件后直接清仓，避免后续依赖
`dragon_half_protect` 接力退出。

## 核心规则

- `prev_regime == bull`
- `prev_trend == up`
- `open_gap <= -2%`
- `max_floating_pnl >= 10%`
- 如果取不到 `max_floating_pnl`，使用当前 `pnl >= 5%`

满足以上条件后：

- `action = exit`
- `reason = breadth_gap_risk_exit_direct`
- `sell_ratio = 1.00`

MA5 和 `ma5_distance` 继续记录在日志中，但不再决定半仓或清仓动作。

## 清仓与账本

风控信号复用：

`execute_sell_signal -> submit_exit_order -> finalize_exited_position`

本版本不调用 partial sell，不修改 stage 为 half，不新增账本，也不修改
v1.1.3 partial sell 实际成交数量修复。

## 新增或保留日志

- `BREADTH_GAP_RISK_CHECK`
- `BREADTH_GAP_RISK_SELL`
- `BREADTH_GAP_RISK_ERROR`

`BREADTH_GAP_RISK_SELL` 成功提交时应输出：

- `action=exit`
- `reason=breadth_gap_risk_exit_direct`
- `sell_ratio=1.00`
- `stage_after_if_known=exit`

## 不修改

- 买入条件
- Dragon score
- deep_water
- prefilter 权重
- Top250
- get_call_auction
- 原止损
- 原止盈
- 原加仓
- 仓位参数
- 账本逻辑
- TRADE_CLOSE 计算
- set_order_cost

## 建议回测

第一阶段：2026-01-01 至 2026-06-14。

第二阶段：2025-07-01 至 2026-06-14。

重点对比 v1.3.0 与 v1.3.0A：

- 最终收益
- 最大回撤
- 胜率
- 盈亏比
- `BREADTH_GAP_RISK_SELL` 触发次数
- 是否出现 `TRADE_ACCOUNTING_WARN`
- 是否出现 `accounting_error=1`
