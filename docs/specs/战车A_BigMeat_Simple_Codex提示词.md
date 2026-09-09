# Codex 执行提示词：战车A BigMeat 简化版

请基于当前战车A策略代码，新建一个极简抓大肉版本，文件名：

```text
战车A_BigMeat_Simple.py
```

## 重要要求

1. 不要覆盖原文件。
2. 不要删除原版。
3. 不要读取或修改 `.env`、账号、密钥、token。
4. 不要大面积重构项目目录。
5. 只新建一个独立策略文件。
6. 修改完成后必须输出改动摘要、关键函数列表、语法检查结果。
7. 文件顶部必须新增版本更新日志，说明这是 BigMeat 简化版。

---

## 一、策略目标

把当前战车A简化成 **Dragon-only 抓大肉版本**。

核心思想：

```text
只做最强 Dragon；
只做 deep_water；
不做普通杂毛；
不堆复杂参数；
不追求高胜率；
目标是低频、高赔率、抓大肉；
亏损确认失败后再走，避免被 -3.5% 洗出去；
盈利后用 MA5 保护，尽量让大肉继续跑。
```

不要为了提高胜率而提前止盈。
不要为了提高资金利用率去买第三只质量较低的票。
仓位利用率通过 **赢家尾盘加仓** 解决，而不是增加杂毛票数量。

---

## 二、总体保留和删除

### 保留

1. Dragon 候选池生成逻辑。
2. `dragon_score` 评分。
3. `deep_water` 识别逻辑。
4. `market_trend` 大盘趋势判断。
5. `is_stock_uptrend` / 个股趋势过滤逻辑。
6. Dragon 原版卖出逻辑中的 MA5 保护思想：
   - 不赚钱跌破 MA5，确认失败后退出；
   - 盈利后跌破 MA5，先卖半仓；
   - 半仓后跌破保护线，清剩余仓位。
7. 缺口止损延迟确认思想：
   - 09:31 预警；
   - 09:35 确认；
   - 恢复到 -2% 以上取消止损。
8. 日志输出。
9. 每日诊断。
10. 原版必要兼容层。

### 删除或禁用实盘买入

1. `firstboard_lowopen`
2. `firstboard`
3. `weak_to_strong`
4. 普通候选合并排序
5. `unified_score` 作为买入阈值
6. `env_weight` / `quality_multiplier` / `q_mult` 对仓位的影响
7. DPM 动态扩仓
8. CSI1000 分位 + 波动率权重对买入仓位的影响
9. `panic_scout`
10. `strict_bear` 复杂模式
11. 多层 bull / neutral / bear 仓位细分
12. `open_ratio` 的复杂小数点优化

注意：
这些函数可以暂时保留在代码里，避免破坏依赖。
但它们不能参与新开仓实盘买入。
新开仓只允许 **Dragon + deep_water**。

---

## 三、买入逻辑

买入时间仍使用原策略 `09:32`。

只允许买入：

```python
entry_type == 'dragon_follow'
tpl == 'deep_water'
```

### 买入过滤条件

#### 1. 大盘下跌趋势不新开 Dragon

```python
if g.market_trend == 'down':
    continue
```

跳过原因日志：

```text
market_down_block
```

#### 2. 只买 deep_water

```python
if item.get('tpl') != 'deep_water':
    continue
```

跳过原因日志：

```text
not_deep_water
```

#### 3. dragon_score 最低要求为 0.70

```python
if dragon_score < 0.70:
    continue
```

跳过原因日志：

```text
score_below_0.70
```

#### 4. open_ratio 只做宽范围过滤

不要做细分参数优化。

允许区间：

```text
1.5% <= open_ratio <= 5.5%
```

逻辑：

```python
if open_ratio < 0.015 or open_ratio > 0.055:
    continue
```

跳过原因日志：

```text
open_ratio_out_of_range
```

#### 5. 个股趋势必须向上

