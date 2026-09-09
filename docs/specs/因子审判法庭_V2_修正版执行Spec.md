# 因子审判法庭 V2 — 修正版执行 Spec

> 给 Claude Code / Codex 执行。
> 本文档是在 V1（Gate0 + Gate1 已建成、机制验证通过）基础上，补建 Gate2 / Gate3 / Gate4，把“因子审判法庭”建完整。
> 本修正版已合并审核意见：多重检验敏感性校正、去冗余不使用 `|corr|`、衰减规则量化、机制自检修正、配置快照落盘。

---

## 0. 本版定位

### 0.1 当前背景

V1 已完成：

- Gate0：字段审计、因子值计算、防未来函数、样本过滤、收益对齐；
- Gate1：OOS Rank IC + HAC t 检验；
- 受审材料：31 个 features 通用技术因子；
- V1 结果：29 / 31 个因子通过 Gate1；
- 但存在三个限制：
  - OOS 纯度 unknown；
  - 因子高度冗余；
  - 未做多重检验校正；
  - 未做衰减监控。

所以 V1 通过者只能标：

```text
gate1_candidate_alpha
```

不得标：

```text
robust_alpha
```

---

### 0.2 V2 的任务

V2 的任务不是证明这 29 个因子真有 alpha。

V2 的任务是：

```text
把后三关机制建完整，并验证后三关能正确砍掉：
1. 多重检验后站不住的因子；
2. 显著但高度重复的因子；
3. 历史有效但近期衰减的因子。
```

这 31 个通用技术因子只是试跑材料，不是产品级 alpha。

---

### 0.3 V2 最终结论边界

V2 最终最多输出：

```text
gate_all_pass_candidate
```

严禁输出：

```text
robust_alpha
```

原因：

- 本批因子 OOS 纯度 unknown；
- 本批因子是教科书通用技术因子；
- 没有经过 2026 Final 终审；
- 没有证明其在新挖掘因子场景下的干净样本外有效性；
- 没有进入组合回测 / 成本敏感性 / 实盘约束验证。

---

## 1. 红线

以下红线不可破：

1. **绝不标 robust_alpha**
   四关全过最多标 `gate_all_pass_candidate`。

2. **不碰 2026 数据**
   OOS 仍截至 2025-12-31。
   2026 留作 Final Confirmation。

3. **不下最终可用性结论**
   CC 只输出结果、证据、报告。
   是否认可、是否进入下一阶段，由 Wallace 拍板。

4. **优先复用 V1 产出，不重复跑大计算**
   V2 后三关应基于 V1 每日 IC 序列运行。
   如果 V1 只落盘汇总、没有每日 IC 序列，则 V2 第一步先补存每日 IC 序列。
   除补存 IC 序列外，不重新跑 7.7M 行原始因子计算。

5. **不动 194 个原始因子文件**
   V2 只读取和分析，不修改原始因子定义。

6. **不擅自安装依赖**
   优先纯 numpy / pandas 实现。
   如果必须安装 scipy，先停下报告，由 Wallace 决定是否安装。

7. **卡住就停下报告**
   不能擅自改口径继续跑。

---

## 2. 输入与输出

### 2.1 输入目录

V1 产出目录：

```text
research/factor_court/v1/
```

### 2.2 输入文件

必须读取：

```text
factor_gate1_results.csv
```

预期行数：

```text
31 factors × 2 masks × 2 return types = 124 rows
```

还需要读取或生成：

```text
daily_ic_series.csv
```

如果 V1 已经落盘每日 IC 序列，则直接读取。
如果没有，则按 V1 完全相同口径补存一次每日 IC 序列。

---

### 2.3 主口径

V2 主口径沿用 V1 主口径：

```text
mask_type = universal_clean_mask
return_type = fwd_return_10d_cs_demean
ic_type = daily cross-sectional Rank IC
t_type = HAC t-stat
```

说明：

- V1 已确认 Rank IC 对目标横截面去均值基本不变；
- raw return 只作为对照；
- V2 后三关主判断只基于主口径；
- board_domain 作为对照结果，不作为 V2 主判据。

---

### 2.4 输出目录

新建：

```text
research/factor_court/v2/
```

不得覆盖 V1 文件。

---

## 3. 配置快照

