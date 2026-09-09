# 战车A V1.1.0 对照组实验

## 五个实验组

- `A0_BASE`: 原始策略基线组，不覆盖任何参数。
- `A1_DPM_CONSERVE`: 收紧 DPM 总仓位、组合仓位上限和中性趋势扩仓条件。
- `A2_TRENDCORE_FILTER`: 只拦截 Dragon 的 `trend_core` 模板，要求 `regime=bull` 且 `trend=up`。
- `A3_DRAGON_RISK_FAST`: Dragon 连亏保护更快触发，并加入高开分层，3%-4% 半仓，超过 4% 跳过。
- `A4_COMBO`: 同时启用 A1、A2、A3 的组合方案。

## 聚宽里如何切换

在 `strategy_A_v1_1_0.py` 顶部 imports 后找到：

```python
EXPERIMENT_NAME = 'A0_BASE'
```

每次回测前把它改成需要跑的实验组名，例如：

```python
EXPERIMENT_NAME = 'A3_DRAGON_RISK_FAST'
```

## 推荐回测区间

`2026-03-30` 到 `2026-05-27`

聚宽成交模型、滑点、手续费、benchmark 保持策略原设置，不要为了实验改这些项。

## 日志文件命名

每组跑完后导出聚宽日志，建议保存为：

- `jq_A0_BASE.log`
- `jq_A1_DPM_CONSERVE.log`
- `jq_A2_TRENDCORE_FILTER.log`
- `jq_A3_DRAGON_RISK_FAST.log`
- `jq_A4_COMBO.log`

## 汇总日志

把 5 个日志文件放在本目录，然后运行：

```bash
python analyze_jq_experiment_logs.py jq_A0_BASE.log jq_A1_DPM_CONSERVE.log jq_A2_TRENDCORE_FILTER.log jq_A3_DRAGON_RISK_FAST.log jq_A4_COMBO.log
```

也可以直接运行，默认读取当前目录下所有 `jq_*.log`：

```bash
python analyze_jq_experiment_logs.py
```

输出文件：

```text
experiment_summary.csv
```

字段包含：

```text
exp,date,nav,drawdown,win_rate,profit_loss_ratio,total_trades,positions,A_buys,A_sell,regime,trend,pool,score
```

旧日志如果没有 `exp=` 字段，会填 `UNKNOWN`。

## 判断标准

- 最大回撤是否下降。
- 4 月亏损是否减少。
- 收益/回撤比是否提高。
- 交易次数是否过少。
- 是否过度依赖少数大肉票。
