# 打板事件模块 A1b — 125 因子四关审判 Summary

> 生成时间 2026-06-24。环境 `.venv_court`。**本报告为数据汇总,不下最终结论。**
> 主口径固定:`event_pool_all` + T+3 + HAC(lag=horizon) + 方向锁定。脚本 `a1b_run.py`,落盘 8 个 CSV + 本文件。

---

## 0. 一句话现状
125 个 can_calculate 因子跑完四关 + 四关自检(全 PASS)。漏斗:**125 → Gate1 过 59 → Gate2(BH-FDR n=125)过 59 → Gate3 去冗余后剩 9 个独立簇 → Gate4 全部非 decaying → 9 个 `gate_all_pass_candidate`(其中 6 个带 decay_warning)**。**这是"通过四关筛选的候选",不是 robust_alpha、不是实盘结论。**

---

## 1. 因子池与字段口径

- **can_calculate = 125 / 194**(field_unavailable 69,leakage_suspected 0)。识别规则:`fields_used ⊆ AVAILABLE` 且非空 且公式不含未来函数(fwd_return/_t1close/_t3close/_t5close 等)。
- **seal_dependent = 107 / 125**(自动识别:required_fields 含 `seal_strength/seal_ratio/seal_minutes/open_times/limit_turnover` 任一即判 seal;以审计为准,未硬写 147)。含 ts_ 的 88 个。
- **seal 因子 IC 限 sealed 子集**:seal 类因子算 IC 时样本限 `in_limit_list_d=True 且 sealed_limit=True`。`failed_board/near_limit` 行 seal 字段为 NaN,**不进 IC、不填 0、不 ffill**;过滤后按池阈值重新检查样本数(不用过滤前样本数冒充)。
- **ts_ 算子两类口径(选 A,已实证对齐)**:
  - **K线类**(return_3d/rsi_14/retail_line/价量等有稠密日序的):在 features 全市场**稠密日线**上算,`ts_shift=上一交易日`、`ts_zscore=滚动窗口`。实证:return_3d 事件行 000001.SZ 2024-02-21 面板值=稠密上一交易日值(一致)。
  - **seal/lhb 事件类**:按**事件序列**(该股上一次涨停/上榜行)算。实证:open_times 事件行 2024-10-08 面板值=该股上一事件行(2024-02-21,隔 230 天)原值,证明按事件序列非日历。
  - 面板 board_event_panel_full(48 列)原生含 8 个 DENSE_FIELDS 的**事件日值**(5 K线类 retail_line/retail_line_change/vol_vs_prev/intraday_range/kdj_j + 3 市场级 daily_total_limits/market_max_board/first_board_ratio);非 ts_ 用法用面板原生值,只从稠密日线补 panel 没有的 6 个 K线字段(return_3d/rsi_14/bb_position/up_streak/vol_ratio_5d/price_position_60d)。

---

## 2. 四关漏斗

| 阶段 | 结果 |
|---|---|
| can_calculate | **125** |
| Gate1 过(主口径 event_pool_all/T3,HAC t>3 且有效IC日≥120) | **59**(fail 66:insufficient_coverage 51 + hac_t≤3 15) |
| Gate2 过(BH-FDR 校正族=125) | **59**(全部 Gate1 过关者均通过 FDR) |
| Gate2 敏感性 n=194 | 59(同 n=125,不敏感) |
| Gate2 Bonferroni 对照(更严) | n=125: 57 / n=194: 57 |
| Gate3 去冗余(IC序列 corr>0.7 union-find 聚类) | 59 → **9 个独立簇**(代表保留 9,冗余 50) |
| Gate3 负相关互补对(corr<-0.7) | **0 对** |
| Gate4 半年度衰减(9 代表) | decay_warning 6 + stable 3,**decaying 0、insufficient_segment_data 0** |
| **final_verdict** | **gate1_fail 66 / gate3_redundant 50 / gate_all_pass_candidate 9** |