V2 必须新增配置快照文件：

```text
factor_court_v2_config.json
```

必须记录：

```text
run_time
input_v1_dir
output_v2_dir
main_mask_type
main_return_type
ic_type
hac_lag
oos_start
oos_end
final_holdout_start
final_holdout_end
alpha_fdr
primary_fdr_family_size
sensitivity_family_size
bonferroni_alpha
cluster_corr_threshold
negative_corr_threshold
decay_ratio_decaying_threshold
decay_ratio_warning_threshold
use_abs_corr_for_clustering
robust_alpha_allowed
notes
```

建议默认值：

```json
{
  "main_mask_type": "universal_clean_mask",
  "main_return_type": "fwd_return_10d_cs_demean",
  "ic_type": "daily_cross_sectional_rank_ic",
  "hac_lag": 10,
  "oos_start": "2023-01-01",
  "oos_end": "2025-12-31",
  "final_holdout_start": "2026-01-01",
  "alpha_fdr": 0.05,
  "primary_fdr_family_size": 31,
  "sensitivity_family_size": 194,
  "bonferroni_alpha": 0.05,
  "cluster_corr_threshold": 0.7,
  "negative_corr_threshold": -0.7,
  "decay_ratio_decaying_threshold": 0.5,
  "decay_ratio_warning_threshold": 0.7,
  "use_abs_corr_for_clustering": false,
  "robust_alpha_allowed": false
}
```

特别注意：

```text
use_abs_corr_for_clustering 必须为 false。
```

---

## 4. Gate2 — 多重检验校正

### 4.1 目标

Gate2 负责回答：

```text
这些 Gate1 显著的因子，在考虑多重检验后是否还站得住？
```

V1 有 31 个因子参与测试，其中 29 个通过 Gate1。
Gate2 必须按实际测试过的 31 个因子进行主校正，同时增加原始 194 候选因子规模的敏感性校正。

---

### 4.2 主判据

主判据：

```text
BH-FDR, alpha_fdr = 0.05, family_size = 31
```

做法：

1. 读取每个因子主口径的 V1 HAC t；
2. 由 HAC t 计算双尾 p 值：

```text
p_two_sided_hac = 2 * (1 - Φ(|t_hac|))
```

3. 对 31 个因子的 p 值做 Benjamini-Hochberg FDR 校正；
4. 输出每个因子的 BH q-value / adjusted p；
5. 判断是否通过 FDR。

---

### 4.3 p 值方向

V2 默认使用双尾 p 值，作为保守判据：

```text
p_two_sided_hac
```

同时可以输出单尾 p 值作为参考：

```text
p_one_sided_hac_reference
```

但 Gate2 主判据只使用双尾 p 值。

原因：

- V1 已锁定因子方向；
- 但 V2 仍采用双尾以避免过度乐观；
- 单尾结果只用于参考，不进入 final verdict。

---

### 4.4 敏感性校正

除了主校正外，必须额外输出：

```text
BH-FDR_n194_sensitivity
Bonferroni_n31
Bonferroni_n194_sensitivity
```

解释：

- n=31：本次 features 可计算且实际测试的因子数；
- n=194：原始候选因子池规模，作为压力测试；
- n=194 不作为 V2 主判据，但必须进入 summary，避免低估多重检验风险。

---

### 4.5 Gate2 判定

```text
如果 Gate1 未通过：
    gate2_status = not_applicable_due_to_gate1_fail

如果 Gate1 通过，但 BH-FDR_n31 不通过：
    gate2_status = gate2_fail

如果 Gate1 通过，且 BH-FDR_n31 通过：
    gate2_status = gate2_pass
```

n=194 敏感性不直接改变 gate2_status，但必须输出字段：

```text
bh_fdr_n194_pass_sensitivity
bonferroni_n31_pass
bonferroni_n194_pass_sensitivity
```

---

### 4.6 Gate2 输出文件

输出：

```text
factor_gate2_fdr.csv
```

字段建议：

```text
factor_name
gate1_status
hac_t
p_two_sided_hac
p_one_sided_hac_reference
bh_rank_n31
bh_threshold_n31
bh_q_value_n31
bh_fdr_n31_pass
bh_rank_n194_sensitivity
bh_threshold_n194_sensitivity
bh_q_value_n194_sensitivity
bh_fdr_n194_pass_sensitivity
bonferroni_threshold_n31
bonferroni_n31_pass
bonferroni_threshold_n194_sensitivity
bonferroni_n194_pass_sensitivity
gate2_status
fail_reason
```

