# -*- coding: utf-8 -*-
"""Project1 Paper — 日线/竞价增量尾巴构建(当日候选池数据链,盘后跑)。

主缓存(daily_2020_2026.parquet)止于 20260626。本脚本补主缓存之后的日子:
  ① canonical/minute_1m 聚合(与主缓存同源同法;含竞价=09:30首根)——能补到 warehouse 更新到哪
  ② tushare 日线兜底(复用 dragon 链路 tushare_daily_panel.py,治 QMT/warehouse 慢定盘)——
     只补 canonical 缺的 (code,day);tushare 无竞价量,缺口日的"前日竞价"由 live_pool
     盘前经 xtdata 1m 首根取 + tushare open 定盘校验(update_tail 同款闸门)。

产物:cache/daily_tail.parquet(code,d8,open,high,low,close,volume,amount,nbar,src)
     cache/auction_tail.parquet(code,d8,auction_open,auction_volume,auction_amount)
pool_repro._load 自动拼接(只取主缓存之后的日子,历史结果零影响)。

用法: py -3.10 update_daily_cache.py [--asof 20260703]
只读 canonical/tushare,只写 phaseA cache/ 的 tail 文件。
"""
import os
import sys
import glob
import argparse
import datetime as dt
import subprocess
import tempfile

import pandas as pd
import duckdb

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import paper_config as C   # noqa: E402


def _main_max_d8(con):
    return con.execute("SELECT max(d8) FROM read_parquet(?)",
                       [C.MAIN_DAILY_PARQUET]).fetchone()[0]


def build_canonical_tail(con, main_max, asof):
    years = sorted({main_max[:4], asof[:4]})
    globs = ["D:/data_warehouse/canonical/minute_1m/by_code/code=*/year=%s.parquet" % y
             for y in years]
    files = []
    for g in globs:
        files += glob.glob(g)
    if not files:
        return pd.DataFrame(), pd.DataFrame()
    d_lo = "%s-%s-%s" % (main_max[:4], main_max[4:6], main_max[6:8])
    d_hi = "%s-%s-%s" % (asof[:4], asof[4:6], asof[6:8])
    lst = "['" + "','".join(f.replace("\\", "/") for f in files) + "']"
    daily = con.execute(
        "SELECT code, strftime(datetime,'%Y%m%d') AS d8,"
        " arg_min(open, datetime) AS open, max(high) AS high, min(low) AS low,"
        " arg_max(close, datetime) AS close, sum(volume) AS volume, sum(amount) AS amount,"
        " count(*) AS nbar"
        " FROM read_parquet(" + lst + ", hive_partitioning=1)"
        " WHERE CAST(datetime AS DATE) > DATE '" + d_lo + "'"
        "   AND CAST(datetime AS DATE) <= DATE '" + d_hi + "'"
        "   AND open IS NOT NULL"
        " GROUP BY code, d8").df()
    auc = con.execute(
        "SELECT code, strftime(datetime,'%Y%m%d') AS d8,"
        " open AS auction_open, volume AS auction_volume, amount AS auction_amount"
        " FROM read_parquet(" + lst + ", hive_partitioning=1)"
        " WHERE CAST(datetime AS DATE) > DATE '" + d_lo + "'"
        "   AND CAST(datetime AS DATE) <= DATE '" + d_hi + "'"
        "   AND strftime(datetime,'%H:%M') = '09:30' AND open IS NOT NULL").df()
    daily['src'] = 'canonical'
    return daily, auc


def build_tushare_fill(main_max, asof, have_pairs):
    """tushare 补 canonical 缺的 (code,d8)。返回同 schema df(nbar=0,src='tushare')。"""
    start = (dt.datetime.strptime(main_max, "%Y%m%d") + dt.timedelta(days=1)).strftime("%Y%m%d")
    tmp = os.path.join(tempfile.gettempdir(), "paper_ts_panel_%s_%s.csv" % (start, asof))
    r = subprocess.run(["py", "-3.10", C.TUSHARE_PANEL_SCRIPT, start, asof, tmp],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(tmp):
        print("[tushare] 面板取数失败(不中止,tail只含canonical): %s" % (r.stderr or r.stdout)[-300:])
        return pd.DataFrame()
    ts = pd.read_csv(tmp, dtype={'date': str})
    ts = ts.rename(columns={'date': 'd8'})
    ts['nbar'] = 0
    ts['src'] = 'tushare'
    mask = [((c, d) not in have_pairs) for c, d in zip(ts['code'], ts['d8'])]
    ts = ts[pd.Series(mask, index=ts.index)]
    return ts[['code', 'd8', 'open', 'high', 'low', 'close', 'volume', 'amount', 'nbar', 'src']]


def main(asof=None):
    now = dt.datetime.now()
    if asof is None:
        asof = now.strftime("%Y%m%d")
        if now.hour < 16:      # 盘中/盘前跑:不纳入今天(半日数据会污染)
            asof = (now - dt.timedelta(days=1)).strftime("%Y%m%d")
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    main_max = _main_max_d8(con)
    print("[tail] 主缓存止于 %s,补 (%s, %s]" % (main_max, main_max, asof))
    if asof <= main_max:
        print("[tail] 无需补,退出"); return

    daily_c, auc_c = build_canonical_tail(con, main_max, asof)
    print("[tail] canonical: %d 行日线 / %d 行竞价 / 覆盖日=%s" % (
        len(daily_c), len(auc_c),
        sorted(daily_c['d8'].unique().tolist()) if len(daily_c) else []))

    have = set(zip(daily_c['code'], daily_c['d8'])) if len(daily_c) else set()
    daily_t = build_tushare_fill(main_max, asof, have)
    if len(daily_t):
        by_day = daily_t.groupby('d8').size()
        print("[tail] tushare 兜底: %d 行,按日=%s" % (len(daily_t), by_day.to_dict()))

    daily = pd.concat([daily_c, daily_t], ignore_index=True) if len(daily_t) else daily_c
    if not len(daily):
        print("[tail] 无新数据"); return
    daily = daily.sort_values(['code', 'd8'])
    daily.to_parquet(C.TAIL_DAILY_PARQUET, index=False)
    auc_c.to_parquet(C.TAIL_AUCTION_PARQUET, index=False)
    print("[tail] 写入 %s (%d行) / %s (%d行)" % (
        os.path.basename(C.TAIL_DAILY_PARQUET), len(daily),
        os.path.basename(C.TAIL_AUCTION_PARQUET), len(auc_c)))
    # 覆盖诊断:tushare-only 日 = 竞价缺口日(live_pool 盘前经 xtdata+tushare校验补)
    cov = daily.groupby(['d8', 'src']).size().unstack(fill_value=0)
    print("[tail] 覆盖诊断(行数):\n%s" % cov.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None)
    args = ap.parse_args()
    main(args.asof)
