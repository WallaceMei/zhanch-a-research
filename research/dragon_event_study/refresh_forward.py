# -*- coding: utf-8 -*-
"""补尾部日线 + 重算 forward。历史(已收盘日)数字不变,只补 06-24/06-25 等尾部缺的日线。
- 下载候选股 1d 到最后已收盘交易日(06-25 市场已收盘则纳入)。
- pending:某 forward 日落在"今天且今天未定盘" → 标 pending,区别于 window_incomplete(未来未到期)。
- 元信息标注 选股竞价 / forward日线 两条路径各自的数据截止日。
"""
import io
import sys
import os
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import repro_core as R
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FORWARD_N = 20
TODAY = "20260625"


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def main():
    R.connect()
    pool = pd.read_csv(os.path.join(HERE, "_pool_detail.csv"), dtype={'entry_date': str, 'code': str})
    codes = sorted(pool['code'].unique())
    log("候选股 %d 只 | pool entry_date max=%s" % (len(codes), pool['entry_date'].max()))

    # 下载 1d 到 TODAY(逐只安全下载)
    t0 = time.time()
    done, skipped = R.safe_download(codes, '1d', "20260101", TODAY, timeout=20, logf=log, every=300)
    log("1d 下载完成 %.0fs | skipped=%d" % (time.time() - t0, len(skipped)))

    panel = R.load_daily_panel(codes, "20260101", TODAY)
    # 数据截止日:参考多只票的最大日线日期
    maxdates = [df.index.max() for df in panel.values() if df is not None and len(df)]
    forward_cutoff = max(maxdates) if maxdates else TODAY
    today_settled = any((df.index.max() >= TODAY) for df in panel.values() if df is not None and len(df))
    log("forward 日线截止日=%s | 今日(%s)已定盘=%s" % (forward_cutoff, TODAY, today_settled))

    fwd_rows = []
    pairs = sorted(set(zip(pool['entry_date'], pool['code'])))
    pending_cells = 0
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
        pend_day = None
        for k in range(1, FORWARD_N + 1):
            j = i0 + (k - 1)            # spec §3.2: day1 = t=0 收盘, dayN = t+(N-1) 收盘
            if j < len(idx):
                r = closes[j] / buy_price - 1.0
                fwd['day%d' % k] = round(r * 100, 4)
                rets.append((k, r))
                avail = k
            else:
                fwd['day%d' % k] = None
                # 若该 forward 日恰是"今天且今天未定盘" → pending(紧邻 avail 的下一日)
                if pend_day is None and (not today_settled) and (j == len(idx)):
                    pend_day = k
        fwd['days_available'] = avail
        fwd['window_incomplete'] = (avail < FORWARD_N)
        fwd['pending_day'] = pend_day        # 今日未定盘时,紧邻的下一 forward 日;否则 None
        if pend_day:
            pending_cells += 1
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
    log("forward 行 %d | incomplete=%d | pending_cells=%d | entry_date max=%s" %
        (len(fwd_df), int(fwd_df['window_incomplete'].sum()), pending_cells, fwd_df['entry_date'].max()))

    # 与旧 cache 比对(旧为 off-by-one 版;本次含 day1=t=0 口径修正 → 预期大量变化)
    old_path = os.path.join(HERE, "_forward_cache.csv")
    if os.path.exists(old_path):
        old = pd.read_csv(old_path, dtype={'entry_date': str, 'code': str})
        daycols = ['day%d' % i for i in range(1, 21)]
        merged = old.merge(fwd_df, on=['entry_date', 'code'], suffixes=('_old', '_new'))
        changed = 0
        for c in daycols:
            co, cn = c + '_old', c + '_new'
            both = merged[merged[co].notna() & merged[cn].notna()]
            changed += int((both[co].round(4) != both[cn].round(4)).sum())
        log("与旧cache差异格数=%d(若旧为off-by-one版,差异预期非0=口径修正所致)" % changed)

    fwd_df.to_csv(old_path, index=False, encoding="utf-8-sig")
    # 写数据截止信息供 build_outputs 读
    with io.open(os.path.join(HERE, "_data_cutoff.txt"), 'w', encoding='utf-8') as f:
        f.write("forward_cutoff=%s\nselection_cutoff=%s\ntoday_settled=%s\n" %
                (forward_cutoff, pool['entry_date'].max(), today_settled))
    log("已存 _forward_cache.csv + _data_cutoff.txt")


if __name__ == '__main__':
    main()
