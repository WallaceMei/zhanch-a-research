# -*- coding: utf-8 -*-
#
# research_v140D_ee_s3_load_events.py
#
# v140D Early-Exit Events study -- STAGE S3 ONLY: event loading.
#
# Scope (spec section 7.5, S3):
#   - Load THREE early-exit subclasses into one unified event table.
#   - DO NOT fetch prices. DO NOT compute the 5 protection variants.
#   - ee_ledger_early is loaded at THREE profit gates (>0% / >=3% / >=5%);
#     this stage reports the count per gate and the overlap with the 7
#     reconciled promotion-block events. It does NOT pick a gate and does
#     NOT auto-dedup -- those decisions are left to the user after seeing
#     the numbers (spec section 1.1).
#
# HARD CONSTRAINTS:
#   - Research-only. No order / order_value / order_target / run_backtest /
#     schedule_function. No get_price at this stage (no price fetch in S3).
#   - All paths RELATIVE. Python 3.6 compatible. Code region pure ASCII.
#   - Subclass events come ONLY from the real reconciled ledger / logs; no
#     invented rows; ee_ledger_early holds ONLY positions that really exited.
#
# Sources (all real, already reconciled in S1/S2):
#   - Full realized ledger (37 trades):
#       v140D_smoke_test_audit/04_entry_exit/entry_exit_matched.csv
#   - The 12 OOS failed trades:
#       v140D_failure_analysis/oos_failed_trades.csv
#   - The 7 promotion-block take-profits (S2 reconciled, 7/7):
#       v140D_promotion_protection_design/promotion_protection_event_casebook.csv
#       (also embedded as PROMOTION_EVENTS in the accepted counterfactual script)
#   The ledger rows below are transcribed verbatim from those files; the
#   romanized names match the accepted counterfactual script BASELINE_LEDGER.

import os
import csv

import numpy as np


OUT_DIR = "ee_s3_outputs"
OUT_UNIVERSE = "jq_ee_event_universe.csv"
OUT_SUMMARY_MD = "jq_ee_s3_loading_summary.md"

OOS_START = "2026-04-16"  # v140D OOS window start (entry-date basis for phase)
OOS_END = "2026-06-14"

# ---------------------------------------------------------------------------
# Full realized ledger (37 trades), transcribed from entry_exit_matched.csv.
# Fields: name, stock, entry_date, exit_date, exit_reason, pnl_pct (PERCENT
# units, e.g. 7.63 means +7.63%), pnl_val (RMB), hold_days.
# name is unique (duplicate stocks are suffixed _1/_2 as in the ledger).
# ---------------------------------------------------------------------------

