# -*- coding: utf-8 -*-
"""Project1 Paper — 可插拔选股决策器(spec v0.1 §2)。

三组对照(Step1 盘后结算版),唯一变量 = 选股方式:
  ai_placeholder : 占位AI —— 按 dragon_score 选 top3。
                   ★仅作管线占位(dragon_score v3 已知样本外无alpha),
                   Step4 换成 MiniMax 真AI;本组结果不作"AI价值"判读。
  random3        : 随机3只 —— 种子=交易日期(固定可复现、每日不同)。
  all_in         : 机械全进 —— top12 全部进监测池(过闸票按25%上限买到满75%)。

接口统一:decide(d8, pool) -> list[dict(code, name, rank, reason)]
  pool = pool_repro.dragon_pool() 输出(按 dragon_score 降序的 top12)。
  返回 = 进入"监测池"的票(是否成交由共用进场闸决定,不在决策器内)。
"""
import random

N_PICK = 3   # spec §9.1: AI/随机 各选3只(呼应实盘 MAX_POS=3)


def decide_ai_placeholder(d8, pool):
    """占位AI:dragon_score top3(pool 已按分降序)。"""
    picks = []
    for i, p in enumerate(pool[:N_PICK]):
        picks.append(dict(code=p['stock'], name=p.get('name', ''), rank=i + 1,
                          reason='placeholder_score_top%d' % (i + 1)))
    return picks


def decide_random3(d8, pool):
    """随机3只:seed=int(d8) → 固定可复现、每日不同。"""
    rng = random.Random(int(d8))
    n = min(N_PICK, len(pool))
    chosen = rng.sample(range(len(pool)), n) if len(pool) else []
    picks = []
    for j, idx in enumerate(sorted(chosen)):
        p = pool[idx]
        picks.append(dict(code=p['stock'], name=p.get('name', ''), rank=j + 1,
                          reason='random_seed_%s' % d8))
    return picks


def decide_all_in(d8, pool):
    """机械全进:top12 全部进监测池(买入时按25%/slot上限截断,见组合层)。"""
    return [dict(code=p['stock'], name=p.get('name', ''), rank=i + 1, reason='all_in')
            for i, p in enumerate(pool)]


DECIDERS = dict(
    ai_placeholder=decide_ai_placeholder,
    random3=decide_random3,
    all_in=decide_all_in,
)
