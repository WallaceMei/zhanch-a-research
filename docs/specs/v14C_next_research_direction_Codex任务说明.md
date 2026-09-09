# v1.4.0C 下一阶段研究方向分析任务说明

## 0. 任务背景

当前项目目录：

```text
D:\Code\JQ\战车A
```

v1.4.0C 完整区间研究结果已解压到：

```text
D:\Code\JQ\战车A\role_rotation_result_bundle V140C
```

本次任务不是继续改策略，也不是继续跑回测，而是让 Codex / Antigravity / Claude Code **只读分析已有结果**，重新生成一份下一阶段研究路线图。

---

## 1. 硬性要求

```text
1. 只读分析，不修改任何策略文件。
2. 不修改 research_role_rotation_direct_sim_v1.py。
3. 不重新运行回测。
4. 不为了收益调参。
5. 不建议直接放宽买入条件。
6. 不建议直接扩大仓位。
7. 不建议直接进入主线。
8. 所有结论必须基于数据。
9. 不 git add。
10. 不 git commit。
11. 不联网。
```

本次目标是：

```text
基于 v1.4.0C 完整区间结果，重新做系统复盘，并给出下一轮研究方向和具体实验方案。
```

---

## 2. 需要读取的文件

请从以下目录读取：

```text
D:\Code\JQ\战车A\role_rotation_result_bundle V140C
```

重点读取：

```text
role_rotation_summary.csv
role_rotation_daily_nav.csv
role_rotation_trades.csv
role_rotation_positions.csv
role_rotation_decisions.csv
role_rotation_diagnostics.csv
role_rotation_overfit_check.csv
role_rotation_sensitivity.csv
role_rotation_cost_sensitivity.csv
role_rotation_promotion_attribution.csv
role_rotation_cap_check.csv
v14C_full_diagnosis_report.md
v14C_loss_bigmeat_summary.csv
v14C_fast_loss_samples.csv
v14C_big_meat_samples.csv
v14C_promotion_profit_summary.csv
v14C_overfit_final_check.csv
v14C_entry_feature_need_list.csv
```

---

## 3. 输出文件要求

请输出主报告：

```text
v14C_next_research_direction_report.md
```

请输出 Excel 汇总：

```text
v14C_next_research_direction_outputs.xlsx
```

同时输出必要 CSV：

```text
v14C_trade_attribution_summary.csv
v14C_stock_selection_diagnosis.csv
v14C_overfit_risk_review.csv
v14C_fast_loss_reduction_plan.csv
v14C_position_management_plan.csv
v14C_exit_mechanism_plan.csv
v14C_strategy_architecture_plan.csv
```

---

# v14C_next_research_direction_report.md 报告结构

报告必须覆盖以下 7 个部分：

```text
1. 交易归因
2. 选股
3. 防止过拟合
4. 提高胜率，减少小亏损
5. 仓位管理
6. 止盈止损退出机制
7. 策略的整体结构优化
```

---

## 4. 第一部分：交易归因

请基于以下文件做交易归因：

```text
role_rotation_trades.csv
role_rotation_decisions.csv
role_rotation_promotion_attribution.csv
```

必须回答：

```text
1. 总收益主要来自哪些交易类型：
   - core
   - satellite
   - promoted_core
   - weak_core_replaced

2. 亏损主要来自哪些交易类型。
3. 亏损主要集中在哪些 exit_reason。
4. 大肉主要集中在哪些 exit_reason。

5. 按 hold_days 分组：
   - ≤1 天
   - 2 天
   - 3 天
   - 4~5 天
   - 6~10 天
   - >10 天

6. 分析 fast_loss：
   - 持仓 1~5 天亏损退出的笔数
   - 总亏损
   - 平均亏损
   - 占总亏损比例

7. 分析 big_meat / super_meat：
   - 收益 >10%
   - 收益 >20%
   - 分别来自 core / satellite / promoted_core 的比例

8. 判断当前策略到底是：
   - 胜率驱动
   - 盈亏比驱动
   - 少数大肉驱动
   - 仓位利用驱动
```

---

## 5. 第二部分：选股

请基于已有输出字段分析选股是否还有提高空间。

必须回答：

