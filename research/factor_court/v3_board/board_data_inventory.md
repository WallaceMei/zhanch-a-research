# 打板域数据勘查:能否给 194 因子凑出法庭可用的稠密面板

> 只读勘查,未建面板、未算因子、未改数据。环境 .venv_court。
> 目的:评估 194 个 RD-Agent 打板因子(依赖 26 个打板字段)能否在"全市场×全历史×每日"稠密面板上,用因子审判法庭审。
> 日期 2026-06-22。

---

## 0. 一句话结论

**字段层面 194 因子全部可算(26 个依赖字段在 qlib_data 里全有,4837/5401 股覆盖);但数据结构上撞两堵墙,法庭现有稠密逐日 IC 口径直接用不了:**
1. **时间墙**:打板 qlib_data 只有 **2024-01 ~ 2026-12 日历、且 2026 几乎为空**,实际可用 ≈ 2024-2025 两年 → **切不出 IS(2018-2022),也没有 2026 终审数据**。
2. **稀疏墙(最致命)**:数据是**事件稀疏**结构——每股中位仅 **8 个事件日**有值,每日横截面中位 **53 股**,**≥100 股/日的只有 69/727 天**。这不是稠密日面板,是涨停/上榜候选池的事件日志。法庭默认 `min_daily_stocks=100 / min_oos_ic_days=120` 会废掉 ~90% 的天。

→ **不是"能审几个因子"的问题(字段都齐),而是"法庭逐日稠密 IC 口径不适用于这种事件稀疏数据"。** 要审这 194 个,法庭口径得为打板场景重设计,不能照搬 features 那套。**先停下报告,等你和 Wallace 定方向。**

---

## 1. 字段来源(26 依赖字段,逐字段)

194 因子 `fields_used` 去重 = **26 字段**。全部能在 `C:\quant_project\qlib_data\cn_data\features\{股}\<字段>.day.bin` 找到。

| 字段 | qlib_data .bin | 覆盖股数 | 性质 |
|---|---|---|---|
| seal_strength / seal_ratio / seal_minutes | 有 | 4837 | 封板强度,**仅涨停日有意义** |
| daily_total_limits / market_max_board / industry_limit_count / first_board_ratio | 有 | 4837 | 市场/板块涨停热度,**市场级、本可每日** |
| limit_turnover / open_times / on_lhb | 有 | 4837 | 涨停换手/开板次数/是否上榜,事件性 |
| lhb_net / inst_net | 有 | 4837 | 龙虎榜/机构净额,**仅上榜日有** |
| float_mv_yi | 有 | 4837 | 流通市值,**本可每日** |
| return_3d / rsi_14 / vol_ratio_5d / bb_position / up_streak / price_position_60d / intraday_range / morning_vol_ratio / tail_vol_ratio / vol_vs_prev / kdj_j / retail_line / retail_line_change | 有 | 4837 | 价量技术,**本可每日** |

**结论**:26 字段在 qlib_data 里**一个不缺**(`miss=无`)。所以从"字段齐不齐"看,194 因子**全部**可进入计算。问题在数据结构(见下),不在字段。

---

## 2. 能不能凑成稠密面板

### 覆盖范围
- features 目录 5401 个,板块字段覆盖 **4837 股**(近全市场沪深)。注册表 all.txt = 4838。覆盖面够。

### 时间跨度 ★墙1
- qlib 日历:**2024-01-02 ~ 2026-12-31,727 日**。
- 分年每日有值股数中位:**2024=82,2025=53,2026=0**。→ **2026 实质为空**,实际数据 ≈ 2024-2025。
- **没有 2018-2022 的打板数据** → 法庭 IS(2018-2022)/OOS(2023-2025) 的标准切分**无法成立**;最多 2024 当 IS、2025 当 OOS(各约 1 年,极短),2026 终审无数据。

### 稠密度 ★墙2(最关键)
- seal_strength 总非nan行 = **44,331** / (727日 × 4837股 ≈ 351万格) → 稠密度 **≈1.3%**。
- **每股事件日数**:中位 8、均值 9.2、最大 48;1–5 天的有 1687 股,6–20 天 2790 股。
- **每日横截面规模**:中位 **53 股**、均值 61;**≥100 股:仅 69/727 天**;≥50:402 天;≥30:503 天。
- 关键实证:同一股 `seal_strength 非nan 天数 == close 非nan 天数`(如 9=9、11=11)→ **数据只在该股的事件日(涨停/候选日)存在,其余交易日整行没有**。
- → **这是事件稀疏日志,不是稠密日面板。** 法庭的"每日全市场横截面 Rank IC + 每日≥100股"口径在这种数据上**绝大多数天不成立**。

