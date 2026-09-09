# -*- coding: utf-8 -*-
"""第二步·第1阶段:机制 + 小样本验证(报 Wallace 确认后再全量)。

验四件事:
  ① 2026 holdout 确实没进任何计算(断言)
  ② IS(2020-23)/OOS(24-25)切分正确
  ③ 池内逐日 rank-IC / big10 区分力 算得出、方向可锁、OOS 只验不翻向
  ④ ★打乱目标归零自检:打乱 big10 后 IC 均值→≈0、HAC t→不显著(N(0,1))
小样本=只审 2 个因子(open_ratio, ret3),证明机制对。不是全量、不下结论。
"""
import io
import os
import sys
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core as C


def main():
    print("=" * 72)
    print("Top12 池内单因子验证 — 机制 + 小样本自检 (conditioned_on_dragon_top12)")
    print("=" * 72)

    # ---------- ① 数据层 + 2026 holdout 断言 ----------
    df = C.load_pool(verbose=True)
    print("\n[①+② 切分/holdout 断言]")
    print("  数据最大年份 =", int(df.year.max()), "(应=2025)")
    print("  2026 行数 =", int((df.year == 2026).sum()), "(应=0)")
    print("  seg 取值 =", sorted(df.seg.unique()), "(应只有 IS/OOS,无 DROP/2026)")
    assert df.year.max() == 2025 and (df.year == 2026).sum() == 0
    assert set(df.seg.unique()) <= {"IS", "OOS"}
    print("  → 2026 未进任何计算 ✓ ;IS/OOS 切分正确 ✓")

    SMALL = ["open_ratio", "ret3"]
    LAB = C.MAIN_LABEL    # is_big_meat_10

    # ---------- ③ 池内 IC / big10 区分力 + 方向锁 + OOS 不翻向 ----------
    print("\n[③ 池内 big10 区分力:IS 锁方向 → OOS 只验不翻向]  HAC lag=%d" % C.HAC_LAG_EVENT)
    print("  %-12s | %-26s | %-26s | 方向" % ("factor", "IS(2020-23)", "OOS(2024-25)"))
    for f in SMALL:
        ris, _ = C.gate1_eval(df, f, LAB, C.HAC_LAG_EVENT, "IS")
        ros, _ = C.gate1_eval(df, f, LAB, C.HAC_LAG_EVENT, "OOS")
        dir_is = "+" if ris["mean_ic"] > 0 else "-"
        flip = (np.sign(ris["mean_ic"]) != np.sign(ros["mean_ic"]))
        print("  %-12s | IC=%+.4f t=%+.2f p=%.3f n=%3d | IC=%+.4f t=%+.2f p=%.3f n=%3d | IS锁%s OOS%s" % (
            f, ris["mean_ic"], ris["hac_t"], ris["p_two_sided"], ris["n_days"],
            ros["mean_ic"], ros["hac_t"], ros["p_two_sided"], ros["n_days"],
            dir_is, ("翻向!" if flip else "未翻向✓")))

    # 顺带:连续前向收益各周期 IC(看哪个周期区分力强)——仅展示机制,不下结论
    print("\n  [前向连续收益 Rank IC(IS),看周期]")
    for f in SMALL:
        row = []
        for pk, col in C.FWD_PERIODS.items():
            r, _ = C.gate1_eval(df, f, col, C.HAC_LAG_FWD[pk], "IS")
            row.append("%s IC=%+.4f t=%+.2f" % (pk, r["mean_ic"], r["hac_t"]))
        print("  %-12s | %s" % (f, " | ".join(row)))

    # ---------- ④ ★打乱目标归零自检 ----------
    print("\n[④ ★打乱 big10 标签归零自检](IS, n_shuffle=150)")
    print("  期望:打乱后 null IC 均值≈0、null HAC t≈N(0,1)(mean≈0 std≈1);真实信号应离 null 远")
    selfcheck_pass = True
    for f in SMALL:
        nmu, nt, real = C.shuffle_null(df, f, LAB, C.HAC_LAG_EVENT, "IS",
                                       n_shuffle=150, seed=42)
        null_mu_mean = float(np.mean(nmu)); null_mu_abs = float(np.mean(np.abs(nmu)))
        null_t_mean = float(np.mean(nt)); null_t_std = float(np.std(nt))
        null_t_sig = float(np.mean(np.abs(nt) > 1.96))   # null 里"显著"比例,应≈5%
        # 真实 IC 在 null 分布中的分位(双尾)
        pct = float(np.mean(np.abs(nmu) >= abs(real["mean_ic"])))
        ok_null0 = abs(null_mu_mean) < 0.01 and null_t_std < 1.5 and null_t_sig < 0.15
        selfcheck_pass = selfcheck_pass and ok_null0
        print("  %-12s real: IC=%+.4f t=%+.2f" % (f, real["mean_ic"], real["hac_t"]))
        print("    null IC: mean=%+.5f mean|.|=%.5f | null t: mean=%+.3f std=%.3f sig%%=%.1f%% | real在null尾部比例=%.3f → %s" % (
            null_mu_mean, null_mu_abs, null_t_mean, null_t_std, null_t_sig * 100, pct,
            "归零✓" if ok_null0 else "未归零✗"))

    print("\n" + "=" * 72)
    print("机制自检结论:%s" % ("SELF_CHECK_PASS — 机制正确,可全量" if selfcheck_pass
                              else "SELF_CHECK_FAILED — 打乱未归零,停止"))
    print("=" * 72)
    print("说明:本步只验机制(2因子小样本),未下因子结论、未全量、未碰 2026、未跑四关FDR/去冗余/衰减。")


if __name__ == "__main__":
    main()
