# 打板事件模块 A1a — 字段补齐 + 验真 + 覆盖率 + 194因子预审报告(回填后终版)

> A1a 只做数据准备,不跑四关。复用 A0 事件池(83,211 事件行/2024-2025),未重造。
> 红线:不碰2026调参、不标robust_alpha、字段补不出如实标unavailable(不硬造/不填0/不forward fill)。
> 环境 .venv_court(龙虎榜+Tushare用各自现成环境只读,token不入库)。日期 2026-06-22。**A1a 完成,停下,等确认再进 A1b。**

---

## 0. 一句话结论

**Tushare limit_list_d(xiaodefa 代理 https://tt.xiaodefa.cn)解开封单硬墙后,194 因子里 can_calculate = 125(从初版的 7 跃升);69 个仍 field_unavailable,只剩 3 类字段拦路:morning_vol_ratio(43)、tail_vol_ratio(39,需分钟)、inst_net(34,需龙虎榜机构明细)。** 其中 147 个因子用到 seal 类字段——这些字段只在"封住涨停"行有值(全池 34% / sealed 子集 89%),**A1b 算这些因子的 IC 必须把样本限定在 sealed_limit 子集**(在封住的票里比强弱),不能把 NaN 行塞进 IC。

---

## 1. 字段补齐总览

| 类 | 字段 | 源 | 覆盖 | 状态 |
|---|---|---|---|---|
| 类1 K线/市场级 | retail_line/retail_line_change/vol_vs_prev/intraday_range/kdj_j/daily_total_limits/market_max_board/first_board_ratio | features 日线+全市场聚合 | ≥99% | ok |
| 类2 龙虎榜 | lhb_net/on_lhb | AKShare(quant_platform/.venv 只读) | 全覆盖(34,463上榜记录;未上榜=0真值) | ok |
| 类2 龙虎榜 | inst_net | —— | 0 | **unavailable**(需逐股机构明细,挡34) |
| **类3 封单(Tushare)** | **seal_strength/seal_ratio/seal_minutes/open_times/float_mv_yi/limit_turnover** | **Tushare limit_list_d 派生** | 全池34%/**sealed子集89%** | **ok(sealed子集)** |
| 类3衍生 | industry_limit_count | limit_list_d 按行业当日计数 | 同上 | ok(sealed子集) |
| 类1 分钟 | morning_vol_ratio/tail_vol_ratio | —— | 0 | **unavailable**(需分钟,挡43/39) |

### 封单字段口径(钉死,已验)
- `seal_strength = fd_amount/float_mv`(均元;面板内中位 0.00904,<0.007 占 41%,与原 `<0.007=封板弱` 量级一致)
- `seal_ratio = fd_amount/amount`;`open_times` 直接;`float_mv_yi=float_mv/1e8`;`limit_turnover=turnover_ratio`
- `seal_minutes = first_time→15:00 封板持续分钟`(交易分钟,中位 199,范围 0-240;240=一字/早封,0=尾盘封)
- `industry_limit_count` = 当日该 industry 涨停家数

### ★ seal 类 NaN 处理(关键)
- limit_list_d 只含**封住涨停**的股 → seal 类字段**只在封住行有值**;failed_board/near_limit 行 = **NaN(真实"没封板就没封单",非缺失)**。**未填0、未forward fill。**
- 面板新增 `in_limit_list_d` 标记(True=有seal值);`sealed_limit` 31,211 行中 27,938(89%)匹配到 limit_list_d(差额=本地近似涨停判定 vs Tushare官方涨停名单的边界差,如ST/板块涨幅)。
- **提醒 A1b:seal 类因子(147个)算 IC 时样本必须限 sealed_limit 子集**(在封住的票里比封单强弱),NaN 行不进 IC。

---

## 2. 龙虎榜信息时点声明(不变)
lhb_net/on_lhb 是 **T 日收盘后**信息,**只能用于 T+1 open 之后收益验证**(本模块收益从 T+1 open 起算,可用);不可用于 T 日盘中决策。

## 3. tick 说明
xtdata tick 无 2024-2025 历史(仅 2026 近端),**封单字段最终改由 Tushare limit_list_d 提供**(覆盖开发窗口,口径已验)。tick 仅留作将来近端/实时备选。详见 board_tick_manual_validation.csv。

---

## 4. 194 因子预审(回填后,board_factor_field_audit_precheck.csv)

| 计数 | 初版 | **回填后** |
|---|---|---|
| **can_calculate** | 7 | **125** |
| field_unavailable | 187 | **69** |
| leakage_suspected | 0 | 0 |
| 用到 seal 类(IC需限sealed子集) | —— | 147 |

**剩余拦路字段(只剩 3 类)**:
| 字段 | 挡几个 | 可补性 |
|---|---|---|
| morning_vol_ratio | 43 | 软墙,需本地分钟(2020-2026) |
| tail_vol_ratio | 39 | 软墙,需本地分钟 |
| inst_net | 34 | 较重,需龙虎榜机构席位明细(逐股) |

(三者重叠,合计挡 69 个。)

---

## 5. 是否进入 A1b

**125/194 已可审,足以让四关法庭跑全量练兵。** 两种走法(归 Wallace):
- **路 A1(推荐):直接用现有 125 个进 A1b**(seal 因子 IC 限 sealed 子集),先把四关在打板域跑通;morning/tail/inst 这 69 个留后续补。
- **路 A2:先补 morning/tail_vol_ratio(本地分钟,挡 82 个去重后约 50+)再进 A1b**,把可审数推到更高;inst_net(34)最重,可最后补。
- 提醒:seal 类因子 147 个,A1b 主口径(event_pool_all)下它们的有效样本是 sealed 子集,样本量小于其它因子,需注意样本阈值。

**事实判断(非决策)**:封单硬墙已解,125 个足够开 A1b;morning/tail 是软墙、值不值得先补看你要不要那 ~50 个因子;inst_net 最重、收益最小(仅34)。

---

## 6. A1a 产出(research/board_event_a1/)
board_event_panel_full.parquet(含 seal 类 + in_limit_list_d 标记)/ board_field_backfill_report.md / board_field_coverage.csv / board_tick_manual_validation.csv / board_factor_field_audit_precheck.csv / _limit_list_d_2024_2025.parquet(33,295行涨停明细)/ _lhb_2024_2025.csv;过程模块 build_class1/class2_lhb_pull/batch_limit_list/backfill_seal/assemble_a1a.py。

## 7. 红线自证
复用A0事件池;未碰2026;无robust_alpha;seal类NaN如实保留(无填0/无ffill),并标 in_limit_list_d;Tushare/AKShare token未入库未打印;**A1a 完成,停下,等确认再进 A1b**。
