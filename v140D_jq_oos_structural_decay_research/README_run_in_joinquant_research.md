# 聚宽研究环境运行指南

## 注意事项

- **必须在聚宽 (JoinQuant) 的“研究环境 (Research)”中运行该脚本。**
- **本地运行会失败**，因为依赖聚宽特有的 `jqdata` API (如 `get_price`, `get_trade_days`)。
- **不得将该脚本当作“策略 (Strategy)”运行**，它不包含策略框架所需的 `initialize`, `handle_data` 等函数。
- **不得将结果用于直接调参**，本脚本产出仅用于诊断架构衰退和验证方向期望。

## 操作步骤

1. 登录聚宽 (JoinQuant) 平台，进入“研究”页面。
2. 新建一个 Python 文件，命名为 `research_v140D_jq_oos_structural_decay.py`。
3. 将本地该同名脚本的内容全选复制，粘贴到聚宽研究环境的文件中。
4. 在聚宽中执行该脚本（可通过新建一个 Terminal 运行 `python research_v140D_jq_oos_structural_decay.py` 或者在 Jupyter Notebook 中执行）。
5. 运行完毕后，**优先从聚宽下载生成的 ZIP 文件**：
   - `v140D_jq_oos_structural_decay_outputs.zip`

   如果 zip 生成失败，再分别下载以下单独文件：
   - `jq_oos_market_regime_daily.csv`
   - `jq_oos_watch_pool_forward_returns.csv`
   - `jq_oos_failed_trade_price_path.csv`
   - `jq_promotion_block_10d_path.csv`
   - `jq_structural_decay_summary.csv`
   - `jq_oos_structural_decay_report.md`
6. 下载完成后，请**解压并上传这些文件给 ChatGPT 或保存到本地诊断目录**，以进行下一阶段机制设计讨论。