保留原版 `is_stock_uptrend` 判断。
如果个股趋势不向上，跳过。

跳过原因日志：

```text
stock_trend_down
```

#### 6. 不使用 unified_score 阈值拦截 Dragon

不要再用以下内容参与买入或仓位调节：

```text
unified_score
env_weight
quality_multiplier
q_mult
CSI1000 分位权重
波动率权重
```

#### 7. 排序规则极简化

```python
score = dragon_score
```

按 `dragon_score` 从高到低排序。

---

## 四、仓位管理：2核心 + 利弗莫尔式尾盘赢家加仓

不要使用原版 DPM 动态扩仓。
不要使用 `q_mult` / `env_weight` / `quality_multiplier` 调仓。
不要为了提高仓位利用率去买第三只质量较低的票。

采用 **2核心 + 尾盘赢家加仓** 模型。

### 初始仓位

1. 最大初始持仓：2只 Dragon
2. Top1 初始仓位：35%
3. Top2 初始仓位：25%
4. 初始总仓位最多：60%
5. 单日最多新开：2只
6. `market_trend == 'down'` 时不新开 Dragon

### 总仓位限制

1. 总仓位上限：75%
2. 永远保留至少 25% 现金
3. 单只股票最大仓位：50%

### 仓位分配

Top1 Dragon：

```python
pos_ratio = 0.35
```

Top2 Dragon：

```python
pos_ratio = 0.25
```

不要用动态仓位。
不要根据市场环境进一步细分仓位。
不要新增更多仓位档位。

---

## 五、尾盘赢家加仓规则

加仓逻辑参考利弗莫尔原则：

```text
只向盈利仓加仓；
绝不向亏损仓加仓；
市场证明判断正确后再加仓；
不要摊平亏损。
```

### 加仓时间

只在尾盘检查加仓。
建议时间：

```text
14:40
```

可以注册一个 schedule，例如：

```python
check_livermore_tail_add
```

不要在早盘或盘中加仓。

原因：
A股 T+1，新加仓位当天不能卖，早盘加仓容易被下午跳水套住。
尾盘加仓可以等日内波动确认后再行动。

### 允许加仓条件

1. 持仓 `entry_type == dragon_follow`
2. 持仓 `tpl == deep_water`
3. 持仓至少 1 个交易日，买入当天不加仓
4. 当前持仓盈利 `pnl >= 10%`
5. 当前价格 `curr_price > MA5`
6. 当前价格 `curr_price > 当日开盘价`
7. `market_trend != down`
8. 没有触发 `dragon_stop_warning`
9. 当前不在 Dragon 连亏暂停状态
10. 每只 Dragon 最多加仓一次
11. 加仓后总仓位 `<= 75%`
12. 加仓后单票仓位 `<= 50%`

### 加仓金额

```python
winner_add_pos_ratio = 0.15
```

即加仓 15%。

### 冲高回落过滤

需要计算：

```python
intraday_drawdown = (day_high - curr_price) / day_high
```

如果：

```python
intraday_drawdown > 0.05
```

则不允许加仓。

跳过原因日志：

```text
intraday_pullback_too_large
```

### 其他加仓失败原因日志

```text
pnl_not_enough
below_ma5
below_day_open
market_down
already_added
same_day_no_add
stop_warning_active
single_stock_cap
total_position_cap
pause_active
```

### 加仓成功日志必须输出

```text
stock
current_pnl
curr_price
ma5
day_open
day_high
intraday_drawdown
current_position_ratio
add_position_ratio
after_position_ratio
total_position_ratio
reason=livermore_tail_add
```

---

## 六、Dragon 卖出逻辑：参考原版，但修正 -3.5% 容易被洗出去的问题

原版 Dragon 的核心逻辑保留：

1. 不赚钱跌破 MA5，失败退出。
2. 盈利达到保护阈值后跌破 MA5，卖半仓。
3. 半仓后跌破保护线，清剩余仓位。
4. 不做固定止盈，让大肉继续跑。

