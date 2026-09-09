# v1.4.0C ???????????

## 0. ????

* ?????? `role_rotation_result_bundle V140C` ??????
* ?????????????????????????? `git add`?? `git commit`?
* ???? v1.4.0C ?????????????? train / validation / oos??????????????????fast_loss???????? cap ???

## 1. ????

* v1.4.0C / role_rotation_observer ????? 61.91%??? 69.16%????? -22.42%?Sharpe 1.65??? 29.31%?
* ?? baseline_core_only ????? 17.81%?v1.4.0C ??????? baseline_core_satellite 17.06%?????????????????/????????????????
* ?????train 15.68%?validation 10.19%?oos 28.29%?????????????????
* ?????????????????? 10.70%????????? `sensitivity_return_std=Fail`?`profit_concentration_top3=Fail`??? fast_loss ????????????
* ????????????????? fast_loss ?????????????????????????????????????

## 2. ????

```text
          section      role  trade_count  win_count  loss_count  total_pnl_val  avg_pnl_pct  median_pnl_pct  avg_hold_days  big_meat_10_count  super_meat_20_count  fast_loss_count  small_loss_count  win_rate trade_category                   reason hold_bucket  pnl_abs_share  loss_share_if_loss  profit_share_if_profit
          by_role      core           91         26          65   5.605505e+05     0.027711       -0.021523       6.725275                 15                    7               49                36  0.285714            NaN                      NaN         NaN       0.218497                 NaN                0.355275
          by_role satellite           25          8          17   2.955385e+04     0.004339       -0.051449       4.120000                  5                    3               16                 2  0.320000            NaN                      NaN         NaN       0.011520                 NaN                0.018731
by_trade_category       NaN           75         17          58   3.871552e+05     0.021489       -0.030043       5.960000                 11                    6               46                31  0.226667           core                      NaN         NaN       0.150910                 NaN                0.245378
by_trade_category       NaN           16          9           7   1.733953e+05     0.056880        0.018473      10.312500                  4                    1                3                 5  0.562500  promoted_core                      NaN         NaN       0.067588                 NaN                0.109897
by_trade_category       NaN           25          8          17   2.955385e+04     0.004339       -0.051449       4.120000                  5                    3               16                 2  0.320000      satellite                      NaN         NaN       0.011520                 NaN                0.018731
   by_exit_reason       NaN           45          0          45  -3.569260e+05    -0.028155       -0.030043       4.577778                  0                    0               30                33  0.000000            NaN      core_below_ma5_loss         NaN       0.139126            0.361376                     NaN
   by_exit_reason       NaN           13         13           0   6.822849e+05     0.217434        0.082067      13.615385                  6                    4                0                 0  1.000000            NaN       core_drawdown_exit         NaN       0.265948                 NaN                0.432430
   by_exit_reason       NaN           17          0          17  -4.469183e+05    -0.087254       -0.078181       2.411765                  0                    0               16                 0  0.000000            NaN           core_stop_loss         NaN       0.174205            0.452490                     NaN
   by_exit_reason       NaN            5          0           5  -3.878912e+04    -0.047141       -0.051130       2.800000                  0                    0                5                 1  0.000000            NaN satellite_below_ma5_loss         NaN       0.015120            0.039273                     NaN
   by_exit_reason       NaN            9          8           1   1.974092e+05     0.131105        0.117110       7.000000                  5                    3                0                 1  0.888889            NaN       satellite_max_hold         NaN       0.076948                 NaN                0.125117
   by_exit_reason       NaN           11          0          11  -1.290663e+05    -0.075979       -0.069652       2.363636                  0                    0               11                 0  0.000000            NaN      satellite_stop_loss         NaN       0.050309            0.130675                     NaN
   by_exit_reason       NaN           16         13           3   6.821100e+05     0.152837        0.107337      11.750000                  9                    3                3                 3  0.812500            NaN       weak_core_replaced         NaN       0.265880                 NaN                0.432319
   by_hold_bucket       NaN           10          0          10  -8.470532e+04    -0.034466       -0.032718       2.000000                  0                    0               10                 6  0.000000            NaN                      NaN          2d       0.033017            0.085761                     NaN
   by_hold_bucket       NaN           12          0          12  -1.680002e+05    -0.055878       -0.056959       3.000000                  0                    0               12                 3  0.000000            NaN                      NaN          3d       0.065485            0.170095                     NaN
   by_hold_bucket       NaN           19          3          16  -1.782580e+05    -0.037303       -0.037859       4.421053                  0                    0               16                 7  0.157895            NaN                      NaN        4-5d       0.069483            0.180480                     NaN
   by_hold_bucket       NaN           26         13          13   2.053772e+05     0.047561        0.009431       7.076923                  7                    3                0                10  0.500000            NaN                      NaN       6-10d       0.080054                 NaN                0.130167
   by_hold_bucket       NaN           27          0          27  -4.295676e+05    -0.061415       -0.063008       1.000000                  0                    0               27                 8  0.000000            NaN                      NaN        <=1d       0.167441            0.434923                     NaN
   by_hold_bucket       NaN           22         18           4   1.245258e+06     0.217081        0.118969      16.545455                 13                    7                0                 4  0.818182            NaN                      NaN        >10d       0.485390                 NaN                0.789241
```

