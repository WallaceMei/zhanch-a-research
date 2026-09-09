# 战车A 全版本策略档案（v1.4.0D交接版）

生成时间：2026-06-21 01:24:53

本档案按用户要求只做只读扫描与档案整理。除本 Markdown 档案及扫描记录外，不修改任何策略逻辑文件。

## 0. 项目总览与权限边界

- 项目目录：`D:\Code\JQ\战车A`
- 当前研究阶段：`v1.4.0C -> P1~P5 -> D candidate -> v1.4.0D observer`
- 当前不是主线策略。
- 当前不是实盘版。
- 不放宽 `deep_water`。
- 不扩大仓位。
- 不自动参数搜索。
- 不修改主策略。
- 不执行 `git add` / `git commit`。
- 不联网。
- 不运行完整回测。

## 1. 全目录文件扫描摘要

下表来自 `Get-ChildItem -Recurse` 与 Python 只读扫描。完整扫描也写入 `战车A_全版本只读扫描记录.md`。

| 文件名 | 路径 | 是否存在 | 大小(bytes) | 修改时间 | 类型 | 初步用途判断 |
| --- | --- | --- | --- | --- | --- | --- |
| analyze_jq_experiment_logs.py | analyze_jq_experiment_logs.py | 是 | 5901 | 2026-05-30 22:06:36 | 分析脚本 | 回测日志/分析日志 |
| analyze_v14B_log_compare.py | analyze_v14B_log_compare.py | 是 | 46964 | 2026-06-17 13:08:33 | 分析脚本 | 回测日志/分析日志 |
| DeepSeek_CC_v14B_fix日志分析执行方案.md | DeepSeek_CC_v14B_fix日志分析执行方案.md | 是 | 6651 | 2026-06-17 12:40:45 | 研究报告/任务说明 | 用途待确认 |
| JoinQuant官方JQData_api.py | JoinQuant官方JQData_api.py | 是 | 60396 | 2026-06-14 09:38:46 | 其他 | 用途待确认 |
| JoinQuant官方JQData_test_api.py | JoinQuant官方JQData_test_api.py | 是 | 88682 | 2026-06-14 09:38:46 | 其他 | 用途待确认 |
| jq_A0_BASE_original.log | jq_A0_BASE_original.log | 是 | 162108 | 2026-05-29 02:46:02 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v130A_20260101_20260614.log.txt | jq_v130A_20260101_20260614.log.txt | 是 | 872137 | 2026-06-15 14:59:30 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v121A_20250701_20260614.log.txt | log\jq_v121A_20250701_20260614.log.txt | 是 | 3344600 | 2026-06-15 09:13:14 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v130A_20260101_20260614.log.txt | log\jq_v130A_20260101_20260614.log.txt | 是 | 872137 | 2026-06-15 14:59:30 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v13A_20260101_20260614.log.txt | log\jq_v13A_20260101_20260614.log.txt | 是 | 876144 | 2026-06-15 13:51:32 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v140B_20260101_20260614.log.txt | log\jq_v140B_20260101_20260614.log.txt | 是 | 1573980 | 2026-06-17 10:04:08 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v140B_fix_20260101_20260614.log.txt | log\jq_v140B_fix_20260101_20260614.log.txt | 是 | 1469198 | 2026-06-17 14:13:58 | 日志/文本备份 | 回测日志/分析日志 |
| jq_v14A_20260101_20260614.log.txt | log\jq_v14A_20260101_20260614.log.txt | 是 | 1551730 | 2026-06-16 16:49:46 | 日志/文本备份 | 回测日志/分析日志 |
| README_EXPERIMENTS.md | README_EXPERIMENTS.md | 是 | 1897 | 2026-05-29 02:49:36 | 研究报告/任务说明 | 用途待确认 |
| real_add_attribution_detail.csv | real_add_attribution_detail.csv | 是 | 5805 | 2026-06-15 15:46:47 | 结果 CSV | 用途待确认 |
| real_add_attribution_summary.csv | real_add_attribution_summary.csv | 是 | 1601 | 2026-06-15 15:46:47 | 结果 CSV | 用途待确认 |
| real_add_bad_samples.csv | real_add_bad_samples.csv | 是 | 4241 | 2026-06-15 15:46:47 | 结果 CSV | 用途待确认 |
| real_add_good_samples.csv | real_add_good_samples.csv | 是 | 2205 | 2026-06-15 15:46:47 | 结果 CSV | 用途待确认 |
| research_analyze_exit_add_rules.py | research_analyze_exit_add_rules.py | 是 | 10923 | 2026-06-15 06:20:04 | 研究脚本 | 用途待确认 |
| research_batch_analysis.py | research_batch_analysis.py | 是 | 29948 | 2026-05-30 23:51:00 | 研究脚本 | 用途待确认 |
| research_role_rotation_direct_sim_v1.py | research_role_rotation_direct_sim_v1.py | 是 | 136763 | 2026-06-17 18:37:03 | 研究脚本 | v1.4.0C 聚宽研究环境直接模拟脚本 |
| research_shadow_rotation_2plus2.py | research_shadow_rotation_2plus2.py | 是 | 68143 | 2026-06-16 14:42:57 | 研究脚本 | 用途待确认 |
| research_v14C_D_candidate_research.py | research_v14C_D_candidate_research.py | 是 | 25527 | 2026-06-21 00:29:46 | 研究脚本 | D0~D4 candidate replay/汇总脚本 |
| research_v14C_P1_to_P5_master.py | research_v14C_P1_to_P5_master.py | 是 | 85067 | 2026-06-20 01:18:27 | 研究脚本 | P1~P5 研究主脚本 |
| role_rotation_daily_nav.csv | role_rotation_result_bundle 2\role_rotation_daily_nav.csv | 是 | 94779 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_decisions.csv | role_rotation_result_bundle 2\role_rotation_decisions.csv | 是 | 61217 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_diagnostics.csv | role_rotation_result_bundle 2\role_rotation_diagnostics.csv | 是 | 77470 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_outputs.xlsx | role_rotation_result_bundle 2\role_rotation_outputs.xlsx | 是 | 368664 | 2026-06-17 17:19:54 | Excel 输出 | 用途待确认 |
| role_rotation_overfit_check.csv | role_rotation_result_bundle 2\role_rotation_overfit_check.csv | 是 | 811 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_positions.csv | role_rotation_result_bundle 2\role_rotation_positions.csv | 是 | 181734 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_report.md | role_rotation_result_bundle 2\role_rotation_report.md | 是 | 9290 | 2026-06-17 17:19:54 | 研究报告/任务说明 | 用途待确认 |
| role_rotation_summary.csv | role_rotation_result_bundle 2\role_rotation_summary.csv | 是 | 2294 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_trades.csv | role_rotation_result_bundle 2\role_rotation_trades.csv | 是 | 90075 | 2026-06-17 17:19:52 | 结果 CSV | 用途待确认 |
| role_rotation_cap_check.csv | role_rotation_result_bundle V140C\role_rotation_cap_check.csv | 是 | 50617 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_cost_sensitivity.csv | role_rotation_result_bundle V140C\role_rotation_cost_sensitivity.csv | 是 | 590 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_daily_nav.csv | role_rotation_result_bundle V140C\role_rotation_daily_nav.csv | 是 | 94896 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_decisions.csv | role_rotation_result_bundle V140C\role_rotation_decisions.csv | 是 | 65462 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_diagnostics.csv | role_rotation_result_bundle V140C\role_rotation_diagnostics.csv | 是 | 77472 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_outputs.xlsx | role_rotation_result_bundle V140C\role_rotation_outputs.xlsx | 是 | 411913 | 2026-06-18 16:24:30 | Excel 输出 | v1.4.0C 研究输出/报告 |
| role_rotation_overfit_check.csv | role_rotation_result_bundle V140C\role_rotation_overfit_check.csv | 是 | 1207 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_positions.csv | role_rotation_result_bundle V140C\role_rotation_positions.csv | 是 | 181239 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_promotion_attribution.csv | role_rotation_result_bundle V140C\role_rotation_promotion_attribution.csv | 是 | 2291 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_report.md | role_rotation_result_bundle V140C\role_rotation_report.md | 是 | 12918 | 2026-06-18 16:24:30 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| role_rotation_sensitivity.csv | role_rotation_result_bundle V140C\role_rotation_sensitivity.csv | 是 | 1809 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_summary.csv | role_rotation_result_bundle V140C\role_rotation_summary.csv | 是 | 2394 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_trades.csv | role_rotation_result_bundle V140C\role_rotation_trades.csv | 是 | 98057 | 2026-06-18 16:24:28 | 结果 CSV | v1.4.0C 研究输出/报告 |
| run_manifest.json | role_rotation_result_bundle V140C\run_manifest.json | 是 | 474 | 2026-06-18 16:24:28 | manifest/JSON | v1.4.0C 研究输出/报告 |
| v14C_big_meat_samples.csv | role_rotation_result_bundle V140C\v14C_big_meat_samples.csv | 是 | 8450 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_entry_feature_need_list.csv | role_rotation_result_bundle V140C\v14C_entry_feature_need_list.csv | 是 | 13505 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_fast_loss_samples.csv | role_rotation_result_bundle V140C\v14C_fast_loss_samples.csv | 是 | 32378 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_full_diagnosis_outputs.xlsx | role_rotation_result_bundle V140C\v14C_full_diagnosis_outputs.xlsx | 是 | 36063 | 2026-06-18 16:24:32 | Excel 输出 | v1.4.0C 研究输出/报告 |
| v14C_full_diagnosis_report.md | role_rotation_result_bundle V140C\v14C_full_diagnosis_report.md | 是 | 9313 | 2026-06-18 16:24:32 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v14C_loss_bigmeat_summary.csv | role_rotation_result_bundle V140C\v14C_loss_bigmeat_summary.csv | 是 | 351 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_overfit_final_check.csv | role_rotation_result_bundle V140C\v14C_overfit_final_check.csv | 是 | 296 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_promotion_profit_summary.csv | role_rotation_result_bundle V140C\v14C_promotion_profit_summary.csv | 是 | 243 | 2026-06-18 16:24:32 | 结果 CSV | v1.4.0C 研究输出/报告 |
| p1_entry_feature_diagnosis.csv | role_rotation_result_bundle V140C_P1_P5\p1_entry_feature_diagnosis.csv | 是 | 1192 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p1_entry_feature_trade_log.csv | role_rotation_result_bundle V140C_P1_P5\p1_entry_feature_trade_log.csv | 是 | 19921 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p1_fast_loss_vs_big_meat_features.csv | role_rotation_result_bundle V140C_P1_P5\p1_fast_loss_vs_big_meat_features.csv | 是 | 504 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p2_confirm_add_position_detail.csv | role_rotation_result_bundle V140C_P1_P5\p2_confirm_add_position_detail.csv | 是 | 9770 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p2_fast_loss_experiment_summary.csv | role_rotation_result_bundle V140C_P1_P5\p2_fast_loss_experiment_summary.csv | 是 | 245 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p2_next_day_acceptance_detail.csv | role_rotation_result_bundle V140C_P1_P5\p2_next_day_acceptance_detail.csv | 是 | 854 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p2_quick_fail_exit_detail.csv | role_rotation_result_bundle V140C_P1_P5\p2_quick_fail_exit_detail.csv | 是 | 15892 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p3_cap_and_regime_summary.csv | role_rotation_result_bundle V140C_P1_P5\p3_cap_and_regime_summary.csv | 是 | 1500 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p3_cap_check_detail.csv | role_rotation_result_bundle V140C_P1_P5\p3_cap_check_detail.csv | 是 | 53616 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p3_risk_off_proxy_summary.csv | role_rotation_result_bundle V140C_P1_P5\p3_risk_off_proxy_summary.csv | 是 | 508 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p4_promotion_protection_detail.csv | role_rotation_result_bundle V140C_P1_P5\p4_promotion_protection_detail.csv | 是 | 2549 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p4_promotion_protection_summary.csv | role_rotation_result_bundle V140C_P1_P5\p4_promotion_protection_summary.csv | 是 | 320 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p5_combined_observer_report.md | role_rotation_result_bundle V140C_P1_P5\p5_combined_observer_report.md | 是 | 2802 | 2026-06-18 18:22:38 | 研究报告/任务说明 | P1~P5 输出或任务说明 |
| p5_combined_observer_summary.csv | role_rotation_result_bundle V140C_P1_P5\p5_combined_observer_summary.csv | 是 | 377 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p5_combined_observer_trades.csv | role_rotation_result_bundle V140C_P1_P5\p5_combined_observer_trades.csv | 是 | 27004 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p_cost_sensitivity_summary.csv | role_rotation_result_bundle V140C_P1_P5\p_cost_sensitivity_summary.csv | 是 | 590 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p_overfit_check_summary.csv | role_rotation_result_bundle V140C_P1_P5\p_overfit_check_summary.csv | 是 | 1387 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| p_profit_concentration_summary.csv | role_rotation_result_bundle V140C_P1_P5\p_profit_concentration_summary.csv | 是 | 1219 | 2026-06-18 18:22:38 | 结果 CSV | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_master_report.md | role_rotation_result_bundle V140C_P1_P5\v14C_P1_to_P5_master_report.md | 是 | 9197 | 2026-06-18 18:22:38 | 研究报告/任务说明 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_outputs.xlsx | role_rotation_result_bundle V140C_P1_P5\v14C_P1_to_P5_outputs.xlsx | 是 | 95991 | 2026-06-18 18:22:39 | Excel 输出 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_result_bundle.zip | role_rotation_result_bundle V140C_P1_P5\v14C_P1_to_P5_result_bundle.zip | 是 | 127402 | 2026-06-18 18:22:39 | 压缩包 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_run_manifest.json | role_rotation_result_bundle V140C_P1_P5\v14C_P1_to_P5_run_manifest.json | 是 | 1390 | 2026-06-18 18:22:39 | manifest/JSON | P1~P5 输出或任务说明 |
| role_rotation_daily_nav.csv | role_rotation_result_bundle\role_rotation_daily_nav.csv | 是 | 4931 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_decisions.csv | role_rotation_result_bundle\role_rotation_decisions.csv | 是 | 86 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_diagnostics.csv | role_rotation_result_bundle\role_rotation_diagnostics.csv | 是 | 5572 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_outputs.xlsx | role_rotation_result_bundle\role_rotation_outputs.xlsx | 是 | 16498 | 2026-06-17 16:35:28 | Excel 输出 | 用途待确认 |
| role_rotation_overfit_check.csv | role_rotation_result_bundle\role_rotation_overfit_check.csv | 是 | 153 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_positions.csv | role_rotation_result_bundle\role_rotation_positions.csv | 是 | 4 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_report.md | role_rotation_result_bundle\role_rotation_report.md | 是 | 5747 | 2026-06-17 16:35:28 | 研究报告/任务说明 | 用途待确认 |
| role_rotation_result_bundle.zip | role_rotation_result_bundle\role_rotation_result_bundle.zip | 是 | 27319 | 2026-06-17 18:04:21 | 压缩包 | 用途待确认 |
| role_rotation_summary.csv | role_rotation_result_bundle\role_rotation_summary.csv | 是 | 536 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| role_rotation_trades.csv | role_rotation_result_bundle\role_rotation_trades.csv | 是 | 135 | 2026-06-17 16:35:28 | 结果 CSV | 用途待确认 |
| v14C_big_meat_samples.csv | role_rotation_result_bundle\v14C_big_meat_samples.csv | 是 | 135 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_entry_feature_need_list.csv | role_rotation_result_bundle\v14C_entry_feature_need_list.csv | 是 | 84 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_fast_loss_samples.csv | role_rotation_result_bundle\v14C_fast_loss_samples.csv | 是 | 135 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_full_diagnosis_outputs.xlsx | role_rotation_result_bundle\v14C_full_diagnosis_outputs.xlsx | 是 | 7750 | 2026-06-17 18:37:17 | Excel 输出 | v1.4.0C 研究输出/报告 |
| v14C_full_diagnosis_report.md | role_rotation_result_bundle\v14C_full_diagnosis_report.md | 是 | 5273 | 2026-06-17 18:37:17 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v14C_loss_bigmeat_summary.csv | role_rotation_result_bundle\v14C_loss_bigmeat_summary.csv | 是 | 191 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_overfit_final_check.csv | role_rotation_result_bundle\v14C_overfit_final_check.csv | 是 | 232 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_promotion_profit_summary.csv | role_rotation_result_bundle\v14C_promotion_profit_summary.csv | 是 | 221 | 2026-06-17 18:37:16 | 结果 CSV | v1.4.0C 研究输出/报告 |
| role_rotation_result_bundle_V140C_D_candidate_research.zip | role_rotation_result_bundle_V140C_D_candidate_research.zip | 是 | 263277 | 2026-06-21 00:13:23 | 压缩包 | D candidate 输出压缩包 |
| shadow_rotation_candidate_pool.csv | shadow_rotation_candidate_pool.csv | 是 | 642251 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| shadow_rotation_confirmed_signals.csv | shadow_rotation_confirmed_signals.csv | 是 | 247 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| shadow_rotation_portfolio_sim_summary.csv | shadow_rotation_portfolio_sim_summary.csv | 是 | 288 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| shadow_rotation_rule_summary.csv | shadow_rotation_rule_summary.csv | 是 | 240 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| shadow_rotation_trade_sim_detail.csv | shadow_rotation_trade_sim_detail.csv | 是 | 443 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| shadow_rotation_watch_signals.csv | shadow_rotation_watch_signals.csv | 是 | 103551 | 2026-06-16 12:56:25 | 结果 CSV | 用途待确认 |
| strategy_A_v1_1_0.py | strategy_A_v1_1_0.py | 是 | 242284 | 2026-05-29 02:48:49 | 其他 | 用途待确认 |
| tail_add_refined_rule_detail.csv | tail_add_refined_rule_detail.csv | 是 | 5446 | 2026-06-15 15:35:04 | 结果 CSV | 用途待确认 |
| tail_add_refined_rule_summary.csv | tail_add_refined_rule_summary.csv | 是 | 1767 | 2026-06-15 15:35:04 | 结果 CSV | 用途待确认 |
| v1.1.2_Codex修改规格说明_账本V2安全日志安全性能优化.md | v1.1.2_Codex修改规格说明_账本V2安全日志安全性能优化.md | 是 | 11756 | 2026-06-15 02:10:29 | 研究报告/任务说明 | 用途待确认 |
| v1.1.3_Codex修改规格说明_partial_sell实际成交数量账本修复.md | v1.1.3_Codex修改规格说明_partial_sell实际成交数量账本修复.md | 是 | 9805 | 2026-06-15 03:29:47 | 研究报告/任务说明 | 用途待确认 |
| v1.2.0_Codex修改规格说明_Dragon竞价预筛性能优化.md | v1.2.0_Codex修改规格说明_Dragon竞价预筛性能优化.md | 是 | 9327 | 2026-06-15 04:17:13 | 研究报告/任务说明 | 用途待确认 |
| v1.2.1A_Codex修改规格说明_研究环境数据采集版.md | v1.2.1A_Codex修改规格说明_研究环境数据采集版.md | 是 | 11336 | 2026-06-15 06:04:18 | 研究报告/任务说明 | 研究环境数据采集版 |
| v1.3.0_Codex修改规格说明_普涨后低开风控实验版.md | v1.3.0_Codex修改规格说明_普涨后低开风控实验版.md | 是 | 8811 | 2026-06-15 11:15:13 | 研究报告/任务说明 | 普涨后低开风控实验版 |
| v1.4.0_影子轮动精细化_满仓复利研究方案.md | v1.4.0_影子轮动精细化_满仓复利研究方案.md | 是 | 4294 | 2026-06-16 14:35:00 | 研究报告/任务说明 | 用途待确认 |
| v1.4.0A_shadow_rotation_fullB_独立实验版修改要求.md | v1.4.0A_shadow_rotation_fullB_独立实验版修改要求.md | 是 | 10225 | 2026-06-16 15:11:35 | 研究报告/任务说明 | shadow rotation fullB 独立实验版 |
| v1.4.0B_fix_log_compare_outputs.xlsx | v1.4.0B_fix_log_compare_outputs.xlsx | 是 | 981095 | 2026-06-17 14:17:35 | Excel 输出 | v1.4.0B 单卫星约束修复版 |
| v1.4.0B_fix_日志对比分析_过拟合初检报告.md | v1.4.0B_fix_日志对比分析_过拟合初检报告.md | 是 | 13508 | 2026-06-17 14:17:35 | 研究报告/任务说明 | v1.4.0B 单卫星约束修复版 |
| v1.4.0B_log_compare_outputs.xlsx | v1.4.0B_log_compare_outputs.xlsx | 是 | 756371 | 2026-06-17 10:54:29 | Excel 输出 | 原核心 + 单卫星 shadow rotation 控制变量版 |
| v1.4.0B_shadow_rotation_original_core_独立实验版修改要求.md | v1.4.0B_shadow_rotation_original_core_独立实验版修改要求.md | 是 | 8196 | 2026-06-16 17:10:25 | 研究报告/任务说明 | 原核心 + 单卫星 shadow rotation 控制变量版 |
| v1.4.0B_日志对比分析_过拟合初检报告.md | v1.4.0B_日志对比分析_过拟合初检报告.md | 是 | 25667 | 2026-06-17 10:54:29 | 研究报告/任务说明 | 原核心 + 单卫星 shadow rotation 控制变量版 |
| v1.4.0C_quantitative_analysis_report.md | v1.4.0C_quantitative_analysis_report.md | 是 | 4645 | 2026-06-18 17:44:24 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v1.4.0C_小区间研究输出诊断报告.md | v1.4.0C_小区间研究输出诊断报告.md | 是 | 9343 | 2026-06-17 16:54:39 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v1.4.0C_核心卫星角色轮动_聚宽研究环境直接模拟方案.md | v1.4.0C_核心卫星角色轮动_聚宽研究环境直接模拟方案.md | 是 | 14310 | 2026-06-17 14:56:43 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v14C_exit_mechanism_plan.csv | v14C_exit_mechanism_plan.csv | 是 | 3637 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_fast_loss_reduction_plan.csv | v14C_fast_loss_reduction_plan.csv | 是 | 2968 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_next_research_direction_Codex任务说明.md | v14C_next_research_direction_Codex任务说明.md | 是 | 11028 | 2026-06-18 17:50:37 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v14C_next_research_direction_outputs.xlsx | v14C_next_research_direction_outputs.xlsx | 是 | 94253 | 2026-06-18 17:56:41 | Excel 输出 | v1.4.0C 研究输出/报告 |
| v14C_next_research_direction_report.md | v14C_next_research_direction_report.md | 是 | 40496 | 2026-06-18 17:56:40 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| v14C_overfit_risk_review.csv | v14C_overfit_risk_review.csv | 是 | 4517 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_P1_P5_master_final_fix_Codex任务说明.md | v14C_P1_P5_master_final_fix_Codex任务说明.md | 是 | 8653 | 2026-06-19 03:38:50 | 研究报告/任务说明 | v1.4.0C 研究输出/报告 |
| p1_entry_feature_diagnosis.csv | v14C_P1_to_P5_JQ_result_bundle\p1_entry_feature_diagnosis.csv | 是 | 783 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p1_entry_feature_missing_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p1_entry_feature_missing_summary.csv | 是 | 757 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p1_entry_feature_trade_log.csv | v14C_P1_to_P5_JQ_result_bundle\p1_entry_feature_trade_log.csv | 是 | 77919 | 2026-06-20 01:43:04 | 结果 CSV | 回测日志/分析日志 |
| p1_fast_loss_vs_big_meat_features.csv | v14C_P1_to_P5_JQ_result_bundle\p1_fast_loss_vs_big_meat_features.csv | 是 | 277 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p1_jq_entry_feature_diagnostics.csv | v14C_P1_to_P5_JQ_result_bundle\p1_jq_entry_feature_diagnostics.csv | 是 | 95 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p1_jq_entry_features.csv | v14C_P1_to_P5_JQ_result_bundle\p1_jq_entry_features.csv | 是 | 77919 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_confirm_add_position_detail.csv | v14C_P1_to_P5_JQ_result_bundle\p2_confirm_add_position_detail.csv | 是 | 22275 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_daily_nav.csv | v14C_P1_to_P5_JQ_result_bundle\p2_daily_nav.csv | 是 | 96639 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_decisions.csv | v14C_P1_to_P5_JQ_result_bundle\p2_decisions.csv | 是 | 111706 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_fast_loss_experiment_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p2_fast_loss_experiment_summary.csv | 是 | 3526 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_positions.csv | v14C_P1_to_P5_JQ_result_bundle\p2_positions.csv | 是 | 196682 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p2_trades.csv | v14C_P1_to_P5_JQ_result_bundle\p2_trades.csv | 是 | 117322 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p3_cap_and_regime_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p3_cap_and_regime_summary.csv | 是 | 2477 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p3_daily_nav.csv | v14C_P1_to_P5_JQ_result_bundle\p3_daily_nav.csv | 是 | 63487 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p3_decisions.csv | v14C_P1_to_P5_JQ_result_bundle\p3_decisions.csv | 是 | 69838 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p3_positions.csv | v14C_P1_to_P5_JQ_result_bundle\p3_positions.csv | 是 | 135442 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p3_trades.csv | v14C_P1_to_P5_JQ_result_bundle\p3_trades.csv | 是 | 69298 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p4_daily_nav.csv | v14C_P1_to_P5_JQ_result_bundle\p4_daily_nav.csv | 是 | 96078 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p4_decisions.csv | v14C_P1_to_P5_JQ_result_bundle\p4_decisions.csv | 是 | 112720 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p4_positions.csv | v14C_P1_to_P5_JQ_result_bundle\p4_positions.csv | 是 | 201418 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p4_promotion_protection_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p4_promotion_protection_summary.csv | 是 | 3540 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p4_trades.csv | v14C_P1_to_P5_JQ_result_bundle\p4_trades.csv | 是 | 106592 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_combined_observer_report.md | v14C_P1_to_P5_JQ_result_bundle\p5_combined_observer_report.md | 是 | 4185 | 2026-06-20 01:43:04 | 研究报告/任务说明 | 用途待确认 |
| p5_combined_observer_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p5_combined_observer_summary.csv | 是 | 2043 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_component_effect_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p5_component_effect_summary.csv | 是 | 1114 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_daily_nav.csv | v14C_P1_to_P5_JQ_result_bundle\p5_daily_nav.csv | 是 | 32215 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_decisions.csv | v14C_P1_to_P5_JQ_result_bundle\p5_decisions.csv | 是 | 41158 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_positions.csv | v14C_P1_to_P5_JQ_result_bundle\p5_positions.csv | 是 | 54057 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p5_trades.csv | v14C_P1_to_P5_JQ_result_bundle\p5_trades.csv | 是 | 35850 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p_cost_sensitivity_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p_cost_sensitivity_summary.csv | 是 | 590 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p_overfit_check_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p_overfit_check_summary.csv | 是 | 557 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p_path_simulation_status.csv | v14C_P1_to_P5_JQ_result_bundle\p_path_simulation_status.csv | 是 | 489 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| p_profit_concentration_summary.csv | v14C_P1_to_P5_JQ_result_bundle\p_profit_concentration_summary.csv | 是 | 1209 | 2026-06-20 01:43:04 | 结果 CSV | 用途待确认 |
| role_rotation_cap_check.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_cap_check.csv | 是 | 50617 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_cost_sensitivity.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_cost_sensitivity.csv | 是 | 590 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_daily_nav.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_daily_nav.csv | 是 | 94896 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_decisions.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_decisions.csv | 是 | 65462 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_diagnostics.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_diagnostics.csv | 是 | 77472 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_outputs.xlsx | v14C_P1_to_P5_JQ_result_bundle\role_rotation_outputs.xlsx | 是 | 411912 | 2026-06-20 01:42:22 | Excel 输出 | 用途待确认 |
| role_rotation_overfit_check.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_overfit_check.csv | 是 | 1207 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_positions.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_positions.csv | 是 | 181239 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_promotion_attribution.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_promotion_attribution.csv | 是 | 2291 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_report.md | v14C_P1_to_P5_JQ_result_bundle\role_rotation_report.md | 是 | 12918 | 2026-06-20 01:42:22 | 研究报告/任务说明 | 用途待确认 |
| role_rotation_result_bundle.zip | v14C_P1_to_P5_JQ_result_bundle\role_rotation_result_bundle.zip | 是 | 500290 | 2026-06-20 01:42:22 | 压缩包 | 用途待确认 |
| role_rotation_sensitivity.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_sensitivity.csv | 是 | 1809 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_summary.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_summary.csv | 是 | 2394 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| role_rotation_trades.csv | v14C_P1_to_P5_JQ_result_bundle\role_rotation_trades.csv | 是 | 98057 | 2026-06-20 01:42:20 | 结果 CSV | 用途待确认 |
| run_manifest.json | v14C_P1_to_P5_JQ_result_bundle\run_manifest.json | 是 | 507 | 2026-06-20 01:42:20 | manifest/JSON | 用途待确认 |
| v14C_P1_to_P5_JQ_master_report.md | v14C_P1_to_P5_JQ_result_bundle\v14C_P1_to_P5_JQ_master_report.md | 是 | 26737 | 2026-06-20 02:01:20 | 研究报告/任务说明 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_JQ_outputs.xlsx | v14C_P1_to_P5_JQ_result_bundle\v14C_P1_to_P5_JQ_outputs.xlsx | 是 | 1098464 | 2026-06-20 01:43:08 | Excel 输出 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_JQ_result_bundle.zip | v14C_P1_to_P5_JQ_result_bundle\v14C_P1_to_P5_JQ_result_bundle.zip | 是 | 2463808 | 2026-06-20 02:01:05 | 压缩包 | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_JQ_run_manifest.json | v14C_P1_to_P5_JQ_result_bundle\v14C_P1_to_P5_JQ_run_manifest.json | 是 | 3790 | 2026-06-20 02:01:10 | manifest/JSON | P1~P5 输出或任务说明 |
| v14C_P1_to_P5_master_Codex任务说明.md | v14C_P1_to_P5_master_Codex任务说明.md | 是 | 15625 | 2026-06-18 18:13:29 | 研究报告/任务说明 | P1~P5 输出或任务说明 |
| v14C_position_management_plan.csv | v14C_position_management_plan.csv | 是 | 824 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_stock_selection_diagnosis.csv | v14C_stock_selection_diagnosis.csv | 是 | 2169 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_strategy_architecture_plan.csv | v14C_strategy_architecture_plan.csv | 是 | 778 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| v14C_trade_attribution_summary.csv | v14C_trade_attribution_summary.csv | 是 | 5001 | 2026-06-18 17:56:40 | 结果 CSV | v1.4.0C 研究输出/报告 |
| WORKLOG_v1.2.1A_research_data_collector.md | WORKLOG_v1.2.1A_research_data_collector.md | 是 | 1814 | 2026-06-15 06:20:04 | 研究报告/任务说明 | 研究环境数据采集版 |
| WORKLOG_v1.3.0_breadth_gap_risk_control.md | WORKLOG_v1.3.0_breadth_gap_risk_control.md | 是 | 1961 | 2026-06-15 11:22:49 | 研究报告/任务说明 | 普涨后低开风控实验版 |
| WORKLOG_v1.3.0A_breadth_gap_direct_exit.md | WORKLOG_v1.3.0A_breadth_gap_direct_exit.md | 是 | 2369 | 2026-06-15 14:20:48 | 研究报告/任务说明 | 普涨低开直接清仓实验版 |
| WORKLOG_v1.4.0A_shadow_rotation_fullB.md | WORKLOG_v1.4.0A_shadow_rotation_fullB.md | 是 | 3361 | 2026-06-16 15:20:59 | 研究报告/任务说明 | shadow rotation fullB 独立实验版 |
| WORKLOG_v1.4.0B_shadow_rotation_original_core.md | WORKLOG_v1.4.0B_shadow_rotation_original_core.md | 是 | 3047 | 2026-06-16 18:06:51 | 研究报告/任务说明 | 原核心 + 单卫星 shadow rotation 控制变量版 |
| WORKLOG_战车A.md | WORKLOG_战车A.md | 是 | 7536 | 2026-06-15 04:21:52 | 研究报告/任务说明 | 回测日志/分析日志 |
| 战车A_BigMeat_Simple.py | 战车A_BigMeat_Simple.py | 是 | 139604 | 2026-06-12 18:35:23 | 历史策略版本 | 用途待确认 |
| 战车A_BigMeat_Simple_backup_before_fix.py | 战车A_BigMeat_Simple_backup_before_fix.py | 是 | 261119 | 2026-06-11 18:42:02 | 历史策略版本 | 用途待确认 |
| 战车A_BigMeat_Simple_Codex修改版解析与二次瘦身提示词.md | 战车A_BigMeat_Simple_Codex修改版解析与二次瘦身提示词.md | 是 | 14798 | 2026-06-12 17:06:44 | 研究报告/任务说明 | 用途待确认 |
| 战车A_BigMeat_Simple_Codex提示词.md | 战车A_BigMeat_Simple_Codex提示词.md | 是 | 16573 | 2026-06-11 17:47:54 | 研究报告/任务说明 | 用途待确认 |
| 战车A_BigMeat_Simple_二次修复与回测加速_Codex提示词.md | 战车A_BigMeat_Simple_二次修复与回测加速_Codex提示词.md | 是 | 12713 | 2026-06-12 12:06:49 | 研究报告/任务说明 | 用途待确认 |
| 战车A_BigMeat_Simple_交易统计与加仓确认Bug修复_Codex提示词.md | 战车A_BigMeat_Simple_交易统计与加仓确认Bug修复_Codex提示词.md | 是 | 9369 | 2026-06-12 14:18:34 | 研究报告/任务说明 | 用途待确认 |
| 战车A_BigMeat_Simple_瘦身版运行修复与候选池加速_Codex提示词.md | 战车A_BigMeat_Simple_瘦身版运行修复与候选池加速_Codex提示词.md | 是 | 10415 | 2026-06-12 18:34:06 | 研究报告/任务说明 | 用途待确认 |
| 战车A_BigMeat_Simple_聚宽网页版日志优化与代码瘦身_Codex提示词.md | 战车A_BigMeat_Simple_聚宽网页版日志优化与代码瘦身_Codex提示词.md | 是 | 9403 | 2026-06-12 16:17:21 | 研究报告/任务说明 | 用途待确认 |
| 战车A龙头3.py | 战车A龙头3.py | 是 | 176829 | 2026-06-15 04:24:43 | 主策略 | 当前稳定主策略 v1.2.0-auction-prefilter |
| 战车A龙头3.txt | 战车A龙头3.txt | 是 | 152981 | 2026-06-15 00:32:27 | 日志/文本备份 | 历史来源文本/旧主策略备份；Git 状态 AM |
| 战车A龙头3_v1.2.1A_research_data_collector.py | 战车A龙头3_v1.2.1A_research_data_collector.py | 是 | 216028 | 2026-06-15 06:23:04 | 历史策略版本 | 研究环境数据采集版 |
| 战车A龙头3_v1.3.0_breadth_gap_risk_control.py | 战车A龙头3_v1.3.0_breadth_gap_risk_control.py | 是 | 186163 | 2026-06-15 11:25:04 | 历史策略版本 | 普涨后低开风控实验版 |
| 战车A龙头3_v1.3.0A_breadth_gap_direct_exit.py | 战车A龙头3_v1.3.0A_breadth_gap_direct_exit.py | 是 | 185403 | 2026-06-15 14:20:27 | 历史策略版本 | 普涨低开直接清仓实验版 |
| 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | 是 | 204435 | 2026-06-16 15:20:40 | 历史策略版本 | shadow rotation fullB 独立实验版 |
| 战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py | 战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py | 是 | 206669 | 2026-06-17 11:29:30 | 历史策略版本 | v1.4.0B 单卫星约束修复版 |
| 战车A龙头3_v1.4.0B_shadow_rotation_original_core.py | 战车A龙头3_v1.4.0B_shadow_rotation_original_core.py | 是 | 206669 | 2026-06-17 11:29:30 | 历史策略版本 | 原核心 + 单卫星 shadow rotation 控制变量版 |
| 战车A龙头3_v1.4.0D_observer.py | 战车A龙头3_v1.4.0D_observer.py | 是 | 216492 | 2026-06-21 00:32:26 | observer 策略 | D3 observer 观察版，当前新增，需核查等价性 |
| 放入本地目录说明.txt | 放入本地目录说明.txt | 是 | 538 | 2026-05-29 02:46:02 | 日志/文本备份 | 用途待确认 |
| 聚宽量化交易平台 API 知识库.md | 聚宽量化交易平台 API 知识库.md | 是 | 63688 | 2026-06-14 09:15:34 | 研究报告/任务说明 | 用途待确认 |
| 《过拟合检测》  真实阿尔法.ipynb | 过拟合检测\《过拟合检测》  真实阿尔法.ipynb | 是 | 52146 | 2026-06-17 14:05:08 | Notebook | 用途待确认 |
| 过拟合检测.ipynb | 过拟合检测\过拟合检测.ipynb | 是 | 110581 | 2026-06-16 18:04:26 | Notebook | 用途待确认 |

