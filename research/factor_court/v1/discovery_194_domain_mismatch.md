# 发现存档:194 RD-Agent 因子 vs features.parquet = 0 可算(数据域错位)

> 因子审判法庭 V1 §1 只读勘查的关键发现,留档。只读勘查产物,未算因子、未下因子结论。
> 日期 2026-06-22。

## 结论
原计划用法庭审 194 个 RD-Agent 候选因子(`C:\quant_project\limit_up\qlib_results\rdagent_factors_v4.jsonl`),但勘查证实:**这 194 个因子里,能直接在 `C:\quant_project\features.parquet` 上算出来的 = 0 个。** 原因是数据域错位。

## 证据

### 194 因子(jsonl)
- 194 条;字段 name/economic_meaning/formula/direction/fields_used/train_ic/test_ic/round/phase。
- `direction` 全为 1;无任何挖掘窗口字段(discovery window 不可考)。
- formula 为 qlib 风格表达式(cs_rank/ts_zscore/ts_shift/np.log1p + df['字段'])。
- `fields_used` 去重字段全集 = **26 种**。

### features.parquet
- 76 列 / 7,747,155 行 / 5,120 股 / 2018-07-04 ~ 2026-04-03。
- 列为通用技术面(returns / ma_ratio / volatility / atr / rsi / macd / bb / shadow / streak / price_position)+ 各自截面 _rank,无任何打板域字段。

### 字段映射(26 依赖字段 → features 列)
- features **有 5 种**:bb_position, price_position_60d, rsi_14, up_streak, vol_ratio_5d
- features **没有 21 种**(打板域为主):seal_strength, seal_ratio, seal_minutes, limit_turnover, daily_total_limits, industry_limit_count, first_board_ratio, market_max_board, lhb_net, on_lhb, inst_net, float_mv_yi, retail_line, retail_line_change, open_times + 命名/粒度差:return_3d, vol_vs_prev, morning_vol_ratio, tail_vol_ratio, intraday_range, kdj_j
- **194 因子按"fields_used 全部命中"统计:全命中 0 / 部分命中 123 / 完全不命中 71** → 可算 = 0。

## 含义与决策
- 这不是 bug,是 RD-Agent 在**打板域**挖的因子(几乎每个都依赖 seal_*/limit_*/lhb_* 等打板字段),features 是**通用技术域**,域不匹配。
- 决策(Wallace 拍):走"做法 A"——**先用 features 现成的通用技术单因子把法庭建成、跑通、验证机制;194 打板因子挂起,等将来打板域数据到位、用同一个法庭审。**
- 对应 spec:`docs/specs/factor_court_v1_spec_A.md`。

## 边界
只读 jsonl + features schema/列;未碰 2026 数据、未算因子值、未跑 IC、未改任何文件、未动 194 因子原文件。
