# -*- coding: utf-8 -*-
"""Project1 Phase A —— 候选池复现层。

复用 research/dragon_event_study/repro_core.py 的**选股打分逻辑(L1-L9)零改动**,
只把它的数据访问接口换成本地 minute 聚合出的全量日线 + 竞价(09:30首根):

  - rc.get_universe       <- 本地全量代码(剔创/科/北 + 新股近似过滤)
  - 日线 panel            <- cache/daily_2020_2026.parquet  (build_daily_cache.py 产物)
  - 竞价 today/prev       <- cache/auction_2020_2026.parquet

为何如此:warehouse 的 daily/auction 元库被瘦身到只剩 600519.SH,read.daily/auction 对
其他票返空(2026-06-30 勘查);唯一全量本地源是 canonical/minute_1m(竞价正是其衍生)。
打分核心 _decide_tpl/_score(L5/L6)原样调用,不编辑 repro_core / 不碰战车A选股代码。
"""
import os
import sys
import bisect

import numpy as np
import pandas as pd

os.environ.setdefault("REPRO_BACKEND", "warehouse")  # 让 connect()=no-op,避免 import xtquant
_DRAGON = r"D:\Code\JQ\战车A\research\dragon_event_study"
if _DRAGON not in sys.path:
    sys.path.insert(0, _DRAGON)

import repro_core as rc  # noqa: E402

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
DAILY_PARQUET = os.path.join(_CACHE, "daily_2020_2026.parquet")
AUCTION_PARQUET = os.path.join(_CACHE, "auction_2020_2026.parquet")
# paper 阶段增量尾巴(update_daily_cache.py 产物;只含主缓存之后的日子,加法式,
# 不存在时行为与 Phase A 完全一致,历史结果不受影响)
TAIL_DAILY_PARQUET = os.path.join(_CACHE, "daily_tail.parquet")
TAIL_AUCTION_PARQUET = os.path.join(_CACHE, "auction_tail.parquet")

EXCLUDE_PREFIX = ('30', '688', '689', '8', '4', '9')  # 同 wh_data:剔创/科/北
MIN_DAILY_ROWS_FOR_UNIVERSE = 30   # 新股近似过滤:全周期内有效日线<30则不入 universe(替代 OpenDate)

_PANEL = None       # {code: df(index=d8 str, cols open/high/low/close/volume/amount)}
_IDX = None         # {code: np.array(sorted d8 str)}  供 bisect 快速定位
_AUC = None         # {(code,d8): (auction_open, auction_volume_手, auction_amount_元)}
_TRADE_DAYS = None  # sorted list of d8 (市场交易日历, 取自日线 cache 的 date 并集)
_UNIVERSE = None    # list[code]
_META = None        # {code: {feat: np.array 对齐 _IDX[code]}}  向量化预算的日线特征

# _meta_from_df 返回的字段(逐字段与其对齐,保证池不变)
_META_FEATS = ('y_close', 'y_high', 'y_hl', 'y_money', 'y_vol', 'ret3', 'ret1',
               'avg_money_5', 'avg_money_10', 'ret_5', 'ret_10',
               'close_to_20d_high', 'avg_range', 'range_10')


def _build_meta_vectorized(dd):
    """一次性向量化预算全量日线特征(严格复刻 repro_core._meta_from_df 每条公式),
    返回列已加入 dd(按 code,d8 升序,与 _IDX 对齐)。
    row i(0-based/股内)= 以该行作为"截至 prev_date 的最近行[-1]"的 meta。"""
    g = dd.groupby('code', sort=False)
    close = dd['close']; high = dd['high']; low = dd['low']; amount = dd['amount']
    n = g.cumcount()                                        # 股内位置(0-based)
    dd['m_y_close'] = close
    dd['m_y_high'] = high
    dd['m_y_money'] = amount
    dd['m_y_vol'] = dd['volume']
    dd['m_y_hl'] = (g['close'].shift(1) * 1.10).round(2)    # prev2_close*1.1
    ret3 = close / g['close'].shift(3) - 1.0                # close[-4]
    dd['m_ret3'] = ret3
    dd['m_ret1'] = close / g['close'].shift(1) - 1.0
    dd['m_avg_money_5'] = g['amount'].rolling(5, min_periods=1).mean().values
    dd['m_avg_money_10'] = g['amount'].rolling(10, min_periods=1).mean().values
    ret_5 = close / g['close'].shift(5) - 1.0
    ret_10 = close / g['close'].shift(10) - 1.0
    dd['m_ret_5'] = ret_5.where(n >= 5, ret3)              # 不足6行→ret3
    dd['m_ret_10'] = ret_10.where(n >= 10, ret3)           # 不足11行→ret3
    high_20 = g['high'].rolling(20, min_periods=1).max().values
    dd['m_c2h20'] = close / high_20
    rng = (high - low) / close
    dd['m_avg_range'] = (rng.groupby(dd['code']).rolling(10, min_periods=5)
                         .mean().reset_index(level=0, drop=True).fillna(0.0).values)
    dd['m_valid'] = (n >= 3).values                        # >=4 行才有效
    return dd


