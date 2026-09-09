# 贡献说明

## 分支与提交

- 使用短生命周期分支，例如 `feature/<topic>` 或 `fix/<topic>`。
- 使用 Conventional Commit，例如 `docs: add public repository overview`。
- 不直接提交凭证、原始行情、回测缓存或账户文件。

## 研究产物

提交可复现的脚本、参数说明和摘要；大体量 CSV/Parquet、原始分钟数据、HTML 数据分片请放在本地数据目录或外部受控存储。

## 提交前检查

```powershell
git status --short
git diff --check
py -3.10 -m compileall -q .
```

确认 `.env`、日志、数据文件未被暂存后再提交。
