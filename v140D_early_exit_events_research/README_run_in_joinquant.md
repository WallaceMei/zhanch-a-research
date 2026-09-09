# v140D Early-Exit Events -- run instructions (JoinQuant research)

Research-only. No orders, no backtest engine, no live trading, no mechanism
design, no parameter search. Strategy code and ledgers are read-only.

## What this is

One JoinQuant research script that studies three early-exit subclasses with
five spec-locked protection variants (counterfactual, ranking/measurement only):

- `ee_promotion_block` (7) -- S2-reconciled promotion-block take-profits.
- `ee_failed_trade` (12) -- OOS failed trades (loss-only).
- `ee_ledger_early` (6) -- ledger positions exited while still profitable,
  gate >=3%, overlapping 7 removed (locked S3 user decision).

= 25 mutually-exclusive events. Anchor price = exit-day close (uniform across
subclasses for comparability).

## How to run

1. Upload `research_v140D_ee_jq_counterfactual.py` into a JoinQuant research
   notebook (jqdata enabled).
2. Run:  `%run research_v140D_ee_jq_counterfactual.py`  (or import + main()).
3. Outputs land in `ee_outputs/`:
   - jq_ee_event_universe.csv   (25 events + subclass + data_quality_flag)
   - jq_ee_cases.csv            (event x 5 variants, with subclass)
   - jq_ee_by_subclass_summary.csv  (layer 1: per-subclass distribution + concentration)
   - jq_ee_mergeability.csv     (layer 2: mergeability evidence; pooled = inspection only)
   - jq_ee_sensitivity.csv      (trail_pct x keep_frac dispersion; no best mark)
   - jq_ee_report.md            (answers spec Q1-Q8 + auto VERDICT)
   - v140D_ee_outputs.zip       (flat bundle of the 6 files above)
4. Download the zip.

## Reading the verdict

The script auto-selects ONE of the four spec verdicts from the CSVs:
- protection_robust_design_next -- ONLY if cross-subclass direction is
  consistent AND gains survive removing the top 10% of events on >=15 ok events.
- subclass_heterogeneous_split  -- subclasses diverge (not one population).
- still_outlier_driven_no_design -- gains vanish after removing the top 10%.
- data_insufficient_continue    -- proxy run, or sample too small/poor quality.

Concentration + mergeability are the core drivers. trail (proxy=high) is
ranking-only and is NOT core evidence. The user makes the final call and may
override using the tables in the report.

## Local validation done (NOT a JoinQuant run)

Local checks only: py_compile, no BOM, pure-ASCII code, get_price has no
`count`, no order/backtest/schedule calls, all relative paths, the 5 variant
scorers are byte-identical to the accepted script, and the S5/S6/S7 aggregation
+ verdict logic was unit-tested with synthetic paths. Real captured_extra
values require the JoinQuant run; local runs are PROXY mode (all zeros).
