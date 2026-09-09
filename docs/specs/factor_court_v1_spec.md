# 因子审判法庭 V1 — 执行 Spec（Gate0 + Gate1 做满）

> 给 CC 执行。这是"独立筛选层"的第一版，核心目的是**建成一个可复现、无泄漏、可审计的因子审判流水线**，并用它审判 194 个 RD-Agent 候选因子。
>
> **本版定位**：建流水线 + 练兵，不是终审。通过者只标 `gate1_candidate_alpha`，**严禁标 robust_alpha**。
>
> **协作纪律**：CC 按本 spec 执行、出结果、出报告，**不下"这个因子能不能用"的最终结论**——那由 Wallace 拍。涉及留痕/写文件的操作正常做（这是 research 产出，不碰实盘、不碰禁改文件）。卡住或拿不准就停下报告，不要自己猜着改口径。

---

## 0. 边界（先划清，全程遵守）

**只读、不动的**：
- 那 194 因子的原始文件 `limit_up/qlib_results/rdagent_factors_v4.jsonl` —— 只读，不改、不覆盖。
- `features.parquet` / `labels_only.csv` —— 只读。
- 2026 年的数据 —— **本版完全不碰**（留作将来 Final 终审）。OOS 截止 2025-12-31。

**本版不做的**（留 V2）：
- DSR / Deflated Sharpe
- ONC 聚类 / 有效独立试验数估计
- 因子去冗余
- 衰减监控
- 2026 Final 终审
- 组合回测 / long-short 组合 / 实盘组合
- **robust_alpha 最终判定**

**输出目录**：`research/factor_court/v1/`
- 台账文件：先查 `research/factor_validation/` 下是否已有 `factor_conclusions_ledger.csv` 种子。**不要重复建**。本版的 Gate1 台账可以是一个独立的 v1 结果文件（见 §6），是否并入主台账等 Wallace 定。

---

## 1. 执行前：先摸清两个输入的真实结构（只读勘查，先别算）

动手算之前，先把两个输入的实际情况摸清楚，报告给我（Wallace），确认无误再往下。**这一步只勘查、不计算。**

### 1.1 摸清 194 因子 jsonl 的实际结构
读 `limit_up/qlib_results/rdagent_factors_v4.jsonl`，报告：
- 总条数（确认是不是 194）
- 每条记录的**实际字段名**（之前盘点说有 name/economic_meaning/formula/direction/fields_used/train_ic/test_ic/round/phase —— 核实是不是这些，有没有别的）
- `formula` 字段长什么样（举 3-5 个真实例子）——是 qlib 表达式？还是别的格式？用了哪些算子？
- `fields_used` 字段长什么样——它声明每个因子用到哪些底层字段。**这是后面字段审计的关键**。把所有因子用到的**字段全集**列出来（去重后总共依赖多少种字段）。
- `direction` 字段——有没有？是每个因子都有明确方向，还是部分缺失？
- 有没有任何字段记录"该因子挖掘时用了哪段时间的数据"（discovery window 相关）——大概率没有，确认一下。

### 1.2 摸清 features.parquet 的实际列
读 `features.parquet` 的 schema（列名 + dtype），报告：
- 总列数、所有列名
- 确认这些关键列在不在、叫什么：复权价（open_adj/high_adj/low_adj/close_adj）、原始价（open/high/low/close）、量（vol/amount）、前向收益（return_5d/10d/20d）、日期列、股票代码列
- 日期范围（确认 2018-2026）、股票数
- **关键**：把 1.1 里那个"194 因子依赖的字段全集"，跟 features 的列**做一次映射**，报告：
  - 有多少种依赖字段 features 里**有**（能对上）
  - 有多少种**没有**（features 里查无此列，比如打板专用的 seal_strength/auction_* 这类）
  - **由此估计：194 因子里，有多少个的依赖字段能被 features 完全满足**（这些才能进入计算；其余直接 missing_fields 出局）

**这一步报告回来，我（和 Wallace）看一眼"能算的因子大概有几个"，确认后再让你进 Gate0 实际计算。** 如果能算的极少（比如个位数），我们可能要调整策略，所以先停在这里报告。

---

## 2. Gate0 — 把因子值干净地算出来（地基）

> Gate0 的每一个产出都是后面判决可信的前提。**地基歪了，后面 t 值再严都是判错。** 防泄漏是 Gate0 的最高优先级。

### Step 1：扫描因子定义
读 194 因子 jsonl，对每个因子提取：`factor_id`(可用行号或name)、`factor_name`、`formula`、`required_fields`(从 fields_used 取)、`direction`(若有)。

### Step 2：字段映射审计 → 出 `factor_field_audit.csv`
对每个因子，检查 `required_fields` 是否都在 features 列里：
- 全部都在 → `field_coverage_status = full`，`can_calculate = True`
- 部分在 → `field_coverage_status = partial`，`can_calculate = False`（部分缺就不算，避免半拉子因子）
- 都不在/关键字段缺 → `field_coverage_status = missing`，`can_calculate = False`

输出字段：`factor_id, factor_name, source_file, formula, required_fields, available_fields, missing_fields, field_coverage_status, can_calculate, reason`