## 2. 全版本时间线

| 版本 | 文件名 | Source From | Change Type | 核心变化 | 是否主线 | 是否研究分支 | 是否已跑回测 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 无法确认 | strategy_A_v1_1_0.py | 无法确认 | 无法确认 | 原版/旧版策略源 | 否 | 历史 | 历史源文件 | 无法确认 |
| 无法确认 | 战车A_BigMeat_Simple.py | 无法确认 | 无法确认 | BigMeat Simple 历史策略 | 否 | 历史 | 历史阶段使用 | 无法确认 |
| 无法确认 | 战车A_BigMeat_Simple_backup_before_fix.py | 无法确认 | 无法确认 | BigMeat Simple 历史策略 | 否 | 历史 | 历史阶段使用 | 无法确认 |
| v1.2.0-auction-prefilter | 战车A龙头3.py | 战车A龙头3.txt | - auction-prefilter-v1; - strategy-performance-experiment; - 在 get_call_auction 前新增 Dragon 日线预筛; - 目标减少进入 get_call_auction 的股票数量; - 预筛只使用 get_call_auction 前可获得的数据; - 预筛只决定竞价调用范围，不替代 Dragon score; - 不修改 v1.1.3 账本修复逻辑 | v1.2.0 auction prefilter 稳定主策略 | 是 | 否 | 已知有后续对照，但本扫描未运行回测 | 性能优化实验版 |
| v1.2.1A-research-data-collector | 战车A龙头3_v1.2.1A_research_data_collector.py | 战车A龙头3.py | - research-data-collector; - logging-only; - 新增 HOLD_SNAPSHOT / EXIT_EVENT / ADD_CANDIDATE_SNAPSHOT; - 新增 LIVERMORE_ADD_BLOCKED / TRADE_ANALYTICS / DAILY_ANALYTICS; - 为聚宽研究环境离线分析浮盈保护、止损修复、提前加仓提供数据; - 不修改真实交易逻辑; - 不修改预筛权重、Top250、止盈止损、加仓、仓位和账本 | 研究环境数据采集 + ENTRY/EXIT/ADD 日志 | 否 | 是 | 作为 v1.2.1A 日志来源使用 | 研究环境数据采集版 |
| v1.3.0A-breadth-gap-direct-exit | 战车A龙头3_v1.3.0A_breadth_gap_direct_exit.py | 战车A龙头3_v1.3.0_breadth_gap_risk_control.py | - breadth-gap-direct-exit; - experiment; - 基于 v1.3.0 普涨低开风控版复制生成独立实验文件; - 市场条件收紧为 prev_regime=bull 且 prev_trend=up; - 满足普涨低开风控条件时直接清仓，不再先卖半仓; - 不修改 Dragon 预筛、买入、原止损止盈、原加仓和账本逻辑 | 普涨低开直接清仓实验 | 否 | 是 | 有 jq_v130A_20260101_20260614.log.txt | 独立实验版 |
| v1.3.0-breadth-gap-risk-control | 战车A龙头3_v1.3.0_breadth_gap_risk_control.py | 战车A龙头3.py | - breadth-gap-risk-control; - experiment; - 基于 v1.2.0 主策略复制生成独立实验文件; - 新增普涨后低开风控; - 不修改 Dragon 预筛、Top250、买入、原止损止盈、原加仓和账本逻辑; - 普涨后低开风控只在 09:32 对已有持仓生效 | 普涨后低开风控实验，半仓/清仓规则 | 否 | 是 | 已知 v1.3.0 当前版结果存在于日志分析 | 独立实验版 |
| v1.4.0A-shadow-rotation-fullB | 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | 战车A龙头3.py | - shadow-rotation-fullB; - watch-pool-satellite; - independent-experiment; - 新增 WATCH_POOL + Rule D deep_water 卫星仓轮动; - Full-B: core 70% + satellite 15% x 2, max 100%; - 不修改原策略文件，不绕开 v1.1.3 交易账本; - 卫星仓使用独立 slot_type/strategy_tag 标记 | WATCH_POOL + Rule D deep_water，Full-B 70%+15%x2 | 否 | 是 | log/jq_v14A_20260101_20260614.log.txt 存在 | 独立实验版 |
| v1.4.0B-shadow-rotation-original-core | 战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py | 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | - shadow-rotation-original-core; - single-watch-pool-satellite; - independent-experiment; - 恢复原核心仓：Top1 35%、Top2 25%、初始上限 60%、总仓 75%; - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1; - 不做卫星替换，用于验证原核心 + 小卫星仓是否增厚收益; - 不修改原策略文件，不绕开 v1.1.3 交易账本 | v1.4.0B 单卫星仓约束修复 | 否 | 是 | log/jq_v140B_fix_20260101_20260614.log.txt 存在 | 独立控制变量实验版 |
| v1.4.0B-shadow-rotation-original-core | 战车A龙头3_v1.4.0B_shadow_rotation_original_core.py | 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | - shadow-rotation-original-core; - single-watch-pool-satellite; - independent-experiment; - 恢复原核心仓：Top1 35%、Top2 25%、初始上限 60%、总仓 75%; - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1; - 不做卫星替换，用于验证原核心 + 小卫星仓是否增厚收益; - 不修改原策略文件，不绕开 v1.1.3 交易账本 | 原核心仓参数 + 单卫星 15%，不做替换 | 否 | 是 | log/jq_v140B_20260101_20260614.log.txt 存在 | 独立控制变量实验版 |
| v1.4.0B-shadow-rotation-original-core | 战车A龙头3_v1.4.0D_observer.py | 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py | - shadow-rotation-original-core; - single-watch-pool-satellite; - independent-experiment; - 恢复原核心仓：Top1 35%、Top2 25%、初始上限 60%、总仓 75%; - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1; - 不做卫星替换，用于验证原核心 + 小卫星仓是否增厚收益; - 不修改原策略文件，不绕开 v1.1.3 交易账本 | D3 observer：cap_fixed + no_promotion_take_profit 观察版 | 否 | 是 | 未发现回测日志 | 独立控制变量实验版 |

