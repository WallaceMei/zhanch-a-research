# Codex 执行提示词：修复 BigMeat 交易统计与尾盘加仓确认 Bug

请继续修复当前文件：

```text
战车A_BigMeat_Simple.py
```

本次不要调策略参数，不要重新设计买入卖出逻辑。

最新回测已经确认：

1. `FAST_MODE` 已生效；
2. `skip_auction_score_jq` 已生效；
3. `BIGMEAT_FILTER_SUMMARY` 已生效；
4. `initial_position_cap` 基本已修复；
5. 买入日志已包含 `current_position_ratio / remaining_initial / actual_pos_ratio`；
6. 净值已经能跑到 `1.2377`。

但是还有两个严重 bug 必须修复：

1. `TRADE_CLOSE` 全部被统计成 `-100%`；
2. `LIVERMORE_ADD` 在订单未成交或被涨停取消时，也被错误标记为成功。

---

## 一、修复 TRADE_CLOSE 全部 -100% 的统计 bug

当前日志里所有 `TRADE_CLOSE` 都变成：

```text
trade_ret=-100.00%
realized_pnl_value=-total_buy_value
win=0
```

这是错误的。

典型日志：

```text
TRADE_CLOSE|stock=002009.XSHE|entry_type=dragon_follow|trade_ret=-100.00%|realized_pnl_value=-23096.00|total_buy_value=23096.00|win=0
```

### 问题判断

`finalize_exited_position` 中计算 `exit_amount` 时，可能使用了：

```text
pending_exit_requested_amount
或
last_amount
```

但清仓完成后，`last_amount` 很可能已经变成 0。

所以：

```python
final_sell_value = exit_price * exit_amount
```

变成：

```python
final_sell_value = 0
```

最终：

```python
realized_pnl_value = 0 - total_buy_value
```

导致整笔交易被算成 `-100%`。

### 修复要求

#### 1. 在 submit_exit_order 或卖出下单前记录退出前持仓数量

请记录：

```python
meta['pending_exit_amount_before'] = 当前持仓 total_amount
meta['pending_exit_closeable_amount_before'] = 当前可卖数量
meta['pending_exit_requested_amount'] = 本次实际请求卖出的数量
```

#### 2. 如果是清仓

`pending_exit_requested_amount` 应该等于退出前的 `total_amount` 或 `closeable_amount`，不要等成交后再从 `last_amount` 取。

#### 3. finalize_exited_position 中处理异常

如果：

```python
pending_exit_requested_amount <= 0
```

不要用：

```python
last_amount = 0
```

计算。

应该回退使用：

```python
pending_exit_amount_before
```

#### 4. final_sell_value 计算

应该使用：

```python
final_sell_value = exit_price * actual_exit_amount
```

其中：

```python
actual_exit_amount
```

不能是 0，除非订单确实没有成交。

#### 5. partial sell 和 final sell 都要累计

需要累计：

```text
total_sell_value
realized_pnl_value
partial_sell_records
```

#### 6. 整笔 trade_ret 计算

整笔收益应该是：

```python
trade_ret = (total_sell_value - total_buy_value) / total_buy_value
```

不要只用最后一次 `sell_all` 的 `pnl` 判断整笔交易盈亏。

#### 7. 盈利卖半后的整笔统计

如果一只票先盈利卖半，后面剩余仓清仓，必须按整笔加权收益计算。

不要出现：

```text
先 +14% 卖半，最后剩余仓小亏清仓，整笔被记成 -100%
```

#### 8. 修复后日志要求

修复后不应该再出现大量：

```text
trade_ret=-100.00%
```

除非真的归零亏完，但普通股票交易不可能出现这种情况。

### 新日志格式

请输出：

```text
TRADE_CLOSE|stock=...|entry_type=dragon_follow|trade_ret=...|total_buy_value=...|total_sell_value=...|realized_pnl_value=...|win=1/0
```

---

## 二、修复 LIVERMORE_ADD 未成交却标记成功的问题

当前日志里出现：

```text
已经涨停，市价买单取消
订单取消完成
LIVERMORE_ADD|stock=600378.XSHG|...
```

这说明加仓订单被取消了，但代码仍然打印 `LIVERMORE_ADD`，并且很可能把 `added_times` 标成已加仓。

这是严重错误。

---

### 修复要求

#### 1. 不要只因为 order_value 返回非 None 就认为加仓成功

在 `check_livermore_tail_add` 中，下加仓单后，不能只因为 `order_value` 返回非 None 就认为成功。

#### 2. 订单取消时不能输出成功日志

如果订单被取消、涨停买单取消、委托未成交，不允许打印：

```text
LIVERMORE_ADD
```

#### 3. 未确认成交前不允许设置加仓成功状态

不允许设置：

```python
meta['added_times'] += 1
meta['pending_add'] = True
meta['livermore_added'] = True
```

除非确认成交。

---

## 三、建议的加仓确认机制

### 1. 下单前记录

下单前记录：

```python
meta['pending_add'] = True
meta['pending_add_amount_before'] = 当前持仓数量
meta['pending_add_target_value'] = add_value
meta['pending_add_date'] = today
meta['pending_add_price'] = curr_price
```

但不要立刻认为加仓成功。

可以输出：

```text
LIVERMORE_ADD_SUBMIT|stock=...|add_ratio=...|reason=livermore_tail_add
```

