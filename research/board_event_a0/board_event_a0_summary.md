# 打板事件模块 A0 — 总结(事件面板 + Gate0/Gate1 小闭环)

> A0 目标:验证"事件池定义 + 收益对齐 + 池内 IC + 滚动验证 + 打乱目标归零"这条**方法链路**是否成立,**不是找强因子**。
> 红线:不接 194 全量、不做 Gate2/3/4、不碰 2026 调参、不标 robust_alpha。数据:现有 features.parquet(2024-2025 稠密日线)。环境 .venv_court。

---

## 0. 一句话

**链路跑通、四项自检全过(打乱目标 IC 归零是关键)、M120 与 M60 滚动结果高度一致。A0 成功标准全部满足,建议进入 A1。** 这 5 个测试因子本身不强(A0 不要求强):多数池内 IC 接近 0;唯一显著的 F3 是**负向**(连板/事件池里"越像强趋势"反而次 3 日越弱,反转),锁方向后在滚动中最稳——这是 A1 值得细看的线索,A0 不下判定。

---

## 1. 测试因子(从 194 里筛出的 5 个纯 K线可算因子)

扫 194 因子,`fields_used` 全部落在"日线 K线可自算"集合内的**只有 5 个**(其余 189 个都至少依赖 seal_strength/lhb_net 等打板取数复杂字段,留 A1)。被选 5 个依赖字段全是 `return_3d / rsi_14 / bb_position / up_streak / vol_ratio_5d / price_position_60d`,**均从 features 日线自算,无缺失、无未来字段**。

| 因子 | 公式(cs_rank=当日池内 pct rank) | required_fields | available | missing |
|---|---|---|---|---|
| F1_trend_breakout_a | `cs_rank(return_3d*price_position_60d)*(1-cs_rank(rsi_14))` | return_3d,price_position_60d,rsi_14 | 全有 | 无 |
| F2_trend_breakout_b | `cs_rank(return_3d*bb_position)*cs_rank(1/rsi_14)*cs_rank(up_streak)` | return_3d,bb_position,rsi_14,up_streak | 全有 | 无 |
| F3_trend_consolidation | `cs_rank(return_3d*bb_position)*cs_rank(price_position_60d)*cs_rank(1/rsi_14)` | return_3d,bb_position,price_position_60d,rsi_14 | 全有 | 无 |
| F4_trend_vol_confirm | `cs_rank(return_3d*bb_position*up_streak)*cs_rank(vol_ratio_5d/rsi_14)` | +vol_ratio_5d | 全有 | 无 |
| F5_trend_mom_vol_confirm | 同 F4(194 里两条目公式相同) | 同上 | 全有 | 无 |

**为什么选它们**:唯一一批 fields_used ⊆ 现有日线可算集的真实 194 因子;用真因子+现有易得字段验链路,避免示意因子验通、A1 接真因子撞字段坑。基础字段口径:return_3d/rsi_14(Wilder)/bb_position((close−MA20)/2σ20)/up_streak(连涨)/vol_ratio_5d(量/5日均量)/price_position_60d((close−LL60)/(HH60−LL60)),全用复权价、仅用 ≤T 数据。

---

## 2. 三套池的 IC / Spread(主收益 T+3)

| 因子 | event_pool_all IC / spread | first_board IC | multi_board IC |
|---|---|---|---|
| F1 | +0.008 / +0.0020 | +0.010 | −0.019 |
| F2 | −0.003 | +0.012 | −0.039 |
| **F3** | **−0.037** (hac −6.21) | **−0.028** (−4.81) | **−0.077** (−5.17) |
| F4 | +0.004 | +0.017 (hac 2.13) | −0.013 |
| F5 | +0.004 | +0.017 (hac 2.13) | −0.013 |

**池间对照有信息量**:first_board_pool 普遍比 multi_board_pool 正(F1/F2/F4 在首板正、连板负)——首板与连板行为确实不同,正是 C 分层要暴露的。F3 三池都强负(反转),最一致。

每日样本:event 中位 115(min30)、first 中位 98(min18)、multi 中位 16(min8,**200 天触发 floor=8 并标 small_sample_warning**,机制正确)。

---

## 3. 收益周期对照(event_pool_all,mean_ic)

| 因子 | T+1 | T+2 | T+3 | T+5 |
|---|---|---|---|---|
| F1 | −0.008 | +0.004 | +0.008 | +0.018 |
| F2 | −0.017 | −0.005 | −0.003 | +0.003 |
| F3 | −0.026 | −0.025 | −0.037 | −0.043 |
| F4/F5 | +0.006 | +0.001 | +0.004 | +0.007 |

梯度合理:F1 随周期走强、F3 随周期负向加深、F2 次日最负后回升——说明收益周期维度计算正确、有区分。HAC lag 按周期设(T1=1…T5=5),naive_t 与 hac_t 均输出,主判据用 hac_t。

