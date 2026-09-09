# -*- coding: utf-8 -*-
"""dragon_event_study 数据层 —— 统一数据中台(data_warehouse)后端。

与 repro_core 的 QMT 数据层**同签名**,供 REPRO_BACKEND='warehouse' 切换。
只换数据来源(日历/全A码/日线/竞价 → 中台 read 接口 + 元库),选股逻辑零改动。

口径对齐(已验):
  - 日线 read.daily(adjust='none') 不复权;volume=手、amount=元(与 QMT 1d 一致)。
  - 竞价 read.auction = 分钟首根(09:30);auction_open/volume(手)/amount(元),与 QMT 1m 首根 100% 吻合。
  - 交易日历 trade_calendar(2015-2026);全A码 data_coverage(daily)。
"""
import os
import sys
import datetime

_WH_ROOT = os.environ.get("DW_ROOT", r"D:\Code\data_warehouse_app")
if _WH_ROOT not in sys.path:
    sys.path.insert(0, _WH_ROOT)

import duckdb  # noqa: E402
from data_warehouse import read  # noqa: E402
from data_warehouse.core.config import load_config  # noqa: E402

_cfg = load_config()
_DUCK = str(_cfg.duckdb_path)

# 与 repro_core 一致(剔创/科/北)
EXCLUDE_PREFIX = ('30', '688', '689', '8', '4', '9')
DAILY_FIELDS = ['open', 'high', 'low', 'close', 'volume', 'amount']


# ---------- 日期工具 ----------
def _d2dash(d):   # 'YYYYMMDD' -> 'YYYY-MM-DD'
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8])


# ---------- 交易日历(trade_calendar) ----------
_TD = None


def _trading_days():
    global _TD
    if _TD is None:
        con = duckdb.connect(_DUCK, read_only=True)
        try:
            rows = con.execute(
                "SELECT CAST(date AS VARCHAR) FROM trade_calendar "
                "WHERE is_trading_day=TRUE ORDER BY date").fetchall()
        finally:
            con.close()
        _TD = [r[0].replace("-", "") for r in rows]   # 'YYYYMMDD'
    return _TD


def trade_days_until(date, n):
    """<= date 的最近 n 个交易日(升序,'YYYYMMDD')。"""
    return [d for d in _trading_days() if d <= date][-n:]


def prev_trading_day(date):
    prev = [d for d in _trading_days() if d < date]
    return prev[-1] if prev else None


def forward_trading_days(date, n):
    """>= date 的最近 n 个交易日(升序),含 date 自身(若为交易日)。"""
    return [d for d in _trading_days() if d >= date][:n]


# ---------- 全A代码(剔创/科/北) ----------
def all_a_codes():
    con = duckdb.connect(_DUCK, read_only=True)
    try:
        rows = con.execute(
            "SELECT DISTINCT code FROM data_coverage WHERE data_type='daily'").fetchall()
    finally:
        con.close()
    return sorted(r[0] for r in rows
                  if not r[0].split('.')[0].startswith(EXCLUDE_PREFIX))


# ---------- 日线 panel ----------
def load_daily_panel(codes, start, end):
    """批量日线(不复权)→ {stock: df(列 open/high/low/close/volume/amount, 索引 'YYYYMMDD' 升序)}。
    start/end 入参 'YYYYMMDD'(与 QMT 版一致)。"""
    df = read.daily(codes=list(codes), start=_d2dash(start), end=_d2dash(end),
                    adjust='none', strict=False)
    out = {}
    if df is None or len(df) == 0:
        return out
    df = df.copy()
    # ★停牌日剔除:中台日线(分钟聚合)对停牌日会留"零成交平盘占位bar"(O=H=L=C=昨收, vol=0),
    #   而 QMT 1d 停牌日直接无 bar。若不剔,占位bar会污染 20 日滚动窗(ret3/avg_range/avg_money 失真,
    #   dropna 不掉因 close 非空)。剔 volume<=0 → 与 QMT"只含真实交易日"口径一致。
    df = df[df['volume'] > 0]
    df['d8'] = df['date'].astype(str).str.replace('-', '', regex=False).str.slice(0, 8)
    df = df.sort_values(['code', 'd8'])
    for code, g in df.groupby('code', sort=False):
        gg = g[DAILY_FIELDS].copy()
        gg.index = g['d8'].values
        out[code] = gg
    return out


# ---------- 竞价(中台 read.auction = 分钟首根 09:30) ----------
def read_auction(stocks, date):
    """只读竞价 → {stock: (竞价价, 竞价量手, 竞价额元)}。date 入参 'YYYYMMDD'。"""
    if not stocks:
        return {}
    df = read.auction(codes=list(stocks), start=_d2dash(date), end=_d2dash(date),
                      strict=False)
    out = {}
    if df is None or len(df) == 0:
        return out
    for _, r in df.iterrows():
        curr = float(r['auction_open'])
        vol = float(r['auction_volume'])
        amt = float(r['auction_amount'])
        if curr > 0 and vol > 0:
            out[r['code']] = (curr, vol, amt)
    return out


def get_auction(stock, date):
    return read_auction([stock], date).get(stock)


def batch_auction(stocks, date):
    return read_auction(stocks, date)


# ---------- 下载类 → 中台已有数据,全部 no-op ----------
def download_auction_1m(stocks, date):
    return


def safe_download(stocks, period, start, end, done=None, timeout=20, logf=None, every=100):
    done = done if done is not None else set()
    done.update(stocks)
    return done, []


def safe_download_1m(stocks, start, end, done=None, timeout=20, logf=None, every=100):
    return safe_download(stocks, '1m', start, end, done=done, timeout=timeout,
                         logf=logf, every=every)
