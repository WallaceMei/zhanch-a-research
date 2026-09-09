# -*- coding: utf-8 -*-
#
# detect_promotion_block_from_log.py
#
# Route A detector (S2): reconcile promotion-block events directly from the
# authoritative observer log. NO re-implemented scanner, NO invented rule,
# NO JoinQuant API. It only parses the PROMOTION_BLOCK_TAKE_PROFIT lines that
# the observer itself emitted -- these ARE the ground-truth events.
#
# S2 scope: run ONLY over the log segment that produced the original 7 events
# and verify all 7 are recovered (block date within +/-1 trade day). It does
# NOT run the full-range universe (that is S3) and does NOT score variants
# (that is S4).
#
# Engineering: UTF-8 no BOM, ASCII code region, Python 3.6 compatible,
# relative paths only. The detector reads a local text artifact; it does not
# call any JoinQuant API and does not pretend to.

import os
import re

# Relative path to the authoritative observer log (route A source).
LOG_PATH = os.path.join("..", "log", "jq_v140D_20260101_20260614.log.txt")

# The line the observer emits when the promotion-block take-profit fires.
BLOCK_TAG = "PROMOTION_BLOCK_TAKE_PROFIT|date="

# Field regex (matches on ASCII fields only; the Chinese name field is skipped
# so log encoding does not affect parsing or matching).
BLOCK_RE = re.compile(
    r"PROMOTION_BLOCK_TAKE_PROFIT\|date=(\d{4}-\d{2}-\d{2})"
    r"\|stock=(\d{6}\.[A-Z]+)\|"
    r".*?pnl_pct=([\-0-9.]+)%\|"
    r".*?satellite_entry_date=(\d{4}-\d{2}-\d{2})\|"
    r"satellite_entry_price=([0-9.]+)\|"
    r"exit_price=([0-9.]+)\|"
    r"pnl_val=([\-0-9.]+)\|"
    r"hold_days=(\d+)"
)

# The original 7 promotion-block events to reconcile against (ground truth from
# the prior audit). Matching is by stock CODE; date checked within +/-1 trade
# day. pinyin label is for human reading only.
EXPECTED_SEVEN = [
    ("600487.XSHG", "2026-01-28", "hengtong"),
    ("603212.XSHG", "2026-02-04", "saiwu"),
    ("000510.XSHE", "2026-02-27", "xinjinlu"),
    ("600773.XSHG", "2026-03-13", "xizang_ct"),
    ("002176.XSHE", "2026-04-24", "jiangte"),
    ("002222.XSHE", "2026-05-07", "fujing"),
    ("000021.XSHE", "2026-05-27", "shenkeji"),
]


def parse_block_events(log_path):
    """Parse every PROMOTION_BLOCK_TAKE_PROFIT line from the log into dicts.
    Reads with gb18030 (the observer log is GBK-family) but matching uses only
    ASCII fields, so a decode slip in the name never breaks reconciliation."""
    events = []
    with open(log_path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("gb18030", errors="replace")
    for line in text.split("\n"):
        if BLOCK_TAG not in line:
            continue
        m = BLOCK_RE.search(line)
        if not m:
            events.append({"parse_error": True, "raw": line.strip()[:120]})
            continue
        events.append({
            "event_date": m.group(1),
            "stock": m.group(2),
            "pnl_pct": float(m.group(3)),
            "satellite_entry_date": m.group(4),
            "satellite_entry_price": float(m.group(5)),
            "exit_price": float(m.group(6)),
            "pnl_val": float(m.group(7)),
            "hold_days": int(m.group(8)),
            "parse_error": False,
        })
    return events


def _date_to_ordinal(date_str):
    y, mo, d = (int(x) for x in date_str.split("-"))
    # Simple proleptic day count; good enough for a +/-1 day proximity check
    # within the same month/adjacent days (no trade calendar needed because the
    # expected dates come from the same log family and should match exactly).
    return y * 372 + mo * 31 + d


def reconcile(events):
    """Match the parsed events against EXPECTED_SEVEN by stock code."""
    by_code = {}
    for ev in events:
        if ev.get("parse_error"):
            continue
        by_code.setdefault(ev["stock"], []).append(ev)

    rows = []
    recovered = 0
    for code, exp_date, label in EXPECTED_SEVEN:
        matches = by_code.get(code, [])
        if not matches:
            rows.append({
                "label": label, "stock": code, "expected_date": exp_date,
                "found": False, "matched_date": "", "date_diff_days": "",
                "pnl_pct": "", "note": "no PROMOTION_BLOCK line for this code",
            })
            continue
        # Pick the closest-dated match.
        exp_ord = _date_to_ordinal(exp_date)
        best = min(matches, key=lambda e: abs(_date_to_ordinal(e["event_date"]) - exp_ord))
        diff = abs(_date_to_ordinal(best["event_date"]) - exp_ord)
        within = diff <= 1
        if within:
            recovered += 1
        rows.append({
            "label": label, "stock": code, "expected_date": exp_date,
            "found": True, "matched_date": best["event_date"],
            "date_diff_days": diff, "pnl_pct": best["pnl_pct"],
            "note": "ok" if within else "date outside +/-1",
        })
    return rows, recovered


def main():
    if not os.path.exists(LOG_PATH):
        print("LOG_NOT_FOUND:", LOG_PATH)
        return
    events = parse_block_events(LOG_PATH)
    clean = [e for e in events if not e.get("parse_error")]
    perr = [e for e in events if e.get("parse_error")]
    print("total_block_lines =", len(events))
    print("parsed_ok =", len(clean))
    print("parse_errors =", len(perr))

    rows, recovered = reconcile(clean)
    print("recovered =", recovered, "/", len(EXPECTED_SEVEN))
    print("")
    print("label,stock,expected_date,found,matched_date,date_diff_days,pnl_pct,note")
    for r in rows:
        print("{label},{stock},{expected_date},{found},{matched_date},"
              "{date_diff_days},{pnl_pct},{note}".format(**r))

    # Extra events in the log beyond the expected 7 (should be 0 in S2 window).
    expected_codes = set(c for c, _, _ in EXPECTED_SEVEN)
    extras = [e for e in clean if e["stock"] not in expected_codes]
    print("")
    print("extra_block_events_beyond_seven =", len(extras))
    for e in extras:
        print("EXTRA:", e["event_date"], e["stock"], e["pnl_pct"])

    gate = (recovered == len(EXPECTED_SEVEN))
    print("")
    print("S2_GATE_7_OF_7 =", gate)


if __name__ == "__main__":
    main()
