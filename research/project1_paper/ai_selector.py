# -*- coding: utf-8 -*-
"""Project1 Paper — MiniMax 选股器(spec §2.1/§3;§9.3 纯MiniMax单AI)。

⚠️ 护栏2(两种"历史"分清,违者返工):
  ✅ 喂"每只候选票的历史表现"(快照字段)当选股依据 —— 合法,spec §3.1 本来就有。
  ❌ 严禁把"历史某天"当"今天"让真 MiniMax 选那天的票(验证/演习都不行)——
     LLM 权重已知历史结果会背答案,同 dragon_score"回测361%/实盘-5%"病。
  → 代码级强制:mode='real' 时 assert 目标日期 == 今天(见 select());
     历史日期只允许 mode='mock'(机械规则占位,只为验管线,非AI)。

异常处理(spec §3.4):超时/无返回/JSON错/字段异常 → 当日 AI 组空仓不参与,
不 fallback 成全进或随机(否则污染对照)。完整留痕(输入/输出/时戳/模型版本)。

真实调用测试 = 周一清单项(需 MINIMAX_API_KEY 环境变量,今日未配)。
"""
import os
import sys
import json
import time
import datetime as dt

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import paper_config as C   # noqa: E402

SYSTEM_PROMPT = (
    "你是A股短线打板选股助手。给你今日候选池(战车A龙头候选,已按体系打分排序)每只票的"
    "盘前信息(昨日表现/近期涨停结构/今日集合竞价),从中选出最多3只【今天最值得进入"
    "'等确认买入'监测池】的票。注意:你只做盘前选择,买入确认由日内机械闸(VWAP站稳)负责,"
    "你不需要判断日内走势。部分字段为null表示数据源未接(行业/题材/封单/市值/新闻),"
    "请基于现有字段判断,不要臆造缺失信息。"
    "只输出JSON(不要任何其他文字),格式:"
    '{"picks":[{"code":"XXXXXX.SZ","name":"...","confidence":0.0到1.0,'
    '"weight_suggest":0.0到1.0,"reason":"简短理由"}],'
    '"rejected":[{"code":"...","reason":"..."}],"market_note":"一句话盘面判断"}'
    " 要求:picks最多3只且只能来自候选列表;若认为今天都不值得选,picks可以为空数组并在"
    "market_note说明。")


def build_prompt(d8, snapshots):
    lines = ["今日日期:%s(盘前决策,9:25竞价已出)" % d8,
             "候选池(%d只,按dragon_score降序):" % len(snapshots)]
    for i, s in enumerate(snapshots):
        lines.append("%d. %s" % (i + 1, json.dumps(s, ensure_ascii=False)))
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# MiniMax 真实调用(OpenAI兼容 chatcompletion_v2;密钥只读环境变量)
# ----------------------------------------------------------------------------
def call_minimax(prompt):
    """返回 (content_str, meta dict)。失败抛异常(上层按 §3.4 空仓)。"""
    import requests
    key = os.environ.get(C.MINIMAX_KEY_ENV)
    if not key:
        raise RuntimeError("缺 %s 环境变量(真实调用测试=周一清单项)" % C.MINIMAX_KEY_ENV)
    t0 = time.time()
    resp = requests.post(
        C.MINIMAX_API_URL,
        headers={"Authorization": "Bearer %s" % key, "Content-Type": "application/json"},
        json=dict(model=C.MINIMAX_MODEL, temperature=0.2,
                  messages=[{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}]),
        timeout=C.AI_TIMEOUT_SEC)
    resp.raise_for_status()
    data = resp.json()
    base = data.get('base_resp') or {}
    if base.get('status_code') not in (0, None):
        raise RuntimeError("minimax base_resp=%s" % base)
    content = data['choices'][0]['message']['content']
    meta = dict(model=C.MINIMAX_MODEL, latency_sec=round(time.time() - t0, 2),
                usage=data.get('usage'))
    return content, meta


