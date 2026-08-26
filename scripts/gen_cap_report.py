# -*- coding: utf-8 -*-
"""gen_cap_report.py —— 读取 cap_results.jsonl 生成自包含 HTML 报告(内联 SVG 图表+文字)"""
import json, os, re

DIMS = ["math","code","linux","knowledge","chinese"]
DIM_NAME = {"math":"数学与逻辑","code":"编程","linux":"系统与Linux","knowledge":"知识事实","chinese":"中文与指令"}
DIM_ORDER = DIMS
PALETTE = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#17becf"]
MODEL_LABEL = {
    "oc/hy-3":"oc/hy-3","42":"42 (muse-spark)","oc/big-pickle":"oc/big-pickle",
    "oc/mimo-v2.5":"oc/mimo-v2.5","nvidia/minimax-m3":"nvidia/minimax-m3",
    "grok-4.6":"grok-4.6","nvidia/deepseek-v4-flash-0731":"deepseek-v4-flash",
    "nvidia/nemotron-3-ultra-550b-a55b":"nemotron-550b",
}

def load(path):
    rows=[]
    if os.path.exists(path):
        with open(path,encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line:
                    try: rows.append(json.loads(line))
                    except: pass
    return rows

def aggregate(rows, models):
    # 去重: 每个 (model,qid) 只保留最后一条记录(重试成功后旧记录作废)
    best = {}
    for r in rows:
        best[(r["model"], r["qid"])] = r
    rows = list(best.values())
    data={}
    for m in models:
        recs=[r for r in rows if r["model"]==m]
        by_dim={d:[] for d in DIMS}
        for r in recs:
            if r.get("status")=="ok" and r.get("score") is not None:
                by_dim[r["dim"]].append(r["score"])
        dim_avg={}
        for d in DIMS:
            dim_avg[d]=round(sum(by_dim[d])/len(by_dim[d]),1) if by_dim[d] else None
        avail=sum(1 for d in DIMS if dim_avg[d] is not None)
        overall=round(sum(v for v in dim_avg.values() if v is not None)/avail,1) if avail else None
        data[m]={"dim":dim_avg,"overall":overall,"avail":avail,"n":len(recs)}
    return data

# ---------- SVG: 排名横向条形 ----------
def svg_ranking(data):
    ms=[(m,v) for m,v in data.items() if v["overall"] is not None]
    ms.sort(key=lambda x:-x[1]["overall"])
    W,H=920,60+len(ms)*40
    rowh=40; barx=260; barmax=560
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Arial,sans-serif">']
    s.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    for i,(m,v) in enumerate(ms):
        y=40+i*rowh
        color=PALETTE[i%len(PALETTE)]
        bw=barmax*v["overall"]/100.0
        s.append(f'<text x="10" y="{y+18}" font-size="14" fill="#222">{MODEL_LABEL.get(m,m)}</text>')
        s.append(f'<rect x="{barx}" y="{y+4}" width="{barmax}" height="22" fill="#eee" rx="3"/>')
        s.append(f'<rect x="{barx}" y="{y+4}" width="{bw:.1f}" height="22" fill="{color}" rx="3"/>')
        s.append(f'<text x="{barx+barmax+8}" y="{y+20}" font-size="14" fill="#222" font-weight="bold">{v["overall"]}</text>')
    s.append('</svg>')
    return "".join(s)

# ---------- SVG: 分维度分组柱状 ----------
def svg_grouped(data):
    models=[m for m in data if data[m]["overall"] is not None]
    n=len(models); nd=len(DIMS)
    W=920; H=420; mleft=50; mbottom=90; mtop=30; plotw=W-mleft-20; ploth=H-mtop-mbottom
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Arial,sans-serif">']
    s.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    # y grid
    for g in range(0,101,20):
        y=mtop+ploth*(1-g/100)
        s.append(f'<line x1="{mleft}" y1="{y:.1f}" x2="{W-20}" y2="{y:.1f}" stroke="#eee"/>')
        s.append(f'<text x="{mleft-6}" y="{y+4:.1f}" font-size="11" fill="#888" text-anchor="end">{g}</text>')
    gw=plotw/nd
    bw=gw/(n+1)
    for j,d in enumerate(DIMS):
        x0=mleft+j*gw
        s.append(f'<text x="{x0+gw/2:.1f}" y="{H-mbottom+18}" font-size="13" fill="#333" text-anchor="middle">{DIM_NAME[d]}</text>')
        for i,m in enumerate(models):
            v=data[m]["dim"][d]
            if v is None: continue
            x=x0+(i+0.5)*bw
            bh=ploth*v/100.0
            y=mtop+ploth-bh
            s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.8:.1f}" height="{bh:.1f}" fill="{PALETTE[i%len(PALETTE)]}" rx="2"/>')
    # legend
    ly=mtop+8
    for i,m in enumerate(models):
        lx=W-300
        s.append(f'<rect x="{lx}" y="{ly+i*18}" width="12" height="12" fill="{PALETTE[i%len(PALETTE)]}"/>')
        s.append(f'<text x="{lx+18}" y="{ly+i*18+11}" font-size="12" fill="#333">{MODEL_LABEL.get(m,m)}</text>')
    s.append('</svg>')
    return "".join(s)

