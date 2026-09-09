# -*- coding: utf-8 -*-
"""Project1 Paper — mock 端到端演习(证明 Step2-4 全链路接得上)。

在隔离的 paper_state_drill/ 里,对一段历史日逐日跑完整三段:
  盘前(mock AI 决策)→ 盘中(回放bar喂实时监测器+三组买入)→ 盘后(重放引擎结算)
每步都走真实 CLI(subprocess),与实际运营完全同路径。

⚠️ 护栏2:演习用 --ai mock(机械规则占位),绝不是真 MiniMax 选历史票;
   演习结果只证明"管线通",无任何选股价值含义。
用法: py -3.10 run_mock_e2e.py [--start 20231204 --end 20231213] [--fresh]
"""
import os
import sys
import shutil
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASEA = os.path.normpath(os.path.join(_HERE, '..', 'project1_phaseA'))
for p in (_HERE, _PHASEA):
    if p not in sys.path:
        sys.path.insert(0, p)
import paper_config as C    # noqa: E402


def sh(script, *args):
    cmd = ["py", "-3.10", os.path.join(_HERE, script)] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    tail = (r.stdout or "").strip().splitlines()
    for ln in tail[-4:]:
        print("    " + ln)
    if r.returncode != 0:
        print("    STDERR: " + (r.stderr or "")[-500:])
        raise SystemExit("步骤失败: %s" % " ".join(cmd))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20231204")
    ap.add_argument("--end", default="20231213")
    ap.add_argument("--fresh", action="store_true", help="清空演习state重来")
    args = ap.parse_args()

    if args.fresh and os.path.isdir(C.DRILL_STATE_DIR):
        shutil.rmtree(C.DRILL_STATE_DIR)     # 只删演习目录(本项目自建),不碰真实state

    import pool_repro as PR
    PR._load()
    days = [d for d in PR.trade_days() if args.start <= d <= args.end]
    print("[e2e] 演习 %d 个交易日 (%s..%s),state=drill,AI=mock" % (
        len(days), days[0], days[-1]))
    for d in days:
        print("== %s ==" % d)
        print("  [1/3] morning (mock AI)")
        sh("run_paper_morning.py", "--mode", "drill", "--d8", d, "--ai", "mock", "--state", "drill")
        print("  [2/3] intraday (replay->monitor->buy)")
        sh("run_paper_intraday.py", "--mode", "drill", "--d8", d, "--state", "drill")
        print("  [3/3] settle (replay engine)")
        sh("run_paper_settle.py", "--mode", "drill", "--d8", d, "--state", "drill")
    print("\n[e2e] 演习完成。产物: %s" % C.DRILL_STATE_DIR)
    print("      看板切到 src=drill 可视化本演习(标注:演习数据,无价值含义)")


if __name__ == "__main__":
    main()
