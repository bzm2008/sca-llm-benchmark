# -*- coding: utf-8 -*-
"""
按 relay-capability-test skill 规范生成自包含 HTML 报告。
- 实际得分 = 判分器分(0-100)/100 × 题面分值，满分 150（非 jsonl score 原值累加）
- 排除 skill 认定的死模型: anthropic/claude-sonnet-4.6, gpt-4o, qwen3.8-max
- 含: 综合排名(150制) / 逐题热力图 / 维度分组柱状图 / 各模型雷达图 / 优缺点总结 / 耗时与报错对比 / 时间性价比
"""
import os, json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "final80_results.jsonl")
QFILE = os.path.join(HERE, "final80_qs.json")
OUT = os.path.join(HERE, "capability_report_final.html")

DEAD = {"anthropic/claude-sonnet-4.6", "gpt-4o", "qwen3.8-max"}

# ---------- 题面分值 & 维度映射 ----------
def build_point_map():
    """70 题 / 150 分 V2 分值映射（删 10 道简单题 + 超难题加权）。"""
    pm = {}
    for q in ['P0'+str(i) for i in range(1,5)]: pm[q]=0.5
    for q in ['P0'+str(i) for i in range(5,10)]: pm[q]=1
    for q in ['P'+str(i) for i in range(10,16)]: pm[q]=1.5
    for q in ['P16','P17','P18']: pm[q]=4          # 超难加权 3→4
    pm['L01']=0.5; pm['L02']=1; pm['L03']=1; pm['L04']=1.5; pm['L05']=1.5
    pm['L06']=5                                     # 超难加权 3→5
    pm['W01']=0.5; pm['W02']=1; pm['W03']=1.5
    pm['W04']=5                                     # 超难加权 3→5
    pm['M01']=1.5
    for q in ['M02','M03','M04']: pm[q]=4           # 超难加权 3→4
    # HumanEval: 删 OB-C4, 剩 4 题各 2 分
    for i in [1,2,3,5]: pm[f'OB-C{i}']=2            # OB-C4 已删
    # GPQA: 删 OB-K4/K6, K3→5 K5→6 其余 4 分
    pm['OB-K1']=4; pm['OB-K2']=4; pm['OB-K3']=5; pm['OB-K5']=6  # K4/K6 已删
    # MMLU: 删 OB-M1/M3/M6, 剩 M2/M4/M5 各 1 分
    for i in [2,4,5]: pm[f'OB-M{i}']=1              # M1/M3/M6 已删
    # SWE-bench: SW1-6 加权 3→4, SW7 保持 3
    for i in range(1,7): pm[f'SW{i}']=4             # SW1-6 各 4
    pm['SW7']=3                                     # SW7 保持 3
    # AIME: 删 AI2, 剩各 3 分
    for i in [1,3,4]: pm[f'AI{i}']=3                # AI2 已删
    # MATH-500: 不变, 各 2 分
    for i in range(1,8): pm[f'MH{i}']=2
    # MMLU-Pro: 删 MP1/MP8, 剩各 1 分
    for i in [2,3,4,5,6,7]: pm[f'MP{i}']=1          # MP1/MP8 已删
    # OpenCompass: 删 OC3, 剩各 1 分
    for i in [1,2,4,5]: pm[f'OC{i}']=1              # OC3 已删
    return pm

POINT = build_point_map()
DIMS = ["编程", "Linux系统", "写作", "数学推理", "知识科学"]
DIM_COLOR = {"编程":"#31C476","Linux系统":"#7CE0A8","写作":"#F5C518","数学推理":"#4FC3F7","知识科学":"#B388FF"}

def dim_of(qid):
    if qid.startswith("P") or qid.startswith("OB-C") or qid.startswith("SW"): return "编程"
    if qid.startswith("L"): return "Linux系统"
    if qid.startswith("W"): return "写作"
    # 注意: MP 以 M 开头, 必须在 M 之前判断, 否则被误归数学推理
    if qid.startswith("OB-K") or qid.startswith("OB-M") or qid.startswith("MP") or qid.startswith("OC"): return "知识科学"
    if qid.startswith("M") or qid.startswith("AI") or qid.startswith("MH"): return "数学推理"
    return "知识科学"

# 维度满分
DIM_MAX = defaultdict(float)
for q,p in POINT.items():
    DIM_MAX[dim_of(q)] += p