# ---------- SVG: 雷达图 ----------
def svg_radar(data):
    models=[m for m in data if data[m]["overall"] is not None]
    cx,cy,R=330,300,210
    n=len(DIMS)
    import math
    ang=lambda i: -math.pi/2 + i*2*math.pi/n
    s=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 600" font-family="Segoe UI,Arial,sans-serif">']
    s.append('<rect width="720" height="600" fill="#fff"/>')
    # grid rings
    for ring in (20,40,60,80,100):
        pts=[]
        for i in range(n):
            r=R*ring/100
            x=cx+r*math.cos(ang(i)); y=cy+r*math.sin(ang(i))
            pts.append(f"{x:.1f},{y:.1f}")
        s.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="#eee"/>')
    # axes + labels
    for i,d in enumerate(DIMS):
        x=cx+R*math.cos(ang(i)); y=cy+R*math.sin(ang(i))
        s.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#ddd"/>')
        lx=cx+(R+28)*math.cos(ang(i)); ly=cy+(R+28)*math.sin(ang(i))
        s.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="13" fill="#333" text-anchor="middle">{DIM_NAME[d]}</text>')
    for i,m in enumerate(models):
        pts=[]
        for j,d in enumerate(DIMS):
            v=data[m]["dim"][d] or 0
            r=R*v/100.0
            x=cx+r*math.cos(ang(j)); y=cy+r*math.sin(ang(j))
            pts.append(f"{x:.1f},{y:.1f}")
        col=PALETTE[i%len(PALETTE)]
        s.append(f'<polygon points="{" ".join(pts)}" fill="{col}22" stroke="{col}" stroke-width="2"/>')
    # legend
    for i,m in enumerate(models):
        lx=620; ly=40+i*22
        s.append(f'<rect x="{lx}" y="{ly}" width="12" height="12" fill="{PALETTE[i%len(PALETTE)]}"/>')
        s.append(f'<text x="{lx+18}" y="{ly+11}" font-size="12" fill="#333">{MODEL_LABEL.get(m,m)}</text>')
    s.append('</svg>')
    return "".join(s)

def build(result_path, models):
    rows=load(result_path)
    data=aggregate(rows, models)
    ranked=[(m,v) for m,v in data.items() if v["overall"] is not None]
    ranked.sort(key=lambda x:-x[1]["overall"])
    na=[m for m in models if data[m]["overall"] is None]

    # 文本分析
    rank_lines=[]
    for i,(m,v) in enumerate(ranked):
        rank_lines.append(f"<tr><td>{i+1}</td><td>{MODEL_LABEL.get(m,m)}</td><td><b>{v['overall']}</b></td>"
                          +"".join(f"<td>{v['dim'][d] if v['dim'][d] is not None else '—'}</td>" for d in DIMS)
                          +f"<td>{v['avail']}/5</td></tr>")

    # 各维最强最弱
    dim_extreme=[]
    for d in DIMS:
        vals=[(m,v["dim"][d]) for m,v in data.items() if v["dim"][d] is not None]
        if vals:
            best=max(vals,key=lambda x:x[1]); worst=min(vals,key=lambda x:x[1])
            dim_extreme.append(f"<li><b>{DIM_NAME[d]}</b>：最强 {MODEL_LABEL.get(best[0],best[0])} ({best[1]})；最弱 {MODEL_LABEL.get(worst[0],worst[0])} ({worst[1]})</li>")

    na_line = ("<p>以下模型全部题目不可用(中转站无后端渠道/503)：<b>"+
               "、".join(MODEL_LABEL.get(m,m) for m in na)+"</b></p>") if na else ""

    rank1 = ranked[0][0] if ranked else None
    rankN = ranked[-1][0] if ranked else None
    narrative = ""
    if ranked:
        narrative += f"<p>综合排名第一：<b>{MODEL_LABEL.get(rank1,rank1)}</b>（{ranked[0][1]['overall']}分）。"
        narrative += f"末位：<b>{MODEL_LABEL.get(rankN,rankN)}</b>（{ranked[-1][1]['overall']}分）。</p>"
    narrative += "<ul>"+"".join(dim_extreme)+"</ul>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>中转站多模型能力评测报告</title>