**只有 `can_calculate = True` 的因子进入后续步骤。** 其余在最终台账标 `missing_fields` 出局。

### Step 3：discovery window 审计 → 出 `factor_discovery_window_audit.csv`
尽量从 jsonl / RD-Agent 残留 log / metadata 提取"每个因子挖掘时用了哪段数据"。
- 查得到 → 据实填，并判断 OOS(2023-2025) 是否在挖掘窗口内：不在→`oos_purity=clean`；在→`oos_purity=tainted`
- **查不到（大概率）→ `oos_purity=unknown`**，reason 写明"RD-Agent 运行环境已不在，无法确认挖掘数据窗口"

输出字段：`factor_id, factor_name, rdagent_run_id, candidate_generation_data_start, candidate_generation_data_end, is_start, is_end, oos_start, oos_end, final_start, final_end, oos_purity, oos_purity_reason`

**重要**：`oos_purity != clean` 的因子，后面**仍然计算 IC/t**，但最终结论里必须标注"OOS 可能不纯，本结果按历史验证看、不作严格样本外铁证"。不因为 unknown 就跳过计算。

### Step 4：算因子值（★防未来函数是重中之重）
对 `can_calculate = True` 的因子，用 features 算出每只票每个交易日的因子值。**铁律**：
- **T 日的因子值，只能用 T 日及之前的数据算。** 因子公式里若出现：未来字段、负的 shift（向未来取数）、直接引用 return_5d/10d/20d 这类前向收益字段 → **判 `calc_error` 或 `leakage_suspected`，该因子出局并标红**。
- 前向收益（return_10d 等）**只能作为被预测的标签**，绝对不能进因子计算。这条要在代码里显式检查。
- 标准化若需要，用**滚动 zscore**（只用历史窗口，不用全样本均值/std）—— 参考 AlphaCFG 那个 `rolling_zscore_normalize` 的纪律。
- 复权口径：用 features 的 `*_adj` 列算（注意 local_data_inventory 标过复权口径存疑，算收益/排名用比率不受影响，但若公式用到绝对价要留意）。

### Step 5：构造收益标的
主收益 `return_10d_cs_demean`：
```
return_10d_cs_demean[某股,某日] = return_10d[某股,某日] − 当日全市场 return_10d 均值
```
（横截面去均值，零成本消除市场整体涨跌偏差，不需要任何基准指数数据）

辅助收益 `raw_return_10d`：直接读 features 的 return_10d。

features 已有 return_10d 就直接读，不要自己重算（避免口径不一致）。

### Step 6：构造两套 mask（★打板因子不能误杀）
- **`universal_clean_mask`**（适合通用因子）：过滤 ST、停牌、未来收益缺失、价格/成交量异常、不可交易样本；**过滤涨跌停日**。
- **`board_domain_mask`**（适合打板因子）：过滤 ST、停牌、未来收益缺失、严重异常；**保留涨停相关样本**；单独标记一字板/无法买入样本。

