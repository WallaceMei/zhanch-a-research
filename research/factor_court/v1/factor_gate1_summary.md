# 因子审判法庭 V1 — Gate0+Gate1 总结(做法 A:审 features 现成单因子)

> 本版定位:**建法庭 + 验机制**。通过者只标 `gate1_candidate_alpha`,**严禁 robust_alpha**。
> 不下"因子能不能用"最终结论(Wallace 拍)。OOS 截至 2025-12-31,不碰 2026。
> 运行环境 `D:\quant_env\.venv_court`(pandas+pyarrow,不碰 .venv_qlib/.venv_rdagent/quant_platform)。

---

## 0. 一句话

法庭流水线(Gate0 准备 → 双 mask → IS 锁方向 → OOS HAC t 判决 → 台账)**完整跑通、机制经对照验证正确**。受审 31 个 features 通用技术单因子,**29/31 在 2023-2025 OOS 上 HAC t>3.0**——但全部仅 `gate1_candidate_alpha` + **OOS 纯度 unknown + 高度冗余 + 未做多重检验**,**不代表稳健 alpha、不能上线**。本版价值是法庭建成可用,不是"审出 29 个金因子"。

---

## 1. 受审范围
- features.parquet:76 列 / 7,747,155 行 / 5,120 股 / 2018-07-04~2026-04-03。
- 三分类:原料列 14、前向/标签相关 12、**受审因子 31**(25 技术 + 6 动量[后向 return],均取 _rank 版,原始/rank 二选一)。覆盖率全 = 1.000。
- 目标:**自算前向** `fwd_return_10d[T]=close_adj[T+10]/close_adj[T]-1`,再横截面去均值。**绝不读 features 的 return_* 列(那是后向)**。
- ★ 泄漏防线:纳入的 6 个 return 列是后向收益(因子,T 日已知),自算 fwd_return_10d 是目标(未来,T+10 才知),代码显式 assert 因子集不含目标列。

## 2. Gate0
- 因子值直接读 features 列(做法 A 不现算)。
- 收益:fwd_return_10d_cs_demean(主)+ fwd_return_10d(辅)。**注:Spearman Rank IC 对目标的逐日横截面去均值不变,故 cs_demean 与 raw 的 IC 完全相同(rank IC 的固有性质,非 bug)。**
- 双 mask:universal(排涨跌停)有效 7,410,419;board_domain(留涨停)有效 7,563,120;涨跌停样本 157,432;ST 样本 134,317(ST 由 name 前缀近似识别,涨跌停由 pct_chg≥9.7% 近似,主板口径,STAR/创业板20%、ST5% 未精确区分)。
- 方向:IS(2018-2022)mean IC 符号锁定,`direction_locked_before_oos=True`,OOS 只验证不翻向。

## 3. Gate1(OOS 2023-2025,727 个交易日)
- 逐日横截面 Spearman Rank IC;HAC/Newey-West t(lag=10)为主判据,naive t 仅参考。
- 阈值:t>3.0、min_daily_stocks=100、min_oos_ic_days=120、min_factor_coverage=0.3。
- 结果:124 行(31×2mask×2ret),**112 行过 HAC t>3.0**;去重到因子级 **29/31 过**。仅 2 因子(macd_hist 在 universal、price_position_10d 在 universal)未全过。
- 最强(HAC t):overnight_return_rank 6.78、return_20d_rank 6.49、vol_ratio_20d 6.43、vol_price_corr_10d 6.35、ma_ratio_60d 6.32。
- naive→HAC 中位收缩 2.07×(HAC 确实在压自相关虚高),但收缩后多数仍 >3。

## 4. ★ 机制验证(对照,证明法庭不放水)
| 对照 | ic_mean | HAC t | 判读 |
|---|---|---|---|
| 噪声因子 vs 真目标 | -0.0006 | **-1.19** | 垃圾判不过 ✅ |
| 真因子 vs 打乱目标 | +0.0001 | **+0.32** | 断开因子-目标即归零 ✅ |
| 真因子 vs 真目标(复现) | -0.074 | -5.98 | 复现主管道、符号自洽 ✅ |
→ 法庭机制正确:噪声不过、打乱归零。**29/31 全过不是 bug**,是 A 股技术因子该期 10 日 IC 普遍强(动量/反转/波动率真实)。

## 5. 双 mask 对照(§4 解读)
几乎所有因子 universal 与 board_domain **都过**,board_domain 的 t 普遍略高(保留涨停样本、有效样本更多)。涨跌停样本仅占 ~2%,两套差异小。本版受审通用因子,universal 是主场;board_domain 主要把机制验全(将来审打板因子用)。

## 6. ★ 为什么"全过"仍只能是 candidate_alpha(必须强调的局限)
1. **OOS 纯度 unknown**:这 31 个是教科书级通用技术因子(ma/rsi/动量/波动率),2023-2025 几乎必然在它们被研究/优化的区间内。t>3 只说明"该期 IC 真实非零",**不等于样本外新发现**。
2. **高度冗余**:29 个里大量是同一效应——动量簇(return_5/10/20/60d + ma_ratio + price_position 互相高度相关)、波动率簇(volatility/atr)、量簇(vol_ratio/amount_ratio)。去冗余后独立信号远少于 29(V2 ONC/去冗余才能定)。
3. **未做多重检验**:测了 31 因子,无 DSR/Deflated Sharpe/FDR/Bonferroni 校正(V2)。
4. **HAC lag=10 对慢因子可能欠校正**:ma_60d/return_60d/price_position_60d 的 IC 序列自相关可能超 10 日,lag=10 下 t 偏高。本版按 spec 固定 lag=10。
5. 未做衰减监控、未做 2026 终审、未做组合回测。
→ 综上,`gate1_candidate_alpha` = **只过第一关(OOS t>3 + 方向预锁),OOS 纯度 unknown,不是稳健 alpha,不能直接实盘**。

## 7. 法庭纪律(新增,记此)
**凡用 features 的列,口径一律数据实证确认、不靠列名猜。** 反例:`return_10d` 列名像前向标签,实测 corr(后向)=1.000 → 是后向收益;若按列名直接当预测目标,法庭判据从根上错。本版已据此:目标自算前向、pct_chg 口径实证为百分比(ratio=100)、ma_ratio 实证为 close/MA5(≤T)。

## 8. 产出文件(research/factor_court/v1/)
- `factor_universe_audit.csv` — 31 受审因子清单 + 覆盖率 + 泄漏核查
- `factor_gate1_results.csv` — 124 行逐因子×mask×ret 结果(IC/naive t/HAC t/verdict)
- `factor_court_v1_ledger.csv` — 31 因子台账(每因子最佳 mask/ret + verdict)
- `factor_gate1_summary.md` — 本文件
- `discovery_194_domain_mismatch.md` — 194 打板因子 vs features=0 可算 的域错位存档
- `factor_court_v1.py` — 法庭模块(会迭代到 V2)

## 9. 边界 / 红线自证
research-only;只读 features、不碰 2026、不碰 194 因子原文件、不下因子最终结论;verdict 仅用允许集(本版只出 gate1_candidate_alpha / gate1_fail);**无 robust_alpha**。