---

## 3. 前向收益(T+N)

- 打板事件行的前向收益**可以复用 features 那套**:features.parquet 是稠密的(5120 股,2018-2026,有 `close_adj`),对某股某事件日 T,直接取 `close_adj[T+10]/close_adj[T]-1`。2024-2025 的事件日都在 features 覆盖内 → **可用**。
- ⚠️ **代码格式不一致**:qlib_data 用 `sh600006`,features 用 `600006.SH` → 复用前需做代码映射(一行转换,非障碍,但要做)。
- 备选源:`limit_up\daily_recent.csv`(113MB 稠密日线)、`all_stocks_daily.csv` 也能算前向收益。
- 结论:前向收益**不是瓶颈**,features 或 daily_recent 都能供;只是要对齐代码格式 + 注意复权口径(features `*_adj` 口径存疑那条仍适用)。

---

## 4. 数据源是否还在 / 能否重拉、稠密化

builder = `limit_up\build_qlib_data.py`,把 **`limit_up\limit_up_features.csv`(稀疏板块特征)+ `all_stocks_daily.csv`(稠密日线)** 合并成 qlib bin。
原始源**大体还在**:
- `limit_up\limit_up_features_backup.csv`(15MB)、`dragon_tiger.csv`/`dragon_tiger_detail.csv`(3.6/33MB,龙虎榜=lhb_net/inst_net 源)、`limit_list.csv`/`limit_list_history.csv`(涨停列表=seal/daily_total_limits 源)、`daily_recent.csv`(113MB 稠密日线)、`minute_features.csv`(8MB)。
- Tushare `phase1_download.py` 在(含 token),理论可重拉(token 是否仍有效未测)。

**能否稠密化(把 26 字段补成每股每天都有)**:**部分能,部分本质不能**——
- ✅ **可稠密**:float_mv_yi(市值)、return_3d、rsi_14、vol_ratio_5d、bb_position、price_position_60d、daily_total_limits / industry_limit_count / market_max_board(市场/板块级,每天都有)等——这些从 daily_recent.csv / Tushare 每日都能算。
- ❌ **本质事件性、无法对非事件日稠密化**:seal_strength / seal_ratio / seal_minutes / open_times / on_lhb / lhb_net / first_board_ratio——**一只票没涨停/没上榜的那天,"封板强度""龙虎榜净额"压根不存在**(强行填 0/NaN 会改变因子语义)。这些因子**本来就只在涨停候选池里才有定义**。

---

## 5. 诚实评估

- **能审几个(字段齐)**:194 个**全部**字段齐(26 字段全在)。字段不是瓶颈。
- **数据是稠密还是只涨停日**:**只事件/涨停日**(稠密度 1.3%,每股中位 8 天,每日中位 53 股)。**法庭的稠密逐日 IC 口径不适用。**
- **时间**:仅 2024-2025 可用(2026 空、无 2018-2022)→ 切不出标准 IS/OOS,也无 2026 终审数据。
- **缺的字段能不能补**:字段不缺;缺的是"稠密度"和"历史长度"。市场/价量类可稠密化、可向前补历史(daily_recent/Tushare);但 seal_*/lhb_* 类**本质事件性,补不出非事件日的值**。

### 给决策的三条路(只列,不替你拍)
1. **为打板场景重设计法庭口径**(推荐方向):不强求"全市场每日≥100股稠密 IC",改成**事件研究 / 涨停候选池内的横截面**——每日样本就是当天的涨停候选(几十只),前向收益用 features close_adj 算,IC 在这个小池内算,门槛(min_daily_stocks)按池子实际规模调。机制(FDR/去冗余/衰减)可沿用。代价:口径变了,统计功效低(每日样本小)。
2. **先稠密化能稠密的字段、向前补历史**,只审"可稠密"那部分因子(放弃 seal_*/lhb_* 纯事件因子)——但那样审的就不是"打板因子"的核心了,意义打折。
3. **暂缓审 194 打板因子**,认定当前打板数据(2024-2025、事件稀疏)不足以支撑严格 IS/OOS 法庭,先补数据/补历史再说。

---

## 6. 边界
只读 jsonl + qlib_data(.bin 用 numpy 手动解析,未装/未用 qlib)+ 列了 limit_up 源文件清单;**未建面板、未算因子值、未跑 IC、未改任何数据、未碰 features 写入**。代码格式映射、复权口径、Tushare token 有效性均为"待确认"项,未实测。
