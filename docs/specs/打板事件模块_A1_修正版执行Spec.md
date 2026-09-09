# 打板事件模块 A1 — 修正版执行 Spec

> 给 Claude Code / Codex 执行。
> 本文档是在原《打板事件模块 A1 — 执行 Spec》基础上的修正版。
> 主要修正点：
> 1. A1 拆成 A1a / A1b 两阶段；
> 2. tick 封单字段必须先小样本人工验真；
> 3. 龙虎榜字段必须标注信息时点，防止盘中使用造成未来函数；
> 4. 四关主判据固定主口径，禁止在多池/多周期/多窗口中挑最佳结果；
> 5. Gate1 增加 Top-Bottom Spread 证据；
> 6. Gate4 增加半年度分段最小样本保护；
> 7. A1a 完成后必须停下报告，确认后再进入 A1b。

---

## 0. 本版定位

### 0.1 A1 的目标

A0 已完成：

```text
事件面板 + Gate0/Gate1 小闭环
```

并验证：

```text
事件池生成正确；
收益从 T+1 open 开始；
池内 Rank IC 可计算；
滚动验证可运行；
打乱目标后 IC 归零；
链路无明显泄漏。
```

A1 的目标是在 A0 基础上：

```text
补齐打板字段；
接入 194 个 RD-Agent 打板因子；
用四关法庭做全量审判。
```

但 A1 不是一步到位挂机任务。
它必须拆成：

```text
A1a：字段补齐 + 字段质量验真 + 字段覆盖率审计
A1b：194 因子全量计算 + 四关审判
```

---

### 0.2 为什么必须拆成 A1a / A1b

A1 最大风险不是四关法庭，而是打板字段本身。

尤其是：

```text
seal_strength
seal_ratio
seal_minutes
open_times
limit_turnover
lhb_net
inst_net
on_lhb
```

这些字段涉及：

```text
tick 数据；
分钟数据；
龙虎榜公告时点；
盘口单位；
流通市值口径；
涨停价匹配；
炸板次数识别。
```

只要字段口径错，后面 194 因子审判全部会被污染。

所以：

```text
A1a 只负责把字段补齐并验真；
A1b 只有在 A1a 确认后才允许开始。
```

---

## 1. 红线

以下红线不可破：

1. **不标 robust_alpha**
   四关全过最多标：

```text
gate_all_pass_candidate
```

2. **不碰 2026 调参**
   开发验证只用：

```text
2024-01-01 至 2025-12-31
```

   2026 只作为 final holdout，不用于调规则、不用于选口径、不用于判断阈值。

3. **不下最终可用性结论**
   CC 只输出结果和证据，Wallace 决定是否认可。

4. **复用 A0，不重造事件池**
   A1 在 A0 的：

```text
board_event_panel.parquet
```

   基础上补字段。不得擅自修改 A0 的事件池定义。

5. **字段补不出来就如实标记**
   不允许硬造、不允许随意填 0、不允许 forward fill 伪造历史。

6. **装新包先报**
   如需安装 AKShare / 其他依赖，先报告，不擅自安装。

7. **tick / miniQMT 数据取数需半盯**
   miniQMT 客户端需要开启；第一次接 tick 字段不允许纯挂机。

8. **自检不过就停止**
   任一自检失败，写：

```text
SELF_CHECK_FAILED
```

   并停止输出 final verdict。

---

# 第一阶段：A1a — 字段补齐 + 字段质量验真

## 2. A1a 目标

A1a 只做数据准备，不跑四关审判。

A1a 的目标是生成：

```text
board_event_panel_full.parquet
```

以及：

```text
board_field_backfill_report.md
board_field_coverage.csv
board_factor_field_audit_precheck.csv
```

并回答：

```text
194 个因子里，最终有多少个字段齐全、可以进入 A1b？
```

---

## 3. 待补字段

A0 已有纯 K 线字段，例如：

```text
return_3d
rsi_14
bb_position
up_streak
vol_ratio_5d
price_position_60d
```

A1a 需要补的字段分三类。

---

### 3.1 类 1：纯 K 线 / 日线 / 市场级字段

优先级最高，先做。

包括：

```text
retail_line
retail_line_change
morning_vol_ratio
tail_vol_ratio
vol_vs_prev
intraday_range
kdj_j
daily_total_limits
market_max_board
industry_limit_count
first_board_ratio
```

说明：

```text
retail_line = 100 * (HHV(high, 60) - close) / (HHV(high, 60) - LLV(low, 60))
```

这类字段外部依赖低、可复现性强，应先补。

