# -*- coding: utf-8 -*-
"""全程跑三版候选池(v1/v2/v3) + forward day1-20。可断点续传。
管线:detail缓存 → 日线panel预载 → Pass1(无下载,收survivors) → 1m逐只安全下载(超时跳过,checkpoint)
      → Pass2(本地读竞价→finalize→三版打分) → forward(并集算一次) → 落盘 _pool_detail/_forward_cache。
"""
import io
import sys
import os
import json
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import repro_core as R
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
# 可配置(默认=原 QMT 4个月行为;Phase3 用 env 放宽到中台 6.5 年)
STUDY_START = os.environ.get("STUDY_START", "20260301")
STUDY_END = os.environ.get("STUDY_END", "20260630")
PANEL_START = os.environ.get("PANEL_START", "20260101")   # 需早于 STUDY_START 约20交易日
OUT_TAG = os.environ.get("OUT_TAG", "")                    # 输出文件后缀(防覆盖原产物)
MODES = ['v1', 'v2', 'v3']
FORWARD_N = 20

DETAIL_CACHE = os.path.join(HERE, "_detail_cache.json")
PASS1_CKPT = os.path.join(HERE, "_pass1%s.json" % ("_" + OUT_TAG if OUT_TAG else ""))
DL_CKPT = os.path.join(HERE, "_downloaded%s.json" % ("_" + OUT_TAG if OUT_TAG else ""))
POOL_OUT = os.path.join(HERE, "_pool_detail%s.csv" % ("_" + OUT_TAG if OUT_TAG else ""))
FWD_OUT = os.path.join(HERE, "_forward_cache%s.csv" % ("_" + OUT_TAG if OUT_TAG else ""))


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def main():
    R.connect()
    t_all = time.time()

    n = R.load_detail_cache(DETAIL_CACHE)
    if n < 1000:
        log("detail缓存不足(%d),预热中…" % n)
        R.warm_detail_cache()
        R.save_detail_cache(DETAIL_CACHE)
    log("detail缓存: %d 只" % len(R._detail_cache))

    # 取 STUDY_START 起足够多交易日(9999 → 全量,覆盖多年),再按 STUDY_END 截断
    study_days = [d for d in R.forward_trading_days(STUDY_START, 9999) if d <= STUDY_END]
    log("研究交易日 %d 天: %s ~ %s" % (len(study_days), study_days[0], study_days[-1]))

    raw_codes = R.get_raw_codes()          # 后端无关(qmt:沪深A股剔创科北;warehouse:中台daily码)
    panel = R.load_daily_panel(raw_codes, PANEL_START, study_days[-1])
    log("日线 panel: %d 只" % sum(1 for v in panel.values() if v is not None and len(v)))

    # ---- Pass 1(可续):逐日 survivors ----
    if os.path.exists(PASS1_CKPT):
        with open(PASS1_CKPT, 'r', encoding='utf-8') as f:
            day_surv = json.load(f)        # date -> [prev_date, [survivors]]
        log("Pass1 复用 checkpoint: %d 天" % len(day_surv))
    else:
        day_surv = {}
        for date in study_days:
            prev_date = R.prev_trading_day(date)
            _, _, seed = R.compute_seed_prefilter(date, prev_date, panel=panel)
            day_surv[date] = [prev_date, sorted(seed) if seed else []]
        with open(PASS1_CKPT, 'w', encoding='utf-8') as f:
            json.dump(day_surv, f)
        log("Pass1 完成并存 checkpoint")
    union_stocks = sorted(set(s for v in day_surv.values() for s in v[1]))
    log("survivor union: %d 只" % len(union_stocks))

    # ---- 1m 逐只安全下载(超时跳过 + checkpoint 续传)----
    done = set()
    if os.path.exists(DL_CKPT):
        with open(DL_CKPT, 'r', encoding='utf-8') as f:
            done = set(json.load(f))
        log("下载 checkpoint: 已 %d 只" % len(done))
    dl_start = R.prev_trading_day(study_days[0]) or study_days[0]
    todo = [s for s in union_stocks if s not in done]
    log("待下载 %d 只(超时20s/只跳过)" % len(todo))
    t0 = time.time()
    CHUNK = 100
    for i in range(0, len(todo), CHUNK):
        R.safe_download_1m(todo[i:i + CHUNK], dl_start, study_days[-1], done=done,
                           timeout=20, logf=log, every=50)
        with open(DL_CKPT, 'w', encoding='utf-8') as f:
            json.dump(sorted(done), f)
        log("  下载进度 %d/%d (%.0fs)" % (min(i + CHUNK, len(todo)), len(todo), time.time() - t0))
    log("1m 下载完成 %.0fs | done=%d / union=%d" % (time.time() - t0, len(done), len(union_stocks)))

    # ---- Pass 2:逐日本地读竞价 → finalize → 三版打分 ----
    rows = []
    for date in study_days:
        prev_date, seed = day_surv[date]
        if not seed:
            continue
        per_stock, ret3_top, seed2 = R.compute_seed_prefilter(date, prev_date, panel=panel)
        if not seed2:
            continue
        today_auc = R.read_auction(seed2, date)
        prev_auc = R.read_auction(seed2, prev_date)
        base = R.finalize_base(per_stock, ret3_top, seed2, today_auc, prev_auc, prev_date)
        if not base:
            continue
        for mode in MODES:
            for p in R.score_base(base, mode):
                rows.append(dict(
                    score_mode=mode, entry_date=date, prev_date=prev_date,
                    rank=p['rank'], code=p['stock'], name=p['name'], tpl=p['tpl'],
                    dragon_score=round(p['dragon_score'], 6),
                    open_ratio=round(p['open_ratio'], 6),
                    close_to_high=round(p['close_to_high'], 6),
                    auc_ratio=round(p['auction_ratio'], 6),
                    auc_amount=round(p['auction_amount'], 0),
                    ret3=round(p['ret3'], 6),
                ))
    pool_df = pd.DataFrame(rows)
    log("候选池明细行: %d | 按版本: %s" %
        (len(pool_df), pool_df.groupby('score_mode').size().to_dict() if len(pool_df) else {}))

    # ---- forward:三版并集,版本无关算一次 ----
    pairs = sorted(set((r['entry_date'], r['code']) for r in rows))
    log("forward 并集 (date,stock): %d" % len(pairs))
    fwd_rows = []
    for entry_date, code in pairs:
        df = panel.get(code)
        if df is None or len(df) == 0:
            continue
        idx = list(df.index)
        if entry_date not in idx:
            continue
        i0 = idx.index(entry_date)
        opens = df['open'].astype(float).values
        closes = df['close'].astype(float).values
        highs = df['high'].astype(float).values
        lows = df['low'].astype(float).values
        buy_price = float(opens[i0])
        if buy_price <= 0:
            continue
        fwd = dict(entry_date=entry_date, code=code, buy_price=round(buy_price, 4))
        rets = []
        avail = 0
        for k in range(1, FORWARD_N + 1):
            j = i0 + (k - 1)            # spec §3.2: day1 = t=0 收盘
            if j < len(idx):
                r = closes[j] / buy_price - 1.0
                fwd['day%d' % k] = round(r * 100, 4)
                rets.append((k, r))
                avail = k
            else:
                fwd['day%d' % k] = None
        fwd['days_available'] = avail
        fwd['window_incomplete'] = (avail < FORWARD_N)
        if rets:
            rs = [r for _, r in rets]
            mx = max(rs)
            fwd['max_ret'] = round(mx * 100, 4)
            fwd['day_to_peak'] = rets[rs.index(mx)][0]
            fwd['final_ret'] = round(rs[-1] * 100, 4)
            fwd['final_day'] = rets[-1][0]
            tp1 = tp2 = sl = None
            for k, _ in rets:
                j = i0 + (k - 1)
                hi = highs[j] / buy_price - 1.0
                lo = lows[j] / buy_price - 1.0
                if tp1 is None and hi >= 0.09:
                    tp1 = k
                if tp2 is None and hi >= 0.15:
                    tp2 = k
                if sl is None and lo <= -0.07:
                    sl = k
            fwd['tp1_hit_day'] = tp1
            fwd['tp2_hit_day'] = tp2
            fwd['sl_7pct_hit_day'] = sl
            fwd['is_big_meat_10'] = int(mx >= 0.10)
            fwd['is_super_meat_20'] = int(mx >= 0.20)
        fwd_rows.append(fwd)
    fwd_df = pd.DataFrame(fwd_rows)
    log("forward 缓存行: %d (incomplete=%d)" %
        (len(fwd_df), int(fwd_df['window_incomplete'].sum()) if len(fwd_df) else 0))

    pool_df.to_csv(POOL_OUT, index=False, encoding="utf-8-sig")
    fwd_df.to_csv(FWD_OUT, index=False, encoding="utf-8-sig")
    log("已存 %s / %s | 总耗时 %.0fs" %
        (os.path.basename(POOL_OUT), os.path.basename(FWD_OUT), time.time() - t_all))


if __name__ == '__main__':
    main()