> **关键:Gate3 出现一个 47 成员的大簇**(代表 id69 market_strength_volume_retail_flow_v2)。即 59 个过关因子里 47 个 IC 序列彼此 corr>0.7、本质同一信号(市场强度×量×散户资金流)。真正彼此独立的信号只有 9 个。**"59 个显著"严重高估了独立 alpha 数量。**

---

## 3. 9 个 gate_all_pass_candidate(=9 簇代表)

| id | 因子名 | seal | hac_t | BH q(n125) | spread | spread_t | 正spread占比 | decay | 所属簇大小 |
|---|---|---|---|---|---|---|---|---|---|
| 34 | seal_quality_with_trend_confirmation | ✔ | 12.65 | 0.0000 | +0.0158 | 7.23 | 0.68 | decay_warning | 5 |
| 124 | seal_quality_retail_flow_vs_float_mv | ✔ | 11.16 | 0.0000 | +0.0147 | 7.16 | 0.68 | stable | 1 |
| 69 | market_strength_volume_retail_flow_v2 | ✔ | 10.85 | 0.0000 | +0.0144 | 6.46 | 0.65 | decay_warning | **47** |
| 26 | market_heat_with_breakout_consistency | ✘ | 7.69 | 0.0000 | +0.0101 | 4.31 | 0.62 | decay_warning | 1 |
| 94 | volume_breakout_retail_exit | ✘ | 6.36 | 0.0000 | +0.0064 | 4.94 | 0.60 | decay_warning | 1 |
| 12 | trend_momentum_consolidation | ✘ | 6.27 | 0.0000 | +0.0028 | 2.21 | 0.55 | decay_warning | 1 |
| 102 | seal_quality_with_retail_flow | ✔ | 4.31 | 0.0000 | +0.0058 | 2.85 | 0.57 | stable | 1 |
| 18 | trend_momentum_consolidation | ✘ | 3.86 | 0.0003 | +0.0064 | 2.53 | 0.56 | stable | 1 |
| 119 | early_seal_industry_flow | ✔ | 3.10 | 0.0042 | +0.0043 | 1.95 | 0.54 | decay_warning | 1 |

- seal 候选 5 个(34/124/69/102/119),非 seal 4 个(26/94/12/18)。最强的三个都是 seal 类(hac_t 10~13、spread_t 6~7、正 spread 占比 0.65~0.68)。
- id12 与 id18 同名 trend_momentum_consolidation,是公式变体,分到不同单成员簇,各自保留。

---

## 4. 三池 / 多周期对照(辅助,非主判据)

**三池 Gate1 过关数(T3):**

| 池 | gate1_pass | insufficient_coverage |
|---|---|---|
| event_pool_all(主) | 59 | 51 |
| first_board_pool | 52 | 51 |
| multi_board_pool | 19 | 52(每日需≥10/降8只,多数日不足) |

**多周期 Gate1 过关数(event_pool_all):** T1=56 / T2=62 / **T3=59(主)** / T5=56;mean_ic 均值 T3 最高(0.0553)> T5(0.0398)> T2(0.0360)≈ T1(0.0356)。

- **禁挑最佳已执行**:final_verdict 仅用主口径(event_pool_all/T3);first/multi 池、T1/T2/T5 只作对照,不升级判定。
- **2 个因子(id58、id138)在 first/multi 池 T3 过关但主口径 fail**。脚本**未实现 `pool_specific_candidate` 标注**,这俩在 ledger 里记为 `gate1_fail`。⚠️ 见 §7 已知缺口。

---

## 5. IC 显著但 spread 弱

gate2_pass 的 59 个里,spread 弱(|spread_t|<2 或 spread≤0)的只有 **2 个**:id119 early_seal_industry_flow(spread_t=1.95)、id120 strong_seal_weak_retail_flow(spread_t=1.90)。其中 **id119 是候选之一**(IC 端 hac_t=3.10 勉强过线,但 spread 端 t=1.95 不显著)——这个候选的分层赚钱能力存疑,IC 显著未必转化为可交易价差。其余候选 spread 端均显著(t≥2.2)。

---

## 6. 四关自检结果(全 PASS)

