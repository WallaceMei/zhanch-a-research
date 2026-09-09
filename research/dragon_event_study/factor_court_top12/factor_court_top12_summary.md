# 战车A 第二步·①验因子 — Top12 候选池内单因子四关法庭

> **conditioned_on_dragon_top12(条件命题)**:本报告只回答「在 dragon Top12 最终幸存者池**内部**,哪些单因子还能区分赢家(big10)」。
> **不是**全市场 alpha、**不是**大预筛池选牛股、**不是**多因子评分、**不是** robust_alpha。只单因子审判,不组合/不调权重/不拼新score/不改 dragon_score。**2026 完全未碰**(holdout)。

- 数据底座 event_study_dragon_2020_2026.csv;Top12池=v1/v2/v3并集去重 unique(date,code)。
- 切分:IS=2020-2023(14166) / OOS=2024-2025(7178) / **2026 holdout 未进任何计算**。
- 主判据=is_big_meat_10(≥10%,池内逐日Spearman区分力,HAC lag=20);辅助=is_super_meat_20;连续周期 T3/T5/T10 Rank IC 作周期对照。
- 受审因子(族=8):open_ratio, auc_ratio, auc_amount, close_to_high, ret3, avg_money, close_to_20d_high, avg_range;benchmark=dragon_score(v3,仅对照)。

## 1) 四关机制自检(每关)
- **Gate1 打乱 big10 归零(最关键)**:8 因子逐个打乱标签后,null IC 均值≈0、null HAC t 退回 N(0,1)(std≈1、显著率≈5%)。逐因子见 selfcheck_gate1_shuffle.csv。
  - open_ratio         null_ic=0.0004 null_t_std=1.01 sig%=5% → 归零✓
  - auc_ratio          null_ic=-0.0006 null_t_std=1.02 sig%=6% → 归零✓
  - auc_amount         null_ic=0.0008 null_t_std=0.95 sig%=5% → 归零✓
  - close_to_high      null_ic=0.0014 null_t_std=0.94 sig%=6% → 归零✓
  - ret3               null_ic=-0.0004 null_t_std=1.03 sig%=5% → 归零✓
  - avg_money          null_ic=0.0022 null_t_std=0.86 sig%=0% → 归零✓
  - close_to_20d_high  null_ic=0.0003 null_t_std=1.02 sig%=6% → 归零✓
  - avg_range          null_ic=-0.0006 null_t_std=1.03 sig%=5% → 归零✓
- Gate2 噪声 FDR 自检:20 个 N(0,1) 噪声,BH-FDR 通过 0 个(应≈0)→ ✓
- Gate3 合成相关自检:A~B 同簇、A≠C、A/D 强负相关标互补 → ✓
- Gate4 人造衰减自检:stable/warning/decaying/reversal 4/4 判对 → ✓

## 2) 每因子对 big10 结果(IS 锁方向,OOS 验不翻向)
| 因子 | IS IC | IS t | IS p | OOS IC | OOS t | OOS翻向 | Gate1 |
|---|---|---|---|---|---|---|---|
| open_ratio | +0.0174 | +1.46 | 0.145 | +0.0394 | +2.28 | 否 | fail |
| auc_ratio | +0.0164 | +1.43 | 0.154 | -0.0034 | -0.18 | 是 | fail |
| auc_amount | -0.0142 | -1.30 | 0.194 | -0.0234 | -1.39 | 否 | fail |
| close_to_high | -0.1041 | -8.82 | 0.000 | -0.0655 | -3.95 | 否 | pass |
| ret3 | +0.0074 | +0.75 | 0.452 | +0.0144 | +1.06 | 否 | fail |
| avg_money | -0.0130 | -0.86 | 0.388 | -0.0238 | -0.89 | 否 | fail |
| close_to_20d_high | -0.0634 | -4.77 | 0.000 | -0.0541 | -3.95 | 否 | pass |
| avg_range | +0.1422 | +8.68 | 0.000 | +0.0800 | +3.43 | 否 | pass |
| **dragon_score(benchmark,v3)** | +0.0926 | +6.30 | 0.000 | +0.0771 | +4.12 | — | benchmark |

## 3) 每因子 super20 对照(≥20% 大肉能力)
| 因子 | super20 IS IC | IS t | IS p | OOS翻向 | super20_pass |
|---|---|---|---|---|---|
| open_ratio | +0.0218 | +1.85 | 0.064 | 否 | fail |
| auc_ratio | +0.0438 | +3.38 | 0.001 | 否 | pass |
| auc_amount | -0.0059 | -0.48 | 0.634 | 是 | fail |
| close_to_high | -0.1069 | -9.35 | 0.000 | 否 | pass |
| ret3 | +0.0261 | +2.65 | 0.008 | 否 | pass |
| avg_money | -0.0406 | -2.28 | 0.022 | 否 | pass |
| close_to_20d_high | -0.0652 | -4.89 | 0.000 | 否 | pass |
| avg_range | +0.1698 | +11.32 | 0.000 | 否 | pass |

