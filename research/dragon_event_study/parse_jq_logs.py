# -*- coding: utf-8 -*-
"""解析聚宽 v140D 日志(默认 score_mode=v3 的实际交易):ENTRY_FEATURE_LOG / EXIT_OUTCOME_LOG。
仅取 ASCII 字段(code+数值),中文名乱码忽略。输出 _entry_log.csv / _exit_log.csv。
注意:这是 v3-default 那一次真实交易的入场/出场;v1/v2 无独立交易日志。"""
import io
import os
import re
import csv

LOG = r"D:\Code\JQ\战车A\log\jq_v140D_20230101_20260622.log.txt"
HERE = os.path.dirname(os.path.abspath(__file__))


def jq2qmt(code):
    return code.replace('.XSHG', '.SH').replace('.XSHE', '.SZ')


def kv(line):
    d = {}
    for part in line.split('|'):
        if '=' in part:
            k, _, v = part.partition('=')
            d[k.strip()] = v.strip()
    return d


def num(v):
    if v in (None, '', 'nan', 'None'):
        return ''
    v = v.replace('%', '')
    try:
        return float(v)
    except Exception:
        return ''


def main():
    entries, exits = [], []
    with io.open(LOG, 'r', encoding='latin-1') as f:
        for line in f:
            if 'ENTRY_FEATURE_LOG|' in line:
                d = kv(line[line.index('ENTRY_FEATURE_LOG'):])
                dt = d.get('date', '')
                if not ('2026-03' <= dt[:7] <= '2026-06'):
                    continue
                entries.append(dict(
                    entry_date=dt.replace('-', ''), code=jq2qmt(d.get('stock', '')),
                    entered=1, entry_type=d.get('entry_type', ''),
                    entry_open_ratio=num(d.get('entry_open_ratio')),
                    entry_day_ret=num(d.get('entry_day_ret')),
                    entry_close_to_high=num(d.get('entry_close_to_high')),
                    entry_volume_ratio=num(d.get('entry_volume_ratio')),
                    entry_auc_ratio=num(d.get('entry_auc_ratio')),
                    entry_ma5_distance=num(d.get('entry_ma5_distance')),
                    entry_ma10_distance=num(d.get('entry_ma10_distance')),
                    breadth_up_ratio=num(d.get('breadth_up_ratio')),
                    entry_score=num(d.get('entry_score')),
                ))
            elif 'EXIT_OUTCOME_LOG|' in line:
                d = kv(line[line.index('EXIT_OUTCOME_LOG'):])
                ed = d.get('entry_date', '')
                if not ('2026-03' <= ed[:7] <= '2026-06'):
                    continue
                exits.append(dict(
                    entry_date=ed.replace('-', ''), code=jq2qmt(d.get('stock', '')),
                    exit_date=d.get('exit_date', '').replace('-', ''),
                    exit_reason=d.get('exit_reason', ''),
                    actual_pnl_pct=num(d.get('pnl_pct')),
                    actual_pnl_val=num(d.get('pnl_val')),
                    hold_days=num(d.get('hold_days')),
                    is_fast_loss=num(d.get('is_fast_loss')),
                    exit_big_meat_10=num(d.get('is_big_meat_10')),
                    exit_super_meat_20=num(d.get('is_super_meat_20')),
                    slot_type=d.get('slot_type', ''),
                    stage=d.get('stage', ''),
                ))

    def dump(rows, path, cols):
        with io.open(path, 'w', encoding='utf-8-sig', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    dump(entries, os.path.join(HERE, '_entry_log.csv'), list(entries[0].keys()) if entries else ['entry_date', 'code'])
    dump(exits, os.path.join(HERE, '_exit_log.csv'), list(exits[0].keys()) if exits else ['entry_date', 'code'])
    print("ENTRY rows:", len(entries), "| EXIT rows:", len(exits))
    print("entry dates:", sorted(set(e['entry_date'] for e in entries))[:6], "...")


if __name__ == '__main__':
    main()
