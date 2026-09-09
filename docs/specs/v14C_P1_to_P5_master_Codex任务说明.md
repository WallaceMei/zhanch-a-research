# v1.4.0C-P1~P5 一体化研究脚本 Codex 任务说明

## 0. 背景与最终定版结论

当前项目目录：

```text
D:\Code\JQ\战车A
```

当前 v1.4.0C 完整区间研究结果目录：

```text
D:\Code\JQ\战车A\role_rotation_result_bundle V140C
```

当前已有核心结论：

```text
1. v1.4.0C / role_rotation_observer 表面收益明显优于 baseline。
2. 但该版本不能进入主线，不能进入真实执行版。
3. 主要问题不是收益不够，而是收益结构不稳：
   - 胜率低；
   - fast_loss 过高；
   - Top3 盈利贡献过度集中；
   - 参数扰动不稳定；
   - 晋级后纯段 PnL 为负；
   - 买入时 cap 仍有超限。
4. 因此下一阶段不是直接优化收益，而是研究：
   - 为什么快亏；
   - 如何识别大肉；
   - 如何减少小亏；
   - 如何修复仓位 cap；
   - 如何验证晋级是否真的有价值；
   - 如何降低过拟合风险。
```

本次任务目标：

```text
新建一个独立研究脚本，在一个脚本内完成 v1.4.0C 的 P1~P5 研究。
```

推荐新脚本名称：

```text
research_v14C_P1_to_P5_master.py
```

推荐输出目录：

```text
D:\Code\JQ\战车A\role_rotation_result_bundle V140C_P1_P5
```

---

## 1. 核心原则

请严格遵守：

```text
1. 不修改主策略文件。
2. 不修改原始研究脚本 research_role_rotation_direct_sim_v1.py。
3. 不把实验结果合并进主线。
4. 不实盘化。
5. 不为了提高收益调参。
6. 不根据单一区间最优结果自动搜索参数。
7. 不放宽 deep_water 条件。
8. 不扩大仓位作为主要优化手段。
9. 不因为 v1.4.0C 收益高就建议进入主线。
10. 不 git add。
11. 不 git commit。
12. 不联网。
```

本脚本只用于研究：

```text
research_v14C_P1_to_P5_master.py = 独立研究脚本
```

不是：

```text
策略主线版本
实盘执行版本
参数寻优器
自动优化器
```

---

## 2. 总体设计

请在一个脚本内完成 P1~P5，但必须模块化，不允许写成一个混乱的大函数。

推荐结构：

```text
research_v14C_P1_to_P5_master.py

Layer 0：基础工具与数据读取
Layer 1：v1.4.0C 原始结果读取与基准复核
Layer 2：P1 entry feature 补采集
Layer 3：P2 fast_loss 降损实验
Layer 4：P3 仓位 cap 与弱市降频实验
Layer 5：P4 晋级后保护实验
Layer 6：P5 综合观测版
Layer 7：统一反过拟合检查
Layer 8：统一报告、Excel、CSV、ZIP 输出
```

推荐主入口：

```python
def run_all_p1_to_p5(
    start_date="2025-07-01",
    end_date="2026-06-14",
    source_dir="role_rotation_result_bundle V140C",
    output_dir="role_rotation_result_bundle V140C_P1_P5",
    run_p1=True,
    run_p2=True,
    run_p3=True,
    run_p4=True,
    run_p5=True,
):
    pass
```

---

## 3. 读取文件

请从 source_dir 读取以下文件：

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

如果某些文件缺失：

```text
1. 不要崩溃。
2. 在报告中标记 missing。
3. 对应分析项输出 WARNING。
4. 不允许静默跳过。
```

---

## 4. 输出文件

输出目录：

```text
D:\Code\JQ\战车A\role_rotation_result_bundle V140C_P1_P5
```

必须输出：

```text
v14C_P1_to_P5_master_report.md
v14C_P1_to_P5_outputs.xlsx
v14C_P1_to_P5_run_manifest.json
v14C_P1_to_P5_result_bundle.zip
```

建议输出 CSV：

