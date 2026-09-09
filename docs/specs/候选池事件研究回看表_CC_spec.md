# 候选池事件研究回看表 — CC 执行 spec（战车A龙头3 v1.4.0D_observer）

> 方向性 spec，不含代码示例。CC 自读策略源码 `战车A龙头3_v1_4_0D_observer.py` 实现。
> 标的：BigMeat Simple 单池版（聚宽回测，research-only observer 分支）。
> 参考视觉：`C:\quant_project` 下尾盘选股标注网页，CC 先打开对齐染色/布局。

---

## 0. 目标（一句话）

把战车A 龙头候选池（每日 top12 dragon candidates）在 2026-03~06 全部枚举，以选股日 t=0，列 day1–day20 裸 forward 收益 + 候选参数 + 标签 + 是否实际入场，输出可筛选条件染色的离线回看表。核心研究问题：**deep_water 过滤 + 实际入场，是否真选中了 forward 更好的票。**

---

## 1. 这版的池结构（先对齐认知）

- **单池**：只有 `dragon_follow`（Dragon 龙头）。firstboard_lowopen / firstboard / weak_to_strong / DPM / 统一评分全部关闭，不涉及。
- **候选池** = `g.dragon_candidates_today[:12]`，每日 top12，来自 `_get_dragon_stock_list_A_impl`。
- **模板细分** `tpl`：`trend_core` / `deep_water`。
- **实际新开仓**：只允许 `tpl == 'deep_water'`，且受仓位/slot 上限约束（核心 Top1 35%/Top2 25%/上限 60%/卫星 deep_water 15%×1/总仓 75%）。
- ⇒ 候选池（全集，含两类 tpl）⊋ 实际买入（deep_water 子集）。回看表要把这层落差显式标出来。

---

## 2. 数据路径 = CC 直接跑回测 + 解析日志（三版并列）

CC 已有选股逻辑和数据，直接在聚宽研究环境跑回测。策略自带 observer 日志，候选池/入场/出场已记录。

### 2.1 跑 3 次回测（v1/v2/v3 各一次）
dragon_score 决定候选池排序+top12 截断，**三版候选池组成和排名不同**，必须分别跑：
- [ ] 每次锁定 `dragon_score_mode` = v1 / v2 / v3，跑 2026-03-01 ~ 2026-06-30。
- [ ] 三套日志分目录存，文件名/元信息标清版本。
- [ ] 每次都设 `bigmeat_verbose_pool_log = True`（默认只记 top3，不设则候选池不全）。
- [ ] 确认 `dragon_enable = True`，记录 `EXPERIMENT_NAME` 到元信息。

### 2.2 解析三条日志流（每版各一套）
| 日志 | 用途 | 主键 |
|---|---|---|
| `BIGMEAT_POOL_TOP` | 候选池逐票（主表行来源） | (version, date, stock) |
| `ENTRY_FEATURE_LOG` | 标记 entered + 补入场特征 | (version, date, stock) |
| `EXIT_OUTCOME_LOG` | 策略实际出场结果（参考列） | (version, entry_date, stock) |

### 2.3 forward 只算一次（版本无关，三版共享）
- 同股同日的 day1-20 forward 与评分版本无关，**按三版候选的 (date, stock) 并集去重算一次**，建一张 forward 缓存表。
- 三版主表各自左 join 这张 forward 缓存——避免重复算、保证三版 forward 数字一致。

### 2.4 join 逻辑（每版内部）
- 主表 = 该版 `BIGMEAT_POOL_TOP` 全候选。
- 左 join `ENTRY_FEATURE_LOG` → `entered` + 入场特征。
- 左 join `EXIT_OUTCOME_LOG` → 策略实际出场（与 forward 并列，不替代）。
- 左 join forward 缓存 → day1-20。

---

## 3. forward 收益层（聚宽 get_price，独立于策略持有，三版共享）

### 3.1 时间窗
- t=0 = 选股日（候选入池日）。
- day1–day20 = t=0 起 20 个交易日。
- 范围 t=0 ∈ 2026-03-01~06-30 全候选。不满 20 日**全列**，缺失 day 留空标 `window_incomplete=true`，不补 0、不外推。

### 3.2 买入基准与口径
- `buy_price` = t=0 当日开盘价。
- `day_n` = 第 n 交易日收盘相对 buy_price 累计收益率（day1 = t=0 收盘，day20 = t+19 收盘）。
- 裸持有 raw forward，**对全部候选算**（不管 entered 与否），不套策略 T+ 卖出规则、不套实盘风控。

---

## 4. 字段契约（每候选一行）

