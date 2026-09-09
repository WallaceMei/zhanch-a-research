# 因子审判法庭 V1 — 执行 Spec（做法 A：审 features 现成单因子）

> 给 CC 执行。这是"独立筛选层"的第一版。
>
> **背景（必读）**：原计划审 194 个 RD-Agent 因子，但 §1 勘查证实它们是打板域因子、依赖 seal_*/limit_*/lhb_* 等打板字段，features.parquet（通用技术域）一个都没有 → 0 个能算，**数据域错位**。决策（Wallace 拍）：走路三——**先用 features 现成的通用技术因子把法庭建成、跑通、验证机制，那 194 个打板因子挂起，等将来主攻战车A、打板域数据到位了再用同一个法庭审。**
>
> **本版定位**：**建法庭 + 验证机制**为首要目的，不是给这批因子下严格样本外终审。通过者只标 `gate1_candidate_alpha`，**严禁标 robust_alpha**。
>
> **协作纪律**：CC 按 spec 执行、出结果、出报告，**不下"因子能不能用"的最终结论**——Wallace 拍。卡住/拿不准就停下报告，不要自己猜着改口径。

---

## 0. 受审对象 + 边界

**受审对象**：features.parquet 里**现成的单因子列**（每个技术指标列当一个因子直接审），例如 `rsi_14`、`ma_ratio_*`、`volatility_*`、`atr_ratio`、`vol_ratio_*`、`bb_position`、`price_position_*`、`macd_hist`、`upper/lower_shadow_ratio`、`body_ratio`、`up/down_streak` 等。**具体审哪些列由 §1 勘查确定**（features 里所有"像因子"的技术指标列，排除价格/量/收益/日期/代码这些原料列和前向收益列）。

> 注意：features 里很多因子有 `_rank` 截面版。同一因子的原始版和 _rank 版**二选一审**（优先审 _rank 版，因为它已是截面标准化的，更接近 IC 计算需要的形态；若只有原始版就审原始版）。§1 勘查时把这个理清，别把同一因子的两个版本都当独立因子重复审。

**只读、不动的**：
- features.parquet / labels_only.csv —— 只读
- 那 194 因子 jsonl —— 本版不碰（挂起，将来审）
- **2026 年数据 —— 本版完全不碰**（留 Final 终审），OOS 截至 2025-12-31

**本版不做的**（留 V2）：DSR、ONC 聚类、去冗余、衰减监控、2026 Final 终审、组合回测、long-short 组合、**robust_alpha 最终判定**

**输出目录**：`research/factor_court/v1/`（本版确定要建了）
- 台账：先查 `research/factor_validation/` 是否已有 `factor_conclusions_ledger.csv` 种子，**不重复建**；本版出独立的 v1 结果文件（§6），并入主台账与否 Wallace 定

---

## 1. 执行前：只读勘查（先别算 IC，做完报告）

### 1.1 把 features 里"可审的单因子列"清单确定下来
读 features.parquet 的 schema，把列分三类报告：
- **原料列**（不审）：ts_code, trade_date, open/high/low/close, *_adj, vol, amount, pct_chg 等
- **前向收益列**（不审，是标签）：return_5d/10d/20d/60d, overnight_return, intraday_return
- **可审的因子列**（审这些）：所有技术指标列。对每个，注明有没有 `_rank` 版。**给出最终受审清单**（同一因子原始/_rank 二选一后，总共多少个因子受审）

### 1.2 核查 features 因子列本身无泄漏（做法 A 特有的关键核查）
做法 A 不现算因子值（直接读 features 的列），所以泄漏风险转移到"features 当初生成这些列时有没有泄漏"。核查：
- features 的因子列是不是都用 **T 日及之前**的数据算的（没有引用未来数据）？尽量从 features 的生成脚本或列的定义判断。
- 前向收益列（return_10d 等）的算法核实一遍：return_10d 是不是 "T 日 → T+10 日的收益"这种标准前向口径，有没有未来函数。
- **若无法确认 features 列的生成无泄漏 → 报告标注"features 列生成口径未完全确认，结果按参考看"**，不阻塞，但要诚实记下来。