```text
1. signal_score 是否能有效区分盈利交易和亏损交易。
2. fast_loss 和 big_meat 在已有字段上是否有明显差异。
3. 哪些字段目前缺失，导致无法进一步判断选股质量。
4. 根据 v14C_entry_feature_need_list.csv，列出下一版必须补采集的 entry features。
```

重点关注下一版是否需要补采集：

```text
entry_open_ratio
entry_day_ret
entry_close_to_high
entry_volume_ratio
entry_auc_ratio
entry_ma5_distance
entry_ma10_distance
entry_turnover
entry_rank
entry_score
sector_strength_rank
breadth_up_ratio
market_state
market_10d_ret
```

请提出下一阶段“选股研究方向”，但不要直接建议调低或调高阈值。

### 5.1 可研究方向

```text
1. 结构质量过滤
2. 市场环境过滤
3. 板块强度过滤
4. 买入后首日承接确认
5. 大肉票特征归因
```

### 5.2 暂不建议方向

```text
1. 简单提高 DRAGON_MIN_SCORE
2. 简单放宽 deep_water 条件
3. 为了增加交易而降低筛选条件
4. 根据单一区间最优结果调参
```

---

## 6. 第三部分：防止过拟合

请读取：

```text
role_rotation_overfit_check.csv
role_rotation_sensitivity.csv
role_rotation_cost_sensitivity.csv
v14C_overfit_final_check.csv
```

必须回答：

```text
1. 参数扰动是否稳定。
2. 哪些扰动参数最敏感。
3. 成本提高 1.5x / 2x / 滑点加倍后是否仍有效。
4. top1 / top3 / top5 盈利贡献是否过度集中。
5. 收益是否主要来自少数交易。
6. train / validation / oos 是否一致。
7. 当前是否存在明显过拟合风险。
8. 哪些方案不能直接进入主线。
```

### 6.1 下一阶段防过拟合框架

请在报告中给出框架：

```text
1. 不用单一区间调参
2. 不追求最高收益
3. 检查参数邻域稳定性
4. 检查交易样本数
5. 检查收益贡献集中度
6. 检查成本敏感性
7. 检查 oos 表现
8. 检查逻辑合理性
```

---

## 7. 第四部分：提高胜率，减少小亏损

请重点分析 fast_loss。

必须回答：

```text
1. 小亏损主要发生在买入后第几天。
2. 小亏损主要来自 core 还是 satellite。
3. 小亏损的 exit_reason 分布。
4. 小亏损是否集中在某些月份、市场状态或股票。
5. 当前止损是否太晚，还是买入质量不足。
6. 是否适合做“首买小仓 + 次日确认加仓”。
```

### 7.1 研究实验 A：首买小仓 + 次日确认加仓

实验描述：

```text
Top1 首买 20%~25%
Top2 首买 15%~20%
次日确认仍强再补到原目标仓位
```

研究目标：

```text
减少买错时的首日伤害。
```

注意：

```text
只作为研究实验，不直接作为最终参数。
```

### 7.2 研究实验 B：快速失效退出

实验描述：

```text
买入后 1~2 天内，如果跌破 MA5 或浮亏超过指定阈值，提前退出。
```

研究目标：

```text
减少 fast_loss 扩大。
```

注意：

```text
不要用单一区间结果寻找最优止损参数。
```

### 7.3 研究实验 C：弱市降频

实验描述：

```text
bear 或弱 breadth 状态下限制买入。
禁止 satellite / promotion 或降低总仓。
```

研究目标：

```text
减少错误市场环境中的交易。
```

---

## 8. 第五部分：仓位管理

请读取：

```text
role_rotation_cap_check.csv
role_rotation_daily_nav.csv
```

必须回答：

```text
1. 是否存在买入时 cap 超限。
2. 超限是买入时发生，还是持仓浮盈后自然发生。
3. core / satellite / promoted_core 的实际仓位是否符合设计。
4. 当前平均仓位和最大仓位是否合理。
5. 是否存在高收益但靠更高仓位暴露实现的问题。
```

### 8.1 下一阶段仓位管理方案

请提出：

