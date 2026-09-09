# -*- coding: utf-8 -*-
"""Project1 Paper Step2 — 实时进场闸监测器(增量版,feed 无关)。

与 engine_phaseA.find_signal(entry_mode='full') **逐bar状态等价**:
  - VWAP = 全日累计 amount / 累计成交股数(含 09:30 竞价根的量额)
  - 判定只在观察窗 [max(obs_start,'09:31'), obs_end] 的**已完结** 1m bar 收盘时做
  - 站稳(close>=VWAP)后:(a) 全程未有效跌破 min_low >= VWAP*(1-tol) 当根即信号
    (b) 回踩(close<VWAP)后 win 根内收回 close>=VWAP 即信号
  - 信号"那一刻" = 信号bar完结时;capture_price = 信号bar close(判定价,
    live 另记 capture 瞬间最新 tick 价,两者差值供成本模型校准)

本模块零第三方依赖(纯python),可被 replay(历史bar)与 live(xtdata bar)共用;
参数默认值镜像 engine_phaseA.DEFAULT_CFG,等价性由 run_step2_replay_check.py 对拍守护。

只读判定,不含任何交易指令。
"""

# 镜像 engine_phaseA.DEFAULT_CFG 的进场闸参数(对拍脚本守护一致性)
GATE_DEFAULTS = dict(obs_start='09:30', obs_end='10:30',
                     vwap_break_tol=0.005, vwap_pullback_window=15)


class GateMonitor:
    """单票增量进场闸。按到达顺序 push 已完结 1m bar,命中返回 signal dict(一次性)。"""

    def __init__(self, code, obs_start=None, obs_end=None, tol=None, win=None):
        g = GATE_DEFAULTS
        self.code = code
        self.obs_lo = max(obs_start or g['obs_start'], '09:31')  # 跳过09:30竞价根(同批量版)
        self.obs_end = obs_end or g['obs_end']
        self.tol = g['vwap_break_tol'] if tol is None else tol
        self.win = g['vwap_pullback_window'] if win is None else win
        self.i = -1                 # 当日bar序号(含09:30竞价根,与批量版索引一致)
        self.cum_amt = 0.0          # 累计成交额(元)
        self.cum_vol_sh = 0.0       # 累计成交量(股)
        self.stand = False          # 是否已首次站稳
        self.run_min_low = float('inf')
        self.last_dip_i = None      # 最近一次回踩(close<VWAP)的bar序号
        self.signal = None          # 命中后固化
        self.expired = False        # 观察窗已过且未命中

    def push_bar(self, hm, o, h, l, c, vol_hand, amt):
        """推入一根**已完结** 1m bar(hm='09:31'式;vol单位=手;amt单位=元)。
        命中返回 signal dict,否则 None。命中/过窗后继续推入只累计不再判定。"""
        self.i += 1
        i = self.i
        self.cum_amt += float(amt)
        self.cum_vol_sh += float(vol_hand) * 100.0
        if self.signal is not None or self.expired:
            return None
        if hm > self.obs_end:
            self.expired = True
            return None
        if hm < self.obs_lo:
            return None
        if self.cum_vol_sh <= 0:                 # VWAP 未定义(等价批量版 isnan 跳过)
            return None
        v = self.cum_amt / self.cum_vol_sh
        c = float(c); l = float(l)

        if not self.stand:
            if c >= v:
                self.stand = True
                self.run_min_low = l
                if l >= v * (1 - self.tol):      # 站稳当根即判定(a)
                    return self._hit(i, hm, v, c)
            return None
        # 已首次站稳
        self.run_min_low = min(self.run_min_low, l)
        if c < v:                                # 回踩中
            self.last_dip_i = i
            return None
        if self.run_min_low >= v * (1 - self.tol):           # (a) 全程未有效跌破
            return self._hit(i, hm, v, c)
        if self.last_dip_i is not None and (i - self.last_dip_i) <= self.win:
            return self._hit(i, hm, v, c)                     # (b) 回踩win根内拉回
        return None

    def _hit(self, i, hm, vwap, close):
        self.signal = dict(code=self.code, bar_i=i, signal_hm=hm,
                           vwap=round(vwap, 4), capture_price=close)
        return self.signal


class PoolMonitor:
    """监测池(多票)封装:去重、逐bar分发、收集信号(同票被多组选中只监测一次)。"""

    def __init__(self, codes, **kw):
        self.mons = {c: GateMonitor(c, **kw) for c in dict.fromkeys(codes)}
        self.signals = {}           # code -> signal dict(含 capture 附加信息)

    def push_bar(self, code, hm, o, h, l, c, vol_hand, amt, extra=None):
        m = self.mons.get(code)
        if m is None or m.signal is not None:
            return None
        sig = m.push_bar(hm, o, h, l, c, vol_hand, amt)
        if sig is not None:
            if extra:
                sig.update(extra)
            self.signals[code] = sig
        return sig

    def pending(self):
        return [c for c, m in self.mons.items() if m.signal is None and not m.expired]
