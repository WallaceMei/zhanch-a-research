# -*- coding: utf-8 -*-
"""
战车A龙头3 v1.4.0D_observer —— 候选池本地精确复现(QMT 数据,不开聚宽)

移植自 战车A龙头3_v1.4.0D_observer.py:
  - _get_dragon_stock_list_A_impl   (4006-4373)  选股主链
  - _prefilter_dragon_auction_candidates (3859-4003) 竞价前6因子预筛250
  - get_base_stock_universe        (4551+)       universe
  - v1/v2/v3 三套打分               (4254-4356)
  - tpl 判定                        (4244-4249)

核心突破:聚宽 get_call_auction 的"集合竞价价+量",等价于 QMT 1m 首根(09:30)的 open/volume。
  实测对 2026-03-02 三只票,open_ratio/auc_ratio/close_to_high 与聚宽回测日志精确吻合(4位小数)。
  → 整条选股链(universe→竞价层→tpl→score)可本地精确复现,全程覆盖,不需 tick、不需聚宽。

数据口径:
  - 日线:QMT 1d,前复权(dividend_type 可配),截至 prev_trade_day,count=20。
  - 竞价:QMT 1m 首根(09:30)。open=竞价价,volume(手)=竞价量,amount(元)=竞价额。
  - 单位:QMT volume=手, amount=元。auc_ratio=竞价量/昨量(单位无关比值);auc_amount 用1m首根amount。
"""
import sys
import os
import json
import threading
import datetime

QMT_SP = r"D:\国金QMT交易端模拟\bin.x64\Lib\site-packages"
if QMT_SP not in sys.path:
    sys.path.insert(0, QMT_SP)

from xtquant import xtdata as xd  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

QMT_IP = os.environ.get("QMT_IP", "127.0.0.1")
QMT_PORT = int(os.environ.get("QMT_PORT", "58610"))

# ===== 常量(照搬源码 g.cfg) =====
EXCLUDE_PREFIX = ('30', '688', '689', '8', '4', '9')   # 创/科/北
NEW_STOCK_DAYS = 50            # 上市<50自然日剔除(get_base_stock_universe)
RET3_TOP_N = 160              # dragon_ret3_top_n
MONEY_TOP_PCT = 0.20         # dragon_money_top_pct
MIN_PREV_MONEY = 1.5e8       # dragon_min_prev_money(全局)
MAX_AVG_RANGE = 0.08         # dragon_max_avg_daily_range
PREFILTER_TOP = 250          # max_auction_prefilter_count
AUC_TOP_N = 80               # dragon_auc_top_n
MIN_AUC_RATIO = 0.006        # dragon_min_auction_ratio
MIN_AUC_AMOUNT = 8.0e6       # dragon_min_auction_amount
PREV_AUCTION_MULT = 0.50     # dragon_prev_auction_mult (v1)
A_DRAGON_MIN_RET_3D = 0.03   # A_dragon_min_ret_3d (v1)
TOP_N = 12

DIVIDEND_TYPE = os.environ.get("REPRO_DIVIDEND", "none")  # 实证:聚宽该回测用不复权,raw 精确吻合

# ===== 数据后端开关(并存,默认 QMT,选股逻辑零改动) =====
#   REPRO_BACKEND=qmt        直连 QMT(原逻辑,默认)
#   REPRO_BACKEND=warehouse  读统一数据中台(wh_data),可扩到 2020-2026 6.5 年
BACKEND = os.environ.get("REPRO_BACKEND", "qmt").lower()
_wh = None

# 竞价开盘价覆盖:{(date,stock): open_px}。尾部补数时用 tushare EOD 真实 open 覆盖 QMT 慢定盘的脏 open,
# 竞价量仍取 QMT 1m 首根。update_tail 在 compute_base 前填充。空则用原 QMT open。
AUCTION_OPEN_OVERRIDE = {}


def _whmod():
    global _wh
    if _wh is None:
        import wh_data as _w
        _wh = _w
    return _wh


_connected = False


def connect():
    if BACKEND == 'warehouse':
        return          # 中台后端不连 QMT
    global _connected
    if not _connected:
        xd.reconnect(QMT_IP, QMT_PORT)
        _connected = True


