# Audit Outputs File Index

| File Path | Description / Purpose | Key Fields | Target Reviewer |
| :--- | :--- | :--- | :--- |
| `00_README/README_v140D_smoke_test_audit.md` | General directory overview and principles | Log source, usage constraints | All reviewers |
| `01_raw_log_extract/key_events_extract.txt` | Consolidated line-by-line key events | Logging category, original log lines | QA / Dev |
| `01_raw_log_extract/error_extract.txt` | Verified list of actual errors, exceptions, and tracebacks (0 real errors found) | Exception messages or 'No real Traceback/ERROR/TASK_ERROR/Exception found' | QA / Dev |
| `01_raw_log_extract/cap_related_extract.txt` | Key log lines relating to capacity and tail addition | `CAP_FIXED_*`, `LIVERMORE_ADD_SUBMIT` | Risk Control Team |
| `02_cap_fixed/cap_fixed_events.csv` | Full listing of all capacity check events | `date`, `time`, `stock`, `name`, `path`, `target_value`, `actual_value`, `current_total_ratio`, `post_total_ratio`, `cap_limit`, `trim_reason` | Risk Control Team |
| `02_cap_fixed/cap_post_buy_check.csv` | Specific validation of buying limits | `post_total_ratio`, `is_over_0_75`, `mark_to_market_or_pre_existing` | Risk Control Team |
| `02_cap_fixed/cap_fixed_summary.md` | Summary analysis of capacity protections | Event counts, max ratios, violations checklist | Risk Control Team |
| `03_promotion_block/promotion_block_events.csv` | Logged promotion blocks and metadata | `promotion_logic_source`, `d3_equivalence`, `pnl_pct`, `below_ma5` | Strategy Team |
| `03_promotion_block/promotion_block_chain_check.csv` | Trace of exit loop logic execution | `has_shadow_exit_signal`, `has_exit_outcome_log`, exit reasons | Strategy Team / Dev |
| `03_promotion_block/promotion_block_summary.md` | Summary analysis of promotion blocking | Verification results, assertion outcomes | Strategy Team |
| `04_entry_exit/entry_feature_events.csv` | Individual entry events list | `entry_type`, `entry_score`, `log_stage`, `filled_confirmed` | Strategy Team |
| `04_entry_exit/exit_outcome_events.csv` | Individual exit events list | `entry_date`, `exit_date`, `exit_reason`, `slot_type`, `stage` | Strategy Team |
| `04_entry_exit/entry_exit_matched.csv` | Matched trades chronological list | `stock`, `entry_date`, `exit_date`, `hold_days`, `pnl_pct`, `is_fast_loss` | Strategy Team |
| `04_entry_exit/entry_exit_summary.md` | Matching statistics and check results | Matched/unmatched counts, checklists | Strategy Team |
| `05_tail_add/tail_add_events.csv` | Tail additions list under cap limits | `original_target_value`, `actual_value`, ratios | Risk Control Team |
| `05_tail_add/tail_add_cap_check.csv` | Validation that tail adds went through capacity check | `has_cap_fixed`, `is_bypass` | Risk Control Team |
| `05_tail_add/tail_add_summary.md` | Summary analysis of tail addition protection | Protective checks status, timing window check | Risk Control Team |
| `06_final_report/v140D_smoke_test_report.md` | Final audit report with conservative verdict | Audit findings, verdicts, warnings | All Stakeholders |
| `99_manifest/audit_manifest.json` | JSON metadata of generated files | Counts, checksums/paths, forbidden flags | System Integrator |