<style>
 body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',Arial,sans-serif;max-width:1000px;margin:auto;padding:24px;color:#222;background:#fafafa}}
 h1{{color:#00453E}} h2{{color:#00453E;border-left:4px solid #31C476;padding-left:10px;margin-top:32px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;background:#fff}}
 th,td{{border:1px solid #ddd;padding:8px;text-align:center;font-size:14px}}
 th{{background:#00453E;color:#fff}} tr:nth-child(even){{background:#f3f7f5}}
 .card{{background:#fff;border:1px solid #e3e8e6;border-radius:10px;padding:14px;margin:14px 0;box-shadow:0 1px 3px #0001}}
 .note{{font-size:13px;color:#666;background:#fff8e1;border:1px solid #ffe082;padding:10px 14px;border-radius:8px}}
 svg{{width:100%;height:auto;display:block}}
</style></head><body>
<h1>中转站多模型能力评测报告</h1>
<p class="note">端点 <code>https://YOUR_RELAY.example.com/v1</code> ｜ 评测维度：数学与逻辑 / 编程 / 系统与Linux / 知识事实 / 中文与指令（共 17 题）。
打分方式：数值题精确匹配、编程题沙箱执行比对输出、知识/指令题关键词与字数判定、中文写作题由 <code>ministral-8b-latest</code> 裁判 0–100 分。模型 <code>42</code> 真实为 <code>muse-spark-1.2-contributor-free</code>（强推理，已给足 token）。</p>

<h2>总排名</h2>
<div class="card">{svg_ranking(data)}</div>

<h2>分维度对比</h2>
<div class="card">{svg_grouped(data)}</div>

<h2>能力雷达</h2>
<div class="card">{svg_radar(data)}</div>

<h2>明细得分表</h2>
<table><tr><th>排名</th><th>模型</th><th>综合</th><th>数学</th><th>编程</th><th>Linux</th><th>知识</th><th>中文</th><th>有效维度</th></tr>
{"".join(rank_lines)}</table>

<h2>文字分析</h2>
<div class="card">{narrative}{na_line}</div>

<h2>方法学与局限</h2>
<div class="card"><ul>
<li>本评测为<strong>自定义精选小题</strong>，用于横向相对比较，非标准学术基准（如 MMLU/GPQA），绝对分值不代表模型真实水平。</li>
<li>编程题在受限沙箱中执行（禁止 os/subprocess/eval 等危险调用），仅校验输出数值。</li>
<li>中文写作题由轻量裁判模型打分，存在主观偏差；其余为程序化客观判定。</li>
<li>限速 188 次/分钟、625000 tokens/分钟；评测已做节拍控制与 429 退避；单个模型最长等待 180s/题。</li>
<li>推理型模型（42/grok-4.6 等）首字慢，已通过流式保活避免超时误判。</li>
</ul></div>
</body></html>"""
    out="capability_report.html"
    with open(out,"w",encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {out}  ({len(ranked)} 个模型有效, {len(na)} 个不可用)")

if __name__=="__main__":
    import sys
    build("cap_results.jsonl",
          ["oc/hy-3","42","oc/big-pickle","oc/mimo-v2.5","nvidia/minimax-m3","grok-4.6","nvidia/deepseek-v4-flash-0731","nvidia/nemotron-3-ultra-550b-a55b"])