---

## 5. Gate3 — 去冗余

### 5.1 目标

Gate3 负责回答：

```text
这些通过 Gate2 的因子里，哪些其实是在表达同一个 alpha / 同一个预测行为？
```

目标不是选最多因子，而是压缩成少数独立信号簇。

---

### 5.2 重要修正规则：不得使用 |corr| 做主聚类

Gate3 主冗余判定不得使用：

```text
|corr| > 0.7
```

原因：

- IC 序列强正相关通常代表预测行为类似；
- IC 序列强负相关不一定代表冗余；
- 强负相关可能代表互补、对冲、不同市场状态轮动；
- 用 `|corr|` 会把潜在互补因子误杀。

所以 Gate3 主聚类只使用：

```text
corr > 0.7
```

对于：

```text
corr < -0.7
```

不判冗余，单独输出为：

```text
potential_complement_pair
```

---

### 5.3 主数据

只对 Gate2 pass 的因子做 Gate3 主聚类。

使用：

```text
OOS 期间每日 IC 序列
```

相关性：

```text
Pearson correlation of daily IC series
```

---

### 5.4 聚类方法

优先纯 numpy / pandas。

可以使用简单阈值并查集替代层次聚类：

1. 对 Gate2 pass 因子两两计算 IC 序列 Pearson corr；
2. 如果 `corr > 0.7`，连边；
3. 使用 union-find / connected components 得到簇；
4. 每个连通分量视为一个 redundancy cluster。

这样不需要 scipy。

---

### 5.5 每簇代表因子选择

每簇选择一个代表因子。

优先级：

1. HAC t 最高；
2. 如果 HAC t 接近，则优先覆盖率更高；
3. 如果覆盖率也接近，则优先年度 IC 更稳定；
4. 如果仍接近，则优先公式更简单 / 更容易解释。

代表因子字段：

```text
gate3_representative = True
```

非代表因子字段：

```text
gate3_status = gate3_redundant
fail_reason = redundant_to_<representative_factor_name>
```

---

### 5.6 强负相关因子对

必须额外输出强负相关因子对：

```text
corr < -0.7
```

这些因子对不判冗余，标记为：

```text
potential_complement_pair
```

输出文件：

```text
factor_gate3_negative_corr_pairs.csv
```

字段建议：

```text
factor_a
factor_b
ic_corr
note
```

note 示例：

```text
strong_negative_ic_corr_not_marked_redundant
```

---

### 5.7 关于因子值相关的说明

V2 Gate3 主去冗余基于：

```text
IC series corr
```

这表示：

```text
预测行为去冗余
```

但它不等价于：

```text
持仓重合度去冗余
```

如果 V1 已保存因子值面板，可额外计算：

```text
factor_rank_corr_to_representative
```

作为参考。

如果没有因子值面板，不强求重算，summary 里必须注明：

```text
本版 Gate3 基于 IC 序列相关进行预测行为去冗余，不等同于持仓重合度去冗余。
```

---

### 5.8 Gate3 输出文件

输出：

```text
factor_gate3_clusters.csv
```

字段建议：

```text
factor_name
gate2_status
cluster_id
cluster_size
cluster_members
cluster_representative
gate3_representative
ic_corr_to_representative
factor_rank_corr_to_representative_optional
gate3_status
fail_reason
cluster_label
```

输出：

```text
factor_gate3_corr_matrix.csv
```

输出：

```text
factor_gate3_negative_corr_pairs.csv
```

---

## 6. Gate4 — 衰减监控

### 6.1 目标

Gate4 负责回答：

```text
这个因子的 IC 是否在 OOS 期间逐年弱化？
```

Gate4 是风险标记，不是硬杀。

它不负责证明因子失效，只负责标出：

```text
这个因子可能正在衰减，需要 2026 终审重点观察。
```

---

### 6.2 年度切分

按 OOS 年份切分：

```text
2023
2024
2025
```

对每个因子计算：

```text
yearly_ic_2023
yearly_ic_2024
yearly_ic_2025
```

