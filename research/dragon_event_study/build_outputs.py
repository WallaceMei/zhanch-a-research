# -*- coding: utf-8 -*-
"""join 候选池 + forward + ENTRY/EXIT → 交付 CSV/JSON,并产 summary.md(spec 7.1)。
- 主表:每 (score_mode, entry_date, code) 一行(三版各自的候选池)。
- forward 版本无关,按 (entry_date, code) 左 join。
- ENTRY/EXIT 来自聚宽 v3-default 实际交易日志(v1/v2 无独立交易 → entered/exit 反映实际那次 v3 运行)。
"""
import io
import os
import sys
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def rd(name, **kw):
    return pd.read_csv(os.path.join(HERE, name), dtype={'entry_date': str, 'code': str,
                                                        'prev_date': str}, **kw)


def main():
    pool = rd("_pool_detail.csv")
    fwd = rd("_forward_cache.csv")
    entry = rd("_entry_log.csv")
    exit_ = rd("_exit_log.csv")
    # entry/exit entry_date as str
    for d in (entry, exit_):
        if 'entry_date' in d:
            d['entry_date'] = d['entry_date'].astype(str)
        if 'code' in d:
            d['code'] = d['code'].astype(str)

    day_cols = ['day%d' % i for i in range(1, 21)]
    fwd_keep = (['entry_date', 'code', 'buy_price'] + day_cols +
                ['days_available', 'window_incomplete', 'pending_day', 'max_ret', 'day_to_peak',
                 'final_ret', 'final_day', 'tp1_hit_day', 'tp2_hit_day',
                 'sl_7pct_hit_day', 'is_big_meat_10', 'is_super_meat_20'])
    fwd_keep = [c for c in fwd_keep if c in fwd.columns]

    m = pool.merge(fwd[fwd_keep], on=['entry_date', 'code'], how='left')
    m = m.merge(entry, on=['entry_date', 'code'], how='left')
    m = m.merge(exit_, on=['entry_date', 'code'], how='left')
    m['entered'] = m['entered'].fillna(0).astype(int)
    m['month'] = m['entry_date'].str.slice(0, 6)

    # 交付 CSV
    csv_path = os.path.join(HERE, "event_study_dragon_3to6.csv")
    m.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print("CSV:", csv_path, "| rows:", len(m))

    # 交付 JSON(喂 HTML)。NaN→None。
    def clean(v):
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        return v
    records = [{k: clean(v) for k, v in row.items()} for row in m.to_dict('records')]
    cutoff = {}
    cpath = os.path.join(HERE, "_data_cutoff.txt")
    if os.path.exists(cpath):
        for ln in io.open(cpath, encoding='utf-8'):
            if '=' in ln:
                k, v = ln.strip().split('=', 1)
                cutoff[k] = v
    meta = dict(
        generated_for="战车A龙头3 v1.4.0D_observer 候选池3-6月forward回看",
        versions=sorted(m['score_mode'].unique().tolist()),
        months=sorted(m['month'].unique().tolist()),
        n_rows=len(m),
        forward_cutoff=cutoff.get('forward_cutoff', ''),
        selection_cutoff=cutoff.get('selection_cutoff', ''),
        today_settled=cutoff.get('today_settled', ''),
        note="forward版本无关; ENTRY/EXIT来自聚宽v3-default实际交易; v1/v2为本地code-faithful复现(无ground truth)",
    )
    json_path = os.path.join(HERE, "event_study_dragon_3to6.json")
    with io.open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dict(meta=meta, rows=records), f, ensure_ascii=False)
    print("JSON:", json_path)

    build_summary(m, day_cols)


def _stats(series):
    s = pd.to_numeric(series, errors='coerce').dropna()
    if len(s) == 0:
        return ('–', '–', '–', 0)
    return (round(float(s.mean()), 2), round(float(s.median()), 2),
            round(float((s > 0).mean() * 100), 1), int(len(s)))


