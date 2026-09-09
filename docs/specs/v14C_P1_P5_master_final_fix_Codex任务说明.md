# v14C P1~P5 Master 脚本补强任务说明

## 0. 任务背景

当前项目目录：

```text
D:\Code\JQ\战车A
```

当前文件：

```text
research_v14C_P1_to_P5_master.py
```

你已经完成 P2~P5 独立路径重放的主要修复。现在先不要跑聚宽小区间，也不要跑完整区间。请先把剩余问题一次性补齐，避免后续 P1 特征缺口、P2 明细不完整、P3 cap 验收字段不足、P4 晋级状态不完整。

---

## 1. 硬性要求

只允许修改：

```text
research_v14C_P1_to_P5_master.py
```

禁止修改：

```text
战车A龙头3.py
战车A龙头3.txt
research_role_rotation_direct_sim_v1.py
任何主策略文件
```

禁止执行：

```text
git add
git commit
联网
完整区间运行
```

修复后只做：

```text
python -m py_compile research_v14C_P1_to_P5_master.py
```

可以做 `local_analysis` 结构验收，但不要跑完整区间。

---

# 2. P1：补完整 entry features

当前 `ENTRY_FEATURES` 包含：

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

请补齐 `enrich_entry_features_from_jq()`。

原则：

```text
1. 能真实计算的，真实计算。
2. 不能稳定计算的，输出 NaN。
3. 每个缺失字段必须有 available 标记和 missing_reason。
4. 不允许用猜测值填充。
5. 不允许静默缺失。
```

## 2.1 entry_auc_ratio

优先用 `get_call_auction` 计算：

```text
entry_auc_ratio = auction_volume / previous_day_volume
```

输出字段：

```text
auction_volume
auction_money
auction_price
entry_auc_ratio
entry_auc_available
entry_auc_missing_reason
```

如果 `get_call_auction` 对部分日期/股票失败，不要中断，记录 missing_reason。

---

## 2.2 entry_turnover

优先尝试从聚宽可用字段或估值数据中获取 `turnover_ratio`。

如果取不到：

```text
entry_turnover = NaN
entry_turnover_available = 0
entry_turnover_missing_reason = "turnover_data_unavailable"
```

---

## 2.3 sector_strength_rank

如果当前脚本没有行业 / 板块分类能力，先保守输出：

```text
sector_strength_rank = NaN
sector_strength_available = 0
sector_strength_missing_reason = "sector_classification_not_available"
```

不要伪造板块强度。

如果可以通过聚宽行业分类 API 获取行业，则按买入日前 5 日行业内平均涨幅排名，并输出：

```text
sector_code
sector_name
sector_5d_ret
sector_strength_rank
sector_strength_available
```

---

## 2.4 breadth_up_ratio

优先级：

```text
1. 如果 role_rotation_diagnostics.csv 中已有 breadth_up_ratio / market breadth 字段，直接 merge。
2. 如果没有，用全市场股票当日 close > pre_close 的比例估算。
3. 如果计算成本太高，只用原 direct sim 股票池 / 候选池估算，并明确标记 breadth_source。
```

输出字段：

```text
breadth_up_ratio
breadth_source
breadth_available
breadth_missing_reason
```

---

## 2.5 market_10d_ret

用指数计算，优先使用：

```text
000001.XSHG
```

输出字段：

```text
market_index_code
market_10d_ret
market_10d_ret_available
market_10d_ret_missing_reason
```

---

## 2.6 entry_rank

如果原 trades / decisions 中有以下字段，优先 merge：

```text
rank
prefilter_rank
entry_rank
score_rank
```

如果没有：

```text
entry_rank = NaN
entry_rank_available = 0
entry_rank_missing_reason = "entry_rank_not_in_source_outputs"
```

---

## 2.7 entry_score

优先使用：

```text
signal_score
```

输出：

```text
entry_score
entry_score_source = "signal_score"
```

---

# 3. P1 输出增强

必须输出：

```text
p1_jq_entry_features.csv
p1_jq_entry_feature_diagnostics.csv
p1_entry_feature_missing_summary.csv
p1_fast_loss_vs_big_meat_features.csv
p1_entry_feature_trade_log.csv
```

`p1_entry_feature_missing_summary.csv` 至少包含：

```text
feature
available_count
missing_count
available_rate
missing_reason_top1
must_fix_before_next_stage
```

报告中必须明确：

```text
1. 哪些字段已真实采集。
2. 哪些字段是 NaN 但有明确 missing_reason。
3. 哪些字段必须下一轮通过 direct sim 增强。
4. fast_loss 和 big_meat 是否已经具备可比特征数据。
```

---

# 4. P2：修复 confirm_add 明细完整性

当前 `confirm_add` 已经实现首买 65% 和后续确认加仓，但必须保证所有 `confirm_pending` 仓位都有明细记录。