LEDGER = [
    ("xinjinlu_1", "000510.XSHE", "2026-01-05", "2026-01-28", "dragon_half_protect", 54.64, 19138.0, 23),
    ("zhenghe", "605069.XSHG", "2026-01-05", "2026-01-12", "dragon_fail_fast", -1.63, -400.0, 7),
    ("shenkai", "002278.XSHE", "2026-01-13", "2026-01-15", "dragon_confirm_stop", -5.90, -1305.0, 2),
    ("shiyun", "603920.XSHG", "2026-01-20", "2026-01-22", "dragon_fail_fast", -2.15, -387.0, 2),
    ("shengda", "000603.XSHE", "2026-01-21", "2026-01-22", "gap_down_stop", -3.60, -495.0, 1),
    ("hengtong", "600487.XSHG", "2026-01-26", "2026-01-28", "shadow_no_promotion_take_profit", 7.63, 1190.0, 2),
    ("litong", "603629.XSHG", "2026-01-30", "2026-02-13", "dragon_half_protect", 39.89, 22804.0, 14),
    ("jinchen", "603396.XSHG", "2026-02-02", "2026-02-03", "dragon_delayed_stop", -3.63, -1080.0, 1),
    ("saiwu", "603212.XSHG", "2026-02-03", "2026-02-04", "shadow_no_promotion_take_profit", 4.68, 820.0, 1),
    ("tianrun", "002283.XSHE", "2026-02-05", "2026-03-03", "dragon_half_protect", 21.49, 10793.0, 26),
    ("zhende", "603301.XSHG", "2026-02-13", "2026-02-24", "dragon_confirm_stop", -5.25, -1416.0, 11),
    ("zhangyuan", "002378.XSHE", "2026-02-25", "2026-03-05", "dragon_half_protect", 19.17, 8778.0, 8),
    ("xinjinlu_2", "000510.XSHE", "2026-02-25", "2026-02-27", "shadow_no_promotion_take_profit", 9.14, 1881.0, 2),
    ("xiamen_w", "600549.XSHG", "2026-03-05", "2026-03-06", "dragon_confirm_stop", -5.24, -2055.0, 1),
    ("jinkai", "600821.XSHG", "2026-03-06", "2026-03-17", "dragon_half_protect", 11.62, 7348.0, 11),
    ("meiliyun", "000815.XSHE", "2026-03-11", "2026-03-13", "dragon_confirm_stop", -5.40, -2156.0, 2),
    ("xizang_ct", "600773.XSHG", "2026-03-11", "2026-03-13", "shadow_no_promotion_take_profit", 5.57, 672.0, 2),
    ("changfei", "601869.XSHG", "2026-03-18", "2026-03-19", "dragon_fail_fast", -1.96, -858.0, 1),
    ("huasheng", "002980.XSHE", "2026-03-18", "2026-03-19", "dragon_confirm_stop", -6.28, -2450.0, 1),
    ("wanbangde", "002082.XSHE", "2026-03-31", "2026-04-09", "dragon_half_protect", 16.72, 9230.0, 9),
    ("zaisheng", "603601.XSHG", "2026-04-02", "2026-04-03", "dragon_confirm_stop", -5.45, -1968.0, 1),
    ("zhaoshang", "601872.XSHG", "2026-04-07", "2026-04-09", "dragon_confirm_stop", -6.19, -2000.0, 2),
    ("hesheng", "002824.XSHE", "2026-04-14", "2026-04-24", "dragon_fail_fast_confirmed", -0.37, -210.0, 10),
    ("xizang_ky", "000762.XSHE", "2026-04-14", "2026-05-13", "dragon_fail_fast_confirmed", -0.92, -588.0, 29),
    ("yujing_1", "002943.XSHE", "2026-04-16", "2026-04-22", "shadow_below_ma5_loss", -1.43, -328.0, 6),
    ("jiangte", "002176.XSHE", "2026-04-22", "2026-04-24", "shadow_no_promotion_take_profit", 9.75, 2299.0, 2),
    ("rendong", "002647.XSHE", "2026-04-27", "2026-05-15", "dragon_fail_fast", -2.95, -1637.0, 18),
    ("fujing", "002222.XSHE", "2026-05-06", "2026-05-07", "shadow_no_promotion_take_profit", 5.81, 1078.0, 1),
    ("tongda", "002560.XSHE", "2026-05-07", "2026-05-11", "minute_stop_loss", -5.06, -1296.0, 4),
    ("hongchang", "603002.XSHG", "2026-05-13", "2026-05-15", "minute_stop_loss", -6.98, -1695.0, 2),
    ("yujing_2", "002943.XSHE", "2026-05-18", "2026-05-25", "dragon_fail_fast_confirmed", -0.20, -112.0, 7),
    ("jingquanhua", "002885.XSHE", "2026-05-18", "2026-05-19", "dragon_fail_fast", -3.05, -1104.0, 1),
    ("tongding", "002491.XSHE", "2026-05-22", "2026-05-26", "dragon_fail_fast", -2.09, -799.0, 4),
    ("shenkeji", "000021.XSHE", "2026-05-25", "2026-05-27", "shadow_no_promotion_take_profit", 9.60, 1975.0, 2),
    ("mulinsen", "002745.XSHE", "2026-05-27", "2026-05-29", "dragon_fail_fast", -3.17, -1768.0, 2),
    ("xinjieneng", "605111.XSHG", "2026-05-28", "2026-05-29", "dragon_fail_fast", -3.07, -1045.0, 1),
    ("shengquan", "605589.XSHG", "2026-05-28", "2026-05-29", "minute_stop_loss", -5.27, -1032.0, 1),
]

LEDGER_COLS = ("name", "stock", "entry_date", "exit_date", "exit_reason",
               "pnl_pct", "pnl_val", "hold_days")

# The 7 promotion-block events (S2 reconciled 7/7) -- identified by name.
PROMOTION_NAMES = [
    "hengtong", "saiwu", "xinjinlu_2", "xizang_ct",
    "jiangte", "fujing", "shenkeji",
]

# The 12 OOS failed trades, verbatim from oos_failed_trades.csv -- by name.
FAILED_NAMES = [
    "hesheng", "xizang_ky", "yujing_1", "rendong", "tongda", "hongchang",
    "yujing_2", "jingquanhua", "tongding", "mulinsen", "xinjieneng", "shengquan",
]

# Profit gates for ee_ledger_early (percent units).
GATES = [("gt0", 0.0, ">0%"), ("ge3", 3.0, ">=3%"), ("ge5", 5.0, ">=5%")]


