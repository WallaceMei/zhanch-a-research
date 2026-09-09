# v1.4.0D OOS Regime Diagnosis Report

## 1. 核心诊断回答 (Key Diagnostic Answers)

**Q1: OOS 期间的主要损失来源于哪类入场类型？**
根据 `oos_entry_type_exit_reason_breakdown.csv`：
- 在 12 笔失败交易中，**8 笔来源于 `dragon_follow` (核心跟随)**，4 笔来源于 `shadow_satellite` (卫星仓)。
- 纯 OOS 新建仓的 10 笔中，`dragon_follow` 占据 6 笔，`shadow_satellite` 占据 4 笔。
结论：主要损失来源于核心仓位跟随 (`dragon_follow`) 失败。

**Q2: 失败交易的退出原因是什么？是否出现了集中性的快速止损？**
- 是的，出现了集中性快速止损。纯 OOS 期间（10 笔）的 **fast_loss_ratio 高达 70.0%**。
- `dragon_fail_fast` 触发了 6 次，`minute_stop_loss` 触发了 4 次。
结论：入场后动能迅速衰竭，触发了极端的快速止损机制。

**Q3: 这些失败交易发生时的市场环境（Regime / Market Trend）是怎样的？**
根据 `oos_failed_trade_regime_tags.csv` 和 `oos_daily_market_context.csv`：
- OOS 期间系统级 Regime 判定主要为：`bull` (19天), `neutral` (15天)。`bear` 仅有 5 天。
- Market Trend 主要为：`sideways` (17天), `up` (13天)。
- Micro Regime 极度偏向：**`neutral_crowding` (27天)**。
结论：系统未能识别出实质性的下行趋势，反而将持续的横盘震荡和微观拥挤（Crowding）误判为“可交易的牛市/震荡市” (bull / neutral)，导致持续发出做多信号。

**Q4: 监控池（Watch Pool）在此期间的信号质量如何？**
根据 `oos_watch_pool_quality_probe.csv`：
- 共有 144 次 `WATCH_POOL_ADD` 动作，平均 `signal_score` 为 **0.713**。
- `SHADOW_CONFIRM_CHECK` 发生了 150 次，其中 `SKIP` 143 次，仅有 7 次 `PASS`。
结论：信号打分普遍偏低（均值约 0.71），大量信号被加入监控池但绝大多数（95%+）未能通过二阶确认（Shadow Confirm），说明底层 Alpha 信号质量在 OOS 期间严重恶化。

**Q5: 是否存在明显的 “Regime Mismatch” 现象？**
- **存在严重错配**。策略在设计上依赖于强趋势环境，但在 OOS 期间，环境演变为 `neutral_crowding` 和 `sideways`，此时高位股容易出现 A 杀。系统底层的宽泛 Regime 判定未能阻断这种微观结构的恶化，导致在高位震荡拥挤期持续高位接盘。

**Q6: 是否有证据表明特定类型的信号（例如 Deep Water）失效？**
- 从 Watch Pool 提取的数据看，绝大多数添加都是 `deep_water` 类型的信号。在拥挤震荡市中，Deep Water 捞底往往捞到的是真正破位下跌的股票，导致 `minute_stop_loss` 和 `dragon_fail_fast` 大量触发。

**Q7: OOS 失败是否仅仅是因为参数设置不当，还是逻辑机制存在结构性缺陷？**
- **结构性缺陷**。OOS 胜率降至 20%，Fast loss 比例达 70%，且信号确认通过率极低（7/150）。这表明底层的多因子打分模型和 Regime 过滤器在该市场结构下完全失效。单纯调整参数（如放宽/收紧打分、调整止损线）无法改变该结构下的负向期望。

**Q8: 结论是什么？**
- **判定结果：C 级 (Structural Decay - Start Regime & Signal Redesign)**。
- v1.4.0D 暴露了现有 Alpha 逻辑在 `neutral_crowding` 环境下的脆弱性。必须冻结该版本，并在下一代（如 v1.5 或 v2）中引入更灵敏的微观结构阻断机制或降维重构打分模型。

## 2. 诊断产物列表
- `oos_trade_typology_check.csv`: 基础分类核对。
- `oos_entry_type_exit_reason_breakdown.csv`: 入场/退出分布和快速止损率。
- `oos_daily_market_context.csv`: 每日大盘环境追踪。
- `oos_failed_trade_regime_tags.csv`: 失败交易的环境归因。
- `oos_watch_pool_quality_probe.csv`: 信号池与确认通过率探针。
- `regime_hypothesis_matrix.csv`: 失效假设矩阵。

## 3. 最终建议 (Final Recommendations)
1. **维持 v1.4.0D 冻结状态**，绝对禁止实盘。
2. 承认当前 Regime 过滤器在识别“高位震荡+微观拥挤”时的迟钝性。
3. 下阶段研发（若有）应转向：
   - A. 引入更严苛的微观拥挤惩罚（Micro-Crowding Penalty）。
   - B. 重新审视 `deep_water` 入场逻辑，防范破位陷阱。
   - C. 提高 SHADOW_CONFIRM 的确认阈值，或将其作为全局过滤条件。
