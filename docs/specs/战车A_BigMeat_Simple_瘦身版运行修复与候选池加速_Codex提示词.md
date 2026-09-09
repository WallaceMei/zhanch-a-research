# 战车A BigMeat Simple 最新瘦身版解析与下一轮修复提示词

## 一、文件性质

本次上传的是最新瘦身后的策略代码，不是回测日志。

本次解析基于：

```text
静态代码检查
```

不是完整回测结果。

---

## 二、总体结论

这版 Codex 修改比上一版明显干净很多，已经从约 6300 行压缩到约 3500 行，方向是对的。

### 已经完成得比较好的部分

| 项目 | 结果 |
|---|---|
| 顶部历史注释压缩 | 已完成 |
| 明确聚宽网页版回测专用 | 已完成 |
| `EXPERIMENT_NAME` 改为 `BIGMEAT_SIMPLE` | 已完成 |
| 旧实验组 A1/A2/A3/A4 | 已删除 |
| QMT / TickEngine / L2 / ATR / OBV | 基本删除 |
| `TickSignalEngine` 大类 | 已删除 |
| `_get_stock_list_A_impl` 旧普通选股 | 已删除 |
| `compute_env_weights / compute_quality_multiplier / compute_unified_score` | 已删除 |
| 股票中文名称缓存 | 已保留 |
| 日志 `name=` 字段 | 大部分已保留 |
| `BIGMEAT_POOL_TOP` | 已保留 |
| `DAILY_SUMMARY` | 已保留 |
| `POSITION` | 已保留 |
| `PARTIAL_SELL_CONFIRMED` | 已保留 |
| `STAGE_CHANGE_CONFIRMED` | 已保留 |
| `TRADE_CLOSE` | 已保留 |
| 语法 AST 解析 | 通过 |

---

## 三、最严重问题：`timedelta` 未定义

当前代码顶部是：

```python
import datetime
```

但是在 `get_base_stock_universe` 里使用了：

```python
cutoff_date = context.current_dt.date() - timedelta(days=g.cfg['new_stock_days'])
```

这里的 `timedelta` 没有导入。

这会导致聚宽网页版运行到选股宇宙时直接报：

```text
NameError: name 'timedelta' is not defined
```

### 修复方式二选一

方案 A：

```python
from datetime import timedelta
```

方案 B，更推荐，因为当前已经 `import datetime`：

```python
cutoff_date = context.current_dt.date() - datetime.timedelta(days=g.cfg['new_stock_days'])
```

建议用方案 B，避免新增导入风格混乱。

---

## 四、第二个问题：Dragon 候选池仍有两个速度瓶颈

虽然代码整体瘦身了，但 `get_dragon_stock_list_A` 里仍有两个旧速度瓶颈：

### 1. 每只股票循环调用 `attribute_history` 算 avg_range

当前逻辑仍然在 seed 循环里逐票调用：

```python
attribute_history(stock, 10, '1d', ['high', 'low', 'close'])
```

这会拖慢聚宽网页版回测。

建议改成批量：

```python
get_price(list(seed), end_date=prev_date, frequency='daily',
          fields=['high', 'low', 'close'], count=10, panel=False)
```

然后 groupby code 计算：

```python
avg_range = mean((high - low) / close)
```

### 2. v3 模式下仍然查询上一日竞价 `prev_auc_vol`

当前 `dragon_score_mode='v3'`，但代码仍然每只股票调用：

```python
get_call_auction(stock, start_date=start_prev, end_date=end_prev)
```

而 v3 评分没有使用 `prev_auc_vol`。

建议：

```python
if g.cfg.get('dragon_score_mode') == 'v1':
    查询 prev_auc_vol
else:
    prev_auc_vol = 0.0
```

这不会改变 v3 结果，但会减少大量 RPC。

---

## 五、第三个问题：仍有少量旧字段和兼容函数，但可以接受

目前仍保留了一些轻量兼容字段或函数，例如：

```text
panic_yesterday_ret
A_dd_cooldown_active
deadlock_flat_days
check_orphan_positions
orphan_sweeper_execute
update_portfolio_nav_and_brake
update_daily_risk_switch_yesterday
```

