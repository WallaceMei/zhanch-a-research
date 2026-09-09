# 战车A v1.4.0A shadow rotation fullB 工作记录

## 当前实验文件

* 实验策略文件：战车A龙头3_v1.4.0A_shadow_rotation_fullB.py
* 来源稳定文件：战车A龙头3.py
* 当前版本：v1.4.0A-shadow-rotation-fullB
* 修改类型：独立实验版

## 版本说明

### v1.4.0A-shadow-rotation-fullB

日期：2026-06-15

目标：

1. 基于当前稳定策略复制出独立实验版，不覆盖主策略文件。
2. 新增 WATCH_POOL，对未买入的 deep_water 龙头候选进行 3 个交易日影子跟踪。
3. 新增 Rule D deep_water 趋势确认卫星仓逻辑。
4. 使用 Full-B 仓位结构：核心仓 70%，卫星仓 15% x 2，总仓位上限 100%。
5. 卫星仓买入、替换、退出复用现有下单和账本流程，不新写账本。

## 核心逻辑

### WATCH_POOL

收盘后从当日 Dragon deep_water 候选中记录未买入、未持仓、未 pending 的股票：

* signal_date
* signal_price
* signal_rank
* signal_score
* signal_source
* signal_entry_type
* expire_days = 3

### Rule D deep_water 确认

确认检查在 14:45 执行，只使用当时可见数据：

* ret_from_signal >= 5%
* day_ret >= 5%
* 1.0 <= volume_ratio_vs_prev <= 2.0
* ma5_distance <= 10%
* close_to_day_high >= 0.97
* 非涨停
* 非停牌 / 非 ST
* signal_entry_type == deep_water

### Full-B 仓位

* 核心仓：2 个，合计 70%
* 卫星仓：2 个，每个 15%
* 总仓位上限：100%
* 不绕过原策略已有风控和暂停逻辑

### 替换规则

卫星仓已满时，只允许替换最弱卫星仓，不替换核心仓。

替换判断：

* 优先考虑亏损、跌破 MA5、持有多日不涨的卫星仓。
* 不替换当前盈利最多且趋势最强的卫星仓。
* 新候选强度必须明显高于最弱卫星仓。

## 新增日志

* WATCH_POOL_ADD
* WATCH_POOL_EXPIRE
* WATCH_POOL_REMOVE
* SHADOW_CONFIRM_CHECK
* SHADOW_CONFIRM_PASS
* SHADOW_CONFIRM_SKIP
* SHADOW_BUY_SUBMIT
* SHADOW_BUY_CONFIRMED
* SHADOW_REPLACE_DECISION
* SHADOW_REPLACE_SKIP
* SHADOW_REPLACE_EXECUTE
* SHADOW_EXIT_SIGNAL
* SHADOW_EXIT_SUBMIT
* SHADOW_EXIT_CONFIRMED
* SHADOW_DAILY_SUMMARY

## 保护声明

本实验版不修改原稳定文件：

* 战车A龙头3.py
* 战车A龙头3.txt
* WORKLOG_战车A.md
* research_shadow_rotation_2plus2.py

本实验版保留并复用：

* v1.1.3 partial sell 实际成交数量账本修复
* submit_exit_order
* finalize_exited_position
* sync_position_meta_with_real_positions
* TRADE_CLOSE
* accounting_error 保护

本实验版不新增：

* 新账本
* 未来函数
* 新的 Dragon score
* 新的 deep_water 条件
* 新的 get_call_auction 逻辑

## 待验证事项

1. 聚宽网页版能否正常编译和运行。
2. WATCH_POOL_ADD 是否每日正常记录未买入 deep_water 候选。
3. SHADOW_CONFIRM_PASS 是否只出现在 Rule D deep_water 条件满足时。
4. 卫星仓买入后是否有 SHADOW_BUY_CONFIRMED。
5. 卫星仓退出后是否有 SHADOW_EXIT_CONFIRMED 和正常 TRADE_CLOSE。
6. 是否没有 TRADE_ACCOUNTING_WARN。
7. 是否没有 accounting_error=1。
8. 最大回撤是否明显扩大。
9. 卫星仓收益是否为正贡献。

## 建议回测区间

先跑：

* 2026-01-01 至 2026-06-14

再跑：

* 2025-07-01 至 2026-06-14

重点对比：

* v1.2.0 主策略
* v1.3.0A 普涨低开直接清仓实验版
* v1.4.0A shadow rotation fullB 实验版