def _fast_build_daily_meta(universe, prev_date, panel=None):
    """替换 repro_core.build_daily_meta:bisect 定位"截至 prev_date 的最近行",
    从向量化预算的 _META 查表构 meta(等价 df[df.index<=prev_date].tail(20) 的 _meta_from_df,
    公式逐字段复刻)→ 池结果不变、速度大幅提升(供 Step0~7 反复重跑)。"""
    per_stock = {}
    for stock in universe:
        idxarr = _IDX.get(stock)
        if idxarr is None:
            continue
        pos = bisect.bisect_right(idxarr, prev_date) - 1   # 最后一个 <= prev_date 的位置
        if pos < 3:
            continue
        mb = _META[stock]
        if not mb['m_valid'][pos]:
            continue
        per_stock[stock] = dict(
            y_close=mb['m_y_close'][pos], y_high=mb['m_y_high'][pos], y_hl=mb['m_y_hl'][pos],
            y_money=mb['m_y_money'][pos], y_vol=mb['m_y_vol'][pos],
            ret3=mb['m_ret3'][pos], ret1=mb['m_ret1'][pos],
            avg_money_5=mb['m_avg_money_5'][pos], avg_money_10=mb['m_avg_money_10'][pos],
            ret_5=mb['m_ret_5'][pos], ret_10=mb['m_ret_10'][pos],
            close_to_20d_high=mb['m_c2h20'][pos],
            avg_range=mb['m_avg_range'][pos], range_10=mb['m_avg_range'][pos],
        )
    return per_stock


