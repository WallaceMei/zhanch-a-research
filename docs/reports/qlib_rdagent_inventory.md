# qlib_rdagent_inventory.md — qlib / RD-Agent / 自建 factor_lab 家底盘点(只读)

> 目的:为"基于 qlib+RD-Agent 搭通用多因子挖掘系统、自造严格筛选层"做动手前盘点。
> 本文件只盘点,**未装/未跑/未挖因子/未改任何东西**。盘点时间 2026-06-22。

---

## 0. 一句话结论

**挖掘层(qlib + RD-Agent)之前真跑通过——RD-Agent 跑完 200 轮产出 194 个候选因子(带 train/test Rank IC),qlib+LightGBM 数据/回测管线在 `C:\quant_project\limit_up\` 留有完整产物;但两者现在都没装在活动环境里,且只在"打板情绪"域跑过。最关键的是:三套(qlib / RD-Agent / 自建 factor_lab)没有任何一个实现严格筛选刹车——Deflated Sharpe / FDR / Bonferroni / 因子衰减监控全为零,只有基础 IС/EV/单次 IS-OOS。所以你说的"独立严格筛选层"确实得从头造,这判断成立。**

---

## 一、qlib

| 项 | 实况 |
|---|---|
| 是否安装 | **当前未安装**。`C:\quant_platform\.venv` 里 `import qlib` → ModuleNotFoundError;全盘无 qlib site-packages;无 conda 环境。 |
| 历史用过吗 | **用过**,在 `C:\quant_project\limit_up\`:`build_qlib_data.py`(建 qlib 数据)、`qlib_backtest_chart*.png`、`factor_wf_results.csv`(按年 walk-forward)、`test_predictions.csv`、`feature_importance.csv`、`lgbm_model.txt`(根目录)。 |
| 模型 | **LightGBM**(baseline IC 0.1584,截面 Rank IC);无 Alpha158/360 handler 配置痕迹——因子是自定义表达式,非 qlib 内置 handler。 |
| 版本 | **未知**(无安装、无 requirements pin) |
| 跑过什么 | 自定义因子 → LightGBM 预测 → 回测出 equity 图;限于 limit_up 打板域。 |

**qlib_data 完整性**(`C:\quant_project\qlib_data\cn_data\`):
- 标准 qlib 格式:`calendars/` + `features/` + `instruments/all.txt` + `labels/`,**格式正确、重装 qlib 后可直接用**。
- 标的:**5401**(含指数 sh000300)。
- 字段:每股 `open/high/low/close/volume/change` 的 `.day.bin`(**仅 6 个原始字段,无复权因子 bin**)。
- 时间:**2024-01-02 ~ 2026-12-31**(727,含未来占位)——**只 ~2.5 年,偏短**;真正长历史在另一套 `features.parquet`(2018-2026,非 qlib 格式)。
- → 够做 Alpha158/360(它们由 OHLCV 运行时算),但**历史短、未复权**,大规模多年挖掘要重建更长的 qlib_data。

**自定义因子/handler**:有(limit_up 的因子工作 + RD-Agent 公式用 `cs_rank/ts_zscore/ts_shift` 这类 qlib 表达式风格),但没看到 Alpha158/360 标准 handler 的固化配置。

---

## 二、RD-Agent

| 项 | 实况 |
|---|---|
| 是否安装 | **当前未安装**(`import rdagent` → ModuleNotFoundError;无 site-packages) |
| 历史跑过吗 | **跑过且跑通**,产物在 `C:\quant_project\limit_up\qlib_results\` |
| 做的是 | **因子挖掘 factor loop** |
| 跑到哪一步 | `rdagent_review_v4.md`:**200 轮 / 通过质检 112 个 / baseline LightGBM IC 0.1584 / 截面 Rank IC(Spearman 按 datetime)**;`rdagent_factors_v4.jsonl` = **194 条候选因子**(name/economic_meaning/formula/direction/fields_used/train_ic/test_ic/round/phase)。已生成人工复审文档(审核 checkbox 还空着 → 停在"待人工审核") |
| 因子质量 | Top 因子 test Rank IC ~0.10(如 market_strength_volume_retail_flow_v2:test 0.1013/train 0.0798);也有大量 test IC ≈0/负 |
| 数据域 | **limit_up 打板情绪域**字段(daily_total_limits / market_max_board / industry_limit_count / seal_strength / first_board_ratio / vol_ratio_5d…),**不是** features.csv 的通用技术字段 |
| 数据源 | Tushare(`C:\quant_platform\.env` 的 TUSHARE_BASE_URL)取原始数据;qlib_data 供 qlib |
| LLM 接口 | **当前文件里找不到 RD-Agent 自身的 LLM 配置**(运行环境已不在);项目别处(`limit_up/after_market.py`)用 **DeepSeek** 做 AI 复盘,RD-Agent 实际接的模型**存疑,需你确认** |

→ RD-Agent 不是"没碰过",而是**完整跑过一轮 V4(200 轮→194 因子→生成复审文档),卡在人工审核**;但环境没了、且只在打板域跑过。

---

## 三、quant_platform/factor_lab(自建)

| 项 | 实况 |
|---|---|
| 性质 | **独立自建**,纯 pandas,**不基于 qlib** |
| harness 实现 | `backtest_engine.py`(BacktestEngine.run + quick_baseline_run)、`data_loader.py`(load_signals + **split_walk_forward**)、`target_functions.py`(compute_targets / `_pnl_ev` 命中率+EV)、`tp_sl_grid_search.py`(止盈止损网格 run_grid) |
| factors/library.py | **23 个因子**(V2_FACTORS + WEB_DERIVED_FACTORS),schema = id/name/category/cols_needed/**filter_fn(df→df' 二元过滤)**/source/corr_with_pnl。类别:选股/竞价/盘口/环境/退出/V2 反推 |
| 24 因子原件 | 在 `C:\quant_project\limit_up\factor_library.py`(FactorLibrary 类,add_factor 带 direction/strength/verified_date)。factor_lab/library.py 是它的 v1 适配 |
| 24 因子验证记录 | **有**:`limit_up/factor_report.md`(2026-04-05,24 因子,每个带 方向/强度(corr 如 -0.043/+0.043)/效果(胜率/大亏率影响));`factor_wf_results.csv` 按年 walk-forward(year/factor/ret/wr/n) |
| 实验记录 | `factor_lab/experiments/` **55 个实验**(r1_A…r3_D×多版),每个 log.md 有 metrics_full + **metrics_train(IS)/metrics_test(OOS)/diff** + overfit_risk 标记;窗口 2025-08~2026-04(302 dataset),**单次切分** |

**与 qlib 的重复**:功能上**两套并行、范式不同**——
- qlib 路线:ML(LightGBM)+ 截面 Rank IC + 连续因子;
- factor_lab 路线:**二元过滤规则 + EV/命中率 + 止盈止损网格**(打板出场导向)。
- 重叠点仅在"都做回测 + 都有 IS/OOS 概念",但实现各自独立,不是同一套。

---

## 四、三套关系 + 缺口评估

### 关系/重复
```
原始数据 ──┬─ Tushare ──► limit_up/build_qlib_data.py ──► qlib_data/cn_data(qlib 格式, 2024-2026)
           │                                              │
           │                                              ├─► qlib + LightGBM(limit_up)──► factor_wf / 回测图
           │                                              └─► RD-Agent factor loop ──► 194 候选因子(qlib_results)
           │
           └─ features.parquet(2018-2026, 非 qlib)──► (技术因子, 见 local_data_inventory)

