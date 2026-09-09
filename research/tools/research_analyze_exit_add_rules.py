"""JoinQuant research helper for v1.2.1A structured strategy logs.

This script is intentionally separate from the strategy. It parses exported
backtest logs and performs approximate rule scans. It does not place orders and
does not claim to replace a full backtest.
"""

import argparse
import pathlib
import re

import numpy as np
import pandas as pd


EVENT_NAMES = (
    'HOLD_SNAPSHOT',
    'EXIT_EVENT',
    'ADD_CANDIDATE_SNAPSHOT',
    'LIVERMORE_ADD_BLOCKED',
    'TRADE_ANALYTICS',
    'DAILY_ANALYTICS',
)


def _coerce_value(value):
    text = str(value).strip()
    if text in ('', 'NA', 'None', 'null', 'nan'):
        return np.nan
    numeric_text = text[:-1] if text.endswith('%') else text
    numeric_text = numeric_text.replace(',', '')
    try:
        return float(numeric_text)
    except ValueError:
        return text


def parse_key_value_log(line):
    """Parse one structured log line into a dictionary."""
    pattern = r'(' + '|'.join(EVENT_NAMES) + r')\|'
    match = re.search(pattern, line)
    if not match:
        return None
    event = match.group(1)
    payload = line[match.end():].strip()
    record = {'event': event, '_raw': line.rstrip('\n')}
    for token in payload.split('|'):
        if '=' not in token:
            continue
        key, value = token.split('=', 1)
        record[key.strip()] = _coerce_value(value)
    return record


def parse_log_lines(lines):
    """Return parsed records for all supported structured events."""
    records = []
    for line_number, line in enumerate(lines, 1):
        record = parse_key_value_log(line)
        if record is None:
            continue
        record['_line_number'] = line_number
        records.append(record)
    return records


def load_log_file(path, encoding='utf-8-sig'):
    """Load and parse an exported JoinQuant log text file."""
    log_path = pathlib.Path(path)
    with log_path.open('r', encoding=encoding, errors='replace') as handle:
        return parse_log_lines(handle)


def _build_event_df(records, event):
    rows = [record for record in records if record.get('event') == event]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    if 'date' in frame.columns and 'time' in frame.columns:
        frame['snapshot_dt'] = pd.to_datetime(
            frame['date'].astype(str) + ' ' + frame['time'].astype(str),
            errors='coerce',
        )
    return frame


def build_hold_snapshot_df(records):
    return _build_event_df(records, 'HOLD_SNAPSHOT')


def build_trade_analytics_df(records):
    return _build_event_df(records, 'TRADE_ANALYTICS')


def build_add_candidate_df(records):
    return _build_event_df(records, 'ADD_CANDIDATE_SNAPSHOT')


def _latest_trade_by_stock(trade_df):
    if trade_df is None or trade_df.empty or 'stock' not in trade_df.columns:
        return pd.DataFrame(columns=['stock', 'trade_ret'])
    trades = trade_df.copy()
    trades['_order'] = np.arange(len(trades))
    return trades.sort_values('_order').groupby(
        'stock', as_index=False
    ).tail(1)


def scan_float_profit_protection(hold_df, trade_df):
    """Approximate 15/5, 20/7 and 30/10 floating-profit protection scans."""
    columns = [
        'rule', 'trigger_count', 'stock_count', 'avg_trigger_pnl',
        'avg_max_pnl', 'avg_drawdown_at_trigger', 'avg_final_trade_ret',
        'better_than_actual_count', 'worse_than_actual_count',
    ]
    if hold_df is None or hold_df.empty:
        return pd.DataFrame(columns=columns)

    rules = {
        'rule_fp_15_5': (15.0, 5.0),
        'rule_fp_20_7': (20.0, 7.0),
        'rule_fp_30_10': (30.0, 10.0),
    }
    trades = _latest_trade_by_stock(trade_df)
    results = []
    for rule, (max_pnl_min, drawdown_min) in rules.items():
        matched = hold_df[
            (pd.to_numeric(
                hold_df.get('max_floating_pnl'), errors='coerce'
            ) >= max_pnl_min)
            & (pd.to_numeric(
                hold_df.get('floating_pnl_drawdown'), errors='coerce'
            ) >= drawdown_min)
        ].copy()
        if matched.empty:
            results.append({
                'rule': rule,
                'trigger_count': 0,
                'stock_count': 0,
                'avg_trigger_pnl': np.nan,
                'avg_max_pnl': np.nan,
                'avg_drawdown_at_trigger': np.nan,
                'avg_final_trade_ret': np.nan,
                'better_than_actual_count': 0,
                'worse_than_actual_count': 0,
            })
            continue

        sort_columns = [
            column for column in ('snapshot_dt', '_line_number')
            if column in matched.columns
        ]
        if sort_columns:
            matched = matched.sort_values(sort_columns)
        first_trigger = matched.groupby('stock', as_index=False).head(1)
        comparison = first_trigger.merge(
            trades[['stock', 'trade_ret']]
            if not trades.empty else pd.DataFrame(
                columns=['stock', 'trade_ret']
            ),
            on='stock',
            how='left',
            suffixes=('_trigger', '_final'),
        )
        trigger_pnl = pd.to_numeric(
            comparison.get('pnl'), errors='coerce'
        )
        final_ret = pd.to_numeric(
            comparison.get('trade_ret'), errors='coerce'
        )
        results.append({
            'rule': rule,
            'trigger_count': len(matched),
            'stock_count': matched['stock'].nunique(),
            'avg_trigger_pnl': trigger_pnl.mean(),
            'avg_max_pnl': pd.to_numeric(
                first_trigger.get('max_floating_pnl'), errors='coerce'
            ).mean(),
            'avg_drawdown_at_trigger': pd.to_numeric(
                first_trigger.get('floating_pnl_drawdown'), errors='coerce'
            ).mean(),
            'avg_final_trade_ret': final_ret.mean(),
            'better_than_actual_count': int(
                (trigger_pnl > final_ret).fillna(False).sum()
            ),
            'worse_than_actual_count': int(
                (trigger_pnl < final_ret).fillna(False).sum()
            ),
        })
    return pd.DataFrame(results, columns=columns)


