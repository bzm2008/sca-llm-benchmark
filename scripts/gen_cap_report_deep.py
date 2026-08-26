# -*- coding: utf-8 -*-
"""gen_cap_report_deep.py —— 深度评测报告(排名条形图/分维度柱状图/逐题热力图/文字分析)"""
import json, os, math

DIMS=["code","linux","bash"]
DIM_NAME={"code":"编程Python","linux":"Linux命令","bash":"Bash脚本"}
DIM_COLOR={"code":"#1f77b4","linux":"#2ca02c","bash":"#9467bd"}
MODEL_LABEL={
    "oc/hy-3":"oc/hy-3","42":"42 (muse-spark)","nvidia/minimax-m3":"minimax-m3",
    "grok-4.6":"grok-4.6","nvidia/deepseek-v4-flash-0731":"deepseek-v4-flash",
    "nvidia/nemotron-3-ultra-550b-a55b":"nemotron-550b",
    "oc/big-pickle":"oc/big-pickle","oc/mimo-v2.5":"oc/mimo-v2.5"}
QID_ORDER=["p1","p2","p3","p4","p5","p6","p7","p8","p9","p10","p11","p12",
           "l1","l2","l3","l4","l5","l6","l7","l8","l9","l10","b1","b2","b3"]

def load(path):
    rows=[]
    if os.path.exists(path):
        with open(path,encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if line:
                    try: rows.append(json.loads(line))
                    except Exception: pass
    return rows

def build(result_path, models):
    rows=load(result_path)
    best={}
    for r in rows:
        best[(r["model"],r["qid"])]=r
    rows=list(best.values())

    # 每题得分矩阵: model -> {qid: score}
    mat={}
    for m in models:
        mat[m]={}
    for r in rows:
        if r.get("status")=="ok" and r.get("score") is not None:
            mat[r["model"]][r["qid"]]=r["score"]

    def dim_avg(m,d):
        vals=[mat[m].get(q) for q in QID_ORDER if q in mat[m]]
        return None if not vals else round(sum(vals)/len(vals),1)
    def overall(m):
        vals=[mat[m].get(q) for q in QID_ORDER if q in mat[m]]
        return None if not vals else round(sum(vals)/len(vals),1)

    ranked=[(m,overall(m)) for m in models if overall(m) is not None]
    ranked.sort(key=lambda x:-x[1])
    na=[m for m in models if overall(m) is None]

    # ---- SVG 1: 排名条形 ----
    W,H=900,50+len(ranked)*42
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Arial,sans-serif">']
    s.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    barx=270; barmax=540
    cols=["#00453E","#31C476","#1f77b4","#ff7f0e","#8c564b","#e377c2"]
    for i,(m,v) in enumerate(ranked):
        y=40+i*42
        bw=barmax*v/100.0
        s.append(f'<text x="10" y="{y+19}" font-size="14" fill="#222">{MODEL_LABEL.get(m,m)}</text>')
        s.append(f'<rect x="{barx}" y="{y+4}" width="{barmax}" height="24" fill="#eee" rx="3"/>')
        s.append(f'<rect x="{barx}" y="{y+4}" width="{bw:.1f}" height="24" fill="{cols[i%len(cols)]}" rx="3"/>')
        s.append(f'<text x="{barx+barmax+8}" y="{y+21}" font-size="14" fill="#222" font-weight="bold">{v}</text>')
    s.append('</svg>')
    rank_svg="".join(s)

    # ---- SVG 2: 分维度柱状(3组×6模型) ----
    models_ok=[m for m,_ in ranked]
    n=len(models_ok); nd=3
    W2=900; H2=420; ml=50; mb=90; mt=30; pw=W2-ml-20; ph=H2-mt-mb
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W2} {H2}" font-family="Segoe UI,Arial,sans-serif">']
    s.append(f'<rect width="{W2}" height="{H2}" fill="#fff"/>')
    for g in range(0,101,20):
        y=mt+ph*(1-g/100)
        s.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W2-20}" y2="{y:.1f}" stroke="#eee"/>')
        s.append(f'<text x="{ml-6}" y="{y+4:.1f}" font-size="11" fill="#888" text-anchor="end">{g}</text>')
    gw=pw/nd; bw=gw/(n+1)
    for j,d in enumerate(DIMS):
        x0=ml+j*gw
        s.append(f'<text x="{x0+gw/2:.1f}" y="{H2-mb+18}" font-size="13" fill="#333" text-anchor="middle">{DIM_NAME[d]}</text>')
        for i,m in enumerate(models_ok):
            v=dim_avg(m,d)
            if v is None: continue
            x=x0+(i+0.5)*bw
            bh=ph*v/100.0; y=mt+ph-bh
            s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.8:.1f}" height="{bh:.1f}" fill="{cols[i%len(cols)]}" rx="2"/>')
    ly=mt+8
    for i,m in enumerate(models_ok):
        s.append(f'<rect x="{W2-300}" y="{ly+i*18}" width="12" height="12" fill="{cols[i%len(cols)]}"/>')
        s.append(f'<text x="{W2-300+18}" y="{ly+i*18+11}" font-size="12" fill="#333">{MODEL_LABEL.get(m,m)}</text>')
    s.append('</svg>')
    dim_svg="".join(s)

    # ---- SVG 3: 逐题热力图 (模型行 × 25题列) ----
    nq=len(QID_ORDER); nm=len(models_ok)
    ch=34; cw=56; lw=220; hh=44
    W3=lw+40+nq*cw+20; H3=hh+nm*ch+40
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W3} {H3}" font-family="Segoe UI,Arial,sans-serif">']
    s.append(f'<rect width="{W3}" height="{H3}" fill="#fff"/>')
    def cell_color(v):
        if v is None: return "#e8e8e8"
        if v>=90: return "#2e9e5b"
        if v>=70: return "#8fd14f"
        if v>=50: return "#ffd23f"
        if v>=30: return "#ff9f43"
        return "#e4572e"
    # 列头(题号+维度色条)
    for j,q in enumerate(QID_ORDER):
        x=lw+30+j*cw
        dim=next((d for d in DIMS if any(r["qid"]==q and r["dim"]==d for r in rows)),"")
        col=DIM_COLOR.get(dim,"#999")
        s.append(f'<rect x="{x}" y="{10}" width="{cw}" height="6" fill="{col}"/>')
        s.append(f'<text x="{x+cw/2:.1f}" y="{hh-14}" font-size="12" fill="#333" text-anchor="middle" font-weight="bold">{q}</text>')
    # 分组分隔线
    def group_boundary(qidx_list):
        pass
    for bnd in (12,22):
        x=lw+30+bnd*cw
        s.append(f'<line x1="{x:.1f}" y1="{10}" x2="{x:.1f}" y2="{hh+nm*ch}" stroke="#bbb" stroke-dasharray="4 3"/>')
    # 行: 模型 × 每题
    for i,m in enumerate(models_ok):
        y=hh+i*ch
        s.append(f'<text x="{lw+10}" y="{y+22}" font-size="13" fill="#222" text-anchor="end">{MODEL_LABEL.get(m,m)}</text>')
        for j,q in enumerate(QID_ORDER):
            x=lw+30+j*cw
            v=mat[m].get(q)
            s.append(f'<rect x="{x:.1f}" y="{y+2:.1f}" width="{cw-4:.1f}" height="{ch-4:.1f}" fill="{cell_color(v)}" rx="2"/>')
            if v is not None:
                s.append(f'<text x="{x+cw/2:.1f}" y="{y+20:.1f}" font-size="12" fill="#fff" text-anchor="middle" font-weight="bold">{v:.0f}</text>')
    # 图例
    leg_y=H3-16
    for k,(lab,c) in enumerate([("90-100","#2e9e5b"),("70-89","#8fd14f"),("50-69","#ffd23f"),("30-49","#ff9f43"),("0-29","#e4572e"),("不可用","#e8e8e8")]):
        x=lw+30+k*95
        s.append(f'<rect x="{x}" y="{leg_y-10}" width="14" height="14" fill="{c}"/>')
        s.append(f'<text x="{x+18}" y="{leg_y}" font-size="11" fill="#333">{lab}</text>')
    s.append('</svg>')
    heat_svg="".join(s)

    # ---- 明细表 ----
    rows_html=[]
    for i,(m,v) in enumerate(ranked):
        rows_html.append(f"<tr><td>{i+1}</td><td>{MODEL_LABEL.get(m,m)}</td><td><b>{v}</b></td>"
                         +"".join(f"<td>{dim_avg(m,d) if dim_avg(m,d) is not None else '—'}</td>" for d in DIMS)
                         +f"<td>{sum(1 for q in QID_ORDER if q in mat[m])}/{len(QID_ORDER)}</td></tr>")

    # ---- 文字分析 ----
    txt=[]
    if ranked:
        txt.append(f"<p><b>综合第一：{MODEL_LABEL.get(ranked[0][0],ranked[0][0])}</b>（{ranked[0][1]} 分），末位 {MODEL_LABEL.get(ranked[-1][0],ranked[-1][0])}（{ranked[-1][1]} 分）。</p>")
    for d in DIMS:
        vals=[(m,dim_avg(m,d)) for m,_ in ranked if dim_avg(m,d) is not None]
        if vals:
            bst=max(vals,key=lambda x:x[1]); wst=min(vals,key=lambda x:x[1])
            txt.append(f"<li><b>{DIM_NAME[d]}</b>：最强 {MODEL_LABEL.get(bst[0],bst[0])}（{bst[1]}）；最弱 {MODEL_LABEL.get(wst[0],wst[0])}（{wst[1]}）</li>")
    # 逐题亮点
    best_per_q=[]
    for q in QID_ORDER:
        vals=[(m,mat[m].get(q)) for m,_ in ranked if q in mat[m] and mat[m][q] is not None]
        if vals:
            bst=max(vals,key=lambda x:x[1]); wst=min(vals,key=lambda x:x[1])
            if bst[1]<100 or wst[1]>0:
                best_per_q.append(f"<li><b>{q}</b>：{MODEL_LABEL.get(bst[0],bst[0])} {bst[1]:.0f} vs {MODEL_LABEL.get(wst[0],wst[0])} {wst[1]:.0f}</li>")
    na_line = f"<p>不可用模型：{'、'.join(MODEL_LABEL.get(m,m) for m in na)}</p>" if na else ""

    html=f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>编程 & Linux 深度能力评测报告</title>
