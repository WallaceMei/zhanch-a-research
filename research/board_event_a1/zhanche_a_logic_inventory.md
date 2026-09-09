# 战车A 选股逻辑盘点（为"四关法庭审战车A选股"做准备）

> 生成 2026-06-25。**只读勘查产物,未改任何代码、未建因子、未算IC、未下结论。**
> 目的:盘清战车A里所有"选股/选票/过滤/打分/打标签"逻辑各自的形态、真实公式、依赖字段、版本关系,初判能否送进 A1b 四关法庭。
> 参照面板:`board_event_a1/board_event_panel_full.parquet`(48列,**打板/封单事件面板**)。

---

## 0. 一句话结论(先看这个)

战车A 的核心选股是**一条流水线**(初始宇宙→日线候选→竞价预筛250→竞价过滤→deep_water/trend_core 模板→dragon_score 打分→Top12→再筛Top2),外加 v1.4.0 起的 **deep_water 卫星仓(Rule D 确认)** 旁路。

**关键发现:战车A 选股用的字段大多是"竞价前日线候选宇宙 + 竞价数据"口径(多日均成交额/涨幅、昨收/昨高、竞价量比、MA 等),跟 A1b 的"打板事件面板"口径对不上。** board_event_panel_full 是为封单/打板事件因子(seal_strength 等)建的,缺竞价量比、昨收昨高比、多日均振幅/成交额、MA 序列。所以**几乎没有逻辑能直接拿现有事件面板送四关审**——要么字段缺,要么得另建一个"Dragon 候选宇宙截面面板"。好消息:`research/dragon_event_study/` 已有一套能算 dragon_score 全字段的独立数据管线(连 DB 建 daily_meta),审战车A选股应复用它,而不是 A1b 事件面板。

**dragon_score 已验死(IS +361% / 样本外无 alpha,见 [[dragon-score-v3-overfit]]),不重审。** 真正值得审的旁路是 **deep_water 卫星 Rule D**(Wallace 标的重点,样本小13笔),但它是"信号后1-3日确认的二元闸门",不是截面打分因子,翻译成池内IC形态有难度。

---

## 1. 总表:所有选股逻辑 × 形态 × 位置 × 字段 × 能否送审

| # | 逻辑名 | 形态 | 主定义位置 | 依赖字段 | 事件面板有? | 送审判定 |
|---|---|---|---|---|---|---|
| L1 | 初始宇宙过滤 `get_base_stock_universe` | 二元过滤 | 战车A龙头3.py:3550-3625 | 代码前缀、is_st、paused、上市日 | 部分(is_st/is_paused有) | 不适合(是宇宙裁剪非选股因子) |
| L2 | 日线候选 Seed `ret3_top ∪ money_top` | 排序截断 | 战车A龙头3.py:3005-3160 | 近3日涨幅、昨成交额 | ❌(无ret3/成交额) | 字段缺 |
| L3 | 竞价前日线预筛 `_prefilter_dragon_auction_candidates`→Top250 | 阈值过滤+加权评分 | 战车A龙头3.py:2858-3002 | 5/10日均成交额、5/10日涨幅、收盘/20日高、10日均振幅 | ❌ | 字段缺 |
| L4 | 竞价过滤(auction filter) | 条件串 | 战车A龙头3.py:3161-3216 | 竞价价/量、前日量、涨停价、open_ratio | ❌(无竞价数据) | 字段缺 |
| **L5** | **deep_water / trend_core 模板** | 二元标签 | 战车A龙头3.py:3243-3248 | close_to_high(昨收/昨高)、open_ratio、auc_ratio | ❌(竞价字段缺) | 要翻译+字段缺(需Dragon宇宙面板) |
| **L6** | **dragon_score(v1/v2/v3)** | 连续评分 | 战车A龙头3.py:3294-3327 | close_to_high、avg_range(10日)、auc_ratio、ret3 | ❌(关键字段缺) | **已验死,不重审** |
| L7 | Dragon池排序裁断 Top12 | 排序截断 | 战车A龙头3.py:3363-3372 | dragon_score | 依赖L6 | 随L6 |
| L8 | Dragon池激活 `update_dragon_mode` | 二元(择时开关) | 战车A龙头3.py:3375-3431 | top1/top2 dragon_score、EMA | 依赖L6 | 非选票(是"今天开不开龙头模式") |
| L9 | 买入再评分 `score_candidates_A`→Top2 | 条件串 | 战车A龙头3.py:3440-3546 | tpl、dragon_score、open_ratio、market_trend、MA5/10/20 | ❌ | 要翻译+字段缺 |
| L10 | 个股趋势 `is_stock_uptrend` | 条件串(二元) | 战车A龙头3.py:1292-1344 | MA5/10/20、近10/前10日低点 | ❌(无MA) | 要翻译(MA可从稠密日线建) |
| L11 | 大盘趋势 `get_market_trend` | 三态(择时) | 战车A龙头3.py:1255-1289 | 指数(000852)MA5/10/20 | ❌ | 非个股选票(是市场闸门) |
| **L12** | **deep_water 卫星 Rule D 确认 `_shadow_rule_d_deep_water_passes`** | 二元(6条件AND) | observer.py:3446-3454 | 距信号涨幅、当日涨幅、量比、距MA5、收盘/日高、是否涨停 | 部分(振幅/量比类似,无信号后轨迹) | 要翻译(中难,重点审标的) |
| L13 | WATCH_POOL 构建 | 选池 | observer.py:3331-3375 | deep_water候选、是否已买、是否block | 依赖L5 | 随L5/L12 |
| L14 | 最弱卫星替换 `_shadow_pick_weakest_satellite` | 评分(轮动出场) | observer.py:3499-3516 | pnl、是否破MA5、持有天数 | ❌(持仓态) | 非选票(是换仓出场) |