补充说明：
- 当前主策略文件证据：`战车A龙头3.py:2` 为 `Strategy Version: v1.2.0-auction-prefilter`，`战车A龙头3.py:6` 为 `Source From: 战车A龙头3.txt`。
- v1.4.0A：`战车A龙头3_v1.4.0A_shadow_rotation_fullB.py`，Full-B 结构，`max_total_position_ratio=1.00`、`shadow_satellite_slot_ratio=0.15`。
- v1.4.0B：`战车A龙头3_v1.4.0B_shadow_rotation_original_core.py`，原核心仓 + 单卫星 15%。
- v1.4.0B_fix：`战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py`，单卫星约束修复版。
- v1.4.0C：本目录未发现 `v1.4.0C*.py` 策略文件；v1.4.0C 主要证据来自 `research_role_rotation_direct_sim_v1.py` 与 `role_rotation_result_bundle V140C` 结果包。
- v1.4.0D_observer：`战车A龙头3_v1.4.0D_observer.py`，文件头显示 Source From 为 `战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py`，不是 v1.4.0C 策略文件。

## 3. v1.4.0C 准确来源核查

结论：未发现 v1.4.0C 原始策略 `.py` 文件。无法确认 observer 是 v1.4.0C 的严格派生版本。

| 核查项 | 结论 | 证据 |
| --- | --- | --- |
| v1.4.0C 原始策略文件是否存在 | 否 | `rg --files` 与 Python 扫描未发现 `*v1.4.0C*.py` 或 `*v14C*.py` 策略文件；仅发现研究脚本与报告/结果文件。 |
| 准确文件名 | 无法确认，缺少证据 | 存在 `research_role_rotation_direct_sim_v1.py`、`v1.4.0C_核心卫星角色轮动_聚宽研究环境直接模拟方案.md`、`role_rotation_result_bundle V140C/*`，但不是策略文件。 |
| v1.4.0C 研究基于什么 | 基于研究脚本与结果包 | `research_role_rotation_direct_sim_v1.py`、`role_rotation_result_bundle V140C/role_rotation_summary.csv`、`role_rotation_result_bundle V140C/run_manifest.json`。 |
| v1.4.0C 与 v1.4.0B / fix 关系 | 无法确认，缺少策略文件证据 | v1.4.0B 策略文件存在；v1.4.0C 仅见直接模拟脚本/结果，缺少策略派生头。 |
| v1.4.0D_observer 是否从 v1.4.0C 派生 | 无法确认，缺少证据 | `战车A龙头3_v1.4.0D_observer.py:6` 写明 Source From 是 `战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py`。 |