```text
p1_entry_feature_trade_log.csv
p1_fast_loss_vs_big_meat_features.csv
p1_entry_feature_diagnosis.csv

p2_fast_loss_experiment_summary.csv
p2_confirm_add_position_detail.csv
p2_quick_fail_exit_detail.csv
p2_next_day_acceptance_detail.csv

p3_cap_and_regime_summary.csv
p3_cap_check_detail.csv
p3_market_regime_position_detail.csv

p4_promotion_protection_summary.csv
p4_promotion_detail.csv
p4_post_promotion_pnl_compare.csv

p5_combined_observer_summary.csv
p5_combined_observer_daily_nav.csv
p5_combined_observer_trades.csv

p_overfit_check_summary.csv
p_cost_sensitivity_summary.csv
p_profit_concentration_summary.csv
```

---

# 5. P1：entry feature 补采集版

## 5.1 目标

P1 只做数据采集，不改变交易逻辑。

目标：

```text
区分 fast_loss 和 big_meat 在买入当天是否有可识别差异。
```

P1 不做：

```text
1. 不过滤股票。
2. 不改变买入。
3. 不改变卖出。
4. 不改变仓位。
5. 不改变晋级。
```

## 5.2 必须补采集字段

每一笔买入交易都要补采集 entry features：

```text
entry_date
stock
name
variant
role
trade_category
entry_price
entry_open
entry_high
entry_low
entry_close
entry_volume
entry_money

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

next_day_open_ret
next_day_close_ret
next_day_close_to_high
next_day_volume_ratio
next_day_ma5_break
```

如果某些字段在当前旧结果中无法还原：

```text
1. 在 p1_entry_feature_diagnosis.csv 标记 missing。
2. 在报告中说明下一轮聚宽直接模拟需要补采集。
3. 不要用猜测值填充。
```

## 5.3 分类标签

为每笔交易生成标签：

```text
is_win
is_loss
is_fast_loss
is_small_loss
is_big_meat_10
is_super_meat_20
hold_bucket
exit_reason
pnl_pct
pnl_value
```

fast_loss 定义：

```text
hold_days <= 5 且 pnl_pct < 0
```

big_meat 定义：

```text
pnl_pct >= 0.10
```

super_meat 定义：

```text
pnl_pct >= 0.20
```

## 5.4 P1 输出分析

必须输出：

```text
1. fast_loss 和 big_meat 的 entry feature 对比。
2. fast_loss 和 super_meat 的 entry feature 对比。
3. 盈利交易和亏损交易的 signal_score 分布。
4. 判断 signal_score 是否足够区分。
5. 哪些字段缺失，下一版必须补采集。
```

P1 最终报告必须明确：

```text
1. fast_loss 是否能在买入当天提前识别。
2. big_meat 是否有明显共同特征。
3. 当前字段是否不足。
4. 下一轮最关键的 5 个 entry features 是什么。
```

---

# 6. P2：fast_loss 降损实验版

## 6.1 目标

减少买入后 1~5 天快速亏损。

当前问题：

```text
fast_loss 数量多，亏损金额占总亏损比例高。
```

P2 不能追求最高收益，核心验收是：

```text
fast_loss 金额下降；
validation / oos 不坍塌；
super_meat 不被大量错杀。
```

## 6.2 P2A：首买小仓 + 次日确认加仓

研究逻辑：

```text
Top1 原本目标仓位 35%，改为首买 20%~25%。
Top2 原本目标仓位 25%，改为首买 15%~20%。
次日确认仍强，再补到原目标仓位。
```

次日确认条件建议只做固定实验，不自动寻优：

```text
1. 未跌破 MA5。
2. 未出现明显浮亏。
3. 收盘不弱。
4. close_to_high 不弱。
5. market_state 不转 bear。
```

输出：

```text
p2_confirm_add_position_detail.csv
```

必须统计：

```text
1. 首买后未确认的交易数量。
2. 因未确认而少亏的金额。
3. 因未确认而错过的大肉数量。
4. fast_loss 变化。
5. super_meat 变化。
```

## 6.3 P2B：快速失效退出

研究逻辑：

```text
买入后 1~2 天内，如果出现快速失效，则提前退出。
```

快速失效候选条件：

```text
1. 跌破 MA5 且浮亏。
2. 浮亏超过固定阈值。
3. close_to_high 明显下降。
4. next_day_close_ret 明显为负。
5. 市场状态转弱。
```

注意：

```text
不要搜索最优阈值。
只做少数几个固定规则对照。
```

输出：

```text
p2_quick_fail_exit_detail.csv
```

必须统计：