# ---------------------------------------------------------------------------
# 交易日历
# ---------------------------------------------------------------------------
def _ymd(ts_ms):
    return datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%Y%m%d")


def trade_days_until(date, n):
    """返回 <= date 的最近 n 个交易日(升序, 'YYYYMMDD')。"""
    if BACKEND == 'warehouse':
        return _whmod().trade_days_until(date, n)
    connect()
    start = (datetime.datetime.strptime(date, "%Y%m%d") -
             datetime.timedelta(days=n * 3 + 40)).strftime("%Y%m%d")
    tds = xd.get_trading_dates("SH", start_time=start, end_time=date)
    return [_ymd(t) for t in tds][-n:]


def prev_trading_day(date):
    if BACKEND == 'warehouse':
        return _whmod().prev_trading_day(date)
    days = trade_days_until(date, 2)
    if len(days) >= 2 and days[-1] == date:
        return days[-2]
    # date 自身非交易日时,days[-1] 即最近交易日(< date)
    return days[-1] if days else None


def forward_trading_days(date, n):
    """返回 >= date 的最近 n 个交易日(升序),含 date 自身(若为交易日)。"""
    if BACKEND == 'warehouse':
        return _whmod().forward_trading_days(date, n)
    connect()
    end = (datetime.datetime.strptime(date, "%Y%m%d") +
           datetime.timedelta(days=n * 3 + 40)).strftime("%Y%m%d")
    tds = [_ymd(t) for t in xd.get_trading_dates("SH", start_time=date, end_time=end)]
    return tds[:n]


# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------
_detail_cache = {}


def _detail(code):
    if code not in _detail_cache:
        if BACKEND == 'warehouse':
            # 中台后端不连 QMT:名称/上市日来自已载入的 _detail_cache.json;缺失给空
            return {'InstrumentName': '', 'OpenDate': None}
        try:
            d = xd.get_instrument_detail(code) or {}
        except Exception:
            d = {}
        # 只留需要的字段(可序列化持久化)
        _detail_cache[code] = {
            'InstrumentName': d.get('InstrumentName', ''),
            'OpenDate': d.get('OpenDate'),
        }
    return _detail_cache[code]


def load_detail_cache(path):
    """从 JSON 载入 code->{InstrumentName,OpenDate},省去 5210 次 get_instrument_detail。"""
    global _detail_cache
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                _detail_cache = json.load(f)
            return len(_detail_cache)
        except Exception:
            return 0
    return 0


