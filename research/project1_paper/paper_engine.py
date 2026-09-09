# -*- coding: utf-8 -*-
"""Project1 Paper — 出场引擎的分钟数据兜底层(live settle 用)。

问题:canonical/minute_1m 由 warehouse 17:30 任务更新,可能断档(实测 07-01~03 缺)。
兜底:持仓票(每组≤3只,量级极小)当日分钟经 xtdata 下载 → 本目录 cache_min/ →
     monkeypatch engine_phaseA.minute_day(先 canonical 后本地兜底)。
只读 xtdata 行情;质量闸:兜底bar日收盘 vs tushare 当日 close 偏差>0.5% 打 warn(留痕)。
"""
import os
import sys
import functools

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import engine_phaseA as E     # noqa: E402
import paper_config as C      # noqa: E402

CACHE_MIN = os.path.join(_HERE, 'cache_min')
_ORIG_MINUTE_DAY = E.minute_day


def _local_path(code, d8):
    return os.path.join(CACHE_MIN, "%s_%s.parquet" % (code, d8))


@functools.lru_cache(maxsize=20000)
def minute_day_with_fallback(code, d8):
    df = _ORIG_MINUTE_DAY(code, d8)
    if df is not None:
        return df
    p = _local_path(code, d8)
    if os.path.exists(p):
        df = pd.read_parquet(p)
        return df if len(df) else None
    return None


def install():
    """替换 engine 的分钟读取(canonical 优先,本地兜底其次)。"""
    E.minute_day = minute_day_with_fallback


def ensure_minute_live(codes, d8, log=print):
    """对 canonical 缺 (code,d8) 分钟的票,经 xtdata 下载补到 cache_min/。
    返回 {code: 'canonical'|'fetched'|'missing'}。"""
    os.makedirs(CACHE_MIN, exist_ok=True)
    status = {}
    need = []
    for c in codes:
        if _ORIG_MINUTE_DAY(c, d8) is not None:
            status[c] = 'canonical'
        elif os.path.exists(_local_path(c, d8)):
            status[c] = 'fetched'
        else:
            need.append(c)
    if not need:
        return status
    from xtquant import xtdata      # 行情只读
    ref = _tushare_close_map(d8)
    for c in need:
        try:
            xtdata.download_history_data(c, '1m', start_time=d8, end_time=d8)
            md = xtdata.get_market_data_ex([], [c], period='1m',
                                           start_time=d8, end_time=d8 + '235959')
            df = md.get(c)
            if df is None or len(df) == 0:
                status[c] = 'missing'
                continue
            out = pd.DataFrame(dict(
                hm=["%s:%s" % (str(i)[8:10], str(i)[10:12]) for i in df.index],
                open=df['open'].values, high=df['high'].values, low=df['low'].values,
                close=df['close'].values, volume=df['volume'].values,
                amount=df['amount'].values))
            ts_close = ref.get(c)
            day_close = float(out['close'].iloc[-1])
            if ts_close and abs(day_close / ts_close - 1.0) > 0.005:
                log("[paper_engine] ⚠️ %s %s xtdata收盘%.3f vs tushare %.3f 偏差>0.5%%(QMT慢定盘?)"
                    " 仍写入但打flag" % (c, d8, day_close, ts_close))
            out.to_parquet(_local_path(c, d8), index=False)
            status[c] = 'fetched'
        except Exception as ex:
            log("[paper_engine] %s %s 分钟兜底失败: %r" % (c, d8, ex))
            status[c] = 'missing'
    return status


def _tushare_close_map(d8):
    if not os.path.exists(C.TAIL_DAILY_PARQUET):
        return {}
    tl = pd.read_parquet(C.TAIL_DAILY_PARQUET)
    tl = tl[(tl['d8'].astype(str) == d8) & (tl['src'] == 'tushare')]
    return {r.code: float(r.close) for r in tl.itertuples(index=False) if r.close > 0}
