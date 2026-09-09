# dragon_event_study 接中台 — Phase2 并行验证报告

> 2026-06-28。重叠期 2026-03-02 ~ 06-25(79 交易日),中台后端 vs 原 QMT 后端,同一份 repro_core(只翻 `R.BACKEND`)。
> 脚本:`compare_backends.py`;差异明细:`_compare_diff.csv`。**结论:实质一致,通过,可进 Phase3(6.5年重跑)。**

## 一、最终一致性(剔停牌占位bar后)

**A. 日线 meta 漂移(同 universe,中台 panel vs QMT-live panel,抽样4天12749股次)**
| 字段 | maxΔ | meanΔ | 评 |
|---|---|---|---|
| y_close | 5.7e-14 | 7.7e-16 | 浮点级=完全相同 |
| y_high | 2.3e-13 | 9e-16 | 浮点级=完全相同 |
| ret3 | 4.4e-16 | 6.9e-17 | 浮点级=完全相同 |
| y_money | 1189元 | 18元 | 相对1e9基≈1e-6,可忽略 |
| avg_range | 0.00125 | 6.7e-7 | 仅0.16%股>1e-4(分钟聚合H/L vs QMT 1d 微差) |
| close_to_20d_high | 0.0142 | 2.8e-5 | 同上派生 |

**B. 端到端 Top12(中台 vs 原产物 _pool_detail.csv)**
| 模式 | Top12全一致天 | rank1一致 | Jaccard | 共同股各字段(open_ratio/auc_ratio/auc_amount/close_to_high/ret3/dragon_score) |
|---|---|---|---|---|
| v1 | 66/79 | 78/79 | 0.967 | **全部 maxΔ=0** |
| v2 | 61/79 | 78/79 | 0.955 | **全部 maxΔ=0** |
| v3 | 62/79 | 77/79 | 0.961 | **全部 maxΔ=0** |

→ **凡两端都选中的股,竞价字段、日线因子、dragon_score 逐位相同(含 v3)**。竞价 100% 吻合(再次复核确认)。

## 二、查到并修复的问题:停牌日"零成交平盘占位bar"

- 现象:中台日线(分钟聚合)对**停牌日**会留占位 bar(O=H=L=C=昨收、volume=0、amount=0);QMT 1d 停牌日**直接无 bar**。
- 危害:占位bar污染 20 日滚动窗(`dropna(close)` 不掉,因 close 非空)→ ret3/avg_range/avg_money 失真 → 个别停牌股被错误选中(修复前 600673.SH 因QMT侧反而把停牌期当窗口、ret3虚高0.20被QMT选rank1)。
- 修复:`wh_data.load_daily_panel` 加 `df = df[df['volume']>0]` —— 剔零成交(=非交易)日,与 QMT"只含真实交易日"口径对齐。
- 修复效果:avg_range maxΔ 0.0485→0.00125,y_high maxΔ 4.26→2e-13,y_money maxΔ 4.6e9→1189,dragon_score(共同股)→全0。

> ★中台侧遗留观察(非本次修复范围):中台日线对停牌日存零成交平盘bar,其它消费方直读 read.daily 也会读到。建议后续在中台层面考虑(read.daily 过滤 vol=0 或聚合时不产停牌bar)。本次在 dragon 适配层已规避。

## 三、残留差异(~4% Top12 churn)—— 已解释,可接受

差异明细 57 条"仅QMT"/54 条"仅中台":
1. **84%(48/57)= 平开knife-edge**:股票竞价价**恰等于昨收** → open_ratio 恰为 0。门槛 `if open_ratio<=0: continue` 拒绝。
   - 中台存的是干净价(如 77.85)→ open_ratio=0.0 → 剔除;
   - QMT 有浮点噪声(77.85000000000001)→ open_ratio=1e-16>0 → 混入(原产物里 rank 甚至到1)。
   - **中台更正确**(平开非高开,门槛本意要求正向高开)。属选股逻辑在边界上的确定性行为,数据本身相同。
2. 其余 ~16% = avg_range 微差(0.16%股)致 rank 11-12 边界互换。

→ 数据本体逐位相同;分歧只发生在"平开门槛浮点边界"+"H/L 微差的排名末位",且两处中台均**不劣于(多数更优于)** QMT。判定**实质一致**。

## 四、结论
- 接入正确:中台数据驱动的选股链与原 QMT 产物实质一致,竞价/日线因子/dragon_score 对共同股逐位吻合。
- 修复了停牌占位bar(适配层),并解释了全部残留差异(平开knife-edge + H/L微差,均benign)。
- **通过,进 Phase3**:放宽到 2020-2026,用中台 6.5 年数据重跑生成候选池。
