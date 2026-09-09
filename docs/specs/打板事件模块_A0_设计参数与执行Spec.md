# 打板事件模块 A0 — 设计参数与执行 Spec

> 给 Claude Code / Codex 执行。
> 本文档用于定义“打板事件模块”的 A0 版本：先建立事件面板 + Gate0/Gate1 小闭环，不直接审 194 个 RD-Agent 因子，不直接上完整四关。
> 核心目标：把打板域的数据口径、样本池、收益标签、池内 IC、滚动验证和最小样本阈值先跑干净，避免后续四关法庭建立在错误样本上。

---

## 0. 本版定位

### 0.1 为什么要先做 A0

通用因子法庭 V1/V2 已经证明：

- Gate1 能计算 OOS IC + HAC t；
- Gate2 能做多重检验；
- Gate3 能去冗余；
- Gate4 能识别衰减；
- 自检机制可以拦住口径错误。

但打板域不是通用横截面因子，不能简单照搬全市场 IC。

打板域的核心问题是：

```text
样本池不是全市场，而是涨停 / 接近涨停 / 冲板 / 炸板这类事件池。
```

所以 A0 的目标不是筛出最终 alpha，而是先验证：

```text
打板事件池定义是否正确；
首板 / 连板是否能准确拆分；
收益标签是否严格无泄漏；
池内 Rank IC 是否能稳定计算；
样本量阈值是否合理；
滚动验证是否能跑通。
```

---

### 0.2 A0 不做什么

A0 不做：

```text
不审 194 个 RD-Agent 打板因子；
不做 Gate2 / Gate3 / Gate4；
不标 robust_alpha；
不使用 2026 做调参；
不直接得出实盘结论。
```

A0 只做：

```text
事件面板 + Gate0/Gate1 小闭环。
```

---

## 1. 样本池定义：C 分层 + B 扩展池

### 1.1 总体拍板

涨停候选池采用：

```text
C 分层 + B 扩展池
```

也就是：

```text
底层样本不是只看收盘涨停，
而是纳入涨停、接近涨停、触板、冲板失败等样本；
再拆成首板池和连板池。
```

---

### 1.2 为什么不能只用收盘涨停

不建议只使用：

```text
当天所有收盘涨停的票 close >= 涨停价
```

原因是只看收盘涨停会漏掉：

```text
冲板失败；
炸板；
接近涨停但没封住；
盘中触板但收盘没封住；
强势冲高但尾盘回落。
```

这些负样本对判断打板因子非常关键。

如果只保留封板成功样本，法庭会天然缺少“失败案例”，容易高估因子有效性。

---

### 1.3 事件总池 event_pool_all

主样本池定义为：

```text
event_pool_all
```

候选条件满足任意一条即可：

```text
1. 当日涨幅 >= 7%
2. 当日 high >= limit_up_price * 0.995
3. 当日 close >= limit_up_price * 0.995
```

其中：

```text
limit_up_price = 当日涨停价
```

说明：

- `涨幅>=7%` 用来捕捉接近涨停但未触板的强势票；
- `high>=涨停价*0.995` 用来捕捉盘中触板 / 接近触板；
- `close>=涨停价*0.995` 用来捕捉收盘接近封板的票。

---

### 1.4 事件标签

在 event_pool_all 中，为每只股票每个交易日生成以下标签：

```text
sealed_limit
limit_touch
near_limit
failed_board
```

建议定义：

```text
sealed_limit:
    close >= limit_up_price * 0.995

limit_touch:
    high >= limit_up_price * 0.995

near_limit:
    pct_chg >= 7% 或 close >= limit_up_price * 0.97

failed_board:
    limit_touch = True 且 sealed_limit = False
```

说明：

- `sealed_limit`：收盘接近或达到涨停；
- `limit_touch`：盘中触及或接近涨停；
- `near_limit`：强势接近涨停；
- `failed_board`：盘中冲板但未封住，是重要负样本。

---

### 1.5 首板池 first_board_pool

首板池定义：

```text
first_board_pool
```

条件：

```text
event_pool_all = True
且 previous_consecutive_limit_days = 0
```

含义：

```text
今日是第一个涨停/冲板事件日，之前没有连续涨停。
```

注意：

- 首板池不一定只包含收盘封住的首板；
- 也包含首板冲板失败 / 接近涨停强势票；
- 这是为了让因子能比较“谁更像明天有溢价的首板”。