> "送审判定"四档:**易审 / 要翻译 / 难翻译 / 字段缺**。整张表没有"易审"——根因见 §0(面板口径不匹配)。

---

## 2. 每个逻辑详解(真实公式,非只写名字)

### L1 初始宇宙过滤 — 二元过滤
- 排除代码前缀 `('30','688','689','8','4','9')`(创业板/科创/北交所等)
- 排除当日 ST、停牌、退市
- `include_new=False` 时排除上市 < 50 天新股
- **作用**:裁剪候选宇宙,不是选股因子本身。

### L2 日线候选 Seed — 排序截断(并集)
- `ret3_top` = 按 `ret3 = 昨收/3日前收 - 1` 降序取 top 160(`dragon_ret3_top_n`)
- `money_top` = 按昨成交额降序取 top 20%(`dragon_money_top_pct`)
- `seed = ret3_top ∪ money_top`
- 之后为每只算:5/10日均成交额、ret_5、ret_10、收盘/20日高、10日均振幅(avg_range)。

### L3 竞价前日线预筛 → Top250 — 阈值过滤 + 加权评分
- **三重阈值**:`昨收 < 昨涨停*0.995`(排已涨停) 且 `昨成交额 ≥ 1.5e8` 且 `avg_range ≤ 0.08`
- **评分(百分位加权)**:
  ```
  prefilter_score = avg_money_5_rank*0.25 + avg_money_10_rank*0.15
                  + ret_5_rank*0.20 + ret_10_rank*0.10
                  + close_to_20d_high_rank*0.15 + range_10_rank*0.15
  ```(权重和=1.0)
- 排序取 Top 250 → 作为 `get_call_auction()` 输入(v1.2.0 的核心优化:把竞价调用范围压到250只)。

### L4 竞价过滤 — 条件串
用 09:15-09:26 竞价数据:`open_ratio = curr/昨收-1 > 0`、`curr < 涨停*0.995`、`auc_ratio = 竞价量/昨量 ≥ 0.006`、`auc_amount = 竞价量*curr ≥ 8e6`。

### L5 deep_water / trend_core 模板 — 二元标签 ⭐
```python
tpl = 'trend_core'
if (0.90 <= close_to_high < 0.975        # 昨收在昨高的90~97.5%(回调充分)
        and open_ratio >= 0.015          # 竞价开盘涨幅≥1.5%
        and auc_ratio >= dragon_min_auction_ratio * 1.2):  # 竞价量比≥0.72%
    tpl = 'deep_water'
```
- **deep_water = 低吸模板**(回调充分+竞价温和+量能稳),**trend_core = 其它(追涨型,后续被买入逻辑剔除)**。
- 三处代码完全一致:主策略、BigMeat(2585-2589)、repro_core(`_decide_tpl` 463-467)。

### L6 dragon_score(v1/v2/v3) — 连续评分 ⭐(已验死)
三套模式同源,**当前用 v3**。逐项公式(主策略3294-3327 / BigMeat2659-2668 / repro_core484-491 逐字相同):
```python
# v3(当前默认):Dragon预测型
inv_c2h = 1.0 - close_to_high
avg_rng = avg_range            # 10日均振幅
score  = inv_c2h * 2.5                          # 反转收高比
       + avg_rng * 4.0                          # 振幅
       + max(0, 0.03 - auc_ratio) * 8.0         # 低换手奖励(<3%)
       + min(max(ret3,0), 0.25) * inv_c2h * 2.0 # 成长×反转交互
       + min(max(ret3,0), 0.30) * 0.50          # 成长基础分
if tpl == 'deep_water': score += 0.15           # deep_water 加分
```
- **v1=追涨型**(竞价涨幅权重1.05最大,c2h方向反了)→ **v2=回调型**(c2h反转、删竞价量比)→ **v3=Dragon预测型**(加振幅、低换手、交互项)。是**同一逻辑的三个版本**,不是三个独立逻辑。
- 代码注释自述 v3 回测 Top3 累计 **+361%** —— 这正是 [[dragon-score-v3-overfit]] 记录的过拟合数字:**IS +361% vs 实测样本外超额 -5.38%,样本外无 alpha**。**结论:不重审 dragon_score 评分本身**(结论仅限评分,不否定 deep_water/整体策略)。

