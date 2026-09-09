# 战车A 第二步·①验因子 第二轮 — 可交易持有收益(hold_T5)四关法庭

> **conditioned_on_dragon_top12**;主判据=**hold_T5(可交易持有5天收益)**:买 entry(T) open、卖 T+5 close(底座 day6),持5天、**T+1合法**(排除 day1 的0天持仓);辅 hold_T3=day4/hold_T10=day11。
> 本轮目的:用可交易收益**复核 big10「触及」标签的波动率假阳性**。**不是**全市场 alpha、**不是**多因子评分、**不是** robust_alpha;只单因子;**2026 全程未碰**。
- 切分:IS=2020-2023(14166) / OOS=2024-2025(7178) / 2026 holdout 未进。
- 受审 8 因子(族=8):open_ratio, auc_ratio, auc_amount, close_to_high, ret3, avg_money, close_to_20d_high, avg_range;benchmark=dragon_score(v3,仅对照)。

## ★1) 核心:big10(触及) vs hold_T5(可交易) IC 对照 —— 照出假阳性
| 因子 | big10 IS IC(t) | hold_T5 IS IC(t) | hold_T5 OOS IC(t) | 标签诊断 |
|---|---|---|---|---|
| open_ratio | +0.0174(+1.5) | -0.0278(-2.5) | -0.0417(-2.7) | tradable_only_newdir |
| auc_ratio | +0.0164(+1.4) | -0.0444(-4.5) | -0.0790(-5.0) | tradable_only_newdir |
| auc_amount | -0.0142(-1.3) | -0.0049(-0.5) | -0.0364(-2.4) | neither |
| close_to_high | -0.1041(-8.8) | +0.0162(+1.3) | +0.0368(+2.0) | touch_only_weakened |
| ret3 | +0.0074(+0.8) | -0.0496(-3.9) | -0.0405(-2.5) | tradable_only_newdir |
| avg_money | -0.0130(-0.9) | +0.0535(+4.3) | +0.0448(+2.5) | tradable_only_newdir |
| close_to_20d_high | -0.0634(-4.8) | -0.0085(-0.7) | +0.0202(+1.1) | touch_only_weakened |
| avg_range | +0.1422(+8.7) | -0.0482(-3.4) | -0.1028(-4.4) | touch_false_positive_FLIP |
| **dragon_score(bench,v3)** | +0.0926(+6.3) | -0.0392(-3.0) | -0.0600(-3.3) | benchmark |

诊断口径:`touch_false_positive_FLIP`=big10显著但hold_T5显著反向(触及假阳性);`touch_only_weakened`=big10显著但hold_T5不显著(触及虚高);`tradable_signal`=hold_T5显著且OOS不翻向(且与big10同向,真信号);`tradable_only`=hold_T5有效但big10下不显著;`neither`=两标签都无效。

## 2) hold_T5 四关结果(IS锁方向,OOS验不翻向)
| 因子 | IS IC | IS t | IS p | OOS IC | OOS t | OOS翻向 | Gate1 | Gate2 | Gate3代表 | 衰减 | final |
|---|---|---|---|---|---|---|---|---|---|---|---|
| open_ratio | -0.0278 | -2.54 | 0.011 | -0.0417 | -2.75 | 否 | pass | pass | 是 | stable | gate_all_pass_candidate |
| auc_ratio | -0.0444 | -4.45 | 0.000 | -0.0790 | -5.03 | 否 | pass | pass | 是 | stable | gate_all_pass_candidate |
| auc_amount | -0.0049 | -0.48 | 0.631 | -0.0364 | -2.35 | 否 | fail | - | - | stable | gate1_fail |
| close_to_high | +0.0162 | +1.30 | 0.193 | +0.0368 | +1.99 | 否 | fail | - | - | stable | gate1_fail |
| ret3 | -0.0496 | -3.93 | 0.000 | -0.0405 | -2.55 | 否 | pass | pass | 是 | stable | gate_all_pass_candidate |
| avg_money | +0.0535 | +4.25 | 0.000 | +0.0448 | +2.55 | 否 | pass | pass | 是 | stable | gate_all_pass_candidate |
| close_to_20d_high | -0.0085 | -0.68 | 0.499 | +0.0202 | +1.06 | 是 | fail | - | - | decaying | gate1_fail |
| avg_range | -0.0482 | -3.35 | 0.001 | -0.1028 | -4.45 | 否 | pass | pass | 是 | stable | gate_all_pass_candidate |

## 3) 周期对照(IS Rank IC):hold_T3 / hold_T5 / hold_T10
| 因子 | T3 IC(t) | **T5 IC(t)主** | T10 IC(t) |
|---|---|---|---|
| open_ratio | -0.0351(-3.2) | **-0.0278(-2.5)** | -0.0328(-3.1) |
| auc_ratio | -0.0368(-3.7) | **-0.0444(-4.5)** | -0.0497(-4.5) |
| auc_amount | +0.0068(+0.7) | **-0.0049(-0.5)** | -0.0107(-1.0) |
| close_to_high | +0.0122(+1.0) | **+0.0162(+1.3)** | +0.0160(+1.3) |
| ret3 | -0.0452(-3.9) | **-0.0496(-3.9)** | -0.0395(-3.4) |
| avg_money | +0.0516(+4.3) | **+0.0535(+4.3)** | +0.0448(+3.3) |
| close_to_20d_high | +0.0015(+0.1) | **-0.0085(-0.7)** | -0.0022(-0.2) |
| avg_range | -0.0380(-2.8) | **-0.0482(-3.4)** | -0.0590(-3.3) |

