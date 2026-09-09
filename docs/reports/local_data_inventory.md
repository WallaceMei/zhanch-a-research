# local_data_inventory.md — 本地数据家底盘点(只读)

> 目的:评估能否在本地做"全市场 / 3-5 年 / 可 IS-OOS"的大规模因子挖掘。
> 本文件只盘点,**未挖因子、未写框架、未动/未改任何数据**。
> 盘点时间:2026-06-22。盘点范围:`D:\quant_project\`、`C:\quant_project\`、`C:\quant_platform\`、`D:\量化策略\`。

---

## 0. 一句话结论

**本地已有一份现成的全市场日线因子面板(`C:\quant_project\features.parquet`,2018-07 ~ 2026-04,约 7.7 年,含复权价 + ~30 技术因子 + 三重门标签),足以支撑"价量类技术因子"的大规模 IS/OOS 挖掘;再加 2020-2026 全市场分钟数据(~134GB)可做日内因子。但缺基本面(市值/换手/行业/估值)、缺 ST/停牌显式标记、复权口径待核、基准指数只有沪深300——这几项要从聚宽补,否则做不了规模/价值/行业中性类因子。**

---

## 1. 行情数据源清单

| 源 | 路径 | 格式 | 频率 | 覆盖范围 | 时间跨度 | 体积 |
|---|---|---|---|---|---|---|
| **日线因子面板(主力)** | `C:\quant_project\features.parquet`(及同内容 `.csv`) | parquet / csv | 日线 | 全市场(.SH/.SZ) | **2018-07-04 ~ 2026-04-03** | parquet 4.0G / csv 10G |
| 标签 | `C:\quant_project\labels_only.csv` | csv | 日线 | 同上 | 同上 | 354M |
| qlib 日线 | `C:\quant_project\qlib_data\cn_data\` | qlib .bin | 日线 | **5401** 标的(含指数 sh000300) | **2024-01-02 ~ 2026-12-31**(727 日历日,含未来占位) | ~小 |
| **分钟线(CSV)** | `D:\quant_project\minute_2020 … minute_2026\` | csv(每股每年一个) | 1 分钟 | 全市场 sh+sz(**无北交所 bj**) | 2020 ~ 2026 | **~134G**(各年 18-24G) |
| 分钟线(parquet 副本) | `D:\quant_project\data_store\minute_v2\{CODE}\{year}.parquet` | parquet | 1 分钟 | 同上 | 2020 ~ 2026 | 紧凑 |
| tick | `D:\quant_project\data_store\tick_v1\{YYYYMMDD}\` | 按日 | tick | —— | **仅 2026-03-25 起**(极少) | 小 |
| 标的基础信息 | `C:\quant_platform\data\stock_basic.csv` | csv | —— | 全市场 | —— | 129K |

另:`C:\quant_platform\factor_lab\`(已有因子研究框架:`harness/{backtest_engine,data_loader,target_functions,tp_sl_grid_search}.py` + `factors/library.py` + experiments/combinations/proposals)——**基础设施已存在一部分**。

---

## 2. 有没有全市场日线?分钟能不能聚合成日线?

**有现成全市场日线**:`features.parquet` 就是,不需要从分钟聚合。覆盖全市场、2018→2026、含复权与原始价。日线因子直接用它即可。

**分钟→日线聚合(若要自建)**:可以,但有一个硬坑——
- 分钟数据**每日首 bar = 09:30:00,无 09:25 集合竞价 bar**(已核:首 bar 的 O=C=H=L)。
- 所以聚合出的"开盘价" = 09:30 第一分钟开盘,**不等于真实集合竞价开盘价**。涉及 `开盘价/隔夜跳空/open_ratio` 的因子会失真。
- 收盘价 = 15:00 bar,含尾盘集合竞价,**可靠**。最高/最低/成交量/成交额聚合可靠。
- **结论**:日线因子别用分钟聚合(用 features 的 open),分钟数据留给"日内/微结构"因子。

---

## 3. 各源实际字段

**features.csv/parquet(76 列)**:
- 价:`open/high/low/close`(原始)+ `open_adj/high_adj/low_adj/close_adj`(复权)
- 量:`vol`、`amount`、`pct_chg`
- 收益:`return_5d/10d/20d/60d`、`overnight_return`、`intraday_return`
- 技术因子:`ma_ratio_*`、`volatility_*`、`atr_14d/atr_ratio`、`vol_ratio_*`、`vol_price_corr_10d`、`amount_ratio_5d`、`rsi_14`、`macd_hist`、`bb_position`、`upper/lower_shadow_ratio`、`body_ratio`、`up/down_streak`、`price_position_10/20/60d`
- 以及上述大部分因子的 **截面 `_rank` 版**(共约 30 个 rank 列)
- ❌ **无**:换手率、市值/流通市值、行业、PE/PB 等基本面/规模字段

**labels_only.csv**:`label`、`barrier_type`、`barrier_return`、`holding_days`(三重门标签,ML 直接可用)

**minute CSV(11 列)**:`时间,代码,名称,开盘,收盘,最高,最低,成交量,成交额,涨幅,振幅` —— 有 OHLCV+成交额,❌ 无换手率/市值

**qlib cn_data**:每股 `open/high/low/close/volume/change` 的 `.day.bin`(6 字段),原始价

**stock_basic.csv**:仅 `ts_code,name` —— ❌ 无行业/市值/上市日等

---

## 4. 复权

| 源 | 复权情况 |
|---|---|
| features | **同时有原始价 + `*_adj` 复权价** → 可复权。⚠️ 但刻度存疑:平安银行 2018-07-04 原始 close 8.61 vs `close_adj` 915.32(约 106 倍),像"上市以来后复权(hfq)"的累积因子。**用前先核对复权口径**(算收益用比率不受影响,但绝对价别直接用)。 |
| 分钟 CSV | 看来是**不复权**(原始成交价,无复权列) |
| qlib | `.bin` 为原始 OHLCV + `change`,**无复权因子** → 跨除权日需自行处理 |

→ 想要干净复权:优先用 features 的 `*_adj`(核对口径后),或从聚宽取复权因子。

---

## 5. 数据质量

- **缺失/停牌**:分钟数据停牌日表现为缺当日 bar 或零成交量 bar(已见 14:59 量=0 的占位)。features 是否已剔停牌/前向填充**需抽查验证**。
- **ST 标记**:无显式 ST 列。只能从 `name` 字段前缀("ST"/"*ST")推断 → 需自行解析,且历史 ST 状态是否随时点变化未知。
- **北交所**:分钟数据 sh+sz 两类,**无 bj(北交所)** → 全市场实为"沪深全市场",不含北交所。
- **退市股**:features 含已退市票与否未核(survivorship 风险点),**需验证是否包含退市股的历史**,否则有幸存者偏差。
- **基准指数**:qlib 有 `sh000300`;做超额/IC 常用的中证500(000905)、中证1000(000852)**本地是否齐全需确认**(seg1 当时是从聚宽取 000852)。

---

## 6. 诚实评估:够不够支撑"全市场 / 3-5 年 / IS-OOS 的大规模因子挖掘"?

### ✅ 够的部分(价量/技术类因子)
- **全市场**:features 覆盖沪深全市场(~5000+,含主板/创业板/科创板)。
- **跨度**:2018-07 ~ 2026-04 ≈ **7.7 年**,远超 3-5 年要求,IS/OOS 切分宽裕(如 IS 2018-2022 / OOS 2023-2026)。
- **现成因子 + 标签**:~30 个基础技术因子(含截面 rank)+ 三重门标签,**可直接进 IS/OOS 与 IC/分层流程**,不用从零造数据。
- **日内因子**:2020-2026 全市场分钟(~134GB)支撑微结构/日内因子。
- **基础设施**:`factor_lab/harness` 已有 backtest_engine / data_loader / target_functions / grid_search,不必从零搭框架。

### ❌ 缺口(必须补,否则这几类因子做不了)
| 缺口 | 影响 | 补法 |
|---|---|---|
| **基本面/规模**:市值、流通市值、换手率、行业、PE/PB | 做不了规模因子、换手因子、行业中性化、价值因子 | 从聚宽下载(`get_fundamentals` / `valuation` / 行业分类 / 换手率) |
| **复权口径未核** | 绝对价不可信,跨除权日收益可能错 | 核对 features `*_adj` 约定,或取聚宽复权因子 |
| **ST/停牌/退市显式标记** | 过滤不干净 → 因子被脏样本污染 + 幸存者偏差 | 取聚宽 ST 列表/停牌表/退市表,或核 features 是否已含退市股 |
| **基准指数齐全性** | 超额/IC 口径(中证500/1000)可能缺 | 本地确认,缺则从聚宽补 000905/000852 |
| **北交所缺失** | 若要全市场含北交所,缺一块 | 看是否需要;不需要则忽略 |
| **数据新鲜度**:features 到 2026-04、分钟到 2026 | 近两个月数据需刷新 | 增量从聚宽/数据源补 |

### 结论
- **价量/技术因子的大规模 IS-OOS 挖掘:本地数据基本够,可以现在就在 `features.parquet` 上开干**(7.7 年全市场 + 现成因子 + 标签 + 已有 harness)。
- **基本面/规模/价值/行业类因子:本地不够**,必须先从聚宽补 市值/换手/行业/估值 + 复权因子 + ST/停牌/退市表。
- **优先级建议**:先用 features 做技术因子挖掘(零额外成本);要扩到全因子谱系,再排一次聚宽下载补齐 §6 缺口表。

---

## 7. 备注
- 读取性能:用 `features.parquet`(4G)而非 `.csv`(10G),加载快得多。
- `features.parquet` 与 `features.csv` 内容一致(同一套);`labels_only.csv` 单独存标签。
- 本盘点未读 parquet 内部 schema(本地无 pandas/pyarrow);列结构以同内容的 `features.csv` 表头为准。
- 全程只读,未改/未移动/未删除任何数据文件,未写任何挖因子或框架代码。