### L7 Dragon池排序裁断 Top12 — 按 dragon_score 降序去重取 top12。
### L8 Dragon池激活 — 二元择时开关
`strong_single`(top1≥0.12) 或 `cluster_follow`(top2均≥0.08) 或 `concentrated`(top1≥0.09) → 开龙头模式;另有恐慌日超车(市场大跌+top1≥0.10)。**这是"今天开不开仓"的择时,不是选具体票。**

### L9 买入再评分 `score_candidates_A` → Top2 — 条件串
依次过滤:① `tpl=='deep_water'`(剔除 trend_core) ② `dragon_score ≥ 0.70` ③ `0.015 ≤ open_ratio ≤ 0.055` ④ `market_trend=='down'` 全剔 ⑤ `is_stock_uptrend`(L10) ⑥ `当前价 < 涨停*0.995`。→ 按 dragon_score 取 Top2,仓位 Top1=35%/Top2=25%。

### L10 个股趋势 `is_stock_uptrend` — 条件串(二元)
`MA5>MA10>MA20` 且 `收盘>MA20` 且 `min(近10日) ≥ min(前10日)*(1-0.02)`(低点抬升),三条全满足。

### L11 大盘趋势 `get_market_trend` — 三态
000852 指数:`MA5>MA10>MA20 且 价≥MA5`→up;反之→down(下跌阻止开仓);否则 sideways。

### L12 deep_water 卫星 Rule D 确认 — 二元(6条件 AND)⭐(重点审标的)
```python
def _shadow_rule_d_deep_water_passes(snapshot):  # observer.py:3446
    return (ret_from_signal >= 0.05        # 距信号价涨≥5%
        and day_ret >= 0.05                # 当日涨≥5%
        and 1.0 <= volume_ratio_vs_prev <= 2.0   # 量比1~2倍
        and ma5_distance <= 0.10           # 距MA5≤10%
        and close_to_day_high >= 0.97      # 收盘在日内高点97%以上
        and is_limit_up == 0)              # 未涨停
```
- **流程**:Dragon 池里 deep_water 模板但**没买进**的候选 → 进 WATCH_POOL(L13,3日有效期)→ 信号后第 1/2/3 日盘中跑这 6 条件确认 → 通过则以 15% 仓买入卫星仓。
- **形态注意**:这是"信号后 1-3 日的盘中确认闸门",**不是截面排序因子**。要送四关审得翻译成"事件后窗口确认成功率"类指标,且需要信号后的逐日轨迹数据(事件面板没有)。

### L13 WATCH_POOL 构建 — 选池
来源 `dragon_candidates_today` 中 tpl=='deep_water' 且未买入/未block 的,记 signal_date/price/score,expire 3 日。**依赖 L5 模板。**

### L14 最弱卫星替换 `_shadow_pick_weakest_satellite` — 评分(轮动出场)
`score = pnl*100 - 5(若破MA5) - 3(若持有>3日且pnl≤0)`,取最低分踢出(若最弱恰是最高盈利则不动)。**这是换仓出场,不是选票入场。**

---

## 3. 逻辑之间的关系(主线 + 版本 + 分支)

### 3.1 主选股流水线(战车A龙头3.py v1.2.0,当前稳定主线)
```
L1 初始宇宙 → L2 日线Seed → L3 竞价前预筛Top250 → L4 竞价过滤
→ L5 模板(deep_water/trend_core) → L6 dragon_score → L7 Top12
→ L8 池激活(择时) → L9 再评分(只买deep_water,Top2) → 买入
   旁路:L10 个股趋势/L11 大盘趋势 作为 L9 的闸门
```

### 3.2 deep_water 卫星仓(v1.4.0A 起,observer.py)— 旁路,不在 v1.2.0 主线
```
L13 WATCH_POOL(收主线没买的 deep_water 候选)
→ L12 Rule D 确认(信号后1-3日)→ 15% 卫星仓买入
→ L14 最弱替换(轮动)
```
注意:`deep_water` 一词有**两层含义**——(a) L5 的**模板标签**(打分阶段),(b) L12 的**卫星确认规则**(Rule D)。WATCH_POOL 用 (a) 喂入,(b) 是独立闸门。

