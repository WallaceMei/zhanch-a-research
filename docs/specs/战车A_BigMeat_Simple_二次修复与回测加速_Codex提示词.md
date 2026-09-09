# Codex 执行提示词：战车A BigMeat Simple 二次修复与回测加速

请继续修复当前文件：

```text
战车A_BigMeat_Simple.py
```

我已经跑了一轮 `2026-03-01` 到 `2026-06-11` 的回测日志，发现当前版本方向基本正确，但存在几个工程问题和逻辑过严问题。

这次不要重新设计策略，不要改成复杂参数优化。

本次只修复以下问题：

1. 回测速度太慢；
2. 胜率、盈亏比、交易统计不正确；
3. Dragon 连亏保护太敏感；
4. `initial_position_cap` 导致有仓位却无法补第二只核心 Dragon；
5. 尾盘赢家加仓从未成功触发，条件过严；
6. 聚宽回测中 TickEngine 竞价评分仍在运行，拖慢回测。

---

## 一、保持不变的核心逻辑

以下内容必须保持不变：

```text
Dragon-only
deep_water-only
不买 firstboard_lowopen
不买 firstboard
不买 weak_to_strong
Top1 初始仓位 35%
Top2 初始仓位 25%
初始仓位上限 60%
总仓位上限 75%
单股上限 50%
-3.5% 预警，不立即卖
-5% 确认止损
盈利 >=10% 后跌破 MA5 卖半仓
半仓后跌破 max(prev_close, MA5) 清仓
不向亏损仓加仓
不买入当天加仓
```

---

## 二、修复回测速度慢

当前日志显示聚宽回测里每天仍然执行：

```text
[TickEngine] 竞价评分: 12只
```

但 BigMeat 版买入排序只使用 `dragon_score`，不使用 `auction_score`。

### 新增配置

请新增：

```python
backtest_fast_mode = True
enable_auction_score_backtest = False
bigmeat_verbose_filter_log = False
```

### 关闭聚宽回测 TickEngine 竞价评分

在 `post_auction_prepare` 或等价函数里：

```python
if g.is_qmt == False and g.cfg.get('backtest_fast_mode', True):
    跳过 engine.compute_auction_score_jq(stock, context)
```

日志输出一行：

```text
FAST_MODE|skip_auction_score_jq=1
```

要求：

1. QMT 实盘可以保留 TickEngine。
2. 不要影响 QMT。
3. 聚宽回测默认跳过竞价 TickEngine 评分。

### 缩减 minute_stop_loss_all 调度

当前聚宽回测下 `minute_stop_loss_all` 每 2 分钟运行一次，回测太慢。

在 `backtest_fast_mode` 下，将聚宽回测的 `minute_stop_loss_all` 调度改为固定检查点：

```text
09:40
09:50
10:00
10:15
10:30
11:00
13:30
14:00
14:30
14:50
```

要求：

1. `09:31` gap warning 保留。
2. `09:35` gap confirm 保留。
3. `11:20` / `14:50` `strategy_sell_only` 保留。
4. `14:40` `check_livermore_tail_add` 保留。
5. QMT `tick_monitor` 不要删除。
6. 聚宽回测 fast mode 下不要每 2 分钟注册 `minute_stop_loss_all`。

日志输出：

```text
FAST_MODE|minute_stop_schedule=10_points
```

---

## 三、缓存 MA5，减少 attribute_history 调用

当前 `_estimate_intraday_ma5` 每次都会调用：

```python
attribute_history(stock, 4, '1d', ['close'])
```

这会让 `minute_stop_loss_all` 和 `check_livermore_tail_add` 反复请求数据，拖慢回测。

### 新增缓存变量

请新增：

```python
g.ma5_base_cache = {}
g.ma5_base_cache_date = None
```

每天 `morning_prepare` 清空缓存。

### 新增函数

新增：

```python
_get_ma5_base_sum(stock, context)
```

逻辑：

1. `cache_key = stock`
2. 如果当天缓存存在，直接返回。
3. 否则调用：

```python
attribute_history(stock, 4, '1d', ['close'])
```

4. 缓存最近 4 日 close 之和。
5. `_estimate_intraday_ma5(stock, curr_price, context)` 使用：

```python
ma5 = (base_sum + curr_price) / 5
```

要求：

1. 同一天同一只股票只取一次 `attribute_history`。
2. 不改变 MA5 计算口径。
3. 不要逐次打印日志，避免刷屏。

---

## 四、修复过滤日志刷屏

当前 `BIGMEAT_FILTER` 逐票打印过多，会拖慢回测。

如果：

```python
bigmeat_verbose_filter_log == False
```

则不要逐票打印：

```text
BIGMEAT_FILTER|stock=...
```

改为统计每种过滤原因数量，最后输出一行：

```text
BIGMEAT_FILTER_SUMMARY|not_deep_water=...|score_below_0.70=...|open_ratio_out_of_range=...|stock_trend_down=...|market_down_block=...
```

如果：

```python
bigmeat_verbose_filter_log == True
```

