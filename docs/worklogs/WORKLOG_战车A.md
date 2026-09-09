# 战车A 策略工作记录

## 当前主文件

* 主策略文件：战车A龙头3.py
* 历史来源文件：战车A龙头3.txt
* 当前分支：v1.2.0-auction-prefilter
* 当前版本：v1.2.0-auction-prefilter

## 版本记录

### v1.1.0-trade-accounting

日期：2026-06-15

修改类型：

* 工程修复
* 交易统计账本修复
* 日志增强
* 不修改交易逻辑

修改内容：

1. 将策略主文件从 `战车A龙头3.txt` 同步为 `战车A龙头3.py`。
2. 增加版本号注释。
3. 修复 TRADE_CLOSE 在分批卖出后可能漏记部分卖出金额的问题。
4. 增加交易账本字段：

   * buy_amount_accum
   * sell_amount_accum
   * sell_value_accum
   * realized_pnl_accum
   * accounting_error
5. accounting_error=1 时，不再错误触发：

   * DRAGON_LOSS_CLASSIFY
   * dragon_consecutive_losses
   * DRAGON_PAUSE

保护声明：

本版本不修改：

* 买入条件
* 卖出条件
* 止损参数
* 止盈参数
* 仓位参数
* 加仓条件
* 选股逻辑
* run_daily / schedule_all 时间
* get_call_auction
* get_price
* set_order_cost

待验证事项：

1. 聚宽网页版能否正常运行。
2. 万邦德、协鑫能科类似分批卖出案例是否不再出现 -50%、-69% 假亏损。
3. TRADE_CLOSE 是否正确输出：

   * sell_value_accum
   * final_sell_value
   * total_sell_value
   * accounting_error
4. accounting_error=1 时是否跳过 DRAGON_PAUSE。
5. 收益曲线变化是否来自错误暂停修复，而不是买卖逻辑变化。

回测记录：

| 日期  | 版本                      | 区间  | NAV | 最大回撤 | 交易数 | 备注    |
| --- | ----------------------- | --- | --: | ---: | --: | ----- |
| 待填写 | v1.1.0-trade-accounting | 待填写 | 待填写 |  待填写 | 待填写 | 等聚宽回测 |

## 回撤方式

如果本版本出问题，可以回退：

1. 使用 Git 回退到上一个 commit。
2. 或复制 `战车A龙头3.txt` 旧版本。
3. 或切换回上一个分支。

## v1.1.1-profile-diagnosis

日期：2026-06-15

修改类型：

* 性能诊断
* 临时版本
* 不修改交易逻辑

修改内容：

1. 在 initialize(context) 中启用 enable_profile()。
2. 用于聚宽回测性能分析，查看耗时最高函数。
3. 本版本只用于短区间性能诊断，不作为正式策略版本。
4. 临时诊断版已完成性能定位。
5. 不作为正式回测版本，正式版本已移除 enable_profile。

建议回测区间：

2026-03-25 至 2026-04-15

性能分析重点：

* total time 最高的函数
* cumulative time 最高的函数
* 09:28 选股阶段是否最慢
* get_call_auction 是否最慢
* get_price / attribute_history 是否重复调用过多
* sync_position_meta_with_real_positions 是否因为账本修复变慢
* 日志输出是否占用明显时间

保护声明：

本版本不修改：

* 买入条件
* 卖出条件
* 止损参数
* 止盈参数
* 仓位参数
* 加仓条件
* 选股逻辑
* run_daily / schedule_all 时间

## v1.1.2-accounting-real-record-speedlog-safeperf

日期：2026-06-15

说明：

* v1.1.1-profile-diagnosis 已完成性能定位，正式版移除 enable_profile。
* profile 结果显示主要瓶颈在 09:28 Dragon 选股。
* 最大耗时来自 get_call_auction 逐票调用和 _get_dragon_stock_list_A_impl 的全市场处理。
* 本版本不做高风险 auction 预筛，只做等价性能优化。
* 修复 v1.1.0 只隔离错误但未补齐部分卖出账本的问题。
* 部分卖出订单提交成功后立即记录估算卖出金额。
* 使用订单唯一键防止重复累计。
* 降低普通日志输出。
* 保留所有交易关键日志和账本验证日志。
* 不修改交易逻辑。

建议验证区间：

2026-03-17 至 2026-04-18

重点验证：

