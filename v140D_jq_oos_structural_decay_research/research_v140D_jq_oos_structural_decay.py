# -*- coding: utf-8 -*-
# research_v140D_jq_oos_structural_decay.py
# 运行环境: 聚宽 (JoinQuant) 研究环境 (Research Environment)
# 严禁在策略环境运行！严禁用于实盘！严禁用于调参！

import pandas as pd
import numpy as np
import datetime
import json
from jqdata import *

# === HARDCODED DATA FROM PREVIOUS AUDIT PHASES ===
failed_trades_json = r'''[{"stock":"002824.XSHE","name":"\u548c\u80dc\u80a1\u4efd","entry_date":"2026-04-14","exit_date":"2026-04-24","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast_confirmed","pnl_pct":"-0.37%","pnl_val":-210.0,"hold_days":10,"is_fast_loss":0,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"exit_date_in_oos_cross_period_position"},{"stock":"000762.XSHE","name":"\u897f\u85cf\u77ff\u4e1a","entry_date":"2026-04-14","exit_date":"2026-05-13","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast_confirmed","pnl_pct":"-0.92%","pnl_val":-588.0,"hold_days":29,"is_fast_loss":0,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"exit_date_in_oos_cross_period_position"},{"stock":"002943.XSHE","name":"\u5b87\u6676\u80a1\u4efd","entry_date":"2026-04-16","exit_date":"2026-04-22","entry_type":"shadow_satellite","slot_type":"satellite","stage":"satellite","exit_reason":"shadow_below_ma5_loss","pnl_pct":"-1.43%","pnl_val":-328.0,"hold_days":6,"is_fast_loss":0,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002647.XSHE","name":"\u4ec1\u4e1c\u63a7\u80a1","entry_date":"2026-04-27","exit_date":"2026-05-15","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast","pnl_pct":"-2.95%","pnl_val":-1637.0,"hold_days":18,"is_fast_loss":0,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002560.XSHE","name":"\u901a\u8fbe\u80a1\u4efd","entry_date":"2026-05-07","exit_date":"2026-05-11","entry_type":"shadow_satellite","slot_type":"satellite","stage":"satellite","exit_reason":"minute_stop_loss","pnl_pct":"-5.06%","pnl_val":-1296.0,"hold_days":4,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"603002.XSHG","name":"\u5b8f\u660c\u7535\u5b50","entry_date":"2026-05-13","exit_date":"2026-05-15","entry_type":"shadow_satellite","slot_type":"satellite","stage":"satellite","exit_reason":"minute_stop_loss","pnl_pct":"-6.98%","pnl_val":-1695.0,"hold_days":2,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002943.XSHE","name":"\u5b87\u6676\u80a1\u4efd","entry_date":"2026-05-18","exit_date":"2026-05-25","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast_confirmed","pnl_pct":"-0.20%","pnl_val":-112.0,"hold_days":7,"is_fast_loss":0,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002885.XSHE","name":"\u4eac\u6cc9\u534e","entry_date":"2026-05-18","exit_date":"2026-05-19","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast","pnl_pct":"-3.05%","pnl_val":-1104.0,"hold_days":1,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002491.XSHE","name":"\u901a\u9f0e\u4e92\u8054","entry_date":"2026-05-22","exit_date":"2026-05-26","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast","pnl_pct":"-2.09%","pnl_val":-799.0,"hold_days":4,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"002745.XSHE","name":"\u6728\u6797\u68ee","entry_date":"2026-05-27","exit_date":"2026-05-29","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast","pnl_pct":"-3.17%","pnl_val":-1768.0,"hold_days":2,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"605111.XSHG","name":"\u65b0\u6d01\u80fd","entry_date":"2026-05-28","exit_date":"2026-05-29","entry_type":"dragon_follow","slot_type":"core","stage":"full","exit_reason":"dragon_fail_fast","pnl_pct":"-3.07%","pnl_val":-1045.0,"hold_days":1,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"},{"stock":"605589.XSHG","name":"\u5723\u6cc9\u96c6\u56e2","entry_date":"2026-05-28","exit_date":"2026-05-29","entry_type":"shadow_satellite","slot_type":"satellite","stage":"satellite","exit_reason":"minute_stop_loss","pnl_pct":"-5.27%","pnl_val":-1032.0,"hold_days":1,"is_fast_loss":1,"is_big_meat_10":0,"is_super_meat_20":0,"oos_classification_basis":"entry_date_in_oos"}]'''
watch_adds_json = r'''[{"date":"2026-04-16","log_type":"WATCH_POOL_ADD","stock":"002240.XSHE","name":"\u76db\u65b0\u9502\u80fd","signal_date":"2026-04-16","signal_price":49.8,"signal_score":0.7091,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-16","log_type":"WATCH_POOL_ADD","stock":"002738.XSHE","name":"\u4e2d\u77ff\u8d44\u6e90","signal_date":"2026-04-16","signal_price":85.49,"signal_score":0.6574,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-16","log_type":"WATCH_POOL_ADD","stock":"002756.XSHE","name":"\u6c38\u5174\u6750\u6599","signal_date":"2026-04-16","signal_price":78.9,"signal_score":0.6478,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-17","log_type":"WATCH_POOL_ADD","stock":"603061.XSHG","name":"\u91d1\u6d77\u901a","signal_date":"2026-04-17","signal_price":243.9,"signal_score":0.7412,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-20","log_type":"WATCH_POOL_ADD","stock":"000628.XSHE","name":"\u9ad8\u65b0\u53d1\u5c55","signal_date":"2026-04-20","signal_price":60.0,"signal_score":0.6412,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-20","log_type":"WATCH_POOL_ADD","stock":"002176.XSHE","name":"\u6c5f\u7279\u7535\u673a","signal_date":"2026-04-20","signal_price":11.22,"signal_score":0.621,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-20","log_type":"WATCH_POOL_ADD","stock":"002850.XSHE","name":"\u79d1\u8fbe\u5229","signal_date":"2026-04-20","signal_price":199.61,"signal_score":0.5918,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-20","log_type":"WATCH_POOL_ADD","stock":"000062.XSHE","name":"\u6df1\u5733\u534e\u5f3a","signal_date":"2026-04-20","signal_price":31.17,"signal_score":0.5784,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-21","log_type":"WATCH_POOL_ADD","stock":"603687.XSHG","name":"\u5927\u80dc\u8fbe","signal_date":"2026-04-21","signal_price":19.55,"signal_score":0.7238,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-22","log_type":"WATCH_POOL_ADD","stock":"002328.XSHE","name":"\u65b0\u670b\u80a1\u4efd","signal_date":"2026-04-22","signal_price":11.81,"signal_score":0.7064,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-22","log_type":"WATCH_POOL_ADD","stock":"002645.XSHE","name":"\u534e\u5b8f\u79d1\u6280","signal_date":"2026-04-22","signal_price":23.13,"signal_score":0.6646,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-22","log_type":"WATCH_POOL_ADD","stock":"603876.XSHG","name":"\u9f0e\u80dc\u65b0\u6750","signal_date":"2026-04-22","signal_price":25.05,"signal_score":0.609,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-22","log_type":"WATCH_POOL_ADD","stock":"002866.XSHE","name":"\u4f20\u827a\u79d1\u6280","signal_date":"2026-04-22","signal_price":27.3,"signal_score":0.5763,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-23","log_type":"WATCH_POOL_ADD","stock":"603778.XSHG","name":"\u56fd\u665f\u79d1\u6280","signal_date":"2026-04-23","signal_price":26.54,"signal_score":0.6431,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-23","log_type":"WATCH_POOL_ADD","stock":"600884.XSHG","name":"\u6749\u6749\u80a1\u4efd","signal_date":"2026-04-23","signal_price":14.96,"signal_score":0.6387,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-24","log_type":"WATCH_POOL_ADD","stock":"000815.XSHE","name":"\u7f8e\u5229\u4e91","signal_date":"2026-04-24","signal_price":19.17,"signal_score":0.7128,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-24","log_type":"WATCH_POOL_ADD","stock":"002384.XSHE","name":"\u4e1c\u5c71\u7cbe\u5bc6","signal_date":"2026-04-24","signal_price":187.9,"signal_score":0.7116,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-24","log_type":"WATCH_POOL_ADD","stock":"600482.XSHG","name":"\u4e2d\u56fd\u52a8\u529b","signal_date":"2026-04-24","signal_price":40.4,"signal_score":0.6782,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-24","log_type":"WATCH_POOL_ADD","stock":"001389.XSHE","name":"\u5e7f\u5408\u79d1\u6280","signal_date":"2026-04-24","signal_price":170.6,"signal_score":0.6673,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-27","log_type":"WATCH_POOL_ADD","stock":"002975.XSHE","name":"\u535a\u6770\u80a1\u4efd","signal_date":"2026-04-27","signal_price":117.26,"signal_score":0.763,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-27","log_type":"WATCH_POOL_ADD","stock":"002938.XSHE","name":"\u9e4f\u9f0e\u63a7\u80a1","signal_date":"2026-04-27","signal_price":77.18,"signal_score":0.7421,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-27","log_type":"WATCH_POOL_ADD","stock":"000534.XSHE","name":"\u4e07\u6cfd\u80a1\u4efd","signal_date":"2026-04-27","signal_price":41.18,"signal_score":0.7315,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-27","log_type":"WATCH_POOL_ADD","stock":"002636.XSHE","name":"\u91d1\u5b89\u56fd\u7eaa","signal_date":"2026-04-27","signal_price":44.1,"signal_score":0.6977,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-27","log_type":"WATCH_POOL_ADD","stock":"601869.XSHG","name":"\u957f\u98de\u5149\u7ea4","signal_date":"2026-04-27","signal_price":377.5,"signal_score":0.6876,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-28","log_type":"WATCH_POOL_ADD","stock":"603083.XSHG","name":"\u5251\u6865\u79d1\u6280","signal_date":"2026-04-28","signal_price":155.19,"signal_score":0.5416,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-29","log_type":"WATCH_POOL_ADD","stock":"003018.XSHE","name":"\u91d1\u5bcc\u79d1\u6280","signal_date":"2026-04-29","signal_price":55.06,"signal_score":0.6864,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-29","log_type":"WATCH_POOL_ADD","stock":"002432.XSHE","name":"\u4e5d\u5b89\u533b\u7597","signal_date":"2026-04-29","signal_price":75.16,"signal_score":0.6737,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-29","log_type":"WATCH_POOL_ADD","stock":"601231.XSHG","name":"\u73af\u65ed\u7535\u5b50","signal_date":"2026-04-29","signal_price":40.28,"signal_score":0.6248,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-30","log_type":"WATCH_POOL_ADD","stock":"002222.XSHE","name":"\u798f\u6676\u79d1\u6280","signal_date":"2026-04-30","signal_price":86.82,"signal_score":0.6239,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-30","log_type":"WATCH_POOL_ADD","stock":"002290.XSHE","name":"\u79be\u76db\u65b0\u6750","signal_date":"2026-04-30","signal_price":81.28,"signal_score":0.6064,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-04-30","log_type":"WATCH_POOL_ADD","stock":"002384.XSHE","name":"\u4e1c\u5c71\u7cbe\u5bc6","signal_date":"2026-04-30","signal_price":186.73,"signal_score":0.5824,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"600186.XSHG","name":"\u83b2\u82b1\u63a7\u80a1","signal_date":"2026-05-06","signal_price":11.4,"signal_score":0.8776,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"603083.XSHG","name":"\u5251\u6865\u79d1\u6280","signal_date":"2026-05-06","signal_price":179.22,"signal_score":0.8161,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"600773.XSHG","name":"\u897f\u85cf\u57ce\u6295","signal_date":"2026-05-06","signal_price":27.49,"signal_score":0.8036,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"002636.XSHE","name":"\u91d1\u5b89\u56fd\u7eaa","signal_date":"2026-05-06","signal_price":46.56,"signal_score":0.7453,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"600736.XSHG","name":"\u82cf\u5dde\u9ad8\u65b0","signal_date":"2026-05-06","signal_price":8.77,"signal_score":0.7292,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"002580.XSHE","name":"\u5723\u9633\u80a1\u4efd","signal_date":"2026-05-06","signal_price":29.78,"signal_score":0.7175,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"002560.XSHE","name":"\u901a\u8fbe\u80a1\u4efd","signal_date":"2026-05-06","signal_price":15.12,"signal_score":0.7126,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"000925.XSHE","name":"\u4f17\u5408\u79d1\u6280","signal_date":"2026-05-06","signal_price":10.0,"signal_score":0.7029,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-06","log_type":"WATCH_POOL_ADD","stock":"600105.XSHG","name":"\u6c38\u9f0e\u80a1\u4efd","signal_date":"2026-05-06","signal_price":43.68,"signal_score":0.7011,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-07","log_type":"WATCH_POOL_ADD","stock":"002135.XSHE","name":"\u4e1c\u5357\u7f51\u67b6","signal_date":"2026-05-07","signal_price":9.35,"signal_score":0.7646,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-07","log_type":"WATCH_POOL_ADD","stock":"002565.XSHE","name":"\u987a\u704f\u80a1\u4efd","signal_date":"2026-05-07","signal_price":19.86,"signal_score":0.6895,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-07","log_type":"WATCH_POOL_ADD","stock":"002371.XSHE","name":"\u5317\u65b9\u534e\u521b","signal_date":"2026-05-07","signal_price":552.14,"signal_score":0.6683,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-07","log_type":"WATCH_POOL_ADD","stock":"603929.XSHG","name":"\u4e9a\u7fd4\u96c6\u6210","signal_date":"2026-05-07","signal_price":206.0,"signal_score":0.5965,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-08","log_type":"WATCH_POOL_ADD","stock":"002738.XSHE","name":"\u4e2d\u77ff\u8d44\u6e90","signal_date":"2026-05-08","signal_price":88.88,"signal_score":0.7157,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-08","log_type":"WATCH_POOL_ADD","stock":"603399.XSHG","name":"\u6c38\u6749\u9502\u4e1a","signal_date":"2026-05-08","signal_price":23.99,"signal_score":0.6654,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"002217.XSHE","name":"\u5408\u529b\u6cf0","signal_date":"2026-05-11","signal_price":3.57,"signal_score":0.8893,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"002081.XSHE","name":"\u91d1\u87b3\u8782","signal_date":"2026-05-11","signal_price":7.25,"signal_score":0.7651,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"002240.XSHE","name":"\u76db\u65b0\u9502\u80fd","signal_date":"2026-05-11","signal_price":57.81,"signal_score":0.7421,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"600487.XSHG","name":"\u4ea8\u901a\u5149\u7535","signal_date":"2026-05-11","signal_price":74.99,"signal_score":0.7415,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"002149.XSHE","name":"\u897f\u90e8\u6750\u6599","signal_date":"2026-05-11","signal_price":75.44,"signal_score":0.7364,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"603002.XSHG","name":"\u5b8f\u660c\u7535\u5b50","signal_date":"2026-05-11","signal_price":15.31,"signal_score":0.7347,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"600986.XSHG","name":"\u6d59\u6587\u4e92\u8054","signal_date":"2026-05-11","signal_price":10.94,"signal_score":0.7312,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"603220.XSHG","name":"\u4e2d\u8d1d\u901a\u4fe1","signal_date":"2026-05-11","signal_price":31.1,"signal_score":0.7284,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"600206.XSHG","name":"\u6709\u7814\u65b0\u6750","signal_date":"2026-05-11","signal_price":32.87,"signal_score":0.722,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"000060.XSHE","name":"\u4e2d\u91d1\u5cad\u5357","signal_date":"2026-05-11","signal_price":8.5,"signal_score":0.7132,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-11","log_type":"WATCH_POOL_ADD","stock":"603688.XSHG","name":"\u77f3\u82f1\u80a1\u4efd","signal_date":"2026-05-11","signal_price":66.6,"signal_score":0.7004,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"002222.XSHE","name":"\u798f\u6676\u79d1\u6280","signal_date":"2026-05-12","signal_price":113.36,"signal_score":0.8542,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"002015.XSHE","name":"\u534f\u946b\u80fd\u79d1","signal_date":"2026-05-12","signal_price":21.26,"signal_score":0.766,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"605598.XSHG","name":"\u4e0a\u6d77\u6e2f\u6e7e","signal_date":"2026-05-12","signal_price":57.8,"signal_score":0.7652,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"603083.XSHG","name":"\u5251\u6865\u79d1\u6280","signal_date":"2026-05-12","signal_price":189.42,"signal_score":0.736,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"002475.XSHE","name":"\u7acb\u8baf\u7cbe\u5bc6","signal_date":"2026-05-12","signal_price":77.19,"signal_score":0.6862,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"600301.XSHG","name":"\u534e\u9521\u6709\u8272","signal_date":"2026-05-12","signal_price":62.36,"signal_score":0.6861,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-12","log_type":"WATCH_POOL_ADD","stock":"000938.XSHE","name":"\u7d2b\u5149\u80a1\u4efd","signal_date":"2026-05-12","signal_price":30.69,"signal_score":0.6789,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-13","log_type":"WATCH_POOL_ADD","stock":"600531.XSHG","name":"\u8c6b\u5149\u91d1\u94c5","signal_date":"2026-05-13","signal_price":16.58,"signal_score":0.6531,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-13","log_type":"WATCH_POOL_ADD","stock":"000630.XSHE","name":"\u94dc\u9675\u6709\u8272","signal_date":"2026-05-13","signal_price":6.98,"signal_score":0.5703,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-14","log_type":"WATCH_POOL_ADD","stock":"603031.XSHG","name":"\u5b89\u5b5a\u79d1\u6280","signal_date":"2026-05-14","signal_price":51.5,"signal_score":0.7244,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-14","log_type":"WATCH_POOL_ADD","stock":"002865.XSHE","name":"\u94a7\u8fbe\u80a1\u4efd","signal_date":"2026-05-14","signal_price":100.28,"signal_score":0.6628,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-14","log_type":"WATCH_POOL_ADD","stock":"601609.XSHG","name":"\u91d1\u7530\u80a1\u4efd","signal_date":"2026-05-14","signal_price":13.3,"signal_score":0.6153,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"002149.XSHE","name":"\u897f\u90e8\u6750\u6599","signal_date":"2026-05-15","signal_price":69.02,"signal_score":0.8497,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"603290.XSHG","name":"\u65af\u8fbe\u534a\u5bfc","signal_date":"2026-05-15","signal_price":124.95,"signal_score":0.7952,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"002364.XSHE","name":"\u4e2d\u6052\u7535\u6c14","signal_date":"2026-05-15","signal_price":47.85,"signal_score":0.7792,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"605589.XSHG","name":"\u5723\u6cc9\u96c6\u56e2","signal_date":"2026-05-15","signal_price":42.08,"signal_score":0.7713,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"603296.XSHG","name":"\u534e\u52e4\u6280\u672f","signal_date":"2026-05-15","signal_price":113.85,"signal_score":0.7349,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"000591.XSHE","name":"\u592a\u9633\u80fd","signal_date":"2026-05-15","signal_price":6.01,"signal_score":0.7228,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"002409.XSHE","name":"\u96c5\u514b\u79d1\u6280","signal_date":"2026-05-15","signal_price":107.46,"signal_score":0.678,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"600584.XSHG","name":"\u957f\u7535\u79d1\u6280","signal_date":"2026-05-15","signal_price":58.05,"signal_score":0.6701,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-15","log_type":"WATCH_POOL_ADD","stock":"002975.XSHE","name":"\u535a\u6770\u80a1\u4efd","signal_date":"2026-05-15","signal_price":114.99,"signal_score":0.6684,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"002015.XSHE","name":"\u534f\u946b\u80fd\u79d1","signal_date":"2026-05-18","signal_price":21.47,"signal_score":0.815,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"600522.XSHG","name":"\u4e2d\u5929\u79d1\u6280","signal_date":"2026-05-18","signal_price":43.95,"signal_score":0.7722,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"600641.XSHG","name":"\u5148\u5bfc\u57fa\u7535","signal_date":"2026-05-18","signal_price":31.04,"signal_score":0.7664,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"002600.XSHE","name":"\u9886\u76ca\u667a\u9020","signal_date":"2026-05-18","signal_price":17.07,"signal_score":0.7153,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"002792.XSHE","name":"\u901a\u5b87\u901a\u8baf","signal_date":"2026-05-18","signal_price":50.27,"signal_score":0.6573,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-18","log_type":"WATCH_POOL_ADD","stock":"002929.XSHE","name":"\u6da6\u5efa\u80a1\u4efd","signal_date":"2026-05-18","signal_price":95.99,"signal_score":0.6404,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-20","log_type":"WATCH_POOL_ADD","stock":"002971.XSHE","name":"\u548c\u8fdc\u6c14\u4f53","signal_date":"2026-05-20","signal_price":37.8,"signal_score":0.7602,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-20","log_type":"WATCH_POOL_ADD","stock":"002918.XSHE","name":"\u8499\u5a1c\u4e3d\u838e","signal_date":"2026-05-20","signal_price":15.09,"signal_score":0.658,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-20","log_type":"WATCH_POOL_ADD","stock":"603156.XSHG","name":"\u517b\u5143\u996e\u54c1","signal_date":"2026-05-20","signal_price":49.05,"signal_score":0.6343,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"600246.XSHG","name":"\u4e07\u901a\u53d1\u5c55","signal_date":"2026-05-21","signal_price":15.41,"signal_score":0.7893,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"000636.XSHE","name":"\u98ce\u534e\u9ad8\u79d1","signal_date":"2026-05-21","signal_price":34.2,"signal_score":0.7883,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"000021.XSHE","name":"\u6df1\u79d1\u6280","signal_date":"2026-05-21","signal_price":36.37,"signal_score":0.7366,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"002938.XSHE","name":"\u9e4f\u9f0e\u63a7\u80a1","signal_date":"2026-05-21","signal_price":94.48,"signal_score":0.7344,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"002916.XSHE","name":"\u6df1\u5357\u7535\u8def","signal_date":"2026-05-21","signal_price":343.88,"signal_score":0.6281,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-21","log_type":"WATCH_POOL_ADD","stock":"001309.XSHE","name":"\u5fb7\u660e\u5229","signal_date":"2026-05-21","signal_price":656.1,"signal_score":0.5874,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-22","log_type":"WATCH_POOL_ADD","stock":"000066.XSHE","name":"\u4e2d\u56fd\u957f\u57ce","signal_date":"2026-05-22","signal_price":20.93,"signal_score":0.8742,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-22","log_type":"WATCH_POOL_ADD","stock":"603738.XSHG","name":"\u6cf0\u6676\u79d1\u6280","signal_date":"2026-05-22","signal_price":50.24,"signal_score":0.8327,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-22","log_type":"WATCH_POOL_ADD","stock":"002384.XSHE","name":"\u4e1c\u5c71\u7cbe\u5bc6","signal_date":"2026-05-22","signal_price":220.55,"signal_score":0.8118,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-22","log_type":"WATCH_POOL_ADD","stock":"002185.XSHE","name":"\u534e\u5929\u79d1\u6280","signal_date":"2026-05-22","signal_price":15.43,"signal_score":0.7756,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-25","log_type":"WATCH_POOL_ADD","stock":"002782.XSHE","name":"\u53ef\u7acb\u514b","signal_date":"2026-05-25","signal_price":28.31,"signal_score":0.7854,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-25","log_type":"WATCH_POOL_ADD","stock":"605589.XSHG","name":"\u5723\u6cc9\u96c6\u56e2","signal_date":"2026-05-25","signal_price":45.85,"signal_score":0.7177,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-25","log_type":"WATCH_POOL_ADD","stock":"002617.XSHE","name":"\u9732\u7b11\u79d1\u6280","signal_date":"2026-05-25","signal_price":9.58,"signal_score":0.6184,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-26","log_type":"WATCH_POOL_ADD","stock":"002380.XSHE","name":"\u79d1\u8fdc\u667a\u6167","signal_date":"2026-05-26","signal_price":44.67,"signal_score":0.7671,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-26","log_type":"WATCH_POOL_ADD","stock":"603031.XSHG","name":"\u5b89\u5b5a\u79d1\u6280","signal_date":"2026-05-26","signal_price":53.13,"signal_score":0.6433,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-27","log_type":"WATCH_POOL_ADD","stock":"002654.XSHE","name":"\u4e07\u6da6\u79d1\u6280","signal_date":"2026-05-27","signal_price":16.42,"signal_score":0.7191,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-27","log_type":"WATCH_POOL_ADD","stock":"603283.XSHG","name":"\u8d5b\u817e\u80a1\u4efd","signal_date":"2026-05-27","signal_price":66.01,"signal_score":0.6697,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-27","log_type":"WATCH_POOL_ADD","stock":"001309.XSHE","name":"\u5fb7\u660e\u5229","signal_date":"2026-05-27","signal_price":665.0,"signal_score":0.6207,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-28","log_type":"WATCH_POOL_ADD","stock":"603063.XSHG","name":"\u79be\u671b\u7535\u6c14","signal_date":"2026-05-28","signal_price":60.29,"signal_score":0.8222,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-28","log_type":"WATCH_POOL_ADD","stock":"002600.XSHE","name":"\u9886\u76ca\u667a\u9020","signal_date":"2026-05-28","signal_price":15.95,"signal_score":0.6702,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-29","log_type":"WATCH_POOL_ADD","stock":"002885.XSHE","name":"\u4eac\u6cc9\u534e","signal_date":"2026-05-29","signal_price":44.2,"signal_score":0.6921,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-29","log_type":"WATCH_POOL_ADD","stock":"002703.XSHE","name":"\u6d59\u6c5f\u4e16\u5b9d","signal_date":"2026-05-29","signal_price":18.84,"signal_score":0.6901,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-29","log_type":"WATCH_POOL_ADD","stock":"601600.XSHG","name":"\u4e2d\u56fd\u94dd\u4e1a","signal_date":"2026-05-29","signal_price":11.42,"signal_score":0.6326,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-29","log_type":"WATCH_POOL_ADD","stock":"002920.XSHE","name":"\u5fb7\u8d5b\u897f\u5a01","signal_date":"2026-05-29","signal_price":101.76,"signal_score":0.5893,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-05-29","log_type":"WATCH_POOL_ADD","stock":"000807.XSHE","name":"\u4e91\u94dd\u80a1\u4efd","signal_date":"2026-05-29","signal_price":28.49,"signal_score":0.5681,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"000988.XSHE","name":"\u534e\u5de5\u79d1\u6280","signal_date":"2026-06-01","signal_price":143.07,"signal_score":0.842,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"600378.XSHG","name":"\u660a\u534e\u79d1\u6280","signal_date":"2026-06-01","signal_price":40.88,"signal_score":0.7965,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"002706.XSHE","name":"\u826f\u4fe1\u80a1\u4efd","signal_date":"2026-06-01","signal_price":14.53,"signal_score":0.7887,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"603986.XSHG","name":"\u5146\u6613\u521b\u65b0","signal_date":"2026-06-01","signal_price":468.0,"signal_score":0.7793,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"601138.XSHG","name":"\u5de5\u4e1a\u5bcc\u8054","signal_date":"2026-06-01","signal_price":73.75,"signal_score":0.7553,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"000938.XSHE","name":"\u7d2b\u5149\u80a1\u4efd","signal_date":"2026-06-01","signal_price":27.84,"signal_score":0.7423,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-01","log_type":"WATCH_POOL_ADD","stock":"000066.XSHE","name":"\u4e2d\u56fd\u957f\u57ce","signal_date":"2026-06-01","signal_price":18.48,"signal_score":0.7384,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-02","log_type":"WATCH_POOL_ADD","stock":"000630.XSHE","name":"\u94dc\u9675\u6709\u8272","signal_date":"2026-06-02","signal_price":7.08,"signal_score":0.6578,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-05","log_type":"WATCH_POOL_ADD","stock":"000799.XSHE","name":"\u9152\u9b3c\u9152","signal_date":"2026-06-05","signal_price":44.51,"signal_score":0.7463,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-08","log_type":"WATCH_POOL_ADD","stock":"601888.XSHG","name":"\u4e2d\u56fd\u4e2d\u514d","signal_date":"2026-06-08","signal_price":57.45,"signal_score":0.5951,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"600498.XSHG","name":"\u70fd\u706b\u901a\u4fe1","signal_date":"2026-06-09","signal_price":58.85,"signal_score":0.8089,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"600549.XSHG","name":"\u53a6\u95e8\u94a8\u4e1a","signal_date":"2026-06-09","signal_price":63.93,"signal_score":0.7949,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"600703.XSHG","name":"\u4e09\u5b89\u5149\u7535","signal_date":"2026-06-09","signal_price":17.3,"signal_score":0.7881,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"600063.XSHG","name":"\u7696\u7ef4\u9ad8\u65b0","signal_date":"2026-06-09","signal_price":7.96,"signal_score":0.7651,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"002125.XSHE","name":"\u6e58\u6f6d\u7535\u5316","signal_date":"2026-06-09","signal_price":17.07,"signal_score":0.7402,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"000727.XSHE","name":"\u51a0\u6377\u79d1\u6280","signal_date":"2026-06-09","signal_price":2.99,"signal_score":0.7325,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"000070.XSHE","name":"\u7279\u53d1\u4fe1\u606f","signal_date":"2026-06-09","signal_price":19.53,"signal_score":0.7289,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"000988.XSHE","name":"\u534e\u5de5\u79d1\u6280","signal_date":"2026-06-09","signal_price":155.53,"signal_score":0.7112,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-09","log_type":"WATCH_POOL_ADD","stock":"000823.XSHE","name":"\u8d85\u58f0\u7535\u5b50","signal_date":"2026-06-09","signal_price":18.6,"signal_score":0.7106,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-11","log_type":"WATCH_POOL_ADD","stock":"600641.XSHG","name":"\u5148\u5bfc\u57fa\u7535","signal_date":"2026-06-11","signal_price":28.91,"signal_score":0.7367,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-11","log_type":"WATCH_POOL_ADD","stock":"600392.XSHG","name":"\u76db\u548c\u8d44\u6e90","signal_date":"2026-06-11","signal_price":25.27,"signal_score":0.6597,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"600226.XSHG","name":"\u4ea8\u901a\u80a1\u4efd","signal_date":"2026-06-12","signal_price":7.5,"signal_score":0.8667,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"003026.XSHE","name":"\u4e2d\u6676\u79d1\u6280","signal_date":"2026-06-12","signal_price":33.19,"signal_score":0.8199,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"603929.XSHG","name":"\u4e9a\u7fd4\u96c6\u6210","signal_date":"2026-06-12","signal_price":218.08,"signal_score":0.7544,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"002297.XSHE","name":"\u535a\u4e91\u65b0\u6750","signal_date":"2026-06-12","signal_price":22.44,"signal_score":0.7523,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"000733.XSHE","name":"\u632f\u534e\u79d1\u6280","signal_date":"2026-06-12","signal_price":47.16,"signal_score":0.7291,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"002741.XSHE","name":"\u5149\u534e\u79d1\u6280","signal_date":"2026-06-12","signal_price":29.63,"signal_score":0.7227,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"601231.XSHG","name":"\u73af\u65ed\u7535\u5b50","signal_date":"2026-06-12","signal_price":33.9,"signal_score":0.7174,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"002916.XSHE","name":"\u6df1\u5357\u7535\u8def","signal_date":"2026-06-12","signal_price":379.5,"signal_score":0.7157,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"000670.XSHE","name":"\u76c8\u65b9\u5fae","signal_date":"2026-06-12","signal_price":8.63,"signal_score":0.7107,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"000063.XSHE","name":"\u4e2d\u5174\u901a\u8baf","signal_date":"2026-06-12","signal_price":36.35,"signal_score":0.7103,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"},{"date":"2026-06-12","log_type":"WATCH_POOL_ADD","stock":"603083.XSHG","name":"\u5251\u6865\u79d1\u6280","signal_date":"2026-06-12","signal_price":182.99,"signal_score":0.7062,"signal_entry_type":"deep_water","current_price":null,"ret_from_signal":null,"day_ret":null,"volume_ratio_vs_prev":null,"ma5_distance":null,"close_to_day_high":null,"is_limit_up":null,"reason":"core_candidate_not_bought"}]'''
promotion_events_json = r'''[
{"stock":"600487.XSHG","name":"亨通光电","block_date":"2026-01-28","pnl_pct_at_block":0.0763,"hold_days":2},
{"stock":"603212.XSHG","name":"赛伍技术","block_date":"2026-02-04","pnl_pct_at_block":0.0468,"hold_days":1},
{"stock":"000510.XSHE","name":"新金路","block_date":"2026-02-27","pnl_pct_at_block":0.0914,"hold_days":2},
{"stock":"600773.XSHG","name":"西藏城投","block_date":"2026-03-13","pnl_pct_at_block":0.0557,"hold_days":2},
{"stock":"002176.XSHE","name":"江特电机","block_date":"2026-04-24","pnl_pct_at_block":0.0975,"hold_days":2},
{"stock":"002222.XSHE","name":"福晶科技","block_date":"2026-05-07","pnl_pct_at_block":0.0581,"hold_days":1},
{"stock":"000021.XSHE","name":"深科技","block_date":"2026-05-27","pnl_pct_at_block":0.0960,"hold_days":2}
]'''