但修改硬止损：

```text
不要再让 -3.5% 变成立即全卖。
把 -3.5% 改成预警线。
真正确认失败后才卖。
```

### 新增或调整参数

```python
dragon_warn_stop = 0.035
dragon_confirm_stop = 0.05
dragon_profit_protect = 0.10
```

注意：
参数含义是正数，但判断 `pnl` 时是负收益。

### 卖出优先级

#### 1. 灾难确认止损

```python
if pnl <= -0.05:
    sell_all
    reason = 'dragon_confirm_stop'
```

这条任何时间都有效。

#### 2. 10:00 之前

```python
if pnl <= -0.035:
    meta['dragon_stop_warning'] = True
    reason = 'dragon_stop_warning'
    # 不下卖单
```

10:00 前仍然可以执行 `-5%` 灾难确认止损。

#### 3. 10:00 之后

```python
if pnl <= -0.035 and curr_price < MA5:
    sell_all
    reason = 'dragon_delayed_stop'
```

#### 4. 失败快跑

10:00 之后，如果：

```python
if pnl <= 0 and curr_price < MA5:
    sell_all
    reason = 'dragon_fail_fast'
```

注意：
10:00 前不要因为轻微跌破 MA5 就过早卖出。
Dragon 早盘要给波动空间。
但 `-5%` 灾难止损始终有效。

#### 5. 大肉保护

```python
if stage == 'full' and pnl >= 0.10 and curr_price < MA5:
    sell_half
    reason = 'dragon_profit_protect'
    stage = 'half'
```

#### 6. 半仓保护

```python
if stage == 'half':
    protect_line = max(prev_close, MA5)
    if curr_price < protect_line:
        sell_all
        reason = 'dragon_half_protect'
```

#### 7. 不要固定止盈

不要写成：

```text
盈利 5% 全卖
盈利 8% 全卖
盈利 10% 全卖
```

盈利后只用 MA5 保护，不要提前砍掉大肉。

---

## 七、minute_stop_loss_all 修改要求

原版 `minute_stop_loss_all` 对 Dragon 使用 `-3.5%` 立即止损，容易被洗出去。

BigMeat 版本要求：

对 `entry_type == dragon_follow`：

### 1. pnl <= -5%

```python
立即全卖
reason = 'dragon_confirm_stop'
```

### 2. pnl <= -3.5%

如果当前时间 `< 10:00`：

```python
只记录 warning
不卖
```

如果当前时间 `>= 10:00` 且 `curr_price < MA5`：

```python
全卖
reason = 'dragon_delayed_stop'
```

### 3. 不要在 10:00 前执行 dragon_fail_fast

### 4. 10:00 后才执行

```python
if pnl <= 0 and curr_price < MA5:
    全卖
    reason = 'dragon_fail_fast'
```

---

## 八、gap_down_stop_loss / confirm_gap_down_stop 修改要求

保留原版缺口止损延迟确认：

```text
09:31：只预警
09:35：再确认
```

如果恢复到 `-2%` 以上：

```text
取消止损
```

对于 Dragon：

1. `-3.5%` 不是立即卖出线，只是预警线。
2. `-5%` 才是确认止损线。
3. 如果 09:35 后仍然弱，并且符合 `dragon_confirm_stop` 或 `dragon_delayed_stop`，再卖。
4. 日志要明确写：

```text
gap_warning
gap_recovered
gap_confirm_stop
dragon_stop_warning
```

---

## 九、连亏保护：保持极简

不要复杂降仓。
不要做多级仓位衰减。
直接暂停。

规则：

```text
如果 Dragon 连续亏损 2 笔：
    暂停 Dragon 新开仓 2 个交易日。
```

暂停期间：

```text
不允许新买 Dragon。
已有持仓继续按卖出规则管理。
```

暂停结束：