def _row_dict(row):
    return dict(zip(LEDGER_COLS, row))


def _phase_for(entry_date):
    return "oos" if entry_date >= OOS_START else "pre_oos"


def build_events():
    """Return list of unified event dicts across the three subclasses.

    Columns per spec 3.1 (plus extra traceability columns):
      subclass, stock, name, entry_date, exit_date, exit_reason,
      exit_pnl_pct (percent units), pnl_val, hold_days, phase,
      gate_gt0, gate_ge3, gate_ge5, overlap_promotion_block,
      data_quality_flag
    Gate flags are only meaningful for ee_ledger_early (1/0); for the other
    two subclasses they are left blank. overlap_promotion_block flags
    ee_ledger_early rows that ARE one of the 7 promotion-block events.
    """
    by_name = {r[0]: _row_dict(r) for r in LEDGER}
    promo_set = set(PROMOTION_NAMES)
    failed_set = set(FAILED_NAMES)

    events = []

    def base_cols(d, subclass):
        return {
            "subclass": subclass,
            "stock": d["stock"],
            "name": d["name"],
            "entry_date": d["entry_date"],
            "exit_date": d["exit_date"],
            "exit_reason": d["exit_reason"],
            "exit_pnl_pct": d["pnl_pct"],
            "pnl_val": d["pnl_val"],
            "hold_days": d["hold_days"],
            "phase": _phase_for(d["entry_date"]),
            "gate_gt0": "",
            "gate_ge3": "",
            "gate_ge5": "",
            "overlap_promotion_block": "",
            "data_quality_flag": "ok",  # S3 has no price; ledger record is complete
        }

    # 1) ee_promotion_block (7), reused verbatim, not re-detected.
    for nm in PROMOTION_NAMES:
        events.append(base_cols(by_name[nm], "ee_promotion_block"))

    # 2) ee_failed_trade (12), verbatim from oos_failed_trades.csv.
    for nm in FAILED_NAMES:
        events.append(base_cols(by_name[nm], "ee_failed_trade"))

    # 3) ee_ledger_early: every ledger position that exited while STILL
    #    profitable (pnl_pct > 0). Gate flags mark >0% / >=3% / >=5%.
    for r in LEDGER:
        d = _row_dict(r)
        if d["pnl_pct"] <= 0.0:
            continue
        row = base_cols(d, "ee_ledger_early")
        row["gate_gt0"] = 1 if d["pnl_pct"] > 0.0 else 0
        row["gate_ge3"] = 1 if d["pnl_pct"] >= 3.0 else 0
        row["gate_ge5"] = 1 if d["pnl_pct"] >= 5.0 else 0
        row["overlap_promotion_block"] = 1 if d["name"] in promo_set else 0
        events.append(row)

    # Sanity: no failed trade should ever be profitable (loss-only population).
    for nm in FAILED_NAMES:
        assert by_name[nm]["pnl_pct"] <= 0.0, "failed trade unexpectedly profitable: " + nm

    return events