failed_trades = json.loads(failed_trades_json)
watch_adds = json.loads(watch_adds_json)
promotion_events = json.loads(promotion_events_json)

OOS_START = '2026-04-16'
OOS_END = '2026-06-14'

def calc_max_ret(prices, base_price, periods):
    if len(prices) <= periods or base_price <= 0:
        return np.nan
    future_prices = prices[1:periods+1]
    if len(future_prices) == 0:
        return np.nan
    return (max(future_prices) - base_price) / base_price

def calc_min_ret(prices, base_price, periods):
    if len(prices) <= periods or base_price <= 0:
        return np.nan
    future_prices = prices[1:periods+1]
    if len(future_prices) == 0:
        return np.nan
    return (min(future_prices) - base_price) / base_price

def safe_ratio(num, den):
    try:
        if den is None or den == 0:
            return np.nan
        return float(num) / float(den)
    except Exception:
        return np.nan

def pct_or_na(value):
    try:
        if pd.isna(value):
            return 'NA'
        return '{:.2%}'.format(float(value))
    except Exception:
        return 'NA'

def get_market_breadth_universe(date_str):
    """Use 000852 + 000905 constituents as proxy universe in JoinQuant research."""
    stocks = []
    try:
        stocks.extend(list(get_index_stocks('000852.XSHG', date=date_str)))
    except Exception as e:
        print("WARNING: get_index_stocks 000852 failed on {}: {}".format(date_str, e))
    try:
        stocks.extend(list(get_index_stocks('000905.XSHG', date=date_str)))
    except Exception as e:
        print("WARNING: get_index_stocks 000905 failed on {}: {}".format(date_str, e))
    # Preserve order while de-duplicating.
    return list(dict.fromkeys([s for s in stocks if s]))