这些不一定需要立刻删除。

原因：

1. 它们仍被当前运行路径引用；
2. 删除可能带来 `NameError`；
3. 它们不像 TickEngine 那样庞大；
4. 当前优先级是先让聚宽网页版稳定跑通。

建议暂时保留，等完整回测稳定后再继续瘦身。

---

## 六、第四个问题：`refresh_limit_up_cache` 等旧涨停函数已经删除，方向对

当前检查结果显示：

```text
refresh_limit_up_cache: 已删除
get_limit_up_stocks: 已删除
get_touch_limit_up_stocks: 已删除
_get_stock_list_A_impl: 已删除
TickSignalEngine: 已删除
compute_unified_score: 已删除
```

这说明普通首板、弱转强、统一评分和 TickEngine 这类旧模块已经基本从代码层清掉。

---

## 七、第五个问题：顶部说明已经合格

顶部现在已经变成：

```text
战车A BigMeat Simple
聚宽网页版回测专用
Dragon-only / deep_water-only
不启用 QMT、TickEngine、L2、ATR、OBV、竞价评分或本地报告
```

这比上一版干净很多。

---

## 八、当前不建议继续大删

这版已经瘦身比较明显，不建议继续大规模删除。

下一轮只做：

```text
1. 修复 timedelta 未定义；
2. 优化 Dragon 候选池两个速度瓶颈；
3. 保留现有结构化日志；
4. 跑聚宽网页版短回测验证。
```

不要再让 Codex 继续大范围删函数。

---

# 下一轮 Codex 修复提示词

你现在在当前策略项目目录中。

请继续修改：

```text
战车A_BigMeat_Simple.py
```

本轮不是调参，不是继续大规模瘦身，而是修复当前瘦身版的运行问题和两个回测速度瓶颈。

当前版本已经完成：

1. 顶部注释压缩；
2. 明确聚宽网页版回测专用；
3. `EXPERIMENT_NAME = BIGMEAT_SIMPLE`；
4. 删除旧实验组 A1/A2/A3/A4；
5. 删除 `TickSignalEngine` 大类；
6. 删除 `_get_stock_list_A_impl`；
7. 删除统一评分旧函数；
8. 保留股票中文名缓存；
9. 保留 `BIGMEAT_POOL_TOP / DAILY_SUMMARY / POSITION`；
10. 保留 `PARTIAL_SELL_CONFIRMED / STAGE_CHANGE_CONFIRMED / TRADE_CLOSE`。

但是还存在一个会直接报错的问题：

```python
cutoff_date = context.current_dt.date() - timedelta(days=g.cfg['new_stock_days'])
```

当前文件只写了：

```python
import datetime
```

没有导入：

```python
timedelta
```

所以聚宽网页版运行时会出现：

```text
NameError: name 'timedelta' is not defined
```

---

## 一、必须修复：timedelta 未定义

请把：

```python
cutoff_date = context.current_dt.date() - timedelta(days=g.cfg['new_stock_days'])
```

改成：

```python
cutoff_date = context.current_dt.date() - datetime.timedelta(days=g.cfg['new_stock_days'])
```

不要新增复杂逻辑。

---

## 二、优化 Dragon 候选池 avg_range 逐票查询

当前 `get_dragon_stock_list_A` 中仍然对 seed 里的股票逐票调用：

```python
attribute_history(stock, 10, '1d', ['high', 'low', 'close'])
```

这会拖慢聚宽网页版回测。

请改成批量取数：

```python
range_df = get_price(
    list(seed),
    end_date=prev_date,
    frequency='daily',
    fields=['high', 'low', 'close'],
    count=10,
    panel=False
)
```

然后按 `code` 分组计算：

```python
avg_range = ((high - low) / close).mean()
```

写入：

```python
per_stock[stock]['avg_range'] = avg_range
```

后续循环中不要再逐票调用 `attribute_history` 来算 `avg_range`。

如果某只股票数据缺失：

```python
avg_range = 0.0
```

保持原有过滤逻辑：

```python
if avg_range > g.cfg.get('dragon_max_avg_daily_range', 0.08):
    continue
```

---

## 三、v3 模式下跳过无用 prev_auc_vol 查询

