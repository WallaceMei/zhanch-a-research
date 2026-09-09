# -*- coding: utf-8 -*-
"""第二步·①验因子 第二轮(可交易持有收益)— 机制+小样本验证。

核对后口径(Wallace 拍板):买 = entry_date(T) open(dragon真实入场,T+1合法),
  hold_return_Tk = 卖 T+k close = 底座 day(k+1):T3=day4 / T5=day6 / T10=day11;主判据 T5。
  排除 day1(0天持仓,违反T+1)。本轮用连续持有收益 Rank IC 复核 big10 触及标签的波动率假阳性。

小样本=2因子(avg_range[big10下疑似假阳性] + close_to_high),target=hold_T5,验:
  ① 2026未进 ② IS/OOS切分对 ③ hold_T5口径=day6且T+1合法 ④ ★打乱hold_T5归零自检。
复用 ../factor_court_top12/core.py 的统计与关卡函数。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "factor_court_top12")
sys.path.insert(0, _CORE)
import core as C

HERE = os.path.dirname(os.path.abspath(__file__))
# hold_return 口径:买 T open,卖 T+k close = 底座 day(k+1)
HOLD = {"T3": "day4", "T5": "day6", "T10": "day11"}
HOLD_LAG = {"T3": 3, "T5": 5, "T10": 10}
MAIN = "hold_T5"


def load_pool_tradable(verbose=True):
    d = pd.read_csv(C.BASE, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    keep = (["entry_date", "code", "year"] + C.BASE_FACTORS +
            ["is_big_meat_10", "is_super_meat_20"] + list(HOLD.values()))
    u = d.drop_duplicates(["entry_date", "code"])[keep].copy()
    # 合并重算的3因子(复用第一轮 augment 产物)
    aug = pd.read_csv(os.path.join(_CORE, "_factors_augmented.csv"), dtype={"entry_date": str, "code": str})
    u = u.merge(aug, on=["entry_date", "code"], how="left")
    # ★剔 2026 holdout(按 entry 年;2025入场的forward可含2026初价作结果,与第一轮big10标签同口径)
    u = u[u["year"] != C.HOLDOUT_YEAR].reset_index(drop=True)
    assert (u["year"] == C.HOLDOUT_YEAR).sum() == 0 and u["year"].max() <= 2025, "红线:2026进入!"
    # hold_return 列(percent,Rank IC 对单调变换不敏感)
    for k, col in HOLD.items():
        u["hold_%s" % k] = u[col]
    u["seg"] = np.where(u["year"] <= C.IS_YEARS[1], "IS",
                        np.where(u["year"] <= C.OOS_YEARS[1], "OOS", "DROP"))
    if verbose:
        print("[load] unique 去2026 = %d | IS=%d OOS=%d" % (
            len(u), (u.seg == "IS").sum(), (u.seg == "OOS").sum()))
    return u


def main():
    print("=" * 72)
    print("可交易持有收益复核 — 机制+小样本自检 (conditioned_on_dragon_top12)")
    print("=" * 72)
    df = load_pool_tradable()

    print("\n[① 口径确认]")
    print("  买入=entry(T) open;hold_T5=day6=close[T+5]/open[T]-1 → 持有5天、T+1合法(最早T+2才卖,这里T+5)")
    print("  day1(0天持仓,违反T+1)= 不使用 ✓")
    print("  hold_T5 与 day6 一致?", bool((df["hold_T5"].fillna(-999) == df["day6"].fillna(-999)).all()))

    print("\n[② 切分/holdout 断言]")
    print("  max year =", int(df.year.max()), "| 2026行 =", int((df.year == 2026).sum()),
          "| seg =", sorted(df.seg.unique()))
    assert df.year.max() == 2025 and (df.year == 2026).sum() == 0 and set(df.seg.unique()) <= {"IS", "OOS"}
    print("  → 2026未进、IS/OOS对 ✓")

    SMALL = ["avg_range", "close_to_high"]
    print("\n[③ hold_T5 池内 Rank IC:IS锁方向 → OOS不翻向]  HAC lag=%d" % HOLD_LAG["T5"])
    for f in SMALL:
        ris, _ = C.gate1_eval(df, f, MAIN, HOLD_LAG["T5"], "IS")
        ros, _ = C.gate1_eval(df, f, MAIN, HOLD_LAG["T5"], "OOS")
        flip = np.sign(ris["mean_ic"]) != np.sign(ros["mean_ic"])
        print("  %-14s | IS IC=%+.4f t=%+.2f p=%.3f n=%d | OOS IC=%+.4f t=%+.2f n=%d | %s" % (
            f, ris["mean_ic"], ris["hac_t"], ris["p_two_sided"], ris["n_days"],
            ros["mean_ic"], ros["hac_t"], ros["n_days"], "翻向!" if flip else "未翻向✓"))
        # 对照:同因子 big10 IC(看是否假阳性)
        b_is, _ = C.gate1_eval(df, f, "is_big_meat_10", C.HAC_LAG_EVENT, "IS")
        print("    [对照] %s big10 IS IC=%+.4f t=%+.2f  ←→ hold_T5 IS IC=%+.4f t=%+.2f" % (
            f, b_is["mean_ic"], b_is["hac_t"], ris["mean_ic"], ris["hac_t"]))

    print("\n[④ ★打乱 hold_T5 归零自检](IS, n_shuffle=150)")
    ok_all = True
    for f in SMALL:
        nmu, nt, real = C.shuffle_null(df, f, MAIN, HOLD_LAG["T5"], "IS", n_shuffle=150, seed=42)
        nm = float(np.mean(nmu)); ts = float(np.std(nt)); sig = float(np.mean(np.abs(nt) > 1.96))
        ok = abs(nm) < 0.01 and ts < 1.5 and sig < 0.15
        ok_all = ok_all and ok
        print("  %-14s real IC=%+.4f t=%+.2f | null IC mean=%+.5f t_std=%.3f sig%%=%.1f%% → %s" % (
            f, real["mean_ic"], real["hac_t"], nm, ts, sig * 100, "归零✓" if ok else "✗"))

    print("\n" + "=" * 72)
    print("机制自检:%s" % ("SELF_CHECK_PASS — 可全量" if ok_all else "SELF_CHECK_FAILED"))
    print("=" * 72)
    print("说明:小样本2因子验机制;未全量、未下结论、未碰2026、未多因子。")


if __name__ == "__main__":
    main()
