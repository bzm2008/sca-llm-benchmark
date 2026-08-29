# -*- coding: utf-8 -*-
"""生成 V4.2 横评报告 (2026-08-29)
- 数据源: final80_results.jsonl + gemini37_results.jsonl + de5_results/*.jsonl
- 题组: final80_qs.json (70 题 / 150 分)
- 计分: 归一化口径 = 已完成题实得分 / 已完成题满分 × 150 (公平比较残缺模型)
       同时保留原始分(已完成题累加)供参考
- 模型名归一化: MiniMax-M3==minimax-m3, qwen3.8-27b==qwen-3.8-27b
"""
import json, glob, os, html
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "scripts")

def build_point_map():
    p = {}
    for q in ['P0'+str(i) for i in range(1,5)]: p[q]=0.5
    for q in ['P0'+str(i) for i in range(5,10)]: p[q]=1
    for q in ['P'+str(i) for i in range(10,16)]: p[q]=1.5
    for q in ['P16','P17','P18']: p[q]=4
    p['L01']=0.5;p['L02']=1;p['L03']=1;p['L04']=1.5;p['L05']=1.5;p['L06']=5
    p['R01']=0.5;p['R02']=1;p['R03']=1.5;p['R04']=5
    p['M01']=1.5
    for q in ['M02','M03','M04']: p[q]=4
    for i in [1,2,3,5]: p[f'OB-C{i}']=2
    p['OB-K1']=4;p['OB-K2']=4;p['OB-K3']=5;p['OB-K5']=6
    for i in range(1,8): p[f'BK0{i}']=1
    for i in range(1,7): p[f'SW{i}']=4
    p['SW7']=3
    for i in [1,3,4]: p[f'AI{i}']=3
    for i in [1,3,5,6]: p[f'MH{i}']=2
    for i in range(1,4): p[f'BM0{i}']=2
    for i in [2,3,4,5,6,7]: p[f'MP{i}']=1
    return p

P = build_point_map()
QD = json.load(open(os.path.join(SCR,"final80_qs.json"),encoding="utf-8"))
QS = QD["questions"] if isinstance(QD,dict) else QD
ALLQ = [q["qid"] for q in QS]
assert len(ALLQ)==70, f"题组应为70题, 实际{len(ALLQ)}"

NORM = {
    "MiniMax-M3": "minimax-m3",
    "minimax-m3": "minimax-m3",
    "qwen3.8-27b": "qwen-3.8-27b",
    "qwen-3.8-27b": "qwen-3.8-27b",
}
def norm_name(m): return NORM.get(m, m)

last = {}
files = [os.path.join(SCR,"final80_results.jsonl"), os.path.join(SCR,"gemini37_results.jsonl")] + sorted(glob.glob(os.path.join(SCR,"de5_results","*.jsonl")))
for f in files:
    for l in open(f,encoding="utf-8"):
        l=l.strip()
        if not l: continue
        try: r=json.loads(l)
        except: continue
        m=norm_name(r.get("model")); q=r.get("qid")
        if m and q: last[(m,q)]=r

# 聚合
ok_pts=defaultdict(float); ok_max=defaultdict(float); ok_cnt=defaultdict(int)
for (m,q),r in last.items():
    if r.get("status")=="ok" and q in P:
        pt=P[q]
        ok_pts[m]+=float(r.get("score") or 0)/100.0*pt
        ok_max[m]+=pt
        ok_cnt[m]+=1

rows=[]
for m in ok_cnt:
    if ok_cnt[m] < 50:   # 完成度过低(缺题>20)不纳入主排名, 避免失真
        continue
    raw=ok_pts[m]
    norm = raw/ok_max[m]*150 if ok_max[m]>0 else 0
    rows.append({"model":m,"ok":ok_cnt[m],"raw":round(raw,1),"norm":round(norm,1),"full":ok_cnt[m]==70})
rows.sort(key=lambda x:-x["raw"])  # 主排名用原始分(缺题记0,保守估计)

print(f"V4.2 纳入模型数: {len(rows)} (完整70题: {sum(1 for r in rows if r['full'])})\n")
print(f"{'#':<3}{'模型':<40}{'ok':>4} {'原始/150':>9} {'归一化/150':>10}")
for i,r in enumerate(rows,1):
    tag="✅" if r["full"] else f"{r['ok']}题"
    print(f"  {i:<3}{r['model']:<40}{tag:>5} {r['raw']:>8.1f} {r['norm']:>9.1f}")

# 写 JSON
out={"generated":"2026-08-29","n_models":len(rows),"models":rows}
json.dump(out, open(os.path.join(HERE,"v42_summary.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)

# HTML
def bar(v,mx=150,w=200):
    pct=max(0,min(100,v/mx*100))
    return f'<div style="background:#e9ecef;border-radius:4px;width:{w}px;height:14px;display:inline-block;vertical-align:middle"><div style="background:#31C476;height:14px;border-radius:4px;width:{pct* w/100:.0f}px"></div></div>'
rows_html=""
for i,r in enumerate(rows,1):
    color = "#00453E" if r["full"] else "#b8860b"
    badge = "完整" if r["full"] else f"缺{70-r['ok']}题"
    rows_html+=f"""<tr>
<td>{i}</td><td style="color:{color};font-weight:600">{html.escape(r['model'])}</td>
<td>{r['ok']}/70</td><td>{badge}</td>
<td>{r['raw']:.1f}</td><td>{bar(r['raw'])}</td><td>{r['norm']:.1f}</td></tr>"""

html_doc=f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM 中转站横评 V4.2</title>
<style>
body{{font-family:-apple-system,'Segoe UI',sans-serif;max-width:960px;margin:40px auto;padding:0 20px;color:#222;background:#fafafa}}
h1{{color:#00453E}} .sub{{color:#666;margin-bottom:24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #eee;font-size:14px}}
th{{background:#00453E;color:#fff}}
tr:hover{{background:#f5f9f7}}
.note{{background:#fff;border-left:4px solid #31C476;padding:12px 16px;margin:20px 0;border-radius:4px}}
</style></head><body>
<h1>LLM 中转站能力横评 · V4.2</h1>
<div class="sub">题组 70 题 / 150 分 · 生成于 2026-08-29 · 主排名用原始分(缺题记0,保守)</div>
<div class="note">
<b>计分说明</b>：主排名列"原始/150" = 已完成题实得分累加（未完成题记 0，故分数偏保守）。
标注"缺N题"的模型在对应题上未取得有效成绩（通道空响应/裁判失败），其真实能力可能高于显示值，仅供参考。
"归一化/150"列为辅助参考（已完成题加权推算），但因残缺题非随机子集，可能高估，不作为主排名。
M 类主观题(13.5分)裁判：V4.1 模型用 deepseek-v4-flash(gpuhome)；gemini/glm 用 deepseek-v4-flash(de5)；de5 批次用 gpt-oss-20b（de5 的 deepseek 裁判 8-29 起返回空，已换）。
</div>
<table><thead><tr><th>#</th><th>模型</th><th>完成</th><th>状态</th><th>原始/150</th><th></th><th>归一化/150</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<p style="color:#999;font-size:12px;margin-top:24px">完整70题模型 {sum(1 for r in rows if r['full'])} 个；共纳入 {len(rows)} 个模型（完成度≥50题）。</p>
</body></html>"""
open(os.path.join(HERE,"capability_report_v42.html"),"w",encoding="utf-8").write(html_doc)
print("\n报告已生成: capability_report_v42.html")
