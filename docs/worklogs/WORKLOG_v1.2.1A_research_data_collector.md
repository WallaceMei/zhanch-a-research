# v1.2.1A 研究环境数据采集版工作记录

## 当前文件

* 基线版本：v1.2.0-auction-prefilter
* 独立策略文件：战车A龙头3_v1.2.1A_research_data_collector.py
* 研究脚本：research_analyze_exit_add_rules.py
* 当前版本：v1.2.1A-research-data-collector
* 当前分支：v1.2.1A-research-data-collector

## v1.2.1A-research-data-collector

日期：2026-06-15

说明：

* v1.2.0 已通过多个区间验证。
* 当前不直接修改止盈止损和加仓逻辑。
* 本版本只输出聚宽研究环境需要的数据。
* 通过 `HOLD_SNAPSHOT`、`EXIT_EVENT`、`ADD_CANDIDATE_SNAPSHOT` 和
  `TRADE_ANALYTICS`，让研究环境离线扫描浮盈保护和提前加仓规则。
* 不改变任何真实交易逻辑。

新增日志：

1. `HOLD_SNAPSHOT`
2. `EXIT_EVENT`
3. `ADD_CANDIDATE_SNAPSHOT`
4. `LIVERMORE_ADD_BLOCKED`
5. `TRADE_ANALYTICS`
6. `DAILY_ANALYTICS`

新增研究字段：

* 入场预筛排名和分数
* 入场预筛日线因子
* 持仓最大/最小浮盈
* 浮盈回撤
* 入场后最高价
* 从最高价回撤
* 加仓成交数量和金额累计

研究脚本扫描：

* 浮盈保护：15/5、20/7、30/10
* 尾盘加仓：5/5/量比1.0
* 尾盘加仓：8/5/量比1.2
* 尾盘加仓：10/5/量比1.0且接近日内高点

保护声明：

本版本不修改：

* 买入条件
* 卖出条件
* 止损参数
* 止盈参数
* 加仓条件
* 仓位参数
* Dragon score
* deep_water
* prefilter 权重
* Top250
* get_call_auction
* 交易账本
* run_daily / schedule_all
* set_order_cost

验证重点：

1. v1.2.1A 与 v1.2.0 同区间交易路径应基本一致。
2. 新增日志正常输出。
3. 没有 `TRADE_ACCOUNTING_WARN`。
4. 没有 `accounting_error=1`。
5. 研究脚本可以解析导出的日志。

建议回测：

2026-03-01 至 2026-04-18