---

### 1.6 连板池 multi_board_pool

连板池定义：

```text
multi_board_pool
```

条件：

```text
event_pool_all = True
且 previous_consecutive_limit_days >= 1
```

含义：

```text
此前已有至少 1 天连续涨停 / 涨停事件，今日属于连板或连板冲击。
```

连板池样本天然更少，后续 IC 计算需要更低样本阈值，并标记小样本风险。

---

## 2. 前向收益标签

### 2.1 主评估周期

主评估使用：

```text
T+3
```

主收益标签：

```text
fwd_return_T1open_to_T3close
```

定义：

```text
fwd_return_T1open_to_T3close = T+3 close / T+1 open - 1
```

---

### 2.2 为什么从 T+1 open 开始

打板事件中的很多信息是在 T 日收盘后才完整知道的，例如：

```text
是否封住涨停；
收盘封单状态；
是否炸板；
最终换手；
最终量能；
收盘强弱。
```

如果用这些 T 日收盘后信息，却假设 T 日收盘或 T 日涨停价可以成交，就会产生隐性未来函数 / 不可交易假设。

所以 A0 主口径统一从：

```text
T+1 open
```

开始计算收益。

---

### 2.3 辅助收益周期

除了主评估 T+3，还要辅助输出：

```text
fwd_return_T1open_to_T1close
fwd_return_T1open_to_T2close
fwd_return_T1open_to_T5close
```

对应：

```text
T+1
T+2
T+5
```

用途：

- T+1：看次日溢价；
- T+2：看短线延续；
- T+3：主评估；
- T+5：看是否仍有短期持续性。

---

### 2.4 暂不混用盘中打板成交标签

A0 暂不使用：

```text
board_entry_return_Tlimit_to_T2close
```

原因：

盘中打板成交涉及：

```text
是否能排到；
封单变化；
撤单；
盘中触板时间；
一字板无法成交；
成交概率建模。
```

这是下一阶段的问题，不在 A0 里混入。

后续如果要模拟盘中打板成交，可以单独做：

```text
A1.5 board_entry_return 模块
```

---

## 3. 池内 IC 口径

### 3.1 主 IC

A0 使用：

```text
每日事件池内 Rank IC
```

定义：

```text
每天在涨停候选池内：
Rank IC = SpearmanRankCorr(factor_value, fwd_return_T1open_to_T3close)
```

注意：

```text
不是全市场横截面 IC。
```

打板因子的比较对象应该是：

```text
同一天同一事件池内，谁更强、谁未来收益更好。
```

而不是和全市场普通股票比较。

---

### 3.2 分池计算

A0 至少计算三套池内 IC：

```text
event_pool_all
first_board_pool
multi_board_pool
```

输出字段：

```text
pool_type
```

允许值：

```text
event_pool_all
first_board_pool
multi_board_pool
```

---

### 3.3 Top-Bottom Spread 辅助指标

除了 Rank IC，还要输出：

```text
top_bottom_spread
```

定义：

```text
每天按 factor_value 排序；
取 top 30% 和 bottom 30%；
top_bottom_spread = top组未来收益均值 - bottom组未来收益均值
```

用途：

```text
IC 反映排序相关性；
Top-Bottom Spread 反映实际收益差。
```

打板池样本小，单独看 IC 可能噪声大，Spread 是重要辅助证据。

---

## 4. 滚动窗口验证

### 4.1 主滚动窗口

主口径：

```text
M = 120
K = 20
step = 20
```

含义：

```text
前 120 个交易日用于方向锁定 / 参数确认；
后 20 个交易日用于验证；
每 20 个交易日向前滚动一次。
```

---

### 4.2 敏感性窗口

辅助敏感性口径：

```text
M = 60
K = 20
step = 20
```

用途：

```text
观察较短近期窗口下是否稳定。
```

但注意：

```text
M=60 不作为唯一主口径。
```

如果一个因子只在 M=60 下好、M=120 下不好，不能直接认为稳定有效，可能是近期过拟合。

---

## 5. 每日最小样本阈值

### 5.1 阈值拍板

不同池使用不同最小样本阈值：

```text
event_pool_all: min_daily_samples = 25
first_board_pool: min_daily_samples = 15
multi_board_pool: min_daily_samples = 10
```

如果连板池样本不足，可允许降到：