---

### 3.2 类 2：龙虎榜字段 AKShare

字段：

```text
lhb_net
inst_net
on_lhb
```

数据源：

```text
AKShare stock_lhb_detail_em
```

要求：

1. 先确认 AKShare 是否已安装；
2. 未安装先报告；
3. 小样本拉取 3-5 个交易日验证字段含义；
4. 再批量拉 2024-2025；
5. 记录接口失败、缺失日期、覆盖率。

---

### 3.3 龙虎榜字段的信息时点约束

龙虎榜字段是 T 日收盘后公布的信息。

因此：

```text
lhb_net / inst_net / on_lhb
```

只允许用于：

```text
T+1 open 之后的收益验证
```

不得用于：

```text
T 日盘中打板成交口径
```

A1 当前收益标签从 T+1 open 起算，所以可以使用。
但字段报告必须写清楚：

```text
龙虎榜字段是 T 日收盘后信息，不可用于 T 日盘中决策。
```

如果未来做盘中打板成交模块，龙虎榜字段必须被排除。

---

### 3.4 类 3：tick / 分钟封板微观字段

字段：

```text
seal_strength
seal_ratio
seal_minutes
open_times
limit_turnover
```

数据源：

```text
miniQMT tick / minute data
```

这些是 A1a 最大风险源，必须小样本验真后才能批量生成。

---

## 4. tick 封单字段验真要求

### 4.1 小样本人工验真

批量生成前，必须抽样：

```text
5-10 个已知涨停日样本
```

覆盖：

```text
普通封板；
一字板；
炸板；
多次回封；
尾盘封板；
冲板失败。
```

对每个样本核对：

```text
date
code
name
limit_up_price
tick_time
bidPrice[0]
bidVol[0]
seal_amount
float_market_cap
seal_strength
seal_ratio
seal_minutes
open_times
limit_turnover
manual_check_note
```

---

### 4.2 必须核对的问题

必须确认：

```text
1. bidPrice[0] 是否在涨停价附近；
2. bidVol[0] 的单位是股、手，还是接口自定义单位；
3. seal_amount = bidPrice[0] * bidVol[0] 的单位是否正确；
4. float_market_cap 口径是否正确；
5. seal_strength 是否量纲合理；
6. 一字板是否能识别；
7. 炸板次数 open_times 是否准确；
8. seal_minutes 是否真的代表封板时长；
9. limit_turnover 是否没有把非涨停成交混进去；
10. 复权价和原始价没有混用。
```

---

### 4.3 验真结论

输出：

```text
board_tick_manual_validation.csv
```

字段：

```text
date
code
name
case_type
limit_up_price
sample_tick_time
bid_price_1
bid_vol_1
bid_vol_unit
seal_amount
float_market_cap
seal_strength
seal_ratio
seal_minutes
open_times
limit_turnover
manual_validation_status
manual_validation_note
```

如果验真不通过：

```text
tick_validation_failed
```

并停止 tick 字段批量生成。

---

## 5. 字段补齐原则

### 5.1 不硬造字段

字段缺失时，允许：

```text
NaN
field_unavailable
insufficient_coverage
```

不允许：

```text
随意填 0
用未来值填补
用 forward fill 伪造历史
用同类字段替代但不记录
```

---

### 5.2 字段覆盖率

每个字段必须输出：

```text
coverage_start
coverage_end
non_null_count
coverage_ratio
affected_factor_count
data_source
quality_status
```

质量状态允许：

```text
ok
partial
low_coverage
unavailable
validation_failed
```

---

## 6. A1a 输出文件

输出目录：

```text
research/board_event_a1/
```

A1a 输出：

```text
board_event_panel_full.parquet
board_field_backfill_report.md
board_field_coverage.csv
board_tick_manual_validation.csv
board_factor_field_audit_precheck.csv
```

---

### 6.1 board_field_backfill_report.md 必须包含

```text
1. 补了哪些字段；
2. 每个字段的数据源；
3. 每个字段的覆盖日期；
4. 每个字段的覆盖率；
5. 哪些字段不可用；
6. 不可用字段影响哪些因子；
7. tick 小样本验真结果；
8. 龙虎榜字段的信息时点声明；
9. 194 个因子预审后 can_calculate 数量；
10. 是否建议进入 A1b。
```

---

## 7. A1a 停止点

A1a 完成后必须停下报告。

不得自动进入 A1b。

A1a 报告中必须给出：

```text
can_calculate_factor_count
field_unavailable_factor_count
low_coverage_factor_count
leakage_suspected_factor_count
```