## 4) 连续前向收益 Rank IC(IS,看哪个周期最强;big10为主判据)
| 因子 | T3 IC(t) | T5 IC(t) | T10 IC(t) |
|---|---|---|---|
| open_ratio | -0.0316(-2.9) | -0.0287(-2.7) | -0.0343(-3.2) |
| auc_ratio | -0.0379(-3.7) | -0.0460(-4.7) | -0.0487(-4.4) |
| auc_amount | +0.0099(+1.0) | -0.0018(-0.2) | -0.0091(-0.8) |
| close_to_high | -0.0099(-0.9) | +0.0086(+0.7) | +0.0225(+1.8) |
| ret3 | -0.0342(-2.9) | -0.0442(-3.7) | -0.0429(-3.5) |
| avg_money | +0.0531(+4.4) | +0.0503(+4.1) | +0.0480(+3.4) |
| close_to_20d_high | -0.0113(-1.0) | -0.0062(-0.5) | -0.0037(-0.3) |
| avg_range | -0.0237(-1.8) | -0.0447(-3.2) | -0.0611(-3.6) |
> 注:连续收益 IC 与 big10(触及)可能方向相反——高动量票易盘中触+10%但持有到收盘回落。big10 为主判据。

## 5) ★牛熊年份分层(big10 池内区分力,逐年;2026未计)
| 因子 | 2020 | 2021 | **2022熊** | **2023熊** | 2024 | 2025 | IS期 | OOS期 | 衰减 |
|---|---|---|---|---|---|---|---|---|---|
| open_ratio | +0.024 | +0.005 | **+0.036** | **+0.005** | +0.065 | +0.018 | +0.018 | +0.042 | stable |
| auc_ratio | -0.025 | +0.016 | **+0.048** | **+0.025** | +0.028 | -0.030 | +0.016 | -0.001 | decaying |
| auc_amount | -0.006 | -0.053 | **-0.033** | **+0.037** | -0.006 | -0.038 | -0.014 | -0.022 | stable |
| close_to_high | -0.048 | -0.090 | **-0.122** | **-0.154** | -0.087 | -0.048 | -0.104 | -0.067 | decay_warning |
| ret3 | -0.008 | +0.017 | **+0.013** | **+0.006** | +0.004 | +0.023 | +0.007 | +0.013 | stable |
| avg_money | +0.030 | -0.058 | **-0.043** | **+0.022** | -0.027 | -0.021 | -0.012 | -0.024 | stable |
| close_to_20d_high | -0.054 | -0.044 | **-0.073** | **-0.083** | -0.057 | -0.052 | -0.064 | -0.054 | stable |
| avg_range | +0.074 | +0.143 | **+0.161** | **+0.187** | +0.089 | +0.073 | +0.141 | +0.081 | decay_warning |
> 核心问题:因子在 2022/2023 熊市还成立吗?看 bear 两列符号是否与 IS 方向一致、是否归零/反向。

## 6) Gate1-4 漏斗
```
受审单因子(族): 8
-> Gate1 big10 通过(IS显著+OOS不翻向): 3
-> Gate2 BH-FDR(族=8)通过: 3
-> Gate3 去冗余后独立信号(代表): 3
-> Gate4 代表中 decaying: 0
-> gate_all_pass_candidate: 3
```

## 7) 去冗余后剩几个独立信号
- 独立簇代表(3 个):close_to_high, close_to_20d_high, avg_range
- 无 corr<-0.7 的强负相关对。

## 8) dragon_score benchmark 对照
- dragon_score(v3) big10 IS IC=+0.0926 t=+6.30 / OOS IC=+0.0771 t=+4.12。
- ★它是 benchmark(在自己选出的 Top12 内的自指标),**不是主候选**,不进 FDR 族、不参与去冗余。仅供单因子强弱参照。

## 9) final_verdict 分布
- super20_specific_candidate: 3 (auc_ratio, ret3, avg_money)
- gate_all_pass_candidate: 3 (close_to_high, close_to_20d_high, avg_range)
- gate1_fail: 2 (open_ratio, auc_amount)

## 10) ★声明(必读)
- 本报告是 **Top12 条件池内单因子验证**,标签 **conditioned_on_dragon_top12**。
- **不是**全市场 alpha、**不是**从大预筛池选牛股、**不是**多因子评分、**不是** robust_alpha。
- 只单因子审判:未组合、未调权重、未拼新 score、未改 dragon_score。
- **2026 全程未碰**(Final holdout):不用于调规则/选因子/任何 Gate。
- gate_all_pass_candidate 仅表示「在本四关口径下,该单因子在 Top12 内对 big10 仍有显著且未翻向、非冗余、未衰减的区分力」,**不等于可实盘、不等于新 alpha**。

## 11) 本轮结论·诚实评估（必读）

本轮四关法庭的主要成果是验证机制，而不是发现可直接实盘的新 alpha。虽然 close_to_high、close_to_20d_high、avg_range 在 Top12 条件池内通过 big10 四关审判，但需要谨慎解释：

1. avg_range 对 big10 的区分力很可能包含标签机械关系。big10 定义为未来窗口内"触及 ≥10%"，而高振幅股票天然更容易触及阈值；同时 avg_range 对连续收盘收益 T10 IC 为负，说明它更像"触及概率"信号，不等于可交易持有收益信号。

2. close_to_high、close_to_20d_high 与 dragon 原有选股/预筛逻辑存在自指成分。本报告是在 conditioned_on_dragon_top12 幸存者池内验证，不能解释为独立全市场 alpha，也不能解释为新发现因子。

3. auc_ratio、ret3、avg_money 只标为 super20_specific_candidate，不进入 big10 主候选。super20 表现仅作为大肉能力对照，不参与主 verdict。

4. 因此，本轮结论应定义为：四关法庭机制有效，Top12 内单因子审判完成；但在现有 8 个因子中，未发现干净、非自指、且可交易性明确的新单因子 alpha。下一步不应直接进入多因子加权调参，而应先扩展到更大的预筛池或改用可交易收益标签复核。