* ??????????????????? 29.31%?????? + ???? + ???????
* ???? 16.0????? 56.25%????????? 173395?
* ?????? `total_post_promotion_pnl_amount` ? -108974????????????????????????/????????
* fast_loss: 65 ???? -880790?????????????????
* big_meat + super_meat ???????????big_meat 10 ??super_meat 10 ?????????????????

## 3. ??

```text
                  section           group  sample_count  avg_signal_score  median_signal_score  min_signal_score  max_signal_score  avg_pnl_pct  avg_hold_days                                                        note
signal_score_distribution       all_sells           116          0.812352             0.813591          0.701045          1.035685     0.022674       6.163793
signal_score_distribution            wins            34          0.818884             0.818055          0.701045          1.035685     0.191498      12.294118
signal_score_distribution          losses            82          0.809644             0.813591          0.702569          0.960368    -0.047326       3.621951
signal_score_distribution       fast_loss            65          0.810101             0.813357          0.702569          0.960368    -0.053295       2.369231
signal_score_distribution   big_meat_gt10            20          0.830216             0.837251          0.707400          1.035685     0.302872      13.950000
signal_score_distribution super_meat_gt20            10          0.827927             0.840041          0.707400          0.937814     0.464890      15.200000
           score_quantile    (0.7, 0.744]            24          0.722793                  NaN               NaN               NaN     0.015012            NaN  win_rate=33.33%; total_pnl=42326; fast_loss=12; big_meat=3
           score_quantile  (0.744, 0.791]            23          0.767574                  NaN               NaN               NaN    -0.007310            NaN win_rate=21.74%; total_pnl=-42645; fast_loss=14; big_meat=3
           score_quantile  (0.791, 0.829]            23          0.812962                  NaN               NaN               NaN     0.059500            NaN win_rate=26.09%; total_pnl=378688; fast_loss=14; big_meat=4
           score_quantile  (0.829, 0.872]            23          0.852784                  NaN               NaN               NaN     0.021967            NaN win_rate=34.78%; total_pnl=159897; fast_loss=14; big_meat=5
           score_quantile  (0.872, 1.036]            23          0.909542                  NaN               NaN               NaN     0.024535            NaN  win_rate=30.43%; total_pnl=51839; fast_loss=11; big_meat=5
```

* ?? `signal_score` ??????????????????????????????????????? DRAGON_MIN_SCORE?
* fast_loss ? big_meat ?????????????????????? entry_open_ratio?entry_day_ret?entry_close_to_high?entry_volume_ratio?entry_auc_ratio?entry_ma5_distance?entry_ma10_distance?entry_turnover?entry_rank?entry_score?sector_strength_rank?breadth_up_ratio?market_state?market_10d_ret?
* ??????????????????????????????????????????? fast_loss ?????????

??/??????????

