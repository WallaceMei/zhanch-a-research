# DeepSeek + Claude Code 接手 v1.4.0B 后续工作的执行方案

## 0. 当前状态

Codex 额度不足，后续改由 DeepSeek + Claude Code 执行。

当前任务不是继续大改策略，而是完成：

```text
1. 验证 v1.4.0B 单卫星仓修复是否生效
2. 重新跑 v14B_fix 日志
3. 用日志分析脚本重新对比 v13A / v130A / v14A / v14B / v14B_fix
4. 判断 v14B_fix 是否值得继续优化
```

---

## 1. 当前关键文件

项目目录：

```text
D:\Code\JQ\战车A
```

日志目录：

```text
D:\Code\JQ\战车A\log
```

当前已有日志：

```text
jq_v13A_20260101_20260614.log.txt
jq_v130A_20260101_20260614.log.txt
jq_v14A_20260101_20260614.log.txt
jq_v140B_20260101_20260614.log.txt
jq_v121A_20250701_20260614.log.txt
```

当前应新增的修复后日志：

```text
jq_v140B_fix_20260101_20260614.log.txt
```

当前分析脚本：

```text
analyze_v14B_log_compare.py
```

当前策略实验文件：

```text
战车A龙头3_v1.4.0B_shadow_rotation_original_core.py
```

过拟合检测 notebook 目录：

```text
D:\Code\JQ\战车A\过拟合检测
```

---

## 2. 工作顺序

### 第一步：先在聚宽重新跑 v1.4.0B 修复版

回测区间：

```text
2026-01-01 至 2026-06-14
```

保存日志为：

```text
D:\Code\JQ\战车A\log\jq_v140B_fix_20260101_20260614.log.txt
```

重点检查日志中是否有：

```text
SHADOW_SLOT_GUARD
SHADOW_BUY_SUBMIT
SHADOW_BUY_SKIP|reason=satellite_slot_full
SHADOW_BUY_SKIP|reason=satellite_pending_buy
SHADOW_DAILY_SUMMARY
TRADE_ACCOUNTING_WARN
```

验收标准：

```text
SHADOW_DAILY_SUMMARY 里 satellite_count 最大值 <= 1
同一天 SHADOW_BUY_SUBMIT 最多 1 次
replace_count 始终为 0
不出现 SHADOW_REPLACE_EXECUTE
total_position_ratio 不超过 75%
不出现 TRADE_ACCOUNTING_WARN
```

---

## 3. 交给 Claude Code 的任务

### 任务目标

只读分析日志，不再改策略。

需要修改或新增的分析文件：

```text
analyze_v14B_log_compare.py
```

允许输出：

```text
v1.4.0B_fix_日志对比分析_过拟合初检报告.md
v1.4.0B_fix_log_compare_outputs.xlsx
```

如需要，也可以输出辅助 CSV：

```text
v14B_fix_version_summary.csv
v14B_fix_trade_attribution.csv
v14B_fix_shadow_summary.csv
v14B_fix_position_summary.csv
```

---

## 4. Claude Code 必须做的分析

### 4.1 版本对比

必须同时对比：

```text
v13A
v130A
v14A
v14B
v14B_fix
```

对应日志：

```text
jq_v13A_20260101_20260614.log.txt
jq_v130A_20260101_20260614.log.txt
jq_v14A_20260101_20260614.log.txt
jq_v140B_20260101_20260614.log.txt
jq_v140B_fix_20260101_20260614.log.txt
```

输出每个版本：

```text
final_nav
total_return_pct
max_drawdown_pct
closed_trades
win_rate_pct
payoff
core_realized_pnl
satellite_realized_pnl
satellite_trade_count
avg_total_position_ratio_pct
avg_core_position_ratio_pct
avg_satellite_position_ratio_pct
max_satellite_count
top_profit_share_pct
top3_profit_share_pct
accounting_warn_count
accounting_error_count
```

---

### 4.2 v14B_fix 单卫星仓约束检查

重点检查：