```text
1. 修复买入时 cap 严格约束：
   - pre_buy_total_ratio
   - post_buy_total_ratio
   - cap_limit
   - cap_exceeded_on_buy

2. 首买分层：
   - 初始仓位小一些
   - 确认后再加仓

3. 市场状态动态仓位：
   - bull：允许 75%~90%
   - neutral：维持 60%~75%
   - bear：降到 35%~50%

4. 卫星仓控制：
   - 不扩大卫星数量
   - 不直接满仓
   - 先研究卫星质量而不是数量
```

---

## 9. 第六部分：止盈止损退出机制

请基于：

```text
role_rotation_trades.csv
exit_reason
```

分析当前退出机制。

必须回答：

```text
1. 哪些 exit_reason 贡献最大盈利。
2. 哪些 exit_reason 贡献最大亏损。
3. core_drawdown_exit 是否有效。
4. satellite_max_hold 是否有效。
5. stop_loss 是否太晚。
6. below_ma5_loss 是否可以提前触发。
7. 晋级后退出是否合理。
```

### 9.1 下一阶段退出机制研究方案

请提出：

```text
1. fast_loss 提前退出：
   - 买入后 1~2 天内失败则退出

2. 盈利保护：
   - 浮盈超过一定水平后，启动回撤保护

3. 晋级后保护：
   - 晋级后如果 1~2 天内不继续走强，则退出或降回卫星

4. 大肉延长持有：
   - 对强趋势票不要过早止盈

5. 不建议：
   - 简单扩大止损
   - 简单降低止损
   - 用单一区间最优参数拟合退出
```

---

## 10. 第七部分：策略整体结构优化

请重新审视当前结构：

```text
baseline_core_only
baseline_core_satellite
role_rotation_observer
```

必须回答：

```text
1. 当前 role_rotation 是否真的优于 baseline。
2. role_rotation 的收益来自哪里。
3. role_rotation 的风险在哪里。
4. 晋级机制是否应该保留。
5. 卫星仓机制是否应该保留。
6. 是否应该进入主线。
7. 是否应该进入策略观测版。
8. 是否应该继续作为研究分支。
```

---

## 11. 下一阶段版本规划

请在报告中提出明确版本规划。

### 11.1 v1.4.0C-P1：交易归因与 entry feature 补采集版

目标：

```text
1. 采集买入当日结构字段。
2. 分析 fast_loss 和 big_meat 区别。
3. 不改变交易逻辑。
```

### 11.2 v1.4.0C-P2：首买小仓 + 次日确认加仓实验版

目标：

```text
1. 减少首日 / 前 3 日亏损。
2. 不追求总收益最高。
```

### 11.3 v1.4.0C-P3：弱市降频 + 动态仓位实验版

目标：

```text
1. 降低 bear / 弱市场下的交易频率。
2. 控制回撤。
```

### 11.4 v1.4.0C-P4：晋级后保护机制实验版

目标：

```text
1. 验证卫星晋级后是否继续持有有价值。
2. 减少晋级后回吐。
```

### 11.5 v1.4.0C-P5：综合观测版

目标：

```text
1. 只打日志，不实盘执行。
2. 验证上述机制在完整回测中是否稳定。
```

---

## 12. 最终结论必须明确回答

报告最后必须明确回答：

```text
1. 当前 v1.4.0C 是否建议进主线：是 / 否
2. 当前 v1.4.0C 是否建议进真实执行版：是 / 否
3. 当前 v1.4.0C 是否建议继续研究：是 / 否
4. 下一步最优先做什么
5. 哪些方向暂时不要做
6. 哪些方向有最大提升空间
```

---

## 13. 禁止输出的错误倾向

报告中不要出现以下结论：

```text
1. 直接放宽 deep_water 条件。
2. 直接提高仓位到满仓。
3. 直接降低止损阈值以提高收益。
4. 直接提高 DRAGON_MIN_SCORE 作为唯一选股优化。
5. 只看最终收益，不看过拟合风险。
6. 只看一个区间，不看 train / validation / oos。
7. 因为收益高就建议进入主线。
```

---

## 14. 本次任务本质

```text
这不是策略开发任务。
这是 v1.4.0C 结果复盘、交易归因、风险识别、下一阶段研究方案制定任务。
```

请严格基于已有输出文件给出结论和下一步方案。