等 Wallace 确认后，再进入 A1b。

---

# 第二阶段：A1b — 194 因子全量四关审判

## 8. A1b 前置条件

只有满足以下条件，才允许进入 A1b：

```text
1. board_event_panel_full.parquet 已生成；
2. board_field_backfill_report.md 已完成；
3. board_factor_field_audit_precheck.csv 已完成；
4. tick 字段如使用，已通过小样本人工验真；
5. 龙虎榜字段已标注信息时点；
6. Wallace 已确认进入 A1b。
```

---

## 9. 字段审计

读取：

```text
rdagent_factors_v4.jsonl
```

对 194 个因子逐个审计：

```text
factor_name
formula
required_fields
available_fields
missing_fields
can_calculate
field_status
leakage_status
```

输出：

```text
board_factor_field_audit.csv
```

判定：

```text
字段齐全且无泄漏 → can_calculate=True
缺字段 → field_unavailable
覆盖率太低 → insufficient_coverage
公式含未来字段 → leakage_suspected
```

---

## 10. 因子值计算

对 `can_calculate=True` 的因子计算因子值。

要求：

```text
1. T 日因子值只能使用 T 日及以前信息；
2. 不允许使用 fwd_return；
3. 不允许使用未来收益字段；
4. 不允许使用负 shift；
5. 不允许使用 T+1/T+2/T+3/T+5 标签；
6. 对每个事件行生成 factor_value。
```

如果发现泄漏：

```text
leakage_suspected
```

并从后续四关出局。

---

# 11. 主口径固定，禁止挑最佳

这是 A1b 的核心防过拟合约束。

A1b 会计算多个维度：

```text
三套池：
event_pool_all
first_board_pool
multi_board_pool

四个收益周期：
T+1
T+2
T+3
T+5

两套滚动窗口：
M120/K20
M60/K20
```

但 final verdict 不允许从这些结果里挑最好的。

---

## 11.1 主判据固定

A1b final verdict 的主口径固定为：

```text
pool_type = event_pool_all
return_horizon = T+3
rolling_window = M120/K20
```

即：

```text
主池：event_pool_all
主收益：fwd_return_T1open_to_T3close
主窗口：M=120 / K=20 / step=20
```

---

## 11.2 辅助口径

以下只作为辅助 / 敏感性，不参与主 verdict：

```text
first_board_pool
multi_board_pool
T+1
T+2
T+5
M60/K20
```

如果某因子只在 first_board_pool 或 multi_board_pool 中有效，标记：

```text
pool_specific_candidate
```

不得直接升级为全局：

```text
gate_all_pass_candidate
```

---

# 12. Gate1 — 池内 IC + HAC t + Spread

## 12.1 Gate1 计算

三套池都计算：

```text
event_pool_all
first_board_pool
multi_board_pool
```

四个收益周期都计算：

```text
T+1
T+2
T+3
T+5
```

但主判据只使用：

```text
event_pool_all + T+3 + M120
```

---

## 12.2 IC 口径

每天在事件池内计算：

```text
Rank IC = SpearmanRankCorr(factor_value, future_return)
```

不是全市场横截面 IC。

---

## 12.3 HAC t

HAC lag 按收益周期：

```text
T+1: lag=1
T+2: lag=2
T+3: lag=3
T+5: lag=5
```

主判据：

```text
HAC t > 3.0
```

---

## 12.4 Top-Bottom Spread

Gate1 必须同时输出：

```text
mean_top_bottom_spread
spread_t
positive_spread_ratio
```

定义：

```text
每天按因子值排序；
top 30% 未来收益均值 - bottom 30% 未来收益均值；
得到 daily spread 序列；
计算 mean、t、正 spread 占比。
```

如果：

```text
HAC t 显著，但 Spread 不显著
```

summary 必须单独标记：

```text
ic_significant_but_spread_weak
```

此类因子不直接判死，但不得过度解读。

---

## 12.5 样本阈值

```text
event_pool_all: min_daily_samples = 25
first_board_pool: min_daily_samples = 15
multi_board_pool: min_daily_samples = 10
```

连板池必要时可降到：

```text
8
```

但必须：

```text
small_sample_warning=True
```

---

## 12.6 方向锁定

方向必须由 train 窗口锁定。

```text
train 决定方向；
validation 只验证；
validation 不允许翻方向。
```

---

## 12.7 Gate1 判定

主口径下：

```text
HAC t > 3.0
且 direction_locked=True
且 leakage_check_pass=True
且 shuffled_target_check_pass=True
```

