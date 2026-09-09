# 战车 A：A 股龙头研究与策略工具箱

> 研究用途源码仓库。**不构成投资建议，不包含实盘账户、凭证、行情原始数据或可直接执行的交易部署配置。**

## 内容

- `战车A龙头3_v*.py`：聚宽环境策略版本与 observer 研究分支。
- `research/`：候选池事件研究、因子验证、打板事件研究与 Project1 实验引擎。
- `docs/specs/`：研究和执行契约。
- `docs/reports/`：可公开的研究结论、实验说明与环境要求。
- `reference/`：聚宽 API 参考资料。

## 发布范围

本仓库是**源码与可复现实验说明**快照：

- 纳入：Python 源码、Markdown 文档、Notebook、启动脚本。
- 不纳入：原始行情、分钟数据、候选池面板、回测明细、日志、HTML 数据分片、账户配置、`.env`、token、Excel/压缩文件。
- 数据需要由使用者在本地按文档自行接入；研究结果中的数值不应被视为未来表现承诺。

## 环境

推荐 Python 3.10+。安装研究依赖：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-research.txt
```

### 可选数据/运行环境

- 聚宽策略需要聚宽研究或回测环境提供的 `jqdata` API。
- QMT 研究路径需要已安装的 `xtquant` 与可用的 MiniQMT 数据服务。
- Tushare、AkShare 和本地数据仓库均为可选适配层；配置变量请从 `.env.example` 复制到本地 `.env`，不要提交凭证。

## 研究纪律

1. 研究候选池与实盘下单环境分离；此仓库不承担实盘执行职责。
2. 对候选池/forward 研究保留交易日、数据截止日和数据源口径。
3. 新研究应保留可复现脚本和摘要，不提交大体量原始数据或缓存。

## 快速导航

- [候选池事件研究 spec](docs/specs/候选池事件研究回看表_CC_spec.md)
- [因子验证结论台账](research/factor_validation/README_factor_conclusions_ledger.md)
- [实验说明](docs/reports/README_EXPERIMENTS.md)
- [贡献说明](CONTRIBUTING.md)
- [安全说明](SECURITY.md)

## 许可

当前未授予开源许可。除非仓库所有者另行书面许可，保留所有权利。