def save_detail_cache(path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(_detail_cache, f, ensure_ascii=False)


def warm_detail_cache(codes=None):
    """对全 universe 预热 detail 缓存(一次性 5210 次 RPC)。"""
    if BACKEND == 'warehouse':
        return len(_detail_cache)   # 中台后端复用已有 _detail_cache.json,不连 QMT
    connect()
    if codes is None:
        codes = xd.get_stock_list_in_sector('沪深A股') or []
    for c in codes:
        _detail(c)
    return len(_detail_cache)


def get_universe(date):
    """date 当日的 A 股 universe(剔创/科/北 + 上市<50自然日)。'YYYYMMDD'。
    注:不按 *当前* 名称剔 ST/退 —— QMT instrument detail 只有当前名,用它会引入前视/幸存者偏差
    (例:002082 现名'ST万邦',但 03-31 是非ST的 rank1 龙头候选,被误剔)。真正退市/停牌不可交易的票
    由日线 panel ≥4 行硬要求自然排除。当期ST误纳的风险小(ST量价难过龙头种子+竞价门槛)。"""
    if BACKEND == 'warehouse':
        codes = _whmod().all_a_codes()   # 已剔创/科/北
    else:
        connect()
        codes = xd.get_stock_list_in_sector('沪深A股') or []
    cutoff = (datetime.datetime.strptime(date, "%Y%m%d") -
              datetime.timedelta(days=NEW_STOCK_DAYS)).strftime("%Y%m%d")
    uni = []
    for c in codes:
        bare = c.split('.')[0]
        if any(bare.startswith(p) for p in EXCLUDE_PREFIX):
            continue
        d = _detail(c)
        od = d.get('OpenDate')
        if od and str(od) > cutoff:        # 上市太晚(新股)
            continue
        uni.append(c)
    return uni


def get_raw_codes():
    """全A原始码(剔创/科/北),供 run_full 预载 panel。后端无关。"""
    if BACKEND == 'warehouse':
        return _whmod().all_a_codes()
    connect()
    return [c for c in (xd.get_stock_list_in_sector('沪深A股') or [])
            if not c.split('.')[0].startswith(EXCLUDE_PREFIX)]


# ---------------------------------------------------------------------------
# 日线特征 (per_stock meta) —— 对齐 _get_dragon_stock_list_A_impl 4032-4139
# ---------------------------------------------------------------------------
DAILY_FIELDS = ['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose']


def load_daily_panel(codes, start, end):
    """一次性批量拉全 universe 的 1d(不复权),供逐日切片复用。返回 {stock: df(按日升序)}。"""
    if BACKEND == 'warehouse':
        return _whmod().load_daily_panel(codes, start, end)
    connect()
    data = xd.get_market_data_ex(
        DAILY_FIELDS, codes, period='1d', start_time=start, end_time=end,
        dividend_type=DIVIDEND_TYPE, fill_data=False)
    # 索引规整为 'YYYYMMDD' 字符串(QMT 1d 默认 int 索引),便于按日切片/forward 对齐
    for s, df in data.items():
        if df is not None and len(df):
            df.index = df.index.astype(str).str.slice(0, 8)
    return data


def _meta_from_df(df):
    """单只 1d 切片(已截至 prev_date, ≤20 行)→ meta。不足返回 None。"""
    if df is None or len(df) < 4:
        return None
    df = df.dropna(subset=['close'])
    if len(df) < 4:
        return None
    close = df['close'].astype(float).values
    high = df['high'].astype(float).values
    low = df['low'].astype(float).values
    amount = df['amount'].astype(float).values
    volume = df['volume'].astype(float).values

    y_close = close[-1]
    if y_close <= 0:
        return None
    y_high = high[-1]
    y_money = amount[-1]
    y_vol = volume[-1]
    prev2_close = close[-2] if len(close) >= 2 else y_close
    y_hl = round(prev2_close * 1.10, 2)
    ret3 = y_close / close[-4] - 1 if close[-4] > 0 else 0.0
    ret1 = y_close / close[-2] - 1 if len(close) >= 2 and close[-2] > 0 else 0.0
    avg_money_5 = float(np.mean(amount[-5:]))
    avg_money_10 = float(np.mean(amount[-10:]))
    ret_5 = (close[-1] / close[-6] - 1) if len(close) >= 6 and close[-6] > 0 else ret3
    ret_10 = (close[-1] / close[-11] - 1) if len(close) >= 11 and close[-11] > 0 else ret3
    high_20 = float(np.max(high[-20:]))
    close_to_20d_high = y_close / high_20 if high_20 > 0 else 0.0
    rng_vals = [(high[i] - low[i]) / close[i]
                for i in range(len(close)) if close[i] > 0][-10:]
    avg_range = float(np.mean(rng_vals)) if len(rng_vals) >= 5 else 0.0
    return dict(
        y_close=y_close, y_high=y_high, y_hl=y_hl, y_money=y_money, y_vol=y_vol,
        ret3=ret3, ret1=ret1, avg_money_5=avg_money_5, avg_money_10=avg_money_10,
        ret_5=ret_5, ret_10=ret_10, close_to_20d_high=close_to_20d_high,
        avg_range=avg_range, range_10=avg_range,
    )


def build_daily_meta(universe, prev_date, panel=None):
    """per_stock meta。panel 给定则按 prev_date 切片复用(快);否则单独拉 count=20。"""
    connect()
    per_stock = {}
    if panel is not None:
        for stock in universe:
            df = panel.get(stock)
            if df is None or len(df) == 0:
                continue
            sl = df[df.index <= prev_date].tail(20)
            meta = _meta_from_df(sl)
            if meta is not None:
                per_stock[stock] = meta
        return per_stock

    data = xd.get_market_data_ex(
        DAILY_FIELDS, universe, period='1d', end_time=prev_date, count=20,
        dividend_type=DIVIDEND_TYPE, fill_data=False)
    for stock, df in data.items():
        meta = _meta_from_df(df)
        if meta is not None:
            per_stock[stock] = meta
    return per_stock


def _build_daily_meta_legacy(universe, prev_date):
    """原始逐字段实现(保留供参考,未用)。"""
    connect()
    fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'preClose']
    data = xd.get_market_data_ex(
        fields, universe, period='1d', end_time=prev_date, count=20,
        dividend_type=DIVIDEND_TYPE, fill_data=False)

    per_stock = {}
    for stock, df in data.items():
        if df is None or len(df) < 4:
            continue
        df = df.dropna(subset=['close'])
        if len(df) < 4:
            continue
        close = df['close'].astype(float).values
        high = df['high'].astype(float).values
        low = df['low'].astype(float).values
        amount = df['amount'].astype(float).values
        volume = df['volume'].astype(float).values

        y_close = close[-1]
        y_high = high[-1]
        y_money = amount[-1]
        y_vol = volume[-1]
        if y_close <= 0:
            continue
        # 昨涨停价:主板=前一日(即昨日)的涨停= 昨日之前收盘*1.1。
        # 用前复权 close[-2]*1.1 近似(0.995 buffer 吸收四舍五入)。
        prev2_close = close[-2] if len(close) >= 2 else y_close
        y_hl = round(prev2_close * 1.10, 2)

        ret3 = y_close / close[-4] - 1 if close[-4] > 0 else 0.0
        ret1 = y_close / close[-2] - 1 if len(close) >= 2 and close[-2] > 0 else 0.0

        # 近5/10日均额、ret_5/ret_10、close_to_20d_high、近10日均振幅
        avg_money_5 = float(np.mean(amount[-5:])) if len(amount) >= 1 else y_money
        avg_money_10 = float(np.mean(amount[-10:])) if len(amount) >= 1 else y_money
        ret_5 = (close[-1] / close[-6] - 1) if len(close) >= 6 and close[-6] > 0 else ret3
        ret_10 = (close[-1] / close[-11] - 1) if len(close) >= 11 and close[-11] > 0 else ret3
        high_20 = float(np.max(high[-20:])) if len(high) >= 1 else y_high
        close_to_20d_high = y_close / high_20 if high_20 > 0 else 0.0

        rng_vals = [(high[i] - low[i]) / close[i]
                    for i in range(len(close)) if close[i] > 0][-10:]
        avg_range = float(np.mean(rng_vals)) if len(rng_vals) >= 5 else 0.0
        range_10 = avg_range

        per_stock[stock] = dict(
            y_close=y_close, y_high=y_high, y_hl=y_hl, y_money=y_money, y_vol=y_vol,
            ret3=ret3, ret1=ret1, avg_money_5=avg_money_5, avg_money_10=avg_money_10,
            ret_5=ret_5, ret_10=ret_10, close_to_20d_high=close_to_20d_high,
            avg_range=avg_range, range_10=range_10,
        )
    return per_stock


