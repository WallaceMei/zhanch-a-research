# -*- coding: utf-8 -*-
"""Project1 Paper — 状态持久化(组合账本 + 留痕CSV,真实/演习双目录隔离)。"""
import os
import json
import csv

import paper_config as C

STATE_FILE = "state.json"


def state_dir(kind):
    return C.STATE_DIR if kind == 'real' else C.DRILL_STATE_DIR


def load_state(kind):
    d = state_dir(kind)
    p = os.path.join(d, STATE_FILE)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return dict(kind=kind, last_settle=None,
                groups={g: dict(cash=1.0, positions={}) for g in C.GROUPS})


def save_state(kind, st):
    d = state_dir(kind)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, STATE_FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(d, STATE_FILE))


def append_csv(kind, name, rows, header):
    if not rows:
        return
    d = state_dir(kind)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in header})


def day_file(kind, d8, suffix):
    d = os.path.join(state_dir(kind), "days")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s_%s.json" % (d8, suffix))


def write_day(kind, d8, suffix, obj):
    with open(day_file(kind, d8, suffix), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def read_day(kind, d8, suffix):
    p = day_file(kind, d8, suffix)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def group_equity(g_state):
    return g_state['cash'] + sum(p['value'] for p in g_state['positions'].values())


EQUITY_HEADER = ['d8', 'group', 'equity', 'cash', 'n_pos']
TRADES_HEADER = ['group', 'code', 'name', 'buy_d8', 'buy_hm', 'buy_price',
                 'sell_d8', 'sell_hm', 'sell_price', 'exit_reason', 'hold_days',
                 'net_return', 'peak_return', 'entry_cost', 'pnl_frac']
DECISIONS_HEADER = ['d8', 'group', 'rank', 'code', 'name', 'pick_reason',
                    'confidence', 'model_version', 'buy_status']