```text
恢复正常。
consecutive_losses 可清零或在下一笔盈利后清零。
```

盈利一笔：

```text
清零 Dragon 连亏计数。
```

亏损定义：

```text
Dragon 平仓后最终收益 < 0。
```

日志输出：

```text
dragon_consecutive_losses
dragon_pause_days_left
pause_triggered
pause_released
```

---

## 十、需要重点修改的函数

请优先检查并修改这些函数。
如果当前文件函数名不同，请找到等价函数处理。

### 1. make_global_config

要求：

```text
max_total_positions 固定为 2 或 3，但初始新开最多 2
max_daily_new_positions 设为 2
dpm_enable = False
max_portfolio_position_ratio = 0.75
保留 dragon_enable = True
不允许 DPM 扩展到 5 只
```

### 2. make_strategy_A_config

要求：

```text
max_hold = 2
pos_ratio 默认不用动态，可保留 0.25 兼容
dragon_pos_ratio 不再动态使用
```

新增或明确：

```python
dragon_warn_stop = 0.035
dragon_confirm_stop = 0.05
dragon_profit_protect = 0.10
livermore_add_pos_ratio = 0.15
top1_pos_ratio = 0.35
top2_pos_ratio = 0.25
max_single_stock_ratio = 0.50
max_total_position_ratio = 0.75
```

### 3. get_A_mode

要求：

```text
删除复杂 panic / strict / DPM 对买入的影响
market_trend == down 时，不允许新开 Dragon
保留简单 normal / dragon 模式即可
不要新增复杂环境状态
```

### 4. select_candidates_A

要求：

```text
只返回 Dragon 候选
不再合并普通候选
不让 firstboard_lowopen / firstboard / weak_to_strong 参与实盘买入
可以保留它们的函数，但不接入最终买入列表
```

### 5. score_candidates_A

要求：

```text
只处理 entry_type == dragon_follow
只保留 tpl == deep_water
dragon_score < 0.70 跳过
open_ratio 不在 1.5%~5.5% 跳过
market_trend == down 跳过
个股趋势不向上跳过
不使用 unified_score 阈值
不使用 q/env/quality_multiplier 调仓
排序只按 dragon_score 降序
Top1 仓位 35%，Top2 仓位 25%
```

### 6. open_positions_A 或等价买入执行函数

要求：

```text
最多买入 Top1 和 Top2
若已有持仓，需要计算剩余可买数量
总仓位不超过 60% 初始仓
不触发 DPM
不买第三只新票
```

### 7. 新增或修改 check_livermore_tail_add

要求：

```text
14:40 执行
检查已有 Dragon 持仓
满足尾盘赢家加仓条件后，加仓 15%
每只最多加仓一次
加仓后总仓位 <= 75%
加仓后单股仓位 <= 50%
写清楚所有加仓成功/失败日志
```

### 8. evaluate_sell_signal_A

要求：

```text
重写 Dragon 卖出逻辑
不要让 -3.5% 立即全卖
-3.5% 是 warning
-5% 是 confirm stop
10:00 后跌破 MA5 且亏损，再确认失败
盈利 >=10% 后跌破 MA5 卖半仓
半仓后跌破 max(prev_close, MA5) 全卖
```

### 9. minute_stop_loss_all

要求：

```text
Dragon 不再使用 -3.5% 立即止损
按新的 warning / confirm / delayed stop 逻辑执行
普通持仓可保留原逻辑兼容，但 BigMeat 不再新开普通持仓
```

### 10. gap_down_stop_loss / confirm_gap_down_stop

要求：

```text
保留延迟确认思想
Dragon 使用 -5% 确认止损
-3.5% 只预警
恢复到 -2% 以上取消止损
```

### 11. after_market_close 或交易统计函数

要求：

```text
正确统计 Dragon 连亏
平仓后更新 consecutive_losses
亏损 2 笔触发暂停 2 个交易日
盈利后清零
输出日志
```