```text
multi_board_pool: min_daily_samples = 8
```

但必须标记：

```text
small_sample_warning = True
```

---

### 5.2 样本不足处理

如果某日某池样本数量低于阈值：

```text
该日该池不计算 IC；
不进入 daily IC 序列；
在日志中记录 skipped_due_to_small_sample。
```

输出字段：

```text
valid_daily_sample_count
skipped_days_count
small_sample_warning
```

---

## 6. 数据周期

### 6.1 数据归档范围

数据可以归档：

```text
2024-01-01 至 now
```

---

### 6.2 开发 / 验证范围

A0 开发和滚动验证只使用：

```text
2024-01-01 至 2025-12-31
```

---

### 6.3 2026 封存

2026 数据作为：

```text
Final Holdout
```

规则：

```text
可以下载；
可以清洗；
可以归档；
但不能用于调参数；
不能用于选口径；
不能用于决定阈值；
不能用于判断 A0 是否成功。
```

等 A0 口径固定、A1/A2 审判流程固定后，再使用 2026 做最终确认。

---

## 7. Gate0 / Gate1 小闭环

### 7.1 A0 只做 Gate0 和 Gate1

A0 只实现：

```text
Gate0: 事件面板 + 因子值 + 收益标签 + 防泄漏
Gate1: 池内 IC + HAC t + 滚动验证
```

暂不做：

```text
Gate2 FDR
Gate3 去冗余
Gate4 衰减
```

---

### 7.2 Gate0 内容

Gate0 必须完成：

```text
1. 生成 event_pool_all / first_board_pool / multi_board_pool；
2. 生成 sealed_limit / limit_touch / near_limit / failed_board 标签；
3. 生成 previous_consecutive_limit_days；
4. 生成 T+1 open 到 T+N close 的收益标签；
5. 过滤 ST / 停牌 / 无价格 / 无成交 / 未来收益缺失样本；
6. 标记一字板 / 不可买入样本；
7. 确认 T 日因子值只使用 T 日及以前信息；
8. 输出事件面板。
```

---

### 7.3 Gate1 内容

Gate1 必须完成：

```text
1. 在池内计算 daily Rank IC；
2. 输出 daily IC 序列；
3. 计算 naive t；
4. 计算 HAC t；
5. 计算 top-bottom spread；
6. 按 M=120/K=20 和 M=60/K=20 做滚动验证；
7. 输出每个测试因子在各池、各收益周期下的结果。
```

---

### 7.4 HAC t

主收益周期为 T+3，建议：

```text
hac_lag = 3
```

辅助收益周期对应：

```text
T+1: hac_lag = 1
T+2: hac_lag = 2
T+3: hac_lag = 3
T+5: hac_lag = 5
```

如果实现上统一，可以先使用：

```text
hac_lag = horizon
```

---

## 8. A0 测试因子范围

A0 不直接接入 194 个 RD-Agent 因子。

A0 先选 5-10 个已知、容易解释、容易验证的打板相关因子。

建议示例：

```text
auction_strength
open_gap
turnover_rate
volume_ratio
sealed_strength
failed_board_flag
limit_touch_time_proxy
previous_consecutive_limit_days
intraday_high_close_gap
amount_ratio
```

如果某些字段暂时没有，可以先用已有字段构造替代版本。

A0 的目标不是证明这些因子强，而是验证：

```text
事件池、收益标签、池内 IC、滚动验证整条链路能跑通。
```

---

## 9. 输出文件

输出目录建议：

```text
research/board_event_a0/
```

### 9.1 事件面板

```text
board_event_panel.parquet
```

建议字段：

```text
date
code
name
open
high
low
close
pre_close
pct_chg
limit_up_price
event_pool_all
first_board_pool
multi_board_pool
sealed_limit
limit_touch
near_limit
failed_board
previous_consecutive_limit_days
is_st
is_paused
is_one_price_limit
tradable_next_open
fwd_return_T1open_to_T1close
fwd_return_T1open_to_T2close
fwd_return_T1open_to_T3close
fwd_return_T1open_to_T5close
```

---

### 9.2 每日 IC 序列

```text
board_event_daily_ic.csv
```

建议字段：

```text
factor_name
pool_type
return_horizon
date
sample_count
rank_ic
top_bottom_spread
small_sample_warning
```

---

### 9.3 Gate1 汇总

