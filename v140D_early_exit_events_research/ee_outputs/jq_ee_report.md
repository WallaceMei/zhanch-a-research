# v140D Early-Exit Events -- Multi-Direction Counterfactual Report

Research-only. No orders, no backtest engine, no live trading, no mechanism design, no parameter search. Strategy code and ledgers are read-only.

Locked config (user, after S3): ee_ledger_early gate = >=3%; overlapping 7 events assigned to ee_promotion_block and removed from ee_ledger_early. Subclasses mutually exclusive: promotion 7 + failed 12 + ledger_early 6 = 25 events.
Anchor price = exit-day close, uniform across subclasses (comparability; differs slightly from S2 promotion-only run).

## Q1. Subclass sample sizes and overlap

- ee_promotion_block: 7 (S2-reconciled, verbatim)
- ee_failed_trade: 12 (loss-only; no overlap with the profit subclasses)
- ee_ledger_early (>=3%, dedup): 6 new events; the 7 overlapping profitable exits were moved to ee_promotion_block.
- Gate counts seen at S3: >0%=13, >=3%=13, >=5%=12 (overlap with the 7 promotion = 7/7/6). The profitable-exit sample barely expands; the 6 new ledger_early events are all big-meat dragon_half_protect (>=11%).
- Events with usable forward path (ok): 25 of 25.

## Q2. Layer one -- per-subclass distribution (independent)

| subclass | variant | n | hit_rate | mean | median | top10%_share | sum_excl_top10% | pos_after_excl | proxy |
|---|---|---|---|---|---|---|---|---|---|
| ee_promotion_block | pv_immediate_full_exit | 7 | 0.0000 | 0.0000 | 0.0000 | nan | 0.0000 | False | low |
| ee_promotion_block | pv_half_exit_hold_half | 7 | 0.4286 | 0.0144 | -0.0042 | 0.7769 | 0.0224 | True | low |
| ee_promotion_block | pv_delay_1d_confirm | 7 | 0.2857 | 0.0128 | -0.0302 | 1.7480 | -0.0668 | False | low |
| ee_promotion_block | pv_trail_from_high | 7 | 0.4286 | 0.0119 | -0.0510 | 2.1333 | -0.0948 | False | high |
| ee_promotion_block | pv_downgrade_small_pos | 7 | 0.4286 | 0.0096 | -0.0028 | 0.7769 | 0.0149 | True | low |
| ee_failed_trade | pv_immediate_full_exit | 12 | 0.0000 | 0.0000 | 0.0000 | nan | 0.0000 | False | low |
| ee_failed_trade | pv_half_exit_hold_half | 12 | 0.1667 | -0.0035 | -0.0076 | -1.9854 | -0.1247 | False | low |
| ee_failed_trade | pv_delay_1d_confirm | 12 | 0.1667 | -0.0070 | -0.0151 | -1.9854 | -0.2494 | False | low |
| ee_failed_trade | pv_trail_from_high | 12 | 0.5000 | 0.0193 | 0.0057 | 0.9742 | 0.0060 | True | high |
| ee_failed_trade | pv_downgrade_small_pos | 12 | 0.1667 | -0.0023 | -0.0050 | -1.9854 | -0.0831 | False | low |
| ee_ledger_early | pv_immediate_full_exit | 6 | 0.0000 | 0.0000 | 0.0000 | nan | 0.0000 | False | low |
| ee_ledger_early | pv_half_exit_hold_half | 6 | 0.3333 | -0.0104 | -0.0089 | -0.4003 | -0.0875 | False | low |
| ee_ledger_early | pv_delay_1d_confirm | 6 | 0.3333 | -0.0208 | -0.0178 | -0.4003 | -0.1749 | False | low |
| ee_ledger_early | pv_trail_from_high | 6 | 0.3333 | -0.0128 | -0.0272 | -1.3585 | -0.1808 | False | high |
| ee_ledger_early | pv_downgrade_small_pos | 6 | 0.3333 | -0.0069 | -0.0059 | -0.4003 | -0.0583 | False | low |

Read: compare ee_promotion_block vs ee_failed_trade vs ee_ledger_early on the same variant -- do the early exits behave like the same illness?

## Q3. Concentration -- are gains outlier-driven?

For each subclass x variant, 'pos_after_excl' = does the summed captured_extra stay positive after removing the top 10% of events? If it flips negative, the gain was outlier-driven. See the table above (sum_excl_top10% and pos_after_excl columns).

## Q4. Layer two -- mergeability of the three subclasses

Per-subclass exit_pnl_pct and captured_extra distributions plus cross-subclass sign agreement are in jq_ee_mergeability.csv. Key cross-subclass signals (captured_extra):

