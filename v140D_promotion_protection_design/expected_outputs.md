# 预期输出（expected_outputs）

脚本跑完后，在 `promotion_protection_outputs/` 下生成 5 个文件（4 份结果 +
1 个 zip）。全部相对路径，无绝对 D:\ 路径，CSV 建议无 BOM。

## 1. jq_promotion_protection_counterfactual_cases.csv （5 变体 x 7 事件 = 35 行）

列：
- variant：5 个小写 spec 变体 ID 之一
- ledger_key / stock / block_date / phase
- block_return / block_pnl_val：realized 块收益率 / 块盈亏额
- position_value：block_pnl_val / block_return 反推的仓位市值
- captured_extra_return：变体相对块价多拿的收益率（PROXY 模式恒为 0）
- counterfactual_pnl_val = block_pnl_val + position_value * captured_extra_return
- delta_pnl_val：counterfactual_pnl_val - block_pnl_val
- proxy_distortion_flag：trail 类=high，MA5 类/baseline=low
- proxy_mode：True 表示该事件未取到路径（本地无 jqdata）

预期：pv_immediate_full_exit 行 captured_extra_return 全 0、delta 全 0。
JQDATA 模式下其余变体出现非 0 值；PROXY 模式下全 0（预期，不是 bug）。

## 2. jq_promotion_protection_summary.csv （独立文件，6 行：REALIZED_BASELINE + 5 变体）

列：variant, net_pnl, gross_profit, gross_loss, top1, top3, top5,
top3_share_of_net, top5_share_of_net, net_excl_top5, proxy_distortion_flag

REALIZED_BASELINE 行应复现已知锚点（用于自检）：
- net_pnl = 59822
- top1 = 22804
- top3 = 52735
- top5 = 70743
- top3_share_of_net ~= 0.8815
- top5_share_of_net ~= 1.1826
- net_excl_top5 = -10921

若 REALIZED_BASELINE 这几个数对不上，说明 BASELINE_LEDGER 被改坏了，
先排查台账再看变体。集中度对**全部 5 个变体**各算一遍，横向可比。

## 3. jq_promotion_protection_sensitivity.csv （网格扩散，无 best 标记）

trail_pct {0.03,0.05,0.08} x keep_frac {1/3,0.5} x 5 变体 = 30 行。
列含 variant / trail_pct / keep_frac / net_pnl / top5_share_of_net /
net_excl_top5 / proxy_distortion_flag。只铺开看扩散，不标最优、不排序选参。
（delay 不在网格里——它是 pv_delay_1d_confirm 的固定 1 日定义，不是旋钮。）

## 4. jq_promotion_protection_report.md

人读摘要。顶部标 MODE: PROXY 或 MODE: JQDATA，并单独声明 trail 类
close_proxy 失真。正文给出 summary 表（含 proxy_distortion_flag 列）+ 判读
指引（盯 net_excl_top5，不是 net_pnl；推得更负=扣分）。

## 5. v140D_promotion_protection_counterfactual_outputs.zip

脚本内用 zipfile 打包上面 4 个文件。zip 内只保留**文件名**，不带目录前缀。

## 自检清单（跑完核对）

- [ ] REALIZED_BASELINE 的 net_pnl=59822、top5=70743、net_excl_top5=-10921
- [ ] cases 共 35 行，summary 共 6 行，sensitivity 共 30 行
- [ ] pv_immediate_full_exit 的 delta_pnl_val 全 0
- [ ] proxy_distortion_flag：pv_trail_from_high=high，其余=low
- [ ] report.md 顶部正确标注当前 MODE 且含 trail 失真声明