### 3.3 版本/同源关系(别当成多个独立逻辑)
- **dragon_score v1→v2→v3**:同一打分逻辑的三代(追涨→回调→Dragon预测),当前 v3。
- **BigMeat_Simple.py**:跟主策略**共用同一套** L1-L11(dragon_score/模板逐字相同),是"瘦身打包"版,**不是新选股逻辑**。
- **战车A龙头3 v1.2.1A/v1.3.0/v1.3.0A/v1.4.0A/B/D**:都是从 v1.2.0 派生的实验/数据采集/风控/卫星实验版,**选股核心(L1-L11)基本不变**,差异在风控/卫星/日志(档案见 `docs/reports/战车A_全版本策略档案_v1.4.0D交接版.md`)。
- **research/v14C/research_role_rotation_direct_sim_v1.py**(role rotation 研究):**离线复现**同一套"核心仓 top1/top2 deep_water 35%/25% + 卫星 WATCH_POOL Rule D 15%"架构,**不是新逻辑**,是把策略搬到研究环境跑模拟做归因。
- **research/dragon_event_study/repro_core.py**:**dragon_score 验死的地方**——它精确复现 L5(`_decide_tpl`)+ L6(`_score` v1/v2/v3),在事件研究里证明评分样本外无 alpha。**它自带一套能算 dragon_score 全字段的数据管线(连 DB 建 daily_meta:ret3/avg_money/avg_range/竞价),这是审战车A选股该复用的数据源,不是 A1b 事件面板。**

---

## 4. dragon_score / deep_water 已知信息核对(回应任务点4)

- **dragon_score 在战车A里的位置**:L6,主选股流水线的**打分核心**,决定 Top12 排序和 L9 的 Top2。三个版本(v1/v2/v3),当前 v3。**已验死**([[dragon-score-v3-overfit]]:IS+361%/样本外超额-5.38%),**本次不重验评分**;但它依赖的 deep_water 模板(L5)和整体策略不受此结论否定。
- **deep_water 是重点审对象**:对应两处——L5 模板标签(打分时 +0.15)和 L12 卫星 Rule D 确认(13笔小样本、模拟显示可能有用)。两者都用竞价/盘中字段,**事件面板缺**,需复用 dragon_event_study 管线或另建截面面板。L12 是二元确认闸门,翻译成可算 IC 的因子形态属"要翻译/中难"。

---

## 5. 优先级判断(哪些先审 / 哪些要先解决前置)

**A. 值得优先送审(但都要先解决数据,非现成面板可审)**
1. **deep_water 模板(L5)作为二元因子** —— 形态最简单(二元标签),"低吸 vs 追涨"是个清晰假设,且独立于已验死的 dragon_score 加权。送审需要竞价字段(close_to_high/open_ratio/auc_ratio),**复用 dragon_event_study 管线即可**。判定:**要翻译(把二元标签当0/1因子算池内IC)+ 用 dragon_event_study 面板**。
2. **deep_water 卫星 Rule D(L12)** —— Wallace 标的重点、样本小需独立验证。但它是"信号后1-3日确认闸门"非截面因子,得先定义"审什么"(确认通过组 vs 未通过组的前向收益差?),并准备信号后逐日轨迹数据。判定:**难翻译(形态不匹配)+ 需专门数据**,优先级看 Wallace 是否认这个旁路值得花成本。

**B. 不审 / 暂不审**
3. **dragon_score 评分(L6/L7)** —— **已验死,不重审。**
4. **prefilter/seed/趋势/择时(L2/L3/L8/L10/L11)** —— 要么字段缺(多日均成交额/振幅/MA 不在事件面板),要么是宇宙裁剪/择时闸门而非个股选票因子。要审需另建"Dragon 候选宇宙截面面板"。

**C. 必须先解决的前置(否则没法审)**
- **面板口径问题**:A1b 的 board_event_panel_full 是打板/封单事件面板,**不含战车A选股要的竞价量比、昨收昨高比、多日均成交额/振幅、MA**。审战车A选股要么(a)复用 `research/dragon_event_study/` 的 daily_meta 管线建"Dragon 候选宇宙截面面板",要么(b)扩 A1b 面板补这些字段。**建议走 (a)**——dragon_event_study 已能精确复现选股字段(注释称 2026-03-02 三票竞价数据与聚宽日志4位小数吻合)。

---

## 6. 声明
- 本文件**只读盘点**,未改代码、未建因子、未算 IC、未跑回测、未碰 2026、未下最终结论。
- 公式/行号均来自当次只读(主策略 战车A龙头3.py、observer、BigMeat、repro_core、role_rotation 研究脚本)。
- 版本谱系参照 `docs/reports/战车A_全版本策略档案_v1.4.0D交接版.md`。
- 能否送审是**初判**,具体送审口径(选哪套面板、二元因子怎么定义、Rule D 审什么)需 Wallace 拍板后再设计。
