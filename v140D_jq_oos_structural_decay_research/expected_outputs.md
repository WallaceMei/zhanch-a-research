# 预期聚宽研究环境输出文件清单

执行脚本后，应期望获取以下文件：

**优先下载：**
0. **`v140D_jq_oos_structural_decay_outputs.zip`**: 包含以下所有 6 个文件的压缩包。

（如果 zip 失败，请分别下载以下文件：）
1. **`jq_oos_market_regime_daily.csv`**: OOS 区间每日市场宽度与指数状态。
2. **`jq_oos_watch_pool_forward_returns.csv`**: 144 笔 Watch Pool Add 信号的前向 1-10 日收益追踪与 A 字杀验证。
3. **`jq_oos_failed_trade_price_path.csv`**: 12 笔 OOS 失败交易入场后的真实极值收益路径与快速回撤验证。
4. **`jq_promotion_block_10d_path.csv`**: 7 笔 Promotion Block 被阻断后的 10 日机会成本与大肉截断分级验证。
5. **`jq_structural_decay_summary.csv`**: 汇总统计指标表。
6. **`jq_oos_structural_decay_report.md`**: 最终 Markdown 格式的答辩报告（含 A/B/C/D 结论）。
