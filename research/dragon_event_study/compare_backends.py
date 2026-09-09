# -*- coding: utf-8 -*-
"""Phase2 并行验证:中台后端 vs 原 QMT 后端,重叠期(2026-03~06)逐字段比对。

同一份 repro_core(只翻 R.BACKEND 全局),分别用中台/QMT 数据跑同一选股链,比:
  A. 端到端 Top12(候选池):中台 vs 已存 _pool_detail.csv(QMT 原产物)。逐 (mode,date,code) 比 dragon_score
     及竞价字段(open_ratio/auc_ratio/auc_amount)、close_to_high、ret3。
  B. 日线 meta 漂移:同 universe 下中台 panel vs QMT-live panel 的 avg_range/close/high/y_money 逐股差
     —— 重点查接入方案标注的"日线 H/L 源差→avg_range→v3 dragon_score 漂移"。

用 py-3.10 跑(同时具备 data_warehouse + xtquant)。QMT 端需 miniQMT 在线(读本地已下载缓存)。
"""
import io
import os
import sys
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.environ.setdefault('REPRO_BACKEND', 'warehouse')
import repro_core as R

HERE = os.path.dirname(os.path.abspath(__file__))
MODES = ['v1', 'v2', 'v3']
COLS = ['open_ratio', 'close_to_high', 'auc_ratio', 'auc_amount', 'ret3', 'dragon_score']


def run_pool(panel, dates):
    """用当前 R.BACKEND 跑逐日 v1/v2/v3 Top12 → DataFrame。"""
    rows = []
    for date in dates:
        prev = R.prev_trading_day(date)
        per_stock, ret3_top, seed2 = R.compute_seed_prefilter(date, prev, panel=panel)
        if not seed2:
            continue
        today_auc = R.read_auction(seed2, date)
        prev_auc = R.read_auction(seed2, prev)
        base = R.finalize_base(per_stock, ret3_top, seed2, today_auc, prev_auc, prev)
        if not base:
            continue
        for mode in MODES:
            for p in R.score_base(base, mode):
                rows.append(dict(
                    score_mode=mode, entry_date=int(date), code=p['stock'], rank=p['rank'],
                    dragon_score=round(p['dragon_score'], 6),
                    open_ratio=round(p['open_ratio'], 6),
                    close_to_high=round(p['close_to_high'], 6),
                    auc_ratio=round(p['auction_ratio'], 6),
                    auc_amount=round(p['auction_amount'], 0),
                    ret3=round(p['ret3'], 6)))
    return pd.DataFrame(rows)