### 4.1 候选池字段（来自 BIGMEAT_POOL_TOP / impl）
| 字段 | 含义 |
|---|---|
| `entry_date` | 选股日 t=0 |
| `rank` | 当日候选排名 |
| `code` / `name` | 代码 / 名称 |
| `dragon_score` | 龙头评分（标 score_mode 版本） |
| `tpl` | trend_core / deep_water |
| `open_ratio` | 竞价相对昨收涨幅 |
| `close_to_high` | 收高比 |
| `auc_ratio` | 竞价量比 |
| `score_mode` | 当前行所属 dragon_score 版本（v1/v2/v3，由版本切换器决定可见集） |

### 4.2 入场标志与特征（来自 ENTRY_FEATURE_LOG，未入场则 null）
| 字段 | 含义 |
|---|---|
| `entered` | 是否实际买入（0/1） |
| `entry_day_ret` / `entry_volume_ratio` | 入场日内涨幅 / 量比 |
| `entry_ma5_distance` / `entry_ma10_distance` | 距 MA5 / MA10 |
| `breadth_up_ratio` | 当日市场宽度 |

### 4.3 forward 收益列
| 字段 | 含义 |
|---|---|
| `buy_price` | t=0 开盘价 |
| `day1`…`day20` | 累计收益率(%)，缺失留空 |
| `window_incomplete` | 右侧是否截断 |

### 4.4 forward 汇总/标注列
| 字段 | 含义 |
|---|---|
| `max_ret` / `day_to_peak` | 区间最大涨幅 / 到顶第几日 |
| `final_ret` | day20（不满则最后有效日并标注） |
| `sl_7pct_hit` | 是否触发 7% 追踪止损（intraday high，记触发日） |
| `tp1_hit` / `tp2_hit` | 是否触及 +9% / +15%（各记首次日） |
| `is_big_meat_10` / `is_super_meat_20` | forward 是否 ≥10% / ≥20%（与策略 EXIT 口径对齐，研究用） |

### 4.5 策略实际出场（来自 EXIT_OUTCOME_LOG，未入场则 null；参考列）
| 字段 | 含义 |
|---|---|
| `exit_date` / `exit_reason` | 实际出场日 / 原因 |
| `actual_pnl_pct` / `hold_days` | 策略实际收益 / 持有天数 |

---

## 5. 展示层（单文件离线 HTML — 美观 + 易读是硬指标）

### 5.1 基本约束
- 单文件 HTML，数据从同目录 JSON 读，双击直开，无需起服务。
- 三版数据全打进同一文件，顶部**版本切换器（v1/v2/v3）**，切换即换候选池组成+评分+排名；forward 数字版本无关、切换时不变。
- 主表每候选一行，day1–20 共 20 收益列。

### 5.2 顶部控制区
- 版本切换器（v1/v2/v3，分段按钮）。
- 月份切片（全部 / 03 / 04 / 05 / 06）。
- 筛选：tpl(trend_core/deep_water)、entered(是否入场)、参数区间。
- 排序：entry_date / max_ret / final_ret / dragon_score / rank。
- 一行迷你统计条：当前筛选下的候选数、deep_water vs trend_core 的 day20 中位对比（实时随筛选更新）。

### 5.3 易读性设计（这是重点，CC 不许糊弄）
- **day1-20 热力图染色**：A股惯例红涨绿跌，发散色阶（0 为中性白），收益绝对值越大色越深。色阶要柔和不刺眼，深色单元格上的数字自动转白字保证对比度。先打开 `C:\quant_project` 尾盘选股网页对齐配色基调。
- **冻结列**：左侧 code/name/entry_date/tpl/entered 固定，20 个 day 列横向滚动；表头吸顶。
- **行密度**：紧凑但不挤，行高足够数字不贴边；斑马纹或细分隔线降低串行。
- **entered 视觉强化**：entered=1 的行左侧加一条彩色标识条 + tpl 用色块/标签区分（deep_water 一种色、trend_core 另一种），一眼看清"被买的"和"没买的"。
- **数字格式**：收益统一带符号百分比、对齐小数位；缺失/未到期单元格灰底标 `–` 不留空白洞。
- **sl/tp 标注**：sl_7pct_hit 触发日单元格加角标或边框；不喧宾夺主，能定位即可。
- **行展开**：点击行展开抽屉/面板，显示该票全字段（入场特征 + 实际出场 + 各参数），主表保持干净。

### 5.4 对比视角（核心研究功能）
- 支持按 `entered`×`tpl` 分组看 forward 分布；切月份时同步刷新，逐月看 deep_water vs trend_core 区分度是稳是飘。
- 顶部或侧栏放一个小对照卡：当前版本×当前月，trend_core 与 deep_water 的 day5/day10/day20 中位+胜率并排，数字直接可比。