| 自检 | 内容 | 结果 |
|---|---|---|
| 自检1 打乱归零(**最关键**) | 主口径目标打乱后 hac_t | 均\|t\|=0.96,95分位\|t\|=2.64 → **PASS**(打乱后回落到不显著,真实信号非随机) |
| 自检2 噪声 FDR | 30 个噪声 t 跑 BH | 通过 0 个 → PASS(FDR 能拒噪声) |
| 自检3 合成聚类 | A/B 同向、A/C 无关、A/D 互补 | A/B=1.00、A/C=0.12、A/D=-1.00 → PASS |
| 自检4 合成衰减 | stable/warning/decaying/reversal + insufficient | 5 用例全对 → PASS |

---

## 7. 已知缺口 / 与任务规格的差异(诚实标注)

1. **`pool_specific_candidate` 未实现**:脚本 final_verdict 逻辑只遍历主口径,未对"仅 first/multi 池有效"的因子(id58、id138)打 `pool_specific_candidate` 标,它们当前记为 `gate1_fail`。若需要这个标签,需补 verdict 逻辑后重跑。
2. **M120/M60 对照未做**:脚本只用单一 M120(有效 IC 日≥120 + 方向取首 120 日),**没有计算 M60 变体**。规格里提的"M120/M60 对照"在本轮输出中不存在。
3. **K20 未单独体现**:池内每日最少样本阈值用的是 event25/first15/multi10(multi 不足降 8 标 warning),非"K20"。
4. **decay_warning 占多数**:9 候选里 6 个 decay_warning(末段 IC < 首段 0.7),只是未触发 `decaying`(末段<首段 0.5 或末段<0)所以仍归 candidate。**打板因子半年度衰减信号偏强,需警惕。**

---

## 8. 声明(铁律)

- **以上 9 个 candidate 是"通过当前四关筛选的候选",绝非 robust_alpha、绝非实盘可用结论。** ledger 全程禁用 robust_alpha 字段(已 assert)。
- **打板/涨停类因子在 A 股极易失效**(情绪周期切换、监管、资金风格轮动),IC 显著 ≠ 可持续 alpha。9 候选里 6 个已显示半年度 decay_warning。
- **本轮未碰 2026 数据,未做样本外终审**(回测区间 2024-2025 + 2023 暖机)。任何候选投入使用前必须独立样本外 + 持续重验。
- **47 成员大簇**说明所谓"显著因子"高度同质,独立信号实际很少。
- 本报告由 CC 据落盘 CSV 汇总,不替 Wallace 下策略/实盘决策。

---

## 9. 建议下一步(供 Wallace 拍板,不替你决定)

1. **先决定 pool_specific_candidate 这个缺口要不要补**(补则改 verdict 逻辑重跑;不补则明确 first/multi-only 因子不纳入)。
2. 若继续:对 9 候选(尤其 3 个最强 seal 类 id34/124/69)做**样本外验证**(2026 前留出窗口 / 滚动 OOS),验证 IC 与 spread 是否持续——重点盯 6 个 decay_warning 的衰减是否恶化。
3. id119 候选 spread 端不显著(t=1.95),建议单独标记"IC 过线但价差弱",验证时优先核其可交易性。
4. 大簇(47 成员)只需保留代表 id69 做后续,其余 46 个变体不必重复验证。

---

### 落盘文件清单(research/board_event_a1/)
`board_factor_field_audit.csv`(194 因子字段审计)/ `board_a1_gate1_results.csv`(125×3池×4周期 IC+HAC)/ `board_a1_gate1_spread.csv`(主口径 Top-Bottom spread)/ `board_a1_gate2_fdr.csv`(BH-FDR + Bonferroni + n194 敏感性)/ `board_a1_gate3_clusters.csv`(9 簇)/ `board_a1_gate3_negative_corr_pairs.csv`(0 对)/ `board_a1_gate4_decay.csv`(9 代表衰减)/ `board_a1_selfcheck.csv`(四关自检)/ `board_a1_ledger.csv`(125 因子 final_verdict 台账)/ `board_a1_summary.md`(本文件)
