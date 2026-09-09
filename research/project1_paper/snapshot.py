# -*- coding: utf-8 -*-
"""Project1 Paper — 盘前快照构建(喂给 AI 的字段,spec §3.1,全部盘前可得)。

护栏2(关键):快照只含"每只候选票的历史表现 + 今日竞价"——这是合法选股信息。
严禁任何"当天开盘后"的字段进快照(当天分时由机械进场闸负责,AI 不看)。

字段与 spec §3.1 对照(本地可得子集,诚实标注缺失):
  ✅ 代码/名称/模板tpl/dragon_score/open_ratio(竞价高开幅度)
  ✅ 昨日:涨跌幅/是否涨停/成交额/量
  ✅ 近期:近10日涨停次数/连板数/3日涨幅/5日涨幅/10日涨幅/距20日高点
  ✅ 竞价:高开幅度/竞价额占昨日成交额比
  ❌ 未接(字段置null并在prompt声明):行业板块/题材概念标签/封单强度/换手率(需流通股本)/市值/新闻
"""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)

import pool_repro as PR   # noqa: E402

LIMIT_EPS = 1e-3


def _is_limit_up(close, prev_close):
    return close >= round(prev_close * 1.10, 2) - LIMIT_EPS


def build_snapshot(d8, pool_item, today_auc=None):
    """单票快照。pool_item = dragon_pool 输出 dict;today_auc=(px,vol手,amt元) 或 None(从缓存取)。"""
    code = pool_item['stock']
    p = PR.panel().get(code)
    if p is None:
        return None
    prior = p[p.index < d8]
    if len(prior) < 11:
        return None
    c = prior['close'].values
    amt = prior['amount'].values
    prev_close = float(c[-1])
    prev2_close = float(c[-2])
    # 近10日涨停次数 / 连板数
    lu_flags = [_is_limit_up(float(c[i]), float(c[i - 1])) for i in range(len(c) - 10, len(c))]
    consec = 0
    for f in reversed(lu_flags):
        if f:
            consec += 1
        else:
            break
    auc = today_auc if today_auc is not None else PR.get_auction(code, d8)
    auc_amt = float(auc[2]) if auc else None
    return dict(
        code=code, name=pool_item.get('name', ''), tpl=pool_item['tpl'],
        dragon_score=round(float(pool_item['dragon_score']), 4),
        # 昨日
        prev_ret_pct=round((prev_close / prev2_close - 1) * 100, 2),
        prev_is_limit_up=bool(_is_limit_up(prev_close, prev2_close)),
        prev_amount_yi=round(float(amt[-1]) / 1e8, 2),
        # 近期
        limit_up_cnt_10d=int(sum(lu_flags)),
        consec_limit_days=int(consec),
        ret3_pct=round((prev_close / float(c[-4]) - 1) * 100, 2),
        ret5_pct=round((prev_close / float(c[-6]) - 1) * 100, 2),
        ret10_pct=round((prev_close / float(c[-11]) - 1) * 100, 2),
        close_to_20d_high_pct=round(prev_close / float(prior['high'].iloc[-20:].max()) * 100, 1),
        # 今日竞价(9:25后可得)
        auction_open_ratio_pct=round(float(pool_item.get('open_ratio', 0)) * 100, 2),
        auction_amt_over_prev_amt_pct=(
            round(auc_amt / float(amt[-1]) * 100, 2) if (auc_amt and amt[-1] > 0) else None),
        # 未接字段(诚实置null)
        industry=None, concept_tags=None, seal_strength=None,
        turnover_pct=None, market_cap=None, news_brief=None,
    )


def build_snapshots(d8, pool, today_auc_map=None):
    out = []
    for it in pool:
        auc = (today_auc_map or {}).get(it['stock'])
        s = build_snapshot(d8, it, today_auc=auc)
        if s is not None:
            out.append(s)
    return out