---

### 2. 在 sync_position_meta_with_real_positions 或等价成交同步函数中确认

如果：

```python
pending_add == True
```

则检查：

```python
old_amount = pending_add_amount_before
new_amount = 当前持仓 total_amount
```

如果：

```python
new_amount > old_amount
```

说明加仓成交。

然后：

```python
added_amount = new_amount - old_amount
added_value = added_amount * 实际成交价或当前成本变化估算
```

更新：

```python
total_buy_value
added_times += 1
pending_add = False
```

输出：

```text
LIVERMORE_ADD_CONFIRMED|stock=...|added_amount=...|added_value=...|added_times=...
```

---

### 3. 如果未成交或订单取消

如果当天收盘仍没有增加持仓，或检测到订单取消：

```python
pending_add = False
```

不要增加：

```python
added_times
```

不要设置：

```python
livermore_added
```

输出：

```text
LIVERMORE_ADD_CANCELLED|stock=...|reason=no_position_increase_or_order_cancelled
```

如果是涨停取消，可以输出：

```text
LIVERMORE_ADD_CANCELLED|stock=...|reason=limit_up_cancelled
```

---

### 4. already_added 的条件

只有确认成交后，后续才允许：

```text
reason=already_added
```

如果订单被涨停取消，不应该让第二天显示 `already_added`。

---

## 四、修复连亏保护依赖错误 trade_ret 的问题

当前因为 `TRADE_CLOSE` 全部 `-100%`，`DRAGON_LOSS_CLASSIFY` 也全部变成：

```text
hard_loss=1
```

导致连亏保护失真。

请在修复 `trade_ret` 后重新计算：

```python
hard_loss = trade_ret <= -0.015 or final_reason in ('dragon_confirm_stop', 'dragon_delayed_stop')
```

注意：

1. 如果 `trade_ret` 是正数，即使最后退出 reason 不是很好，也必须按整笔收益判断。
2. `dragon_profit_protect` 不应该因为统计错误被算成 hard_loss。
3. 连亏暂停必须基于修复后的 `trade_ret`。

---

## 五、修复日报胜率和盈亏比

当前日志每天显示：

```text
胜率=0.0%
盈亏比=0.00
```

这是 `trade_ret` 错误导致的。

修复后：

1. 胜率必须基于 `TRADE_CLOSE` 的整笔 `trade_ret`。
2. 盈亏比必须基于：

```text
平均盈利交易收益 / 平均亏损交易绝对值
```

3. 如果有盈利交易，胜率不能继续长期为 0。

---

## 六、保留当前已经修好的内容，不要回退

必须保留：

```text
FAST_MODE|minute_stop_schedule=10_points
FAST_MODE|skip_auction_score_jq=1
BIGMEAT_FILTER_SUMMARY
current_position_ratio / remaining_initial / actual_pos_ratio 买入日志
Dragon-only
deep_water-only
Top1 35%
Top2 25%
初始仓位上限 60%
总仓位上限 75%
单股上限 50%
-3.5% 预警
-5% 确认止损
盈利 >=10% 后跌破 MA5 卖半仓
半仓后跌破 max(prev_close, MA5) 清仓
不向亏损仓加仓
不买入当天加仓
```

不要重新接入：

```text
firstboard_lowopen
firstboard
weak_to_strong
DPM
q_mult
env_weight
quality_multiplier
```

---

## 七、验收标准

修改完成后运行：

```bash
python -m py_compile 战车A_BigMeat_Simple.py
```

然后跑短回测：

```text
2026-03-01 到 2026-03-25
```

验收要求：

1. 日志仍然出现：

```text
FAST_MODE|minute_stop_schedule=10_points
FAST_MODE|skip_auction_score_jq=1
BIGMEAT_FILTER_SUMMARY
```

2. `TRADE_CLOSE` 不应该全部是 `-100%`。

3. `002015` 这种盈利保护卖出的票，不应该被记成 `-100%` 亏损。

4. 如果加仓单因为涨停取消：
   - 不允许输出 `LIVERMORE_ADD_CONFIRMED`
   - 不允许增加 `added_times`
   - 下一天不应该因为这次取消单显示 `already_added`

5. 如果加仓真实成交：
   - 必须输出 `LIVERMORE_ADD_CONFIRMED`

6. 日报胜率和盈亏比要能正常变化，不应该一直是：

```text
胜率=0.0%
盈亏比=0.00
```

---

## 八、最终输出报告

请输出：

1. 修复了哪些函数；
2. 是否通过语法检查；
3. `TRADE_CLOSE` 是否正常；
4. `LIVERMORE_ADD` 是否只在成交后确认；
5. 是否保持 BigMeat 核心逻辑不变；
6. 短回测中是否还出现 `trade_ret=-100.00%`；
7. 短回测中是否还出现加仓取消但显示成功的问题。

---

## 九、本轮目标

本轮不是调参，而是修复成交同步和统计口径：

```text
第一优先：修 TRADE_CLOSE -100%
第二优先：修 LIVERMORE_ADD 假成功
第三优先：让胜率、盈亏比、连亏保护恢复可信
第四优先：重新跑 2026-03-01 到 2026-06-11
```

现在不要碰选股参数。先把统计修准，否则胜率、盈亏比、连亏保护、加仓贡献全部都是假数据。
