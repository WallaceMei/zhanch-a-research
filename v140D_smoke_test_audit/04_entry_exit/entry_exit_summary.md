# Entry / Exit Matching Analysis

## Summary Statistics
- **ENTRY_FEATURE_LOG count**: 38 entries
- **EXIT_OUTCOME_LOG count**: 37 exits
- **Successfully Matched Trades**: 37 trades
- **Unmatched Entries**: 1 entries
- **Unmatched Exits**: 0 exits

## Validation
1. **Entry Log Fields Checklist**:
   - Includes `log_stage=order_submitted` for all: True
   - Includes `filled_confirmed=0` for all: True
2. **Exit Log Fields Checklist**:
   - Contains `entry_type`: True
   - Contains `slot_type`: True
   - Contains `stage`: True

## Unmatched Entries Analysis
- **Unmatched Entries count**: 1
- *Details of unmatched entries*:
  - Stock: `600378.XSHG` (昊华科技) Entry Date: `2026-06-05` (Position remained open at the end of the backtest period)

## Unmatched Exits Analysis
- **Unmatched Exits count**: 0
- *Details of unmatched exits*:
  - None (All exits were successfully matched to preceding entries)
