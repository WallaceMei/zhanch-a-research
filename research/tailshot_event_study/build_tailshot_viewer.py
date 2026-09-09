# -*- coding: utf-8 -*-
"""尾盘选股 V2 长样本 forward 动态回看表 — 数据底座 + HTML 壳一体构建。
参照 dragon_event_study 的动态加载模式(meta.js + pool.js + 薄壳 HTML,双击直开)。
数据源: 合并长样本 CSV(302 原 + 4/14~7/3 QMT/Tushare 补, 371 信号)。
"""
import io, os, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, 'viewer')
DATADIR = os.path.join(VIEWER, 'data')
SRC = r'C:\quant_platform\data\tailshot_backfill\outputs_full\tailshot_research_signals.csv'  # full-keep: 含尾盘失败候选

DAYS = ['ret_d%d_close' % i for i in range(1, 11)]
MHS  = ['max_high_d%d' % i for i in range(1, 11)]

def clean(v):
    if v is None: return None
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    return v

def r2(v, mul=100.0):
    v = clean(v)
    return None if v is None else round(v*mul, 2)

def main():
    os.makedirs(DATADIR, exist_ok=True)
    df = pd.read_csv(SRC, dtype={'signal_date': str, 'ts_code': str}, low_memory=False)
    df['signal_date'] = df['signal_date'].astype(str).str.replace('.0','',regex=False)
    print('rows:', len(df))

    # S_v3b 反推评分 (2026-07-03 研究, train 202508-202602 定方向, test 202603-07 验证过)
    # = 当日内 pct-rank 加权: +MA张口% -回踩天 -尾盘通过数 -当日涨跌%; 换算 0-100
    df['_ma_gap'] = (df['ma10'] - df['ma20']) / df['ma10']
    _r = lambda c: df.groupby('signal_date')[c].rank(pct=True).fillna(0.5)
    v3_raw = _r('_ma_gap') - _r('pullback_days') - _r('tail_support_pass_count') - _r('pct_chg')
    df['v3b'] = ((v3_raw + 3) / 4 * 100).round(1)   # raw ∈ [-3,1] → 0-100

    recs = []
    for row in df.to_dict('records'):
        sd = str(row['signal_date'])
        d = [r2(row.get(c)) for c in DAYS]          # D1-D10 收盘收益 %
        mh = [r2(row.get(c)) for c in MHS]           # D1-D10 区间最高 %
        avail = [i+1 for i,x in enumerate(d) if x is not None]
        days_available = len(avail)
        # 区间最大涨幅 = max(max_high_dN); 到顶第几日
        mh_valid = [(i+1,x) for i,x in enumerate(mh) if x is not None]
        max_ret = max((x for _,x in mh_valid), default=None)
        day_to_peak = max(mh_valid, key=lambda t:t[1])[0] if mh_valid else None
        # 末日收益 = 最后一个非空 ret
        finR = d[avail[-1]-1] if avail else None
        final_day = avail[-1] if avail else None
        def b(x):
            x = row.get(x)
            return 1 if (x is True or x==1 or str(x).lower()=='true') else 0
        rk2 = clean(row.get('rank_v2'))
        rec = {
            'signal_date': sd, 'rank': clean(row.get('rank')),
            'rk2': int(rk2) if rk2 is not None else None,
            'tok': 1 if clean(row.get('tail_ok')) == 1 else 0,
            'code': row.get('ts_code'), 'name': row.get('name'),
            'score': clean(row.get('score')), 'v3': clean(row.get('v3b')), 'env': row.get('env_group'),
            'pvr': r2(row.get('pred_vol_ratio'),1), 'ma10d': r2(row.get('ma10_dist_pct')),
            'luc': clean(row.get('limit_up_count_10d')), 'pbd': clean(row.get('pullback_days')),
            'tsp': clean(row.get('tail_support_pass_count')),
            'gap': r2(row.get('gap_t1')), 'og': row.get('open_group'), 'eg': row.get('exit_group'),
            'noh': r2(row.get('next_open_to_high_ret')), 'noc': r2(row.get('next_open_to_close_ret')),
            'mh1': mh[0],  # 次日最高%
            'h15': b('hit_tp_15'), 'h20': b('hit_tp_20'), 'hsl': b('hit_sl_20'),
            'maxR': max_ret, 'day_to_peak': day_to_peak, 'finR': finR, 'final_day': final_day,
            'days_available': days_available,
            'window_incomplete': days_available < 10,
        }
        for i in range(10): rec['d%d'%(i+1)] = d[i]
        recs.append(rec)

    # meta
    years = sorted({r['signal_date'][:4] for r in recs})
    sd_all = [r['signal_date'] for r in recs]
    n = len(recs)
    hit15 = sum(r['h15'] for r in recs)
    n_pass = sum(1 for r in recs if r['tok'] == 1)
    h15_pass = sum(r['h15'] for r in recs if r['tok'] == 1)
    meta = {
        'generated_for': '尾盘选股 V2 · 长样本 forward 回看表(全候选版)',
        'range': f'{min(sd_all)} ~ {max(sd_all)}',
        'years': years,
        'count': n,
        'count_pass': n_pass,
        'hit15_overall': round(100*hit15/n, 1),
        'hit15_pass': round(100*h15_pass/max(n_pass,1), 1),
        'cutoff': {'signal': max(sd_all), 'note': 'full-keep 全期重跑: 前置筛选全候选(含尾盘未过)都算分+forward; 日线Tushare/尾盘1m QMT'},
        'note': 'D1=次日,dN=第N交易日收盘累计收益%(次日开盘买入基准); hit15=次日"开盘→盘中最高"≥+1.5%(命名坑:15指1.5%), hit20≥+2.0%, SL=次日"开盘→最低"≤-2.0%; 未到期不补0',
    }
    io.open(os.path.join(DATADIR,'meta.js'),'w',encoding='utf-8').write(
        'window.META='+json.dumps(meta,ensure_ascii=False)+';')
    # pool(省 None 键)
    slim = []
    for r in recs:
        slim.append({k:v for k,v in r.items() if v is not None})
    io.open(os.path.join(DATADIR,'pool.js'),'w',encoding='utf-8').write(
        'window.POOL='+json.dumps(slim,ensure_ascii=False)+';')
    print('meta.js + pool.js written; hit15 overall =', meta['hit15_overall'], '%')

if __name__ == '__main__':
    main()