```text
1. 减少了多少 fast_loss。
2. 错杀了多少 big_meat。
3. full / train / validation / oos 是否稳定。
```

## 6.4 P2C：买入后首日承接确认

研究逻辑：

```text
买入后第一天看承接，如果承接差，则减仓或退出。
```

承接字段：

```text
next_day_open_ret
next_day_close_ret
next_day_close_to_high
next_day_volume_ratio
next_day_ma5_break
```

输出：

```text
p2_next_day_acceptance_detail.csv
```

---

# 7. P3：仓位 cap 与弱市降频实验版

## 7.1 目标

解决两个问题：

```text
1. 买入时 cap 超限。
2. 弱市环境下交易频率和仓位过高。
```

## 7.2 必须先修 cap 检查

当前要求：

```text
cap_exceeded_on_buy 必须等于 0。
```

每次买入前必须计算：

```text
pre_buy_total_ratio
target_order_ratio
available_ratio
post_buy_total_ratio
cap_limit
cap_exceeded_on_buy
```

硬规则：

```text
post_buy_total_ratio <= cap_limit
```

如果超限：

```text
缩单到 available_ratio，而不是超买。
```

输出：

```text
p3_cap_check_detail.csv
```

## 7.3 动态仓位研究

只做研究，不作为上线参数。

研究配置：

```text
bull:
  total_cap = 0.75 ~ 0.90

neutral:
  total_cap = 0.60 ~ 0.75

bear:
  total_cap = 0.35 ~ 0.50
```

输出：

```text
p3_market_regime_position_detail.csv
```

必须比较：

```text
1. 回撤变化。
2. fast_loss 变化。
3. 收益是否只是靠更高仓位。
4. train / validation / oos 是否稳定。
```

禁止：

```text
因为 max_total_cap=0.90 收益更高就直接推荐扩大仓位。
```

---

# 8. P4：晋级后保护实验版

## 8.1 背景

当前数据说明：

```text
卫星发现强票可能有价值；
但晋级后纯段 pnl 为负。
```

所以 P4 目标不是优化晋级收益，而是回答：

```text
晋级动作是否应该保留？
晋级后是否应该加仓？
晋级后是否应该更快保护？
```

## 8.2 P4 对照实验

### P4A：卫星盈利即止盈，不晋级

逻辑：

```text
达到卫星盈利目标后直接止盈，不晋级核心。
```

目的：

```text
验证“晋级”是否比“卫星止盈”更好。
```

### P4B：晋级只改标签，不加仓

逻辑：

```text
允许 satellite -> promoted_core 标签变化；
但不加仓、不替换核心。
```

目的：

```text
把“识别强票”和“加仓动作”解耦。
```

### P4C：晋级后 1~2 天不走强则退出

逻辑：

```text
晋级后若 1~2 天不继续走强，退出或降回卫星。
```

走强判断建议：

```text
1. 不跌破 MA5。
2. post_promotion_pnl 不转负。
3. close_to_high 不明显转弱。
4. 市场状态不转 bear。
```

输出：

```text
p4_promotion_protection_summary.csv
p4_promotion_detail.csv
p4_post_promotion_pnl_compare.csv
```

## 8.3 P4 验收

必须回答：

```text
1. post_promotion_pnl 是否转正。
2. 晋级是否比卫星止盈更好。
3. 晋级是否需要加仓。
4. 晋级是否需要保护。
5. 是否应该废除晋级动作。
```

---

# 9. P5：综合观测版

## 9.1 目标

P5 不是收益最高组合，而是综合观测版。

只能组合通过初筛的模块：

```text
1. P1 证明有区分度的 entry features。
2. P2 明显减少 fast_loss 且不大量错杀大肉的规则。
3. P3 cap 无超限且不过度牺牲收益的仓位规则。
4. P4 能改善晋级后回吐的保护规则。
```

## 9.2 P5 输出

```text
p5_combined_observer_summary.csv
p5_combined_observer_daily_nav.csv
p5_combined_observer_trades.csv
p5_combined_observer_report.md
```

## 9.3 P5 验收

P5 必须通过：

```text
1. full / train / validation / oos 均不能坍塌。
2. 参数扰动稳定性改善。
3. Top3 盈利集中度下降。
4. fast_loss 金额下降。
5. cap_exceeded_on_buy = 0。
6. 成本敏感性仍通过。
7. 不能靠扩大仓位换收益。
```

---

