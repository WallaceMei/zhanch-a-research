# factor_conclusions_ledger.csv — 因子结论台账(字段说明)

> 这是"标准因子库"的种子台账:**每验证完一个因子,加一行**。
> 它记的是**因子的元结论**(有没有 alpha / 是否过拟合),不是因子值面板。
> 因子值面板/原料数据在 `D:\量化策略\选股因子\`(选股因子 V4 等),两者别混。
> 存储:UTF-8 **带 BOM**(Excel 打开中文不乱码)。含逗号/特殊字符的字段用双引号包裹。

## 11 列字段

| 列 | 含义 | 取值约定 / 示例 |
|---|---|---|
| `factor_name` | 因子名 | 蛇形小写,如 `dragon_score` |
| `version` | 版本 | 如 `v3`;同名因子不同版本各占一行 |
| `factor_type` | 因子类型 | `composite`(复合)/ `single`(单因子)/ `template`(模板判定) |
| `definition_source` | 定义出处 | 指到代码/文件,如 `战车A observer/make_global_config score_mode=v3` |
| `sample_in_ic` | 样本内 IC | 数值或定性:`positive_claimed`(只有宣称无实测)/ 具体值 `0.12` |
| `sample_out_ic` | 样本外 IC | 实测值或区间,如 `-0.009~-0.051(T+1~T+20递减)`;**这是核心证据列** |
| `sample_out_window` | 样本外窗口 | 如 `2023-01~2026-06` |
| `n_samples` | 样本量 | 整数,如 `2067` |
| `verdict` | 结论标签 | 见下方受控词表 |
| `evidence` | 证据摘要 | 关键数字串,用 `/` 分隔多条,如 `分年四年一致负/Q5-Q1无单调/回测+361%vs实测超额-5.38%` |
| `archive_ref` | 归档全文路径 | 相对仓库路径,如 `research/factor_validation/归档结论_*.md` |

## verdict 受控词表(只用这几个,别自由发挥)

| verdict | 含义 |
|---|---|
| `overfit_no_alpha` | 样本外无 alpha,IS 过拟合产物(如 dragon_score v3) |
| `robust_alpha` | 样本外稳定有效(IC 正、分层单调、四年一致) |
| `weak_inconclusive` | 弱/不稳定,样本不足以定论,需补数据 |
| `not_tested` | 已登记但尚未做样本外验证(占位) |

## 加一行的规矩
- 一个 (factor_name, version) 一行;改版本就新加一行,不覆盖旧行(保留可追溯)。
- `verdict` 必须能被 `sample_out_ic` + `evidence` 支撑,不许只填标签无证据。
- `archive_ref` 必须指向一份能复核的归档文档(含实测数字来源)。
- 结论范围若有边界(如"仅限评分、不否定模板"),写进归档文档,台账只放可受控的字段。

## 当前记录
- 第 1 行:`dragon_score / v3 / overfit_no_alpha`(2023-01~2026-06,N=2067)。详见 `归档结论_dragon_score_v3_样本外因子有效性验证.md`。