则：

```text
gate1_candidate
```

否则：

```text
gate1_fail
```

---

# 13. Gate2 — 多重检验 FDR

## 13.1 校正族

Gate2 主校正族：

```text
本次 can_calculate=True 的因子数
```

只基于主口径：

```text
event_pool_all + T+3 + M120
```

做 BH-FDR。

不要把：

```text
first_board / multi_board / T+1/T+2/T+5 / M60
```

混进主判据。

---

## 13.2 敏感性校正

同时输出：

```text
BH-FDR n=194 sensitivity
Bonferroni n=can_calculate
Bonferroni n=194 sensitivity
```

但敏感性校正不直接改变主 verdict。

---

## 13.3 Gate2 判定

```text
BH-FDR 主口径通过 → gate2_pass
否则 → gate2_fail
```

---

# 14. Gate3 — 去冗余

## 14.1 主去冗余

Gate3 主 verdict 基于：

```text
event_pool_all + T+3 + M120
```

对 Gate2 pass 因子的每日 IC 序列做 Pearson 相关。

只使用：

```text
corr > 0.7
```

做正相关冗余聚类。

严禁使用：

```text
|corr| > 0.7
```

---

## 14.2 强负相关

如果：

```text
corr < -0.7
```

不判冗余，单独标：

```text
potential_complement_pair
```

---

## 14.3 代表因子

每簇保留：

```text
HAC t 最高的因子
```

作为代表。

非代表：

```text
gate3_redundant
```

---

## 14.4 三池辅助去冗余

可以分别输出：

```text
first_board_pool
multi_board_pool
```

的去冗余结构。

但不参与全局 final verdict。

---

# 15. Gate4 — 衰减监控

## 15.1 时间切分

打板数据只有 2024-2025，所以按半年度切分：

```text
2024H1
2024H2
2025H1
2025H2
```

---

## 15.2 分段样本保护

每个半年度分段必须满足：

```text
min_segment_ic_days = 30
```

如果任一分段不足：

```text
decay_status = insufficient_segment_data
```

不强行判：

```text
stable
decaying
```

---

## 15.3 衰减规则

沿用 V2 修正后的规则：

```text
不使用 slope<0 直接判 decay_warning
```

但仍输出：

```text
decay_slope
```

供观察。

---

### decaying

满足任一条件：

```text
1. 最后一段 IC 反向；
2. 四段严格逐段下降，且最后一段 < 第一段 * 0.5。
```

---

### decay_warning

未达到 decaying，但满足：

```text
最后一段 < 第一段 * 0.7
```

则：

```text
decay_warning
```

---

### stable

其余：

```text
stable
```

---

# 16. 四关自检

每关必须自检。

任一自检失败：

```text
SELF_CHECK_FAILED
```

并停止输出 final verdict。

---

## 16.1 Gate1 自检：打乱目标归零

打乱未来收益后重新计算 IC。

预期：

```text
mean_ic 接近 0
HAC t 不显著
```

不归零则停止。

---

## 16.2 Gate2 自检：噪声因子

混入纯噪声因子，验证 FDR 能拒绝噪声。

---

## 16.3 Gate3 自检：合成 IC 序列

构造：

```text
A = 随机 IC 序列
B = A + 小噪声
C = 独立随机序列
D = -A + 小噪声
```

预期：

```text
A/B 同簇；
A/C 不同簇；
A/D 不同簇；
A/D 标 potential_complement_pair。
```

---

## 16.4 Gate4 自检：人造衰减序列

构造：

```text
stable
decay_warning
decaying
reversal
insufficient_segment_data
```

确认分类正确。

---

# 17. 综合判定

## 17.1 final_verdict 允许集

只允许：

```text
field_unavailable
insufficient_coverage
leakage_suspected
gate1_fail
gate2_fail
gate3_redundant
gate_pass_but_decaying
gate_all_pass_candidate
pool_specific_candidate
insufficient_segment_data
```

严禁：

```text
robust_alpha
```

---

## 17.2 综合规则

```text
字段缺失 → field_unavailable
覆盖率不足 → insufficient_coverage
泄漏嫌疑 → leakage_suspected
Gate1 未过 → gate1_fail
Gate2 未过 → gate2_fail
Gate3 非代表 → gate3_redundant
Gate4 decaying → gate_pass_but_decaying
主口径四关全过且 stable / decay_warning → gate_all_pass_candidate
只在 first_board / multi_board 辅助口径有效 → pool_specific_candidate
Gate4 分段样本不足 → insufficient_segment_data
```