```text
             section                                                                           group  sample_count  avg_signal_score  median_signal_score  min_signal_score  max_signal_score  avg_pnl_pct  avg_hold_days                                  note
missing_feature_need       Needs MA5 trend strength confirmation / volume support check on entry day            50               NaN                  NaN               NaN               NaN          NaN            NaN from v14C_entry_feature_need_list.csv
missing_feature_need Needs short-term price volatility filter on entry day / high open ratio control            28               NaN                  NaN               NaN               NaN          NaN            NaN from v14C_entry_feature_need_list.csv
missing_feature_need       Needs call auction volume ratio sanity filter / market index state filter             4               NaN                  NaN               NaN               NaN          NaN            NaN from v14C_entry_feature_need_list.csv
```

## 4. ?????

```text
               section                         risk_item     value                         threshold_or_context assessment                                                        evidence
   segment_performance                      full segment  0.619123 train / validation / oos all must be checked       Pass         return=61.91%, dd=-22.42%, sharpe=1.65, win_rate=29.31%
   segment_performance                     train segment  0.156791 train / validation / oos all must be checked       Pass         return=15.68%, dd=-22.42%, sharpe=0.95, win_rate=20.29%
   segment_performance                validation segment  0.101869 train / validation / oos all must be checked       Pass          return=10.19%, dd=-8.05%, sharpe=1.58, win_rate=40.00%
   segment_performance                       oos segment  0.282852 train / validation / oos all must be checked       Pass          return=28.29%, dd=-8.14%, sharpe=4.00, win_rate=45.45%
   final_overfit_check            sensitivity_return_std  0.107029                                        < 10%       Fail                                                 status=Unstable
   final_overfit_check                   cost_1.5x_decay  0.132396                                        < 50%       Pass                                                status=Low decay
   final_overfit_check                   cost_2.0x_decay  0.264959                                        < 75%       Pass                                         status=Acceptable decay
   final_overfit_check         profit_concentration_top3  1.045050                                        < 70%       Fail                                             status=Concentrated
parameter_perturbation                  total_return_std  0.107029                          std < 10% preferred       Fail                                             range=24.34%~67.81%
    sensitivity_detail              promotion_margin=8.0  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail             promotion_margin=10.0  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail             promotion_margin=12.0  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail            satellite_min_pnl=0.02  0.610052                      compare baseline 61.91%      Watch           return=61.01%, dd=-22.76%, sharpe=1.63, promotions=17
    sensitivity_detail            satellite_min_pnl=0.03  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail            satellite_min_pnl=0.05  0.243392                      compare baseline 61.91%      Watch           return=24.34%, dd=-22.04%, sharpe=0.83, promotions=10
    sensitivity_detail           core_drawdown_weak=0.06  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail           core_drawdown_weak=0.08  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail            core_drawdown_weak=0.1  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail          satellite_slot_ratio=0.1  0.550772                      compare baseline 61.91%      Watch           return=55.08%, dd=-21.22%, sharpe=1.57, promotions=16
    sensitivity_detail         satellite_slot_ratio=0.15  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail                max_total_cap=0.75  0.619123                      compare baseline 61.91%      Watch           return=61.91%, dd=-22.42%, sharpe=1.65, promotions=16
    sensitivity_detail                 max_total_cap=0.9  0.678150                      compare baseline 61.91%      Watch           return=67.81%, dd=-19.88%, sharpe=1.77, promotions=17
      cost_sensitivity                     baseline_cost  0.619123                decay should not destroy edge       Pass         return=61.91%, decay=0.00%, dd=-22.42%, win_rate=29.31%
      cost_sensitivity                         1.5x_cost  0.537153                decay should not destroy edge       Pass        return=53.72%, decay=13.24%, dd=-23.86%, win_rate=28.21%
      cost_sensitivity                           2x_cost  0.455081                decay should not destroy edge       Pass        return=45.51%, decay=26.50%, dd=-25.19%, win_rate=27.12%
      cost_sensitivity                   double_slippage  0.491245                decay should not destroy edge       Pass        return=49.12%, decay=20.65%, dd=-24.58%, win_rate=27.12%
  profit_concentration                              core  1.592871        final check says top3 < 70% preferred      Watch  trade_count=75, pnl=387155, top1=0.678, top3=1.593, top5=2.163
  profit_concentration                         satellite  4.355441        final check says top3 < 70% preferred      Watch   trade_count=25, pnl=29554, top1=1.688, top3=4.355, top5=6.099
  profit_concentration                     promoted_core  0.958504        final check says top3 < 70% preferred      Watch  trade_count=16, pnl=173395, top1=0.547, top3=0.959, top5=1.117
  profit_concentration                               all  1.045050        final check says top3 < 70% preferred       Fail trade_count=116, pnl=590104, top1=0.445, top3=1.045, top5=1.419
          position_cap               cap_exceeded_on_buy 10.000000                                    must be 0       Fail                           max_post_buy_ratio=76.45%, cap=75.00%
          position_cap cap_exceeded_after_mark_to_market  8.000000          watch mark-to-market leverage drift      Watch                                       max_post_buy_ratio=76.45%
```