则保留逐票日志。

默认：

```python
bigmeat_verbose_filter_log = False
```

---

## 五、修复 initial_position_cap 买入仓位 bug

日志显示，在已有持仓时，新的合格 Dragon 经常因为 `initial_position_cap` 被全部跳过。

目标逻辑：

1. 初始仓位上限仍然是 60%。
2. 如果当前没有 Dragon 持仓：
   - Top1 买 35%
   - Top2 买 25%
3. 如果当前已有一只 Dragon，且当前初始仓位约 35%：
   - 允许再买一只，仓位使用剩余 initial capacity。
   - 例如 `max_initial_position_ratio=0.60`，当前已用 `0.35`，剩余 `0.25`，则允许新买 25%。
4. 不要因为候选原始 `rank=1` 需要 35%，就把它跳过。
5. 应该根据当前剩余初始仓位动态确定新买仓位：

```python
remaining_initial = max_initial_position_ratio - current_position_ratio

if remaining_initial >= 0.15:
    pos_ratio = min(candidate_default_pos_ratio, remaining_initial)
    允许买入
else:
    跳过，reason=initial_position_cap
```

6. 买入日志增加：

```text
current_position_ratio
remaining_initial
actual_pos_ratio
```

7. 如果已有一只持仓，第二只买入应优先使用 25% 或 `remaining_initial`，而不是固定 35%。

保持：

```text
总仓位上限 75%
单股上限 50%
最多初始持仓 2 只
```

---

## 六、修复胜率、盈亏比和连亏统计口径

当前日志显示胜率长期为 `0.0%`，但实际存在 `dragon_profit_protect` 盈利卖出。这说明统计口径不正确。

请修复：

### 1. 建仓时记录完整交易统计字段

每只股票建仓时记录：

```text
entry_value
entry_amount
total_buy_value
total_sell_value
realized_pnl_value
added_times
partial_sell_records
```

### 2. sell_half 时更新已实现收益

每次 `sell_half` 时：

1. 记录实际卖出金额；
2. 记录实际卖出数量；
3. 记录卖出收益；
4. 更新：

```python
meta['realized_pnl_value']
```

### 3. sell_all 清仓时计算整笔交易收益

最终 `sell_all` 清仓时，计算整笔交易的加权收益：

```python
trade_ret = total_realized_pnl_value / total_buy_value
```

不要只用最后一次 `sell_all` 的 `pnl` 来判断整笔交易盈亏。

例子：

```text
一只票先 +14% 卖半，后面剩余仓 -0.77% 清仓。
这不能简单记为亏损交易。
应按整笔加权收益判断。
```

### 4. 胜率统计

```text
trade_ret > 0 算 win
trade_ret < 0 算 loss
trade_ret == 0 可以不计或算 flat
```

### 5. 盈亏比统计

用整笔 `trade_ret` 统计，不要用最后一笔退出 `pnl`。

### 6. Dragon 连亏保护

Dragon 连亏保护也必须基于整笔 `trade_ret`，不是最后一次卖出 `pnl`。

### 7. 清仓日志

输出：

```text
TRADE_CLOSE|stock=...|entry_type=dragon_follow|trade_ret=...|realized_pnl_value=...|total_buy_value=...|win=1/0
```

---

## 七、修复 Dragon 连亏保护过敏

当前 `-0.29%` 的 `dragon_fail_fast` 也会触发连续亏损计数，太敏感。

新规则：

只有以下情况才计入 Dragon 硬亏损：

1. 整笔 `trade_ret <= -1.5%`
2. 或者最终退出 reason 属于：
   - `dragon_confirm_stop`
   - `dragon_delayed_stop`
3. 或者整笔 `trade_ret < 0` 且连续出现两笔小亏，可以只累计 `soft_loss_count`，不立刻触发暂停。

建议实现：

```python
hard_loss = trade_ret <= -0.015 or final_reason in ('dragon_confirm_stop', 'dragon_delayed_stop')

if hard_loss:
    dragon_consecutive_losses += 1
else:
    if trade_ret < 0:
        dragon_soft_losses += 1
    if trade_ret > 0:
        dragon_consecutive_losses = 0
        dragon_soft_losses = 0
```

暂停触发：

```python
if dragon_consecutive_losses >= 2:
    pause 2 days
```

不要让 `-0.29%`、`-0.30%` 这种轻微 `fail_fast` 直接触发 Dragon 断路器。

日志输出：

```text
DRAGON_LOSS_CLASSIFY|stock=...|trade_ret=...|final_reason=...|hard_loss=0/1|soft_loss_count=...|consecutive_losses=...
```

---

## 八、适度放宽 dragon_fail_fast，减少轻微洗出

当前 `dragon_fail_fast` 次数太多，很多是 `-0.29%`、`-0.30%` 这种轻微破 MA5。

保持 `-5%` 确认止损不变。

### fail_fast 新触发规则

10:00 后才允许 `fail_fast`。

触发条件改为：

条件 A：

```python
pnl <= -0.015 and curr_price < MA5
```

或者条件 B：

