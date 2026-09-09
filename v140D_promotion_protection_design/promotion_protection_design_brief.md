# v140D Promotion Protection 研究设计（research-only）

## 0. 这份东西是什么 / 不是什么

**是**：一个"反事实（counterfactual）研究设计包"。用来回答一个问题——
v1.4.0D observer 里那条 `shadow_no_promotion_take_profit` 规则（卫星仓在
"没等到晋级"时提前止盈），到底是不是砍早了？如果换成 5 种"保护变体"
继续持有，会多赚/少赚多少？更重要的是：这会不会让本来已经很严重的
**利润集中度**（Top5 占净利 118%）变得更糟。

**不是**：
- 不是一个能跑的策略，不是回测，不是实盘配置。
- 脚本里没有 `order / order_value / order_target / order_target_value /
  run_backtest / schedule_function`，一行下单都没有。
- 不替任何决策拍板。只产出"如果当时这么做、数字会变成什么样"的对照表。

## 1. 背景事实（来自已落盘审计，不是新跑的）

- 全样本 37 笔成交，净利 **59822** 元。
- 集中度（`v140D_profit_concentration_review.csv` / `top_profit_dependency.csv`）：
  - Top1 = 22804（净利的 38.12%）
  - Top3 = 52735（净利的 88.15%）
  - Top5 = 70743（净利的 **118.26%**，已超过净利本身）
  - 剔除 Top5 后净利 = **-10921**（转负）
- 7 笔 `shadow_no_promotion_take_profit` 事件都是**小卫星仓**，单笔
  672 ~ 2299 元，全部是正收益但很小（详见 event casebook）。

**核心张力**：这 7 笔砍早的都是小钱。就算保护变体让它们多拿几个点，
绝对额也有限；而真正决定净利的是那 3-5 笔大肉。所以这次研究的真问题
不是"能不能多赚"，而是——**多赚的钱落在谁头上**。如果只是把大winner
撑得更大，集中度风险（净利全靠少数几笔）只会恶化，不会改善。

## 2. 5 个保护变体（spec 锁定，小写命名）

| 变体 ID | 含义 | proxy_distortion_flag |
|---|---|---|
| pv_immediate_full_exit | 维持原样：晋级块当天一次性全退（realized 基线，extra=0） | low |
| pv_half_exit_hold_half | 半仓块当天出；另半仓持到「收盘跌破 MA5 或第 5 日」先到者退 | low |
| pv_delay_1d_confirm | 块当日不退；次日跌破 MA5 或收益负则次日出，否则持到 MA5/第 5 日 | low |
| pv_trail_from_high | 从块后新高回撤 trail_pct 止损出 | **high** |
| pv_downgrade_small_pos | 只留 keep_frac 小仓持到「跌破 MA5 或第 5 日」（非 keep_frac×trail） | low |

退出口径关键：half / delay / downgrade 三个变体用**收盘价 vs 当日 MA5**
（5 日收盘均线）判退；取价窗口向前多取 4 个交易日，保证块当天就能算 MA5。
MA5 用收盘价是 close_proxy 下**可靠**的口径。

默认旋钮：trail_pct=0.05，keep_frac=1/3，持有上限 5 个交易日。
敏感性网格（只看扩散、不标 best）：trail_pct ∈ {0.03, 0.05, 0.08}，
keep_frac ∈ {1/3, 0.5}。delay 不入网格——它是 pv_delay_1d_confirm 的固定
1 日定义，不是旋钮。

## 3. 反事实口径（怎么把"多拿的点"折回组合）

对每个事件：
1. `position_value = block_pnl_val / block_return`（用 realized 块收益
   反推当时仓位市值）。
2. `captured_extra_return` = 变体在"块后价格路径"上相对块收盘价多拿的
   收益率（见脚本第 5 节各 scorer）。
3. `counterfactual_pnl_val = block_pnl_val + position_value *
   captured_extra_return`。
4. 把这 7 笔替换进 37 笔台账，**重算** net / Top1 / Top3 / Top5 /
   net_excl_top5。

## 4. 判读规则（关键，别只看净利）

- 只看 `net_pnl` 上升 = 容易被大肉撑大骗到。
- 真正要盯的是 **net_excl_top5**（剔除前 5 大赢家后的净利）：
  - 若某变体把 net_excl_top5 抬高（利润基盘变宽）→ 才算真改善。
  - 若 net_pnl 上升但 top5_share_of_net 同时上升 → 是集中度副作用，
    风险更集中，不是好事。

## 5. 已知失真 / 不要过度解读

- **close_proxy 失真**：块后路径用的是**日线 close/high**。trailing
  from high 在日线上看不到盘中真实高点，所以 `captured_extra_return`
  是**排序级（ranking-only）**的，不能当成可成交的真实估计。
- 7 笔里有 4 笔在 pre-OOS 段（亨通/赛伍/新金路#2/西藏城投），3 笔在
  OOS 段（江特/福晶/深科技）。样本极小，任何结论都是"方向性提示"。
- 这份设计**不调参为收益**：网格只是为了看稳健性，不是找最优解。

## 6. 怎么用（落地）

把 `research_v140D_jq_promotion_protection_counterfactual.py` 贴进聚宽
research notebook 跑（详见 README）。本地无 jqdata 时它进 PROXY 模式，
只有 pv_immediate_full_exit 有意义，其余变体 extra=0——这是预期行为，用来
先验证管线，不是结果。