* train / validation / oos ?????????????????????????????
* ???????`satellite_min_pnl=0.05` ?????????????????
* ??????????????1.5x ?????? 53.72%?2x ???? 45.51%?????????????????????
* ????????????? `profit_concentration_top3=Fail`??????????????????
* ????????? train / validation / oos?????????????????

## 5. ??????????

```text
priority           module                    issue                                              evidence                                                                                                                  research_action         do_not_do                   expected_metric                  section                   reason  trade_count  win_count  loss_count  total_pnl_val  avg_pnl_pct  median_pnl_pct  avg_hold_days  big_meat_10_count  super_meat_20_count  fast_loss_count  small_loss_count  win_rate      role hold_bucket
      P1        fast_loss               1~5??????? fast_loss_count=65, loss=880790, share_of_loss=89.18% ????/?????? entry_open_ratio?entry_day_ret?entry_close_to_high?entry_volume_ratio?MA5/MA10 distance??? fast_loss ? big_meat ???? ????????????????? fast_loss_count????????????oos???                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
      P1 fast_loss_reason           core_stop_loss                     count=16, pnl=-430307, avg=-8.85%                                                                                           ? exit_reason ?????????/??????????????         ?????????                ?? reason ????????                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
      P1 fast_loss_reason      core_below_ma5_loss                     count=30, pnl=-269378, avg=-3.12%                                                                                           ? exit_reason ?????????/??????????????         ?????????                ?? reason ????????                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
      P1 fast_loss_reason      satellite_stop_loss                     count=11, pnl=-129066, avg=-7.60%                                                                                           ? exit_reason ?????????/??????????????         ?????????                ?? reason ????????                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
      P1 fast_loss_reason satellite_below_ma5_loss                       count=5, pnl=-38789, avg=-4.71%                                                                                           ? exit_reason ?????????/??????????????         ?????????                ?? reason ????????                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
      P1 fast_loss_reason       weak_core_replaced                       count=3, pnl=-13249, avg=-1.38%                                                                                           ? exit_reason ?????????/??????????????         ?????????                ?? reason ????????                      NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN      fast_loss_by_reason      core_below_ma5_loss         30.0        0.0        30.0  -269378.26375    -0.031170       -0.035652       2.633333                0.0                  0.0             30.0              20.0       0.0       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN      fast_loss_by_reason           core_stop_loss         16.0        0.0        16.0  -430306.66625    -0.088511       -0.079266       2.000000                0.0                  0.0             16.0               0.0       0.0       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN      fast_loss_by_reason satellite_below_ma5_loss          5.0        0.0         5.0   -38789.11500    -0.047141       -0.051130       2.800000                0.0                  0.0              5.0               1.0       0.0       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN      fast_loss_by_reason      satellite_stop_loss         11.0        0.0        11.0  -129066.26475    -0.075979       -0.069652       2.363636                0.0                  0.0             11.0               0.0       0.0       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN      fast_loss_by_reason       weak_core_replaced          3.0        0.0         3.0   -13249.37325    -0.013821       -0.009740       1.000000                0.0                  0.0              3.0               3.0       0.0       NaN         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN        fast_loss_by_role                      NaN         49.0        0.0        49.0  -712934.30325    -0.048831       -0.044667       2.326531                0.0                  0.0             49.0              23.0       0.0      core         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN        fast_loss_by_role                      NaN         16.0        0.0        16.0  -167855.37975    -0.066967       -0.066718       2.500000                0.0                  0.0             16.0               1.0       0.0 satellite         NaN
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN fast_loss_by_hold_bucket                      NaN         10.0        0.0        10.0   -84705.32425    -0.034466       -0.032718       2.000000                0.0                  0.0             10.0               6.0       0.0       NaN          2d
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN fast_loss_by_hold_bucket                      NaN         12.0        0.0        12.0  -168000.20575    -0.055878       -0.056959       3.000000                0.0                  0.0             12.0               3.0       0.0       NaN          3d
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN fast_loss_by_hold_bucket                      NaN         16.0        0.0        16.0  -198516.53000    -0.049424       -0.045979       4.437500                0.0                  0.0             16.0               7.0       0.0       NaN        4-5d
     NaN              NaN                      NaN                                                   NaN                                                                                                                              NaN               NaN                               NaN fast_loss_by_hold_bucket                      NaN         27.0        0.0        27.0  -429567.62300    -0.061415       -0.063008       1.000000                0.0                  0.0             27.0               8.0       0.0       NaN        <=1d
```

