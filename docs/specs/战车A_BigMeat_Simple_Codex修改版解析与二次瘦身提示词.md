# 战车A BigMeat Simple：Codex 修改版静态解析与下一轮提示词

## 一、这次上传文件的性质

这次上传的内容是修改后的策略代码，不是完整回测日志。

所以本次结论基于：

```text
静态代码审查
```

不是基于完整回测表现。

---

## 二、总体结论

这版 Codex 修改方向是对的，但只完成了第一层工程收敛。

### 已经做对的部分

| 项目 | 结论 |
|---|---|
| 明确聚宽网页版方向 | 基本完成 |
| QMT 自动检测 | 已去掉，直接 `g.is_qmt = False` |
| 实验组 | 已改为 `BIGMEAT_SIMPLE` |
| 旧 A1/A2/A3/A4 实验组 | 已删除 |
| 股票中文名缓存 | 已新增 `get_stock_name_cached` |
| 关键日志加 `name=` | 大部分已完成 |
| Dragon 候选池长日志 | 已改成 `BIGMEAT_POOL_TOP` TopN |
| 逐票过滤日志 | 已改为 `BIGMEAT_FILTER_SUMMARY` |
| 每日总结 | 已改成 `DAILY_SUMMARY` |
| 每日持仓 | 已增加 `POSITION` |
| TickEngine 聚宽执行 | 已通过 early return 禁止执行 |
| Dragon-only / deep_water-only | 仍然保持 |

### 仍然没做干净的部分

| 问题 | 严重程度 |
|---|---|
| 代码仍然非常臃肿，约 6300 行 | 中 |
| `TickSignalEngine` 大类仍然整段保留 | 中 |
| `_get_stock_list_A_impl` 旧首板/低开/弱转强逻辑仍然保留 | 中 |
| `compute_env_weights / compute_quality_multiplier / compute_unified_score` 仍然保留 | 中 |
| `_generate_daily_report` 里 return 后面还有大量死代码 | 中 |
| `tick_monitor / _jq_tick_engine_update` 里 return 后面还有大量死代码 | 中 |
| 顶部历史说明仍然写着首板低开、弱转强、QMT 等旧特性 | 中 |
| 少量日志仍然不是结构化格式 | 低到中 |
| 还不能确认聚宽网页版实际跑起来后的日志是否完全符合 | 需要回测验证 |

---

## 三、已经符合要求的证据

### 1. 实验组已改成 BIGMEAT_SIMPLE

代码中已经改成：

```python
EXPERIMENT_NAME = 'BIGMEAT_SIMPLE'

EXPERIMENTS = {
    'BIGMEAT_SIMPLE': {
        'global': {},
        'A': {},
    },
}
```

这说明旧实验组 `A1_DPM_CONSERVE / A2_TRENDCORE_FILTER / A3_DRAGON_RISK_FAST / A4_COMBO` 已经被清理掉。

---

### 2. 初始化已固定为聚宽网页版

现在 `initialize` 中已经不再自动 import QMT，而是直接：

```python
g.is_qmt = False
```

并输出：

```text
BIGMEAT_SIMPLE|platform=joinquant_web|status=starting
```

这符合“只服务聚宽网页版”的方向。

但建议再加一行更明确的中文日志：

```text
RUN_ENV|platform=聚宽网页版回测|qmt=0|local=0
```

这样阅读更直接。

---

### 3. 股票中文名称缓存函数已加入

代码已新增：

```python
get_stock_name_cached(stock)
```

逻辑包括：

1. `g.stock_name_cache` 缓存；
2. 优先 `get_current_data()[stock].name`；
3. 失败后 `get_security_info(stock).display_name`；
4. 再失败返回股票代码。

这个方向是正确的。

---

### 4. 关键日志大多已加 name 字段

例如：

```text
BIGMEAT_BUY|stock=...|name=...
DRAGON_SELL|stock=...|name=...
PARTIAL_SELL_CONFIRMED|stock=...|name=...
STAGE_CHANGE_CONFIRMED|stock=...|name=...
POSITION|stock=...|name=...
```

这已经明显提升阅读性。

---

### 5. 候选池日志已从全量长日志改成 TopN

现在已经看到：