v1.4.0D observer 文件头证据:

```text
1: # =========================================================
2: # Strategy Version: v1.4.0D_observer
3: # Updated: 2026-06-21
4: # Status: research-only observer branch
5: # Main File: 战车A龙头3_v1.4.0D_observer.py
6: # Source From: 战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py
7: # Change Type:
8: # - D3_no_promotion_take_profit_plus_cap_fixed
9: # - cap-fixed-order-trim
10: # - no-promotion-take-profit-observer
11: # - entry-exit-outcome-logging
12: # Notes:
13: # - Based on D3_no_promotion_take_profit_plus_cap_fixed.
14: # - Research-only observer branch; not mainline.
15: # - Not live trading.
16: # - No deep_water relaxation.
17: # - No position expansion.
18: # - No auto parameter search.
19: # =========================================================
20:
21: # =========================================================
22: # Strategy Version: v1.4.0B-shadow-rotation-original-core
23: # Updated: 2026-06-15
24: # Status: 独立控制变量实验版
25: # Main File: 战车A龙头3_v1.4.0B_shadow_rotation_original_core.py
26: # Source From: 战车A龙头3_v1.4.0A_shadow_rotation_fullB.py
27: # Change Type:
28: # - shadow-rotation-original-core
29: # - single-watch-pool-satellite
30: # - independent-experiment
31: # Notes:
32: # - 恢复原核心仓：Top1 35%、Top2 25%、初始上限 60%、总仓 75%
33: # - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1
34: # - 不做卫星替换，用于验证原核心 + 小卫星仓是否增厚收益
35: # - 不修改原策略文件，不绕开 v1.1.3 交易账本
```

v1.4.0C `.py` 搜索结果:

- `research_v14C_D_candidate_research.py`
- `research_v14C_P1_to_P5_master.py`

必须写明：无法确认 observer 是 v1.4.0C 的严格派生版本。

## 4. 各版本核心逻辑对比

| 版本 | 选股逻辑 | 买入逻辑 | deep_water | core 仓位 | satellite 仓位 | 总仓 cap | promotion | tail add | 日志 | 风控 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 无法确认 | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 未找到/未找到 | shadow 无证据 | 未找到 | 否/否 | 否 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| 无法确认 | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| 无法确认 | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.2.0-auction-prefilter | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.2.1A-research-data-collector | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.3.0A-breadth-gap-direct-exit | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.3.0-breadth-gap-risk-control | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 无证据 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.4.0A-shadow-rotation-fullB | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.35 | shadow 0.15 | 1.00 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.4.0B-shadow-rotation-original-core | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 0.15 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.4.0B-shadow-rotation-original-core | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 0.15 | 0.75 | 否/否 | 是 | ENTRY=否, EXIT=否 | cap_fixed=否 |
| v1.4.0B-shadow-rotation-original-core | Dragon 竞价/候选池，详见代码 | order_value 路径 | 是 | 0.35/0.25 | shadow 0.15 | 0.75 | 否/是 | 是 | ENTRY=是, EXIT=是 | cap_fixed=是 |

关键字段 grep 证据（v1.4.0D observer）：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| 战车A龙头3_v1.4.0D_observer.py | 16 | deep_water | # - No deep_water relaxation. |
| 战车A龙头3_v1.4.0D_observer.py | 33 | deep_water | # - 保留 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1 |
| 战车A龙头3_v1.4.0D_observer.py | 45 | deep_water | # - 新开仓仅允许 Dragon + deep_water |
| 战车A龙头3_v1.4.0D_observer.py | 47 | deep_water | # - 新增 WATCH_POOL + Rule D deep_water 单卫星仓，15% x 1 |
| 战车A龙头3_v1.4.0D_observer.py | 235 | deep_water | 'dragon_bear_allow_deep_water': 'half',  # bear下deep_water仓位减半(可选: True/False/'half') |
| 战车A龙头3_v1.4.0D_observer.py | 235 | dragon_bear_allow_deep_water | 'dragon_bear_allow_deep_water': 'half',  # bear下deep_water仓位减半(可选: True/False/'half') |
| 战车A龙头3_v1.4.0D_observer.py | 236 | deep_water | 'dragon_deep_water_max_open_ratio': 0.055, |
| 战车A龙头3_v1.4.0D_observer.py | 245 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 541 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 580 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 691 | deep_water | 'dragon_bear_allow_deep_water': 'A_dragon_bear_allow_deep_water', |
| 战车A龙头3_v1.4.0D_observer.py | 691 | dragon_bear_allow_deep_water | 'dragon_bear_allow_deep_water': 'A_dragon_bear_allow_deep_water', |
| 战车A龙头3_v1.4.0D_observer.py | 692 | deep_water | 'dragon_deep_water_max_open_ratio': 'A_dragon_deep_water_max_open_ratio', |
| 战车A龙头3_v1.4.0D_observer.py | 1152 | deep_water | if item.get('entry_type') != 'dragon_follow' or item.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 1152 | tpl | if item.get('entry_type') != 'dragon_follow' or item.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 1269 | tpl | "tpl={}\|rank={}\|current_position_ratio={:.2f}%\|" |
| 战车A龙头3_v1.4.0D_observer.py | 1276 | tpl | item.get('open_ratio', 0.0) * 100, item.get('tpl', ''), |
| 战车A龙头3_v1.4.0D_observer.py | 1750 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 1757 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 1771 | entry_type == 'dragon_follow' | int(entry_type == 'dragon_follow') |
| 战车A龙头3_v1.4.0D_observer.py | 1897 | entry_type == 'dragon_follow' | if entry_type == 'dragon_follow': |
| 战车A龙头3_v1.4.0D_observer.py | 2460 | tpl | 'tpl': pb.get('tpl', ''), |
| 战车A龙头3_v1.4.0D_observer.py | 2873 | deep_water | """14:40仅向已盈利的Dragon deep_water持仓加仓一次15%。""" |
| 战车A龙头3_v1.4.0D_observer.py | 2910 | deep_water | or meta.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 2910 | tpl | or meta.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 3266 | deep_water | if not stock or item.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 3266 | tpl | if not stock or item.get('tpl') != 'deep_water': |
| 战车A龙头3_v1.4.0D_observer.py | 3291 | deep_water | 'signal_entry_type': 'deep_water', |
| 战车A龙头3_v1.4.0D_observer.py | 3376 | deep_water | def _shadow_rule_d_deep_water_passes(snapshot): |
| 战车A龙头3_v1.4.0D_observer.py | 3520 | deep_water | 'tpl': 'deep_water', |

