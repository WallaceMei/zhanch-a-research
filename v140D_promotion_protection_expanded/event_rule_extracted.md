# event_rule_extracted.md — promotion-block 事件判定规则（S1 交接物）

> 本文件是 SPEC「v140D Promotion Protection 样本扩展研究」**S1 段**的唯一交接物。
> S1 只做一件事：**只读**现有策略代码，把 promotion-block 事件的判定规则提取成大白话。
> **本段不写检测器、不跑扫描、不算变体、不下 VERDICT。** 写完即停，等用户放行 S2。
> 本文件自包含：下一段（可能是新会话）只靠本文件 + 已验收脚本即可接手。

## 0. 规则出自哪个文件（只读，未改动）

全部规则来自 `战车A龙头3_v1.4.0D_observer.py`（产生原始 7 笔的 observer 分支，
research-only、非主线、非实盘）。关键函数与行号：

| 环节 | 函数 | 行号 |
|---|---|---|
| 信号入池（watch pool） | `shadow_after_market_update` | 3327 起 |
| 次日确认买入判定 | `_shadow_get_confirm_snapshot` + `_shadow_rule_d_deep_water_passes` | 3393 / 3446 |
| 卫星买入落地 | `_shadow_submit_satellite_buy` | 3519 |
| **block 事件触发** | `should_block_promotion_take_profit` | 3703 |
| 卫星出场总检查（含 block） | `shadow_rotation_exit_check` | 3725 |
| MA5 估算 | `_estimate_intraday_ma5` | 274 |
| 交易日计数 | `_shadow_trade_days_elapsed` | 3136 |

`战车A龙头3.py` / `research_v14C_D_candidate_research.py` 也读了，确认 deep_water
龙头候选的"上游池"在龙头扫描器里生成（见 §3 依赖风险），但 block 事件本身的判
定完全落在上面 observer 函数链里。

---

## 1. 一个 promotion-block 事件，完整链路（大白话）

一个事件不是凭空冒出来的，它必须先变成"影子卫星仓"，再在持有中被 block 规则
止盈。三步：

### 第 1 步：信号入池（收盘后，T0 日）
- 当天龙头候选里，凡是 **tpl == 'deep_water' 且 entry_type == 'dragon_follow'**
  的票，如果**当天没被买成核心仓**（"core_candidate_not_bought"），就被放进
  `shadow_watch_pool` 当观察对象。
- 记下：signal_date = T0、signal_price = T0 当时价、signal_source =
  'BIGMEAT_POOL_TOP'、signal_entry_type = 'deep_water'。
- 观察有效期 **3 个交易日**，过期或已持仓/被拉黑就移出池子。
- ⚠️ 上游：这些 deep_water 龙头候选本身是龙头扫描器（dragon_score 等）算出来
  的，不在 observer 里 —— 见 §3 第 1 条依赖风险。

### 第 2 步：次日确认买入（T0+1 ~ T0+3）
观察池里的票，在信号后第 1/2/3 个交易日盘中做一次"确认"。先取一张快照
（`_shadow_get_confirm_snapshot`），快照能成立的前置条件：
- days_after_signal ∈ {1,2,3}（否则 out_of_range）；
- 不能涨停（current ≥ high_limit×0.999 直接 reject = 'limit_up'）；
- 拿得到前一日收盘/成交量、当日分钟成交量与分钟最高价、MA5。

快照成立后，进场判定 `_shadow_rule_d_deep_water_passes` **全部满足才买**（Rule D
deep water）：
- `ret_from_signal` = 现价/signal_price − 1 **≥ 0.05**（自信号涨≥5%）；
- `day_ret` = 现价/前收 − 1 **≥ 0.05**（当日涨≥5%）；
- `volume_ratio_vs_prev` = 当日量/前日量 **在 [1.0, 2.0] 之间**（放量但不爆量）；
- `ma5_distance` = 现价/MA5 − 1 **≤ 0.10**（不追离 MA5 太远）；
- `close_to_day_high` = 现价/当日最高 **≥ 0.97**（贴着当日高点，没怂回）；
- `is_limit_up` == 0（非涨停）。
- 另外还要：单卫星槽位空着（**15% × 1 个槽**）、没被暂停（market_down /
  各种冷却 / no_new_position 都会暂停新买）。
- 买入价 = 确认日现价，confirm_date = 确认日，max_hold_days = 5，仓位约 15%
  （受总仓位上限 cap 动态削减）。

这一步买进来的，就是"影子卫星仓"（slot_type='satellite' /
strategy_tag='shadow_rotation'）。

### 第 3 步：block 触发 = promotion-block 事件（持有期内盘中）
持有期间每次出场检查（`shadow_rotation_exit_check`），对每个卫星仓：
- pnl = 现价/持仓均价 − 1；
- MA5 = (前 4 日收盘之和 + 当前价) / 5；below_ma5 = 现价 < MA5；
- **block 触发条件**（`should_block_promotion_take_profit`，第 3720 行）：

  > **pnl ≥ 0.03（盈利≥3%） 且 not below_ma5（现价在 MA5 之上、仍强）**

- 一旦触发 → 出场，exit_reason = **`shadow_no_promotion_take_profit`** ——
  **这就是我们要检测的 promotion-block 事件**。
- 优先级：这条 block 检查排在所有其它卫星出场原因**之前**（先判它，再判
  max_hold_5d / stop_loss_6pct / below_ma5_loss / stale_no_profit）。所以只要
  当次盈利≥3%且在 MA5 上，就一定先被 block 止盈，不会落到别的原因。

---

## 2. "未能晋级"到底是什么意思（关键警告：它本身是 proxy）

代码里反复写明（第 7、9、3707、3760 行）：