```text
BIGMEAT_POOL_TOP|rank=...|stock=...|name=...|score=...|tpl=...|open_ratio=...
```

并且配置里有：

```python
bigmeat_pool_log_top_n = 5
bigmeat_verbose_pool_log = False
```

这个符合要求。

---

## 四、当前仍然需要修的地方

### 问题 1：代码瘦身还不彻底

虽然 Codex 禁用了很多旧逻辑，但大量旧代码仍然保留在文件里。

比如：

```text
TickSignalEngine 大类仍然完整保留
tick_monitor 仍然存在
_tick_engine_update 仍然存在
_tick_stop_loss_check 仍然存在
_tick_stage2_check 仍然存在
_get_stock_list_A_impl 仍然保留首板/低开/弱转强逻辑
compute_env_weights 仍然存在
compute_quality_multiplier 仍然存在
compute_unified_score 仍然存在
```

很多函数虽然已经不会被调用，但会造成：

1. 文件过长；
2. 后续 Codex 容易误改旧逻辑；
3. 聚宽编辑器阅读困难；
4. 以后排查 bug 容易混乱。

建议下一轮做“安全删除死代码”，不是继续简单 early return。

---

### 问题 2：顶部说明仍然误导

顶部注释仍然保留大量旧版本说明，比如：

```text
首板低开
首板高开
弱转强
QMT实盘
二次确认
二段买入
TickSignalEngine
统一评分
```

但当前目标是：

```text
聚宽网页版 BigMeat Simple
Dragon-only
deep_water-only
```

建议顶部注释只保留当前版本说明，历史长说明移动到归档或直接删除。

---

### 问题 3：部分旧日志仍然不是结构化格式

虽然大部分关键日志已经加了 `name=`，但仍然有一些旧式中文日志可能会输出：

```text
⚠️ xxx 分批卖出调整...
submit_exit_order(xxx): closeable=0...
TRADE_CLOSE_SKIP|stock=... 但没有 name
pending_exit 重试相关中文日志
```

建议统一改成：

```text
PARTIAL_SELL_ADJUST|stock=...|name=...|reason=lot_rounding|...
EXIT_SKIP|stock=...|name=...|reason=closeable_zero|...
TRADE_CLOSE_SKIP|stock=...|name=...|reason=invalid_exit_snapshot|...
PENDING_EXIT_RETRY|stock=...|name=...|retry_count=...
```

---

### 问题 4：`TickSignalEngine` 应该彻底从运行路径移除

目前 `_jq_tick_engine_update` 已经：

```python
return
```

`tick_monitor` 也已经：

```python
return
```

但是 `TickSignalEngine` 大类还在，`get_tick_engine` 还在，`_tick_engine_update` 还在。

如果确认没有任何运行路径需要这些函数，建议删除。

如果担心删除引起引用错误，则保留最小空壳：

```python
class TickSignalEngine:
    def __init__(self):
        self.enabled = False

def get_tick_engine():
    return TickSignalEngine()
```

但不要保留 L2、OBV、ATR、竞价评分等几百行旧逻辑。

---

### 问题 5：旧普通选股实现应删除或归档

现在：

```python
get_stock_list_A(context)
```

已经直接：

```python
return []
```

但下面仍有：

```python
_get_stock_list_A_impl(context)
```

里面包含首板低开、首板、弱转强等旧逻辑。

既然 BigMeat 不买这些，建议删除 `_get_stock_list_A_impl`，或者改名：

```python
_get_stock_list_A_impl_legacy_disabled
```

并确保没有任何地方调用。

---

### 问题 6：统一评分旧函数应删除

当前仍有：

```python
compute_env_weights
compute_quality_multiplier
compute_unified_score
update_unified_scoring_env
```

其中部分函数已经 early return，但相关配置和函数还在。

建议：

1. 如果完全不参与 BigMeat，删除；
2. 如果担心引用，保留最小空壳；
3. 删除配置里的 `unified_base_edge / unified_quality_mult_min / unified_quality_mult_max` 等旧字段。

---

## 五、当前不建议继续调参数

这版主要是工程层修改，下一步应该先做：

```text
聚宽网页版短回测 2026-03-01 到 2026-03-25
```

确认：

