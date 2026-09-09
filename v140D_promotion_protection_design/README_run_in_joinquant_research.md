# 在聚宽 research 跑这份反事实研究 — 操作说明

## 适用对象
`research_v140D_jq_promotion_protection_counterfactual.py`

这是**研究脚本**，跑在聚宽「研究环境（research notebook）」里，不是策略
回测。它不下单、不调 run_backtest、不 schedule_function。

## 一、上传 / 运行步骤

1. 登录聚宽 -> 进入「研究环境」(Jupyter Notebook)。
2. 把 `research_v140D_jq_promotion_protection_counterfactual.py` 上传到
   research 根目录（或任意你能 cd 进去的目录）。
3. 新建一个 notebook cell，运行：

   ```python
   %run research_v140D_jq_promotion_protection_counterfactual.py
   ```

   或在 cell 里：

   ```python
   import research_v140D_jq_promotion_protection_counterfactual as r
   r.main()
   ```

4. 跑完后在脚本同目录下会生成 `promotion_protection_outputs/`，里面 5 个
   文件（4 份结果 + 1 个 zip 打包，见 expected_outputs.md）：
   - `jq_promotion_protection_counterfactual_cases.csv`（7 事件 x 5 变体）
   - `jq_promotion_protection_summary.csv`（各变体聚合 + 集中度副作用）
   - `jq_promotion_protection_sensitivity.csv`（阈值网格扩散，无 best 标记）
   - `jq_promotion_protection_report.md`
   - `v140D_promotion_protection_counterfactual_outputs.zip`（zip 内只含文件名）

## 二、聚宽特有注意点（踩过的坑）

- **get_price 不能同时传 start_date 和 count**。本脚本已规避：先用
  `get_trade_days(start_date=..., count=N)` 求出交易日窗口，再用
  `get_price(start_date=..., end_date=...)`（不带 count）取价。
  如果你改脚本，务必保持这条。
- **编码**：脚本存为 UTF-8 **无 BOM**。若 line 1 报 "invalid character"，
  八成是被编辑器加了 BOM（ef bb bf）。另存为「UTF-8 无 BOM」即可。
- 脚本代码区是**纯 ASCII**，注释里没有全角标点混进代码，避免 Python 3.6
  解析报错。

## 三、5 个变体（spec 锁定，小写命名）

| variant_id | 退出口径 | proxy_distortion_flag |
|---|---|---|
| pv_immediate_full_exit | block 全退（基线，extra=0） | low |
| pv_half_exit_hold_half | 半仓 block 出；另半仓持到「收盘跌破 MA5 或第 5 日」 | low |
| pv_delay_1d_confirm | 次日确认：跌破 MA5 或收益负则次日出，否则持到 MA5/第 5 日 | low |
| pv_trail_from_high | 块后最高价回撤止损 | **high** |
| pv_downgrade_small_pos | 留 keep_frac 小仓持到「跌破 MA5 或第 5 日」 | low |

其中 half / delay / downgrade 三个变体的退出**真实用收盘价 vs 当日 MA5**
（MA5 = 5 日收盘均线，取价窗口前推 4 个交易日保证 block 当天可算）。

## 四、本地 vs 聚宽 两种模式

- **聚宽里（有 jqdata）**：进 JQDATA 模式，真去取 7 个标的「块前 4 日 +
  块后 10 日」日线路径，算 MA5 与各变体 captured_extra_return。
- **本地没有 jqdata**：自动进 PROXY 模式，只有 pv_immediate_full_exit
  有意义，其余变体 extra=0。**这是预期行为**，用来先验证管线跑通，不是
  结果。报告 md 顶部会写明 `MODE: PROXY`。**本地只验语法/编码，不冒充
  聚宽已跑通。**

## 五、结果怎么读（一句话版）

别只看 `net_pnl` 涨没涨。看 `jq_promotion_protection_summary.csv` 里的
**net_excl_top5**：只有它变大（利润基盘变宽）才算变体真有用；哪个变体把
它推得更负 = 加重脆弱性 = 扣分项。`top5_share_of_net` 又升高同理。
详细判读见 design_brief 第 4、5 节。

## 六、CLOSE_PROXY 失真声明（trail 类）

- `pv_trail_from_high` 用日线最高价回撤，**看不到盘中真实高点**，其
  captured_extra_return 是**排序级、不可成交、close_proxy 失真**
  （`proxy_distortion_flag = high`）。
- MA5 类变体（half/delay/downgrade）用收盘价，proxy 下可靠
  （`proxy_distortion_flag = low`）。
- 7 个事件、其中只有 3 个在 OOS 段，样本极小，结论只作方向性提示。
- 这份研究**不为收益调参**、不标 best、不产出可上线策略、不替任何决策拍板。