def build_summary(m, day_cols):
    lines = []
    P = lines.append
    P("# 候选池 forward 回看 summary(只报数,不下结论)\n")
    P("> 数据源:本地 QMT 1m首根复现候选池(v3 对聚宽日志 15/15 精确吻合)+ QMT 1d forward。")
    P("> ENTRY/EXIT 来自聚宽 v3-default 实际交易日志;v1/v2 为本地 code-faithful 复现,无独立交易,entered/exit 反映实际那次(v3)运行。")
    P("> score_mode 逐版分列。v3 仅记录,不评判选股有效性。\n")

    # 总览
    P("## 总览(按 score_mode × tpl × entered 计数)\n")
    P("| version | tpl | 候选数 | entered=1 | entered=0 |")
    P("|---|---|---:|---:|---:|")
    for ver in sorted(m['score_mode'].unique()):
        mv = m[m['score_mode'] == ver]
        for tpl in ['deep_water', 'trend_core']:
            mt = mv[mv['tpl'] == tpl]
            P("| %s | %s | %d | %d | %d |" %
              (ver, tpl, len(mt), int((mt['entered'] == 1).sum()), int((mt['entered'] == 0).sum())))
    P("")

    # forward 对照,按月分开(核心)
    P("## forward 对照 — trend_core vs deep_water,按月分开(核心)\n")
    P("每格:day5 / day10 / day20 的 均值% | 中位% | 胜率(>0)% | 样本n。**月度稳定性看这里,合计仅参考。**\n")
    months = sorted(m['month'].unique())
    for ver in sorted(m['score_mode'].unique()):
        P("### score_mode = %s\n" % ver)
        for mo in months:
            P("**%s**" % mo)
            P("| tpl | day5 均/中/胜/n | day10 均/中/胜/n | day20 均/中/胜/n |")
            P("|---|---|---|---|")
            sub = m[(m['score_mode'] == ver) & (m['month'] == mo)]
            for tpl in ['deep_water', 'trend_core']:
                st = sub[sub['tpl'] == tpl]
                d5 = _stats(st['day5']); d10 = _stats(st['day10']); d20 = _stats(st['day20'])
                P("| %s | %s/%s/%s/%d | %s/%s/%s/%d | %s/%s/%s/%d |" %
                  (tpl, d5[0], d5[1], d5[2], d5[3], d10[0], d10[1], d10[2], d10[3],
                   d20[0], d20[1], d20[2], d20[3]))
            P("")
        # 合计(参考)
        P("**%s 合计(参考,掩盖月度漂移)**" % ver)
        P("| tpl | day5 均/中/胜/n | day10 均/中/胜/n | day20 均/中/胜/n |")
        P("|---|---|---|---|")
        sub = m[m['score_mode'] == ver]
        for tpl in ['deep_water', 'trend_core']:
            st = sub[sub['tpl'] == tpl]
            d5 = _stats(st['day5']); d10 = _stats(st['day10']); d20 = _stats(st['day20'])
            P("| %s | %s/%s/%s/%d | %s/%s/%s/%d | %s/%s/%s/%d |" %
              (tpl, d5[0], d5[1], d5[2], d5[3], d10[0], d10[1], d10[2], d10[3],
               d20[0], d20[1], d20[2], d20[3]))
        P("")

    # 触发统计 by tpl(用 v3 池,版本无关的 forward 触发)
    P("## 触发统计(按 tpl,forward 口径;每版候选集不同,这里按 score_mode 分)\n")
    P("| version | tpl | n | sl_7pct% | tp1(+9%)% | tp2(+15%)% | big_meat_10% | super_meat_20% |")
    P("|---|---|---:|---:|---:|---:|---:|---:|")
    for ver in sorted(m['score_mode'].unique()):
        for tpl in ['deep_water', 'trend_core']:
            st = m[(m['score_mode'] == ver) & (m['tpl'] == tpl)]
            n = len(st)
            if n == 0:
                continue
            sl = round(float(pd.to_numeric(st['sl_7pct_hit_day'], errors='coerce').notna().mean() * 100), 1)
            t1 = round(float(pd.to_numeric(st['tp1_hit_day'], errors='coerce').notna().mean() * 100), 1)
            t2 = round(float(pd.to_numeric(st['tp2_hit_day'], errors='coerce').notna().mean() * 100), 1)
            bm = round(float(pd.to_numeric(st['is_big_meat_10'], errors='coerce').fillna(0).mean() * 100), 1)
            sm = round(float(pd.to_numeric(st['is_super_meat_20'], errors='coerce').fillna(0).mean() * 100), 1)
            P("| %s | %s | %d | %s | %s | %s | %s | %s |" % (ver, tpl, n, sl, t1, t2, bm, sm))
    P("")

    # forward vs 实际出场(entered=1)
    P("## forward vs 策略实际出场(entered=1 的票)\n")
    P("| version | n(entered) | forward day20 均值% | 实际 pnl 均值% | 实际持有天均 |")
    P("|---|---:|---:|---:|---:|")
    for ver in sorted(m['score_mode'].unique()):
        en = m[(m['score_mode'] == ver) & (m['entered'] == 1)]
        if len(en) == 0:
            P("| %s | 0 | – | – | – |" % ver)
            continue
        f20 = round(float(pd.to_numeric(en['day20'], errors='coerce').mean()), 2)
        pnl = round(float(pd.to_numeric(en['actual_pnl_pct'], errors='coerce').mean()), 2)
        hd = round(float(pd.to_numeric(en['hold_days'], errors='coerce').mean()), 1)
        P("| %s | %d | %s | %s | %s |" % (ver, len(en), f20, pnl, hd))
    P("")
    P("> ⚠️ 只报数。trend_core vs deep_water 的区分度是否真有效,看月度一致性自行判断;summary 不下结论。")

    path = os.path.join(HERE, "summary.md")
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("summary.md:", path)


if __name__ == '__main__':
    main()
