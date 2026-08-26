# -*- coding: utf-8 -*-
import os, sys, json
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "final80_results.jsonl")
QFILE = os.path.join(HERE, "final80_qs.json")

data = json.load(open(QFILE, encoding="utf-8"))
all_qids = [q["qid"] for q in data["questions"]]
TOTAL = len(all_qids)  # V2: 70

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
qset = set(all_qids)  # V2: 只统计题库内的题(排除已删题/旧记录)
for r in recs:
    m = r.get("model"); q = r.get("qid"); st = r.get("status")
    if q not in qset:
        continue
    status_by_mq[(m, q)] = st
    if st == "ok":
        ok_qids[m].add(q)
        score_sum[m] += float(r.get("score") or 0)

# 标准模型清单(按 ALL_MODELS + 已补的 oc/mimo-v2.5)
MODELS = ["oc/hy-3", "nvidia/minimax-m3", "nvidia/deepseek-v4-flash-0731", "gpt-4.1",
          "anthropic/claude-sonnet-4.6", "gpt-4o", "gpt-oss-120b", "gemini-3.1-pro-preview",
          "grok-4.6", "grok-chat-fast", "kimi-k3", "oc/mimo-v2.5",
          "nvidia/nemotron-3-ultra-550b-a55b", "qwen3.8-max", "stealth/ox-alpha", "42",
          "kimi-k2.7-code", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek-v4-pro",
          "glm-5.2", "mistral-large-latest", "nvidia/deepseek-v4-flash-0731"]

print(f"{'MODEL':28} {'OK':>4}/{TOTAL}  {'总分':>8}  {'未完成'}")
print("-" * 90)
rows = []
for m in MODELS:
    ok = ok_qids.get(m, set())
    n = len(ok)
    tot = round(score_sum.get(m, 0), 1)
    missing = [q for q in all_qids if q not in ok]
    rows.append((m, n, tot, missing))
rows.sort(key=lambda x: -x[2])
for m, n, tot, missing in rows:
    miss = ",".join(missing) if missing else "—"
    print(f"{m:28} {n:>4}/{TOTAL}  {tot:>8}  {miss}")
print("-" * 90)

# 汇总整体完成度
fully = [m for m, n, tot, miss in rows if n == TOTAL]
print(f"完全完成({TOTAL}/{TOTAL})的模型数: {len(fully)} / {len(rows)}")
