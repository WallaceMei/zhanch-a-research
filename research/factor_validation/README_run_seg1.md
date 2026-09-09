# 因子验证 第一段 — 运行说明(交接物)

> research-only。不改主策略、不 git、本段不下 VERDICT、不验确认链(那是第二段)。
> 本地只验了语法+编码;真前向价由聚宽研究环境取(get_price 只有聚宽能取真实行情)。

## 文件
- `jq_factor_signal_universe.csv` — 信号底表(本地从权威日志 `log/jq_v140D_20230101_20260622.log.txt` 抽取的 2067 笔 WATCH_POOL_ADD)。字段:stock / signal_date / signal_price / signal_score / signal_rank / signal_entry_type(全 deep_water)。分年 419/471/721/456,0 缺失。
- `factor_seg1_jq_bare_signal_ic.py` — 聚宽取价 + 裸信号 IC/分层/分年/超额 分析脚本。

## 怎么跑(聚宽研究环境)
1. 把上面**两个文件上传到聚宽研究环境同一工作目录**。
2. 运行 `factor_seg1_jq_bare_signal_ic.py`。
3. 取价方式:按 signal_date 批量取一篮子票(~668 次 get_price,非 2067 次单只循环),外加 1 次中证1000、1 次交易日历。

## 产出(写到 `factor_seg1_outputs/` + zip 打包)
- `jq_factor_seg1_signal_forward.csv` — 每笔信号的 T+1/3/5/10/20 绝对收益 + 超额收益 + data_quality_flag。
- `jq_factor_seg1_ic_summary.csv` — IC 汇总:scope(all/2023/24/25/26)× horizon × basis(exc/abs),含 Spearman 秩IC + Pearson + 均值。
- `jq_factor_seg1_score_layer.csv` — signal_score 分层(五分位 Q1-Q5 + Q5-Q1 价差 + 高/低半)各期均值,超额与绝对都给。
- `jq_factor_seg1_report.md` — 描述性结果(无 VERDICT)。
- `factor_seg1_outputs.zip` — 打包(zip 内仅文件名无路径)。

## 关键口径(透明,便于复核)
- **基准价 base = close[T](fq=pre,前复权)**,不是日志原始 signal_price——为消除窗口内分红/拆股失真;signal_price 仅留作 QC(`base_gap_vs_signal_price` 标差异)。若你要改成以原始 signal_price 为基,告诉我改。
- **超额 = 个股前向收益 − 同期中证1000(000852.XSHG)收益**;同时保留绝对收益供对照。
- **防未来函数**:signal_score 来自日志(T 日已知),前向收益只用 T+1..T+20 收盘;T、T+k 来自交易日历。
- **get_price 铁律**:全程 start_date+end_date,不带 count(日历用 get_trade_days 的 start+end 解析)。
- **末端样本**:2026-06 的信号 T+20 超出已有行情 → 标 `insufficient_forward_days` 自动排除该期,不污染。

## 跑完回传
把 `factor_seg1_outputs.zip`(或那几个 csv)传回,我读数后出第一段结论(裸信号 IC 四年一致性 + 分层 + 超额),仍不下 VERDICT、不碰确认链。