## 5. v1.4.0C / P1~P5 / D candidate 研究结论汇总

### v1.4.0C 原版问题

`role_rotation_result_bundle V140C/role_rotation_summary.csv` full 段：

| variant | total_return | max_drawdown | sharpe | win_rate | trade_count | promotion_count |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_core_only | 17.81% | -24.60% | 0.6678 | 22.78% | 79 | 0 |
| baseline_core_satellite | 17.06% | -23.26% | 0.6364 | 29.31% | 116 | 0 |
| role_rotation_observer | 61.91% | -22.42% | 1.6473 | 29.31% | 116 | 16 |

fast_loss / big_meat 摘要（`role_rotation_result_bundle V140C/v14C_loss_bigmeat_summary.csv`）：

| category | trade_count | total_pnl_val | pct_of_all_sells |
| --- | --- | --- | --- |
| fast_loss | 65 | -880789.6830 | 56.03% |
| big_loss | 29 | -586723.9702 | 25.00% |
| normal_loss | 16 | -90285.9410 | 13.79% |
| big_meat | 10 | 321515.4712 | 8.62% |
| super_meat | 10 | 1150728.4240 | 8.62% |
| promoted_big_meat | 4 | 183996.3182 | 3.45% |

#### P1缺失字段

来源：`v14C_P1_to_P5_JQ_result_bundle/p1_entry_feature_missing_summary.csv`，shape=(14, 6)

| feature | available_count | available_rate | missing_count | missing_reason_top1 | must_fix |
| --- | --- | --- | --- | --- | --- |
| entry_open_ratio | 116 | 100.0% | 0 | nan | 0 |
| entry_day_ret | 116 | 100.0% | 0 | nan | 0 |
| entry_close_to_high | 116 | 100.0% | 0 | nan | 0 |
| entry_volume_ratio | 115 | 99.1% | 1 | entry_volume_ratio_price_data_missing | 0 |
| entry_auc_ratio | 115 | 99.1% | 1 | previous_day_volume_missing | 1 |
| entry_ma5_distance | 116 | 100.0% | 0 | nan | 0 |
| entry_ma10_distance | 116 | 100.0% | 0 | nan | 0 |
| entry_turnover | 0 | 0.0% | 116 | turnover_data_unavailable | 1 |
| entry_rank | 0 | 0.0% | 116 | entry_rank_not_in_source_outputs | 1 |
| entry_score | 116 | 100.0% | 0 | nan | 0 |
| sector_strength_rank | 0 | 0.0% | 116 | sector_classification_not_available | 1 |
| breadth_up_ratio | 116 | 100.0% | 0 | nan | 0 |
| market_state | 0 | 0.0% | 116 | feature_not_generated | 0 |
| market_10d_ret | 0 | 0.0% | 116 | market_index_get_price_not_available | 1 |

#### P2 fast_loss

来源：`v14C_P1_to_P5_JQ_result_bundle/p2_fast_loss_experiment_summary.csv`，shape=(12, 23)

| variant | total_return | max_drawdown | sharpe | win_rate | fast_loss_count | fast_loss_amount | cap_exceeded_on_buy | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p2_confirm_add | 45.67% | -19.97% | 1.5459 | 30.17% | 59 | 535061.7935 | 0 | REAL_PATH_SIMULATION_REPLAY |
| p2_quick_fail_exit | 50.43% | -16.79% | 1.5053 | 31.03% | 64 | 830262.5045 | 0 | REAL_PATH_SIMULATION_REPLAY |
| p2_next_day_acceptance | 56.34% | -17.28% | 1.6629 | 31.03% | 67 | 813741.6830 | 0 | REAL_PATH_SIMULATION_REPLAY |

#### P3 cap/regime

来源：`v14C_P1_to_P5_JQ_result_bundle/p3_cap_and_regime_summary.csv`，shape=(8, 23)

| variant | total_return | max_drawdown | sharpe | win_rate | fast_loss_count | fast_loss_amount | cap_exceeded_on_buy | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p3_cap_fixed | 68.24% | -20.81% | 1.8060 | 29.31% | 65 | 844018.5355 | 0 | REAL_PATH_SIMULATION_REPLAY |
| p3_regime_position | 64.98% | -20.81% | 1.7495 | 27.59% | 65 | 839959.6522 | 0 | REAL_PATH_SIMULATION_REPLAY |

#### P4 promotion

来源：`v14C_P1_to_P5_JQ_result_bundle/p4_promotion_protection_summary.csv`，shape=(12, 23)

| variant | total_return | max_drawdown | sharpe | win_rate | fast_loss_count | fast_loss_amount | cap_exceeded_on_buy | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p4_no_promotion | 78.84% | -16.86% | 2.1251 | 35.34% | 62 | 811128.4873 | 0 | REAL_PATH_SIMULATION_REPLAY |
| p4_label_only_no_add | 68.24% | -20.81% | 1.8060 | 29.31% | 65 | 844018.5355 | 0 | REAL_PATH_SIMULATION_REPLAY |
| p4_promotion_protect | 76.14% | -19.58% | 2.0089 | 33.62% | 63 | 827269.5155 | 0 | REAL_PATH_SIMULATION_REPLAY |

#### P5 combined

来源：`v14C_P1_to_P5_JQ_result_bundle/p5_combined_observer_summary.csv`，shape=(4, 32)

| variant | total_return | max_drawdown | sharpe | win_rate | fast_loss_count | fast_loss_amount | cap_exceeded_on_buy | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p5_combined_observer | 43.29% | -13.11% | 1.4268 | 39.13% | 60 | 798166.9936 | 0 | REAL_PATH_SIMULATION_REPLAY |

#### 路径状态

来源：`v14C_P1_to_P5_JQ_result_bundle/p_path_simulation_status.csv`，shape=(5, 4)

| module | is_real_path_simulation | required_outputs | status |
| --- | --- | --- | --- |
| P1 | False | p1_jq_entry_features / p1_entry_feature_trade_log | FEATURE_COLLECTION_ONLY |
| P2 | True | p2_daily_nav,p2_trades,p2_positions,p2_decisions | REAL_PATH_SIMULATION_REPLAY |
| P3 | True | p3_daily_nav,p3_trades,p3_positions,p3_decisions | REAL_PATH_SIMULATION_REPLAY |
| P4 | True | p4_daily_nav,p4_trades,p4_positions,p4_decisions | REAL_PATH_SIMULATION_REPLAY |
| P5 | True | p5_daily_nav,p5_trades,p5_positions,p5_decisions | REAL_PATH_SIMULATION_REPLAY |

### D candidate 结论

来源：`role_rotation_result_bundle_V140C_D_candidate_research.zip` -> `D_candidate_summary_all.csv`。

| 候选 | total_return | max_drawdown | sharpe | win_rate | fast_loss_amount | cap_exceeded_on_buy | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D0_original_role_rotation | 61.91% | -22.42% | 1.6473 | 29.31% | 880789.6830 | 10 | 对照 |
| D1_cap_fixed_only | 68.24% | -20.81% | 1.8060 | 29.31% | 844018.5355 | 0 | 对照 |
| D2_no_promotion_take_profit | 78.84% | -16.86% | 2.1251 | 35.34% | 811128.4873 | 0 | 对照 |
| D3_no_promotion_take_profit_plus_cap_fixed | 78.84% | -16.86% | 2.1251 | 35.34% | 811128.4873 | 0 | D3 当前最优 |
| D4_promotion_protect_plus_cap_fixed | 76.14% | -19.58% | 2.0089 | 33.62% | 827269.5155 | 0 | 对照 |

当前已知研究结论：D3 是当前最优候选；D3 不能直接进主线；D3 不能直接实盘；下一步是 v1.4.0D observer，但 observer 当前仍有等价性和 cap 路径问题。

P1 entry feature outcome 对比摘录：

| outcome_group | feature | sample_count | mean | median | available_rate | missing_reason_top1 |
| --- | --- | --- | --- | --- | --- | --- |
| fast_loss | entry_open_ratio | 65 | 0.0178 | 0.0200 | 100.00% | nan |
| fast_loss | entry_day_ret | 65 | 0.0336 | 0.0352 | 100.00% | nan |
| fast_loss | entry_close_to_high | 65 | 0.9670 | 0.9711 | 100.00% | nan |
| fast_loss | entry_volume_ratio | 65 | 0.9423 | 0.9121 | 98.46% | entry_volume_ratio_price_data_missing |
| fast_loss | entry_auc_ratio | 65 | 0.0136 | 0.0116 | 98.46% | previous_day_volume_missing |
| fast_loss | entry_ma5_distance | 65 | 0.0366 | 0.0326 | 100.00% | nan |
| fast_loss | entry_ma10_distance | 65 | 0.0917 | 0.0829 | 100.00% | nan |
| fast_loss | breadth_up_ratio | 65 | 0.5153 | 0.5133 | 100.00% | nan |
| fast_loss | entry_score | 65 | 0.8101 | 0.8134 | 100.00% | nan |
| big_meat_10 | entry_open_ratio | 10 | 0.0087 | 0.0173 | 100.00% | nan |
| big_meat_10 | entry_day_ret | 10 | 0.0680 | 0.0780 | 100.00% | nan |
| big_meat_10 | entry_close_to_high | 10 | 0.9849 | 0.9869 | 100.00% | nan |
| big_meat_10 | entry_volume_ratio | 10 | 1.2089 | 1.0885 | 100.00% | nan |
| big_meat_10 | entry_auc_ratio | 10 | 0.0117 | 0.0098 | 100.00% | nan |
| big_meat_10 | entry_ma5_distance | 10 | 0.0492 | 0.0567 | 100.00% | nan |
| big_meat_10 | entry_ma10_distance | 10 | 0.1012 | 0.0796 | 100.00% | nan |
| big_meat_10 | breadth_up_ratio | 10 | 0.4708 | 0.4292 | 100.00% | nan |
| big_meat_10 | entry_score | 10 | 0.8325 | 0.8201 | 100.00% | nan |

## 6. D3 replay 定义与边界

- D3 名称：`D3_no_promotion_take_profit_plus_cap_fixed`
- D3 policy：`{"no_promotion": True, "cap_fixed": True}`
- D3 是 replay：是。
- 调用函数：`simulate_replay_path(...)`。
- D3 使用事件：`BUY / SELL / ROLE_PROMOTION_EXECUTE`（证据见 `research_v14C_P1_to_P5_master.py:596`、`:649`、`:677`）。
- D3 是否重新选股：否。
- D3 是否真实策略：否，是反事实路径重放。

D candidate 脚本证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| research_v14C_D_candidate_research.py | 70 | df_to_markdown_compat | def df_to_markdown_compat(df, n=80): |
| research_v14C_D_candidate_research.py | 95 | role_rotation_cap_check | "role_rotation_cap_check", |
| research_v14C_D_candidate_research.py | 172 | entry_row_id | entries["entry_row_id"] = range(len(entries)) |
| research_v14C_D_candidate_research.py | 181 | entry_row_id | for _, entry in entries.sort_values(["variant", "stock", "date", "entry_row_id"]).iterrows(): |
| research_v14C_D_candidate_research.py | 195 | matched_sell_index | "matched_sell_index": np.nan, |
| research_v14C_D_candidate_research.py | 196 | matched_sell_date | "matched_sell_date": pd.NaT, |
| research_v14C_D_candidate_research.py | 197 | matched_sell_reason | "matched_sell_reason": "", |
| research_v14C_D_candidate_research.py | 215 | matched_sell_index | "matched_sell_index": sell.name, |
| research_v14C_D_candidate_research.py | 216 | matched_sell_date | "matched_sell_date": sell.get("date"), |
| research_v14C_D_candidate_research.py | 217 | matched_sell_reason | "matched_sell_reason": sell.get("reason", ""), |
| research_v14C_D_candidate_research.py | 378 | simulate_replay_path | path = master.simulate_replay_path(tables, candidate_name, policy, start_date, end_date) |
| research_v14C_D_candidate_research.py | 387 | D3_no_promotion_take_profit_plus_cap_fixed | ("D3_no_promotion_take_profit_plus_cap_fixed", "replay", None, {"no_promotion": True, "cap_fixed": True}), |
| research_v14C_D_candidate_research.py | 402 | role_rotation_cap_check | cap_check=tables.get("role_rotation_cap_check", pd.DataFrame()) if name == "D0_original_role_rotation" else None, |
| research_v14C_D_candidate_research.py | 433 | D3_no_promotion_take_profit_plus_cap_fixed | d3 = full_row(candidate_outputs.get("D3_no_promotion_take_profit_plus_cap_fixed", {}).get("summary")) |
| research_v14C_D_candidate_research.py | 488 | df_to_markdown_compat | df_to_markdown_compat(fast_vs_meat, 80), |

