# 因子审判法庭 V2 — Gate2/3/4 总结

> 建后三关 + 验机制。final_verdict 仅允许 gate1_fail/gate2_fail/gate3_redundant/gate_pass_but_decaying/gate_all_pass_candidate;**严禁 robust_alpha**。不碰 2026。
> 主口径:universal_clean_mask + fwd_return_10d_cs_demean;HAC lag=10。环境 .venv_court。

## 机制自检(三关)
- Gate2 selfcheck: pass(20 噪声 t~N(0,1),BH-FDR 通过 0 个)
- Gate3 selfcheck: pass(A~B 同簇=True,A≠C 不同簇=True,A/D 强负相关标互补=True)
- Gate4 selfcheck: pass(4/4 用例,stable/warning/decaying/reversal 全对)

## 漏斗
```
31 受审因子(主口径)
-> Gate1 pass: 27
-> Gate2 BH-FDR n31 pass: 27
-> Gate2 BH-FDR n194 敏感性 pass: 27
-> Gate3 独立簇数: 8 (代表因子 8)
-> Gate4 代表中 stable: 4 / warning: 3 / decaying: 1
-> gate_all_pass_candidate: 7
-> gate_pass_but_decaying: 1
```

## final_verdict 分布
- gate3_redundant: 19
- gate_all_pass_candidate: 7
- gate1_fail: 4
- gate_pass_but_decaying: 1

## Gate2 砍了什么
FDR(n=31)后不显著被砍 0 个: 无
n=194 敏感性下 BH-FDR 通过 27 个(压力测试,非主判据)。

## Gate3 簇(代表 + 语义标签)
- 簇0 [趋势/动量] 大小14 代表=return_20d_rank;成员:bb_position_rank|intraday_return_rank|ma_ratio_10d_rank|ma_ratio_20d_rank|ma_ratio_5d_rank|ma_ratio_60d_rank|price_position_20d_rank|price_position_60d_rank|return_10d_rank|return_20d_rank|return_5d_rank|return_60d_rank|rsi_14_rank|up_streak_rank
- 簇1 [波动率] 大小4 代表=atr_ratio_rank;成员:atr_ratio_rank|volatility_10d_rank|volatility_20d_rank|volatility_5d_rank
- 簇2 [波动率(单因子簇)] 大小1 代表=atr_14d_rank;成员:atr_14d_rank
- 簇3 [量能] 大小4 代表=vol_ratio_20d_rank;成员:amount_ratio_5d_rank|vol_ratio_10d_rank|vol_ratio_20d_rank|vol_ratio_5d_rank
- 簇4 [量能(单因子簇)] 大小1 代表=vol_price_corr_10d_rank;成员:vol_price_corr_10d_rank
- 簇5 [K线形态(单因子簇)] 大小1 代表=upper_shadow_ratio_rank;成员:upper_shadow_ratio_rank
- 簇6 [K线形态(单因子簇)] 大小1 代表=lower_shadow_ratio_rank;成员:lower_shadow_ratio_rank
- 簇7 [趋势/动量(单因子簇)] 大小1 代表=overnight_return_rank;成员:overnight_return_rank

## Gate3 强负相关对(potential_complement,不判冗余)
- 无 corr<-0.7 的对。
> 强负相关不判冗余,后续可作潜在互补/对冲信号观察。

## Gate4 衰减
- return_20d_rank: 2023=0.0507 2024=0.0918 2025=0.0795 ratio=1.57 slope=0.01441 -> stable
- atr_ratio_rank: 2023=0.0916 2024=0.0845 2025=0.0593 ratio=0.65 slope=-0.01615 -> decay_warning
- atr_14d_rank: 2023=0.1152 2024=0.0609 2025=0.0572 ratio=0.50 slope=-0.02897 -> decaying
- vol_ratio_20d_rank: 2023=0.0349 2024=0.0475 2025=0.0400 ratio=1.15 slope=0.00256 -> stable
- vol_price_corr_10d_rank: 2023=0.0406 2024=0.0581 2025=0.0420 ratio=1.03 slope=0.00069 -> stable
- upper_shadow_ratio_rank: 2023=0.0615 2024=0.0486 2025=0.0342 ratio=0.56 slope=-0.01367 -> decay_warning
- lower_shadow_ratio_rank: 2023=0.0520 2024=0.0303 2025=0.0302 ratio=0.58 slope=-0.01086 -> decay_warning
- overnight_return_rank: 2023=0.0295 2024=0.0177 2025=0.0271 ratio=0.92 slope=-0.00123 -> stable

## 修正留档(给 V3)
- **Gate4 衰减规则原 spec 有自相矛盾**:§6.5 的 `decay_slope_3y<0 -> decay_warning` 与§8.3 的 stable 用例 [0.03,0.031,0.029](slope=-0.0005)打架——该用例斜率为负会被判 warning,但自检要求 stable。经 Gate4 自检发现,按 Wallace 决定(选项B)**去掉斜率判定,decay_warning 只用 `yearly_ic_2025 < yearly_ic_2023*0.7`**;decay_slope_3y 仍照算并输出到 csv 作参考,不再做判定。理由:真因子年度 IC 必有微小波动,'斜率<0就预警'过敏感、会预警满天飞、失去区分力。
- **慢因子提醒(沿用 V1)**:60d 类因子(ma_ratio_60d/return_60d/price_position_60d)的 IC 序列自相关可能超 10 日,HAC lag=10 下 t/IC 可能偏高。
- Gate3 去冗余基于 IC 序列相关 = **预测行为去冗余**,不等同于持仓重合度去冗余(本版未算因子值面板相关)。

## 重要限制(必读)
- 本版是建后三关 + 验机制;31 个是 features 通用技术因子**试跑材料**,非产品级 alpha。
- 四关全过者仅 **gate_all_pass_candidate**:只表示在 V1 Gate1 + V2 Gate2/3/4 机制口径下暂时通过;**不是 robust_alpha、不能实盘、不是新发现 alpha**。
- OOS 纯度 unknown(教科书因子大概率被既往研究见过全段);未碰 2026;未做 DSR、未做组合回测/成本敏感性。