def scan_tail_add_rules(add_df, trade_df):
    """Approximate three earlier tail-add candidate scans."""
    columns = [
        'rule', 'trigger_count', 'stock_count', 'avg_trigger_pnl',
        'avg_day_ret', 'avg_volume_ratio', 'limit_up_count',
        'actual_add_overlap_count', 'avg_final_trade_ret',
    ]
    if add_df is None or add_df.empty:
        return pd.DataFrame(columns=columns)

    hold_days = pd.to_numeric(add_df.get('hold_days'), errors='coerce')
    pnl = pd.to_numeric(add_df.get('current_pnl'), errors='coerce')
    day_ret = pd.to_numeric(add_df.get('day_ret'), errors='coerce')
    volume_ratio = pd.to_numeric(
        add_df.get('volume_ratio_vs_prev'), errors='coerce'
    )
    close_to_high = pd.to_numeric(
        add_df.get('close_to_day_high'), errors='coerce'
    )
    rules = {
        'rule_add_5_5_v1': (
            (hold_days >= 1) & (pnl >= 5) & (day_ret >= 5)
            & (volume_ratio >= 1.0)
        ),
        'rule_add_8_5_v12': (
            (hold_days >= 1) & (pnl >= 8) & (day_ret >= 5)
            & (volume_ratio >= 1.2)
        ),
        'rule_add_10_5_high': (
            (hold_days >= 1) & (pnl >= 10) & (day_ret >= 5)
            & (volume_ratio >= 1.0) & (close_to_high >= 0.97)
        ),
    }
    trades = _latest_trade_by_stock(trade_df)
    results = []
    for rule, mask in rules.items():
        matched = add_df[mask.fillna(False)].copy()
        final_ret = pd.Series(dtype=float)
        if not matched.empty and not trades.empty:
            final_ret = pd.to_numeric(
                matched.merge(
                    trades[['stock', 'trade_ret']],
                    on='stock',
                    how='left',
                ).get('trade_ret'),
                errors='coerce',
            )
        results.append({
            'rule': rule,
            'trigger_count': len(matched),
            'stock_count': (
                matched['stock'].nunique() if not matched.empty else 0
            ),
            'avg_trigger_pnl': pd.to_numeric(
                matched.get('current_pnl'), errors='coerce'
            ).mean(),
            'avg_day_ret': pd.to_numeric(
                matched.get('day_ret'), errors='coerce'
            ).mean(),
            'avg_volume_ratio': pd.to_numeric(
                matched.get('volume_ratio_vs_prev'), errors='coerce'
            ).mean(),
            'limit_up_count': int(
                (pd.to_numeric(
                    matched.get('is_limit_up'), errors='coerce'
                ) == 1).sum()
            ),
            'actual_add_overlap_count': int(
                (matched.get(
                    'add_skip_reason',
                    pd.Series(index=matched.index, dtype=object),
                ) == 'eligible').sum()
            ),
            'avg_final_trade_ret': final_ret.mean(),
        })
    return pd.DataFrame(results, columns=columns)


def summarize_scan_results(float_profit_results, tail_add_results):
    """Return both scan tables plus a clear approximation warning."""
    return {
        'float_profit_protection': float_profit_results,
        'tail_add_rules': tail_add_results,
        'warning': (
            'These scans compare logged snapshots with final trade outcomes. '
            'They are approximate research results, not replacement backtests.'
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Analyze v1.2.1A JoinQuant structured logs.'
    )
    parser.add_argument('log_file', help='Exported JoinQuant log text file')
    parser.add_argument(
        '--output-dir',
        help='Optional directory for CSV scan outputs',
    )
    args = parser.parse_args()

    records = load_log_file(args.log_file)
    hold_df = build_hold_snapshot_df(records)
    trade_df = build_trade_analytics_df(records)
    add_df = build_add_candidate_df(records)
    float_results = scan_float_profit_protection(hold_df, trade_df)
    add_results = scan_tail_add_rules(add_df, trade_df)
    summary = summarize_scan_results(float_results, add_results)

    print('FLOAT_PROFIT_PROTECTION_SCAN')
    print(float_results.to_string(index=False))
    print('\nTAIL_ADD_RULE_SCAN')
    print(add_results.to_string(index=False))
    print('\nWARNING')
    print(summary['warning'])

    if args.output_dir:
        output_dir = pathlib.Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        float_results.to_csv(
            output_dir / 'float_profit_protection_scan.csv',
            index=False,
            encoding='utf-8-sig',
        )
        add_results.to_csv(
            output_dir / 'tail_add_rule_scan.csv',
            index=False,
            encoding='utf-8-sig',
        )


if __name__ == '__main__':
    main()