当前配置：

```python
dragon_score_mode = 'v3'
```

但是代码仍然每只股票查询上一交易日竞价：

```python
get_call_auction(stock, start_date=start_prev, end_date=end_prev)
```

v3 评分不使用 `prev_auc_vol`，所以这是无用 RPC。

请改成：

```python
prev_auc_vol = 0.0

if g.cfg.get('dragon_score_mode', 'v3') == 'v1' and prev_prev_date is not None:
    查询上一交易日竞价 prev_auc_vol
```

要求：

1. v3 模式下不查询上一日竞价；
2. 不改变 v3 评分结果；
3. v1 兼容可以保留。

---

## 四、不要继续大删函数

当前版本已经大幅瘦身。

本轮不要再删除这些仍被引用的轻量函数：

```text
check_orphan_positions
orphan_sweeper_execute
update_portfolio_nav_and_brake
update_daily_risk_switch_yesterday
get_base_stock_universe
```

除非你确认没有任何引用。

当前优先级是：

```text
聚宽网页版能稳定跑通
```

不是继续压缩行数。

---

## 五、必须保持不变

不得修改以下 BigMeat 核心：

```text
Dragon-only
deep_water-only
Top1 35%
Top2 25%
初始仓位上限 60%
总仓位上限 75%
单股上限 50%
-3.5% 预警
-5% 确认止损
10:00 后弱势跌破 MA5 才失败退出
盈利 >=10% 后跌破 MA5 卖半仓
半仓后跌破 max(prev_close, MA5) 清仓
不向亏损仓加仓
不买入当天加仓
Dragon 连续硬亏 2 笔暂停 2 个交易日
```

不得删除或破坏以下日志：

```text
RUN_ENV
EXPERIMENT
FAST_MODE
BIGMEAT_POOL
BIGMEAT_POOL_TOP
BIGMEAT_FILTER_SUMMARY
BIGMEAT_BUY
BIGMEAT_BUY_SKIP
DRAGON_STOP
DRAGON_SELL
GAP_STOP
DRAGON_FAILFAST_CHECK
LIVERMORE_ADD_SUBMIT
LIVERMORE_ADD_CONFIRMED
LIVERMORE_ADD_CANCELLED
PARTIAL_SELL_CONFIRMED
STAGE_CHANGE_CONFIRMED
TRADE_CLOSE
DAILY_SUMMARY
POSITION
DIAG
```

不得重新接入：

```text
firstboard_lowopen
firstboard
weak_to_strong
DPM
q_mult
env_weight
quality_multiplier
auction_score
TickEngine
QMT
9db / arena
```

---

## 六、聚宽网页版验收

修改后在聚宽网页版先跑短回测：

```text
2026-03-01 到 2026-03-25
```

必须确认：

1. 不再出现 `NameError: timedelta is not defined`；
2. `RUN_ENV|platform=joinquant_web|qmt=0|local=0|tick_engine=disabled` 正常输出；
3. `FAST_MODE|minute_stop_schedule=10_points` 正常输出；
4. `BIGMEAT_POOL_TOP` 正常输出且带中文名称；
5. `BIGMEAT_FILTER_SUMMARY` 正常输出；
6. 能正常买入；
7. 能正常卖出；
8. `PARTIAL_SELL_CONFIRMED` 正常输出；
9. `STAGE_CHANGE_CONFIRMED` 正常输出；
10. `TRADE_CLOSE` 正常输出；
11. 没有函数未定义错误；
12. 回测速度比逐票 `attribute_history + prev_auc` 更快。

如果短回测通过，再跑完整回测：

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
盈利交易数
亏损交易数
平均盈利
平均亏损
加仓确认次数
加仓取消次数
部分止盈确认次数
stage 切换确认次数
连亏暂停次数
是否仍有报错
是否仍有无用长日志
```

---

## 七、最终输出报告

请输出：

1. 是否修复 `timedelta` 未定义；
2. 是否批量化 `avg_range`；
3. v3 模式下是否跳过上一日竞价查询；
4. 是否保持 BigMeat 核心逻辑不变；
5. 是否通过聚宽网页版短回测；
6. 短回测中是否有任何报错。