这些 IC 必须沿用 V1 已锁定方向。

---

### 6.3 衰减指标

必须输出：

```text
decay_ratio_2025_vs_2023
decay_slope_3y
decay_status
```

建议定义：

```text
decay_ratio_2025_vs_2023 = yearly_ic_2025 / max(abs(yearly_ic_2023), eps)
```

其中：

```text
eps = 1e-12
```

`decay_slope_3y` 可以用 2023 / 2024 / 2025 三个点做简单线性斜率。
由于只有 3 个年度点，不做复杂显著性检验。

---

### 6.4 decay_status 枚举

允许：

```text
stable
decay_warning
decaying
```

---

### 6.5 衰减判定规则

#### decaying

满足任一条件：

```text
1. yearly_ic_2025 < 0
```

或者：

```text
2. yearly_ic_2023 > yearly_ic_2024 > yearly_ic_2025
   且 yearly_ic_2025 < yearly_ic_2023 * 0.5
```

解释：

- 2025 IC 已经反向，直接标 decaying；
- 或者三年严格逐年下降，且 2025 不到 2023 的一半，标 decaying。

---

#### decay_warning

未达到 decaying，但满足任一条件：

```text
1. yearly_ic_2025 < yearly_ic_2023 * 0.7
```

或者：

```text
2. decay_slope_3y < 0
```

则标：

```text
decay_warning
```

解释：

- 有弱化迹象；
- 但不够严重，不直接标 decaying；
- 需要在 2026 Final 终审重点观察。

---

#### stable

不满足 decaying 或 decay_warning，则：

```text
decay_status = stable
```

---

### 6.6 Gate4 判定

```text
decay_status = stable:
    gate4_status = gate4_pass

decay_status = decay_warning:
    gate4_status = gate4_pass_with_warning

decay_status = decaying:
    gate4_status = gate4_flag_decaying
```

注意：

```text
Gate4 是风险标记，不是统计硬杀。
```

但是综合 verdict 中：

- `decaying` 应输出 `gate_pass_but_decaying`；
- `decay_warning` 可仍输出 `gate_all_pass_candidate`，但 next_action 必须写明 2026 重点观察。

---

### 6.7 慢因子提醒

如果存在 60d 类慢因子，summary 中必须注明：

```text
HAC lag=10 可能对慢因子欠校正，t/IC 可能偏高。
```

这是 V1 已经提出的提醒，V2 继续保留。

---

### 6.8 Gate4 输出文件

输出：

```text
factor_gate4_decay.csv
```

字段建议：

```text
factor_name
gate3_status
yearly_ic_2023
yearly_ic_2024
yearly_ic_2025
decay_ratio_2025_vs_2023
decay_slope_3y
decay_status
gate4_status
next_action
```

---

## 7. 综合判定与台账

### 7.1 final_verdict 允许集

V2 最终台账 `final_verdict` 只允许：

```text
gate1_fail
gate2_fail
gate3_redundant
gate_pass_but_decaying
gate_all_pass_candidate
```

严禁：

```text
robust_alpha
```

---

### 7.2 综合判定规则

```text
如果 Gate1 未通过：
    final_verdict = gate1_fail

如果 Gate1 通过，但 Gate2 未通过：
    final_verdict = gate2_fail

如果 Gate2 通过，但 Gate3 判为冗余：
    final_verdict = gate3_redundant

如果 Gate2 通过，且是 Gate3 代表，但 Gate4 decay_status = decaying：
    final_verdict = gate_pass_but_decaying

如果 Gate2 通过，且是 Gate3 代表，且 Gate4 decay_status = stable：
    final_verdict = gate_all_pass_candidate

如果 Gate2 通过，且是 Gate3 代表，且 Gate4 decay_status = decay_warning：
    final_verdict = gate_all_pass_candidate
    next_action 必须注明：
        2025 IC 有弱化迹象，2026 Final 终审需重点观察。
```

---

### 7.3 gate_all_pass_candidate 含义

summary 中必须明确写：

```text
gate_all_pass_candidate 只表示：
该因子在 V1 Gate1、V2 Gate2、V2 Gate3、V2 Gate4 的机制口径下暂时通过。

它不表示 robust_alpha。
它不表示可以实盘。
它不表示新发现 alpha。
它仍然受到 OOS purity unknown、教科书因子、未做 2026 终审等限制。
```

