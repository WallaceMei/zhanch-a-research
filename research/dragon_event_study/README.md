# 龙头候选池 day1–20 forward 回看表

战车A龙头3 `v1.4.0D_observer` 候选池(每日 top12 dragon)的 forward 回看研究。
**纯本地复现,不开聚宽**:聚宽 `get_call_auction`(集合竞价)≡ QMT 1m 首根(09:30)的 open/volume。

## ★ 6.5年动态回看表(2020–2026,主交付)
- 数据底座:`event_study_dragon_2020_2026.csv`(51033行=17011×v1/v2/v3,中台warehouse后端,与QMT重叠期逐位验证)。
- 动态网页:`viewer/龙头候选池forward回看表_6.5年.html` + `viewer/data/`(meta.js + pool_v{1,2,3}.js 各~11.7MB,按版本 `<script src>` 动态加载)。
  - **打开方式**:双击 `打开6.5年回看表.bat`(本地起服务+开浏览器,最稳);或直接双击 viewer 下的 html(file:// 也能加载 data/*.js)。
  - 控件:版本 v1/v2/v3 · 年 2020–2026 · 月 01–12 · tpl · 入场 · 排序;URL 参数可直达(`?ver=v3&year=2026&tpl=deep_water&ent=1`)。
  - 大筛选下渲染上限 1500 行(收窄年/月看全)。entered 仅 2026-03~06 有(聚宽实际交易)。
- **增量更新到最新交易日**:`.venv\Scripts\python update_tail.py`(QMT后端补最后已收盘交易日的新候选池+延伸forward,
  ≤倒数第二窗的历史值不动,只补尾部空格;校验历史不变性)→ 再 `build_dynamic.py` + `build_html_dynamic.py`。
  当前数据已到 **2026-06-29**(选股+forward 截止日对齐)。
- 重新生成(数据更新后):`py build_dynamic.py`(读CSV→分片data/*.js+JSON+summary)→ `py build_html_dynamic.py`(壳)。
- summary:`summary_2020_2026.md`(各年×tpl)。全量JSON:`event_study_dragon_2020_2026.json`(56MB)。

## ★ 尾盘买入版(2026-07-03 新增,与原版共用数据)
- 页面:`viewer/龙头候选池回看表_尾盘买入版.html`(生成器 `build_html_closebuy.py`);两页头部互切(⇄ 链接)。
- **口径**:t0 收盘价买入(尾盘) · T+N = 第N个后续交易日收盘相对买入价累计%。
- **零复制**:共用 `viewer/data/pool_v{1,2,3}.js`,浏览器内换基准 `(1+day_{N+1})/(1+day1)-1`(day1=t0收盘,故 T+N=day_{N+1} 相对 day1);买入价=`buy_price×(1+day1/100)`。数据更新后无需额外构建,重跑 `build_html_closebuy.py` 仅当壳改动。
- **口径差异(诚实)**:原版 tp1/tp2 首达日、7%止损日、maxR 基于"开盘买入+盘中价",本版不沿用;本版 maxR/finR 用收盘序列重算(无盘中价,冲高按收盘近似下界)。entered 标记是聚宽实际交易(开盘买入),仅供参考。

## 4个月静态版(原始交付,2026-03~06)
- `event_study_dragon_3to6.csv/.json` + `龙头候选池forward回看表.html`(内嵌JSON,双击直开)+ `summary.md`。

## 交付物
- `event_study_dragon_3to6.csv` — 全候选明细(v1/v2/v3 × date × code,2802 行)
- `event_study_dragon_3to6.json` — 喂 HTML 的数据
- `龙头候选池forward回看表.html` — 单文件离线回看表(内嵌 JSON,**双击直开**)
- `summary.md` — trend_core vs deep_water 按月对照(只报数,不下结论)

## 验证(关键)
- **v3 候选池对聚宽 `jq_v140D` 日志精确吻合**:验收门 03-02~03-06 共 15/15 stock-day,
  score(±0.001)/tpl/open_ratio/close_to_high/auc_ratio 全对上(`run_gate.py`)。03-31 修 universe 后又多对 3 个点。
- **v1/v2**:聚宽那次回测是 v3-default,没有 v1/v2 交易日志 → v1/v2 是**本地 code-faithful 移植**
  (照搬源码 4254-4356 的打分),作用在已验证的同一批竞价/日线输入上,**无 ground truth**。

## 口径与已知偏差(诚实记录)
- 日线:QMT 1d **不复权**(实证:聚宽该回测用不复权,raw 精确吻合;用 front 复权对有分红的票会漂)。
- 竞价:QMT 1m 首根。`open_ratio=open/前日close-1`;`auc_ratio=首根vol/前日1d_vol`;`auc_amount=首根amount`。
- forward:t=0 选股日开盘价买入,裸持 day1-20 累计收益,**对全部候选算**(含 trend_core 对照组)。
  不满 20 日标 `window_incomplete`(今天=06-25,6月候选 forward 多不满,不补0不外推)。
- **entered**:来自聚宽 v3-default 实际交易(`ENTRY_FEATURE_LOG`,只取 `entry_type=dragon_follow` 的早盘候选买入,
  16 笔;另有 9 笔 `shadow_satellite` 是盘中卫星机制、非候选池,正确不计入)。v1/v2 视图的 entered 也是这一份实际(v3)运行。
- **universe**:剔创/科/北 + 上市<50自然日。**不按当前名剔 ST/退**(QMT 只有当前名,用它会前视:
  002082 现名 ST万邦,但 03-31 是非ST的 rank1 龙头候选,会被误剔)。残留小偏差:当期ST误纳(量价难过门槛,影响小)、
  3个月内退市票若已从 QMT 列表消失则不可recover(罕见)。

## 重新跑(QMT 模拟端要开着,:58610)
```
.venv\Scripts\python run_gate.py        # 验收门:v3 对账聚宽 15/15
.venv\Scripts\python run_full.py        # 全程三版候选池+forward(可断点续传,~10-15min)
.venv\Scripts\python parse_jq_logs.py   # 解析聚宽 ENTRY/EXIT
.venv\Scripts\python build_outputs.py   # join → CSV/JSON/summary
.venv\Scripts\python build_html.py       # 生成回看表 HTML
```
- 环境:专用 `.venv`(py3.10 + pandas)。`xtquant` 走 `D:\国金QMT交易端模拟\bin.x64\Lib\site-packages`(sys.path 注入)。
- 复现方法记忆:`~/.claude/.../memory/qmt-1m-firstbar-equals-jq-auction.md`

## 文件
- `repro_core.py` — 选股链移植 + 三套打分 + QMT 数据层(核心)
- `run_gate.py` / `run_full.py` / `parse_jq_logs.py` / `build_outputs.py` / `build_html.py`
- `_*.csv` / `_*.json` — 中间件(pool明细/forward缓存/entry/exit/detail缓存/checkpoint)
