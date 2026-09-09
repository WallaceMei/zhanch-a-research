# CAP_FIXED Protection Audit Summary

## Event Counts
- **CAP_FIXED_TRIM**: 14 times
- **CAP_FIXED_SKIP_NO_CAPACITY**: 7 times
- **CAP_FIXED_BUY_OK**: 44 times

## Capacity Violations Check
- **Maximum `post_total_ratio` on BUY_OK**: 74.88%
- **BUY_OK post_total_ratio > 75% occurrence**: 0 times
  - *No initial or tail additions caused post-buy total ratio to exceed 75%.*

## Mark to Market / Pre-existing Exposure Analysis
- **TRIM/SKIP events where current_total_ratio > 75%**: 4 times
  - These events are correctly marked as `mark_to_market_or_pre_existing` in `cap_post_buy_check.csv`.
  - Since these events were skips or trims, no new positions were created when capacity was already full, verifying that the capacity limit is working properly. The >75% total ratio prior to the trade decision was caused by asset appreciation (mark-to-market) or existing positions, not buying capacity breaches.