1. 中文名是否显示正常；
2. 日志是否清爽；
3. 没有函数未定义；
4. `TRADE_CLOSE`、`PARTIAL_SELL_CONFIRMED`、`STAGE_CHANGE_CONFIRMED` 仍正常；
5. 删除冗余后不影响买卖。

不要现在改：

```text
dragon_score
open_ratio
止损线
加仓线
仓位比例
```

---

# 下一轮 Codex 提示词

你现在在当前策略项目目录中。

请继续修改：

```text
战车A_BigMeat_Simple.py
```

本轮目标不是调参，不是优化收益，而是继续做“聚宽网页版工程收敛”。

上一轮修改已经完成了：

1. `EXPERIMENT_NAME = BIGMEAT_SIMPLE`
2. 删除旧实验组 A1/A2/A3/A4
3. 固定 `g.is_qmt = False`
4. 新增 `get_stock_name_cached`
5. 关键日志大多增加了 `name=`
6. Dragon 候选池改成 `BIGMEAT_POOL_TOP`
7. 每日总结改成 `DAILY_SUMMARY`
8. 每日持仓改成 `POSITION`
9. TickEngine 聚宽执行路径基本被 early return 禁用

但还存在这些问题：

1. 文件仍然很臃肿，约 6300 行；
2. `TickSignalEngine` 大类仍然保留大量 L2 / OBV / ATR / 竞价评分旧代码；
3. `_get_stock_list_A_impl` 仍然保留首板低开、首板、弱转强旧逻辑；
4. `compute_env_weights / compute_quality_multiplier / compute_unified_score` 仍然保留；
5. `_generate_daily_report` 里 return 后还有大量死代码；
6. `tick_monitor / _jq_tick_engine_update` 里 return 后还有大量死代码；
7. 顶部历史注释仍然写着 QMT、首板低开、弱转强、统一评分等旧内容，容易误导；
8. 少量日志仍然不是结构化格式，或缺少 `name=`。

---

## 一、本轮必须保持不变

不要改 BigMeat 核心逻辑：

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
盈利 >=10% 后跌破 MA5 卖半仓
半仓后跌破 max(prev_close, MA5) 清仓
不向亏损仓加仓
不买入当天加仓
FAST_MODE|minute_stop_schedule=10_points
FAST_MODE|skip_auction_score_jq=1
BIGMEAT_FILTER_SUMMARY
BIGMEAT_POOL_TOP
LIVERMORE_ADD_SUBMIT / CONFIRMED / CANCELLED
PARTIAL_SELL_CONFIRMED
STAGE_CHANGE_CONFIRMED
TRADE_CLOSE
DAILY_SUMMARY
POSITION
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
auction_score
TickEngine 竞价评分
QMT
9db / arena
```

---

## 二、清理顶部注释

请将文件顶部的大段历史说明压缩为当前版本说明。

保留：

```text
战车A BigMeat Simple
聚宽网页版回测专用
Dragon-only
deep_water-only
核心仓位和风控规则
当前版本变更记录
```

删除或移到“历史归档注释”的内容：

```text
QMT实盘
二次确认
二段买入
L2 Tick
首板低开
首板
弱转强
统一评分
DPM
旧 v7/v8/v9 大量历史说明
```

目标：

```text
文件顶部 100 行以内。
```

---

## 三、删除 TickSignalEngine 死代码

请搜索所有引用：

```text
TickSignalEngine
get_tick_engine
_jq_tick_engine_update
tick_monitor
_tick_engine_update
_tick_stop_loss_check
_tick_stage2_check
compute_auction_score_jq
update_l2_flow
update_tick_track
compute_atr
get_trailing_stop_price
is_volume_exhausted
get_quality_score
```

如果这些函数已经不在运行路径中，请删除。

如果删除会导致引用错误，则保留最小兼容空壳：

```python
class TickSignalEngine:
    def __init__(self):
        self.enabled = False
        self.is_qmt = False

def get_tick_engine():
    return TickSignalEngine()

def tick_monitor(context):
    return

def _jq_tick_engine_update(context):
    return
```

但不要保留几百行 L2 / OBV / ATR / 竞价评分逻辑。

---

## 四、删除普通选股旧实现

当前 BigMeat 只允许 Dragon + deep_water。

请处理：

```text
_get_stock_list_A_impl
prepare_A_stock_lists
compute_env_weights
compute_quality_multiplier
compute_unified_score
update_unified_scoring_env
```

如果没有任何运行路径调用它们，请删除。

如果有兼容引用，请保留最小空壳：

```python
def get_stock_list_A(context):
    return []