# ---------------------------------------------------------------------------
# 竞价层 —— QMT 1m 首根(09:30) = 集合竞价
# ---------------------------------------------------------------------------
_auc_cache = {}


def get_auction(stock, date):
    """(竞价价, 竞价量手, 竞价额元) from QMT 1m 首根。缺失返回 None。"""
    if BACKEND == 'warehouse':
        return _whmod().get_auction(stock, date)
    key = (stock, date)
    if key in _auc_cache:
        return _auc_cache[key]
    connect()
    try:
        d = xd.get_market_data_ex(
            ['open', 'high', 'low', 'close', 'volume', 'amount'],
            [stock], period='1m', start_time=date, end_time=date,
            dividend_type='none', fill_data=False).get(stock)
    except Exception:
        d = None
    res = None
    if d is not None and len(d):
        r0 = d.iloc[0]
        curr = float(r0['open'])
        vol = float(r0['volume'])
        amt = float(r0['amount'])
        if curr > 0 and vol > 0:
            res = (curr, vol, amt)
    _auc_cache[key] = res
    return res


def download_auction_1m(stocks, date):
    """批量下载 1m(供 get_auction 读)。"""
    if BACKEND == 'warehouse':
        return          # 中台已有数据,无需下载
    connect()
    for s in stocks:
        try:
            xd.download_history_data(s, period='1m', start_time=date, end_time=date)
        except Exception:
            pass