```text
board_event_gate1_results.csv
```

建议字段：

```text
factor_name
pool_type
return_horizon
valid_ic_days
mean_ic
std_ic
naive_t
hac_t
hac_lag
mean_top_bottom_spread
gate1_pass
fail_reason
```

---

### 9.4 滚动验证结果

```text
board_event_rolling_validation.csv
```

建议字段：

```text
factor_name
pool_type
return_horizon
window_type
train_start
train_end
valid_start
valid_end
train_mean_ic
valid_mean_ic
valid_hac_t
direction_locked_by_train
direction
pass_validation
```

---

### 9.5 Summary

```text
board_event_a0_summary.md
```

必须包含：

```text
事件池样本统计；
首板 / 连板样本统计；
跳过天数；
每个收益周期有效天数；
每个测试因子的 Gate1 结果；
滚动验证结果；
发现的数据问题；
是否可以进入 A1。
```

---

## 10. A0 自检

A0 必须做机制自检。

### 10.1 事件池自检

随机抽查若干交易日，输出：

```text
当日 event_pool_all 数量；
sealed_limit 数量；
failed_board 数量；
first_board 数量；
multi_board 数量。
```

检查是否符合直觉。

---

### 10.2 收益对齐自检

随机抽查若干样本，输出：

```text
T 日 close；
T+1 open；
T+3 close；
fwd_return_T1open_to_T3close。
```

确认收益标签没有用错日期。

---

### 10.3 泄漏自检

检查因子字段中是否包含：

```text
future_return
fwd_return
T+1
T+2
T+3
T+5
未来收益标签
```

如果发现因子计算使用未来收益字段，必须直接失败。

---

### 10.4 打乱目标自检

将未来收益随机打乱后重新计算 IC。

预期：

```text
mean_ic 接近 0；
hac_t 不应显著。
```

如果打乱后仍显著，说明流程可能有泄漏或计算错误。

---

## 11. 成功标准

A0 成功不是“找到强因子”。

A0 成功标准是：

```text
1. 事件池能稳定生成；
2. 首板 / 连板能拆分；
3. 收益标签严格从 T+1 open 开始；
4. 池内 IC 能稳定计算；
5. 样本不足能正确跳过；
6. 滚动验证能跑通；
7. 打乱目标自检后 IC 归零；
8. summary 能清楚说明数据问题和下一步。
```

只有 A0 成功后，才进入：

```text
A1: 接入 194 个 RD-Agent 打板因子；
A2: 完整四关审判。
```

---

## 12. 给 CC 的启动提示词

```text
请按《打板事件模块 A0 — 设计参数与执行 Spec》执行。A0 只做事件面板 + Gate0/Gate1 小闭环，不接入 194 个 RD-Agent 因子，不做 Gate2/3/4，不碰 2026 调参，不标 robust_alpha。

参数拍板：
1. 涨停候选池采用 C 分层 + B 扩展池：底层样本为涨幅≥7%或触及/接近涨停的股票，再拆成 first_board_pool 和 multi_board_pool，同时保留 sealed_limit、limit_touch、near_limit、failed_board 标签。
2. 主收益用 fwd_return_T1open_to_T3close，辅助 T+1/T+2/T+5，全部从 T+1 open 开始计算。
3. IC 使用每日事件池内 Rank IC，不使用全市场横截面 IC；同时输出 top30%-bottom30% spread。
4. 滚动验证主口径 M=120/K=20/step=20，敏感性口径 M=60/K=20/step=20。
5. 最小样本阈值：总池25，首板15，连板10；连板不足可降到8但必须标 small_sample_warning。
6. 数据可归档 2024-01 至 now，但开发验证只用 2024-2025；2026 是 final holdout，不用于调规则。
7. 先选 5-10 个已知打板相关因子测试链路。A0 成功标准是事件池、收益对齐、池内 IC、滚动验证和打乱目标自检全部跑通，而不是找到强因子。

输出到 research/board_event_a0/：
board_event_panel.parquet
board_event_daily_ic.csv
board_event_gate1_results.csv
board_event_rolling_validation.csv
board_event_a0_summary.md
```

---

## 13. 一句话原则

```text
打板事件模块 A0 的目的不是筛 alpha，
而是先把“什么是打板样本、怎么算未来收益、怎么在事件池内验证因子”这件事做对。
```