| variant | same_sign_mean | same_sign_median | mean_spread | hint |
|---|---|---|---|---|
| pv_immediate_full_exit | True | True | 0.0000 | consistent_direction |
| pv_half_exit_hold_half | False | True | 0.0248 | divergent |
| pv_delay_1d_confirm | False | True | 0.0336 | divergent |
| pv_trail_from_high | False | False | 0.0320 | divergent |
| pv_downgrade_small_pos | False | True | 0.0165 | divergent |

exit_pnl_pct populations: ee_failed_trade is loss-only while the other two are profit-only -- a strong prior that the subclasses are NOT one population. Merging is NOT done by default; the pooled rows in the CSV are for inspection only. Final merge decision is the user's.

## Q5. Do MA5-class protections still fail on 'kill-then-rally'?

Inspect pv_half_exit_hold_half / pv_delay_1d_confirm / pv_downgrade_small_pos (all proxy=low) in the per-subclass table. If hit_rate stays low and means hug zero/negative on the larger ledger_early + failed samples, the MA5 logic still misses kill-then-rally moves.

## Q6. Is the trail class (proxy=high) still ranking-only?

pv_trail_from_high uses daily highs and misses intraday peaks (proxy_distortion_flag=high). It stays RANKING-ONLY and is excluded from core verdict evidence regardless of how good it looks. See jq_ee_sensitivity.csv for its knob dispersion.

## Q7. Is the sample large enough to discuss mechanism design?

This is a LABEL, not a hard gate. design-relevant n = 12 via largest single subclass (subclasses NOT mergeable -> no pooling across exit semantics); sample_sufficiency = thin (soft hint threshold = 15). Per-subclass ok events: {'ee_promotion_block': 7, 'ee_failed_trade': 12, 'ee_ledger_early': 6} ; pooled = 25.

Important: when the subclasses are NOT mergeable, the design-relevant n is the largest SINGLE subclass (no pooling across different exit semantics) -- the pooled 25 does NOT count as 'sample sufficient' unless mergeability holds.

## Q8. Are master-line / live / tuning / new-strategy still forbidden?

YES. This stage designs nothing, tunes nothing, writes no new strategy, touches no master line, places no orders, and makes no git changes.

## SUGGESTED VERDICT (reference only -- NOT final)

**VERDICT_subclass_heterogeneous_split**

This is a heuristic suggestion derived from the CSVs. Concentration + mergeability are the core drivers. Evidence:
- ok events per subclass: {'ee_promotion_block': 7, 'ee_failed_trade': 12, 'ee_ledger_early': 6} ; pooled=25
- low-distortion variants consistent in direction across subclasses: 0/3 (none) -> mergeable_signal=False
- design-relevant n = 12 via largest single subclass (subclasses NOT mergeable -> no pooling across exit semantics) -> sample_sufficiency=thin (soft hint threshold=15, NOT a hard gate)
- subclass x low-variant cells where gains survive removing top 10%: 2/9
- subclasses diverge on most low-distortion variants -> not one population; study per subclass

Suggestion rules: heterogeneity is checked FIRST; sample sufficiency is a SOFT label checked AFTER, and uses pooled n ONLY when the subclasses look mergeable. protection_robust_design_next is suggested ONLY with consistent cross-subclass direction AND gains that survive removing the top 10% on a non-pooled-padded sample.

## AWAITING MANUAL CONFIRMATION (final verdict = user's call)

The FINAL verdict is set by the user after reading the real CSVs above. The suggestion is advisory only and may be overridden. Choose ONE: VERDICT_protection_robust_design_next / VERDICT_still_outlier_driven_no_design / VERDICT_subclass_heterogeneous_split / VERDICT_data_insufficient_continue. Per spec 5, do NOT pick protection_robust_design_next unless the CSVs clearly support it (concentration survives top-10% removal AND subclasses are genuinely mergeable on an adequate, non-padded sample).

FINAL VERDICT (user decision): 不引入 protection 机制,现有退出逻辑保持现状,封档。

依据:

1. 盈利早退事件结构性稀缺(去重后 distinct=13),protection 收益靠 fujing/jiangte/hengtong 3 笔 promotion 大肉撑,剔最大 1 笔即由 +3.8% 翻负至 -4.0%,无法支撑统计意义的机制设计。
2. 三子类语义异质(failed-trade 纯亏损)、时间窗口错配(failed 集中 4-5 月、ledger 集中 1-4 月),不可合并;mergeability 判定 divergent。
3. captured_extra 显示现有 3% 止盈点位事后大多未损失上涨空间——现有退出机制无需修正。
4. protection 属下游逻辑补丁,与"保持策略简洁、聚焦因子有效性"的主方向相悖。
5. 全程 research-only,未改主策略、未写新机制、未实盘、未调参。
