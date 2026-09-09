#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parse JoinQuant experiment logs into experiment_summary.csv."""

import argparse
import csv
import glob
import os
import re


DIAG_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2}).*DIAG\|(?P<body>.*)")
STAT_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}).*持仓数=(?P<positions>\d+)\s+"
    r"净值=(?P<nav>-?\d+(?:\.\d+)?)\s+"
    r"回撤=(?P<drawdown>-?\d+(?:\.\d+)?)%\s+"
    r"胜率=(?P<win_rate>-?\d+(?:\.\d+)?)%\s+"
    r"盈亏比=(?P<profit_loss_ratio>-?\d+(?:\.\d+)?)\s+"
    r"总交易=(?P<total_trades>\d+)"
)

FIELDS = [
    "variant",
    "exp",
    "date",
    "nav",
    "drawdown",
    "win_rate",
    "profit_loss_ratio",
    "total_trades",
    "positions",
    "A_buys",
    "A_sell",
    "regime",
    "trend",
    "pool",
    "score",
]

SUMMARY_FIELDS = [
    "variant",
    "exp",
    "start_date",
    "end_date",
    "start_nav",
    "end_nav",
    "total_return",
    "max_drawdown",
    "win_rate",
    "profit_loss_ratio",
    "total_trades",
    "rows",
]


def parse_diag_body(body):
    parsed = {}
    for part in body.strip().split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def parse_log(path):
    rows = []
    latest_diag_by_date = {}
    latest_diag = {}

    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        for line in f:
            diag_match = DIAG_RE.search(line)
            if diag_match:
                latest_diag = parse_diag_body(diag_match.group("body"))
                latest_diag_by_date[diag_match.group("date")] = latest_diag
                continue

            stat_match = STAT_RE.search(line)
            if not stat_match:
                continue

            date = stat_match.group("date")
            diag = latest_diag_by_date.get(date, latest_diag)
            variant = diag.get("variant", diag.get("exp", "UNKNOWN"))
            rows.append({
                "variant": variant,
                "exp": diag.get("exp", "UNKNOWN"),
                "date": date,
                "nav": stat_match.group("nav"),
                "drawdown": stat_match.group("drawdown"),
                "win_rate": stat_match.group("win_rate"),
                "profit_loss_ratio": stat_match.group("profit_loss_ratio"),
                "total_trades": stat_match.group("total_trades"),
                "positions": stat_match.group("positions"),
                "A_buys": diag.get("A_buys", ""),
                "A_sell": diag.get("A_sell", ""),
                "regime": diag.get("regime", ""),
                "trend": diag.get("trend", diag.get("market_trend", "")),
                "pool": diag.get("pool", ""),
                "score": diag.get("score", ""),
            })

    return rows


def write_summary(rows, output_path):
    grouped = {}
    for row in rows:
        key = (row.get("variant", "UNKNOWN"), row.get("exp", "UNKNOWN"))
        grouped.setdefault(key, []).append(row)

    summary_rows = []
    for (variant, exp), items in grouped.items():
        items = sorted(items, key=lambda row: row["date"])
        start = items[0]
        end = items[-1]
        nav_values = [float(row["nav"]) for row in items if row.get("nav")]
        dd_values = [float(row["drawdown"]) for row in items if row.get("drawdown")]
        start_nav = nav_values[0] if nav_values else 0.0
        end_nav = nav_values[-1] if nav_values else 0.0
        total_return = end_nav / start_nav - 1 if start_nav else 0.0
        max_drawdown = min(dd_values) if dd_values else 0.0
        summary_rows.append({
            "variant": variant,
            "exp": exp,
            "start_date": start["date"],
            "end_date": end["date"],
            "start_nav": "{:.4f}".format(start_nav),
            "end_nav": "{:.4f}".format(end_nav),
            "total_return": "{:.2%}".format(total_return),
            "max_drawdown": "{:.2f}".format(max_drawdown),
            "win_rate": end.get("win_rate", ""),
            "profit_loss_ratio": end.get("profit_loss_ratio", ""),
            "total_trades": end.get("total_trades", ""),
            "rows": len(items),
        })

    summary_rows.sort(key=lambda row: row["variant"])
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)


def main():
    parser = argparse.ArgumentParser(
        description="Parse JoinQuant experiment logs and write experiment_summary.csv."
    )
    parser.add_argument(
        "logs",
        nargs="*",
        help="Log files to parse. Default: jq_*.log in current directory.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="experiment_summary.csv",
        help="Output CSV path. Default: experiment_summary.csv",
    )
    parser.add_argument(
        "--summary-output",
        default="experiment_final_summary.csv",
        help="Final summary CSV path. Default: experiment_final_summary.csv",
    )
    args = parser.parse_args()

    paths = args.logs or sorted(glob.glob("jq_*.log"))
    if not paths:
        raise SystemExit("No log files found. Pass log files or put jq_*.log in this directory.")

    rows = []
    for path in paths:
        rows.extend(parse_log(path))

    rows.sort(key=lambda row: (row["exp"], row["date"]))
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_summary(rows, args.summary_output)

    print("Wrote {} rows to {}".format(len(rows), os.path.abspath(args.output)))
    print("Wrote final summary to {}".format(os.path.abspath(args.summary_output)))


if __name__ == "__main__":
    main()