def update_unified_scoring_env(context):
    return
```

不要保留首板低开、首板、弱转强、统一评分的完整旧逻辑。

---

## 五、清理配置中的旧字段

请删除明显不参与 BigMeat 的配置项，包括但不限于：

```text
panic_scout_enable
panic_mild_threshold
panic_medium_threshold
panic_severe_threshold
unified_scoring_enable
unified_base_edge
unified_empty_threshold
unified_quality_mult_min
unified_quality_mult_max
lowopen_gap_min
lowopen_gap_max
lowopen_rp_fixed
lowopen_rp_dynamic_base
lowopen_rp_dynamic_scale
lowopen_min_money
lowopen_consecutive_days
lowopen_pos_ratio
normal_min_score
normal_min_open_ratio
normal_firstboard_bonus
normal_weak_bonus
strict_min_score
strict_min_open_ratio
strict_firstboard_bonus
strict_weak_bonus
```

删除前请确认这些字段没有被当前运行路径引用。

如果某些字段还被兼容函数引用，但函数已经不运行，也应一起删除或最小化。

---

## 六、统一剩余旧日志

把剩余非结构化日志改成结构化格式。

例如：

旧：

```text
⚠️ xxx 分批卖出调整...
submit_exit_order(xxx): closeable=0...
TRADE_CLOSE_SKIP|stock=... 但没有 name
pending_exit 重试中文日志
```

改成：

```text
PARTIAL_SELL_ADJUST|stock=...|name=...|reason=lot_rounding|old_amount=...|new_amount=...
EXIT_SKIP|stock=...|name=...|reason=closeable_zero
TRADE_CLOSE_SKIP|stock=...|name=...|reason=invalid_exit_snapshot|exit_amount=...|exit_price=...
PENDING_EXIT_RETRY|stock=...|name=...|retry_count=...
PENDING_EXIT_SKIP|stock=...|name=...|reason=limit_down
```

要求：

1. 只要日志涉及股票，就加 `name=`;
2. 删除 emoji；
3. 删除不必要的长中文句子；
4. 聚宽系统自动订单日志无法关闭，不用处理。

---

## 七、增加明确运行环境日志

初始化时输出：

```text
RUN_ENV|platform=joinquant_web|qmt=0|local=0|tick_engine=disabled
```

保留：

```text
BIGMEAT_SIMPLE|platform=joinquant_web|status=starting
EXPERIMENT|name=BIGMEAT_SIMPLE
```

---

## 八、验收标准

修改后先在聚宽网页版跑短回测：

```text
2026-03-01 到 2026-03-25
```

必须确认：

1. 聚宽网页版能编译；
2. 聚宽网页版能运行；
3. 能正常买入；
4. 能正常卖出；
5. `FAST_MODE` 仍然生效；
6. `BIGMEAT_POOL_TOP` 仍然有中文名；
7. `BIGMEAT_BUY` 仍然有中文名；
8. `DRAGON_SELL` 仍然有中文名；
9. `TRADE_CLOSE` 仍然有中文名；
10. `PARTIAL_SELL_CONFIRMED` 仍然有中文名；
11. `STAGE_CHANGE_CONFIRMED` 仍然有中文名；
12. `DAILY_SUMMARY` 正常输出；
13. `POSITION` 正常输出；
14. 不再出现 `TickEngine` 误导日志；
15. 不再出现长篇 Dragon 候选池旧日志；
16. 不再出现逐票 `BIGMEAT_FILTER`;
17. 不出现 `NameError` 或函数未定义错误。

然后再跑完整回测：

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
最终代码行数
删除了哪些函数
保留了哪些兼容空壳
```

---

## 九、最终输出报告

请输出：

1. 修改了哪些模块；
2. 删除了哪些旧函数；
3. 保留了哪些兼容空壳；
4. 文件行数从多少降到多少；
5. 哪些日志已加中文名称；
6. 哪些日志已改成结构化；
7. 是否通过聚宽网页版短回测；
8. 是否保持 BigMeat 核心逻辑不变。
