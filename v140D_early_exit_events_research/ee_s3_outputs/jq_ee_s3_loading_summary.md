# v140D Early-Exit Events -- S3 Loading Summary

Research-only. S3 = event loading ONLY (no price fetch, no variants). Gate choice and dedup rule are NOT decided here.

## Subclass counts (unified event table)

| subclass | n | source |
|---|---|---|
| ee_promotion_block | 7 | S2-reconciled 7/7 (verbatim) |
| ee_failed_trade | 12 | oos_failed_trades.csv (loss-only) |
| ee_ledger_early (>0% gate rows) | 13 | full ledger, profitable exits |

## ee_ledger_early by profit gate (spec 1.1a)

| gate | n | overlap w/ promotion-block | new (non-overlap) |
|---|---|---|---|
| >0% | 13 | 7 | 6 |
| >=3% | 13 | 7 | 6 |
| >=5% | 12 | 6 | 6 |

## ee_ledger_early exit_pnl_pct distribution by gate (percent units)

| gate | n | min | p25 | median | p75 | max | mean |
|---|---|---|---|---|---|---|---|
| >0% | 13 | 4.68 | 7.63 | 9.75 | 19.17 | 54.64 | 16.59 |
| >=3% | 13 | 4.68 | 7.63 | 9.75 | 19.17 | 54.64 | 16.59 |
| >=5% | 12 | 5.57 | 8.76 | 10.68 | 19.75 | 54.64 | 17.59 |

## Overlap clarity (spec 1.1b -- NOT auto-removed)

- **>0%**: overlapping promotion-block names (7): fujing, hengtong, jiangte, saiwu, shenkeji, xinjinlu_2, xizang_ct
  - new non-overlap names (6): jinkai, litong, tianrun, wanbangde, xinjinlu_1, zhangyuan
- **>=3%**: overlapping promotion-block names (7): fujing, hengtong, jiangte, saiwu, shenkeji, xinjinlu_2, xizang_ct
  - new non-overlap names (6): jinkai, litong, tianrun, wanbangde, xinjinlu_1, zhangyuan
- **>=5%**: overlapping promotion-block names (6): fujing, hengtong, jiangte, shenkeji, xinjinlu_2, xizang_ct
  - new non-overlap names (6): jinkai, litong, tianrun, wanbangde, xinjinlu_1, zhangyuan

ee_failed_trade is loss-only -> NO overlap with ee_ledger_early (profit-only) or ee_promotion_block (profit-only).

## What S3 does NOT decide

- Which gate (>0% / >=3% / >=5%) becomes the main one -- user decides after seeing these numbers.
- Whether overlapping events are deduped to ee_promotion_block -- user decides. Default *suggestion* (non-binding): assign overlap to ee_promotion_block, drop from ee_ledger_early.
