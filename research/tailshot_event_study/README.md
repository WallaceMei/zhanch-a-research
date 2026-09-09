# 尾盘选股 V2 · 长样本 forward 动态回看表

参照 `dragon_event_study` 的动态加载模式做的尾盘选股(Tailshot V2)收益回看看板。

## 打开方式（二选一）
- **最省事**：直接双击 `viewer\尾盘选股forward回看表.html`（file:// 也能加载 `data\*.js`）。
- **最稳**：双击 `打开尾盘回看表.bat`（本地起 http.server:8788 + 开浏览器）。

## 看什么
- **区间**：2025-08-01 ~ 2026-07-02，**全候选版 1679 行**（前置筛选全部候选，含尾盘检查未过的；其中过尾盘=V2 正式信号 358）。"尾盘✓/✗"筛选片可切换。
- **一行 = 一个前置筛选候选**，次日开盘买入为基准。`#` 列 = V2 排名(只在过尾盘内排)，尾盘✗ 的显示 –。
- 数据源：`C:\quant_platform\data\tailshot_backfill\outputs_full\tailshot_research_signals.csv`（full-keep 全期重跑）。
- ⚠️ 评分研究结论(2026-07-03)：尾盘 gate 对次日 hit15 无增益(被刷组 50.5% vs 通过组 45.8%)；全部因子 train/test IC 均 <0.11 不稳定；**不构造 score_v3, V2 分数仅作展示参考**。详 `C:\quant_platform\data\tailshot_backfill\score_v3_research.py` 输出。
- **KPI 条**：整体 hit15、hit20、D1 收盘中位、D1 收红率；分档(70+/60-70/50-60/<50) hit15；**月度 hit15 柱状图**。
- **热力表**：次日最高% + 命中徽章 + 区间最高 + 末日 + **D1–D10 每日收盘累计收益**（红涨绿跌热力染色）。
- **点任意行** → 右侧抽屉看该信号全部因子 + D1–D10 明细。
- **筛选**：年 / 月 / 分档 / rank段 / 仅命中 / 排序。可点表头排序。URL 参数直达：`?year=2026&month=05&hit=h15&sort=maxR`。

## 关键口径（诚实标注）
- `hit15` = 次日"开盘→盘中最高" **≥ +1.5%**（命名坑：`hit_tp_15` 的"15"指 1.5% 不是 15%）；`hit20` ≥ +2.0%；`SL` = 次日"开盘→最低" ≤ -2.0%。
- `dN` = 第 N 交易日**收盘累计收益%**（相对次日开盘）；`次日最高` = 次日 open→high%。
- 未到期(不满对应天数)标 `–`，**不补 0、不外推**。
- 新补段(4/14~7/3)：日线走 Tushare 代理(tt.xiaodefa.cn)，尾盘 1m 走 QMT；与原 302 段口径一致(原也是 Tushare 日线)。
- 数据源：`C:\quant_platform\data\tailshot_backfill\outputs\tailshot_signals_merged_to_0703.csv`。

## 数据更新到最新交易日（将来）
1. 先补日线到最新：`C:\quant_platform` 下重跑 backfill Stage B3(Tushare) + Stage C/D(重跑 research + 合并)。
2. 再重建看板：
   ```
   py build_tailshot_viewer.py   # 读合并CSV → data/meta.js + data/pool.js
   py build_html.py              # 生成 HTML 壳
   ```

## 文件
- `build_tailshot_viewer.py` — 读合并 CSV → `viewer/data/{meta,pool}.js`
- `build_html.py` — 生成 `viewer/尾盘选股forward回看表.html`(薄壳)
- `start_viewer.py` / `打开尾盘回看表.bat` — 本地起服务打开
- `viewer/` — 网页 + 数据(`index.html` 为同内容副本，方便服务器根目录直开)
