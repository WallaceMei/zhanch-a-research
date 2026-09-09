# -*- coding: utf-8 -*-
"""Project1 Paper — 全局配置(spec §9 已定 + Phase A 口径)。

⚠️ 护栏1:实时链路(xtdata live bar/竞价 full_tick)未经实盘验证,
   2026-07-06 周一小样本实测通过前,不得开跑真实 paper(只能 mock/演习)。
⚠️ 护栏3:全系统只读——绝不 import xttrader / 不搭下单接口 / 不发交易指令。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PHASEA_DIR = os.path.normpath(os.path.join(HERE, '..', 'project1_phaseA'))
DRAGON_DIR = os.path.normpath(os.path.join(HERE, '..', 'dragon_event_study'))

# 状态与产物
STATE_DIR = os.path.join(HERE, 'paper_state')          # 真实 paper 状态(周一实测通过后启用)
DRILL_STATE_DIR = os.path.join(HERE, 'paper_state_drill')  # mock 演习专用(隔离,不污染真实)
OUT_DIR = os.path.join(HERE, 'out')
AI_LOG_DIR = os.path.join(STATE_DIR, 'ai_log')

# 三组(spec §2;唯一变量=选股)
GROUPS = ('ai_minimax', 'random3', 'all_in')
N_PICK = 3            # §9.1 AI/随机各选3只
N_SLOTS = 3           # §9.2 25%×3=75% 上限
POS_FRAC = 0.25       # 每只 25%,留 25% 现金

# 进出场(三组一致,护栏4;= Phase A 默认进场闸 + 整机 dd10 出场)
def engine_cfg():
    import engine_phaseA as E
    cfg = dict(E.DEFAULT_CFG)
    cfg['trail_mode'] = 'single'
    cfg['trail_single'] = 0.10
    return cfg

# MiniMax(§9.3 纯MiniMax;真实调用测试=周一清单项)
MINIMAX_API_URL = os.environ.get('MINIMAX_API_URL',
                                 'https://api.minimaxi.com/v1/text/chatcompletion_v2')
MINIMAX_MODEL = os.environ.get('MINIMAX_MODEL', 'MiniMax-Text-01')
MINIMAX_KEY_ENV = 'MINIMAX_API_KEY'      # 密钥只从环境变量读,绝不写进代码/日志
AI_TIMEOUT_SEC = 60
AI_DECISION_DEADLINE = '09:28'           # 盘前决策须在此前完成(9:25竞价后)

# 实时监测
LIVE_POLL_SEC = 3.0
LIVE_UNTIL = '10:33'                     # 信号窗到10:30(PhaseA obs_end),脚本余量自停

# 数据链
MAIN_DAILY_PARQUET = os.path.join(PHASEA_DIR, 'cache', 'daily_2020_2026.parquet')
TAIL_DAILY_PARQUET = os.path.join(PHASEA_DIR, 'cache', 'daily_tail.parquet')
TAIL_AUCTION_PARQUET = os.path.join(PHASEA_DIR, 'cache', 'auction_tail.parquet')
CANON_MIN_GLOB = 'D:/data_warehouse/canonical/minute_1m/by_code/code=*/year=*.parquet'
TUSHARE_PANEL_SCRIPT = os.path.join(DRAGON_DIR, 'tushare_daily_panel.py')