## 4) dragon_score benchmark 在 hold_T5 下还强吗
- big10 下:IS IC=+0.0926(t+6.3) —— 第一轮很强。
- **hold_T5(可交易)下:IS IC=-0.0392(t-3.0) / OOS IC=-0.0600(t-3.3)**。
- 解读见结论:若 big10 强而 hold_T5 弱/反向,提示 dragon_score 可能优化在「触及」靶子上,而非可交易收益。

## 5) 牛熊年份分层(hold_T5 池内 Rank IC,逐年;2026未计)
| 因子 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | IS期 | OOS期 | 衰减 |
|---|---|---|---|---|---|---|---|---|---|
| open_ratio | -0.033 | -0.031 | **+0.007** | **-0.054** | -0.057 | -0.028 | -0.028 | -0.043 | stable |
| auc_ratio | -0.044 | -0.015 | **-0.036** | **-0.083** | -0.084 | -0.075 | -0.045 | -0.079 | stable |
| auc_amount | -0.002 | -0.010 | **-0.011** | **+0.004** | -0.038 | -0.035 | -0.005 | -0.036 | stable |
| close_to_high | -0.003 | +0.012 | **+0.020** | **+0.035** | +0.035 | +0.038 | +0.016 | +0.037 | stable |
| ret3 | -0.048 | -0.009 | **-0.092** | **-0.049** | -0.050 | -0.032 | -0.050 | -0.041 | stable |
| avg_money | +0.062 | +0.008 | **+0.054** | **+0.091** | +0.060 | +0.032 | +0.054 | +0.046 | stable |
| close_to_20d_high | -0.011 | +0.008 | **-0.038** | **+0.006** | +0.045 | -0.001 | -0.009 | +0.022 | decaying |
| avg_range | -0.068 | +0.015 | **-0.068** | **-0.075** | -0.136 | -0.074 | -0.049 | -0.105 | stable |

## 6) Gate1-4 漏斗 + 打乱归零自检
```
受审单因子(族): 8
-> Gate1 hold_T5 通过(IS显著+OOS不翻向): 5
-> Gate2 BH-FDR(族=8): 5
-> Gate3 去冗余独立信号: 5
-> Gate4 代表中 decaying: 0
-> gate_all_pass_candidate: 5
```
- 打乱 hold_T5 归零自检(每因子):open_ratio null_ic=0.0009 t_std=0.93 ✓; auc_ratio null_ic=-0.0004 t_std=0.94 ✓; auc_amount null_ic=0.0007 t_std=0.94 ✓; close_to_high null_ic=0.0014 t_std=0.97 ✓; ret3 null_ic=0.0000 t_std=0.94 ✓; avg_money null_ic=0.0014 t_std=0.81 ✓; close_to_20d_high null_ic=0.0001 t_std=0.90 ✓; avg_range null_ic=-0.0003 t_std=0.96 ✓
- Gate2噪声FDR(过0/20)=✓;Gate3合成聚类=✓;Gate4人造衰减=✓。
- 独立簇代表:open_ratio, auc_ratio, ret3, avg_money, avg_range。

## 7) final_verdict 分布
- gate_all_pass_candidate: 5 (open_ratio, auc_ratio, ret3, avg_money, avg_range)
- gate1_fail: 3 (auc_amount, close_to_high, close_to_20d_high)

## 8) ★声明(必读)
- 本报告 **conditioned_on_dragon_top12**,主标签=**可交易持有收益 hold_T5**(买T open卖T+5 close、排除day1、T+1合法)。
- **不是**全市场 alpha、**不是**多因子评分、**不是** robust_alpha;只单因子审判,未组合/未调权重/未改 dragon_score。
- **2026 全程未碰**(Final holdout)。big10/super20 仅作触及对照,不参与本轮 verdict。
- 本轮目的=校正牛股定义(触及→可交易收益),照出波动率假阳性;不下实盘结论。

## 9) ★本轮核心诊断·结论存证(重大发现)

**1. dragon_score 优化错靶子(核心发现)**
- dragon_score 在 big10(触及)下 IS IC=+0.093(t+6.3)很强,但在 hold_T5(可交易持有5天)下 IS IC=−0.039(t−3.0)/OOS IC=−0.060(t−3.3)**显著为负**。
- 数据层面:在它自己的 Top12 池里,**dragon_score 分越高、持有5天可交易收益越差**。
- 它对齐的是"触及≥10%"靶子,**不是**可交易持有收益。
- ★这可能是 dragon_score 当年 IS +361% / OOS −5.38% 崩塌的根因之一:**从根上优化了错误目标**(选"会蹦到高点的票"而非"持有能赚钱的票")。

**2. 第一轮 big10 候选全军覆没**
- avg_range(翻向)/ close_to_high(缩到不显著)/ close_to_20d_high(缩到不显著)在可交易收益下**没有一个是真信号**。
- 证实"触及"定义骗了第一轮,**避免了拿假因子进多因子评分、重造一个 dragon_score**。

**3. ★警示(必须挂,防误读)**
- hold_T5 下显著的 5 个因子方向**大多为负**,这是"dragon_score 在这些因子上加权方向用反了"的**诊断**,**不是**"新发现的可交易 alpha"。
- 全在 **conditioned_on_dragon_top12 幸存者池内**,不是全市场 alpha,**未考虑交易成本/冲击**,**不能**直接得出"反着 dragon_score 做就能赚"的结论。

**4. 方法论教训**
- 牛股定义**必须用可交易持有收益,不能用"触及"**——触及会被波动率钻空子,且可能让整个策略优化错靶子(dragon_score 就是教训)。

> 以上为结论存证。不下实盘结论、未碰 2026、未进多因子评分。