# 10. 统一反过拟合检查

所有 P1~P5 输出必须统一检查：

```text
1. full
2. train
3. validation
4. oos
5. 参数扰动
6. 成本 1.5x
7. 成本 2.0x
8. 滑点加倍
9. top1 / top3 / top5 盈利贡献
10. fast_loss 数量和金额
11. big_meat 数量和金额
12. cap_exceeded_on_buy
13. 最大回撤
14. 胜率
15. 盈亏比
16. 平均持仓天数
```

输出：

```text
p_overfit_check_summary.csv
p_cost_sensitivity_summary.csv
p_profit_concentration_summary.csv
```

---

# 11. 最终报告结构

最终 Markdown 报告：

```text
v14C_P1_to_P5_master_report.md
```

必须包含：

```text
1. 执行摘要
2. v1.4.0C 当前问题复核
3. P1 entry feature 补采集结果
4. P2 fast_loss 降损实验结果
5. P3 仓位 cap 与弱市降频实验结果
6. P4 晋级后保护实验结果
7. P5 综合观测版结果
8. 统一反过拟合检查
9. 是否建议进入主线
10. 是否建议进入真实执行版
11. 是否建议继续研究
12. 下一步最优先事项
13. 禁止事项
```

最终结论必须明确：

```text
当前 v1.4.0C 不进主线，不进真实执行版。
P1~P5 只作为研究分支。
只有当 P5 通过完整反过拟合检查，才考虑进入只打日志的观测版。
```

---

# 12. 运行方式

在本地 / 聚宽研究环境根据实际情况运行。

建议入口：

```python
import research_v14C_P1_to_P5_master as p

p.run_all_p1_to_p5(
    start_date="2025-07-01",
    end_date="2026-06-14",
    source_dir="role_rotation_result_bundle V140C",
    output_dir="role_rotation_result_bundle V140C_P1_P5",
    run_p1=True,
    run_p2=True,
    run_p3=True,
    run_p4=True,
    run_p5=True,
)
```

如果需要注入聚宽 API，请保持与原研究脚本一致：

```python
from jqdata import *
import importlib
import research_v14C_P1_to_P5_master as p
importlib.reload(p)

p.get_price = get_price
p.get_trade_days = get_trade_days
p.get_all_securities = get_all_securities
p.get_extras = get_extras
p.get_call_auction = get_call_auction

p.run_all_p1_to_p5(
    start_date="2025-07-01",
    end_date="2026-06-14",
    source_dir="role_rotation_result_bundle V140C",
    output_dir="role_rotation_result_bundle V140C_P1_P5",
)
```

---

# 13. 验收标准

脚本完成后必须满足：

```text
1. 不修改任何主策略文件。
2. 不修改 research_role_rotation_direct_sim_v1.py。
3. 新建 research_v14C_P1_to_P5_master.py。
4. 输出 v14C_P1_to_P5_master_report.md。
5. 输出 v14C_P1_to_P5_outputs.xlsx。
6. 输出 v14C_P1_to_P5_run_manifest.json。
7. 输出 v14C_P1_to_P5_result_bundle.zip。
8. 每个 P 阶段都有独立 CSV。
9. 报告中明确说明每个实验是否通过。
10. 报告中明确说明是否存在过拟合风险。
11. 报告中明确说明是否建议进入主线。
```

---

# 14. 禁止事项

不要做：

```text
1. 不要直接改主策略。
2. 不要直接把 P5 合并进主线。
3. 不要自动搜索最优参数。
4. 不要为了总收益提高而扩大仓位。
5. 不要放宽 deep_water。
6. 不要只看 full 区间。
7. 不要忽略 train / validation / oos。
8. 不要忽略 Top3 盈利集中度。
9. 不要忽略 fast_loss。
10. 不要忽略 cap_exceeded_on_buy。
11. 不要 git add。
12. 不要 git commit。
13. 不要联网。
```

---

# 15. 本任务的本质

```text
这是一个研究脚本整合任务。
不是策略上线任务。
不是参数优化任务。
不是主线合并任务。
```

最终交付物应该回答：

```text
1. fast_loss 是否能被识别和减少？
2. big_meat 是否能保留？
3. 仓位 cap 是否能严格控制？
4. 晋级机制是否真的值得保留？
5. 综合观测版是否比 v1.4.0C 更稳？
6. 是否降低了过拟合风险？
```