```text
max_satellite_count 是否 <= 1
同一天 SHADOW_BUY_SUBMIT 是否最多 1 次
replace_count 是否始终为 0
是否出现 SHADOW_REPLACE_EXECUTE
total_position_ratio 是否超过 75%
是否出现 TRADE_ACCOUNTING_WARN
是否出现 accounting_error=1
```

如果发现异常，必须在报告中写清楚：

```text
异常日期
异常事件
异常原因推测
对应日志样例
```

---

### 4.3 卫星仓归因

针对 v14B_fix 统计：

```text
卫星仓交易数
卫星仓胜率
卫星仓平均收益
卫星仓中位收益
卫星仓最大单笔盈利
卫星仓最大单笔亏损
卫星仓 realized_pnl 合计
卫星仓 top1 盈利贡献
卫星仓 top3 盈利贡献
```

判断：

```text
卫星仓是否正贡献
是否仍然靠少数大赚支撑
修复单仓约束后，卫星仓收益是否明显下降
```

---

### 4.4 核心仓归因

针对 v14B_fix 统计：

```text
核心仓交易数
核心仓胜率
核心仓平均收益
核心仓中位收益
核心仓 realized_pnl 合计
核心仓最大亏损
核心仓最大盈利
```

判断：

```text
核心仓是否恢复到接近 v13A / v130A
v14B_fix 的差距来自核心仓还是卫星仓
```

---

### 4.5 初步过拟合检测

参考：

```text
D:\Code\JQ\战车A\过拟合检测
```

只读 notebook，不修改 notebook。

需要把其中方法离线化，用日志中的 `DAILY_SUMMARY` 和 `TRADE_CLOSE` 做：

```text
净值曲线稳定性
20日 / 40日滚动收益
20日 / 40日滚动夏普 proxy
月度收益稳定性
单笔贡献集中度
成本敏感性
样本数量风险
Bootstrap / 块自助法思路
样本外风险提示
参数过拟合风险说明
```

注意：

```text
如果 notebook 依赖 get_backtest 或在线回测 ID，本地无法运行时，不要报错。
只参考方法，把它改造成日志离线检测。
```

---

## 5. 报告必须给出的最终判断

报告最后必须明确：

```text
v14B_fix 是否修复单卫星仓 bug：是 / 否 / 不确定
v14B_fix 是否优于 v14B 未修复版：是 / 否 / 不确定
v14B_fix 是否优于 v14A：是 / 否 / 不确定
v14B_fix 是否接近或超过 v13A / v130A：是 / 否 / 不确定
卫星仓修复后是否仍为正贡献：是 / 否 / 样本不足
卫星仓收益是否仍高度集中：是 / 否 / 样本不足
过拟合风险：低 / 中 / 高
是否建议继续优化 v14B_fix：是 / 否
是否建议进入主线：否
```

主线规则：

```text
v14B_fix 仍然只是控制变量实验版，不允许直接进入主线。
只有当它满足以下条件，才允许讨论下一版：
1. 收益接近或超过原策略
2. 回撤不扩大
3. 卫星仓独立正贡献
4. 单卫星仓约束生效
5. 没有账本异常
6. 过拟合风险下降
```

---

## 6. 硬性边界

Claude Code 必须遵守：

```text
只读日志
不修改原策略文件
不修改 v1.4.0A
不修改 v1.4.0B 策略文件，除非用户明确要求
不删除任何日志
不覆盖原日志
不 git add
不 git commit
不联网
```

如果需要修改分析脚本，只允许修改：

```text
analyze_v14B_log_compare.py
```

---

## 7. 建议输出文件

```text
v1.4.0B_fix_日志对比分析_过拟合初检报告.md
v1.4.0B_fix_log_compare_outputs.xlsx
```

Excel sheet 建议：

```text
1_version_summary
2_trade_attribution
3_shadow_summary
4_position_summary
5_constraint_check
6_monthly_summary
7_rolling_stability
8_contribution_concentration
9_cost_sensitivity
10_overfit_flags
11_warnings
```

如果 Excel 写入失败：

```text
不要让任务失败。
继续输出 Markdown 和 CSV。
报告中说明 Excel 失败原因。
```
