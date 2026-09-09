# -*- coding: utf-8 -*-
"""增量补尾:把 6.5年表更新到最后已收盘交易日(06-26 + 06-29),QMT 后端。
- ≤2026-05-19 行:完全不动。
- 新增 06-26 / 06-29 候选池(QMT 选股,3版)。
- 对 entry_date≥0520 的候选(窗口可能伸进新两日)重算 forward(day1=t=0),
  **只补此前为空的尾部格,已有非空值保持不变**(校验差异=0)。
- entered 仍来自聚宽 v3-default 实际交易(2026-03~06)。
"""
import io
import os
import sys
import time
import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import repro_core as R
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "event_study_dragon_2020_2026.csv")
# NEWDAYS / RECOMP_FROM / PANEL_START 在 main() 里按 CSV 现状 + 当前交易日历动态算(不再写死)
NEWDAYS = []
RECOMP_FROM = None
PANEL_START = None
FN = 20
MODES = ['v1', 'v2', 'v3']
DAYS = ['day%d' % i for i in range(1, 21)]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def forward_for(entry_date, code, panel):
    df = panel.get(code)
    if df is None or len(df) == 0:
        return None
    idx = list(df.index)
    if entry_date not in idx:
        return None
    i0 = idx.index(entry_date)
    opens = df['open'].astype(float).values
    closes = df['close'].astype(float).values
    highs = df['high'].astype(float).values
    lows = df['low'].astype(float).values
    bp = float(opens[i0])
    if bp <= 0:
        return None
    out = dict(buy_price=round(bp, 4))
    rets, avail = [], 0
    for k in range(1, FN + 1):
        j = i0 + (k - 1)
        if j < len(idx):
            r = closes[j] / bp - 1.0
            out['day%d' % k] = round(r * 100, 4)
            rets.append((k, r))
            avail = k
        else:
            out['day%d' % k] = None
    out['days_available'] = avail
    out['window_incomplete'] = (avail < FN)
    if rets:
        rs = [r for _, r in rets]
        mx = max(rs)
        out['max_ret'] = round(mx * 100, 4)
        out['day_to_peak'] = rets[rs.index(mx)][0]
        out['final_ret'] = round(rs[-1] * 100, 4)
        out['final_day'] = rets[-1][0]
        tp1 = tp2 = sl = None
        for k, _ in rets:
            j = i0 + (k - 1)
            hi = highs[j] / bp - 1.0
            lo = lows[j] / bp - 1.0
            if tp1 is None and hi >= 0.09:
                tp1 = k
            if tp2 is None and hi >= 0.15:
                tp2 = k
            if sl is None and lo <= -0.07:
                sl = k
        out['tp1_hit_day'] = tp1
        out['tp2_hit_day'] = tp2
        out['sl_7pct_hit_day'] = sl
        out['is_big_meat_10'] = int(mx >= 0.10)
        out['is_super_meat_20'] = int(mx >= 0.20)
    return out


