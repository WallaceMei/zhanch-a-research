# -*- coding: utf-8 -*-
"""(py3.10)拉 tushare 日线面板到 parquet,供 update_tail 尾部选股+forward 用(免疫 QMT 慢定盘)。
用法: python tushare_daily_panel.py 20260409 20260701 _tushare_panel.parquet
输出列: date(YYYYMMDD str), code(ts_code), open, high, low, close, volume(手), amount(元)
口径对齐 QMT/wh_data:不复权;volume=手(tushare vol);amount=元(tushare amount 千元 ×1000)。
只含 tushare 已出 EOD 的交易日(今天未出则自然缺 → 该日 pool 不写)。"""
import sys
import time
sys.path.insert(0, r'D:\Code\skill\dagao-shoushou-v6\tools')
import tushare_data as td
import pandas as pd


def main():
    start, end, out = sys.argv[1], sys.argv[2], sys.argv[3]
    api = td.get_api()
    cal = api.trade_cal(exchange='SSE', start_date=start, end_date=end, is_open='1')
    days = sorted(cal['cal_date'].tolist())
    frames = []
    for d in days:
        for attempt in range(3):
            try:
                df = api.daily(trade_date=d)
                break
            except Exception:
                time.sleep(1.0)
                df = None
        if df is None or len(df) == 0:
            continue
        sub = df[['trade_date', 'ts_code', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()
        sub.columns = ['date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount']
        sub['amount'] = sub['amount'] * 1000.0     # tushare 千元 → 元
        frames.append(sub)
    if not frames:
        print("no data"); return
    alld = pd.concat(frames, ignore_index=True)
    alld['date'] = alld['date'].astype(str)
    alld.to_csv(out, index=False, encoding='utf-8')
    print("wrote %s | days=%d rows=%d date=%s..%s" %
          (out, len(days), len(alld), alld['date'].min(), alld['date'].max()))


if __name__ == '__main__':
    main()