```python
pnl <= 0 and 连续两次检查 curr_price < MA5
```

也就是说：

```text
轻微亏损只破一次 MA5，不立刻卖。
需要连续两次确认弱势。
```

### 新增 meta 字段

需要在 `meta` 中记录：

```python
meta['below_ma5_count']
```

逻辑：

```python
if curr_price < MA5:
    below_ma5_count += 1
else:
    below_ma5_count = 0
```

触发：

```python
if pnl <= -0.015 and curr_price < MA5:
    sell_all reason=dragon_fail_fast

elif pnl <= 0 and below_ma5_count >= 2:
    sell_all reason=dragon_fail_fast_confirmed
```

日志输出：

```text
DRAGON_FAILFAST_CHECK|stock=...|pnl=...|below_ma5_count=...|reason=...
```

---

## 九、修复尾盘赢家加仓一直不触发的问题

当前回测中 `LIVERMORE_ADD` 成功次数为 0，说明条件过严。

保持原则：

```text
只给盈利仓加仓；
不向亏损仓加仓；
买入当天不加仓；
每只最多加一次；
总仓位 <=75%；
单票 <=50%。
```

但放宽两个条件。

### 1. market_down 不再绝对禁止已有赢家加仓

新规则：

```text
如果 market_trend == 'down'：
    普通情况不加仓；
    但如果已有持仓 pnl >= 15%，curr_price > MA5，intraday_drawdown <= 0.05：
        允许小额加仓 10%，不是 15%。
```

参数：

```python
winner_add_pos_ratio = 0.15
winner_add_pos_ratio_market_down = 0.10
winner_add_pnl_threshold = 0.10
winner_add_pnl_threshold_market_down = 0.15
```

### 2. 不要强制 curr_price > day_open

原因：

```text
高开后横盘的强趋势票可能 curr_price < day_open，但仍然是强势赢家。
```

把条件：

```python
curr_price > day_open
```

改为：

```python
intraday_drawdown <= 0.05
and curr_price > MA5
```

可选增强：

```python
if curr_price < day_open but curr_price >= day_high * 0.95:
    仍允许
```

### 失败原因日志保留

```text
below_ma5
intraday_pullback_too_large
market_down_weak_winner
single_stock_cap
total_position_cap
already_added
same_day_no_add
pnl_not_enough
```

### 成功日志

```text
LIVERMORE_ADD|stock=...|current_pnl=...|add_ratio=...|market_trend=...|intraday_drawdown=...|reason=livermore_tail_add
```

---

## 十、保留 BigMeat 核心，不要乱改

不要改这些：

1. 不要重新接入 `firstboard_lowopen` / `firstboard` / `weak_to_strong`。
2. 不要恢复 DPM 动态扩仓。
3. 不要恢复 `q_mult` / `env_weight` / `quality_multiplier` 调仓。
4. 不要修改 `dragon_score` 最低 `0.70`。
5. 不要修改 `open_ratio` `1.5%~5.5%`。
6. 不要修改 `deep_water-only`。
7. 不要把盈利 5% 或 8% 就全卖。
8. 不要把 `-3.5%` 改回立即止损。
9. 不要让总仓位超过 75%。
10. 不要让单股仓位超过 50%。

---

## 十一、检查和输出

修改完成后运行：

```bash
python -m py_compile 战车A_BigMeat_Simple.py
```

最后输出报告：

1. 是否通过语法检查。
2. 修改了哪些函数。
3. 是否关闭聚宽回测 TickEngine 竞价评分。
4. 是否减少 `minute_stop_loss_all` 调度。
5. 是否加入 MA5 缓存。
6. 是否将 `BIGMEAT_FILTER` 改为摘要日志。
7. 是否修复 `initial_position_cap`。
8. 是否修复整笔交易胜率 / 盈亏比统计。
9. 是否修复连亏保护口径。
10. 是否放宽尾盘赢家加仓。
11. 是否仍保持 Dragon-only / deep_water-only。
12. 是否仍保持 Top1 35%、Top2 25%、尾盘赢家加仓。
13. 是否仍保持 `-3.5%` 预警、`-5%` 确认止损。

---

## 十二、如果可以，请重新回测并输出

如果可以，请重新跑一次：

```text
2026-03-01 到 2026-06-11
```

输出：

```text
期末净值
最大回撤
胜率
盈亏比
总交易
Dragon closed trades
dragon_fail_fast 次数
dragon_confirm_stop 次数
dragon_delayed_stop 次数
dragon_profit_protect 次数
LIVERMORE_ADD 成功次数
连亏暂停触发次数
回测运行耗时
```

---

## 十三、本次修复目标总结

本次不是调参，不是追求立即提高收益，而是先把当前 BigMeat 版本的工程问题修正：

```text
1. 跑得更快；
2. 统计更准；
3. 连亏保护不过敏；
4. 有剩余仓位时能买第二只核心 Dragon；
5. 真正允许强赢家尾盘加仓；
6. 不破坏 Dragon-only / deep_water-only / 抓大肉核心逻辑。
```