* ???????????????????? fast_loss ???
* ????????????????????/???/?????????
* ?????????? + ?????????????

## 6. ????

```text
priority     module                                  issue                                                        evidence                research_action                           do_not_do           expected_metric                 variant  rows  max_pre_buy_total_ratio  max_post_buy_total_ratio  cap_exceeded_on_buy  cap_exceeded_after_mark
      P1   cap_risk ??75% cap ????????90%?????????????????   max_total_ratio=76.45%, avg_total_ratio=45.93%, cap_breach=10    ?? cap ???????????????????? ???? max_total_cap=0.90 ??????? cap         ??/??/??/OOS ????                     NaN   NaN                      NaN                       NaN                  NaN                      NaN
      P2 role_usage      ????????????????????????????????? avg_position_ratio=45.93%, avg_core=39.07%, avg_satellite=6.85% ??????????????????????????????                          ?????????? ??? pnl_post_promotion ??                     NaN   NaN                      NaN                       NaN                  NaN                      NaN
     NaN        NaN                                    NaN                                                             NaN                            NaN                                 NaN                       NaN      baseline_core_only 231.0                 0.712738                  0.716953                  0.0                      0.0
     NaN        NaN                                    NaN                                                             NaN                            NaN                                 NaN                       NaN baseline_core_satellite 231.0                 0.759573                  0.759573                 11.0                     11.0
     NaN        NaN                                    NaN                                                             NaN                            NaN                                 NaN                       NaN  role_rotation_observer 231.0                 0.764538                  0.764538                 10.0                      8.0
```

* ?? 75% cap ??????????????
* `max_total_cap=0.90` ???????????????? cap ?????????????
* ?????????????????????????????

## 7. ????????

