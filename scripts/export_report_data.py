# -*- coding: utf-8 -*-
import os, sys, json
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "final80_results.jsonl")
QFILE = os.path.join(HERE, "final80_qs.json")
OUT = os.path.join(HERE, "report_data.json")

data = json.load(open(QFILE, encoding="utf-8"))
all_qids = [q["qid"] for q in data["questions"]]
qmeta = {q["qid"]: q for q in data["questions"]}

recs = []
with open(RES, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            pass

ok_qids = defaultdict(set)
status_by_mq = {}
score_sum = defaultdict(float)
# best score per (model,qid) regardless, plus last status
best_score = defaultdict(float)
for r in recs:
    m = r.get("model"); q = r.get("qid"); st = r.get("status")
    if m == "1" or m == 1:
        continue
    status_by_mq[(m, q)] = st
    if st == "ok":
        ok_qids[m].add(q)
        score_sum[m] += float(r.get("score") or 0)
        best_score[(m, q)] = max(best_score[(m, q)], float(r.get("score") or 0))

# 标准模型清单(手工维护, 含已补的 oc/mimo-v2.5 与重复键归一)
MODELS = ["oc/hy-3", "nvidia/minimax-m3", "nvidia/deepseek-v4-flash-0731", "gpt-4.1",
          "anthropic/claude-sonnet-4.6", "gpt-4o", "gpt-oss-120b", "gemini-3.1-pro-preview",
          "grok-4.6", "grok-chat-fast", "kimi-k3", "oc/mimo-v2.5",
          "nvidia/nemotron-3-ultra-550b-a55b", "qwen3.8-max", "stealth/ox-alpha", "42",
          "kimi-k2.7-code", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek-v4-pro",
          "glm-5.2", "mistral-large-latest"]

# 友好的模型显示名(去前缀/美化)
def pretty(name):
    repl = {
        "nvidia/minimax-m3": "MiniMax-M3",
        "nvidia/deepseek-v4-flash-0731": "DeepSeek-V4-Flash (nvidia)",
        "anthropic/claude-sonnet-4.6": "Claude-Sonnet-4.6",
        "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron-3-Ultra",
        "oc/hy-3": "HY-3",
        "oc/mimo-v2.5": "Mimo-v2.5",
        "gpt-oss-120b": "GPT-OSS-120B",
        "gemini-3.1-pro-preview": "Gemini-3.1-Pro",
        "grok-4.6": "Grok-4.6",
        "grok-chat-fast": "Grok-Chat-Fast",
        "kimi-k2.7-code": "Kimi-K2.7-Code",
        "kimi-k3": "Kimi-K3",
        "deepseek-v4-flash": "DeepSeek-V4-Flash",
        "deepseek-v4-flash-vision-exp": "DeepSeek-V4-Flash-Vision",
        "deepseek-v4-pro": "DeepSeek-V4-Pro",
        "glm-5.2": "GLM-5.2",
        "mistral-large-latest": "Mistral-Large",
        "gpt-4.1": "GPT-4.1",
        "gpt-4o": "GPT-4o",
        "qwen3.8-max": "Qwen3.8-Max",
        "stealth/ox-alpha": "Stealth-OX-Alpha",
        "42": "Muse-Spark (42)",
    }
    return repl.get(name, name)

# 已知问题标记
STALE = {"gpt-4o", "qwen3.8-max"}   # 旧跑垃圾 0 分, 需重跑
BLOCKED = {"kimi-k3": "三通道全死(K1/oc/gpuhome=503, 旧key=401)",
           "oc/hy-3": "de5 坏窗口(模型500 + 裁判503), 无备用通道",
           "oc/mimo-v2.5": "de5 坏窗口中偶发500, 待窗口恢复补 AI3"}

rows = []
for m in MODELS:
    ok = ok_qids.get(m, set())
    n = len(ok)
    tot = round(score_sum.get(m, 0), 1)
    missing = [q for q in all_qids if q not in ok]
    # 题型分布(未完成)
    miss_types = {}
    for q in missing:
        t = qmeta.get(q, {}).get("type", "?")
        miss_types[t] = miss_types.get(t, 0) + 1
    tag = "ok" if n == 80 else ("stale" if m in STALE else ("blocked" if m in BLOCKED else "partial"))
    rows.append({
        "model": m,
        "pretty": pretty(m),
        "ok": n,
        "total": 80,
        "score": tot,
        "missing": missing,
        "miss_types": miss_types,
        "tag": tag,
        "block_reason": BLOCKED.get(m, ""),
    })

rows.sort(key=lambda x: (-x["score"]) if x["tag"] != "stale" else -1)

# 题型总分(用于题型维度图表)
type_sum = defaultdict(float)
type_cnt = defaultdict(int)
for m, q in best_score:
    t = qmeta.get(q, {}).get("type", "?")
    type_sum[t] += best_score[(m, q)]
    type_cnt[t] += 1

# 题型满分参考: 每题满分在 qmeta 中? 用 max observed? 简化用 150 总分维度
out = {
    "generated": True,
    "n_models": len(rows),
    "fully_done": sum(1 for r in rows if r["ok"] == 80),
    "rows": rows,
    "type_summary": {t: round(type_sum[t], 1) for t in type_sum},
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("已导出 report_data.json, 模型数:", len(rows))
print("完全完成 80/80:", out["fully_done"])
for r in rows:
    print(f"  {r['pretty']:20} {r['ok']:>3}/80  {r['score']:>8}  [{r['tag']}]")