# ----------------------------------------------------------------------------
# mock(机械规则占位,只为验管线;不是AI,结果无选股价值含义)
# ----------------------------------------------------------------------------
def mock_select(snapshots):
    """规则:竞价温和高开(0~+4%)优先,按|open_ratio-2%|升序取3。走与真AI相同的JSON路径。"""
    ranked = sorted(snapshots, key=lambda s: abs((s['auction_open_ratio_pct'] or 0) - 2.0))
    picks = [dict(code=s['code'], name=s['name'], confidence=0.5, weight_suggest=0.25,
                  reason="MOCK规则:竞价温和高开(管线演习,非AI判断)") for s in ranked[:C.N_PICK]]
    rej = [dict(code=s['code'], reason="MOCK未选") for s in ranked[C.N_PICK:]]
    return json.dumps(dict(picks=picks, rejected=rej,
                           market_note="MOCK演习输出,无盘面判断"), ensure_ascii=False)


# ----------------------------------------------------------------------------
# 校验 + 统一入口
# ----------------------------------------------------------------------------
def validate(content, pool_codes):
    """返回 (ok, picks list, err)。任何不合规 → ok=False(AI组当日空仓)。"""
    try:
        txt = content.strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            if txt.startswith("json"):
                txt = txt[4:]
        obj = json.loads(txt)
        picks = obj.get('picks', [])
        if not isinstance(picks, list) or len(picks) > C.N_PICK:
            return False, [], "picks数量非法(%s)" % len(picks)
        seen = set()
        for pk in picks:
            code = pk.get('code')
            if code not in pool_codes:
                return False, [], "pick不在候选池: %s" % code
            if code in seen:
                return False, [], "pick重复: %s" % code
            seen.add(code)
            conf = pk.get('confidence')
            if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                return False, [], "confidence非法: %s" % conf
        return True, picks, None
    except Exception as ex:
        return False, [], "JSON解析失败: %r" % ex


def select(d8, snapshots, mode, log_dir):
    """统一入口。mode: 'real'(仅限今天,护栏2代码级强制)/ 'mock' / 'off'。
    返回 dict(ok, picks, market_note, model_version, error)。全程留痕到 log_dir/<d8>_*。"""
    os.makedirs(log_dir, exist_ok=True)
    today = dt.datetime.now().strftime("%Y%m%d")
    if mode == 'real':
        assert d8 == today, (
            "护栏2违规拦截:mode=real 只允许今天(%s),收到 %s。"
            "真MiniMax绝不回历史日期选股(LLM会背答案→虚高)。" % (today, d8))
    if mode == 'off':
        return dict(ok=False, picks=[], market_note=None,
                    model_version='off', error='ai_off')

    prompt = build_prompt(d8, snapshots)
    with open(os.path.join(log_dir, "%s_prompt.txt" % d8), "w", encoding="utf-8") as f:
        f.write(SYSTEM_PROMPT + "\n\n---\n\n" + prompt)
    model_version = 'MOCK-rule-v1' if mode == 'mock' else C.MINIMAX_MODEL
    meta = dict(mode=mode, model_version=model_version,
                ts=dt.datetime.now().isoformat(timespec='seconds'))
    try:
        if mode == 'mock':
            content = mock_select(snapshots)
        else:
            content, call_meta = call_minimax(prompt)
            meta.update(call_meta)
    except Exception as ex:
        meta['error'] = repr(ex)
        _dump(log_dir, d8, meta, raw=None, parsed=None)
        return dict(ok=False, picks=[], market_note=None,
                    model_version=model_version, error=repr(ex))
    ok, picks, err = validate(content, {s['code'] for s in snapshots})
    meta['validate_ok'] = ok
    if err:
        meta['error'] = err
    _dump(log_dir, d8, meta, raw=content,
          parsed=dict(picks=picks) if ok else None)
    if not ok:
        return dict(ok=False, picks=[], market_note=None,
                    model_version=model_version, error=err)
    note = None
    try:
        note = json.loads(content.strip().strip('`').lstrip('json')).get('market_note')
    except Exception:
        pass
    return dict(ok=True, picks=picks, market_note=note,
                model_version=model_version, error=None)


def _dump(log_dir, d8, meta, raw, parsed):
    with open(os.path.join(log_dir, "%s_meta.json" % d8), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    if raw is not None:
        with open(os.path.join(log_dir, "%s_raw_response.txt" % d8), "w", encoding="utf-8") as f:
            f.write(raw)
    if parsed is not None:
        with open(os.path.join(log_dir, "%s_parsed.json" % d8), "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=1)