def _percentiles(values):
    if not values:
        return {}
    arr = np.asarray(values, dtype=float)
    return {
        "n": len(values),
        "min": float(np.min(arr)),
        "p25": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "p75": float(np.percentile(arr, 75)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def gate_stats(events):
    """Per-gate count, overlap count and overlap name list, pnl percentiles."""
    le = [e for e in events if e["subclass"] == "ee_ledger_early"]
    out = {}
    for gid, thr, label in GATES:
        flag = "gate_" + gid
        members = [e for e in le if e[flag] == 1]
        overlap = [e for e in members if e["overlap_promotion_block"] == 1]
        pct = [e["exit_pnl_pct"] for e in members]
        out[gid] = {
            "label": label,
            "count": len(members),
            "overlap_count": len(overlap),
            "overlap_names": sorted(e["name"] for e in overlap),
            "non_overlap_names": sorted(e["name"] for e in members
                                        if e["overlap_promotion_block"] != 1),
            "pct_stats": _percentiles(pct),
        }
    return out


def write_universe_csv(events, path):
    cols = ["subclass", "stock", "name", "entry_date", "exit_date",
            "exit_reason", "exit_pnl_pct", "pnl_val", "hold_days", "phase",
            "gate_gt0", "gate_ge3", "gate_ge5", "overlap_promotion_block",
            "data_quality_flag"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for e in events:
            w.writerow(e)


def write_summary_md(events, stats, path):
    n_promo = sum(1 for e in events if e["subclass"] == "ee_promotion_block")
    n_failed = sum(1 for e in events if e["subclass"] == "ee_failed_trade")
    n_le = sum(1 for e in events if e["subclass"] == "ee_ledger_early")

    L = []
    L.append("# v140D Early-Exit Events -- S3 Loading Summary")
    L.append("")
    L.append("Research-only. S3 = event loading ONLY (no price fetch, no "
             "variants). Gate choice and dedup rule are NOT decided here.")
    L.append("")
    L.append("## Subclass counts (unified event table)")
    L.append("")
    L.append("| subclass | n | source |")
    L.append("|---|---|---|")
    L.append("| ee_promotion_block | {0} | S2-reconciled 7/7 (verbatim) |".format(n_promo))
    L.append("| ee_failed_trade | {0} | oos_failed_trades.csv (loss-only) |".format(n_failed))
    L.append("| ee_ledger_early (>0% gate rows) | {0} | full ledger, profitable exits |".format(n_le))
    L.append("")
    L.append("## ee_ledger_early by profit gate (spec 1.1a)")
    L.append("")
    L.append("| gate | n | overlap w/ promotion-block | new (non-overlap) |")
    L.append("|---|---|---|---|")
    for gid, thr, label in GATES:
        s = stats[gid]
        L.append("| {0} | {1} | {2} | {3} |".format(
            label, s["count"], s["overlap_count"],
            s["count"] - s["overlap_count"]))
    L.append("")
    L.append("## ee_ledger_early exit_pnl_pct distribution by gate (percent units)")
    L.append("")
    L.append("| gate | n | min | p25 | median | p75 | max | mean |")
    L.append("|---|---|---|---|---|---|---|---|")
    for gid, thr, label in GATES:
        p = stats[gid]["pct_stats"]
        L.append("| {0} | {1} | {2:.2f} | {3:.2f} | {4:.2f} | {5:.2f} | "
                 "{6:.2f} | {7:.2f} |".format(
                     label, p["n"], p["min"], p["p25"], p["median"],
                     p["p75"], p["max"], p["mean"]))
    L.append("")
    L.append("## Overlap clarity (spec 1.1b -- NOT auto-removed)")
    L.append("")
    for gid, thr, label in GATES:
        s = stats[gid]
        L.append("- **{0}**: overlapping promotion-block names "
                 "({1}): {2}".format(label, s["overlap_count"],
                                      ", ".join(s["overlap_names"]) or "none"))
        L.append("  - new non-overlap names ({0}): {1}".format(
            s["count"] - s["overlap_count"],
            ", ".join(s["non_overlap_names"]) or "none"))
    L.append("")
    L.append("ee_failed_trade is loss-only -> NO overlap with ee_ledger_early "
             "(profit-only) or ee_promotion_block (profit-only).")
    L.append("")
    L.append("## What S3 does NOT decide")
    L.append("")
    L.append("- Which gate (>0% / >=3% / >=5%) becomes the main one -- user "
             "decides after seeing these numbers.")
    L.append("- Whether overlapping events are deduped to ee_promotion_block "
             "-- user decides. Default *suggestion* (non-binding): assign "
             "overlap to ee_promotion_block, drop from ee_ledger_early.")
    L.append("")
    with open(path, "w") as f:
        f.write("\n".join(L))


def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    events = build_events()
    stats = gate_stats(events)

    uni_path = os.path.join(OUT_DIR, OUT_UNIVERSE)
    md_path = os.path.join(OUT_DIR, OUT_SUMMARY_MD)
    write_universe_csv(events, uni_path)
    write_summary_md(events, stats, md_path)

    # Console echo.
    print("wrote:", uni_path)
    print("wrote:", md_path)
    print("subclass counts: promotion=%d failed=%d ledger_early(>0)=%d" % (
        sum(1 for e in events if e["subclass"] == "ee_promotion_block"),
        sum(1 for e in events if e["subclass"] == "ee_failed_trade"),
        sum(1 for e in events if e["subclass"] == "ee_ledger_early"),
    ))
    for gid, thr, label in GATES:
        s = stats[gid]
        p = s["pct_stats"]
        print("ledger_early %s: n=%d overlap=%d new=%d | pct min/med/max = "
              "%.2f/%.2f/%.2f mean=%.2f" % (
                  label, s["count"], s["overlap_count"],
                  s["count"] - s["overlap_count"],
                  p["min"], p["median"], p["max"], p["mean"]))
        print("   overlap:", s["overlap_names"])
        print("   new    :", s["non_overlap_names"])


if __name__ == "__main__":
    main()