`p2_confirm_add_position_detail.csv` 必须覆盖：

```text
confirm_add_ok
confirm_add_blocked
confirm_add_no_capacity
confirm_add_policy_exit_before_check
confirm_add_baseline_exit_before_check
confirm_add_missing_price
```

如果某个仓位在确认前被 policy exit 或 baseline exit 卖出，也要记录一条 detail，不能消失。

必须包含字段：

```text
variant
stock
name
entry_date
check_date
entry_price
check_price
ma5
pre_close
pnl_pct
target_value
current_cost
add_value
ma5_ok
loss_ok
close_ok
reason
final_action
```

---

# 5. P3：补充 cap 验收字段

`p3_decisions.csv` 中每一笔 `BUY / BUY_SKIP` 必须包含：

```text
pre_buy_total_ratio
target_order_ratio
available_ratio
post_total_ratio
post_single_ratio
cap_limit
original_value
actual_value
cap_trimmed
skipped_due_to_no_capacity
market_state
```

`p3_cap_and_regime_summary.csv` 必须包含：

```text
variant
segment
total_return
max_drawdown
trade_count
cap_exceeded_on_buy
skipped_due_to_no_capacity
cap_trimmed_count
avg_actual_value_ratio
max_post_total_ratio
max_total_ratio
bear_buy_count
neutral_buy_count
bull_buy_count
```

---

# 6. P4：补充晋级状态完整性

请确保 P4 的三种模式都能从 `role_rotation_decisions.csv` 中读取：

```text
ROLE_PROMOTION_EXECUTE
```

P4 输出中必须包含：

```text
promotion_date
promotion_state
promoted_from_role
post_promotion_entry_price
post_promotion_pnl
promotion_action
```

## 6.1 p4_no_promotion

严格语义：

```text
1. satellite 可以买入。
2. 到 promotion 事件时，不晋级。
3. 执行止盈 / 退出。
4. decision = PROMOTION_BLOCK_EXIT。
```

## 6.2 p4_label_only_no_add

严格语义：

```text
1. satellite 可以买入。
2. 到 promotion 事件时，只改标签。
3. 不加仓。
4. 不替换核心。
5. decision = PROMOTION_LABEL_ONLY。
```

## 6.3 p4_promotion_protect

严格语义：

```text
1. 到 promotion 事件时进入 promotion_state。
2. 晋级后 post_promotion_pnl < 0 退出。
3. 晋级后 2 天仍不强，post_promotion_pnl < 3% 退出。
4. decision = PROMOTION_STATE_ENTER / POLICY_EXIT。
```

---

# 7. P5：补充综合观测版组件验收

P5 summary 中必须明确：

```text
used_p2_confirm_add
used_p2_quick_fail_exit
used_p3_cap_fixed
used_p3_regime_position
used_p4_promotion_protect
```

新增输出：

```text
p5_component_effect_summary.csv
```

该表至少包含：

```text
component
enabled
effect_target
expected_effect
actual_fast_loss_change
actual_drawdown_change
actual_return_change
warning
```

---

# 8. Manifest 和报告增强

manifest 必须新增：

```text
p1_all_required_features_present
p1_missing_required_features
p1_missing_feature_count
p2_confirm_add_detail_complete
p3_cap_detail_complete
p4_promotion_state_complete
p5_component_summary_complete
```

如果 P1 字段仍有缺失，允许继续跑，但 manifest 必须明确：

```text
p1_all_required_features_present = false
```

报告中必须明确：

```text
1. P1 哪些字段缺失。
2. 缺失是否影响选股归因。
3. P2~P5 是否可以作为路径实验。
4. P2~P5 是否仍然只是基于 v1.4.0C 买入事件的反事实路径重放。
5. 当前仍不能作为主线和真实执行版。
```

---

# 9. 验收要求

修复后执行：

```text
python -m py_compile research_v14C_P1_to_P5_master.py
```

可以执行 local_analysis 结构验收，但不要跑完整区间。

完成后汇报：

```text
1. P1 新增了哪些字段。
2. 哪些字段仍然只能 missing_reason。
3. p1_entry_feature_missing_summary.csv 是否生成。
4. p2_confirm_add_position_detail.csv 是否覆盖 blocked / no_capacity / exit_before_check。
5. p3 cap 字段是否完整。
6. p4 promotion_state 字段是否完整。
7. p5_component_effect_summary.csv 是否生成。
8. manifest 新增字段是否存在。
```

---

# 10. 任务边界

本次不是主线策略开发，不是实盘版本，不是参数寻优。

本次只做：

```text
P1 特征补齐
P2 明细完整性
P3 cap 验收字段
P4 晋级状态完整性
P5 组件归因
manifest / report 增强
```
