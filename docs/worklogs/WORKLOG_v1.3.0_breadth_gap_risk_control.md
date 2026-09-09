# v1.3.0-breadth-gap-risk-control

## 背景

v1.2.1A 研究环境扫描显示：

`proxy_bull_up_gap_m2`：昨日 bull 且 trend=up，今日低开 <= -2%。

- better_than_actual_count = 17
- worse_than_actual_count = 1

该结果说明，普涨后低开可能是抱团票退潮信号。

## 本版目标

只测试普涨后低开风控，不叠加其他止盈、止损或加仓实验。

## 核心规则

- 昨日 `prev_regime == bull` 或 `prev_reg2 == bull`
- 且 `prev_trend == up`
- 今日持仓票 `open_gap <= -2%`
- 且 `max_floating_pnl >= 10%`
- 如果取不到 `max_floating_pnl`，使用当前 `pnl >= 5%`

## 动作

- `pnl > 0` 且 `ma5_distance >= 0`：卖半仓，原因 `breadth_gap_risk_reduce`
- `pnl > 0` 且 `ma5_distance < 0`：清仓，原因 `breadth_gap_risk_exit`
- `pnl <= 0`：清仓，原因 `breadth_gap_risk_exit_loss`

半仓复用 `execute_sell_signal -> submit_partial_stage_change`，清仓复用
`execute_sell_signal -> submit_exit_order`。成交确认、实际成交数量和
`TRADE_CLOSE` 继续使用 v1.1.3 原账本流程。

## 新增日志

- `BREADTH_GAP_RISK_CHECK`
- `BREADTH_GAP_RISK_SELL`
- `BREADTH_GAP_RISK_ERROR`

`TRADE_CLOSE` 仅增加 `exit_reason` 和 `breadth_gap_risk_reason` 字段，
不改变收益计算。

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
- partial sell 实际成交数量修复
- set_order_cost

## 验证重点

- 最大回撤是否从 23% 附近明显下降
- 总收益是否没有明显牺牲
- 触发 `BREADTH_GAP_RISK_SELL` 的股票及动作是否符合条件
- 是否没有 `TRADE_ACCOUNTING_WARN`
- 是否没有 `accounting_error=1`
- 半仓成交数量是否继续以真实成交或持仓变化确认

## 建议回测

优先区间：2025-07-01 至 2026-06-14。

长区间通过后再跑：

- 2026-01-01 至 2026-06-14
- 2026-03-01 至 2026-06-14