---

## 17.3 gate_all_pass_candidate 的含义

summary 必须明确写：

```text
gate_all_pass_candidate 不是 robust_alpha。
它只表示该因子在 2024-2025 打板事件池主口径下通过四关。
样本短、打板因子易失效、未做 2026 final holdout、未做实盘成交约束。
不能直接实盘，需要持续重验。
```

---

# 18. 输出文件

输出目录：

```text
research/board_event_a1/
```

---

## 18.1 A1a 输出

```text
board_event_panel_full.parquet
board_field_backfill_report.md
board_field_coverage.csv
board_tick_manual_validation.csv
board_factor_field_audit_precheck.csv
```

---

## 18.2 A1b 输出

```text
board_factor_field_audit.csv
board_a1_gate1_results.csv
board_a1_gate1_spread.csv
board_a1_gate2_fdr.csv
board_a1_gate3_clusters.csv
board_a1_gate3_negative_corr_pairs.csv
board_a1_gate4_decay.csv
board_a1_selfcheck.csv
board_a1_ledger.csv
board_a1_summary.md
```

---

## 19. Summary 要求

`board_a1_summary.md` 必须包含：

```text
1. A1a 字段补齐情况；
2. 每个字段覆盖率；
3. 哪些字段不可用；
4. 不可用字段影响哪些因子；
5. tick 字段人工验真结果；
6. 龙虎榜字段信息时点声明；
7. 194 因子能审几个；
8. 四关漏斗：
   194 total
   → can_calculate X
   → Gate1 Y
   → Gate2 Z
   → Gate3 independent clusters W
   → Gate4 stable / warning / decaying
   → gate_all_pass_candidate N
9. 三池对照；
10. T+1/T+2/T+3/T+5 对照；
11. M120/M60 对照；
12. IC 显著但 Spread 弱的因子；
13. 四关自检结果；
14. 明确声明：非 robust_alpha，不能直接实盘；
15. 建议下一步。
```

---

# 20. 执行顺序

## 20.1 A1a 执行顺序

```text
1. 读取 A0 board_event_panel.parquet；
2. 补纯 K 线 / 市场级字段；
3. 小样本验证字段；
4. 补 AKShare 龙虎榜字段；
5. 写明龙虎榜信息时点；
6. tick 字段小样本人工验真；
7. tick 字段验真通过后再批量补；
8. 拼接 board_event_panel_full.parquet；
9. 做 194 因子字段预审；
10. 输出 A1a 报告；
11. 停下，等待确认。
```

---

## 20.2 A1b 执行顺序

```text
1. 读取 board_event_panel_full.parquet；
2. 读取 rdagent_factors_v4.jsonl；
3. 完整字段审计；
4. 计算 can_calculate 因子值；
5. Gate1 + Spread + 打乱目标自检；
6. Gate2 + FDR 自检；
7. Gate3 + 去冗余自检；
8. Gate4 + 衰减自检；
9. 综合台账；
10. summary；
11. 停下报告。
```

---

# 21. 环境要求

使用：

```text
D:\quant_env\.venv_court
```

注意：

```text
AKShare 未安装先报告；
miniQMT 客户端需要开启；
tick 数据量大，先小样本后批量；
不要擅自安装依赖；
不要擅自改口径。
```

---

# 22. 给 CC 的最短启动提示词

```text
请按《打板事件模块 A1 — 修正版执行 Spec》执行。A1 必须拆成 A1a/A1b：A1a 只做字段补齐、字段质量验真、字段覆盖率审计和 194 因子预审，完成后必须停下报告；A1b 只有确认后才接 194 因子跑四关。tick 封单字段必须先抽 5-10 个涨停样本人工验真，确认 bidPrice/bidVol 单位、seal_amount、seal_strength、seal_minutes、open_times 等口径正确后才能批量生成；龙虎榜字段必须标注为 T 日收盘后信息，只能用于 T+1 open 之后收益验证。A1b 主判据固定为 event_pool_all + T+3 + M120/K20，first/multi、T+1/T+2/T+5、M60 只作辅助，禁止挑最佳口径下判定。Gate1 除 HAC t 外必须输出 Top-Bottom Spread；Gate4 半年度分段 min_segment_ic_days=30，不足则 insufficient_segment_data。全程不碰 2026 调参、不标 robust_alpha、自检不过就停。
```

---

## 23. 一句话原则

```text
A1 的核心风险不是四关审判，而是打板字段口径。
先把字段补齐并验真，再谈 194 因子全量审判。
```