### 5.5 字体与整体
- 无衬线正文 + 等宽字体用于数字列（数字对齐好读）。
- 留白克制、层级清晰、配色不超过主色+涨跌两色+中性灰；避免花哨，以"扫一眼能定位、看一列能比较"为最高标准。

---

## 6. 红线

- ❌ 不丢弃不满 20 日的票，不补 0、不外推未来行情。
- ❌ forward 对全部候选算，不只算 entered 的（否则丢掉对照组，研究失去意义）。
- ❌ score_mode 逐行标清；若 dragon_score 用 v3，仅作记录，不得在产出写"v3 选股有效"。
- ❌ 任何产出不写"Wallace 授权""用户授权"，除非本次明确说"我授权"。
- ❌ 不触碰实盘代码目录 `C:\quant_project\QMT_clean\qmt_v35\`，本项目纯研究、与实盘隔离。
- ❌ 不改策略源码逻辑，只翻 verbose 日志开关 + 跑回测 + 解析日志。observer 分支本身不可改成影响交易。
- ❌ summary.md 只报数，不下选股有效性结论、不给加因子/调权重建议。
- ❌ 日志字段缺失/格式对不上时停下汇报，不自行猜映射硬跑。

---

## 7. 交付物 + commit message

交付：
1. `event_study_dragon_3to6.csv`（全候选明细）
2. `event_study_dragon_3to6.json`（喂展示层）
3. 回看表 HTML（单文件）
4. `summary.md`（纯数字，见 7.1 结构）

### 7.1 summary.md 结构（trend_core vs deep_water 对照必须按月分开）

- **总览**：候选总数、按 tpl×entered 分组计数。
- **forward 对照表 — 按月分开（核心）**：按 entry_date 所在月份（2026-03 / 04 / 05 / 06）各出一张子表，行 = tpl（trend_core / deep_water），列 = day5 / day10 / day20 的均值、中位、胜率(>0占比)、样本数。**不要只给 3-6 月合计**——合计会掩盖月度漂移。
- **合计行**：按月子表后附一张全区间合计表，但合计仅作参考，结论以月度稳定性为准。
- **触发统计**：按 tpl 分组的 sl_7pct / tp1 / tp2 / big_meat_10 / super_meat_20 触发占比。
- **forward vs 实际出场对照**：entered=1 的票，forward day20 收益 vs 策略实际 actual_pnl_pct，看策略的 T+ 短持相比裸持 20 日是赚到还是错过。
- ⚠️ 只报数。trend_core vs deep_water 的区分度是否"真有效"由 Wallace 看月度一致性判断，summary 不下"过滤有效/无效"结论。

commit message：
```
feat(event-study): 龙头候选池3-6月day1-20 forward回看表(v1.4.0D observer)

- 数据源: CC跑3版回测(v1/v2/v3)+解析BIGMEAT_POOL_TOP/ENTRY_FEATURE_LOG/EXIT_OUTCOME_LOG
- 候选池: 每日top12 dragon, 含trend_core/deep_water, 标entered实际入场
- forward: t=0开盘买入, 全候选raw 20日收益, 版本无关算一次三版共享, 不满20日标window_incomplete
- 标注: max_ret/day_to_peak/7%追踪止损(intraday)/TP+9%+15%/big_meat_10/20
- 对照: forward vs 策略实际出场并列, trend_core vs deep_water 按月分开对照
- UI: 单文件HTML, 版本切换+月份切片, 热力图染色, 美观易读为硬指标
- summary: tpl对照按月(03/04/05/06)分列, 合计仅参考, 判稳定性看月度
- 前置: bigmeat_verbose_pool_log=True 记全候选
- 前置: bigmeat_verbose_pool_log=True 记全候选; score_mode逐行标注
```

---

## 8. 口径确认（已拍板，CC 照此执行）

1. **回测谁来跑**：✅ CC 直接跑（已有选股逻辑+数据），跑 v1/v2/v3 三次。
2. **dragon_score 版本**：✅ 三版并列，UI 版本切换器可选看。
3. **候选范围**：✅ 全 12 候选都列，trend_core 作对照组保留，标 entered。
4. **买入价口径**：✅ t=0 当日开盘价。
5. **不满 20 日**：✅ 全列截断，标 window_incomplete。
6. **配色/UI**：✅ 常规版本但美观易读为硬指标（见第 5 节），红涨绿跌，先对齐尾盘网页基调。

CC 开工前的唯一动作：跑回测前确认 `bigmeat_verbose_pool_log = True`，否则候选池只记 top3。如有日志字段/格式与本 spec 不符，停下汇报，不猜映射硬跑。
