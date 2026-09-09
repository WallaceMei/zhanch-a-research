# -*- coding: utf-8 -*-
"""6.5年候选池 → 动态加载回看表的数据底座。
- 读 event_study_dragon_2020_2026.csv(51033行,已含 day1=t=0 口径)。
- 左 join 2026-03~06 的 ENTRY/EXIT(只这段有实际交易日志)→ entered 仅该段有值。
- 数据按 score_mode 分片成 viewer/data/pool_v{1,2,3}.js(<script src> 加载,file:// 双击可用,免起服务)。
- 另出整份 JSON 交付 + 6.5年 summary。
"""
import io
import os
import sys
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, "viewer")
DATADIR = os.path.join(VIEWER, "data")
SRC = os.path.join(HERE, "event_study_dragon_2020_2026.csv")

DAYS = ['day%d' % i for i in range(1, 21)]
# 页面用到的列(精简 payload;score_mode 由分片文件隐含)
KEEP = (['entry_date', 'rank', 'code', 'name', 'tpl', 'dragon_score', 'open_ratio',
         'close_to_high', 'auc_ratio', 'auc_amount', 'ret3', 'buy_price'] + DAYS +
        ['days_available', 'window_incomplete', 'max_ret', 'day_to_peak', 'final_ret',
         'final_day', 'tp1_hit_day', 'tp2_hit_day', 'sl_7pct_hit_day',
         'is_big_meat_10', 'is_super_meat_20',
         'entered', 'entry_type', 'entry_open_ratio', 'entry_ma5_distance',
         'entry_ma10_distance', 'entry_score',
         'exit_date', 'exit_reason', 'actual_pnl_pct', 'hold_days'])


def clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def main():
    os.makedirs(DATADIR, exist_ok=True)
    m = pd.read_csv(SRC, dtype={'entry_date': str, 'code': str, 'prev_date': str}, low_memory=False)
    m['entry_date'] = m['entry_date'].astype(str)
    print("base rows:", len(m))

    # join ENTRY/EXIT(只 2026-03~06 有)
    ent = pd.read_csv(os.path.join(HERE, "_entry_log.csv"), dtype={'entry_date': str, 'code': str})
    exi = pd.read_csv(os.path.join(HERE, "_exit_log.csv"), dtype={'entry_date': str, 'code': str})
    for d in (ent, exi):
        d['entry_date'] = d['entry_date'].astype(str)
        d['code'] = d['code'].astype(str)
    # 只保留 dragon_follow 作 entered(早盘候选买入);shadow_satellite 非候选池
    ent_df = ent[ent['entry_type'] == 'dragon_follow'].copy()
    m = m.merge(ent_df, on=['entry_date', 'code'], how='left')
    m = m.merge(exi, on=['entry_date', 'code'], how='left')
    if 'entered' not in m:
        m['entered'] = 0
    m['entered'] = m['entered'].fillna(0).astype(int)
    m['year'] = m['entry_date'].str[:4]
    m['cmonth'] = m['entry_date'].str[4:6]
    print("entered=1 rows:", int((m['entered'] == 1).sum()))

    # 完整性:中间空后面有值 = forward join bug
    bad = 0
    arr = m[DAYS].to_numpy()
    for row in arr:
        present = [not (x != x) for x in row]  # not NaN
        if any(present):
            last = max(i for i, p in enumerate(present) if p)
            if any(not present[i] for i in range(last)):
                bad += 1
    print("middle-gap rows (应=0):", bad)
    if bad:
        print("!! forward join bug,停下"); sys.exit(1)

    # 分片输出 per version。精简:省 None 键 + 显示精度取整(交付JSON仍全精度)。
    round2 = set(DAYS + ['max_ret', 'final_ret', 'ret3', 'open_ratio', 'actual_pnl_pct',
                         'entry_open_ratio', 'entry_ma5_distance', 'entry_ma10_distance'])
    for ver in sorted(m['score_mode'].unique()):
        sub = m[m['score_mode'] == ver]
        recs = []
        for row in sub.to_dict('records'):
            r = {}
            for k in KEEP:
                v = clean(row.get(k))
                if v is None:
                    continue                      # 省 None 键(非入场行省掉一堆 entry/exit 空键)
                if k in round2 and isinstance(v, float):
                    v = round(v, 2)
                elif k in ('dragon_score', 'close_to_high', 'auc_ratio') and isinstance(v, float):
                    v = round(v, 4)
                r[k] = v
            recs.append(r)
        js = ("window.POOL=window.POOL||{};window.POOL['%s']=%s;" %
              (ver, json.dumps(recs, ensure_ascii=False, separators=(',', ':'))))
        p = os.path.join(DATADIR, "pool_%s.js" % ver)
        io.open(p, 'w', encoding='utf-8').write(js)
        print("  %s: %d rows -> %s (%.1f MB)" % (ver, len(recs), os.path.basename(p), os.path.getsize(p) / 1e6))

    # meta.js
    cutoff = {}
    cpath = os.path.join(HERE, "_data_cutoff.txt")
    if os.path.exists(cpath):
        for ln in io.open(cpath, encoding='utf-8'):
            if '=' in ln:
                k, v = ln.strip().split('=', 1)
                cutoff[k] = v
    counts = {ver: int((m['score_mode'] == ver).sum()) for ver in sorted(m['score_mode'].unique())}
    meta = dict(
        generated_for="战车A龙头3 v1.4.0D_observer 候选池 2020–2026 (6.5年) forward 回看",
        versions=sorted(m['score_mode'].unique().tolist()),
        years=sorted(m['year'].unique().tolist()),
        cutoffs=dict(selection=cutoff.get('selection_cutoff', '20260625'),
                     forward=cutoff.get('forward_cutoff', '20260625'),
                     today_settled=cutoff.get('today_settled', 'True')),
        counts=counts,
        entered_window="2026-03~06(仅此段有聚宽实际交易日志;v3-default,只dragon_follow)",
        note="6.5年/多轮牛熊;forward版本无关(day1=t=0收盘);v3对聚宽精确吻合,v1/v2 code-faithful;中台warehouse后端,与QMT重叠期逐位验证",
    )
    io.open(os.path.join(DATADIR, "meta.js"), 'w', encoding='utf-8').write(
        "window.META=%s;" % json.dumps(meta, ensure_ascii=False))
    print("meta.js written | versions=%s years=%s counts=%s" % (meta['versions'], meta['years'], counts))

    # 整份 JSON 交付(全量,供其它消费)
    full = [{**{k: clean(r.get(k)) for k in KEEP if k in r}, 'score_mode': r['score_mode'],
             'year': r['year']} for r in m.to_dict('records')]
    io.open(os.path.join(HERE, "event_study_dragon_2020_2026.json"), 'w', encoding='utf-8').write(
        json.dumps(dict(meta=meta, rows=full), ensure_ascii=False))
    print("event_study_dragon_2020_2026.json written (%.1f MB)" %
          (os.path.getsize(os.path.join(HERE, "event_study_dragon_2020_2026.json")) / 1e6))

    build_summary(m)