```text
priority      module                    issue                                                  evidence                  research_action  do_not_do     expected_metric           section                   reason  trade_count  win_count  loss_count  total_pnl_val  avg_pnl_pct  median_pnl_pct  avg_hold_days  big_meat_10_count  super_meat_20_count  fast_loss_count  small_loss_count  win_rate
      P1   loss_exit           core_stop_loss count=17, total_pnl=-446918, avg_ret=-8.73%, fast_loss=16 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit      core_below_ma5_loss count=45, total_pnl=-356926, avg_ret=-2.82%, fast_loss=30 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit      satellite_stop_loss count=11, total_pnl=-129066, avg_ret=-7.60%, fast_loss=11 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit satellite_below_ma5_loss    count=5, total_pnl=-38789, avg_ret=-4.71%, fast_loss=5 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit       satellite_max_hold    count=9, total_pnl=197409, avg_ret=13.11%, fast_loss=0 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit       weak_core_replaced   count=16, total_pnl=682110, avg_ret=15.28%, fast_loss=3 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P1   loss_exit       core_drawdown_exit   count=13, total_pnl=682285, avg_ret=21.74%, fast_loss=0 ???????1????????????????/??????? ??????????      ???fast_loss??               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit       core_drawdown_exit    count=13, total_pnl=682285, avg_ret=21.74%, big_meat=6      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit       weak_core_replaced    count=16, total_pnl=682110, avg_ret=15.28%, big_meat=9      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit       satellite_max_hold     count=9, total_pnl=197409, avg_ret=13.11%, big_meat=5      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit satellite_below_ma5_loss     count=5, total_pnl=-38789, avg_ret=-4.71%, big_meat=0      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit      satellite_stop_loss   count=11, total_pnl=-129066, avg_ret=-7.60%, big_meat=0      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit      core_below_ma5_loss   count=45, total_pnl=-356926, avg_ret=-2.82%, big_meat=0      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
      P2 profit_exit           core_stop_loss   count=17, total_pnl=-446918, avg_ret=-8.73%, big_meat=0      ???????????????????????????  ????????? big_meat???????????               NaN                      NaN          NaN        NaN         NaN            NaN          NaN             NaN            NaN                NaN                  NaN              NaN               NaN       NaN
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats      core_below_ma5_loss         45.0        0.0        45.0  -356926.02675    -0.028155       -0.030043       4.577778                0.0                  0.0             30.0              33.0  0.000000
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats       core_drawdown_exit         13.0       13.0         0.0   682284.90575     0.217434        0.082067      13.615385                6.0                  4.0              0.0               0.0  1.000000
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats           core_stop_loss         17.0        0.0        17.0  -446918.32625    -0.087254       -0.078181       2.411765                0.0                  0.0             16.0               0.0  0.000000
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats satellite_below_ma5_loss          5.0        0.0         5.0   -38789.11500    -0.047141       -0.051130       2.800000                0.0                  0.0              5.0               1.0  0.000000
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats       satellite_max_hold          9.0        8.0         1.0   197409.22625     0.131105        0.117110       7.000000                5.0                  3.0              0.0               1.0  0.888889
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats      satellite_stop_loss         11.0        0.0        11.0  -129066.26475    -0.075979       -0.069652       2.363636                0.0                  0.0             11.0               0.0  0.000000
     NaN         NaN                      NaN                                                       NaN                              NaN        NaN                 NaN exit_reason_stats       weak_core_replaced         16.0       13.0         3.0   682109.95550     0.152837        0.107337      11.750000                9.0                  3.0              3.0               3.0  0.812500
```

* ????????????????????
* ????????????fast_loss ?????????big_meat ?????????
* ??????????????????????? post-promotion pnl ???????/???????

## 8. ????????

```text
     stage           theme                                           goal                                                   why_now                 allowed                forbidden                     success_metric
v1.4.0C-P1         ??????? ?? entry features??? fast_loss / big_meat ???? ?? v14C_entry_feature_need_list ?????????????????????????          ?????????????? ??????? deep_water?????? ????? fast_loss ? big_meat????????
v1.4.0C-P2 fast_loss ?????                             ????/?????????????                                   fast_loss=65????=880790      ??????????????????                 ????????    fast_loss??? validation/oos ???
v1.4.0C-P3  ???? + ???????                             ?? bear/??????????                  ?????????22%?validation/oos????????????? ? market_state ???/????              ?????/? cap                       ????????????
v1.4.0C-P4      ??????????                       ????????????????????????            promotion_count=16, post_promotion_pnl=-108974              ?????/????                ?????????              post-promotion pnl ??
v1.4.0C-P5           ?????                     ?????????? P1-P4 ?????????                                             ?????????????                 ???????                   ?????? train/validation/oos??????????????
```

* ?????????????????????????? -> ??/????????????
* ????????????????????????fast_loss ?????
* ??? P1-P5 ???????????????????????

## 9. ????

1. ?? v1.4.0C ??????????
2. ?? v1.4.0C ?????????????
3. ?? v1.4.0C ???????????
4. ??????????v1.4.0C-P1 ?????????? entry features???? P2 fast_loss ??????
5. ?????????????? deep_water????????? cap??????????????????????????????
6. ???????????fast_loss ?????????????/????????????????????
