# -*- coding: utf-8 -*-
"""验收门:v3 复现 2026-03-02~03-06 top3,对账聚宽日志 BIGMEAT_POOL_TOP。"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import repro_core as R

# 聚宽 ground truth(jq_v140D log,默认 dragon_score_mode=v3),top3/日。
# code(QMT), score, tpl, open_ratio%, close_to_high, auc_ratio
GT = {
    "20260302": [("603067.SH", 0.6916, "deep_water", 1.72, 0.9724, 0.0077),
                 ("600590.SH", 0.6880, "trend_core", 0.33, 0.9529, 0.0074),
                 ("600343.SH", 0.6590, "trend_core", 0.80, 0.9581, 0.0073)],
    "20260303": [("002015.SZ", 0.7161, "deep_water", 1.75, 0.9455, 0.0105),
                 ("002470.SZ", 0.7148, "trend_core", 1.03, 0.8534, 0.0345),
                 ("002272.SZ", 0.6938, "deep_water", 2.99, 0.9627, 0.0204)],
    "20260304": [("001896.SZ", 0.6805, "trend_core", 0.15, 0.8540, 0.0566),
                 ("600313.SH", 0.6768, "deep_water", 2.38, 0.9449, 0.0092),
                 ("000807.SZ", 0.6233, "deep_water", 2.59, 0.9555, 0.0080)],
    "20260305": [("600549.SH", 0.7920, "deep_water", 2.79, 0.9657, 0.0084),
                 ("603186.SH", 0.7679, "deep_water", 3.89, 0.9440, 0.0092),
                 ("002149.SZ", 0.7502, "deep_water", 1.88, 0.9446, 0.0086)],
    "20260306": [("600821.SH", 0.7409, "deep_water", 3.20, 0.9444, 0.0124),
                 ("600773.SH", 0.6339, "deep_water", 1.65, 0.9728, 0.0092),
                 ("600860.SH", 0.6224, "deep_water", 1.58, 0.9706, 0.0182)],
}


def ok(a, b, tol):
    return abs(a - b) <= tol


def main():
    R.connect()
    total_pass = total = 0
    for date in sorted(GT):
        pool = R.get_dragon_pool(date, mode='v3')
        my = {p['stock']: p for p in pool}
        print("\n===== %s  (本地 top%d) =====" % (date, len(pool)))
        print("  %-4s %-11s %-8s %-10s %7s %8s %8s" %
              ("rank", "code", "score", "tpl", "or%", "c2h", "ar"))
        for p in pool[:12]:
            print("  %-4d %-11s %-8.4f %-10s %6.2f%% %8.4f %8.4f" %
                  (p['rank'], p['stock'], p['dragon_score'], p['tpl'],
                   p['open_ratio'] * 100, p['close_to_high'], p['auction_ratio']))
        print("  --- vs 聚宽 GT top3 ---")
        for i, (code, sc, tpl, orr, c2h, ar) in enumerate(GT[date], 1):
            total += 1
            p = my.get(code)
            if p is None:
                print("  GT#%d %-11s MISSING in local pool  <<< FAIL" % (i, code))
                continue
            verdict = []
            verdict.append(("rank", p['rank'] == i))
            verdict.append(("score", ok(p['dragon_score'], sc, 0.0011)))
            verdict.append(("tpl", p['tpl'] == tpl))
            verdict.append(("or", ok(p['open_ratio'] * 100, orr, 0.011)))
            verdict.append(("c2h", ok(p['close_to_high'], c2h, 0.00011)))
            verdict.append(("ar", ok(p['auction_ratio'], ar, 0.00011)))
            allok = all(v for _, v in verdict)
            total_pass += allok
            fails = ",".join(k for k, v in verdict if not v)
            print("  GT#%d %-11s local(r%d s=%.4f %s or=%.2f%% c2h=%.4f ar=%.4f) %s%s" %
                  (i, code, p['rank'], p['dragon_score'], p['tpl'],
                   p['open_ratio'] * 100, p['close_to_high'], p['auction_ratio'],
                   "PASS" if allok else "FAIL", "" if allok else " <<< " + fails))
    print("\n==== GATE: %d/%d stock-days fully matched ====" % (total_pass, total))


if __name__ == '__main__':
    main()