两套 mask 各自独立算 IC。ST 识别若 features 无显式列，从 name 前缀（ST/*ST/退）解析，并在报告注明这是近似识别。

### Step 7：锁定因子方向（★OOS 前锁死，防隐蔽未来函数）
优先级：
1. 因子定义(jsonl 的 direction)有明确方向 → 用原始方向，`factor_direction_source = definition`
2. 没有方向 → 用 **IS(2018-2022)** 的 mean IC 符号定方向，`factor_direction_source = is_ic`
3. **OOS(2023-2025) 只验证，绝对不准用 OOS 结果决定/翻转方向**

输出记录：`factor_direction_source, factor_direction, is_ic_mean_before_direction, is_ic_mean_after_direction, oos_ic_mean_before_direction, oos_ic_mean_after_direction, direction_locked_before_oos`

**`direction_locked_before_oos` 必须为 True**，否则该因子不得通过 Gate1。

---

## 3. Gate1 — 样本外 t > 3.0（判决）

> 只在 OOS(2023-2025) 上判。两套 mask 各判一遍。

### Step 8：OOS 上算横截面 Rank IC
在 2023-2025 每个交易日，算横截面 Spearman Rank IC：
```
RankIC[某日] = Spearman( factor_value[当日所有有效票], return_10d_cs_demean[当日所有有效票] )
```
主收益用 `return_10d_cs_demean`，辅助也跑一遍 `raw_return_10d` 作对比。
两套 mask（universal / board_domain）各算一套 IC 序列。

**最低样本要求**（不满足则不给通过，标 insufficient_coverage）：
- `min_daily_stocks = 100`：某日有效票<100 → 该日不算 IC
- `min_oos_ic_days = 120`：OOS 有效 IC 天数<120 → 不给通过
- `min_factor_coverage_ratio = 0.3`：因子覆盖率太低 → 标 insufficient_coverage

### Step 9：算 t 值（★必须用 HAC，否则门槛是假的）
对每条 IC 序列算两个 t：
- `ic_t_naive = mean(IC) / std(IC) * sqrt(N)` —— 仅作参考
- **`ic_t_hac` = Newey-West/HAC t 值，lag=10** —— **主判据**

> 为什么必须 HAC：用 10 日收益、每天算 IC，相邻日的 10 日收益重叠 9 天，IC 序列强自相关，naive t 会虚高。HAC(lag=10) 校正这个自相关，给出诚实的 t。

### Step 10：Gate1 判定
判定规则（按顺序）：
```
字段缺失           → verdict = missing_fields
覆盖率/样本不足     → verdict = insufficient_coverage
算因子值出错/疑泄漏 → verdict = calc_error (或 leakage_suspected)
方向没在OOS前锁定   → verdict = direction_unlocked
OOS 被污染(tainted) → verdict = oos_tainted（仍输出统计值，但不通过 strict Gate1）
HAC t <= 3.0       → verdict = gate1_fail
HAC t > 3.0 且 OOS clean 且方向已锁 → verdict = gate1_candidate_alpha
```

**红线：本版 verdict 只允许上面这几个，严禁出现 `robust_alpha`。**

`gate1_candidate_alpha` 的含义必须在报告里写清：**只过了第一关（样本外 t>3.0），尚未过 DSR/去冗余/衰减/2026终审，不等于稳健 alpha、不能直接用于实盘。**

---

## 4. 两套 mask 的结果怎么解读

每个因子会得到 universal 和 board_domain 两套结果，对照看：
- 两套都过 t>3.0 → 较强信号，可能是通用有效的因子
- 只在 board_domain 过 → 可能只在打板场景有效（涨停样本是它的主场）
- 只在 universal 过 → 可能是通用选股因子，打板场景反而不行
- 都不过 → 在 features 这个通用域站不住

这个对照本身就是有价值的产出，记进结果表。

---

## 5. 几个现实预期（CC 执行时不必慌，照实出结果）

1. **能算的因子可能远少于 194**：194 是打板域因子（依赖 seal_strength/auction_* 等打板字段），features 是通用技术面板，大概率对不上，一大半可能 missing_fields 出局。**这是数据域不匹配的正常结果，不是 bug。**
2. **过 HAC t>3.0 的可能寥寥无几甚至为零**：HAC t>3.0 是极严门槛，加上用通用域验打板因子（域错位），过关个位数甚至 0 都正常。**0 个过关也是有价值的结论。**
3. **OOS 纯度大概率 unknown**：RD-Agent 环境没了，结论按历史验证看、不当严格样本外铁证。

**照实出结果，不要为了"好看"调口径。** 这套法庭的价值就在于敢说"不"。

---

## 6. 输出文件（全部放 `research/factor_court/v1/`）

1. **`factor_field_audit.csv`** — §2 Step2，字段审计
2. **`factor_discovery_window_audit.csv`** — §2 Step3，挖掘窗口审计
3. **`factor_gate1_results.csv`** — Gate1 逐因子结果，字段：
   `factor_id, factor_name, mask_type(universal/board_domain), return_type(raw/cs_demean), factor_direction, factor_direction_source, valid_ic_days, valid_stock_count_mean, factor_coverage_ratio, ic_mean, ic_std, ic_t_naive, ic_t_hac, hac_lag, gate1_pass_naive_t, gate1_pass_hac_t, gate1_final_pass, verdict, fail_reason`
4. **`factor_court_v1_ledger.csv`** — 本版台账（独立文件，不直接并入主台账，并入与否 Wallace 定），字段：
   `factor_id, factor_name, version, source_file, can_calculate, field_status, oos_purity, best_mask_type, best_return_type, gate0_status, gate1_status, verdict, primary_evidence, secondary_evidence, fail_reason, next_action, created_at`
   verdict 只允许：`missing_fields / insufficient_coverage / calc_error / leakage_suspected / oos_tainted / direction_unlocked / gate1_fail / gate1_candidate_alpha`
5. **`factor_gate1_summary.md`** — 人看的总结：多少因子能算、多少出局(各原因分布)、多少过 Gate1、两套 mask 对照发现、OOS 纯度说明、**明确写"本版是 Gate0+1 练兵，通过者仅 candidate_alpha"**

---

## 7. 执行顺序总结（每个阶段可停）

1. **§1 只读勘查**（摸清 jsonl 结构 + features 列 + 估算能算几个因子）→ **停下报告，等确认**
2. 确认后 → **§2 Gate0**（字段审计 → window审计 → 算因子值 → 收益 → 双mask → 锁方向）
3. → **§3 Gate1**（OOS 算 Rank IC → HAC t → 判定）
4. → **§6 出 5 个文件 + summary** → 报告

代码建议放 `research/factor_court/v1/` 下成正式模块（不是一次性脚本，这是会迭代到 V2 的系统）。用哪个 Python 环境：features 是 parquet，需要 pandas/pyarrow——用能读 parquet 的环境（quant_platform 的 .venv 或你确认有 pandas/pyarrow 的环境；**不要用 .venv_qlib/.venv_rdagent**，那俩是挖掘层专用，别污染）。

**全程**：只读 194 因子原文件、只读 features、不碰 2026、不下最终结论。卡住/拿不准就停下报告。
