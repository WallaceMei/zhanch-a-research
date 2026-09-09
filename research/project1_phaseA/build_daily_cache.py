# -*- coding: utf-8 -*-
"""Project1 Phase A —— 从 canonical/minute_1m 聚合全量日线 + 竞价(09:30首根)缓存。

【为何需要】warehouse 的 canonical/daily 与 derived/auction 元库已被瘦身到只剩 600519.SH,
read.daily/read.auction 对其他票全返空(见 2026-06-30 勘查)。唯一全量本地源是
canonical/minute_1m/by_code(5805只 2020-2026)。本脚本用 duckdb 一次性聚合:
  日线 open=09:30bar.open, high=max, low=min, close=15:00bar.close, volume/amount=sum
  竞价 = 09:30 首根 (auction_open/volume/amount)  —— 正是原 warehouse auction 的衍生源
口径:不复权(QMT同源)。停牌日无分钟bar → 自然缺席(等价 volume>0 过滤)。

只读 minute,只写本研究目录 cache。不碰实盘/不改候选池/不装包。
运行:py -3.10 build_daily_cache.py
"""
import os
import time
import duckdb

MIN_GLOB_TMPL = "D:/data_warehouse/canonical/minute_1m/by_code/code=*/year={y}.parquet"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
DAILY_OUT = os.path.join(OUT_DIR, "daily_2020_2026.parquet")
AUC_OUT = os.path.join(OUT_DIR, "auction_2020_2026.parquet")
YEARS = list(range(2020, 2027))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    daily_dir = os.path.join(OUT_DIR, "_daily_by_year")
    auc_dir = os.path.join(OUT_DIR, "_auc_by_year")
    os.makedirs(daily_dir, exist_ok=True)
    os.makedirs(auc_dir, exist_ok=True)

    # 逐年【独立】流式 COPY 到各自 parquet(不累积内存表,内存恒定)
    for y in YEARS:
        glob = MIN_GLOB_TMPL.format(y=y)
        dout = os.path.join(daily_dir, "y%d.parquet" % y)
        aout = os.path.join(auc_dir, "y%d.parquet" % y)
        t0 = time.time()
        con = duckdb.connect()                      # 每年新连接,彻底释放
        con.execute("PRAGMA threads=6")
        con.execute("PRAGMA memory_limit='4GB'")
        con.execute(f"""
        COPY (
          SELECT code,
                 strftime(CAST(datetime AS DATE), '%Y%m%d')          AS d8,
                 arg_min(open, datetime)  AS open,
                 max(high)                AS high,
                 min(low)                 AS low,
                 arg_max(close, datetime) AS close,
                 sum(volume)              AS volume,
                 sum(amount)              AS amount,
                 count(*)                 AS nbar
          FROM read_parquet('{glob}')
          WHERE open IS NOT NULL
          GROUP BY code, CAST(datetime AS DATE)
        ) TO '{dout}' (FORMAT PARQUET)
        """)
        con.execute(f"""
        COPY (
          SELECT code,
                 strftime(CAST(datetime AS DATE), '%Y%m%d') AS d8,
                 open   AS auction_open,
                 volume AS auction_volume,
                 amount AS auction_amount
          FROM read_parquet('{glob}')
          WHERE CAST(datetime AS TIME) = TIME '09:30:00' AND open IS NOT NULL
        ) TO '{aout}' (FORMAT PARQUET)
        """)
        con.close()
        print("year=%d done in %.1fs" % (y, time.time() - t0), flush=True)

    # 合并 7 个小年文件(读出来很小:日线~8M行/几十MB)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute(f"COPY (SELECT * FROM read_parquet('{daily_dir}/*.parquet') ORDER BY code, d8) "
                f"TO '{DAILY_OUT}' (FORMAT PARQUET)")
    con.execute(f"COPY (SELECT * FROM read_parquet('{auc_dir}/*.parquet') ORDER BY code, d8) "
                f"TO '{AUC_OUT}' (FORMAT PARQUET)")
    nd = con.execute(f"SELECT COUNT(*), COUNT(DISTINCT code), MIN(d8), MAX(d8) "
                     f"FROM read_parquet('{DAILY_OUT}')").fetchone()
    na = con.execute(f"SELECT COUNT(*), COUNT(DISTINCT code) FROM read_parquet('{AUC_OUT}')").fetchone()
    print("\n[DAILY] rows=%d codes=%d range=%s..%s -> %s" % (nd[0], nd[1], nd[2], nd[3], DAILY_OUT))
    print("[AUCTION] rows=%d codes=%d -> %s" % (na[0], na[1], AUC_OUT))
    con.close()


if __name__ == "__main__":
    main()