def read_auction(stocks, date):
    """只读(不下载) 1m 首根 → {stock: (竞价价, 竞价量手, 竞价额元)}。需先下载。"""
    if BACKEND == 'warehouse':
        return _whmod().read_auction(stocks, date)
    connect()
    out = {}
    try:
        data = xd.get_market_data_ex(
            ['open', 'volume', 'amount'], list(stocks), period='1m',
            start_time=date, end_time=date, dividend_type='none', fill_data=False)
    except Exception:
        data = {}
    for s, d in (data or {}).items():
        if d is None or len(d) == 0:
            continue
        r0 = d.iloc[0]
        curr = float(r0['open'])
        vol = float(r0['volume'])
        amt = float(r0['amount'])
        ov = AUCTION_OPEN_OVERRIDE.get((date, s))
        if ov is not None and ov > 0:      # tushare EOD 真实 open 覆盖 QMT 脏 open;量取QMT,额按新价重算
            curr = float(ov)
            amt = curr * vol * 100.0       # QMT vol=手 → 股*价=元
        if curr > 0 and vol > 0:
            out[s] = (curr, vol, amt)
    return out


def batch_auction(stocks, date):
    """一天一批:下载+读 1m 首根 → {stock: (竞价价, 竞价量手, 竞价额元)}。"""
    download_auction_1m(stocks, date)
    return read_auction(stocks, date)


def _dl_one(stock, period, start, end):
    try:
        xd.download_history_data(stock, period=period, start_time=start, end_time=end)
    except Exception:
        pass


