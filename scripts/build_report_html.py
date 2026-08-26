# -*- coding: utf-8 -*-
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "report_data.json"), encoding="utf-8"))
rows = DATA["rows"]

# 预处理: 计算完成率, 状态颜色
def status_color(tag):
    return {
        "ok": "#31C476",
        "partial": "#F5C518",
        "blocked": "#FF8A4C",
        "stale": "#FF5C7A",
    }.get(tag, "#9AA0A6")

max_score = max((r["score"] for r in rows if r["tag"] != "stale"), default=1) or 1
for r in rows:
    r["pct"] = round(100.0 * r["ok"] / r["total"], 1)
    r["bar_w"] = round(100.0 * r["score"] / max_score, 1) if r["tag"] != "stale" else 0
    r["color"] = status_color(r["tag"])

# 排序: stale 排最后
ordered = sorted(rows, key=lambda x: (x["tag"] == "stale", -x["score"]))

# V2: 题数动态化(兼容旧 report_data.json)
TOTAL = max((r.get("total", 70) for r in rows), default=70)

# V2: 题数动态化(兼容旧 report_data.json)
TOTAL = max((r.get("total", 70) for r in rows), default=70)

gen_time = "2026-08-26 15:09 (GMT+8)"
fully = DATA["fully_done"]
total_models = DATA["n_models"]
blocked = [r for r in rows if r["tag"] == "blocked"]
stale = [r for r in rows if r["tag"] == "stale"]
partial = [r for r in rows if r["tag"] == "partial"]
avg_score = round(sum(r["score"] for r in rows if r["tag"] != "stale") / max(1, len([r for r in rows if r["tag"] != "stale"])), 1)

# 头部卡片数据
cards = [
    {"label": "参测模型", "value": str(total_models), "sub": "模型通道横评", "c": "#31C476"},
    {"label": "完全完成 80/80", "value": f"{fully}", "sub": f"占 {round(100*fully/total_models)}%", "c": "#31C476"},
    {"label": "平均总分", "value": f"{avg_score}", "sub": "满分约 150×80=12000", "c": "#7CE0A8"},
    {"label": "待处理", "value": f"{len(blocked)+len(stale)}", "sub": f"{len(blocked)} 阻塞 + {len(stale)} 旧垃圾", "c": "#FF8A4C"},
]

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

# 生成每行 HTML
def row_html(r, idx):
    medal = ""
    if r["tag"] != "stale" and idx < 3:
        medal = ["🥇", "🥈", "🥉"][idx]
    tag_label = {"ok": "已完成", "partial": "部分完成", "blocked": "通道阻塞", "stale": "旧数据·需重跑"}[r["tag"]]
    miss = ", ".join(r["missing"]) if r["missing"] else "—"
    miss_types = " · ".join(f"{k}×{v}" for k, v in r["miss_types"].items()) if r["miss_types"] else ""
    note = ""
    if r["tag"] == "blocked":
        note = f'<div class="note">⛔ {esc(r["block_reason"])}</div>'
    elif r["tag"] == "stale":
        note = '<div class="note">⚠️ 早期空响应被误判为 0 分的垃圾数据，非真实失败，需重跑。</div>'
    # 题型缺失小标签
    mt_html = ""
    if miss_types:
        mt_html = f'<span class="mt">{esc(miss_types)}</span>'
    return f'''
    <div class="row" data-tag="{r['tag']}" data-score="{r['score']}">
      <div class="rank">{medal or (idx+1)}</div>
      <div class="name">{esc(r['pretty'])}</div>
      <div class="barwrap">
        <div class="bar" style="width:{r['bar_w']}%;background:linear-gradient(90deg,{r['color']}cc,{r['color']})"></div>
        <span class="score">{r['score']}</span>
      </div>
      <div class="ring" title="完成 {r['ok']}/{TOTAL}">
        {ring_svg(r['pct'], r['color'])}
      </div>
      <div class="pill" style="color:{r['color']};border-color:{r['color']}55;background:{r['color']}1a">{tag_label} · {r['ok']}/{TOTAL}</div>
      <div class="miss">{miss}{mt_html}</div>
      {note}
    </div>'''

def ring_svg(pct, color):
    pct = max(0, min(100, pct))
    r = 15.9  # 周长 100
    off = 100 - pct
    return f'''<svg viewBox="0 0 36 36" class="ring-svg">
      <path class="ring-bg" d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="3.2"/>
      <path d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31" fill="none" stroke="{color}" stroke-width="3.2" stroke-dasharray="100" stroke-dashoffset="{off:.1f}" stroke-linecap="round" transform="rotate(-90 18 18)"/>
      <text x="18" y="20.5" class="ring-txt">{pct:.0f}%</text>
    </svg>'''

rows_html = "\n".join(row_html(r, i) for i, r in enumerate(ordered))

# 卡片 HTML
cards_html = "\n".join(
    f'''<div class="card">
      <div class="card-label">{esc(c['label'])}</div>
      <div class="card-value" style="color:{c['c']}">{c['value']}</div>
      <div class="card-sub">{esc(c['sub'])}</div>
    </div>''' for c in cards)