def _normalize_price_frame(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    out = df.copy()
    if 'code' not in out.columns:
        out = out.reset_index()
    if 'code' not in out.columns:
        # Some JQ/pandas combinations name the security column differently.
        for col in out.columns:
            if str(col).lower() in ('security', 'stock', 'order_book_id'):
                out = out.rename(columns={col: 'code'})
                break
    if 'time' not in out.columns:
        for col in out.columns:
            if str(col).lower() in ('date', 'datetime', 'index'):
                out = out.rename(columns={col: 'time'})
                break
    return out

def calc_market_breadth_proxy(date_str):
    fields = [
        'close', 'money', 'high_limit', 'low_limit'
    ]
    empty = {
        'market_up_ratio': np.nan,
        'market_down_ratio': np.nan,
        'market_above_ma5_ratio': np.nan,
        'market_above_ma10_ratio': np.nan,
        'market_above_ma20_ratio': np.nan,
        'limit_up_count': np.nan,
        'limit_down_count': np.nan,
        'median_ret_1d': np.nan,
        'median_money': np.nan,
        'median_money_change_5d': np.nan,
        'market_breadth_available': 0,
        'market_breadth_universe': 'index_constituents_proxy',
        'market_breadth_sample_count': 0,
        'market_breadth_missing_reason': 'not_calculated',
    }
    universe = get_market_breadth_universe(date_str)
    if not universe:
        empty['market_breadth_missing_reason'] = 'empty_index_constituents'
        return empty
    try:
        raw = get_price(
            universe,
            end_date=date_str,
            frequency='daily',
            fields=fields,
            count=21,
            panel=False,
            skip_paused=False,
            fq='pre'
        )
    except Exception as e:
        empty['market_breadth_missing_reason'] = 'get_price_failed: {}'.format(e)
        return empty
    df = _normalize_price_frame(raw)
    if df.empty or 'code' not in df.columns or 'close' not in df.columns:
        empty['market_breadth_missing_reason'] = 'price_frame_missing_code_or_close'
        return empty
    if 'time' in df.columns:
        df = df.sort_values(['code', 'time'])
    rows = []
    for code, gdf in df.groupby('code'):
        gdf = gdf.dropna(subset=['close'])
        if len(gdf) < 2:
            continue
        closes = gdf['close'].values
        latest = float(closes[-1])
        prev = float(closes[-2])
        if prev <= 0 or latest <= 0:
            continue
        item = {
            'ret_1d': latest / prev - 1.0,
            'above_ma5': np.nan,
            'above_ma10': np.nan,
            'above_ma20': np.nan,
            'money': np.nan,
            'money_change_5d': np.nan,
            'limit_up': 0,
            'limit_down': 0,
        }
        if len(closes) >= 5:
            ma5 = np.mean(closes[-5:])
            item['above_ma5'] = 1 if ma5 > 0 and latest > ma5 else 0
        if len(closes) >= 10:
            ma10 = np.mean(closes[-10:])
            item['above_ma10'] = 1 if ma10 > 0 and latest > ma10 else 0
        if len(closes) >= 20:
            ma20 = np.mean(closes[-20:])
            item['above_ma20'] = 1 if ma20 > 0 and latest > ma20 else 0
        if 'money' in gdf.columns:
            money_values = gdf['money'].dropna().values
            if len(money_values) >= 1:
                item['money'] = float(money_values[-1])
            if len(money_values) >= 6:
                base_money = np.mean(money_values[-6:-1])
                item['money_change_5d'] = latest_money_change = (
                    money_values[-1] / base_money - 1.0
                    if base_money > 0 else np.nan
                )
        last = gdf.iloc[-1]
        if 'high_limit' in gdf.columns and not pd.isna(last.get('high_limit', np.nan)):
            item['limit_up'] = 1 if latest >= float(last.get('high_limit')) * 0.999 else 0
        if 'low_limit' in gdf.columns and not pd.isna(last.get('low_limit', np.nan)):
            item['limit_down'] = 1 if latest <= float(last.get('low_limit')) * 1.001 else 0
        rows.append(item)
    if not rows:
        empty['market_breadth_missing_reason'] = 'no_valid_stock_rows'
        return empty
    bdf = pd.DataFrame(rows)
    return {
        'market_up_ratio': safe_ratio((bdf['ret_1d'] > 0).sum(), len(bdf)),
        'market_down_ratio': safe_ratio((bdf['ret_1d'] < 0).sum(), len(bdf)),
        'market_above_ma5_ratio': bdf['above_ma5'].mean(),
        'market_above_ma10_ratio': bdf['above_ma10'].mean(),
        'market_above_ma20_ratio': bdf['above_ma20'].mean(),
        'limit_up_count': int(bdf['limit_up'].sum()),
        'limit_down_count': int(bdf['limit_down'].sum()),
        'median_ret_1d': bdf['ret_1d'].median(),
        'median_money': bdf['money'].median(),
        'median_money_change_5d': bdf['money_change_5d'].median(),
        'market_breadth_available': 1,
        'market_breadth_universe': 'index_constituents_proxy',
        'market_breadth_sample_count': len(bdf),
        'market_breadth_missing_reason': '',
    }

def run_market_regime_validation():
    print("Running Market Regime Validation...")
    trade_days = get_trade_days(start_date=OOS_START, end_date=OOS_END)
    results = []

    for date in trade_days:
        date_str = date.strftime('%Y-%m-%d')

        # Index data
        idx_000852 = get_price('000852.XSHG', end_date=date_str, frequency='daily', fields=['close'], count=21, skip_paused=False)
        idx_000905 = get_price('000905.XSHG', end_date=date_str, frequency='daily', fields=['close'], count=6, skip_paused=False)

        ret_1d_852, ret_5d_852, ma5_dist_852, ma20_dist_852 = np.nan, np.nan, np.nan, np.nan
        if len(idx_000852) >= 21:
            closes = idx_000852['close'].values
            ret_1d_852 = (closes[-1] / closes[-2]) - 1
            ret_5d_852 = (closes[-1] / closes[-6]) - 1
            ma5_852 = np.mean(closes[-5:])
            ma20_852 = np.mean(closes[-20:])
            ma5_dist_852 = (closes[-1] / ma5_852) - 1
            ma20_dist_852 = (closes[-1] / ma20_852) - 1

        ret_1d_905, ret_5d_905 = np.nan, np.nan
        if len(idx_000905) >= 6:
            closes = idx_000905['close'].values
            ret_1d_905 = (closes[-1] / closes[-2]) - 1
            ret_5d_905 = (closes[-1] / closes[-6]) - 1

        # Market breadth proxy: 000852 + 000905 constituents.
        breadth = calc_market_breadth_proxy(date_str)

        regime_label_raw = 'neutral_crowding_proxy' # Placeholder for complex logic

        results.append({
            'date': date_str,
            'index_000852_ret_1d': ret_1d_852,
            'index_000852_ret_5d': ret_5d_852,
            'index_000852_ma5_distance': ma5_dist_852,
            'index_000852_ma20_distance': ma20_dist_852,
            'index_000905_ret_1d': ret_1d_905,
            'index_000905_ret_5d': ret_5d_905,
            'market_up_ratio': breadth.get('market_up_ratio', np.nan),
            'market_down_ratio': breadth.get('market_down_ratio', np.nan),
            'market_above_ma5_ratio': breadth.get('market_above_ma5_ratio', np.nan),
            'market_above_ma10_ratio': breadth.get('market_above_ma10_ratio', np.nan),
            'market_above_ma20_ratio': breadth.get('market_above_ma20_ratio', np.nan),
            'limit_up_count': breadth.get('limit_up_count', np.nan),
            'limit_down_count': breadth.get('limit_down_count', np.nan),
            'median_ret_1d': breadth.get('median_ret_1d', np.nan),
            'median_money': breadth.get('median_money', np.nan),
            'median_money_change_5d': breadth.get('median_money_change_5d', np.nan),
            'market_breadth_available': breadth.get('market_breadth_available', 0),
            'market_breadth_universe': breadth.get('market_breadth_universe', 'index_constituents_proxy'),
            'market_breadth_sample_count': breadth.get('market_breadth_sample_count', 0),
            'market_breadth_missing_reason': breadth.get('market_breadth_missing_reason', ''),
            'regime_label_raw': regime_label_raw
        })

    df = pd.DataFrame(results)
    df.to_csv('jq_oos_market_regime_daily.csv', index=False, encoding='utf-8-sig')
    print("Generated jq_oos_market_regime_daily.csv")
    return df

def run_watch_pool_validation():
    print("Running Watch Pool Validation...")
    results = []
    for item in watch_adds:
        stock = item.get('stock')
        date_str = item.get('date')
        if not stock or not date_str: continue

        # Get 11 days of future data to compute max/min
        prices_df = get_price(stock, start_date=date_str, end_date='2026-07-01', frequency='daily', fields=['close', 'high', 'low', 'high_limit', 'low_limit'], count=11, skip_paused=False)

        data_quality_flag = 0
        if len(prices_df) < 11:
            data_quality_flag = 1

        prices = prices_df['close'].values if not prices_df.empty else []
        highs = prices_df['high'].values if not prices_df.empty else []
        lows = prices_df['low'].values if not prices_df.empty else []
        high_limits = prices_df['high_limit'].values if not prices_df.empty else []
        low_limits = prices_df['low_limit'].values if not prices_df.empty else []

        base_price = prices[0] if len(prices) > 0 else np.nan

        t1_max = calc_max_ret(highs, base_price, 1)
        t3_max = calc_max_ret(highs, base_price, 3)
        t5_max = calc_max_ret(highs, base_price, 5)
        t10_max = calc_max_ret(highs, base_price, 10)

        t1_min = calc_min_ret(lows, base_price, 1)
        t3_min = calc_min_ret(lows, base_price, 3)
        t5_min = calc_min_ret(lows, base_price, 5)
        t10_min = calc_min_ret(lows, base_price, 10)

        hit_limit_up = 1 if len(highs) > 1 and any([highs[i] >= high_limits[i]*0.99 for i in range(1, min(6, len(highs)))]) else 0
        hit_limit_down = 1 if len(lows) > 1 and any([lows[i] <= low_limits[i]*1.01 for i in range(1, min(6, len(lows)))]) else 0

        a_shape_crash = 1 if t3_max > 0.05 and t10_min < -0.10 else 0

        results.append({
            'stock': stock,
            'name': item.get('name'),
            'signal_date': date_str,
            'signal_price': item.get('signal_price'),
            'signal_score': item.get('signal_score'),
            'signal_entry_type': item.get('signal_entry_type'),
            't1_max_ret': t1_max,
            't3_max_ret': t3_max,
            't5_max_ret': t5_max,
            't10_max_ret': t10_max,
            't1_min_ret': t1_min,
            't3_min_ret': t3_min,
            't5_min_ret': t5_min,
            't10_min_ret': t10_min,
            'hit_limit_up_within_5d': hit_limit_up,
            'hit_limit_down_within_5d': hit_limit_down,
            'a_shape_crash_flag': a_shape_crash,
            'data_quality_flag': data_quality_flag
        })

    df = pd.DataFrame(results)
    df.to_csv('jq_oos_watch_pool_forward_returns.csv', index=False, encoding='utf-8-sig')
    print("Generated jq_oos_watch_pool_forward_returns.csv")
    return df

def run_failed_trades_validation():
    print("Running Failed Trades Validation...")
    results = []
    for item in failed_trades:
        stock = item.get('stock')
        entry_date = item.get('entry_date')
        exit_date = item.get('exit_date')
        if not stock or not entry_date or not exit_date: continue

        prices_df = get_price(stock, start_date=entry_date, end_date=exit_date, frequency='daily', fields=['close', 'high', 'low'])

        data_quality_flag = 0 if not prices_df.empty else 1

        max_ret, min_ret, max_dd = np.nan, np.nan, np.nan
        p1, p3, p5 = np.nan, np.nan, np.nan

        if not prices_df.empty:
            closes = prices_df['close'].values
            highs = prices_df['high'].values
            lows = prices_df['low'].values
            base_p = closes[0]
            max_ret = (max(highs) - base_p) / base_p
            min_ret = (min(lows) - base_p) / base_p

            if len(closes) > 1: p1 = (closes[1] - base_p)/base_p
            if len(closes) > 3: p3 = (closes[3] - base_p)/base_p
            if len(closes) > 5: p5 = (closes[5] - base_p)/base_p

            max_dd = min_ret # Simplification

        a_shape_crash = 1 if max_ret > 0.05 and min_ret < -0.05 else 0

        results.append({
            'stock': stock,
            'name': item.get('name'),
            'entry_date': entry_date,
            'exit_date': exit_date,
            'entry_type': item.get('entry_type'),
            'exit_reason': item.get('exit_reason'),
            'pnl_pct_log': item.get('pnl_pct'),
            'pnl_val_log': item.get('pnl_val'),
            'hold_days_log': item.get('hold_days'),
            'is_fast_loss': item.get('is_fast_loss', 0),
            'oos_classification_basis': item.get('oos_classification_basis'),
            'entry_to_exit_max_ret': max_ret,
            'entry_to_exit_min_ret': min_ret,
            'post_entry_1d_ret': p1,
            'post_entry_3d_ret': p3,
            'post_entry_5d_ret': p5,
            'max_drawdown_before_exit': max_dd,
            'was_a_shape_crash': a_shape_crash,
            'data_quality_flag': data_quality_flag
        })

    df = pd.DataFrame(results)
    df.to_csv('jq_oos_failed_trade_price_path.csv', index=False, encoding='utf-8-sig')
    print("Generated jq_oos_failed_trade_price_path.csv")
    return df

def run_promotion_block_validation():
    print("Running Promotion Block Validation...")
    results = []
    for item in promotion_events:
        stock = item.get('stock')
        block_date = item.get('block_date') or item.get('date')
        if not stock or not block_date: continue

        prices_df = get_price(
            stock,
            start_date=block_date,
            end_date='2026-07-01',
            frequency='daily',
            fields=['close', 'high', 'low'],
            skip_paused=False,
            fq='pre'
        )
        if prices_df is not None and len(prices_df) > 11:
            prices_df = prices_df.iloc[:11]

        data_quality_parts = ['close_proxy']
        if prices_df is None or prices_df.empty:
            data_quality_parts.append('missing_price')
        elif len(prices_df) < 11:
            data_quality_parts.append('insufficient_forward_days')

        highs = prices_df['high'].values if prices_df is not None and not prices_df.empty else []
        lows = prices_df['low'].values if prices_df is not None and not prices_df.empty else []
        closes = prices_df['close'].values if prices_df is not None and not prices_df.empty else []
        base_p = closes[0] if len(closes) > 0 else np.nan

        t1_high = calc_max_ret(highs, base_p, 1)
        t3_high = calc_max_ret(highs, base_p, 3)
        t5_high = calc_max_ret(highs, base_p, 5)
        t10_high = calc_max_ret(highs, base_p, 10)
        t1_low = calc_min_ret(lows, base_p, 1)
        t3_low = calc_min_ret(lows, base_p, 3)
        t5_low = calc_min_ret(lows, base_p, 5)
        t10_low = calc_min_ret(lows, base_p, 10)

        max_opp_cost = t10_high

        label = 'Unclear'
        if not np.isnan(t10_high):
            if t10_high >= 0.10: label = 'Confirmed-High'
            elif t10_high >= 0.05: label = 'Confirmed-Medium'
            else: label = 'Confirmed-Low'

        results.append({
            'stock': stock,
            'name': item.get('name', 'N/A'),
            'block_date': block_date,
            'exit_price': base_p,
            'exit_price_source': 'close_proxy',
            'pnl_pct_at_block': item.get('pnl_pct_at_block', item.get('post_pnl_ratio', np.nan)),
            'hold_days': item.get('hold_days', 'N/A'),
            'post_block_1d_high_ret': t1_high,
            'post_block_3d_high_ret': t3_high,
            'post_block_5d_high_ret': t5_high,
            'post_block_10d_high_ret': t10_high,
            'post_block_1d_low_ret': t1_low,
            'post_block_3d_low_ret': t3_low,
            'post_block_5d_low_ret': t5_low,
            'post_block_10d_low_ret': t10_low,
            'max_opportunity_cost_10d': max_opp_cost,
            'truncation_risk_verified_label': label,
            'data_quality_flag': ';'.join(data_quality_parts)
        })

    df = pd.DataFrame(results)
    df.to_csv('jq_promotion_block_10d_path.csv', index=False, encoding='utf-8-sig')
    print("Generated jq_promotion_block_10d_path.csv")
    return df

def generate_summary_and_report_legacy_disabled(df_market, df_watch, df_failed_val, df_promo):
    """Legacy hard-coded report disabled. Use data-driven generate_summary_and_report below."""
    raise RuntimeError('legacy structural decay report is disabled')
def generate_summary_and_report(df_market, df_watch, df_failed_val, df_promo):
    print("Generating Summary and Report...")

    watch_count = len(df_watch)
    t5_pos = (df_watch['t5_max_ret'] > 0).sum() / watch_count if watch_count else 0
    t10_pos = (df_watch['t10_max_ret'] > 0).sum() / watch_count if watch_count else 0
    t5_limit = df_watch['hit_limit_up_within_5d'].sum() / watch_count if watch_count else 0
    watch_limit_down = df_watch['hit_limit_down_within_5d'].sum() / watch_count if watch_count else 0
    watch_a_shape = df_watch['a_shape_crash_flag'].sum() / watch_count if watch_count else 0

    fail_count = len(df_failed_val)
    fail_fast_loss = (
        df_failed_val['is_fast_loss'].sum() / fail_count
        if fail_count and 'is_fast_loss' in df_failed_val.columns else 0
    )
    fail_a_shape = df_failed_val['was_a_shape_crash'].sum() / fail_count if fail_count else 0

    promo_count = len(df_promo)
    if promo_count and 'truncation_risk_verified_label' in df_promo.columns:
        promo_high = (df_promo['truncation_risk_verified_label'] == 'Confirmed-High').sum()
        promo_med = (df_promo['truncation_risk_verified_label'] == 'Confirmed-Medium').sum()
        promo_low = (df_promo['truncation_risk_verified_label'] == 'Confirmed-Low').sum()
    else:
        promo_high = 0
        promo_med = 0
        promo_low = 0

    breadth_fields = [
        'market_up_ratio',
        'market_down_ratio',
        'market_above_ma5_ratio',
        'market_above_ma10_ratio',
        'market_above_ma20_ratio',
        'limit_up_count',
        'limit_down_count',
        'median_ret_1d',
        'median_money',
        'median_money_change_5d',
    ]
    market_breadth_available = 0
    non_na_count = 0
    if not df_market.empty:
        available_cols = [c for c in breadth_fields if c in df_market.columns]
        if available_cols:
            non_na_count = int(df_market[available_cols].notna().sum().sum())
            market_breadth_available = 1 if non_na_count > 0 else 0

    if promo_count == 0:
        final_diagnosis = 'D. raw price evidence insufficient; continue data repair; do not design new mechanism'
    elif not market_breadth_available:
        final_diagnosis = 'B_partial_only. promotion proxy available; market breadth insufficient; no regime switcher conclusion'
    elif promo_high + promo_med > 0:
        final_diagnosis = 'B_partial_with_breadth_proxy. promotion truncation candidate; research-only, no strategy design yet'
    else:
        final_diagnosis = 'D. promotion truncation not confirmed enough; continue evidence collection'

    summary_data = [
        ('watch_pool_count', watch_count, 'Total raw signals generated in OOS'),
        ('watch_pool_t5_positive_ratio', t5_pos, 'Ratio of signals achieving positive max return in 5 days'),
        ('watch_pool_t10_positive_ratio', t10_pos, 'Ratio of signals achieving positive max return in 10 days'),
        ('watch_pool_t5_hit_limit_up_ratio', t5_limit, 'Limit up hitting ratio within 5 days'),
        ('watch_pool_hit_limit_down_ratio', watch_limit_down, 'Limit down hitting ratio within 5 days'),
        ('watch_pool_a_shape_crash_ratio', watch_a_shape, 'Signals creating an A-shape crash pattern'),
        ('failed_trade_count', fail_count, 'Total analyzed failed trades in OOS'),
        ('failed_trade_fast_loss_ratio', fail_fast_loss, 'Failed trades marked as fast loss in logs'),
        ('failed_trade_a_shape_crash_ratio', fail_a_shape, 'Failed trades that experienced A-shape crash'),
        ('promotion_block_count', promo_count, 'Total promotion block events'),
        ('promotion_confirmed_high_count', promo_high, 'Truncation risk >= 10%'),
        ('promotion_confirmed_medium_count', promo_med, 'Truncation risk between 5% and 10%'),
        ('promotion_confirmed_low_count', promo_low, 'Truncation risk < 5%'),
        ('market_breadth_available', market_breadth_available, '1 means at least one raw breadth field was computed'),
        ('market_breadth_non_na_cell_count', non_na_count, 'Non-NA raw breadth cells across required fields'),
        ('market_breadth_universe', 'index_constituents_proxy', '000852.XSHG + 000905.XSHG constituents if available'),
        (
            'market_weak_days',
            len(df_market[df_market['index_000852_ret_5d'] < 0]) if 'index_000852_ret_5d' in df_market.columns else np.nan,
            'Days with negative 5d return on 852'
        ),
        ('final_diagnosis', final_diagnosis, 'Data-driven final verdict')
    ]

    df_summary = pd.DataFrame(summary_data, columns=['metric', 'value', 'interpretation'])
    df_summary.to_csv('jq_structural_decay_summary.csv', index=False, encoding='utf-8-sig')
    print("Generated jq_structural_decay_summary.csv")

    if market_breadth_available:
        market_text = (
            "market breadth universe = index constituents proxy "
            "(000852.XSHG + 000905.XSHG). Raw breadth cells computed: {}. "
            "This is proxy evidence, not full-market proof."
        ).format(non_na_count)
    else:
        market_text = (
            "market breadth insufficient; structural decay not fully confirmed "
            "by raw breadth. Do not claim raw-market proof of micro-crowding."
        )

    if watch_count:
        watch_text = (
            "WATCH_POOL_ADD count = {count}. T+5 max positive ratio = {t5}; "
            "T+10 max positive ratio = {t10}; 5d limit-up hit ratio = {lim}; "
            "A-shape crash ratio = {ashape}. Conclusion: Watch Pool still has "
            "upside spike ability; risk is path drawdown / confirmation timing, "
            "not simple signal decay."
        ).format(
            count=watch_count,
            t5=pct_or_na(t5_pos),
            t10=pct_or_na(t10_pos),
            lim=pct_or_na(t5_limit),
            ashape=pct_or_na(watch_a_shape)
        )
    else:
        watch_text = "No WATCH_POOL records; insufficient evidence."

    failed_text = (
        "OOS failed trade count = {count}. fast_loss ratio = {fast}; "
        "A-shape crash ratio = {ashape}. Conclusion: separate fast loss from "
        "A-shape crash; do not claim high A-shape proportion unless this ratio supports it."
    ).format(count=fail_count, fast=pct_or_na(fail_fast_loss), ashape=pct_or_na(fail_a_shape))

    promo_text = (
        "promotion block count = {count}. Confirmed-High = {high}; "
        "Confirmed-Medium = {med}; Confirmed-Low = {low}. "
        "Exit price source is close_proxy, marked in data_quality_flag; no real fill price is fabricated."
    ).format(count=promo_count, high=promo_high, med=promo_med, low=promo_low)
    if promo_count == 0:
        promo_conclusion = (
            "D. Original price evidence insufficient; continue data repair; "
            "do not design new mechanism."
        )
    elif promo_high + promo_med > 0:
        promo_conclusion = (
            "Promotion truncation has proxy evidence, but this is close_proxy research data. "
            "It may support continued observation, not direct mainline or live mechanism design."
        )
    else:
        promo_conclusion = (
            "Promotion block proxy evidence does not show meaningful 10d opportunity cost. "
            "Do not proceed to promotion protection design."
        )

    report_md = """# JQ OOS Structural Decay Report

## 1. Market Breadth Evidence

{market_text}

## 2. Watch Pool Forward Returns

{watch_text}

## 3. Failed Trade Path

{failed_text}

## 4. Promotion Block 10d Path

{promo_text}

Promotion conclusion: {promo_conclusion}

## 5. Final Diagnosis

{final_diagnosis}

## 6. Guardrails

* This report is generated from CSV data produced by this research script.
* Do not write that 7 promotion blocks are verified unless `jq_promotion_block_10d_path.csv` has 7 rows.
* Do not write Confirmed-High unless `truncation_risk_verified_label` contains Confirmed-High.
* Do not claim raw micro-crowding proof when market breadth fields are NA.
* Do not claim Watch Pool signals simply decayed if T+5/T+10 max return ratios remain high.
* Do not claim high A-shape crash ratio when `failed_trade_a_shape_crash_ratio` is low.
* This is research-only; no mainline, no live trading, no parameter optimization.
""".format(
        market_text=market_text,
        watch_text=watch_text,
        failed_text=failed_text,
        promo_text=promo_text,
        promo_conclusion=promo_conclusion,
        final_diagnosis=final_diagnosis
    )
    with open('jq_oos_structural_decay_report.md', 'w', encoding='utf-8') as f:
        f.write(report_md)
    print("Generated jq_oos_structural_decay_report.md")

import os
import zipfile

def package_outputs():
    print("Packaging outputs into zip file...")
    files_to_zip = [
        'jq_oos_market_regime_daily.csv',
        'jq_oos_watch_pool_forward_returns.csv',
        'jq_oos_failed_trade_price_path.csv',
        'jq_promotion_block_10d_path.csv',
        'jq_structural_decay_summary.csv',
        'jq_oos_structural_decay_report.md'
    ]
    zip_filename = 'v140D_jq_oos_structural_decay_outputs.zip'

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_zip:
            if os.path.exists(f):
                zf.write(f, f)
                print(f"Added {f} to zip.")
            else:
                print(f"WARNING: missing_output_file: {f}")

    print(f"Packaging complete: {zip_filename}")

if __name__ == '__main__':
    print("Starting JoinQuant OOS Structural Decay Research Validation...")
    df_market = run_market_regime_validation()
    df_watch = run_watch_pool_validation()
    df_failed_val = run_failed_trades_validation()
    df_promo = run_promotion_block_validation()
    generate_summary_and_report(df_market, df_watch, df_failed_val, df_promo)
    package_outputs()
    print("All tasks completed.")