---

## 十一、日志要求

必须保留并新增以下日志。

### 1. 每日 Dragon 候选池数量

```text
Dragon候选池数量
top_score
market_trend
```

### 2. 每只候选过滤原因

```text
not_deep_water
market_down_block
score_below_0.70
open_ratio_out_of_range
stock_trend_down
```

### 3. 买入日志

```text
stock
dragon_score
open_ratio
tpl
rank
pos_ratio
market_trend
reason=dragon_bigmeat_buy
```

### 4. 加仓日志

```text
stock
current_pnl
curr_price
ma5
day_open
day_high
intraday_drawdown
current_position_ratio
add_position_ratio
after_position_ratio
total_position_ratio
reason=livermore_tail_add
```

### 5. 卖出日志

```text
stock
reason
pnl
stage
curr_price
ma5
是否 warning stop
是否 delayed stop
是否 confirm stop
```

### 6. 连亏保护日志

```text
dragon_consecutive_losses
dragon_pause_days_left
pause_triggered
pause_released
```

### 7. 每日报告中增加

```text
BigMeat模式是否开启
Dragon买入数量
Dragon加仓数量
Dragon卖出数量
当前总仓位
当前现金比例
```

---

## 十二、回测验证要求

修改完成后，至少做这些检查：

1. 确认新文件已创建。
2. 确认原文件没有被覆盖。
3. 输出修改了哪些函数。
4. 输出禁用了哪些买入入口。
5. 输出 Dragon 买入逻辑新旧对比。
6. 输出 Dragon 卖出逻辑新旧对比。
7. 输出仓位管理新旧对比。
8. 输出是否通过 python 语法编译检查。

语法检查示例：

```bash
python -m py_compile 战车A_BigMeat_Simple.py
```

如果可以跑回测，请分别跑：

1. 2026-01-01 到 2026-06-11
2. 2026-03-30 到 2026-06-11
3. 2026-04-01 到 2026-04-30 压力测试

重点输出：

```text
净值
累计收益
最大回撤
胜率
盈亏比
总交易
Dragon 胜率
Dragon 平均盈亏
最大单笔盈利
最大单笔亏损
加仓次数
加仓后盈利次数
加仓后亏损次数
尾盘加仓贡献收益
连亏暂停触发次数
```

---

## 十三、禁止事项

不要做以下事情：

1. 不要覆盖原文件。
2. 不要删除原版。
3. 不要新增复杂参数。
4. 不要新增多层市场分类。
5. 不要继续优化 `open_ratio` 小数点参数。
6. 不要把盈利 5% 或 8% 就全卖。
7. 不要重新接入 `firstboard_lowopen` / `firstboard` / `weak_to_strong` 实盘买入。
8. 不要恢复 DPM 动态扩仓。
9. 不要使用 `q_mult` / `env_weight` / `quality_multiplier` 调仓。
10. 不要为了提高胜率牺牲大肉。
11. 不要向亏损仓加仓。
12. 不要买入当天加仓。
13. 不要早盘加仓。
14. 不要让 `-3.5%` 直接全卖。
15. 不要满仓。
16. 不要让总仓位超过 75%。
17. 不要让单股仓位超过 50%。

---

## 十四、最终目标

生成一个更简单、更抗过拟合的 Dragon BigMeat 版本：

```text
Dragon-only；
deep_water-only；
Top1 35%；
Top2 25%；
尾盘赢家加仓 15%；
总仓位上限 75%；
单股上限 50%；
亏损不补仓；
-3.5% 预警；
-5% 确认止损；
10:00 后弱势跌破 MA5 才失败退出；
盈利 >=10% 后跌破 MA5 卖半仓；
半仓后跌破保护线清仓；
连亏 2 笔暂停 2 天；
不买普通首板；
不买首板低开；
不买弱转强；
不做复杂动态仓位；
保留大肉，让利润奔跑。
```