# 图例
legend = f'''
<div class="legend">
  <span><i style="background:#31C476"></i>已完成 {TOTAL}/{TOTAL}</span>
  <span><i style="background:#F5C518"></i>部分完成</span>
  <span><i style="background:#FF8A4C"></i>通道阻塞</span>
  <span><i style="background:#FF5C7A"></i>旧数据·需重跑</span>
</div>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relay 能力横评 · 最终报告</title>
<style>
  :root {{
    --bg:#00453E; --bg2:#06352F; --glass:rgba(255,255,255,0.06);
    --border:rgba(255,255,255,0.14); --text:#D9DBD6; --muted:#9FB3AD;
    --green:#31C476; --green2:#7CE0A8;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;
    background:radial-gradient(1200px 700px at 15% -10%, #0a5a4f 0%, var(--bg) 45%, var(--bg2) 100%);
    color:var(--text); min-height:100vh; padding:32px 20px 60px; -webkit-font-smoothing:antialiased;
  }}
  .wrap {{ max-width:1080px; margin:0 auto; }}
  header {{ margin-bottom:26px; }}
  h1 {{ font-size:28px; font-weight:800; letter-spacing:.5px; }}
  h1 .accent {{ color:var(--green); }}
  .sub {{ color:var(--muted); font-size:13px; margin-top:6px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:22px 0 10px; }}
  .card {{ background:var(--glass); border:1px solid var(--border); border-radius:18px; padding:18px 16px; backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); box-shadow:0 8px 30px rgba(0,0,0,.18); }}
  .card-label {{ font-size:12px; color:var(--muted); }}
  .card-value {{ font-size:30px; font-weight:800; margin:6px 0 2px; }}
  .card-sub {{ font-size:11px; color:var(--muted); }}
  .legend {{ display:flex; gap:18px; flex-wrap:wrap; font-size:12px; color:var(--muted); margin:14px 2px 4px; }}
  .legend i {{ display:inline-block; width:11px; height:11px; border-radius:3px; margin-right:6px; vertical-align:-1px; }}
  .table {{ margin-top:14px; background:var(--glass); border:1px solid var(--border); border-radius:18px; backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); overflow:hidden; }}
  .row {{ display:grid; grid-template-columns:42px 1.5fr 3fr 64px 150px; grid-template-areas:"rank name bar ring pill" "rank miss miss miss note"; align-items:center; gap:10px 14px; padding:14px 18px; border-bottom:1px solid rgba(255,255,255,0.07); }}
  .row:last-child {{ border-bottom:none; }}
  .row:hover {{ background:rgba(255,255,255,0.04); }}
  .rank {{ grid-area:rank; font-weight:800; font-size:15px; color:var(--muted); text-align:center; }}
  .name {{ grid-area:name; font-weight:700; font-size:14.5px; }}
  .barwrap {{ grid-area:bar; position:relative; height:22px; background:rgba(255,255,255,0.07); border-radius:11px; overflow:hidden; }}
  .bar {{ height:100%; border-radius:11px; transition:width .6s ease; }}
  .score {{ position:absolute; right:8px; top:50%; transform:translateY(-50%); font-size:12px; font-weight:700; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,.4); }}
  .ring {{ grid-area:ring; display:flex; justify-content:center; }}
  .ring-svg {{ width:46px; height:46px; }}
  .ring-txt {{ font-size:9px; font-weight:700; fill:var(--text); text-anchor:middle; }}
  .pill {{ grid-area:pill; justify-self:start; font-size:11.5px; font-weight:700; padding:4px 10px; border-radius:999px; border:1px solid; white-space:nowrap; }}
  .miss {{ grid-area:miss; font-size:11.5px; color:var(--muted); }}
  .miss .mt {{ color:var(--green2); margin-left:8px; }}
  .note {{ grid-area:note; font-size:11.5px; color:#FFB38A; margin-top:2px; }}
  footer {{ margin-top:24px; font-size:12px; color:var(--muted); line-height:1.7; }}
  footer b {{ color:var(--green2); }}
  @media (max-width:760px) {{
    .cards {{ grid-template-columns:repeat(2,1fr); }}
    .row {{ grid-template-columns:34px 1.2fr 2.2fr 44px; grid-template-areas:"rank name bar ring" "rank pill pill pill" "rank miss miss miss" "rank note note note"; }}
    .pill {{ justify-self:start; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Relay 中转站 · <span class="accent">模型能力横评</span> 最终报告</h1>
    <div class="sub">{TOTAL} 题 / 150 分权威题组 (V2) · 生成时间 {gen_time} · 数据源 final80_results.jsonl（已清洗 model="1" 污染）</div>
  </header>
  <div class="cards">{cards_html}</div>
  {legend}
  <div class="table">
    {rows_html}
  </div>
  <footer>
    <p><b>说明</b>：分数 = {TOTAL} 题加权得分总和（满分 150）。横条长度按当前最高分 {int(max_score)} 归一。</p>
    <p><b>阻塞模型</b>：HY-3 / Mimo-v2.5 / Kimi-K3 当前因 de5 坏窗口（模型 500 + 裁判 503）或通道全死而补不完，其缺口题将在窗口恢复后自动续跑。</p>
    <p><b>旧数据</b>：GPT-4o、Qwen3.8-Max 显示为 0/{TOTAL} 是早期空响应误判为 0 分的垃圾数据，并非真实失败，需重跑取真实分。</p>
  </footer>
</div>
</body>
</html>'''

out = os.path.join(HERE, "report.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("已生成", out, "大小", len(html), "字节")
