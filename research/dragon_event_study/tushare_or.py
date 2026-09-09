# -*- coding: utf-8 -*-
"""(py3.10)给定交易日,输出 tushare 真实 open_ratio = open/pre_close-1(不复权)。
用法: python tushare_or.py 20260626,20260629   → stdout JSON {"date|code": or_float}
update_tail 的定盘校验门 subprocess 调它,用独立源 tushare 校验中台/QMT 选出的竞价。"""
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
            pc = r.get('pre_close')
            op = r.get('open')
            if pc and op and float(pc) > 0:
                out["%s|%s" % (d, r['ts_code'])] = round(float(op) / float(pc) - 1.0, 6)
    sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    main()