def main():
    R.load_detail_cache(os.path.join(HERE, "_detail_cache.json"))
    R.connect()
    m = pd.read_csv(CSV, dtype={'entry_date': str, 'code': str, 'prev_date': str}, low_memory=False)
    m['entry_date'] = m['entry_date'].astype(str)
    csv_max = m['entry_date'].max()
    log("existing rows: %d | max entry_date: %s" % (len(m), csv_max))

    # ── 动态算要补的日子:CSV 之后、到今天为止的所有真实交易日(gate 会挡未定盘)──
    global NEWDAYS, RECOMP_FROM, PANEL_START
    today = datetime.date.today().strftime("%Y%m%d")
    fwd = R.forward_trading_days(csv_max, 60)
    NEWDAYS = [d for d in fwd if csv_max < d <= today]
    if not NEWDAYS:
        log("CSV 已到最新交易日 %s(今天 %s),无需更新" % (csv_max, today)); return
    tprev = R.trade_days_until(csv_max, 26)          # 近~25 交易日的 entry 需刷 forward
    RECOMP_FROM = tprev[0] if tprev else csv_max
    _tp = R.trade_days_until(RECOMP_FROM, 30)
    PANEL_START = _tp[0] if _tp else RECOMP_FROM
    log("动态: NEWDAYS=%s | RECOMP_FROM=%s | PANEL_START=%s" % (NEWDAYS, RECOMP_FROM, PANEL_START))

    # ── 治本:尾部日线(选股特征 + forward)全用 tushare EOD,QMT 只留竞价量 → 免疫 QMT 慢定盘 ──
    import subprocess
    TP_CSV = os.path.join(HERE, "_tushare_panel.csv")
    tpanel = {}
    try:
        subprocess.run(["py", "-3.10", os.path.join(HERE, "tushare_daily_panel.py"),
                        PANEL_START, NEWDAYS[-1], TP_CSV], capture_output=True, text=True, timeout=300)
        tdf = pd.read_csv(TP_CSV, dtype={'date': str, 'code': str})
        for code, g in tdf.groupby('code'):
            g = g.sort_values('date').set_index('date')
            tpanel[code] = g[['open', 'high', 'low', 'close', 'volume', 'amount']]
        tdays = sorted(tdf['date'].unique())
        log("tushare 日线面板: %d 只 × %d 日(%s..%s)" % (len(tpanel), len(tdays), tdays[0], tdays[-1]))
    except Exception as e:
        log("❌ tushare 日线面板取数失败(%s)→ 中止不写。" % repr(e)[:80])
        return
    # 竞价 open 覆盖:各 NEWDAY 的 tushare open(该日已出 EOD 才在面板里)
    ov = {}
    tp_days = set(tdays)
    for d in NEWDAYS:
        if d not in tp_days:
            continue
        for code, df in tpanel.items():
            if d in df.index:
                ov[(d, code)] = float(df.loc[d, 'open'])
    R.AUCTION_OPEN_OVERRIDE = ov
    log("竞价 open 覆盖(tushare):%d 条,覆盖日=%s" % (len(ov), sorted(set(k[0] for k in ov))))

    # 1) 新两日选股池(QMT)
    new_pool = []
    for d in NEWDAYS:
        base = R.compute_base(d, panel=tpanel)
        if not base:
            log("WARN: %s 选股基底空" % d); continue
        for mode in MODES:
            for p in R.score_base(base, mode):
                new_pool.append(dict(
                    score_mode=mode, entry_date=d, prev_date=base['prev_date'],
                    rank=p['rank'], code=p['stock'], name=p['name'], tpl=p['tpl'],
                    dragon_score=round(p['dragon_score'], 6),
                    open_ratio=round(p['open_ratio'], 6),
                    close_to_high=round(p['close_to_high'], 6),
                    auc_ratio=round(p['auction_ratio'], 6),
                    auc_amount=round(p['auction_amount'], 0),
                    ret3=round(p['ret3'], 6), month=d[:6]))
    new_df = pd.DataFrame(new_pool)
    log("新两日候选池行: %d %s" % (len(new_df), new_df.groupby(['entry_date', 'score_mode']).size().to_dict() if len(new_df) else {}))

    # ── 定盘校验门(独立源 tushare,防写入未定盘脏竞价)──
    # QMT 尾部 1m/1d 会自我修正、且可能 1m与1d 同向错(QMT 内部一致性校验拦不住)。
    # 故用独立源 tushare 真实 open_ratio(open/pre_close-1,不复权)逐只对选中候选;
    # 某日有候选 |偏差|>0.5% → 该日数据未定盘/脏 → 丢弃该日(不写),保留干净日。
    if len(new_df):
        import subprocess
        import json as _json
        try:
            raw = subprocess.run(
                ["py", "-3.10", os.path.join(HERE, "tushare_or.py"), ",".join(NEWDAYS)],
                capture_output=True, text=True, timeout=180).stdout
            real = _json.loads(raw) if raw.strip() else {}
        except Exception as e:
            log("⚠️ tushare 校验取数失败(%s)→ 保守起见中止不写。" % repr(e)[:80])
            return
        bad_days, nref = {}, {d: 0 for d in NEWDAYS}
        for _, r in new_df.iterrows():
            d, c = r['entry_date'], r['code']
            rv = real.get("%s|%s" % (d, c))
            if rv is None:
                continue
            nref[d] = nref.get(d, 0) + 1
            if abs(float(r['open_ratio']) - rv) > 0.005:
                bad_days.setdefault(d, []).append((c, round(float(r['open_ratio']) * 100, 2), round(rv * 100, 2)))
        keep = []
        for d in NEWDAYS:
            bd = bad_days.get(d, [])
            if nref.get(d, 0) == 0:
                log("⏸ %s 无 tushare 参照(今天未收盘/tushare 未出)→ 未定盘,暂不写,等下次跑" % d)
            elif bd:
                log("❌ %s 定盘校验失败 %d 只(QMT竞价 vs tushare真实 偏差>0.5%%),丢弃该日:" % (d, len(bd)))
                for x in bd[:6]:
                    log("   %s pool_or=%+.2f%% tushare_or=%+.2f%%" % x)
            else:
                log("✅ %s 定盘校验通过(选中候选竞价 == tushare真实,%d 只)" % (d, nref[d]))
                keep.append(d)
        if not keep:
            log("→ 两日均脏,不写。等 QMT 定盘后重跑 update_tail。")
            return
        new_df = new_df[new_df['entry_date'].isin(keep)].reset_index(drop=True)
        global NEWDAYS_KEPT
        NEWDAYS_KEPT = keep

    # 2) forward 需刷新的 (entry_date,code):existing≥0520 ∪ new
    recomp_mask = m['entry_date'] >= RECOMP_FROM
    pairs = set(zip(m.loc[recomp_mask, 'entry_date'], m.loc[recomp_mask, 'code']))
    pairs |= set(zip(new_df['entry_date'], new_df['code'])) if len(new_df) else set()
    codes = sorted(set(c for _, c in pairs))
    log("forward 刷新 pairs=%d codes=%d" % (len(pairs), len(codes)))

    # 3) forward 全用 tushare 面板(免疫 QMT;历史settled日 QMT==tushare,不变性成立)
    fwd = {}
    for ed, c in pairs:
        f = forward_for(ed, c, tpanel)
        if f is not None:
            fwd[(ed, c)] = f

    # 4+5) 红线:只补 existing 的空 day 格,已有非空一律不动(源seam无关,历史逐位不变)。
    #      summary(max/final/hit)从"已有非空 + 新填"的合并序列重算,与展示的 day 值自洽。
    m = m.set_index(['entry_date', 'code']).sort_index()
    filled_cells = 0
    for (ed, c), f in fwd.items():
        if (ed, c) not in m.index:
            continue
        block = m.loc[(ed, c)]                          # 同 (date,code) 有 v1/v2/v3 三行(forward 版本无关,取一行读)
        row = block.iloc[0] if getattr(block, 'ndim', 1) == 2 else block
        series, newly = [], False
        for k in range(1, FN + 1):
            col = 'day%d' % k
            ev = row[col] if col in row.index else None
            if pd.notna(ev):
                series.append((k, float(ev)))          # 已有非空:原样保留
            else:
                nv = f.get(col)
                if nv is not None:
                    m.loc[(ed, c), col] = nv             # 只补空格
                    series.append((k, float(nv)))
                    newly = True
                    filled_cells += 1
        if not newly:
            continue
        if pd.isna(row.get('buy_price')) and f.get('buy_price') is not None:
            m.loc[(ed, c), 'buy_price'] = f['buy_price']
        ks = [k for k, _ in series]
        rs = [r / 100.0 for _, r in series]
        mx = max(rs)
        m.loc[(ed, c), 'max_ret'] = round(mx * 100, 4)
        m.loc[(ed, c), 'day_to_peak'] = ks[rs.index(mx)]
        m.loc[(ed, c), 'final_ret'] = round(rs[-1] * 100, 4)
        m.loc[(ed, c), 'final_day'] = ks[-1]
        m.loc[(ed, c), 'days_available'] = max(ks)
        m.loc[(ed, c), 'window_incomplete'] = (max(ks) < FN)
        m.loc[(ed, c), 'is_big_meat_10'] = int(mx >= 0.10)
        m.loc[(ed, c), 'is_super_meat_20'] = int(mx >= 0.20)
        for col in ['tp1_hit_day', 'tp2_hit_day', 'sl_7pct_hit_day']:
            if f.get(col) is not None and pd.isna(row.get(col)):
                m.loc[(ed, c), col] = f[col]
    m = m.reset_index()
    log("只补空格:填了 %d 个 day 空格(existing 已有非空保留不动)" % filled_cells)

    # 6) 新交易日:pool + forward 合并
    fwd_cols = (['buy_price'] + DAYS + ['days_available', 'window_incomplete', 'max_ret',
                'day_to_peak', 'final_ret', 'final_day', 'tp1_hit_day', 'tp2_hit_day',
                'sl_7pct_hit_day', 'is_big_meat_10', 'is_super_meat_20'])
    if len(new_df):
        nf = []
        for _, r in new_df.iterrows():
            f = fwd.get((r['entry_date'], r['code']), {})
            row = dict(r)
            row.update({k: f.get(k) for k in fwd_cols})
            nf.append(row)
        new_full = pd.DataFrame(nf)
        m = pd.concat([m, new_full], ignore_index=True)

    # 7) 排序 + 落盘
    m = m.sort_values(['score_mode', 'entry_date', 'rank']).reset_index(drop=True)
    m.to_csv(CSV, index=False, encoding="utf-8-sig")
    log("写回 %s | 总行 %d | max entry_date %s" % (os.path.basename(CSV), len(m), m['entry_date'].max()))

    # 更新 cutoff(用实际写入的最大日,丢弃脏日时不虚标)
    cutoff = str(m['entry_date'].max())
    with io.open(os.path.join(HERE, "_data_cutoff.txt"), 'w', encoding='utf-8') as f:
        f.write("forward_cutoff=%s\nselection_cutoff=%s\ntoday_settled=True\n" % (cutoff, cutoff))
    log("cutoff -> %s。下一步:build_dynamic.py + build_html_dynamic.py" % cutoff)


if __name__ == '__main__':
    main()
