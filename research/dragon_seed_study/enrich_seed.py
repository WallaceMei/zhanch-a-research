# -*- coding: utf-8 -*-
"""战车A 新研究主线·第一步 — enrich Top250 预筛池(seed 层)成研究面板。

跳出 dragon Top12 成品池(前三轮已证循环自证+整套不成立),回到更前的 Top250 seed 层
(dragon_score 还没排序),为"用可交易收益重找选股因子"备数据。本步只 enrich 生成面板,不验因子。

数据源:research/dragon_event_study/_pass1_2020_2026.json(每天 date→[prev_date, seed250码])。
  注:_pass1.json 是原4个月(全2026,holdout)→ 不用;用 _pass1_2020_2026.json 并剔 2026。
口径:复用数据中台 read + repro_core._meta_from_df,与 dragon_event_study 完全一致。
  - 竞价:read.auction(auction_open/volume/amount/prev_close/auction_return)
  - 价量:open_ratio/auc_ratio/auc_amount/close_to_high/ret3/avg_money/close_to_20d_high/avg_range
  - ★可交易 forward:买 entry(T) open、卖 T+N close → hold_T3/T5/T10(close[i0+N]/open[i0]-1);排除day1(0天);T+1合法
  - 标签:is_big_meat_10/super20(forward 窗内 max close-ret≥10%/20%,与底座同,仅对照)
★holdout 纯度:panel 只载到 2025-12-31,2026 价格不加载 → late-2025 的 hold 超窗标 NaN(不强造)。
SMOKE_DAYS 环境变量>0 时只 enrich 前 N 个交易日(小样本验口径)。py-3.10。
"""
import io
import os
import sys
import json
import numpy as np
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["REPRO_BACKEND"] = "warehouse"
_DRAGON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dragon_event_study")
sys.path.insert(0, _DRAGON)
import repro_core as R

HERE = os.path.dirname(os.path.abspath(__file__))
PASS1 = os.path.join(_DRAGON, "_pass1_2020_2026.json")
PANEL_END = "20251231"          # ★2026 不加载
FWD = {"hold_T1": 1, "hold_T3": 3, "hold_T5": 5, "hold_T10": 10}   # hold_T1=次日(打板主判据)=close[i0+1]/open[i0]
FORWARD_N = 20                  # 标签窗口(同底座)
SMOKE = int(os.environ.get("SMOKE_DAYS", "0"))


def main():
    with open(PASS1, "r", encoding="utf-8") as f:
        day_surv = json.load(f)
    days = sorted(d for d in day_surv if d <= "20251231")    # ★剔 2026
    assert max(days) <= "20251231" and not any(d.startswith("2026") for d in days), "红线:2026 进入!"
    if SMOKE > 0:
        days = days[:SMOKE]
    print("[seed] 交易日 %d (%s ~ %s)%s" % (len(days), days[0], days[-1],
          " [SMOKE]" if SMOKE > 0 else ""))

    codes = sorted({c for d in days for c in day_surv[d][1]})
    print("[seed] 唯一code %d" % len(codes))
    panel = R.load_daily_panel(codes, "20200101", PANEL_END)   # 中台日线,剔停牌vol≤0,不含2026
    print("[panel] 载入 %d 只" % sum(1 for v in panel.values() if v is not None and len(v)))

    rows = []
    n_seed = 0
    for di, date in enumerate(days):
        prev_date, seed = day_surv[date]
        n_seed += len(seed)
        auc = R.read_auction(seed, date)          # 当日竞价(批量)
        for code in seed:
            rec = {"entry_date": date, "prev_date": prev_date, "code": code}
            df = panel.get(code)
            # --- 日线 meta(截至 prev_date 的20日窗)---
            meta = None
            if df is not None and len(df):
                sl = df[df.index <= prev_date].tail(20)
                meta = R._meta_from_df(sl)
            if meta is not None:
                rec["ret3"] = meta["ret3"]; rec["avg_money"] = meta["avg_money_5"]
                rec["close_to_20d_high"] = meta["close_to_20d_high"]; rec["avg_range"] = meta["avg_range"]
                rec["close_to_high"] = meta["y_close"] / max(meta["y_high"], 0.01)
                rec["y_close"] = meta["y_close"]; rec["y_vol"] = meta["y_vol"]
            # --- 竞价 + 派生 ---
            a = auc.get(code)
            if a is not None and meta is not None and meta["y_close"] > 0:
                curr, avol, aamt = a
                rec["auction_open"] = curr; rec["auction_amount"] = aamt
                rec["open_ratio"] = curr / meta["y_close"] - 1
                rec["auc_ratio"] = avol / max(meta["y_vol"], 1)
                rec["auc_amount"] = aamt
            # --- 可交易 forward(买 entry open、卖 T+N close;2026价格不可得→NaN)---
            if df is not None and len(df) and date in df.index:
                idx = list(df.index); i0 = idx.index(date)
                o = df["open"].astype(float).values; c = df["close"].astype(float).values
                buy = o[i0]
                rec["buy_price"] = buy
                if buy > 0:
                    for h, n in FWD.items():
                        j = i0 + n
                        rec[h] = (c[j] / buy - 1.0) * 100 if j < len(c) else np.nan
                    # 标签:max close-ret(★与底座 big10 完全一致:close[i0+0..i0+19]=day1..20,含day1触及)
                    rs = [c[i0 + k] / buy - 1.0 for k in range(0, FORWARD_N) if i0 + k < len(c)]
                    if rs:
                        mx = max(rs)
                        rec["max_ret"] = mx * 100
                        rec["days_available"] = len(rs)
                        rec["window_incomplete"] = int(len(rs) < FORWARD_N)
                        rec["is_big_meat_10"] = int(mx >= 0.10)
                        rec["is_super_meat_20"] = int(mx >= 0.20)
            rows.append(rec)
        if (di + 1) % 200 == 0:
            print("  enrich 进度 %d/%d 天 (%d 行)" % (di + 1, len(days), len(rows)))

    out = pd.DataFrame(rows)
    out["year"] = out["entry_date"].str[:4].astype(int)
    assert out["year"].max() <= 2025 and (out["year"] == 2026).sum() == 0, "红线:2026 进入!"
    fn = "seed250_panel_smoke.csv" if SMOKE > 0 else "seed250_panel_2020_2025.csv"
    out.to_csv(os.path.join(HERE, fn), index=False, encoding="utf-8-sig")

    # ---- 报告摘要 ----
    print("\n=== enrich 完成 ===")
    print("面板行(stock-day): %d | 交易日 %d | seed合计 %d | 唯一code %d"
          % (len(out), out.entry_date.nunique(), n_seed, out.code.nunique()))
    print("每日 seed 数: 中位 %d 最小 %d 最大 %d"
          % (out.groupby("entry_date").size().median(), out.groupby("entry_date").size().min(),
             out.groupby("entry_date").size().max()))
    print("max year =", int(out.year.max()), "(应=2025) | 2026行 =", int((out.year == 2026).sum()))
    key = ["open_ratio", "auc_ratio", "auc_amount", "close_to_high", "ret3",
           "avg_money", "close_to_20d_high", "avg_range", "hold_T1", "hold_T3", "hold_T5", "hold_T10",
           "is_big_meat_10"]
    print("字段缺失率:")
    for k in key:
        if k in out.columns:
            print("  %-18s 缺失 %d (%.1f%%)" % (k, out[k].isna().sum(), out[k].isna().mean() * 100))
    print("落盘:", fn)


if __name__ == "__main__":
    main()