---

### 7.4 综合台账输出

输出：

```text
factor_court_v2_ledger.csv
```

字段建议：

```text
factor_name
gate1_status
gate1_hac_t
gate2_status
p_two_sided_hac
bh_q_value_n31
bh_fdr_n31_pass
bh_fdr_n194_pass_sensitivity
bonferroni_n31_pass
bonferroni_n194_pass_sensitivity
gate3_status
cluster_id
cluster_label
cluster_representative
gate3_representative
ic_corr_to_representative
gate4_status
decay_status
yearly_ic_2023
yearly_ic_2024
yearly_ic_2025
decay_ratio_2025_vs_2023
decay_slope_3y
final_verdict
fail_reason
next_action
created_at
```

---

## 8. V2 机制自检

V2 必须像 V1 一样做机制自检。

自检不过，必须停下报告，不允许继续用该机制下判定。

---

### 8.1 Gate2 自检

目标：

```text
验证 FDR 能正确控制纯噪声因子的假阳性。
```

做法：

1. 构造 20 个纯噪声 synthetic factor / synthetic t / synthetic p；
2. 混入真实 p 值或单独跑一组；
3. 检查 BH-FDR 后噪声因子是否基本被拒；
4. 输出自检结论。

输出字段：

```text
synthetic_noise_count
synthetic_noise_pass_count
gate2_selfcheck_pass
notes
```

要求：

```text
如果大量噪声因子通过 FDR，自检失败。
```

---

### 8.2 Gate3 自检

不要使用 `return_10d` 作为合成因子。

正确做法是直接构造 synthetic IC 序列：

```text
synthetic_ic_A = 随机序列
synthetic_ic_B = synthetic_ic_A + 小噪声
synthetic_ic_C = 独立随机序列
synthetic_ic_D = -synthetic_ic_A + 小噪声
```

验证：

```text
A 和 B 应被分到同一正相关冗余簇；
A 和 C 不应分到同一簇；
A 和 D 虽然强负相关，但不应被判冗余，应进入 potential_complement_pair。
```

这条自检非常重要，因为 V2 明确禁止 `|corr|` 主聚类。

输出字段：

```text
corr_A_B
corr_A_C
corr_A_D
A_B_same_cluster
A_C_same_cluster
A_D_same_cluster
A_D_marked_potential_complement
gate3_selfcheck_pass
```

---

### 8.3 Gate4 自检

目标：

```text
验证衰减规则能识别人工构造的逐年衰减。
```

构造：

```text
synthetic_yearly_ic_stable = [0.03, 0.031, 0.029]
synthetic_yearly_ic_warning = [0.03, 0.025, 0.019]
synthetic_yearly_ic_decaying = [0.03, 0.02, 0.01]
synthetic_yearly_ic_reversal = [0.03, 0.015, -0.005]
```

预期：

```text
stable -> stable
warning -> decay_warning
decaying -> decaying
reversal -> decaying
```

输出字段：

```text
case_name
yearly_ic_2023
yearly_ic_2024
yearly_ic_2025
expected_status
actual_status
gate4_selfcheck_pass
```

---

### 8.4 自检输出文件

输出：

```text
factor_court_v2_selfcheck.csv
```

以及在：

```text
factor_court_v2_summary.md
```

中写明每个自检是否通过。

如果任意一个自检失败：

```text
summary 必须写 SELF_CHECK_FAILED
并停止输出 final verdict。
```

---

## 9. Summary 报告要求

输出：

```text
factor_court_v2_summary.md
```

必须包含以下内容。

---

### 9.1 漏斗图

文字版漏斗：

```text
31 total factors
→ Gate1 pass: X
→ Gate2 BH-FDR n31 pass: Y
→ Gate2 BH-FDR n194 sensitivity pass: Y2
→ Gate3 independent clusters: Z
→ Gate4 stable representatives: W
→ gate_all_pass_candidate: N
```

---

### 9.2 每关砍掉了什么

必须说明：

- Gate2 砍掉了哪些裸 t 显著但 FDR 后不显著的因子；
- Gate3 把哪些因子聚成了同一簇；
- 每个簇的代表因子是谁；
- 每个簇的语义标签；
- Gate4 哪些因子 stable、warning、decaying。

