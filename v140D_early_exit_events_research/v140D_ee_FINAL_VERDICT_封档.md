# v140D Early-Exit Events 研究 -- FINAL VERDICT / 封档

研究性质:research-only,全程未碰主策略/实盘/git/机制设计/调参。

## FINAL VERDICT(Wallace 拍板,2026-06-22)

**不引入 protection 机制,现有退出逻辑保持现状。封档,不再投入。**

对应 spec §5 命名空间:最接近 `VERDICT_still_outlier_driven_no_design`
(叠加 `VERDICT_subclass_heterogeneous_split` 的不可合并判断)。即:不进机制设计。

## 决策依据(Wallace 原文,含 CC 的准确性校注)

1. 盈利早退事件结构性稀缺(distinct 13:7 promotion + 6 ledger_early),靠 3 笔
   promotion 大肉撑、剔头部即翻负,无法支撑统计意义的机制设计。
2. 三子类语义异质(主动止盈 vs 被动快损)、时间窗口错配,不可合并。
3. captured_extra 显示现有 3% 止盈点位事后大多未损失上涨空间,即现有退出机制
   无需修正。
   **CC 校注(已更正)**:此条为【实测】。Wallace 已在聚宽以 proxy_mode=False
   跑出真实结果(下载于 v140D_ee_outputs.zip,解压在 v140D_ee_outputs/),CC 已
   核验:proxy_mode=False、cases captured_extra 100/125 非 0、data_quality 全 ok。
   关键数字均对得上真实 CSV:pv_half_exit_hold_half 盈利侧(promotion+ledger_early
   n=13)总和 +3.80%,剔最大 1 笔 fujing(+7.80%)翻负至 -4.00%;top3 为
   fujing/jiangte/hengtong;mergeability=divergent。
   (此前一版校注误称"未实测",系本地报告为 proxy 占位、未同步真实输出所致,现更正。)
4. protection 属下游逻辑补丁,与"保持策略简洁、聚焦因子有效性"的主方向相悖。

## 关键事实(来自 S3 真实账本/日志,已实证)

- 三子类:ee_promotion_block 7(S2 对账)/ ee_failed_trade 12(纯亏损)/
  ee_ledger_early 6(≥3% 门槛、去重后)。盈利侧 distinct = 13。
- ledger_early 三档门槛笔数 13/13/12,与 7 笔 promotion 重叠 7/7/6;新增非重叠
  恒为 6 笔大肉单(dragon_half_protect ≥11%)。盈利侧样本扩不动。
- failed-trade 全亏损,与盈利侧零重叠,退出语义不同。

## 资产与状态

- 主聚宽脚本 `research_v140D_ee_jq_counterfactual.py`:已完成并本地自检通过
  (py_compile / 无 BOM / 纯 ASCII / get_price 无 count / 5 变体逐字复用验收脚本 /
  verdict 判据已修正为"建议+人工确认"且不靠合并池凑样本)。**已由 Wallace 上聚宽
  以 proxy_mode=False 实跑**,真实输出 6 文件 + zip 在 `v140D_ee_outputs/`,
  FINAL VERDICT 已填入该处 `jq_ee_report.md`。
- S3 装载脚本 `research_v140D_ee_s3_load_events.py` + `ee_s3_outputs/`:已实跑,
  三档/重叠/分位数字真实可用。
- 因封档,脚本保留备查,不再继续 S4-S7 的实跑与分析。

## 后续

本研究线封档。若日后重启,从本档 + S3 交接物 + 验收脚本即可接手。