自建 factor_lab(quant_platform, 不依赖 qlib)──► 23/24 过滤因子 + EV网格 + 55 实验(打板出场域)
```
- **没有"重复造同一个东西"**,但**有域重叠 + 范式分裂**:qlib/RD-Agent 在打板域做 ML 因子,factor_lab 在同域做规则过滤因子,各跑各的,结论没汇到一处。

### ★ 关键:有没有严格筛选刹车?
**没有。三套全无。** 专项扫 `deflated / bonferroni / benjamini / fdr / 多重检验 / family-wise / p_adjust` → 只命中 .git 包、akshare 库、.venv,**自建代码零实现**。

| 能力 | qlib(limit_up) | RD-Agent | 自建 factor_lab |
|---|---|---|---|
| 基础 IC | ✅ Rank IC | ✅ train/test IC | ⚠️ 用 EV/命中率,非 IC |
| IS/OOS | ⚠️ 按年 wf(ret/wr) | ✅ 单次 train/test | ✅ 单次切分(8 个月窗口) |
| 回测 | ✅ | ✅(经 qlib) | ✅(自建引擎) |
| **多重检验校正(Deflated Sharpe/FDR/Bonferroni)** | ❌ | ❌(200 轮挖 194 因子,**完全没做多重检验校正**) | ❌ |
| **因子衰减/半衰期监控** | ❌ | ❌ | ❌ |
| **PBO / 过拟合概率** | ❌(只有 overfit_risk 启发式标记) | ❌(112 通过质检是启发式,非统计) | ❌(overfit_risk 启发式) |
| 滚动多折 walk-forward | ⚠️ 按年但无校正 | ❌ | ❌ 单次 |

→ RD-Agent 的"200 轮挖 194 因子"本身就是**严重多重检验场景**(挖得越多,假阳性越多),而现状**没有任何统计校正**——这正是最大风险点。

### 诚实评估
- **挖掘层(qlib+RD-Agent):现成度高**。RD-Agent factor loop 真跑通过、留有 194 因子 + 复审框架;qlib 数据/LightGBM/回测管线齐。**复用成本主要是工程**:① 重装 qlib + RD-Agent(当前都没装)② 重建 LLM 配置(接口存疑)③ 把数据域从"打板情绪"扩到通用全市场(现成 features.parquet 2018-2026 可做底,但要接进 qlib handler)④ qlib_data 重建更长历史。
- **筛选层(严格刹车):确实得从头造**。Deflated Sharpe / FDR-Bonferroni / 因子衰减 / PBO 一个都没有,现有只有"基础 IC/EV + 单次 IS-OOS + 启发式 overfit 标记"。你把"独立严格筛选层"定为系统核心、且认为要自造——**与盘点结论完全一致,这是真缺口,不是重复劳动**。

### 给系统设计的事实输入(非建议,仅供你拍板)
1. 挖掘层可复用 RD-Agent 的因子表达式产出格式(jsonl: formula/train_ic/test_ic/fields)作为筛选层的输入接口。
2. 筛选层应卡在 RD-Agent"产因子"与"人工审核"之间(现在那 194 因子就是停在人工审核、无统计刹车的状态)。
3. 数据底:通用因子用 features.parquet(2018-2026 全市场,见 local_data_inventory.md);打板域用 limit_up/qlib_data。两套别混口径。

---

## 五、盘点边界
- 全程只读;未安装/卸载、未跑任何 loop、未挖因子、未改/移动/删除任何文件。
- qlib/RD-Agent 版本未知(均未安装,无 pin);RD-Agent 所接 LLM 未在现存文件中确证(运行环境已不在)——这两点需你确认或重建时确定。
- 追加核实:qlib/rdagent 不在当前 `.venv`,**也不在旧 venv 备份**(`_organize_log/old_venv_backup/old_dist_info_dirs.txt`)→ 安装环境彻底无痕;但 `C:\quant_project\test_qlib.py` 确有 `qlib.init(provider_uri='...qlib_data\cn_data', region='cn')`,qlib 确在此数据上跑过。RD-Agent 无任何安装/克隆痕迹(仅产物在),鉴于 `QMT_clean/docker/` 存在,**疑似当年跑在 Docker 容器内**(重建时优先排查 Docker 方案)。
- `.env`/`local_config.json` 仅看键名与非密钥值,**未读取/未记录任何密钥**。