P1~P5 master replay 证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| research_v14C_P1_to_P5_master.py | 579 | policy.get("cap_fixed") | if policy.get("cap_fixed") or policy.get("combined_observer"): |
| research_v14C_P1_to_P5_master.py | 596 | ROLE_PROMOTION_EXECUTE | mask = dec["decision"].astype(str).str.upper().eq("ROLE_PROMOTION_EXECUTE") |
| research_v14C_P1_to_P5_master.py | 649 | def simulate_replay_path | def simulate_replay_path(tables, variant, policy, start_date, end_date): |
| research_v14C_P1_to_P5_master.py | 677 | policy.get("no_promotion") | if policy.get("no_promotion"): |
| research_v14C_P1_to_P5_master.py | 678 | p4_no_promotion_take_profit | reason = "p4_no_promotion_take_profit" |

## 7. v1.4.0D observer 当前实现核查

| 核查项 | 结论 | 证据 |
| --- | --- | --- |
| 文件头 Source From | `战车A龙头3_v1.4.0B_fix_shadow_rotation_original_core.py` | `战车A龙头3_v1.4.0D_observer.py:6` |
| 是否存在 v1.4.0C 派生证据 | 否 | 文件头未指向 v1.4.0C；目录未发现 v1.4.0C 策略文件 |
| 是否存在 v1.4.0B 派生证据 | 是 | 文件头 Source From 指向 v1.4.0B_fix；下方仍保留 v1.4.0B header |
| 是否实现 cap_fixed | 部分实现 | core 买入与 satellite 买入有 CAP_FIXED_*；tail add 未进入 CAP_FIXED 缩单日志 |
| cap_fixed 覆盖路径 | core 初始买入、shadow satellite 买入 | `order_value(stock, buy_value)` 位于 line 1237 与 3516 附近 |
| 是否有路径绕过 cap_fixed | 是 | `check_livermore_tail_add` line 2956-2974：只做 full add_ratio cap 检查，然后 `order_value(stock, add_value)`，无 CAP_FIXED_TRIM/BUY_OK |
| 是否实现 no_promotion_take_profit | 部分实现 | `PROMOTION_BLOCK_TAKE_PROFIT` line 3668；触发条件为简化条件 |
| no_promotion 触发条件 | `pnl >= 0.03 and not below_ma5` | line 3657 附近 |
| 是否保留原 promotion 判断 | 无法确认，缺少证据 | v1.4.0D 未找到 ROLE_PROMOTION_EXECUTE；当前是 observer 简化条件，不是原 replay promotion 事件 |
| 是否实现 ENTRY_FEATURE_LOG | 是 | line 1102 |
| 是否实现 EXIT_OUTCOME_LOG | 是 | line 4982 |
| 日志字段是否完整 | 部分完整 | EXIT_OUTCOME_LOG 缺少 entry_type / slot_type / stage |
| 是否只允许 Dragon + deep_water 新开仓 | 大体保持 | 文件头和配置仍写 Dragon + deep_water；但需 smoke test 验证实际路径 |
| 是否修改 deep_water 阈值 | 未发现明确修改证据 | 未见 D observer 特有 deep_water 阈值改动；核心配置仍继承 v1.4.0B_fix |
| 是否扩大仓位 | 未发现扩大证据 | top1=0.35/top2=0.25/max_total=0.75；satellite=0.15 |