def _stats(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if not len(s):
        return ('–', '–', '–', 0)
    return (round(float(s.mean()), 2), round(float(s.median()), 2),
            round(float((s > 0).mean() * 100), 1), int(len(s)))


def build_summary(m):
    L = []
    P = L.append
    P("# 候选池 2020–2026 (6.5年) forward 回看 summary(只报数)\n")
    P("> 6.5年/多轮牛熊/51033行(17011×v1/v2/v3)。中台warehouse后端,与QMT重叠期逐位验证。")
    P("> forward 版本无关(day1=t=0收盘)。entered 仅 2026-03~06 有(聚宽实际交易,v3-default,dragon_follow)。\n")
    P("## 各年 × tpl forward 对照(day5/day10/day20 均/中/胜/n)\n")
    for ver in sorted(m['score_mode'].unique()):
        P("### score_mode = %s\n" % ver)
        P("| 年 | tpl | day5 均/中/胜/n | day10 均/中/胜/n | day20 均/中/胜/n |")
        P("|---|---|---|---|---|")
        for yr in sorted(m['year'].unique()):
            sub = m[(m['score_mode'] == ver) & (m['year'] == yr)]
            for tpl in ['deep_water', 'trend_core']:
                st = sub[sub['tpl'] == tpl]
                d5, d10, d20 = _stats(st['day5']), _stats(st['day10']), _stats(st['day20'])
                P("| %s | %s | %s/%s/%s/%d | %s/%s/%s/%d | %s/%s/%s/%d |" %
                  (yr, tpl, d5[0], d5[1], d5[2], d5[3], d10[0], d10[1], d10[2], d10[3],
                   d20[0], d20[1], d20[2], d20[3]))
        P("")
    P("> ⚠️ 只报数。区分度是否真有效看各年一致性自行判断;不下结论。")
    io.open(os.path.join(HERE, "summary_2020_2026.md"), 'w', encoding='utf-8').write("\n".join(L))
    print("summary_2020_2026.md written")


if __name__ == '__main__':
    main()