* 002015.XSHE 协鑫能科
* 002082.XSHE 万邦德
* PARTIAL_SELL_CONFIRMED
* sell_amount_accum
* sell_value_accum
* TRADE_CLOSE
* TRADE_ACCOUNTING_WARN
* DRAGON_LOSS_CLASSIFY_SKIP
* DRAGON_PAUSE
* BIGMEAT_POOL
* BIGMEAT_POOL_TOP

成功标准：

1. 协鑫能科正常分批卖出后 accounting_error=0。
2. 万邦德正常分批卖出后 accounting_error=0。
3. sell_amount_accum 不再是 0。
4. sell_value_accum 不再是 0。
5. 不再出现 -69.50%、-50.52%、-46.54% 假亏损。
6. 普通日志数量减少。
7. 关键交易日志仍然完整。
8. 候选池结果不应因为安全性能优化发生主动变化。
9. 回测速度应比 profile 诊断版明显快，因为已移除 enable_profile。

## v1.1.3-accounting-actual-fill-fix

日期：2026-06-15

说明：

* 修复 v1.1.2 partial sell 按理论请求数量入账的问题。
* 典型问题是 650 理论卖出被聚宽调整为 600，但账本仍记录 650。
* 协鑫能科和万邦德均出现 sell_amount_accum + final_sell_amount 超过 buy_amount_accum 50 股。
* 本版本要求 partial sell 以实际成交数量或真实持仓减少数量入账。
* 不修改买入、卖出、止损、止盈、仓位、选股、get_call_auction、get_price 和性能逻辑。

建议验证区间：

2026-03-17 至 2026-04-18

重点验证：

* 002015.XSHE 协鑫能科
* 002082.XSHE 万邦德
* PARTIAL_SELL_CONFIRMED
* requested_amount
* actual_filled_amount
* previous_amount
* current_amount
* sell_amount_accum
* final_sell_amount
* buy_amount_accum
* TRADE_CLOSE
* TRADE_ACCOUNTING_WARN
* DRAGON_LOSS_CLASSIFY_SKIP

成功标准：

1. 协鑫能科 sell_amount_accum + final_sell_amount 不再超过 buy_amount_accum。
2. 万邦德 sell_amount_accum + final_sell_amount 不再超过 buy_amount_accum。
3. 正常分批卖出 accounting_error=0。
4. 不再出现 sell_amount_exceeds_buy。
5. 不修改交易路径和选股结果。

## v1.2.0-auction-prefilter

日期：2026-06-15

修改类型：

* Dragon 竞价预筛性能实验
* 策略性能优化
* 可能改变候选池和收益曲线

修改内容：

1. 在 `get_call_auction` 前新增 Dragon 日线预筛。
2. 预筛最多保留 250 只股票进入竞价接口调用。
3. 预筛只使用竞价前可获得的日线数据：

   * 近 5 日平均成交额
   * 近 10 日平均成交额
   * 近 5 日涨幅
   * 近 10 日涨幅
   * 收盘价距离近 20 日高点的位置
   * 近 10 日日均振幅
4. 保留原有 `ret3_top`、`money_top`、停牌/ST/上市时间过滤。
5. 进入竞价调用后，继续使用原 Dragon score、deep_water 模板和最终排序。
6. 新增：

   * `AUCTION_PREFILTER_SUMMARY`
   * `AUCTION_PREFILTER_TOP`
   * `AUCTION_PREFILTER_DROPPED_SAMPLE`

保护声明：

本版本不修改：

* v1.1.3 partial sell 实际成交数量账本
* `sync_position_meta_with_real_positions`
* `finalize_exited_position`
* `TRADE_CLOSE`
* `accounting_error`
* 买入条件
* 卖出条件
* 止损参数
* 止盈参数
* 仓位参数
* 加仓条件
* Dragon 评分公式
* deep_water 模板条件
* run_daily / schedule_all 时间
* set_order_cost

实验风险：

1. 日线预筛会缩小进入 `get_call_auction` 的股票范围。
2. 被预筛删除的股票不再参与后续 Dragon 竞价评分。
3. 候选池和收益曲线可能与 v1.1.3 不同。
4. 本版本必须先做短区间对照回测，再决定是否保留。

建议验证区间：

1. 2026-03-01 至 2026-04-18。
2. 通过后再跑 2026-03-01 至 2026-06-14。

成功标准：

1. `auction_call_count_after` 稳定落在 150 至 250 左右。
2. `get_call_auction` 调用数量明显下降。
3. `AUCTION_PREFILTER_TOP` 与被过滤样本可人工复核。
4. Dragon score、deep_water 和账本关键日志保持正常。
