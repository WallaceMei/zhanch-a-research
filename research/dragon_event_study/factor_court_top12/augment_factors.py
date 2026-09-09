# -*- coding: utf-8 -*-
"""补算 3 个底座没存的价量因子(avg_money/close_to_20d_high/avg_range)到 Top12 池。
口径与数据底座完全一致:用同一 repro_core._meta_from_df(中台 panel,剔停牌vol≤0),
对每个 (entry_date, code) 取截至 prev_date 的 20 日窗算 meta。2026 不需要(分析层会剔)。
输出 _factors_augmented.csv: entry_date, code, avg_money, close_to_20d_high, avg_range。
py-3.10,REPRO_BACKEND=warehouse。
"""
import io
import os
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["REPRO_BACKEND"] = "warehouse"
_DRAGON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _DRAGON)
import pandas as pd
import repro_core as R

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(_DRAGON, "event_study_dragon_2020_2026.csv")
OUT = os.path.join(HERE, "_factors_augmented.csv")


def main():
    d = pd.read_csv(BASE, dtype={"entry_date": str, "prev_date": str, "code": str})
    d["year"] = d["entry_date"].str[:4].astype(int)
    d = d[d["year"] != 2026]                       # 2026 holdout 不算
    u = d.drop_duplicates(["entry_date", "code"])[["entry_date", "prev_date", "code"]].copy()
    codes = sorted(u["code"].unique())
    print("唯一(date,code): %d | 唯一code: %d" % (len(u), len(codes)))

    # 中台日线 panel(剔停牌 vol≤0,与底座生成时同口径),覆盖 2020-2025
    panel = R.load_daily_panel(codes, "20200101", "20251231")
    print("panel 载入: %d 只有数据" % sum(1 for v in panel.values() if v is not None and len(v)))

    rows = []
    miss = 0
    for r in u.itertuples(index=False):
        df = panel.get(r.code)
        if df is None or len(df) == 0:
            miss += 1
            continue
        sl = df[df.index <= r.prev_date].tail(20)
        m = R._meta_from_df(sl)
        if m is None:
            miss += 1
            continue
        rows.append((r.entry_date, r.code, m["avg_money_5"], m["close_to_20d_high"], m["avg_range"]))
    out = pd.DataFrame(rows, columns=["entry_date", "code", "avg_money",
                                      "close_to_20d_high", "avg_range"])
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("已存 %s | 行 %d | 缺 %d" % (os.path.basename(OUT), len(out), miss))
    print(out.describe().to_string())


if __name__ == "__main__":
    main()