---

## 4. ★ 滚动验证 M120 vs M60 对照(核心判据之一)

event_pool_all × T3,train 锁方向、valid 只验:

| 因子 | M120 通过率 / valid_mean_ic | M60 通过率 / valid_mean_ic | 判读 |
|---|---|---|---|
| F1 | 56% / +0.0046 | 57% / −0.0010 | 两套都"掷硬币",不稳 |
| F2 | 44% / −0.0014 | 38% / −0.0093 | 两套都不稳 |
| **F3** | **89% / +0.0343** | **90% / +0.0325** | **两套都稳**(锁方向后,反转信号一致) |
| F4/F5 | 50% / +0.0002 | 48% / −0.0067 | 两套都"掷硬币" |

**关键结论:M120 与 M60 高度一致——没有任何因子"只在 M60 稳、M120 不稳"(即没有近期过拟合迹象)。** F3 两套都 ~90% 稳,F1/F4/F5 两套都 ~50%,F2 两套都弱。说明滚动验证机制本身可靠、两窗口口径都跑通。**主口径选 M120 还是 M60,留 Wallace 看本对照定**(本数据两者结论一致,差别不大)。

---

## 5. 自检结果

- **10.1 事件池**(Gate0):抽查 5 日 event/sealed/failed/first/multi 数量合理 ✅
- **10.2 收益对齐**(Gate0):抽样面板值 vs 复权价复算**完全一致(<1e-6)**,确认 T+1open→T+Nclose ✅
- **10.3 泄漏自检**:测试因子基础字段无任何 fwd/future/T+N 未来标签 ✅ PASS
- **10.4 打乱目标自检(关键)**:主池×T3 打乱未来收益后,5 因子 shuffled mean_ic∈[−0.004,+0.006]、shuffled hac_t∈[−1.07,+1.14],**全部 |hac_t|<2 且 |mean_ic|<0.02 → IC 归零 ✅ PASS**(无泄漏)。

> 对照真实结果:F3 真值 hac_t=−6.21,打乱后 +0.11 → 说明 F3 的负向 IC 是真信号(不是泄漏假象)。打乱自检既证明无泄漏,也反衬真信号确实存在。

---

## 6. A0 成功标准对照(spec §11)

| 标准 | 结果 |
|---|---|
| 1 事件池能稳定生成 | ✅ 83,211 事件行/485 日 |
| 2 首板/连板能拆分 | ✅ first 71,522 / multi 11,689 |
| 3 收益严格从 T+1 open | ✅ 复算 1e-6 一致 |
| 4 池内 IC 能稳定计算 | ✅ 三池×四周期全算出 |
| 5 样本不足正确跳过 | ✅ multi 200 天 floor=8 标 warning;不足即 skip |
| 6 滚动验证能跑通 | ✅ M120(1040行)+ M60(1220行)双跑 |
| 7 打乱目标后 IC 归零 | ✅ 全部 |hac_t|<2 |
| 8 summary 说清问题与下一步 | ✅ 本文件 |

**A0 成功标准全部满足。**

---

## 7. 发现的数据问题(报你,留 A1 处理)

1. 5 个千级行情日(2024-09-30/10-08 "924行情"等)事件池≈全市场,真实非 bug;逐日 IC 每天等权,影响可控。
2. 停牌复牌股 pre_close 用 close.shift(1) 对个别复牌股的涨停价有失真(小量);A1 接 miniQMT/limit_list 真涨停价时精修。
3. 限价档(主板10%/创业科创20%/ST5%)按代码+名称近似判定,A1 可用交易所精确涨跌停价。
4. 纯 K线可算因子仅 5 个;A1 接入 194 全量需先补 seal_strength(tick·L1)/ 龙虎榜(AKShare)/ 散户线(K线已可算)等字段(见 v3_board 两份可行性报告)。

---

## 8. 是否进入 A1

**建议:可以进入 A1。** A0 验证的链路(事件池 C分层+B扩展、T+1open 收益、池内 Rank IC+spread、双窗滚动、四项自检尤其打乱归零)全部成立、机制正确可复现。A1 工作:① 补齐打板字段(tick 封单/龙虎榜)把 194 全量因子接入;② 复用本 A0 的池内 IC + 滚动 + 自检机制;③ 主口径 M120/M60 由 Wallace 据本对照拍。

> 红线重申:本版未接 194 全量、未做 Gate2/3/4、未碰 2026、**无 robust_alpha**;A0 不下因子可用性结论(Wallace 拍)。

## 9. 产出文件(research/board_event_a0/)
board_event_panel.parquet(Gate0,83211行)/ board_event_daily_ic.csv / board_event_gate1_results.csv / board_event_rolling_validation.csv(2260行)/ board_event_a0_summary.md / build_panel.py / gate1_run.py。
