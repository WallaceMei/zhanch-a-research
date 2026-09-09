# Codex 执行提示词：聚宽网页版 BigMeat 日志优化与代码瘦身

## 背景

当前策略文件：

```text
战车A_BigMeat_Simple.py
```

当前运行环境明确为：

```text
聚宽网页版回测
```

不是本地回测，不是 QMT 实盘，不是 9db / arena 同步环境。

本轮目标不是继续调收益参数，而是工程收敛：

1. 优化日志可读性；
2. 股票日志除了代码，还显示中文名称；
3. 减少无用日志；
4. 清理冗余模块、冗余函数、冗余配置；
5. 保证策略仍然能在聚宽网页版直接运行；
6. 不破坏 BigMeat 核心逻辑。

---

## 一、明确只支持聚宽网页版

请在代码注释和初始化日志里明确：

```text
本版本仅面向聚宽网页版回测。
不包含本地回测适配。
不包含 QMT 实盘适配。
不包含 9db / arena 同步。
```

不要要求我在本地执行：

```bash
python -m py_compile
```

如果 Codex 当前本地环境能做语法检查，可以做；但最终验收必须以：

```text
聚宽网页版能编译、能运行、能回测
```

为准。

---

## 二、日志中增加股票中文名称

当前日志里大量只有股票代码，例如：

```text
BIGMEAT_BUY|stock=002015.XSHE
DRAGON_SELL|stock=600549.XSHG
TRADE_CLOSE|stock=002009.XSHE
```

阅读性不够。

请统一改成：

```text
stock=002015.XSHE|name=协鑫能科
```

如果获取不到中文名，则：

```text
name=002015.XSHE
```

---

## 三、新增股票名称缓存函数

请新增一个聚宽网页版兼容的缓存函数：

```python
def get_stock_name_cached(stock):
    if not hasattr(g, 'stock_name_cache'):
        g.stock_name_cache = {}

    if stock in g.stock_name_cache:
        return g.stock_name_cache[stock]

    name = ''
    try:
        cd = get_current_data()
        if stock in cd and hasattr(cd[stock], 'name'):
            name = cd[stock].name
    except Exception:
        pass

    if not name:
        try:
            info = get_security_info(stock)
            name = getattr(info, 'display_name', '') or getattr(info, 'name', '')
        except Exception:
            name = ''

    if not name:
        name = stock

    g.stock_name_cache[stock] = name
    return name
```

要求：

1. 中文名称必须缓存；
2. 不要每条日志都重新 `get_security_info`；
3. 每天不需要清空股票名称缓存；
4. 必须兼容聚宽网页版；
5. 如果获取失败，不能报错，直接返回代码。

---

## 四、这些关键日志必须增加 name 字段

请给以下日志增加 `name=` 字段：

```text
BIGMEAT_POOL_TOP
BIGMEAT_BUY
BIGMEAT_BUY_SKIP
DRAGON_SELL
DRAGON_STOP
GAP_STOP
DRAGON_FAILFAST_CHECK
PARTIAL_SELL_CONFIRMED
STAGE_CHANGE_CONFIRMED
TRADE_CLOSE
DRAGON_LOSS_CLASSIFY
DRAGON_PAUSE
LIVERMORE_ADD_SKIP
LIVERMORE_ADD_SUBMIT
LIVERMORE_ADD_CONFIRMED
LIVERMORE_ADD_CANCELLED
POSITION
```

---

## 五、优化 Dragon 候选池日志

当前候选池日志太长，例如：

```text
【Dragon候选池】共12只: 1:603067.XSHG s=0.692 tpl=deep_water or=1.7% | ...
```

请改成摘要 + TopN 结构：

```text
BIGMEAT_POOL|count=12|top_score=0.6916|market_trend=up
BIGMEAT_POOL_TOP|rank=1|stock=603067.XSHG|name=xxx|score=0.692|tpl=deep_water|open_ratio=1.7%
BIGMEAT_POOL_TOP|rank=2|stock=600590.XSHG|name=xxx|score=0.688|tpl=trend_core|open_ratio=0.3%
```

默认只输出 Top5：

```python
bigmeat_pool_log_top_n = 5
bigmeat_verbose_pool_log = False
```

如果 `bigmeat_verbose_pool_log=True`，才允许输出完整候选池。

---

## 六、减少无用日志

### 保留核心日志

只保留这些策略自定义关键日志：

```text
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
PARTIAL_SELL_CONFIRMED
STAGE_CHANGE_CONFIRMED
TRADE_CLOSE
DRAGON_LOSS_CLASSIFY
DRAGON_PAUSE
LIVERMORE_ADD_SKIP
LIVERMORE_ADD_SUBMIT
LIVERMORE_ADD_CONFIRMED
LIVERMORE_ADD_CANCELLED
POSITION
DAILY_SUMMARY
DIAG
```

### 删除或降级为 debug 的日志

请删除或改为 debug：

```text
重复的订单对象日志
重复的候选池全量长日志
逐票 BIGMEAT_FILTER
重复的 Pre 长日志
重复的 Post-Auction 长日志
无用的 TickEngine 说明日志
不参与决策的旧模块日志
```

