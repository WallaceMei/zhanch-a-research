# 打板 26 字段数据补长可行性:miniQMT(xtdata) + AKShare

> 只评估 + 最小连通测试。**未新装任何包、未大批量拉数据、未建模块、未改数据。**
> 目标:Tushare 已不可用,评估能否用 miniQMT(xtdata 优先)+ AKShare(+ 分钟自算)把 194 打板因子依赖的 26 字段补成"全市场×长历史×每日"面板,支撑因子审判法庭。
> 环境:xtdata 走运行中的国金 MiniQMT 客户端;AKShare 用**已装的 quant_platform/.venv(1.18.60),未新装**。日期 2026-06-22。

---

## 0. 一句话结论

**两源都连得通,但补不齐到 2018+:价量/市值/龙虎榜类(约 18/26)能补到 2018+;封板微观 + 日内 + "散户线"类(约 8/26)补不到 2018——而这 8 个里恰好含 `seal_strength`(145/194 因子用)和 `retail_line_change`(142/194 因子用)两个被绝大多数因子依赖的字段。** 结论:**打板模块的可用历史现实是 2020+(分钟可算的)/ 近端(真封单需 tick·L2),做不了严格 2018-2022 IS;应按"短样本保守"设计,而非严格三段切分。** 且 `retail_line` 来源不明、`seal_strength` 需要订单簿封单——这两个是补长前必须先解决的卡点。

---

## 1. miniQMT(xtdata)实测

### 连通(最小测试)
- **客户端必须开着**:`XtMiniQmt.exe` 当前在运行(PID 实测在跑);`from xtquant import xtdata` 成功(xtquant 在 `D:\国金QMT交易端模拟\bin.x64\Lib\site-packages`,有 cp310 pyd,.venv_court 3.10 可导入)。
- `get_instrument_detail("600000.SH")` 返回正常(浦发银行)。
- ⚠️ xtdata 只读**本地已下载**数据:首测 2018 日线返回 0 行,`download_history_data` 后才有 → 用前需逐段下载(增量,非现成)。

### 历史深度(1 股最小探测,非批量)
- **日线 K 线:最早 2005-01-04,最晚 2025-12-31(600000.SH 共 5101 行)** → 价量类字段补到 2018+ **毫无压力**。
- **tick:可下**(近端实测 9992 行/数日);但 tick 历史深度有限(QMT 通常只留近端),**不覆盖 2018-2019**。
- **FloatVolume(流通股本)**:`get_instrument_detail` 直接给(实测 281 亿股)→ float_mv 可算;但这是**当前快照**,历史流通股本会变(解禁/增发),长历史精确 float_mv 需历史股本(xtdata 不直接给)→ 近似可、精确有 caveat。

### xtdata 能直接/间接提供的字段
- ✅ **价量(K线可算)**:return_3d / rsi_14 / vol_ratio_5d / bb_position / up_streak / price_position_60d / vol_vs_prev / intraday_range / kdj_j —— 2005+。
- ✅ **市值**:float_mv_yi(FloatVolume × close,当前股本 caveat)。
- ✅ **涨停/市场级**(从全市场日线自算:涨停=close≥涨停价):daily_total_limits / market_max_board / industry_limit_count(需行业映射)/ first_board_ratio / limit_turnover —— 2018+。
- ❌ **龙虎榜**:xtdata **无** lhb_net/inst_net 原生字段 → 走 AKShare。
- ❌ **封板微观**(seal_strength/seal_ratio/seal_minutes/open_times):xtdata 无现成字段。seal_strength=封单金额/流通市值,**封单金额是订单簿(L1 买一量@涨停价),日线/分钟 OHLCV 都没有**,只能从 **tick·L1(近端)**或东财封板资金(见 AKShare)取;seal_minutes/open_times(封板时长/炸板次数)需**分钟/tick 盘中**自算。

---

## 2. AKShare 实测(补 miniQMT 缺的)

