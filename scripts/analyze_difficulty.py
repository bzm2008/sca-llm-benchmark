# -*- coding: utf-8 -*-
"""分析 80 题得分率：排除未作答，找出 100% 得分题 + 各维度难度分布"""
import os, json
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "final80_results.jsonl")
QFILE = os.path.join(HERE, "final80_qs.json")
DEAD = {"anthropic/claude-sonnet-4.6", "gpt-4o", "qwen3.8-max"}

# 题面分值 & 维度
def point_of(qid):
    pm = {}
    for q in ['P0'+str(i) for i in range(1,5)]: pm[q]=0.5
    for q in ['P0'+str(i) for i in range(5,10)]: pm[q]=1
    for q in ['P'+str(i) for i in range(10,16)]: pm[q]=1.5
    for q in ['P16','P17','P18']: pm[q]=3
    pm['L01']=0.5; pm['L02']=1; pm['L03']=1; pm['L04']=1.5; pm['L05']=1.5; pm['L06']=3
    pm['W01']=0.5; pm['W02']=1; pm['W03']=1.5; pm['W04']=3
    pm['M01']=1.5; pm['M02']=3; pm['M03']=3; pm['M04']=3
    for i in range(1,6): pm[f'OB-C{i}']=2
    for i in range(1,7): pm[f'OB-K{i}']=4
    for i in range(1,7): pm[f'OB-M{i}']=1
    for i in range(1,8): pm[f'SW{i}']=3
    for i in range(1,5): pm[f'AI{i}']=3
    for i in range(1,8): pm[f'MH{i}']=2
    for i in range(1,9): pm[f'MP{i}']=1
    for i in range(1,6): pm[f'OC{i}']=1
    return pm.get(qid, 1)

def dim_of(qid):
    if qid.startswith("P") or qid.startswith("OB-C") or qid.startswith("SW"): return "编程"
    if qid.startswith("L"): return "Linux系统"
    if qid.startswith("W"): return "写作"
    if qid.startswith("M") or qid.startswith("AI") or qid.startswith("MH"): return "数学推理"
    if qid.startswith("OB-K") or qid.startswith("OB-M") or qid.startswith("MP") or qid.startswith("OC"): return "知识科学"
    return "知识科学"

qdata = json.load(open(QFILE, encoding="utf-8"))
all_qids = [q["qid"] for q in qdata["questions"]]

# 读结果, 去重取最后一条
raw = []
with open(RES, encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: d=json.loads(line)
        except: continue
        if d.get("model") in DEAD or d.get("model")=="1": continue
        raw.append(d)
last = {}
for r in raw:
    last[(r["model"], r["qid"])] = r

# 每题: 已作答模型数 + 平均判分器分(0-100) + 满分(100)比例
qstat = {}
for q in all_qids:
    scores = []
    for (m, qq), r in last.items():
        if qq == q and r.get("status") == "ok":
            scores.append(float(r.get("score") or 0))
    if scores:
        avg = sum(scores)/len(scores)
        full_pct = sum(1 for s in scores if s >= 99.9) / len(scores) * 100
        qstat[q] = {"n": len(scores), "avg": round(avg,1), "full_pct": round(full_pct,1), "pt": point_of(q), "dim": dim_of(q)}
    else:
        qstat[q] = {"n": 0, "avg": 0, "full_pct": 0, "pt": point_of(q), "dim": dim_of(q)}

# 输出: 按维度分组, 每维度内按 full_pct 降序
print("=" * 90)
print(f"{'题号':8} {'维度':8} {'分值':>4} {'作答数':>5} {'均分':>5} {'满分率%':>7}  判定")
print("-" * 90)
for dim in ["编程", "Linux系统", "写作", "数学推理", "知识科学"]:
    print(f"\n--- {dim} ---")
    qs = [q for q in all_qids if dim_of(q)==dim]
    qs.sort(key=lambda q: -qstat[q]["full_pct"])
    for q in qs:
        s = qstat[q]
        tag = "🔴全对(删)" if s["full_pct"] >= 95 and s["n"] >= 10 else ("🟡偏易" if s["full_pct"] >= 70 else ("🟢适中" if s["full_pct"] >= 30 else "⚡偏难"))
        print(f"{q:8} {dim:8} {s['pt']:>4} {s['n']:>5} {s['avg']:>5} {s['full_pct']:>7}  {tag}")

# 维度汇总
print("\n" + "=" * 90)
print("维度汇总（排除未作答）:")
for dim in ["编程", "Linux系统", "写作", "数学推理", "知识科学"]:
    qs = [q for q in all_qids if dim_of(q)==dim]
    full_pcts = [qstat[q]["full_pct"] for q in qs if qstat[q]["n"] > 0]
    avg_of_avg = sum(qstat[q]["avg"] for q in qs if qstat[q]["n"] > 0) / max(1, len([q for q in qs if qstat[q]["n"] > 0]))
    total_pt = sum(point_of(q) for q in qs)
    print(f"  {dim:8}: {len(qs)}题/{total_pt}分 | 平均满分率 {sum(full_pcts)/max(1,len(full_pcts)):.1f}% | 平均判分器分 {avg_of_avg:.1f}")

# 列出建议删除的题（全对 + 简单维度优先）
print("\n" + "=" * 90)
print("建议删除（full_pct>=95 且作答>=10）:")
del_candidates = [q for q in all_qids if qstat[q]["full_pct"] >= 95 and qstat[q]["n"] >= 10]
del_candidates.sort(key=lambda q: (-qstat[q]["full_pct"], dim_of(q)))
total_del_pt = 0
for q in del_candidates:
    s = qstat[q]
    print(f"  {q:8} {s['dim']:8} {s['pt']:>4}分 满分率{s['full_pct']}% (n={s['n']})")
    total_del_pt += s["pt"]
print(f"  合计 {len(del_candidates)} 题 / {total_del_pt} 分")