cap_fixed / 下单路径证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| 战车A龙头3_v1.4.0D_observer.py | 578 | submit_exit_order | if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=pnl): |
| 战车A龙头3_v1.4.0D_observer.py | 918 | submit_exit_order | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): |
| 战车A龙头3_v1.4.0D_observer.py | 954 | submit_exit_order | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): |
| 战车A龙头3_v1.4.0D_observer.py | 981 | submit_partial_stage_change | if submit_partial_stage_change( |
| 战车A龙头3_v1.4.0D_observer.py | 1201 | CAP_FIXED_TRIM | "CAP_FIXED_TRIM\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 1216 | CAP_FIXED_SKIP_NO_CAPACITY | "CAP_FIXED_SKIP_NO_CAPACITY\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 1237 | order_value(stock, buy_value) | if order_value(stock, buy_value) is not None: |
| 战车A龙头3_v1.4.0D_observer.py | 1257 | CAP_FIXED_BUY_OK | "CAP_FIXED_BUY_OK\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 1893 | submit_exit_order | if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=current_pnl): |
| 战车A龙头3_v1.4.0D_observer.py | 2815 | submit_exit_order | if submit_exit_order(stock, context, reason='orphan_sweeper', ret_snapshot=ret): |
| 战车A龙头3_v1.4.0D_observer.py | 2978 | order_value(stock, add_value) | od = order_value(stock, add_value) |
| 战车A龙头3_v1.4.0D_observer.py | 3474 | CAP_FIXED_TRIM | "CAP_FIXED_TRIM\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 3489 | CAP_FIXED_SKIP_NO_CAPACITY | "CAP_FIXED_SKIP_NO_CAPACITY\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 3516 | order_value(stock, buy_value) | od = order_value(stock, buy_value) |
| 战车A龙头3_v1.4.0D_observer.py | 3542 | CAP_FIXED_BUY_OK | "CAP_FIXED_BUY_OK\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 3700 | submit_exit_order | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): |
| 战车A龙头3_v1.4.0D_observer.py | 5089 | submit_exit_order | def submit_exit_order(stock, context, reason='', ret_snapshot=None): |
| 战车A龙头3_v1.4.0D_observer.py | 5134 | submit_partial_stage_change | def submit_partial_stage_change( |

promotion / no_promotion 证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| 战车A龙头3_v1.4.0D_observer.py | 3661 | pnl >= 0.03 | if pnl >= 0.03 and not below_ma5: |
| 战车A龙头3_v1.4.0D_observer.py | 3661 | not below_ma5 | if pnl >= 0.03 and not below_ma5: |
| 战车A龙头3_v1.4.0D_observer.py | 3662 | shadow_no_promotion_take_profit | reason = 'shadow_no_promotion_take_profit' |
| 战车A龙头3_v1.4.0D_observer.py | 3668 | PROMOTION_BLOCK_TAKE_PROFIT | "PROMOTION_BLOCK_TAKE_PROFIT\|date={}\|stock={}\|name={}\|" |

ENTRY / EXIT 日志证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| 战车A龙头3_v1.4.0D_observer.py | 1075 | log_entry_feature_observer | def log_entry_feature_observer(context, stock, name, entry_type, |
| 战车A龙头3_v1.4.0D_observer.py | 1102 | ENTRY_FEATURE_LOG | "ENTRY_FEATURE_LOG\|stock={}\|name={}\|date={}\|entry_type={}\|" |
| 战车A龙头3_v1.4.0D_observer.py | 1251 | log_entry_feature_observer | log_entry_feature_observer( |
| 战车A龙头3_v1.4.0D_observer.py | 2449 | finalize_exited_position | finalize_exited_position(stock, meta) |
| 战车A龙头3_v1.4.0D_observer.py | 3537 | log_entry_feature_observer | log_entry_feature_observer( |
| 战车A龙头3_v1.4.0D_observer.py | 4836 | finalize_exited_position | def finalize_exited_position(stock, meta): |
| 战车A龙头3_v1.4.0D_observer.py | 4982 | EXIT_OUTCOME_LOG | "EXIT_OUTCOME_LOG\|stock={}\|name={}\|entry_date={}\|exit_date={}\|" |

## 8. 所有买入 / 加仓 / 卖出路径扫描

| 函数名 | 调用代码 | 行号 | 买入/加仓/卖出 | 是否影响仓位增加 | 是否经过 cap_fixed | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| minute_stop_loss_all | if order_target_value(stock, 0) is not None: | 497 | 卖出/调仓 | 否 | 不适用 | 需看上下文 |
| minute_stop_loss_all | if order_target_value(stock, 0) is not None: | 497 | 卖出/调仓 | 否 | 不适用 | 需看上下文 |
| minute_stop_loss_all | if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=pnl): | 578 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| execute_sell_signal | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): | 918 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| execute_sell_signal | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): | 954 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| execute_sell_signal | if submit_partial_stage_change( | 981 | 半仓卖出 | 否 | 不适用 | 卖出路径 |
| execute_buy_orders | target_value = total_value * pos_ratio | 1192 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | buy_value = min(target_value, available_cap_value, planned_cash) | 1196 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | buy_value = min(target_value, available_cap_value, planned_cash) | 1196 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | if buy_value < target_value - 1e-6: | 1198 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | if buy_value < target_value - 1e-6: | 1198 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | "CAP_FIXED_TRIM\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 1201 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | target_value, buy_value, cap_limit * 100, | 1205 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | target_value, buy_value, cap_limit * 100, | 1205 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | (planned_position_value + buy_value) / total_value * 100, | 1207 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | lot_amount = int(buy_value / curr_price / 100) * 100 if curr_price > 0 else 0 | 1212 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | if buy_value <= 0 or lot_amount < 100: | 1214 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | "CAP_FIXED_SKIP_NO_CAPACITY\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 1216 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | target_value, actual_value, cap_limit * 100, | 1220 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | buy_value = actual_value | 1226 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | pos_ratio = buy_value / total_value | 1227 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | if buy_value > planned_cash or buy_value / curr_price < 100: | 1229 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | if order_value(stock, buy_value) is not None: | 1237 | core 初始买入 | 是 | 是（CAP_FIXED） | 低 |
| execute_buy_orders | if order_value(stock, buy_value) is not None: | 1237 | core 初始买入 | 是 | 是（CAP_FIXED） | 低 |
| execute_buy_orders | order_item['entry_value'] = buy_value | 1240 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | planned_position_value += buy_value | 1246 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | planned_cash -= buy_value | 1247 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | "CAP_FIXED_BUY_OK\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 1257 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | target_value, buy_value, cap_limit * 100, | 1261 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | target_value, buy_value, cap_limit * 100, | 1261 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | "stage=initial_buy\|order_value={:.2f}\|" | 1272 | 未知 | 否 | 否 | 待确认 |
| execute_buy_orders | buy_value | 1281 | 未知 | 否 | 否 | 待确认 |
| gap_down_confirm | if submit_exit_order(stock, context, reason=exit_reason, ret_snapshot=current_pnl): | 1893 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| _clear_pending_livermore_add | meta['pending_add_target_value'] = 0.0 | 2353 | 未知 | 否 | 否 | 待确认 |
| _sync_pending_livermore_add | meta['total_buy_value'] = ( | 2383 | 未知 | 否 | 否 | 待确认 |
| _sync_pending_livermore_add | float(meta.get('total_buy_value', 0.0) or 0.0) | 2384 | 未知 | 否 | 否 | 待确认 |
| sync_position_meta_with_real_positions | 'total_buy_value': float( | 2526 | 未知 | 否 | 否 | 待确认 |
| sync_position_meta_with_real_positions | 'pending_add_target_value': 0.0, | 2537 | 未知 | 否 | 否 | 待确认 |
| _orphan_sweeper_execute_impl | if submit_exit_order(stock, context, reason='orphan_sweeper', ret_snapshot=ret): | 2815 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| check_livermore_tail_add | add_value = total_value * add_ratio | 2970 | 未知 | 否 | 否 | 待确认 |
| check_livermore_tail_add | if add_value > context.portfolio.available_cash \ | 2971 | 未知 | 否 | 否 | 待确认 |
| check_livermore_tail_add | or add_value / curr_price < 100: | 2972 | 未知 | 否 | 否 | 待确认 |
| check_livermore_tail_add | od = order_value(stock, add_value) | 2978 | 尾盘赢家加仓 | 是 | 否（只有 cap 预检查，无缩单/CAP_FIXED日志） | BLOCKER：绕过 cap_fixed 缩单 |
| check_livermore_tail_add | od = order_value(stock, add_value) | 2978 | 尾盘赢家加仓 | 是 | 否（只有 cap 预检查，无缩单/CAP_FIXED日志） | BLOCKER：绕过 cap_fixed 缩单 |
| check_livermore_tail_add | meta['pending_add_target_value'] = add_value | 2996 | 未知 | 否 | 否 | 待确认 |
| check_livermore_tail_add | meta['pending_add_target_value'] = add_value | 2996 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value = total_value * target_ratio | 3468 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | buy_value = min(total_value * actual_ratio, float(context.portfolio.available_cash or 0)) | 3469 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | if buy_value < target_value - 1e-6: | 3471 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | if buy_value < target_value - 1e-6: | 3471 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | "CAP_FIXED_TRIM\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 3474 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value, buy_value, cap_limit * 100, | 3478 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value, buy_value, cap_limit * 100, | 3478 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | (current_position_ratio + buy_value / total_value) * 100, | 3480 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | lot_amount = int(buy_value / snapshot['current_price'] / 100) * 100 \ | 3484 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | "CAP_FIXED_SKIP_NO_CAPACITY\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 3489 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value, actual_value, cap_limit * 100, | 3493 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | buy_value = actual_value | 3499 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_ratio = buy_value / total_value | 3500 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | if buy_value <= 0 or buy_value / snapshot['current_price'] < 100: | 3501 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | od = order_value(stock, buy_value) | 3516 | shadow satellite 买入 | 是 | 是（CAP_FIXED） | 低 |
| _shadow_submit_satellite_buy | od = order_value(stock, buy_value) | 3516 | shadow satellite 买入 | 是 | 是（CAP_FIXED） | 低 |
| _shadow_submit_satellite_buy | 'entry_value': buy_value, | 3523 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | "CAP_FIXED_BUY_OK\|date={}\|stock={}\|name={}\|target_value={:.2f}\|" | 3542 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value, buy_value, cap_limit * 100, | 3546 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_value, buy_value, cap_limit * 100, | 3546 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | (current_position_ratio + buy_value / total_value) * 100, | 3548 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | "order_value={:.2f}\|reason={}".format( | 3554 | 未知 | 否 | 否 | 待确认 |
| _shadow_submit_satellite_buy | target_ratio * 100, buy_value, reason | 3556 | 未知 | 否 | 否 | 待确认 |
| shadow_rotation_exit_check | if submit_exit_order(stock, context, reason=reason, ret_snapshot=pnl): | 3700 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| finalize_exited_position | total_buy_value = float(meta.get('total_buy_value', 0.0) or 0.0) | 4897 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | realized_pnl_value = total_sell_value - total_buy_value | 4898 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | if total_buy_value <= 0: | 4915 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | accounting_reasons.append('total_buy_value_missing') | 4916 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | elif total_sell_value <= 0 or total_sell_value < total_buy_value * 0.50: | 4917 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | "final_sell_value={:.2f}\|total_buy_value={:.2f}\|" | 4933 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | total_buy_value, total_sell_value | 4939 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | if total_buy_value > 0: | 4953 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | final_trade_ret = realized_pnl_value / total_buy_value | 4954 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | "total_buy_value={:.2f}\|realized_pnl_value={:.2f}\|" | 4969 | 未知 | 否 | 否 | 待确认 |
| finalize_exited_position | total_buy_value, realized_pnl_value, accounting_error, | 4975 | 未知 | 否 | 否 | 待确认 |
| submit_exit_order | def submit_exit_order(stock, context, reason='', ret_snapshot=None): | 5089 | 清仓/退出 | 否 | 不适用 | 卖出路径 |
| submit_exit_order | od = order_target_value(stock, 0) | 5115 | 卖出/调仓 | 否 | 不适用 | 需看上下文 |
| submit_exit_order | od = order_target_value(stock, 0) | 5115 | 卖出/调仓 | 否 | 不适用 | 需看上下文 |
| submit_partial_stage_change | def submit_partial_stage_change( | 5134 | 半仓卖出 | 否 | 不适用 | 卖出路径 |

## 9. cap_fixed 核查

| 问题 | 结论 | 证据 |
| --- | --- | --- |
| 原总仓 cap | 0.75 | `战车A龙头3_v1.4.0D_observer.py:210` 配置 `max_total_position_ratio: 0.75`；`line 839` 设置 `g.max_total_position_ratio = 0.75` |
| initial cap | 0.60 | `line 211` 配置 `max_initial_position_ratio: 0.60` |
| single stock cap | 存在原逻辑 | `check_livermore_tail_add` line 2959-2964 对单股/总仓做跳过检查 |
| 是否按剩余 cap 缩单 | core/satellite 是；tail add 否 | core line 1191-1224；satellite line 3459-3496；tail add line 2956-2974 |
| 是否处理 100 股整数倍 | core/satellite 是 | `lot_amount = int(... / 100) * 100` line 1209 / 3480 |
| 是否处理现金不足 | core/satellite 是；tail add 仅跳过 | core `min(... planned_cash)`；satellite `min(... available_cash)`；tail add line 2967-2970 |
| 是否处理价格无效 | core/satellite 基本处理 | `curr_price > 0` / `snapshot[current_price] > 0` 的 lot 计算 |
| 是否记录 CAP_FIXED 日志 | core/satellite 是；tail add 否 | CAP_FIXED_* 出现 6 处；tail add 无 |

结论：`check_livermore_tail_add()` 没有执行 cap_fixed 缩单与 CAP_FIXED 日志，按用户规则列为 BLOCKER。

## 10. promotion 原逻辑与 observer 逻辑核查

原研究模拟中 promotion 证据：

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| research_role_rotation_direct_sim_v1.py | 165 | promotion_margin | 'promotion_margin': [8, 10, 12], |
| research_role_rotation_direct_sim_v1.py | 785 | promotion_margin | self.promotion_margin = self.params.get('promotion_margin', PROMOTION_MARGIN) |
| research_role_rotation_direct_sim_v1.py | 930 | promoted_core | trade_category = 'promoted_core' if pos.promoted else pos.role |
| research_role_rotation_direct_sim_v1.py | 1486 | promotion_margin | if sat_quality < weakest_score + self.promotion_margin: |
| research_role_rotation_direct_sim_v1.py | 1515 | ROLE_PROMOTION_EXECUTE | 'decision': 'ROLE_PROMOTION_EXECUTE', |
| research_role_rotation_direct_sim_v1.py | 1654 | promotion_count | promotion_count = 0 |
| research_role_rotation_direct_sim_v1.py | 1670 | promotion_count | # promotion_count |
| research_role_rotation_direct_sim_v1.py | 1672 | ROLE_PROMOTION_EXECUTE | promotion_count = len(decisions_df[decisions_df['decision'] == 'ROLE_PROMOTION_EXECUTE']) |
| research_role_rotation_direct_sim_v1.py | 1672 | promotion_count | promotion_count = len(decisions_df[decisions_df['decision'] == 'ROLE_PROMOTION_EXECUTE']) |
| research_role_rotation_direct_sim_v1.py | 1674 | ROLE_PROMOTION_EXECUTE | promotion_count = len(decisions_df[decisions_df['decision_type'] == 'ROLE_PROMOTION_EXECUTE']) |
| research_role_rotation_direct_sim_v1.py | 1674 | promotion_count | promotion_count = len(decisions_df[decisions_df['decision_type'] == 'ROLE_PROMOTION_EXECUTE']) |
| research_role_rotation_direct_sim_v1.py | 1676 | promotion_count | promotion_count = 0 |
| research_role_rotation_direct_sim_v1.py | 1683 | ROLE_PROMOTION_EXECUTE | replacement_count = len(decisions_df[(decisions_df['decision'] == 'ROLE_PROMOTION_EXECUTE') & valid_replaced]) |
| research_role_rotation_direct_sim_v1.py | 1685 | ROLE_PROMOTION_EXECUTE | replacement_count = len(decisions_df[(decisions_df['decision_type'] == 'ROLE_PROMOTION_EXECUTE') & valid_replaced]) |
| research_role_rotation_direct_sim_v1.py | 1708 | promotion_count | 'promotion_count': promotion_count, |
| research_role_rotation_direct_sim_v1.py | 1756 | promoted_core | categories = ['core', 'satellite', 'promoted_core', 'all'] |
| research_role_rotation_direct_sim_v1.py | 1951 | promotion_count | ('promotion_count', '晋级次数', '{:.0f}'), |
| research_role_rotation_direct_sim_v1.py | 2035 | promotion_count | promo_count = rr_full[0].get('promotion_count', 0) if rr_full else 0 |
| research_role_rotation_direct_sim_v1.py | 2147 | promotion_margin | 'promotion_margin': PROMOTION_MARGIN, |
| research_role_rotation_direct_sim_v1.py | 2409 | promotion_count | 'promotion_count': summary.get('promotion_count', 0), |
| research_role_rotation_direct_sim_v1.py | 2436 | promotion_count | 'promotion_count': summary.get('promotion_count', 0), |
| research_role_rotation_direct_sim_v1.py | 2480 | promotion_count | sensitivity_df = safe_to_csv(sensitivity_df, os.path.join(output_dir, 'role_rotation_sensitivity.csv'), ['param', 'value', 'total_return', 'annual_return', 'max_drawdown', 'sharpe' |
| research_role_rotation_direct_sim_v1.py | 2481 | promotion_count | cost_sensitivity_df = safe_to_csv(cost_sensitivity_df, os.path.join(output_dir, 'role_rotation_cost_sensitivity.csv'), ['cost_scenario', 'total_return', 'annual_return', 'max_drawd |
| research_role_rotation_direct_sim_v1.py | 2634 | promotion_count | ['variant', 'segment', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count']) |
| research_role_rotation_direct_sim_v1.py | 2652 | promotion_count | ['param', 'value', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count']) |
| research_role_rotation_direct_sim_v1.py | 2654 | promotion_count | ['cost_scenario', 'total_return', 'annual_return', 'max_drawdown', 'sharpe', 'trade_count', 'win_rate', 'promotion_count', 'exit_count']) |
| research_role_rotation_direct_sim_v1.py | 2702 | promotion_count | {'metric': 'total_promotion_count', 'value': total_promotions}, |
| research_role_rotation_direct_sim_v1.py | 2703 | promotion_count | {'metric': 'exited_promotion_count', 'value': exited_promotions}, |
| research_role_rotation_direct_sim_v1.py | 2704 | promotion_count | {'metric': 'held_promotion_count', 'value': held_promotions}, |
| research_role_rotation_direct_sim_v1.py | 2737 | promoted_core | promoted_big_meat_trades = obs_profits[(obs_profits['pnl_pct'] >= 0.10) & (obs_profits['trade_category'] == 'promoted_core')] if not obs_profits.empty else pd.DataFrame() |

对比结论：

| 项目 | 原研究/replay | 当前 observer | 结论 |
| --- | --- | --- | --- |
| promotion 判断来源 | `research_role_rotation_direct_sim_v1.py` 与 `research_v14C_P1_to_P5_master.py` 中 `ROLE_PROMOTION_EXECUTE` 事件 | v1.4.0D 中未找到 ROLE_PROMOTION_EXECUTE；使用 `pnl >= 0.03 and not below_ma5` | 不等价 |
| 原动作 | ROLE_PROMOTION_EXECUTE 后晋级/替换/角色变化 | PROMOTION_BLOCK_TAKE_PROFIT 后 submit_exit_order 清仓 | 动作已改变 |
| 是否只改动作 | 无法确认 | 当前 trigger 也简化了 | 无法确认只改动作 |
| 是否清理状态 | 依赖原 submit_exit_order/finalize 流程 | 调用原退出流程 | 大体复用，但需回测日志确认 |
| 是否处理卖不出去 pending_exit | 复用 submit_exit_order/pending_exit | 复用 | 需 smoke test 验证 |
| 是否最终触发 EXIT_OUTCOME_LOG | 理论上 finalize 后触发 | EXIT_OUTCOME_LOG 在 finalize_exited_position 后输出 | 若订单最终成交退出则应触发；未成交当日不一定立即触发 |

必须写明：当前 observer 与 D3 replay 不完全等价。

## 11. deep_water 与 entry 边界

| 核查项 | 结论 | 证据 |
| --- | --- | --- |
| deep_water 定义函数 | 无法在本档案中完整反推 | 需进一步阅读 get_dragon_stock_list / tpl 判定；本扫描只做 grep 证据 |
| 原条件 | Dragon + deep_water-only | 文件头 line 45 附近保留“新开仓仅允许 Dragon + deep_water”；配置 line 235 保留 `dragon_bear_allow_deep_water` |
| observer 是否修改条件 | 未发现明确修改证据 | 未见 observer 专属 deep_water 阈值改动 |
| 是否只允许 Dragon + deep_water 新开仓 | 大体保持，但需小区间日志验证 | `entry_type == dragon_follow` / `tpl deep_water` 多处存在 |
| 其他 tpl / entry_type 是否进入买入 | shadow_satellite 是卫星路径；是否严格 deep_water 取决于 WATCH_POOL snapshot | `_shadow_submit_satellite_buy` mark_pending_buy entry_type=shadow_satellite, tpl=deep_water |
| bear 下 half 逻辑 | 仍存在 | `dragon_bear_allow_deep_water: half` line 235 |

## 12. ENTRY / EXIT 日志闭环

### ENTRY_FEATURE_LOG

| 项目 | 结论 | 证据 |
| --- | --- | --- |
| 触发函数 | `log_entry_feature_observer` | line 1102 |
| 触发时机 | `order_value` 返回非 None 后 | core line 1237 后 line 1248；satellite line 3516 后 line 3533 |
| 是否成交确认后 | 否，属于下单提交后，不是成交确认后 | 未等待 sync/fill；存在订单未最终成交但记录 ENTRY_FEATURE_LOG 的可能 |
| 是否参与交易决策 | 否 | 函数只 log.info，不回写交易决策字段 |
| 字段 | stock/name/date/entry_type/open_ratio/day_ret/close_to_high/volume_ratio/auc_ratio/ma5/ma10/breadth/score | line 1102-1117 |
| 缺失字段 | entry_turnover、sector_strength_rank 等未在 observer 日志中出现 | 与 P1 补采集字段不完全一致 |

### EXIT_OUTCOME_LOG

| 项目 | 结论 | 证据 |
| --- | --- | --- |
| 触发函数 | `finalize_exited_position` | EXIT_OUTCOME_LOG line 4982，位于 TRADE_CLOSE 后 |
| 是否所有退出触发 | 只要走 finalize_exited_position 且非提前 return，应触发 | 若订单未成交/未 finalize，当日不触发 |
| 止损/止盈/promotion block/pending retry | 理论上通过 submit_exit_order -> finalize 后触发 | 需回测日志确认 |
| 字段 | stock/name/entry_date/exit_date/exit_reason/pnl_pct/pnl_val/hold_days/is_fast_loss/is_big_meat_10/is_super_meat_20 | line 4982-4992 |
| 缺失字段 | entry_type、slot_type、stage | 未在 EXIT_OUTCOME_LOG 字符串中出现 |

### 日志断链风险

- `PROMOTION_BLOCK_TAKE_PROFIT` 不一定当日对应 `EXIT_OUTCOME_LOG`；如果卖不出去，需要 pending_exit 后续 finalize 才会出现 outcome。
- ENTRY 与 EXIT 匹配仍需 stock + entry_date/exit_date 或交易 id；当前 observer 没有单独 trade_id。
- 同一股票多次交易仍有错配风险，需研究脚本使用 entry_date / matched_sell_index 类字段。

## 13. research_v14C_D_candidate_research.py 状态

| 核查项 | 结论 | 证据 |
| --- | --- | --- |
| 是否存在 df_to_markdown_compat | 是 | line 70 |
| 是否完全没有 from __future__ import annotations | 是 | grep 无匹配 |
| 是否读取 role_rotation_cap_check.csv | 是 | line 95 |
| D0 cap 是否优先用 role_rotation_cap_check.csv | 是 | line 402-403 将 cap_check/cap_variant 传入 summary |
| entry_feature_outcome_labeled 是否保留 entry_row_id / matched_sell_* | 是 | entry_row_id line 172；matched_sell_index/date/reason line 195-217 |
| 空 entries / trades / sells 时输出列是否完整 | 部分可确认 | 脚本有 no_match 输出字段；需用空表单元测试进一步确认 |
| D0~D4 summary 是否包含 full / train / validation / oos | 是 | zip 中 D_candidate_summary_all.csv 含 20 行：5 candidate x 4 segment |
| top3_profit_concentration 如何计算 | 由 summary/replay 聚合输出 | D_candidate_summary_all.csv 中存在该列；具体公式需追 master calc 函数 |
| cap 检查来自哪个文件 | D0 来自 `role_rotation_cap_check.csv`；D1-D4 来自 replay summary | line 402-403 与 zip summary 证据 |

| 文件 | 行号 | 模式 | 代码片段 |
| --- | --- | --- | --- |
| research_v14C_D_candidate_research.py | 70 | df_to_markdown_compat | def df_to_markdown_compat(df, n=80): |
| research_v14C_D_candidate_research.py | 95 | role_rotation_cap_check | "role_rotation_cap_check", |
| research_v14C_D_candidate_research.py | 172 | entry_row_id | entries["entry_row_id"] = range(len(entries)) |
| research_v14C_D_candidate_research.py | 181 | entry_row_id | for _, entry in entries.sort_values(["variant", "stock", "date", "entry_row_id"]).iterrows(): |
| research_v14C_D_candidate_research.py | 195 | matched_sell_index | "matched_sell_index": np.nan, |
| research_v14C_D_candidate_research.py | 196 | matched_sell_date | "matched_sell_date": pd.NaT, |
| research_v14C_D_candidate_research.py | 197 | matched_sell_reason | "matched_sell_reason": "", |
| research_v14C_D_candidate_research.py | 215 | matched_sell_index | "matched_sell_index": sell.name, |
| research_v14C_D_candidate_research.py | 216 | matched_sell_date | "matched_sell_date": sell.get("date"), |
| research_v14C_D_candidate_research.py | 217 | matched_sell_reason | "matched_sell_reason": sell.get("reason", ""), |
| research_v14C_D_candidate_research.py | 378 | simulate_replay_path | path = master.simulate_replay_path(tables, candidate_name, policy, start_date, end_date) |
| research_v14C_D_candidate_research.py | 387 | D3_no_promotion_take_profit_plus_cap_fixed | ("D3_no_promotion_take_profit_plus_cap_fixed", "replay", None, {"no_promotion": True, "cap_fixed": True}), |
| research_v14C_D_candidate_research.py | 402 | role_rotation_cap_check | cap_check=tables.get("role_rotation_cap_check", pd.DataFrame()) if name == "D0_original_role_rotation" else None, |
| research_v14C_D_candidate_research.py | 433 | D3_no_promotion_take_profit_plus_cap_fixed | d3 = full_row(candidate_outputs.get("D3_no_promotion_take_profit_plus_cap_fixed", {}).get("summary")) |
| research_v14C_D_candidate_research.py | 488 | df_to_markdown_compat | df_to_markdown_compat(fast_vs_meat, 80), |

## 14. 已知问题清单

### BLOCKER

| 编号 | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| B1 | 无法确认 v1.4.0D observer 是 v1.4.0C 的严格派生版本 | observer 文件头 Source From 指向 v1.4.0B_fix；未发现 v1.4.0C 策略 py | 不能把 observer 当作 v1.4.0C 策略化版本验收 |
| B2 | 当前 no_promotion_take_profit 与 D3 replay 不完全等价 | D3 replay 使用 ROLE_PROMOTION_EXECUTE；observer 使用 `pnl >= 0.03 and not below_ma5` 简化条件 | 不能用 observer 回测直接证明 D3 replay 结论 |
| B3 | `check_livermore_tail_add()` 绕过 cap_fixed 缩单/日志 | line 2956-2974 直接 `add_value=total_value*add_ratio` 后 `order_value(stock, add_value)` | 可能出现 cap_fixed 观察版与 D3 cap_fixed 边界不一致 |

### HIGH

| 编号 | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| H1 | ENTRY_FEATURE_LOG 不是成交确认后日志 | core/satellite 在 order_value 返回后立即 log | 可能记录未成交/被取消订单 |
| H2 | EXIT_OUTCOME_LOG 字段不完整 | 缺 entry_type / slot_type / stage | 后续归因需要从 meta/其他日志补字段 |
| H3 | 文件头存在双版本头 | v1.4.0D 新头之后仍保留 v1.4.0B 头 | 新窗口接手容易误读来源 |

### MEDIUM

| 编号 | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| M1 | D3 是反事实 replay，不是重新选股路径 | research_v14C_D_candidate_research.py line 378 调用 simulate_replay_path | 不能直接进入主线 |
| M2 | P1 字段仍有缺失 | entry_turnover/entry_rank 可用率 0% | entry quality 建模需要补字段 |
| M3 | D candidate 输出主要在 zip 内 | 未发现解压后的完整 D candidate 目录 | 查阅不如目录文件直观 |
| M4 | 部分 Git 状态已有 staged/untracked 历史文件 | git status 显示多项 A/??/AM | 后续提交需严格指定文件 |

### LOW

| 编号 | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| L1 | 部分历史注释/中文在 PowerShell 输出中可能乱码 | 终端显示编码问题；Python 读取正常 | 影响可读性，不影响代码 |
| L2 | 历史策略/报告较多，命名不完全统一 | 目录内存在多代 WORKLOG、报告、zip、结果包 | 需要索引文档维持接手效率 |

问题数量：BLOCKER=3，HIGH=3，MEDIUM=4，LOW=2。

## 15. 后续研究路线

### 阶段 1：补齐代码与档案

- 修复 BLOCKER：确认 v1.4.0C 策略来源，或明确以 v1.4.0B_fix 为 observer 基线。
- 将 no_promotion trigger 对齐 D3 replay 的 ROLE_PROMOTION_EXECUTE 事件，或在文档中明确 observer 只是近似版。
- 对 `check_livermore_tail_add()` 补 cap_fixed 缩单/日志，或在 observer 中暂时关闭该路径做纯 D3 对照。

### 阶段 2：小区间 smoke test

- 候选区间：2026-01-01 ~ 2026-01-31。
- 如果该区间缺少 promotion / cap 事件，需要另选有事件的历史区间。
- 目标不是看收益，而是看机制日志：`CAP_FIXED_TRIM`、`CAP_FIXED_SKIP_NO_CAPACITY`、`CAP_FIXED_BUY_OK`、`PROMOTION_BLOCK_TAKE_PROFIT`、`ENTRY_FEATURE_LOG`、`EXIT_OUTCOME_LOG`、`cap_exceeded_on_buy=0`。

### 阶段 3：完整区间回测

- 当前不建议直接跑完整区间机制验收。
- 待 BLOCKER 修复后，再跑 2025-07-01 ~ 2026-06-14，对比原 v1.4.0C、D3 replay、v1.4.0D observer 实际回测。

### 阶段 4：日志归因

- 用 observer 的 ENTRY / EXIT 日志继续分析 fast_loss、big_meat、super_meat、normal_loss / normal_win。

### 阶段 5：v1.4.0E 研究方向

- 只有 D observer 稳定后，才考虑 fast_loss 早期识别、entry_quality_score 重构、大肉保护、市场状态分层、promotion 长期暂停/废除、cap_fixed 默认风控模块。

## 16. 新窗口交接摘要

可复制给新 ChatGPT 窗口：

```text
当前项目：D:\Code\JQ\战车A。用户偏好中文 Markdown、证据优先、每次明确可改/不可改文件、禁止未授权 git add/commit/联网/实盘化。当前主线不是 v1.4.0D，主策略仍是 战车A龙头3.py（v1.2.0-auction-prefilter）。v1.4.0C 没有找到独立策略 py 文件，主要证据是 research_role_rotation_direct_sim_v1.py 和 role_rotation_result_bundle V140C。P1~P5 研究输出在 v14C_P1_to_P5_JQ_result_bundle。D candidate 输出在 role_rotation_result_bundle_V140C_D_candidate_research.zip。D3_no_promotion_take_profit_plus_cap_fixed 是当前研究最优候选，但它是反事实 replay，不是实盘策略。v1.4.0D_observer.py 当前 Source From 指向 v1.4.0B_fix，不是 v1.4.0C；实现了 cap_fixed 日志、ENTRY_FEATURE_LOG、EXIT_OUTCOME_LOG、PROMOTION_BLOCK_TAKE_PROFIT，但存在 BLOCKER：1）无法确认严格派生 v1.4.0C；2）no_promotion 触发用 pnl>=3% 且不破 MA5，和 D3 replay 的 ROLE_PROMOTION_EXECUTE 不等价；3）check_livermore_tail_add 加仓路径绕过 cap_fixed 缩单/日志。下一步先修 BLOCKER，再跑 2026-01 小区间 smoke test。禁止进主线、禁止实盘、禁止 git add/commit、禁止联网。
```

## 17. 最终保守结论

结论选择：B. 只能跑 smoke test，不能做机制验收。

| 权限/动作 | 是否允许 | 理由 |
| --- | --- | --- |
| 是否允许完整区间回测 | 否 | v1.4.0D observer 仍有 BLOCKER，完整区间结果会混入等价性问题 |
| 是否允许进主线 | 否 | D3 是 replay；observer 不是严格等价实现 |
| 是否允许实盘化 | 否 | 当前只是 observer/research-only |
| 是否允许 git add / git commit | 否 | 本轮明确禁止 |
| 是否允许联网 | 否 | 本轮明确禁止 |
| 是否允许小区间 smoke test | 是，仅 smoke test | 只能检查日志链路和机制是否触发，不能视为机制验收通过 |
