# -*- coding: utf-8 -*-
"""Project1 Paper — 当日候选池 live 构建(盘前 09:26-09:28 跑)。

⚠️ 护栏1:xtdata 竞价/历史1m 取数路径未经实盘验证(周一实测项)。
⚠️ 护栏3:只 import xtquant.xtdata(行情只读),不发任何交易指令。

数据链:
  日线 meta(截至昨日)  ← 主缓存 + daily_tail(update_daily_cache 盘后已补)
  今日竞价              ← xtdata.get_full_tick(9:25 后,open/volume/amount)
  昨日竞价              ← canonical/auction_tail;缺口日(warehouse断档)就地用
                          xtdata 历史1m 首根(09:30竞价根)+ tushare open 定盘校验
                          (|xtdata竞价价/tushare open - 1| > 0.5% 丢弃该票,不带病入池)
打分:repro_core L5/L6 零改动(经 pool_repro monkeypatch 的数据接口)。
"""
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_config as C     # noqa: E402
import pool_repro as PR      # noqa: E402


def _tushare_open_map(d8):
    """tail 缓存里 tushare 源的当日 open(定盘校验参照)。"""
    if not os.path.exists(C.TAIL_DAILY_PARQUET):
        return {}
    tl = pd.read_parquet(C.TAIL_DAILY_PARQUET)
    tl = tl[(tl['d8'].astype(str) == d8)]
    return {r.code: float(r.open) for r in tl.itertuples(index=False) if r.open and r.open > 0}


def fetch_prev_auction_xtdata(codes, prev_d8, log=print):
    """缺口日昨竞价:xtdata 历史1m 首根(09:30) + tushare open 校验闸。
    返回 {code: (px, vol手, amt元)};校验不过/无数据的票不返回(=不入池,宁缺毋滥)。"""
    from xtquant import xtdata
    ref = _tushare_open_map(prev_d8)
    out, dropped = {}, []
    for code in codes:
        try:
            xtdata.download_history_data(code, '1m', start_time=prev_d8, end_time=prev_d8)
        except Exception:
            pass
    md = xtdata.get_market_data_ex([], list(codes), period='1m',
                                   start_time=prev_d8, end_time=prev_d8 + '235959')
    for code in codes:
        df = md.get(code)
        if df is None or len(df) == 0:
            dropped.append((code, 'no_1m'))
            continue
        first = df.iloc[0]
        label = str(df.index[0])
        if label[8:12] != '0930':
            dropped.append((code, 'firstbar_%s' % label[8:12]))
            continue
        px = float(first['open']); vol = float(first['volume']); amt = float(first['amount'])
        ts_open = ref.get(code)
        if ts_open is None:
            dropped.append((code, 'no_tushare_ref'))
            continue
        if abs(px / ts_open - 1.0) > 0.005:
            dropped.append((code, 'settle_gate %.3f vs %.3f' % (px, ts_open)))
            continue
        if px > 0 and vol > 0:
            out[code] = (px, vol, amt)
    if dropped:
        log("[live_pool] 昨竞价缺口补数丢弃 %d 只(闸门宁缺毋滥): %s" % (
            len(dropped), dropped[:8]))
    return out


def fetch_today_auction_xtdata(codes, log=print):
    """今日竞价(9:25 后):full_tick 的 open/volume/amount。"""
    from xtquant import xtdata
    out = {}
    ticks = xtdata.get_full_tick(list(codes))
    for code in codes:
        t = ticks.get(code) or {}
        px = float(t.get('open') or 0) or float(t.get('lastPrice') or 0)
        vol = float(t.get('volume') or 0)
        amt = float(t.get('amount') or 0)
        if px > 0 and vol > 0:
            out[code] = (px, vol, amt)
    log("[live_pool] 今日竞价 full_tick: %d/%d 只有效" % (len(out), len(codes)))
    return out


def build_pool_live(d8, log=print):
    """live 当日 top12。返回 (pool list, diag dict)。"""
    PR._load()
    prev = PR.prev_trading_day(d8)
    if prev is None:
        raise RuntimeError("无昨日数据")
    days = PR.trade_days()
    if days[-1] < prev:
        raise RuntimeError("日线数据只到 %s,缺昨日 %s(先跑 update_daily_cache)" % (days[-1], prev))
    rc = PR.rc
    per_stock, ret3_top, auction_seed = rc.compute_seed_prefilter(d8, prev, panel=PR.panel())
    diag = dict(d8=d8, prev=prev, seed=len(auction_seed))
    if not auction_seed:
        return [], diag
    log("[live_pool] %s seed=%d (prev=%s)" % (d8, len(auction_seed), prev))
    today_auc = fetch_today_auction_xtdata(auction_seed, log=log)
    # 昨竞价:先缓存,缺的走 xtdata+tushare 闸门
    prev_auc, missing = {}, []
    for s in auction_seed:
        a = PR.get_auction(s, prev)
        if a is not None:
            prev_auc[s] = a
        else:
            missing.append(s)
    if missing:
        log("[live_pool] 昨竞价缓存缺 %d 只,走 xtdata+tushare 校验闸补" % len(missing))
        prev_auc.update(fetch_prev_auction_xtdata(missing, prev, log=log))
    diag.update(today_auc=len(today_auc), prev_auc=len(prev_auc),
                prev_auc_from_cache=len(auction_seed) - len(missing))
    base = rc.finalize_base(per_stock, ret3_top, auction_seed, today_auc, prev_auc, prev)
    if not base:
        return [], diag
    pool = rc.score_base(base, 'v3')
    diag['pool'] = len(pool)
    return pool, diag


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--d8", required=True, help="交易日(live模式盘前跑)")
    args = ap.parse_args()
    pool, diag = build_pool_live(args.d8)
    print("diag=%s" % diag)
    for p in pool[:12]:
        print("  %s %s tpl=%s score=%.3f" % (p['stock'], p.get('name', ''), p['tpl'], p['dragon_score']))