- **未新装包**:AKShare 1.18.60 已在 `quant_platform/.venv`,只读调用。
- ✅ **龙虎榜 `stock_lhb_detail_em`:连通且历史到 2018**(实测 20180102-03 返回 102 行,20260115-16 返回 199 行)。列含 代码/名称/上榜日/收盘价/涨跌幅/**龙虎榜净买额** → 可供 **lhb_net / inst_net / on_lhb,补到 2018+**(更早大概率也有,未深探)。
- ⚠️ **涨停板池 `stock_zt_pool_em`:本测返回空**(20260116 / 20200102 / 20180102 三个日期都 0 行、空列)。原因未定(东财接口在此 akshare 版本疑似失效/被限,或需换函数)。**未能确认**它能否提供封板资金/封板时间/炸板次数;按 AKShare 文档该接口本就**只约 2020+**,即便修好也补不到 2018。
- 其它(未实测,按文档):AKShare 有 `stock_lhb_*` 系列(龙虎榜机构席位 → inst_net 更细)、行业板块等,可作补充。

---

## 3. 两源结合:26 字段逐个标 + 历史深度

| # | 字段 | 来源 | 能补到 | 备注 |
|---|---|---|---|---|
| 1 | return_3d | xtdata K线 | **2018+** | 2005+ |
| 2 | rsi_14 | xtdata K线 | **2018+** | |
| 3 | vol_ratio_5d | xtdata K线 | **2018+** | |
| 4 | bb_position | xtdata K线 | **2018+** | |
| 5 | up_streak | xtdata K线 | **2018+** | |
| 6 | price_position_60d | xtdata K线 | **2018+** | |
| 7 | vol_vs_prev | xtdata K线 | **2018+** | |
| 8 | intraday_range | xtdata K线 | **2018+** | (high-low)/prev |
| 9 | kdj_j | xtdata K线 | **2018+** | |
| 10 | daily_total_limits | xtdata 全市场自算 | **2018+** | 市场级 |
| 11 | market_max_board | xtdata 全市场自算 | **2018+** | 连板高度 |
| 12 | industry_limit_count | xtdata + 行业映射 | **2018+** | 需行业表 |
| 13 | first_board_ratio | xtdata 自算 | **2018+** | |
| 14 | limit_turnover | xtdata K线+股本 | **2018+** | |
| 15 | float_mv_yi | xtdata FloatVolume×close | **2018+△** | 历史股本 caveat |
| 16 | lhb_net | **AKShare 龙虎榜** | **2018+** | 实测到 2018 |
| 17 | inst_net | **AKShare 龙虎榜(机构席位)** | **2018+** | |
| 18 | on_lhb | **AKShare 龙虎榜** | **2018+** | 是否上榜 |
| 19 | morning_vol_ratio | 分钟自算 | **2020+** | 本地分钟 2020-2026 |
| 20 | tail_vol_ratio | 分钟自算 | **2020+** | 同上 |
| 21 | seal_minutes | 分钟/tick 自算 或 zt_pool | **2020+** | 盘中封板时长 |
| 22 | open_times | 分钟/tick 自算 或 zt_pool | **2020+** | 炸板次数 |
| 23 | seal_ratio | tick·L1 / zt_pool | **近端/2020+** | 需封单 |
| 24 | **seal_strength** | **tick·L1(封单) / zt_pool** | **近端/2020+ ⚠️** | **145/194 因子用;封单=订单簿,OHLCV 无** |
| 25 | retail_line | **来源不明** | **? 两源都无现成** | 自定义"散户线" |
| 26 | **retail_line_change** | **来源不明** | **? 两源都无现成** | **142/194 因子用** |

汇总:
- **能补到 2018+:18 个**(1-18,其中 float_mv 有股本 caveat)。
- **只能到 2020+:4 个**(19-22,分钟自算)。
- **只能近端/2020+ 且技术上难(需订单簿封单):2 个**(seal_ratio、seal_strength)。
- **两源都没有/来源不明:2 个**(retail_line、retail_line_change)。

### 从分钟自算封板强度的可行性(你有 D:\quant_project\minute 2020-2026)
- 分钟 OHLCV 能算:morning/tail 量比、封板时长(连续封死的分钟数)、开板次数(涨停→打开→回封的次数)→ **2020+ 可近似**。
- 分钟 OHLCV **不能**直接算 `seal_strength`(封单金额):封单是涨停价上的买一挂单量,属**订单簿/L2**,分钟 K 线没有。只能用 **tick·L1 买一量**近似(xtdata tick,近端)或东财封板资金(zt_pool,2020+,本测还没连通)。
- **2018-2019 没有本地分钟数据** → 这两年连"分钟自算"的封板/日内字段都做不出。

---

## 4. 诚实评估

### 26 字段实际补长
- **补到 2018+:18 个**;**只能近几年(2020+/近端):8 个**(含 seal_strength、retail_line_change 这两个高频依赖字段)。

### 打板模块的可用历史(现实)
- 受**最受依赖的字段**约束:`seal_strength`(145/194 用)最早只能 **2020+(且真封单需 tick·L2,可能仅近端)**;`retail_line_change`(142/194 用)**来源未定**。
- 所以**整套 194 打板因子的可用历史现实是 ~2020+,不是 2018+**;若坚持要 seal_strength 的真封单口径,可能进一步缩到近端(tick 覆盖年限)。当前 qlib_data 那套是 2024-2025 稀疏;补长后**乐观也就到 2020-2025**(分钟可算的字段),且 seal_strength/retail_line 仍是卡点。

### 设计判断:严格三段切分 还是 短样本保守?
**→ 应按"短样本保守"设计,不要硬上严格 2018-2022 / 2023-2025 / 2026 三段。** 理由:
1. 核心事件字段(封板/散户线)补不到 2018,强行三段会让 IS 段缺最关键因子、口径不一致。
2. 现实最长可用 ≈ 2020-2025(还得先解决 seal_strength 订单簿来源 + retail_line 来源)。在 ~5 年、且前段字段不全的数据上做"严格样本外铁证"功效不足。
3. 务实路径(建议,非拍板):
   - 先**只用能补到 2018+ 的 18 个字段**的子集因子,做一版较长样本的法庭(这批因子才谈得上 2018-2022 IS);
   - 封板/散户线类因子单独走**短样本(2020+/近端)+ 保守统计 + 明确标注样本短**;
   - `retail_line` 必须先查清来源(原策略怎么算的),否则 142 个依赖它的因子无法复现;
   - 真 `seal_strength` 若要,先定封单数据源(tick·L2 近端 or 东财 zt_pool 2020+),并接受其历史短。

---

## 5. 边界 / 卡点
- 最小测试:xtdata 仅下了 1 股日线(2005-2025)+ 近端 tick 探深度;AKShare 仅 2 个小窗口龙虎榜 + 3 个日期涨停池。**未批量拉、未建面板、未改数据、未新装包**。
- 待解卡点(报你,未自行处理):① `stock_zt_pool_em` 返回空,需排查(换函数/版本/反爬);④ xtdata 历史股本(精确 float_mv)未实测。(②③ 已在 §6 查清,见下。)

---

## 6. 追加:retail_line / seal_strength 定义溯源(只读查代码)

> 前提修正(Wallace):打板因子短周期易失效,**只需近期数据(2024-2025 甚至更近)**,重点是"现在能不能算出来",不是补到 2018。

### retail_line / retail_line_change —— ✅ 近期完全可复现(之前误判"来源不明")
- 定义(`limit_up/nuclear_button_qmt.py:128`,RETAIL_PERIOD=60):
  ```
  retail_line(stock,date) = 100*(HHV(high,60) - close) / (HHV(high,60) - LLV(low,60))
  ```
  即"散户线"= 当前收盘在 60 日高低区间里的位置(0=贴 60 日高,100=贴 60 日低),前复权日线算。
- `retail_line_change` = retail_line[T] − retail_line[T_prev](`nuclear_button_qmt.py:202` 用 `ra-rb`;特征表 `unified_strategy_backtest.py:827` 落 `retail_line_change`)。
- **它是纯 K 线价格指标,不依赖任何特殊数据源** → **用 miniQMT 日线(high/low/close,60日,前复权)近期直接可算,零障碍**。之前报告把它列"来源不明"是错的,特此更正。

### seal_strength —— ✅ 近期可复现(tick·L1 确认可行)
- 定义(`limit_up/after_market.py:275`):
  ```
  seal_strength = fd_amount / float_mv     (封单金额 / 流通市值)
  ```
- **原始源 = Tushare `pro.limit_list_d(fields=...fd_amount,float_mv,first_time,open_times...)`**(涨停板每日明细)。Tushare 已不可用 → `fd_amount / first_time(→seal_minutes) / open_times` 这几个事件字段断的就是这个源。
- 近期替代源**已确认可行**:
  - **`fd_amount`(封单金额)≈ tick 的 `bidVol[0] × bidPrice[0]`**(封板时买一量@涨停价)。实测 xtdata tick **有 `bidPrice`/`bidVol`(L1-L5 数组)**字段 → 近期可取(tick 仅近端,正好符合"只需近期")。
  - `float_mv` = xtdata `FloatVolume × close`(已确认 FloatVolume 可取)。
  - 备选:AKShare `stock_zt_pool_em` 的"封板资金"可直接给 fd_amount(且含首次封板时间→seal_minutes、炸板次数→open_times),但该接口本测返回空、需排查;**tick·L1 是更可靠的近期路径**。
- `seal_minutes`(封板时长)、`open_times`(炸板次数):原 Tushare first_time/open_times;近期可从**分钟/tick 盘中自算**(2020+ 本地分钟)或 zt_pool。

### 结论(基于"只需近期数据")
- **retail_line_change 能复现**:能,纯 K线公式,miniQMT 日线即可,**无需任何额外源**。
- **seal_strength 近期封单源**:**tick·L1 可行**(`bidVol[0]×bidPrice[0]`),已实测 tick 含 bid 字段;float_mv 用 FloatVolume×close。
- **打板模块现在能不能动手**:**能**。两个原卡点(retail_line 来源、seal_strength 封单源)都已解开,近期数据(2024-2025-now)下 26 字段均可获得/可算(价量&散户线→K线;市值→FloatVolume;龙虎榜→AKShare;封板→tick·L1;日内/炸板→分钟)。**按"短样本保守"设计动手即可**(不追 2018,符合打板短周期特性)。剩余工程项:zt_pool 排查(可选,tick 路径已够)、行业映射表、tick 批量下载量。