def _load():
    global _PANEL, _IDX, _META, _AUC, _TRADE_DAYS, _UNIVERSE
    if _PANEL is not None:
        return
    if not os.path.exists(DAILY_PARQUET):
        raise FileNotFoundError("缺少日线缓存,请先跑 build_daily_cache.py: %s" % DAILY_PARQUET)
    dd = pd.read_parquet(DAILY_PARQUET)
    dd['d8'] = dd['d8'].astype(str)
    if os.path.exists(TAIL_DAILY_PARQUET):
        tl = pd.read_parquet(TAIL_DAILY_PARQUET)
        tl['d8'] = tl['d8'].astype(str)
        tl = tl[tl['d8'] > dd['d8'].max()][list(dd.columns)]
        if len(tl):
            dd = pd.concat([dd, tl], ignore_index=True)
    dd = dd.sort_values(['code', 'd8']).reset_index(drop=True)
    # 市场交易日历 = 全部出现过的日期(任一票有bar即交易日)
    _TRADE_DAYS = sorted(dd['d8'].unique().tolist())
    # 向量化预算全量日线特征(严格复刻 _meta_from_df)
    dd = _build_meta_vectorized(dd)
    # panel dict + 排序索引数组(bisect 用) + meta block
    _PANEL = {}
    _IDX = {}
    _META = {}
    counts = dd.groupby('code').size()
    for code, g in dd.groupby('code', sort=False):
        gg = g[['open', 'high', 'low', 'close', 'volume', 'amount']].copy()
        gg.index = g['d8'].values
        _PANEL[code] = gg
        _IDX[code] = g['d8'].values   # 已按 d8 升序
        _META[code] = {
            'm_valid': g['m_valid'].values,
            'm_y_close': g['m_y_close'].values, 'm_y_high': g['m_y_high'].values,
            'm_y_hl': g['m_y_hl'].values, 'm_y_money': g['m_y_money'].values,
            'm_y_vol': g['m_y_vol'].values, 'm_ret3': g['m_ret3'].values,
            'm_ret1': g['m_ret1'].values, 'm_avg_money_5': g['m_avg_money_5'].values,
            'm_avg_money_10': g['m_avg_money_10'].values, 'm_ret_5': g['m_ret_5'].values,
            'm_ret_10': g['m_ret_10'].values, 'm_c2h20': g['m_c2h20'].values,
            'm_avg_range': g['m_avg_range'].values,
        }
    # universe:剔前缀 + 新股近似(有效日线>=阈值)
    _UNIVERSE = sorted(
        c for c in _PANEL
        if not c.split('.')[0].startswith(EXCLUDE_PREFIX)
        and counts.get(c, 0) >= MIN_DAILY_ROWS_FOR_UNIVERSE)
    # auction dict(主缓存 + 增量尾巴)
    au = pd.read_parquet(AUCTION_PARQUET)
    au['d8'] = au['d8'].astype(str)
    if os.path.exists(TAIL_AUCTION_PARQUET):
        au_t = pd.read_parquet(TAIL_AUCTION_PARQUET)
        au_t['d8'] = au_t['d8'].astype(str)
        au_t = au_t[au_t['d8'] > au['d8'].max()][list(au.columns)]
        if len(au_t):
            au = pd.concat([au, au_t], ignore_index=True)
    _AUC = {}
    for r in au.itertuples(index=False):
        px = float(r.auction_open); vol = float(r.auction_volume); amt = float(r.auction_amount)
        if px > 0 and vol > 0:
            _AUC[(r.code, r.d8)] = (px, vol, amt)

    # monkeypatch repro_core 的数据访问接口(只换数据来源/加速,不改打分)
    rc.get_universe = lambda date: _UNIVERSE
    rc.build_daily_meta = _fast_build_daily_meta


def trade_days():
    _load()
    return _TRADE_DAYS


def prev_trading_day(d8):
    _load()
    prev = [d for d in _TRADE_DAYS if d < d8]
    return prev[-1] if prev else None


def forward_trading_days(d8, n):
    _load()
    return [d for d in _TRADE_DAYS if d >= d8][:n]


def panel():
    _load()
    return _PANEL


def get_auction(code, d8):
    _load()
    return _AUC.get((code, d8))


def dragon_pool(date, prev_date=None, mode='v3'):
    """复现 date 当日 dragon 候选池 top12(战车A get_dragon_stock_list_A 等价输出)。
    返回 list[dict(stock, name, tpl, dragon_score, ret3, open_ratio, ...)]。"""
    _load()
    if prev_date is None:
        prev_date = prev_trading_day(date)
    if prev_date is None:
        return []
    per_stock, ret3_top, auction_seed = rc.compute_seed_prefilter(date, prev_date, panel=_PANEL)
    if not auction_seed:
        return []
    today_auc = {s: _AUC[(s, date)] for s in auction_seed if (s, date) in _AUC}
    prev_auc = {s: _AUC[(s, prev_date)] for s in auction_seed if (s, prev_date) in _AUC}
    base = rc.finalize_base(per_stock, ret3_top, auction_seed, today_auc, prev_auc, prev_date)
    if not base:
        return []
    return rc.score_base(base, mode)


if __name__ == "__main__":
    # 自检:跑几天看池规模/模板分布
    _load()
    print("universe=%d  trade_days=%d (%s..%s)" % (
        len(_UNIVERSE), len(_TRADE_DAYS), _TRADE_DAYS[0], _TRADE_DAYS[-1]))
    for d in ["20200302", "20210601", "20230301", "20231229"]:
        pool = dragon_pool(d)
        dw = sum(1 for p in pool if p['tpl'] == 'deep_water')
        print("date=%s pool=%d deep_water=%d top=%s" % (
            d, len(pool), dw,
            [(p['stock'], round(p['dragon_score'], 3)) for p in pool[:3]]))
