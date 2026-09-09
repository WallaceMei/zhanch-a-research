# Top250 预筛池(seed)研究面板 — enrich 报告

> 2026-06-29。战车A 新研究主线·第一步:把 dragon 的 **Top250 预筛池(seed 层,dragon_score 还没排序)**
> enrich 成研究面板,为"在更前池子上用**可交易收益**重找选股因子"备数据。**本步只 enrich,不验因子**。

## 背景
前三轮在 dragon **Top12 成品池**验因子,发现循环自证 + dragon 整套在可交易收益下不成立(见
`dragon_event_study/dragon_tradable_backtest/`)。本步回到更前的 **Top250 seed 层**(seed = ret3_top160 ∪
money_top20% → 6因子预筛 Top250,**早于 dragon_score 排序**),跳出 dragon 框架重找因子。

## 数据源 / 口径
- seed 代码:`dragon_event_study/_pass1_2020_2026.json`(6.5年运行的 checkpoint,每天 date→[prev_date, 250码])。
  - ★注:原 `_pass1.json` 是 4 个月(全 2026 holdout)→ **未用**。
- 数据全部走统一数据中台 read + `repro_core._meta_from_df`,**口径与 dragon_event_study 完全一致**(小样本重叠 163 个 (date,code) 逐位吻合,仅底座四舍五入级差)。
- ★**可交易 forward**:买 entry(T) open、卖 **T+N close** → hold_T3/T5/T10(=close[i0+N]/open[i0]−1);**排除 day1(0天持仓)**;最短 hold_T3 持 3 天,**T+1 合法**。
- ★**holdout 纯度**:panel 只载到 **2025-12-31**,2026 价格**根本不加载** → late-2025 entry 的 forward 超窗标 NaN(不强造),保证 2026 不污染下一步验因子。

## 面板规模
- **行(stock-day):359,750** | 交易日 **1439**(2020-02-03 ~ 2025-12-31)| 唯一 code **3125**
- 每日 seed:中位/最小/最大 = **250 / 250 / 250**(每天恰好 250,无残缺)
- 唯一 (entry_date, code):**无重复**
- 文件:`seed250_panel_2020_2025.csv`(109 MB)
- 各年行数:2020=56750(2月起) / 2021=60750 / 2022=60500 / 2023=60500 / 2024=60500 / 2025=60750

## 字段
- 标识:entry_date / prev_date / code / year / buy_price
- 竞价:auction_open / auction_amount / **open_ratio / auc_ratio / auc_amount**
- 价量(8因子全):open_ratio / auc_ratio / auc_amount / close_to_high / ret3 / avg_money / close_to_20d_high / avg_range
- ★可交易 forward:**hold_T3 / hold_T5 / hold_T10**(主标签)
- 标签(对照):max_ret / days_available / window_incomplete / **is_big_meat_10 / is_super_meat_20**

## 缺失情况(NaN 不强造)
| 字段 | 缺失 | % | 原因 |
|---|---|---|---|
| close_to_high/ret3/avg_money/close_to_20d_high/avg_range | 0 | 0.0% | 都有 prev_date 20日窗 |
| open_ratio/auc_ratio/auc_amount | 1179 | 0.3% | entry 当日停牌/无竞价 |
| is_big_meat_10/super20 | 1129 | 0.3% | entry 当日无法买入(停牌) |
| hold_T3 | 1879 | 0.5% | 停牌 + 2025末截断 |
| hold_T5 | 2375 | 0.7% | 同上(2025-12 entry 1333 + 停牌 1129) |
| hold_T10 | 3613 | 1.0% | 同上,持越久越多落进2026被截 |
- forward 缺失随周期递增(T3<T5<T10)= **2025 末 entry 的卖出日落进 2026 被 holdout 截断**(符合预期)+ 少量停牌。

## 2026 holdout 确认
- max year = **2025**;2026 行 = **0**;panel 载入区间 2020-01-01 ~ **2025-12-31**,2026 价格未加载。✓

## 描述性(仅供参考,非因子结论)
- 有 forward 子集:big10 基率 0.349、super20 0.149;hold_T5 中位 −0.76%、均值 −0.05%。
- (注:这些只是面板分布,**本步不验因子、不下结论**;Top250 上的可交易因子验证是下一步。)

## 下一步(非本步)
在此面板上,用 **hold_T5(可交易收益)** 为主标签,验"在已涨已放量的 Top250 更前池子里,哪些单因子能区分可交易赢家"——四关法庭机制复用,2026 仍全程不碰。