---

### 9.3 强负相关因子对

必须单列说明：

```text
strong negative IC corr pairs
```

并注明：

```text
强负相关不在本版判为冗余，后续可作为潜在互补信号观察。
```

---

### 9.4 重要限制

summary 必须明确写：

```text
本版是建法庭后三关 + 验机制；
本批 31 个因子是 features 通用技术因子试跑材料；
四关全过者仅为 gate_all_pass_candidate；
OOS purity unknown；
未碰 2026；
不是 robust_alpha；
不能直接实盘。
```

---

### 9.5 机制自检

必须写：

```text
Gate2 selfcheck: pass / fail
Gate3 selfcheck: pass / fail
Gate4 selfcheck: pass / fail
```

如果有失败：

```text
SELF_CHECK_FAILED
```

并说明哪里失败、停止在哪里。

---

## 10. 执行顺序

按阶段执行，每阶段可停。

### Step 1：确认 V1 每日 IC 序列

1. 检查 V1 是否已有每日 IC 序列；
2. 如果有，读取并验证字段；
3. 如果没有，用 V1 口径补存一次；
4. 输出确认信息。

---

### Step 2：生成配置快照

写出：

```text
factor_court_v2_config.json
```

---

### Step 3：Gate2 + 自检

1. 计算 HAC t 对应 p 值；
2. 做 BH-FDR n=31；
3. 做 BH-FDR n=194 sensitivity；
4. 做 Bonferroni n=31 / n=194；
5. 运行 Gate2 自检；
6. 输出 `factor_gate2_fdr.csv`。

自检失败则停止。

---

### Step 4：Gate3 + 自检

1. 对 Gate2 pass 因子计算每日 IC 序列相关；
2. 使用正相关 `corr > 0.7` 聚类；
3. 不使用 `|corr|`；
4. 输出强负相关因子对；
5. 选簇代表；
6. 运行 Gate3 自检；
7. 输出 `factor_gate3_clusters.csv`、`factor_gate3_corr_matrix.csv`、`factor_gate3_negative_corr_pairs.csv`。

自检失败则停止。

---

### Step 5：Gate4 + 自检

1. 按 2023 / 2024 / 2025 计算年度 mean IC；
2. 计算 decay_ratio 和 decay_slope；
3. 依据规则判断 stable / decay_warning / decaying；
4. 运行 Gate4 自检；
5. 输出 `factor_gate4_decay.csv`。

自检失败则停止。

---

### Step 6：综合台账 + summary

输出：

```text
factor_court_v2_ledger.csv
factor_court_v2_summary.md
```

summary 必须包括漏斗图、每关结果、机制自检、限制声明。

---

## 11. 依赖与环境

使用环境：

```text
D:\quant_env\.venv_court
```

依赖原则：

```text
优先纯 numpy / pandas；
BH-FDR 可纯 numpy 实现；
Gate3 聚类可用 union-find / connected components，不需要 scipy；
正态 CDF 如无 scipy，可用 math.erf 实现；
不要擅自 pip install scipy。
```

正态 CDF 可用：

```python
from math import erf, sqrt

def norm_cdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))
```

---

## 12. 给 CC 的最短启动提示词

```text
请按《因子审判法庭 V2 — 修正版执行 Spec》执行，只做 Gate2/3/4，不碰 2026，不重算 V1 大计算，不标 robust_alpha。重点修正规则：Gate2 主 FDR 用 n=31，同时输出 n=194 敏感性校正；Gate3 主聚类只用 IC 序列正相关 corr>0.7，禁止用 |corr|，corr<-0.7 单独输出 potential_complement_pair；Gate4 使用量化衰减规则，输出 stable/decay_warning/decaying；新增 factor_court_v2_config.json；Gate2/3/4 都必须做机制自检，自检失败就停止报告。最终只允许输出 gate1_fail/gate2_fail/gate3_redundant/gate_pass_but_decaying/gate_all_pass_candidate，严禁 robust_alpha。
```

---

## 13. 一句话最终原则

```text
V2 不是为了证明这些通用技术因子能实盘，
而是为了证明因子审判法庭的后三关能正确识别：
多重检验风险、冗余风险、衰减风险。
```