# ---------- 读取结果 ----------
qdata = json.load(open(QFILE, encoding="utf-8"))
all_qids = [q["qid"] for q in qdata["questions"]]

raw = []
with open(RES, encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: rec=json.loads(line)
        except: continue
        m=rec.get("model")
        if m in DEAD or m=="1" or m==1: continue
        raw.append(rec)

# 去重: (model,qid) 取最后一条
last = {}
for r in raw:
    last[(r["model"], r["qid"])] = r

models = sorted({m for (m,_) in last})
# 友好名
PRETTY = {
    "nvidia/minimax-m3":"MiniMax-M3","nvidia/deepseek-v4-flash-0731":"DeepSeek-V4-Flash(nvidia)",
    "oc/hy-3":"HY-3","oc/mimo-v2.5":"Mimo-v2.5","gpt-oss-120b":"GPT-OSS-120B",
    "gemini-3.1-pro-preview":"Gemini-3.1-Pro","grok-4.6":"Grok-4.6","grok-chat-fast":"Grok-Chat-Fast",
    "kimi-k3":"Kimi-K3","kimi-k2.7-code":"Kimi-K2.7-Code","nvidia/nemotron-3-ultra-550b-a55b":"Nemotron-3-Ultra",
    "stealth/ox-alpha":"Stealth-OX-Alpha","42":"Muse-Spark(42)","deepseek-v4-flash":"DeepSeek-V4-Flash",
    "deepseek-v4-pro":"DeepSeek-V4-Pro","deepseek-v4-flash-vision-exp":"DeepSeek-V4-Flash-Vision",
    "glm-5.2":"GLM-5.2","mistral-large-latest":"Mistral-Large","gpt-4.1":"GPT-4.1",
}
def pretty(m): return PRETTY.get(m, m)

# ---------- 聚合 ----------
agg = {}
for m in models:
    agg[m] = {"ok":0,"total":80,"score_sum":0.0,"dim_score":defaultdict(float),
              "elapsed_ok":[],"ttft_ok":[],"errors":defaultdict(int),
              "q":{}}
    for q in all_qids:
        r = last.get((m,q))
        if r is None:
            agg[m]["q"][q] = None
            continue
        st = r.get("status")
        judge = float(r.get("score") or 0)
        pt = POINT.get(q, 1)
        if st == "ok":
            actual = judge/100.0 * pt
            agg[m]["score_sum"] += actual
            agg[m]["ok"] += 1
            agg[m]["dim_score"][dim_of(q)] += actual
            if r.get("elapsed") is not None: agg[m]["elapsed_ok"].append(float(r["elapsed"]))
            if r.get("ttft") is not None: agg[m]["ttft_ok"].append(float(r["ttft"]))
            agg[m]["q"][q] = judge
        else:
            agg[m]["errors"][st] += 1
            agg[m]["q"][q] = None  # 未完成

# 补全总分(150制); 维度归一%
for m in models:
    a = agg[m]
    a["total_score"] = round(a["score_sum"], 2)
    a["pct"] = round(100.0*a["ok"]/80, 1)
    a["dim_norm"] = {d: (round(100.0*a["dim_score"].get(d,0)/DIM_MAX[d],1) if DIM_MAX[d] else 0) for d in DIMS}
    a["avg_time"] = round(sum(a["elapsed_ok"])/len(a["elapsed_ok"]),1) if a["elapsed_ok"] else 0
    a["avg_ttft"] = round(sum(a["ttft_ok"])/len(a["ttft_ok"]),1) if a["ttft_ok"] else 0
    a["total_time"] = round(sum(a["elapsed_ok"]),1)
    a["err_total"] = sum(a["errors"].values())
    # 性价比指数 = 加权总分(150) / 总耗时(秒) × 100
    a["cpi"] = round(a["total_score"]/a["total_time"]*100, 2) if a["total_time"] else 0

ranked = sorted(models, key=lambda m: -agg[m]["total_score"])
for i,m in enumerate(ranked,1):
    agg[m]["rank"]=i

max_total = max(agg[m]["total_score"] for m in models) or 1

# ---------- 优缺点文字 ----------
def pros_cons(m):
    a=agg[m]
    dn=a["dim_norm"]
    best=max(dn, key=dn.get); worst=min(dn, key=dn.get)
    scen={"编程":"后端/算法/自动化 coding","Linux系统":"运维排障/系统脚本","写作":"文档/通报/决策纪要",
          "数学推理":"竞赛数学/严谨推导","知识科学":"知识问答/学科推理"}
    parts=[]
    parts.append(f"强项聚焦<b style='color:{DIM_COLOR[best]}'>{best}</b>（{dn[best]}%），"
                 f"弱项在<b style='color:#FF8A4C'>{worst}</b>（{dn[worst]}%）。")
    if a["ok"]==80:
        parts.append(f"80/80 全量完成，平均单题 {a['avg_time']}s、TTFT {a['avg_ttft']}s，报错 {a['err_total']} 次。")
    else:
        parts.append(f"仅 {a['ok']}/80 完成（{a['pct']}%），剩余 {80-a['ok']} 题因通道不可用未作答，分数未含缺失项，偏低属预期。")
    parts.append(f"适用场景：{scen.get(best,'综合任务')}。")
    return " ".join(parts)

# ---------- SVG 工具 ----------
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def rank_bars():
    W=860; rowh=26; top=10; H=top+len(ranked)*rowh+10
    svg=[f'<svg viewBox="0 0 {W} {H}" class="chart" preserveAspectRatio="xMinYMin meet">']
    maxv=max_total
    for i,m in enumerate(ranked):
        y=top+i*rowh
        a=agg[m]
        w=max(2, a["total_score"]/maxv*(W-220))
        col="#31C476" if a["ok"]==80 else ("#F5C518" if a["pct"]>=90 else "#FF8A4C")
        svg.append(f'<text x="6" y="{y+rowh/2+4}" class="bl">{i+1}. {esc(pretty(m))}</text>')
        svg.append(f'<rect x="180" y="{y+4}" width="{w}" height="{rowh-10}" rx="5" fill="{col}"/>')
        svg.append(f'<text x="{180+w+6}" y="{y+rowh/2+4}" class="bv">{a["total_score"]:.1f}</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def group_bar():
    # 维度分组柱状图: x=维度, 每组内各模型一根柱(归一% ), 为可读只画 Top12
    topm = ranked[:12]
    nd=len(DIMS); nm=len(topm)
    W=900; H=340; padL=40; padB=60; padT=20
    bw=14; gap=6
    groupw=nm*bw+(nm-1)*gap
    step=(W-padL-20)/nd
    svg=[f'<svg viewBox="0 0 {W} {H}" class="chart">']
    # y 轴网格
    for g in range(0,101,20):
        y=padT+(100-g)/100*(H-padT-padB)
        svg.append(f'<line x1="{padL}" y1="{y}" x2="{W-10}" y2="{y}" stroke="rgba(255,255,255,.08)"/>')
        svg.append(f'<text x="{padL-6}" y="{y+4}" class="ax" text-anchor="end">{g}</text>')
    for di,d in enumerate(DIMS):
        gx=padL+di*step+(step-groupw)/2
        for mi,m in enumerate(topm):
            x=gx+mi*(bw+gap)
            v=agg[m]["dim_norm"][d]
            h=v/100*(H-padT-padB)
            y=padT+(H-padT-padB)-h
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{h:.1f}" rx="2" fill="{DIM_COLOR[d]}" opacity="0.85"><title>{esc(pretty(m))} · {d}: {v}%</title></rect>')
        # x label
        cx=padL+di*step+step/2
        svg.append(f'<text x="{cx}" y="{H-padB+18}" class="ax" text-anchor="middle">{d}</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def radar(m, size=150):
    a=agg[m]; cx=size/2; cy=size/2; R=size/2-22
    N=len(DIMS); step=2*3.14159/N
    pts=[]
    for i,d in enumerate(DIMS):
        ang=-3.14159/2+i*step
        v=a["dim_norm"][d]/100.0
        x=cx+R*v*__import__("math").cos(ang); y=cy+R*v*__import__("math").sin(ang)
        pts.append((x,y))
    poly=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    rings=""
    for rr in (0.25,0.5,0.75,1.0):
        rp=[]
        for i,d in enumerate(DIMS):
            ang=-3.14159/2+i*step
            x=cx+R*rr*__import__("math").cos(ang); y=cy+R*rr*__import__("math").sin(ang)
            rp.append(f"{x:.1f},{y:.1f}")
        rings+=f'<polygon points="{" ".join(rp)}" fill="none" stroke="rgba(255,255,255,.08)"/>'
    axes=""
    labels=""
    for i,d in enumerate(DIMS):
        ang=-3.14159/2+i*step
        x2=cx+R*__import__("math").cos(ang); y2=cy+R*__import__("math").sin(ang)
        axes+=f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255,255,255,.1)"/>'
        lx=cx+(R+12)*__import__("math").cos(ang); ly=cy+(R+12)*__import__("math").sin(ang)
        labels+=f'<text x="{lx:.1f}" y="{ly:.1f}" class="rl" text-anchor="middle">{d}</text>'
    fillcol="#31C476" if a["ok"]==80 else ("#F5C518" if a["pct"]>=90 else "#FF8A4C")
    return f'''<svg viewBox="0 0 {size} {size}" class="radar">
      {rings}{axes}
      <polygon points="{poly}" fill="{fillcol}33" stroke="{fillcol}" stroke-width="1.6"/>
      {labels}
      <text x="{cx}" y="{size-4}" class="rc" text-anchor="middle">{esc(pretty(m))} · {a["total_score"]:.1f}</text>
    </svg>'''

def heatmap():
    # 模型 × 80 题, 颜色按判分器分(0-100)
    cells=[]
    cells.append('<div class="hm-head"><div class="hm-name">模型</div><div class="hm-grid">')
    for q in all_qids:
        cells.append(f'<div class="hm-col" title="{q}">{q}</div>')
    cells.append('</div></div>')
    for m in ranked:
        a=agg[m]
        cells.append(f'<div class="hm-row"><div class="hm-name" title="{esc(pretty(m))}">{esc(pretty(m))}</div><div class="hm-grid">')
        for q in all_qids:
            jv=a["q"].get(q)
            if jv is None:
                cells.append(f'<div class="hm-cell na" title="{esc(pretty(m))} {q}: 未完成"></div>')
            else:
                # 绿阶
                g=int(40+jv*1.6)
                cells.append(f'<div class="hm-cell" style="background:rgb({int(20+jv*0.1)},{g},{int(80+jv*0.6)});opacity:{0.35+0.6*jv/100:.2f}" title="{esc(pretty(m))} {q}: {jv:.0f}分"></div>')
        cells.append('</div></div>')
    return "\n".join(cells)

# ---------- 拼装 HTML ----------
CSS = """
:root{--bg:#00453E;--bg2:#06352F;--glass:rgba(255,255,255,.06);--border:rgba(255,255,255,.14);
--text:#D9DBD6;--muted:#9FB3AD;--green:#31C476;--green2:#7CE0A8;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;
background:radial-gradient(1200px 700px at 15% -10%,#0a5a4f 0%,var(--bg) 45%,var(--bg2) 100%);
color:var(--text);min-height:100vh;padding:32px 20px 70px;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1120px;margin:0 auto;}
header{margin-bottom:22px;}
h1{font-size:27px;font-weight:800;letter-spacing:.5px;} h1 .accent{color:var(--green);}
.sub{color:var(--muted);font-size:13px;margin-top:6px;}
section{margin-top:30px;}
h2{font-size:19px;font-weight:800;margin-bottom:12px;padding-left:11px;border-left:4px solid var(--green);}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 4px;}
.card{background:var(--glass);border:1px solid var(--border);border-radius:18px;padding:16px;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:0 8px 30px rgba(0,0,0,.18);}
.card-label{font-size:12px;color:var(--muted);} .card-value{font-size:28px;font-weight:800;margin:5px 0 2px;} .card-sub{font-size:11px;color:var(--muted);}
.chart{width:100%;height:auto;background:var(--glass);border:1px solid var(--border);border-radius:16px;padding:12px;backdrop-filter:blur(10px);}
.bl{font-size:12px;fill:var(--text);} .bv{font-size:11px;fill:#fff;font-weight:700;} .ax{font-size:10px;fill:var(--muted);} .rl{font-size:8.5px;fill:var(--muted);} .rc{font-size:9px;fill:var(--text);font-weight:700;}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:10px 2px;}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px;vertical-align:-1px;}
.radar-wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-top:8px;}
.radar-wall .radar{background:var(--glass);border:1px solid var(--border);border-radius:14px;padding:6px;width:100%;height:auto;}
.pc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;margin-top:8px;}
.pc{background:var(--glass);border:1px solid var(--border);border-radius:16px;padding:14px 16px;backdrop-filter:blur(10px);}
.pc h3{font-size:14.5px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;}
.pc .tag{font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;}
.pc p{font-size:12.5px;color:var(--text);line-height:1.65;margin-top:6px;}
.pc .mini{font-size:11px;color:var(--muted);margin-top:7px;display:flex;gap:14px;flex-wrap:wrap;}
.tbl{width:100%;border-collapse:collapse;background:var(--glass);border:1px solid var(--border);border-radius:16px;overflow:hidden;font-size:12.5px;margin-top:8px;}
.tbl th,.tbl td{padding:9px 12px;text-align:left;border-bottom:1px solid rgba(255,255,255,.07);}
.tbl th{background:rgba(255,255,255,.05);color:var(--green2);font-weight:700;position:sticky;top:0;}
.tbl tr:hover td{background:rgba(255,255,255,.04);}
.num{font-weight:700;}
.hm{overflow-x:auto;background:var(--glass);border:1px solid var(--border);border-radius:16px;padding:12px;margin-top:8px;}
.hm-head,.hm-row{display:flex;align-items:center;}
.hm-name{width:130px;flex:0 0 130px;font-size:11.5px;font-weight:700;color:var(--text);padding-right:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hm-grid{display:grid;grid-template-columns:repeat(80,14px);gap:2px;}
.hm-col{width:14px;font-size:7px;color:var(--muted);text-align:center;transform:rotate(0deg);writing-mode:vertical-rl;text-orientation:upright;height:60px;line-height:1;}
.hm-cell{width:14px;height:14px;border-radius:2px;}
.hm-cell.na{background:repeating-linear-gradient(45deg,rgba(255,255,255,.05),rgba(255,255,255,.05) 3px,rgba(255,255,255,.12) 3px,rgba(255,255,255,.12) 6px);}
footer{margin-top:26px;font-size:12px;color:var(--muted);line-height:1.8;}
footer b{color:var(--green2);}
@media(max-width:760px){.cards{grid-template-columns:repeat(2,1fr);}.hm-name{width:90px;flex-basis:90px;}}
"""

# 汇总卡
completed=sum(1 for m in models if agg[m]["ok"]==80)
avg_score=round(sum(agg[m]["total_score"] for m in models)/len(models),1)
cards=[
    {"l":"参测模型(已剔除死模型)","v":str(len(models)),"s":f"剔除 {len(DEAD)} 个死模型","c":"#31C476"},
    {"l":"完全完成 80/80","v":str(completed),"s":f"占 {round(100*completed/len(models))}%","c":"#31C476"},
    {"l":"平均总分(150制)","v":str(avg_score),"s":"满分 150","c":"#7CE0A8"},
    {"l":"维度数 / 题数","v":"5 / 80","s":"编程·Linux·写作·数学·知识","c":"#4FC3F7"},
]
cards_html="".join(f'<div class="card"><div class="card-label">{c["l"]}</div><div class="card-value" style="color:{c["c"]}">{c["v"]}</div><div class="card-sub">{c["s"]}</div></div>' for c in cards)
legend='<div class="legend"><span><i style="background:#31C476"></i>满分完成 80/80</span><span><i style="background:#F5C518"></i>≥90% 完成</span><span><i style="background:#FF8A4C"></i>部分/通道阻塞</span><span><i style="background:#555"></i>热力图灰斜纹=未完成</span></div>'

# 雷达墙
radar_wall="".join(radar(m) for m in ranked)

# 优缺点卡
pc_cards=""
for m in ranked:
    a=agg[m]
    tagcol="#31C476" if a["ok"]==80 else ("#F5C518" if a["pct"]>=90 else "#FF8A4C")
    tagtxt="80/80" if a["ok"]==80 else f"{a['ok']}/80"
    pc_cards+=f'''<div class="pc"><h3><span>{esc(pretty(m))}</span><span class="tag" style="color:{tagcol};border:1px solid {tagcol}55;background:{tagcol}1a">#{a["rank"]} · {tagtxt}</span></h3>
    <p>{pros_cons(m)}</p>
    <div class="mini"><span>总分 <b style="color:#fff">{a["total_score"]:.1f}</b></span><span>CPI <b style="color:#fff">{a["cpi"]}</b></span><span>均时 {a["avg_time"]}s</span><span>报错 {a["err_total"]}</span></div></div>'''

# 耗时与报错 表
time_rows=""
for m in sorted(models,key=lambda m:-agg[m]["cpi"]):
    a=agg[m]
    errs=" · ".join(f"{k}×{v}" for k,v in sorted(a["errors"].items(),key=lambda x:-x[1])) or "—"
    time_rows+=f'<tr><td>{esc(pretty(m))}</td><td class="num">{a["cpi"]}</td><td>{a["avg_time"]}s</td><td>{a["avg_ttft"]}s</td><td>{a["total_time"]}s</td><td>{a["err_total"]}</td><td style="color:#FFB38A">{errs}</td></tr>'

# 维度分组柱状图 legend
dim_legend="".join(f'<span><i style="background:{DIM_COLOR[d]}"></i>{d}</span>' for d in DIMS)

# CPI 结论
best_cpi=max(models,key=lambda m:agg[m]["cpi"])
best_score=ranked[0]
cpi_note=f'<p style="font-size:13px;line-height:1.8;margin-top:8px">性价比指数 CPI = 加权总分(150制) ÷ 总耗时(秒) × 100（值越大越划算）。<br><b style="color:#31C476">速度性价比最优</b>：{esc(pretty(best_cpi))}（CPI={agg[best_cpi]["cpi"]}，均时 {agg[best_cpi]["avg_time"]}s）。<br><b style="color:#7CE0A8">综合得分最高</b>：{esc(pretty(best_score))}（{agg[best_score]["total_score"]:.1f}/150）。<br>注：未完成模型的 CPI 仅基于已作答部分，整体偏低不代表真实能力上限，待通道恢复补完后重排。</p>'

gen_time="2026-08-26 15:20 (GMT+8)"
HTML=f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Relay 能力横评 · 最终报告</title><style>{CSS}</style></head>
<body><div class="wrap">
<header><h1>Relay 中转站 · <span class="accent">模型能力横评</span> 最终报告</h1>
<div class="sub">80 题 / 150 分权威题组 · 生成时间 {gen_time} · 得分=判分器分÷100×题面分值（非原始分累加）· 已剔除死模型 {esc("、".join(DEAD))}</div></header>
<div class="cards">{cards_html}</div>

<section><h2>① 综合排名（150 分制）</h2>
{legend}
{rank_bars()}
</section>

<section><h2>② 逐题热力图（判分器分 0-100）</h2>
<div class="sub" style="font-size:12px;margin-bottom:2px">行=模型（按总分降序），列=80 题；绿越深分越高，灰斜纹=未完成。横向可滚动。</div>
<div class="hm">{heatmap()}</div></section>

<section><h2>③ 能力分维图表</h2>
<div class="sub" style="font-size:12px">A. 维度分组柱状图（Top12 模型，按各维度满分归一为 %）</div>
<div class="legend">{dim_legend}</div>
{group_bar()}
<div class="sub" style="font-size:12px;margin-top:14px">B. 各模型多维度雷达图（5 维归一 %）</div>
<div class="radar-wall">{radar_wall}</div></section>

<section><h2>④ 各模型优缺点总结</h2>
<div class="pc-grid">{pc_cards}</div></section>

<section><h2>⑤ 耗时与报错对比 + 时间性价比</h2>
<table class="tbl"><thead><tr><th>模型</th><th>CPI</th><th>均耗时</th><th>均TTFT</th><th>总耗时</th><th>报错数</th><th>报错类型分布</th></tr></thead>
<tbody>{time_rows}</tbody></table>
{cpi_note}</section>

<footer>
<p><b>评分口径</b>：实际得分 = 判分器分(0-100) ÷ 100 × 题面分值；各维度满分 编程56 / Linux8.5 / 写作6 / 数学推理36.5 / 知识科学43，合计 150。</p>
<p><b>阻塞说明</b>：HY-3 / Mimo-v2.5 / Kimi-K3 因 de5 坏窗口（模型 500 + 裁判 503）或无可用通道，部分题未作答，分数未含缺失项，待窗口恢复后续跑补全。</p>
<p><b>已剔除死模型</b>：{esc("、".join(DEAD))}（上游不可用 / 空响应 / Cursor 错误页伪装 200，数据无意义）。</p>
</footer>
</div></body></html>'''

with open(OUT,"w",encoding="utf-8") as f:
    f.write(HTML)
print("OK ->",OUT)
print("模型数:",len(models),"| 满分完成:",completed)
print("Top3:",[(pretty(m),round(agg[m]["total_score"],1)) for m in ranked[:3]])
# 校验分值覆盖
miss=[q for q in all_qids if q not in POINT]
if miss: print("WARN 未配置分值的题:",miss)
