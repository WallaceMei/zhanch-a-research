# -*- coding: utf-8 -*-
"""(py3.10)给定交易日,输出 tushare EOD 真实开盘价(不复权)。
用法: python tushare_open_px.py 20260630,20260701  → stdout JSON {"date|ts_code": open_px}
update_tail 用它覆盖 QMT 慢定盘的脏竞价 open(竞价量仍取 QMT 1m 首根)。
只输出 tushare 已出数据的日子(今天未收盘/未出 EOD 的日子自然缺 → update_tail 那天不写)。"""
import sys
import json
sys.path.insert(0, r'D:\Code\skill\dagao-shoushou-v6\tools')
import tushare_data as td


def main():
    dates = sys.argv[1].split(',') if len(sys.argv) > 1 else []
    api = td.get_api()
    out = {}
    for d in dates:
        try:
            df = api.daily(trade_date=d)
        except Exception:
            df = None
        if df is None or len(df) == 0:
            continue
        for _, r in df.iterrows():
            op = r.get('open')
            if op and float(op) > 0:
                out["%s|%s" % (d, r['ts_code'])] = float(op)
    sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    main()