def safe_download(stocks, period, start, end, done=None, timeout=20, logf=None, every=100):
    """逐只下载 [start,end] 的 period 数据,每只带线程超时(挂死则跳过,不阻塞全程)。
    done: 已下载集合(断点续传,原地更新)。返回 (done, skipped)。
    注:download_history_data2(批量)对个别退市/缺口票会无超时挂死 → 改逐只+超时。"""
    if BACKEND == 'warehouse':
        done = done if done is not None else set()
        done.update(stocks)
        return done, []          # 中台已有数据,无需下载
    connect()
    done = done if done is not None else set()
    skipped = []
    n = len(stocks)
    for i, s in enumerate(stocks):
        if s in done:
            continue
        t = threading.Thread(target=_dl_one, args=(s, period, start, end), daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            skipped.append(s)          # 挂死,留守护线程,继续
        else:
            done.add(s)
        if logf and (i + 1) % every == 0:
            logf("  %s下载 %d/%d (done=%d skipped=%d)" % (period, i + 1, n, len(done), len(skipped)))
    return done, skipped


def safe_download_1m(stocks, start, end, done=None, timeout=20, logf=None, every=100):
    return safe_download(stocks, '1m', start, end, done=done, timeout=timeout, logf=logf, every=every)


def bulk_download_1m(stocks, start, end):
    """逐只安全下载(无超时上限,内部仍逐只)。保留兼容旧调用。"""
    safe_download_1m(list(stocks), start, end)


# ---------------------------------------------------------------------------
# 预筛 250 —— _prefilter_dragon_auction_candidates 3901-4003
# ---------------------------------------------------------------------------
def prefilter_auction(seed, per_stock):
    eligible = []
    for stock in sorted(seed):
        meta = per_stock.get(stock)
        if not meta:
            continue
        if meta['y_close'] >= meta['y_hl'] * 0.995:
            continue
        if meta['y_money'] < MIN_PREV_MONEY:
            continue
        if meta.get('avg_range', 0.0) > MAX_AVG_RANGE:
            continue
        eligible.append(dict(
            stock=stock,
            avg_money_5=meta.get('avg_money_5', meta['y_money']),
            avg_money_10=meta.get('avg_money_10', meta['y_money']),
            ret_5=meta.get('ret_5', meta['ret3']),
            ret_10=meta.get('ret_10', meta['ret3']),
            close_to_20d_high=meta.get('close_to_20d_high',
                                       meta['y_close'] / max(meta['y_high'], 0.01)),
            range_10=meta.get('range_10', meta.get('avg_range', 0.0)),
        ))
    if not eligible:
        return []
    fdf = pd.DataFrame(eligible)
    cols = ['avg_money_5', 'avg_money_10', 'ret_5', 'ret_10',
            'close_to_20d_high', 'range_10']
    for col in cols:
        fdf[col] = pd.to_numeric(fdf[col], errors='coerce').replace(
            [np.inf, -np.inf], np.nan).fillna(0.0)
        fdf[col + '_rank'] = fdf[col].rank(method='average', pct=True)
    fdf['prefilter_score'] = (
        fdf['avg_money_5_rank'] * 0.25 + fdf['avg_money_10_rank'] * 0.15 +
        fdf['ret_5_rank'] * 0.20 + fdf['ret_10_rank'] * 0.10 +
        fdf['close_to_20d_high_rank'] * 0.15 + fdf['range_10_rank'] * 0.15)
    fdf = fdf.sort_values(['prefilter_score', 'stock'],
                          ascending=[False, True]).reset_index(drop=True)
    return fdf.head(max(1, PREFILTER_TOP))['stock'].tolist()


# ---------------------------------------------------------------------------
# tpl + 三套打分 —— 4244-4356
# ---------------------------------------------------------------------------
def _decide_tpl(close_to_high, open_ratio, auc_ratio):
    if (0.90 <= close_to_high < 0.975 and open_ratio >= 0.015
            and auc_ratio >= MIN_AUC_RATIO * 1.2):
        return 'deep_water'
    return 'trend_core'


def _score(mode, meta, tpl, open_ratio, auc_ratio, auc_amount, close_to_high, prev_auc_vol):
    ret3 = meta['ret3']
    ret1 = meta['ret1']
    y_money = meta['y_money']
    if mode == 'v2':
        s = 0.0
        s += min(max(ret3, 0.0), 0.35) * 0.80
        s += min(max(open_ratio, 0.0), 0.10) * 0.30
        s += (1.0 - close_to_high) * 0.15
        s += min(max(ret1, 0.0), 0.10) * 0.20
        if tpl == 'deep_water':
            s += 0.040
        return s
    if mode == 'v3':
        inv_c2h = 1.0 - close_to_high
        avg_rng = meta.get('avg_range', 0.0)
        s = 0.0
        s += inv_c2h * 2.5
        s += avg_rng * 4.0
        s += max(0.0, 0.03 - auc_ratio) * 8.0
        s += min(max(ret3, 0.0), 0.25) * inv_c2h * 2.0
        s += min(max(ret3, 0.0), 0.30) * 0.50
        if tpl == 'deep_water':
            s += 0.15
        return s
    # v1
    s = 0.0
    s += min(max(ret3, 0.0), 0.35) * 0.70
    s += min(max(open_ratio, 0.0), 0.10) * 1.05
    s += min(max(auc_ratio, 0.0), 0.08) * 0.95
    s += min(y_money / 1e9, 10.0) * 0.006
    s += max(min(close_to_high, 1.0), 0.0) * 0.030
    if prev_auc_vol > 0:
        prev_auc_amount = prev_auc_vol * meta['y_close']
        if prev_auc_amount > 0 and (auc_amount / prev_auc_amount) >= PREV_AUCTION_MULT:
            s += 0.006
    if tpl == 'deep_water':
        s += 0.015
    elif close_to_high >= 0.955 and ret3 >= A_DRAGON_MIN_RET_3D:
        s += 0.010
    return s


# ---------------------------------------------------------------------------
# 主链
# ---------------------------------------------------------------------------
def compute_seed_prefilter(date, prev_date, panel=None):
    """无下载半场:universe→meta→seed→prefilter。返回 (per_stock, ret3_top, auction_seed)。"""
    connect()
    universe = get_universe(date)
    if not universe:
        return None, None, None
    per_stock = build_daily_meta(universe, prev_date, panel=panel)
    if not per_stock:
        return None, None, None
    ret3_sorted = sorted(per_stock.items(), key=lambda kv: kv[1]['ret3'], reverse=True)
    ret3_top = set(s for s, _ in ret3_sorted[:RET3_TOP_N])
    money_sorted = sorted(per_stock.items(), key=lambda kv: kv[1]['y_money'], reverse=True)
    money_top_n = max(1, int(len(money_sorted) * MONEY_TOP_PCT))
    money_top = set(s for s, _ in money_sorted[:money_top_n])
    seed = ret3_top | money_top
    if not seed:
        return per_stock, ret3_top, None
    auction_seed = prefilter_auction(seed, per_stock)
    return per_stock, ret3_top, (auction_seed or None)


def finalize_base(per_stock, ret3_top, auction_seed, today_auc, prev_auc, prev_date):
    """从已取竞价(today/prev dict)构建 auc_data → base。无下载。"""
    auc_data = []
    for stock in auction_seed:
        meta = per_stock.get(stock)
        if not meta:
            continue
        if meta['y_close'] >= meta['y_hl'] * 0.995:
            continue
        if meta['y_money'] < MIN_PREV_MONEY:
            continue
        if meta.get('avg_range', 0.0) > MAX_AVG_RANGE:
            continue
        a = today_auc.get(stock)
        if a is None:
            continue
        curr, auc_vol, auc_amt = a
        open_ratio = curr / meta['y_close'] - 1
        if open_ratio <= 0:
            continue
        if curr >= meta['y_hl'] * 0.995:
            continue
        auc_ratio = auc_vol / max(meta['y_vol'], 1)
        if auc_ratio < MIN_AUC_RATIO:
            continue
        if auc_amt < MIN_AUC_AMOUNT:
            continue
        pa = prev_auc.get(stock)
        prev_auc_vol = pa[1] if pa is not None else 0.0
        auc_data.append(dict(stock=stock, open_ratio=open_ratio, auc_ratio=auc_ratio,
                             auc_amount=auc_amt, prev_auc_vol=prev_auc_vol))
    if not auc_data:
        return None
    return dict(per_stock=per_stock, ret3_top=ret3_top, auc_data=auc_data,
                prev_date=prev_date)


def compute_base(date, prev_date=None, panel=None):
    """单日基底(自带下载,供单日/验收用)。批量全程跑请走 compute_seed_prefilter+finalize_base。"""
    connect()
    if prev_date is None:
        prev_date = prev_trading_day(date)
    if prev_date is None:
        return None
    per_stock, ret3_top, auction_seed = compute_seed_prefilter(date, prev_date, panel=panel)
    if not auction_seed:
        return None
    today_auc = batch_auction(auction_seed, date)
    prev_auc = batch_auction(auction_seed, prev_date)
    return finalize_base(per_stock, ret3_top, auction_seed, today_auc, prev_auc, prev_date)


def score_base(base, mode):
    """从基底按 mode 打分排序 → top12 list[dict]。"""
    if not base:
        return []
    per_stock = base['per_stock']
    ret3_top = base['ret3_top']
    auc_data = base['auc_data']
    auc_top = set(x['stock'] for x in
                  sorted(auc_data, key=lambda x: x['open_ratio'], reverse=True)[:AUC_TOP_N])
    out = []
    for info in auc_data:
        stock = info['stock']
        if stock not in auc_top and stock not in ret3_top:
            continue
        meta = per_stock[stock]
        close_to_high = meta['y_close'] / max(meta['y_high'], 0.01)
        open_ratio = info['open_ratio']
        auc_ratio = info['auc_ratio']
        auc_amount = info['auc_amount']
        prev_auc_vol = info['prev_auc_vol']
        tpl = _decide_tpl(close_to_high, open_ratio, auc_ratio)
        score = _score(mode, meta, tpl, open_ratio, auc_ratio, auc_amount,
                       close_to_high, prev_auc_vol)
        out.append(dict(
            stock=stock, name=(_detail(stock).get('InstrumentName', '') or ''),
            tpl=tpl, dragon_score=score, ret3=meta['ret3'], open_ratio=open_ratio,
            auction_ratio=auc_ratio, auction_amount=auc_amount,
            close_to_high=close_to_high,
        ))
    out.sort(key=lambda x: x['dragon_score'], reverse=True)
    uniq, seen = [], set()
    for item in out:
        if item['stock'] in seen:
            continue
        item['rank'] = len(uniq) + 1
        uniq.append(item)
        seen.add(item['stock'])
        if len(uniq) >= TOP_N:
            break
    return uniq


def get_dragon_pool(date, mode='v3', prev_date=None, verbose=False):
    """复现 date 当日 dragon 候选池 top12。mode in {v1,v2,v3}。返回 list[dict]。"""
    base = compute_base(date, prev_date=prev_date)
    return score_base(base, mode)
