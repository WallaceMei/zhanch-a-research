# -*- coding: utf-8 -*-
"""Top250 seed 池·hold_T5 四关法庭 — 机制 + 小样本验证(报确认后再全量)。

验:① 2026 未进(panel 本就到2025-12-31)② IS/OOS 切分 ③ 池内 hold_T5 Rank IC 算得出、方向锁、OOS不翻向
   ④ ★打乱 hold_T5 归零自检 ⑤ 自指标注逻辑(哪些因子跟 seed/预筛逻辑相关)。
小样本=2因子(open_ratio 干净 / ret3 自指)。conditioned_on_dragon_seed。py-3.10。
"""
import io
import os
import sys
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "dragon_event_study", "factor_court_top12"))
import core as C   # 复用纯统计:daily_ic_series/hac_t_mean/gate1_eval/shuffle_null/two_sided_p

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(HERE, "seed250_panel_2020_2025.csv")

FACTORS = ["open_ratio", "auc_ratio", "auc_amount", "close_to_high",
           "ret3", "avg_money", "close_to_20d_high", "avg_range"]
# ★自指标注:Top250 = seed(ret3_top160 ∪ money_top20%) → 6因子预筛(avg_money_5/10,ret_5/10,close_to_20d_high,range_10)
SEED_RELATED = {
    "ret3": "seed 用 ret3_top160(直接自指)",
    "avg_money": "seed money_top + 预筛 avg_money_5/10(直接自指)",
    "close_to_20d_high": "预筛6因子之一(0.15权,自指)",
    "avg_range": "预筛 range_10(0.15权,自指)",
    "open_ratio": "", "auc_ratio": "", "auc_amount": "", "close_to_high": "",
}
MAIN = os.environ.get("MAIN_HOLD", "hold_T5")    # 打板重审用 MAIN_HOLD=hold_T1
HAC_LAG = {"hold_T1": 1, "hold_T3": 3, "hold_T5": 5, "hold_T10": 10}


def load():
    d = pd.read_csv(PANEL, dtype={"entry_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    assert d["year"].max() == 2025 and (d["year"] == 2026).sum() == 0, "红线:2026!"
    d["seg"] = np.where(d.year <= 2023, "IS", "OOS")
    return d


def main():
    print("=" * 74)
    print("Top250 seed 池·hold_T5 四关法庭 — 机制+小样本 (conditioned_on_dragon_seed)")
    print("=" * 74)
    d = load()
    print("\n[①② 切分/holdout]")
    print("  行=%d max_year=%d 2026行=%d | IS(2020-23)=%d OOS(24-25)=%d" % (
        len(d), d.year.max(), (d.year == 2026).sum(), (d.seg == "IS").sum(), (d.seg == "OOS").sum()))
    print("  hold_T5 有效行=%d(缺=%d)" % (d[MAIN].notna().sum(), d[MAIN].isna().sum()))
    assert d.year.max() == 2025 and (d.year == 2026).sum() == 0

    print("\n[⑤ 自指标注(关键)]")
    for f in FACTORS:
        tag = SEED_RELATED[f]
        print("  %-18s %s" % (f, ("★自指: " + tag) if tag else "干净(非seed/预筛逻辑)"))

    print("\n[③ 池内 %s 区分力:IS锁方向→OOS不翻向]  HAC lag=%d" % (MAIN, HAC_LAG[MAIN]))
    for f in ["open_ratio", "ret3"]:
        ris, _ = C.gate1_eval(d, f, MAIN, HAC_LAG[MAIN], "IS")
        ros, _ = C.gate1_eval(d, f, MAIN, HAC_LAG[MAIN], "OOS")
        flip = np.sign(ris["mean_ic"]) != np.sign(ros["mean_ic"])
        print("  %-12s%s | IS IC=%+.4f t=%+.2f p=%.3f n=%d | OOS IC=%+.4f t=%+.2f p=%.3f | %s" % (
            f, "(自指)" if SEED_RELATED[f] else "(干净)", ris["mean_ic"], ris["hac_t"], ris["p_two_sided"],
            ris["n_days"], ros["mean_ic"], ros["hac_t"], ros["p_two_sided"],
            "翻向!" if flip else "未翻向✓"))

    print("\n[④ ★打乱 %s 归零自检](IS, n_shuffle=120)" % MAIN)
    ok_all = True
    for f in ["open_ratio", "ret3"]:
        nmu, nt, real = C.shuffle_null(d, f, MAIN, HAC_LAG[MAIN], "IS", n_shuffle=120, seed=42)
        nm = float(np.mean(nmu)); ts = float(np.std(nt)); sig = float(np.mean(np.abs(nt) > 1.96))
        ok = abs(nm) < 0.01 and ts < 1.5 and sig < 0.15
        ok_all = ok_all and ok
        print("  %-12s real IC=%+.4f t=%+.2f | null IC均=%+.5f t_std=%.2f sig%%=%.0f%% → %s" % (
            f, real["mean_ic"], real["hac_t"], nm, ts, sig * 100, "归零✓" if ok else "✗"))

    print("\n" + "=" * 74)
    print("机制自检:%s" % ("SELF_CHECK_PASS — 可全量" if ok_all else "SELF_CHECK_FAILED"))
    print("=" * 74)
    print("说明:小样本验机制;未全量、未下A/B判定、未碰2026。")


if __name__ == "__main__":
    main()