### 1.3 OOS 纯度说明
features 这些通用技术因子，**很可能之前的研究（v3/dragon_score 等）已在全段数据上用过/看过** → 拿 2023-2025 当 OOS 对它们可能不纯。报告里标注：`oos_purity = unknown（features 通用因子大概率被既往研究见过全段数据）`。**本版核心是建法庭、验机制，这些因子的判决当练兵参考，不当严格样本外铁证。**

**§1 勘查报告回来，确认受审清单 + 泄漏核查结果后，再进 Gate0。**

---

## 2. Gate0 — 准备因子值 + 收益 + mask（做法 A 已简化）

> 做法 A 的因子值是 features 现成列，**直接读，不现算**，所以 Gate0 比原版轻很多。重点变成"收益构造 + mask + 方向锁定"。

### Step 1：读受审因子列
按 §1.1 确定的受审清单，从 features 直接读这些列的值（每只票每个交易日）。**不现算、不做表达式解析**。

### Step 2：（已简化）覆盖率检查
features 自己的列，不存在字段缺失。仅记录每个受审因子的覆盖率（非空值/总样本），覆盖率过低的标 `insufficient_coverage`。

### Step 3：（已简化）discovery window
features 通用因子无 RD-Agent 挖掘窗口问题。统一按 §1.3：`oos_purity = unknown`。

### Step 4：（核查落地）因子值泄漏
不现算因子值，这步是 §1.2 核查结果落地：某因子列若判定生成时有泄漏嫌疑 → 标 `leakage_suspected` 并标红。否则正常进入。
**前向收益列绝不能混进因子（它们是标签）**——代码显式确保受审因子列不含任何 return_* 列。

### Step 5：构造收益标的
主收益 `return_10d_cs_demean`：
```
return_10d_cs_demean[股,日] = return_10d[股,日] − 当日全市场 return_10d 均值
```
（横截面去均值，零成本去市场涨跌偏差，不需基准指数）
辅助收益 `raw_return_10d`：直接读 features 的 return_10d。
features 已有 return_10d 直接读，不自己重算。

### Step 6：构造两套 mask
- **`universal_clean_mask`**：过滤 ST、停牌、未来收益缺失、价量异常、不可交易；**过滤涨跌停日**
- **`board_domain_mask`**：过滤 ST、停牌、未来收益缺失、严重异常；**保留涨停样本**；标记一字板/无法买入样本

> 做法 A 审通用技术因子，理论上 universal_clean_mask 是主场。但**两套都跑**对照看，且把法庭机制验全（将来审打板因子要用 board_domain_mask）。