聚宽系统自动输出的订单日志无法关闭的话，可以不处理。但策略自己不要重复打印订单对象。

---

## 七、每日总结优化

当前每日总结类似：

```text
持仓数=1 净值=1.1609 回撤=0.00% 胜率=0.0% 盈亏比=0.00 总交易=3
```

请改成结构化日志：

```text
DAILY_SUMMARY|date=2026-03-13|nav=1.1609|daily_ret=...|max_drawdown=...|positions=1|closed_trades=3|win_rate=...|payoff=...
```

如果胜率和盈亏比还在修复中，字段可以保留，但不要输出容易误导的中文句子。

---

## 八、每日持仓日志增加中文名称

每天收盘后只输出一次当前持仓：

```text
POSITION|stock=002015.XSHE|name=xxx|entry_type=dragon_follow|amount=...|cost=...|price=...|pnl=...|stage=...
```

要求：

1. 只输出当前持仓；
2. 每天最多输出一次；
3. 放在 `after_market_close` 或等价函数；
4. 不要每分钟输出持仓。

---

## 九、清理冗余模块和函数

当前策略是 BigMeat Simple，且只在聚宽网页版回测中运行。

请清理明显冗余的模块、函数、配置。

---

### 不得参与买入的入口

以下入口不得参与买入，可以删除买入路径或保留最小空壳兼容：

```text
firstboard_lowopen
firstboard
weak_to_strong
panic_scout
DPM
q_mult
env_weight
quality_multiplier
unified_score
strict_bear 复杂仓位
QMT 二次确认
QMT 二段买入
L2 Tick 大单流
ATR trailing stop
volume_exhaustion
auction_score_jq
```

注意：

1. 删除前先搜索所有引用；
2. 不要因为删除函数导致聚宽运行报错；
3. 如果删除风险大，就保留最小兼容空壳，但不要参与决策；
4. 本轮优先“瘦身不破坏”，不要大规模重写。

---

## 十、TickSignalEngine 处理原则

当前环境是聚宽网页版回测，不是 QMT 实盘。

处理原则：

```text
TickSignalEngine 中 QMT/L2/逐笔/盘口相关代码可以删除或不初始化。
聚宽回测中 auction_score_jq 已被 FAST_MODE 跳过。
```

如果删除风险大，可以保留类定义，但不要调度、不要执行、不要打印无用日志。

建议：

```python
if not g.is_qmt:
    engine.enabled = False
```

并删除或降级这类日志：

```text
[TickEngine] 聚宽模式: 竞价近似+分钟线降级(L2/Tick不可用)
```

因为当前 BigMeat 聚宽网页版版本已经不用 TickEngine，输出这句会误导。

---

## 十一、EXPERIMENTS 清理

当前仍有旧实验组：

```text
A1_DPM_CONSERVE
A2_TRENDCORE_FILTER
A3_DRAGON_RISK_FAST
A4_COMBO
```

这些容易误触发旧逻辑。

请改为只保留：

```python
EXPERIMENT_NAME = 'BIGMEAT_SIMPLE'

EXPERIMENTS = {
    'BIGMEAT_SIMPLE': {
        'global': {},
        'A': {},
    }
}
```

日志输出：

```text
EXPERIMENT|name=BIGMEAT_SIMPLE
```

不要再输出乱码符号。

---

## 十二、不要破坏 BigMeat 核心逻辑

必须保持：

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
LIVERMORE_ADD_SUBMIT / CONFIRMED / CANCELLED
PARTIAL_SELL_CONFIRMED
STAGE_CHANGE_CONFIRMED
TRADE_CLOSE
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
TickEngine 竞价评分
```

---

## 十三、聚宽网页版验收标准

修改完成后，在聚宽网页版回测中先跑：

```text
2026-03-01 到 2026-03-25
```

必须满足：

1. 股票相关关键日志都带中文名称；
2. 不再输出无用的全量候选池长日志；
3. 不再输出逐票 `BIGMEAT_FILTER`，只输出 `BIGMEAT_FILTER_SUMMARY`；
4. `FAST_MODE` 仍然生效；
5. `TickEngine` 不再输出误导性的聚宽模式日志；
6. `EXPERIMENT_NAME` 改为 `BIGMEAT_SIMPLE`；
7. 聚宽网页版能编译通过；
8. 策略仍能正常买入和卖出；
9. `TRADE_CLOSE`、`PARTIAL_SELL_CONFIRMED`、`STAGE_CHANGE_CONFIRMED` 仍然存在；
10. 不要因为删冗余导致函数未定义。

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
日志是否已带中文名称
冗余模块清理了哪些
```

---

## 十四、最终输出报告

请输出：

1. 是否明确为聚宽网页版版本；
2. 是否给股票日志增加中文名称；
3. 新增了哪个股票名称缓存函数；
4. 删除或禁用了哪些冗余模块；
5. 保留了哪些兼容空壳；
6. 是否移除了误导性的 TickEngine 聚宽日志；
7. 是否将实验组改为 `BIGMEAT_SIMPLE`；
8. 是否减少无用日志；
9. 是否通过聚宽网页版短回测；
10. 是否保持 BigMeat 核心逻辑不变。