> **"当前 no_promotion 是 observer proxy，不是 D3 replay 的严格
> ROLE_PROMOTION_EXECUTE 等价实现。"**

大白话：真正的 D3 设计里，卫星票如果够格会被"晋级"成核心/龙头仓继续跑。但这个
observer **没有**真去模拟晋级流程。它用一个**代理条件**替代："卫星仓盈利≥3% 且
还站在 MA5 上 → 视为'本该晋级但没晋级'→ 直接止盈了结。" 所以：

- **"晋级失败"在本规则里 = 满足了 block 止盈代理条件（≥3% 且强）的卫星仓**。
  没有独立的"尝试晋级 / 晋级被拒"事件，block 本身就是那个代理。
- 因此**检测器只能复刻这个代理条件**（卫星仓 pnl≥3% 且 现价≥MA5），
  **不许自己另发明一个"晋级模型"**——那会偏离原始 7 笔的口径。

---

## 3. 复现原始 7 笔会遇到的依赖与失真（必须先讲清，关系到 S2 能不能过门）

原始 7 笔（亨通/赛伍/新金路/西藏城投/江特/福晶/深科技）是上面这条**盘中
（intraday）** observer 链跑出来的。要在研究环境用日线复现，存在三层落差：

1. **上游依赖：deep_water 龙头候选池**。第 1 步入池的票来自龙头扫描器
   （dragon_score / BIGMEAT 池），逻辑在 `战车A龙头3.py` 一侧，**不在 observer**。
   想从零复刻进场链，必须连这套候选生成一起复刻 —— 这是**最大的复现成本与
   偏差来源**。

2. **盘中口径 vs 日线 close-proxy**。进场确认用的是分钟级数据（当日分钟量、
   分钟最高价、盘中现价），block 触发也是**盘中**判定。研究环境若用日线收盘做
   代理：
   - MA5：observer 的 `_estimate_intraday_ma5` = (前 4 日收盘 + 当前价)/5；
     用当日收盘代当前价时，正好退化成**标准 5 日收盘均线** —— 这部分 close-proxy
     **可靠**（和已验收脚本里 MA5 口径一致）。
   - 但 block 是"盘中只要触到 ≥3% 且在 MA5 上就止盈"，日线只能看收盘那一个点，
     **会漏掉/错配盘中触发后尾盘回落的情形**。所以日线检测是"代理的代理"，
     必然近似。

3. **原始 7 笔已有权威来源**。`v140D_smoke_test_audit/04_entry_exit/`
   （exit_outcome_events.csv）与 `log/jq_v140D_*.log.txt` 里已经记录了这 7 笔的
   精确成交（exit_reason='shadow_no_promotion_take_profit'）。复现校验时应以这份
   **既有 observer 日志/审计**为基准逐笔对照，而不是假装从日线重算能 1:1 还原。

**结论（留给用户的判断，S1 不替你拍板）**：S2 复现 7 笔时有两条路，各有取舍——
- **路线 A**：直接以既有 observer 日志/审计的 7 笔为基准，研究侧只用日线
  close-proxy 重建"事件特征"，明确承认是 proxy-of-proxy。成本低，但复现是
  "对账"而非"独立重算"。
- **路线 B**：在研究环境重刻 deep_water 候选 + 确认链 + block 链（尽量逼近盘中）。
  独立性强，但成本高、且日线无法还原盘中触发，仍有系统性偏差。

**这两条路怎么选、以及"捞回几笔算过门"，属于研究判断，归用户。S1 不自行决定。**

---

## 4. 原始 7 笔复现预期（S2 要逐笔核对的清单）

下面是 7 笔的基准事实（来自既有审计，仅供 S2 对账，不是 S1 重算结果）：

| 名称 | 代码 | block 日期 | block 时盈利 | hold_days | 阶段 |
|---|---|---|---|---|---|
| 亨通光电 | 600487.XSHG | 2026-01-28 | +7.63% | 2 | pre_oos |
| 赛伍技术 | 603212.XSHG | 2026-02-04 | +4.68% | 1 | pre_oos |
| 新金路 | 000510.XSHE | 2026-02-27 | +9.14% | 2 | pre_oos |
| 西藏城投 | 600773.XSHG | 2026-03-13 | +5.57% | 2 | pre_oos |
| 江特电机 | 002176.XSHE | 2026-04-24 | +9.75% | 2 | oos |
| 福晶科技 | 002222.XSHE | 2026-05-07 | +5.81% | 1 | oos |
| 深科技 | 000021.XSHE | 2026-05-27 | +9.60% | 2 | oos |

S2 过门标准（SPEC §1.3）：用提取的规则跑检测器，必须能捞回**大部分**这 7 笔；
没捞到的逐笔说明原因（日期边界 / 数据缺失 / 口径差异）。**捞不回大部分 = 检测器
错，停下报告，不许往下扫全量。**

注意：全部 7 笔 block 时盈利都 ≥4.68%、且都是"还在涨"时被止盈 —— 与 §1 第 3 步的
"pnl≥3% 且在 MA5 之上"代理条件一致，可作为规则提取正确性的旁证。

---

## 5. S1 段收尾

- 本段只读了 observer/策略代码，**未改任何文件**，未写检测器，未扫描，未算变体，
  未下 VERDICT。
- 5 个 protection 变体（§SPEC 2）将在 S4 直接复用已验收脚本
  `research_v140D_jq_promotion_protection_counterfactual.py` 的 `score_*`，本段不碰。
- 规则口径是否正确、路线 A/B 怎么选、过门阈值定多少 —— 这些研究判断归用户。

**本段完成，等待用户放行 S2，未擅自推进。**