def main():
    R.load_detail_cache(os.path.join(HERE, '_detail_cache.json'))
    qmt_pool = pd.read_csv(os.path.join(HERE, '_pool_detail.csv'))
    dates = [str(d) for d in sorted(qmt_pool['entry_date'].unique())]
    print("重叠期 %d 天: %s ~ %s" % (len(dates), dates[0], dates[-1]))

    # ---------- 中台后端跑 ----------
    R.BACKEND = 'warehouse'
    raw = R.get_raw_codes()
    print("中台 raw codes: %d" % len(raw))
    wh_panel = R.load_daily_panel(raw, "20260101", dates[-1])
    wh = run_pool(wh_panel, dates)
    print("中台候选池行: %d (%s)" % (len(wh), wh.groupby('score_mode').size().to_dict()))

    # ========== A. 端到端 Top12 比对(中台 vs 已存 QMT) ==========
    print("\n" + "=" * 70)
    print("A. 端到端 Top12:中台 vs 原 QMT(_pool_detail.csv)")
    print("=" * 70)
    q = qmt_pool[['score_mode', 'entry_date', 'code', 'rank'] + COLS].copy()
    for mode in MODES:
        qm = q[q.score_mode == mode]
        wm = wh[wh.score_mode == mode]
        qset = set(zip(qm.entry_date, qm.code))
        wset = set(zip(wm.entry_date, wm.code))
        inter = qset & wset
        only_q = qset - wset
        only_w = wset - qset
        # 逐日 Top12 集合完全一致的天数
        days = sorted(set(qm.entry_date))
        exact_days = 0
        rank1_same = 0
        for d in days:
            qs = set(qm[qm.entry_date == d].code)
            ws = set(wm[wm.entry_date == d].code)
            if qs == ws:
                exact_days += 1
            q1 = qm[(qm.entry_date == d) & (qm['rank'] == 1)]['code']
            w1 = wm[(wm.entry_date == d) & (wm['rank'] == 1)]['code']
            if len(q1) and len(w1) and q1.iloc[0] == w1.iloc[0]:
                rank1_same += 1
        # 共同 (date,code) 的字段差
        merged = qm.merge(wm, on=['entry_date', 'code'], suffixes=('_q', '_w'))
        print("\n[%s] QMT池=%d 中台池=%d 交集=%d | 仅QMT=%d 仅中台=%d" %
              (mode, len(qset), len(wset), len(inter), len(only_q), len(only_w)))
        print("     Top12集合完全一致: %d/%d 天 | rank1一致: %d/%d 天 | 候选重合率(Jaccard): %.3f" %
              (exact_days, len(days), rank1_same, len(days),
               len(inter) / max(1, len(qset | wset))))
        for c in COLS:
            dif = (merged[c + '_q'] - merged[c + '_w']).abs()
            print("     %-14s 共同%d  maxΔ=%.6g  meanΔ=%.6g" %
                  (c, len(merged), dif.max() if len(dif) else 0, dif.mean() if len(dif) else 0))

    # 落盘差异明细(仅QMT/仅中台 + dragon_score 漂移最大的)
    diff_path = os.path.join(HERE, '_compare_diff.csv')
    rec = []
    for mode in MODES:
        qm = q[q.score_mode == mode]; wm = wh[wh.score_mode == mode]
        m = qm.merge(wm, on=['entry_date', 'code'], how='outer', suffixes=('_q', '_w'), indicator=True)
        m['score_mode'] = mode
        rec.append(m)
    allm = pd.concat(rec, ignore_index=True)
    allm['ds_diff'] = (allm['dragon_score_q'] - allm['dragon_score_w']).abs()
    allm.sort_values(['_merge', 'ds_diff'], ascending=[True, False]).to_csv(
        diff_path, index=False, encoding='utf-8-sig')
    print("\n差异明细落盘: %s (含 left_only=仅QMT / right_only=仅中台 / both)" % diff_path)

    # ========== B. 日线 meta 漂移(avg_range 重点) ==========
    print("\n" + "=" * 70)
    print("B. 日线 meta 漂移:中台 panel vs QMT-live panel(同 universe)")
    print("=" * 70)
    try:
        R.BACKEND = 'qmt'
        q_panel = R.load_daily_panel(raw, "20260101", dates[-1])
        nq = sum(1 for v in q_panel.values() if v is not None and len(v))
        print("QMT-live panel: %d 只有数据" % nq)
        sample = dates[::20]    # 抽样几天
        fields = ['avg_range', 'close_to_20d_high', 'y_close', 'y_high', 'y_money', 'ret3']
        agg = {f: [] for f in fields}
        nbig = 0; ncommon = 0
        for d in sample:
            prev = R.prev_trading_day(d)
            R.BACKEND = 'warehouse'
            uni = R.get_universe(d)
            mw = R.build_daily_meta(uni, prev, panel=wh_panel)
            mq = R.build_daily_meta(uni, prev, panel=q_panel)
            common = set(mw) & set(mq)
            ncommon += len(common)
            for s in common:
                for f in fields:
                    agg[f].append(abs(mw[s][f] - mq[s][f]))
                if abs(mw[s]['avg_range'] - mq[s]['avg_range']) > 1e-4:
                    nbig += 1
        print("抽样 %d 天, 共同股次 %d" % (len(sample), ncommon))
        for f in fields:
            a = np.array(agg[f]) if agg[f] else np.array([0.0])
            print("  %-18s maxΔ=%.6g  meanΔ=%.6g" % (f, a.max(), a.mean()))
        print("  avg_range 差>1e-4 的股次: %d / %d (%.2f%%)" %
              (nbig, ncommon, 100.0 * nbig / max(1, ncommon)))
    except Exception as e:
        print("QMT-live meta 比对跳过(QMT 不可用?): %s" % e)

    print("\n判定参考:Top12集合高度一致 + 竞价字段≈0差 + dragon_score 漂移小(v3 因 avg_range 略大可接受)→ 通过。")


if __name__ == '__main__':
    main()