ST 识别若 features 无显式列，从 name 前缀（ST/*ST/退）解析，报告注明近似。

### Step 7：锁定因子方向（OOS 前锁死）
优先级：
1. 因子若有公认方向先验，`factor_direction_source = prior`；但通用技术因子方向往往不唯一，更稳的是↓
2. 用 **IS(2018-2022)** 的 mean IC 符号定方向，`factor_direction_source = is_ic`
3. **OOS(2023-2025) 只验证，绝对不准用 OOS 结果定/翻方向**

记录：`factor_direction_source, factor_direction, is_ic_mean_*, oos_ic_mean_*, direction_locked_before_oos`
**`direction_locked_before_oos` 必须 True**，否则不得过 Gate1。

---

## 3. Gate1 — 样本外 t > 3.0（判决，机制不变）

### Step 8：OOS 上算横截面 Rank IC
2023-2025 每个交易日：
```
RankIC[日] = Spearman( factor_value[当日有效票], return_10d_cs_demean[当日有效票] )
```
主收益 cs_demean，辅助 raw_return_10d 也跑。两套 mask 各算一套 IC 序列。

最低样本要求（不满足标 insufficient_coverage）：
- `min_daily_stocks = 100`（某日有效票<100 不算该日 IC）
- `min_oos_ic_days = 120`（OOS 有效 IC 天数<120 不给通过）
- `min_factor_coverage_ratio = 0.3`

### Step 9：算 t 值（必须 HAC）
- `ic_t_naive = mean(IC)/std(IC)*sqrt(N)` —— 仅参考
- **`ic_t_hac` = Newey-West/HAC t，lag=10** —— **主判据**
> 用 10 日收益每天算 IC，相邻日收益重叠 9 天，IC 序列强自相关，naive t 虚高；HAC(lag=10) 校正，给诚实的 t。

### Step 10：Gate1 判定
```
覆盖率/样本不足          → insufficient_coverage
因子列疑泄漏             → leakage_suspected
方向没在OOS前锁定        → direction_unlocked
HAC t <= 3.0            → gate1_fail
HAC t > 3.0 且方向已锁   → gate1_candidate_alpha
```
> 本版 OOS 普遍 unknown，即便过 HAC t>3.0 也标 candidate_alpha + 注明"OOS 纯度 unknown，练兵参考"。

**红线：本版 verdict 严禁出现 robust_alpha。**
`gate1_candidate_alpha` 含义写清：**只过第一关（OOS t>3.0），未过 DSR/去冗余/衰减/2026终审，且本版 OOS 纯度 unknown，不等于稳健 alpha、不能直接用实盘。**

---

## 4. 两套 mask 对照解读
每因子得 universal + board_domain 两套结果，对照：都过/只 universal 过/只 board_domain 过/都不过——记进结果表。本版受审通用因子，重点看 universal；board_domain 主要把机制验全（将来审打板因子要用）。

---

## 5. 现实预期（照实出结果，不调口径求好看）
1. **这次能算的因子多**（features 现成列，不像 194 大量出局）——好事，让法庭机制完整跑一遍。
2. **过 HAC t>3.0 的可能仍不多**——HAC t>3.0 严，通用技术单因子大多 IC 很弱。**过关少甚至接近 0 都正常**，本版重点不是挑金因子是验法庭。
3. **OOS 纯度 unknown**——features 因子大概率被既往研究见过全段数据，判决当练兵参考。

**本版成功标准 = 法庭流水线（Gate0 准备 → 双 mask → 方向锁定 → HAC t 判决 → 出台账）完整跑通、机制正确、可复现可审计。不是"审出多少金因子"。**

---

## 6. 输出文件（放 `research/factor_court/v1/`）
1. **`factor_universe_audit.csv`** — §1.1 受审因子清单（哪些列受审、原始/_rank 怎么选、覆盖率）+ §1.2 泄漏核查
2. **`factor_gate1_results.csv`** — Gate1 逐因子结果：
   `factor_name, mask_type, return_type, factor_direction, factor_direction_source, valid_ic_days, valid_stock_count_mean, factor_coverage_ratio, ic_mean, ic_std, ic_t_naive, ic_t_hac, hac_lag, gate1_pass_naive_t, gate1_pass_hac_t, gate1_final_pass, verdict, fail_reason`
3. **`factor_court_v1_ledger.csv`** — 本版台账：
   `factor_name, version, source, oos_purity, best_mask_type, best_return_type, gate0_status, gate1_status, verdict, primary_evidence, secondary_evidence, fail_reason, next_action, created_at`
   verdict 只允许：`insufficient_coverage / leakage_suspected / direction_unlocked / gate1_fail / gate1_candidate_alpha`
4. **`factor_gate1_summary.md`** — 人看总结：受审多少、多少过 Gate1、双 mask 对照、OOS 纯度说明、**明确写"本版是建法庭+验机制的练兵，通过者仅 candidate_alpha、OOS纯度unknown"**
5. 附：把 **§1 勘查结论（194 因子 vs features = 0 可算，域错位）**存一份在本目录（`discovery_194_domain_mismatch.md`），留档这个发现

---

## 7. 执行顺序（每阶段可停）
1. **§1 只读勘查**（定受审清单 + 核查 features 列无泄漏 + OOS 纯度）→ **停下报告，等确认**
2. 确认后 → **§2 Gate0**（读因子列 → 覆盖率 → 收益 cs_demean → 双 mask → 锁方向）
3. → **§3 Gate1**（OOS 算 Rank IC → HAC t → 判定）
4. → **§6 出文件 + summary** → 报告

代码放 `research/factor_court/v1/` 成正式模块（会迭代到 V2）。环境用 **`D:\quant_env\.venv_court`**（CC 已建，pandas+pyarrow；不碰 .venv_qlib/.venv_rdagent/quant_platform）。

**全程**：只读 features、不碰 2026、不碰 194 因子、不下最终结论。卡住/拿不准就停下报告。