<style>
 body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',Arial,sans-serif;max-width:1150px;margin:auto;padding:24px;color:#222;background:#fafafa}}
 h1{{color:#00453E}} h2{{color:#00453E;border-left:4px solid #31C476;padding-left:10px;margin-top:30px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;background:#fff;font-size:14px}}
 th,td{{border:1px solid #ddd;padding:7px;text-align:center}}
 th{{background:#00453E;color:#fff}} tr:nth-child(even){{background:#f3f7f5}}
 .card{{background:#fff;border:1px solid #e3e8e6;border-radius:10px;padding:14px;margin:14px 0;box-shadow:0 1px 3px #0001}}
 svg{{width:100%;height:auto;display:block}}
 .note{{font-size:13px;color:#666;background:#fff8e1;border:1px solid #ffe082;padding:10px 14px;border-radius:8px}}
 .scroll{{overflow-x:auto}}
</style></head><body>
<h1>编程 & Linux 深度能力评测报告</h1>
<p class="note">端点 <code>https://YOUR_RELAY.example.com/v1</code> ｜ 25 题：编程 Python 12 题（沙箱执行比对）、Linux 命令 10 题（关键词判定）、Bash 脚本 3 题（Git Bash 真实执行）。
全部为程序化客观打分，无裁判偏差。热力图中列按 编程→Linux→Bash 分组。</p>

<h2>综合排名（25 题均分）</h2>
<div class="card">{rank_svg}</div>

<h2>分维度对比</h2>
<div class="card">{dim_svg}</div>

<h2>逐题热力图</h2>
<div class="card scroll">{heat_svg}</div>

<h2>明细得分表</h2>
<table><tr><th>排名</th><th>模型</th><th>综合</th><th>编程Python</th><th>Linux命令</th><th>Bash脚本</th><th>完成题数</th></tr>
{"".join(rows_html)}</table>

<h2>文字分析</h2>
<div class="card">{''.join(txt)}{na_line}</div>

<h2>方法学与局限</h2>
<div class="card"><ul>
<li>编程题在受限沙箱执行（禁止 os/subprocess/eval 等），比对标准输出；纯文本直接作答也计分。</li>
<li>Bash 题在本地 Git Bash 实际执行；命令知识题按关键命令命中判定。</li>
<li>每题 1 次采样、温度 0.3；推理型模型（42/grok 等）已给足 max_tokens（≥3000）确保输出最终答案。</li>
<li>42（muse-spark）后端间歇性 400/401/503，失败题会进入补测；本报告数据为最终去重结果。</li>
<li>限速 188 次/分钟，已做节拍控制与退避。</li>
</ul></div>
</body></html>"""
    out="capability_report_deep.html"
    with open(out,"w",encoding="utf-8") as f: f.write(html)
    print(f"深度报告已生成: {out}  (有效模型 {len(ranked)}, 不可用 {len(na)})")

if __name__=="__main__":
    build("cap_deep.jsonl",
          ["oc/hy-3","nvidia/minimax-m3","grok-4.6","nvidia/deepseek-v4-flash-0731",
           "nvidia/nemotron-3-ultra-550b-a55b","42"])
