# -*- coding: utf-8 -*-
"""
中转站多模型能力评测 (capability_test.py)
- 维度: 数学与逻辑 / 编程 / 系统与Linux / 知识事实 / 中文与指令
- 打分: 程序化(数值/代码执行/关键词/字数) + 快速模型(ministral-8b-latest)当裁判
- 特性: 流式抽取、断点续测、429/超时自动退避重试、进度日志
- 用法:
    python capability_test.py                 # 跑全部 8 个模型
    python capability_test.py oc/hy-3         # 只跑指定模型
    python capability_test.py oc/hy-3 --smoke # 冒烟(每维1题)
"""
import urllib.request, os, json, gzip, time, sys, re, subprocess, threading

KEY = "YOUR_RELAY_API_KEY"
BASE = "https://YOUR_RELAY.example.com/v1"
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
PY = sys.executable

JUDGE_MODEL = "ministral-8b-latest"
# 网关级确认不存在的模型(400/401): 不可用记录永久跳过, 不再重试
GATEWAY_UNAVAILABLE = {"oc/big-pickle", "oc/mimo-v2.5"}
ALL_MODELS = [
    "oc/hy-3", "42", "oc/big-pickle", "oc/mimo-v2.5",
    "nvidia/minimax-m3", "grok-4.6", "nvidia/deepseek-v4-flash-0731",
    "nvidia/nemotron-3-ultra-550b-a55b",
]

# ---------- HTTP 底层 ----------
_op = None
def opener():
    global _op
    if _op is None:
        hd = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}) if PROXY else None
        _op = urllib.request.build_opener(hd) if hd else urllib.request.build_opener()
    return _op

_lock = threading.Lock()

def chat_stream(model, content, max_tokens=2048, timeout=150, temperature=0.3):
    """流式请求, 返回 (text, ttft, elapsed, status, err)"""
    body = json.dumps({"model": model, "messages":[{"role":"user","content":content}],
                       "max_tokens": max_tokens, "stream": True, "temperature": temperature}).encode()
    req = urllib.request.Request(BASE+"/chat/completions", data=body,
        headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","User-Agent":UA,"Accept":"text/event-stream"},
        method="POST")
    t0=time.time(); first=None; buf=[]; status=200; err=""
    try:
        r = opener().open(req, timeout=timeout)
        for raw in r:
            if raw.strip()==b"":
                continue
            line = raw.decode("utf-8","replace")
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            if "error" in obj:
                err = str(obj["error"]); status = obj.get("error",{}).get("code","err")
                break
            try:
                d = obj["choices"][0]["delta"].get("content","")
            except Exception:
                d = ""
            if d:
                if first is None:
                    first = time.time()-t0
                buf.append(d)
        text = "".join(buf)
        return (text, (first or (time.time()-t0)), round(time.time()-t0,2), status, err)
    except urllib.error.HTTPError as e:
        try:
            b = e.read().decode("utf-8","replace")
        except Exception:
            b = ""
        return ("", None, round(time.time()-t0,2), e.code, b[:300])
    except Exception as e:
        return ("", None, round(time.time()-t0,2), "EXC_"+type(e).__name__, str(e)[:200])

def chat_simple(model, content, max_tokens=12, timeout=60, temperature=0):
    body = json.dumps({"model": model, "messages":[{"role":"user","content":content}],
                       "max_tokens": max_tokens, "stream": False, "temperature": temperature}).encode()
    req = urllib.request.Request(BASE+"/chat/completions", data=body,
        headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","User-Agent":UA,"Accept":"application/json"},
        method="POST")
    try:
        r = opener().open(req, timeout=timeout)
        data = r.read()
        if "gzip" in r.headers.get("Content-Encoding","").lower():
            data = gzip.decompress(data)
        obj = json.loads(data)
        return obj["choices"][0]["message"]["content"].strip(), 200, ""
    except urllib.error.HTTPError as e:
        return "", e.code, ""
    except Exception as e:
        return "", "EXC", str(e)[:120]

# ---------- 代码执行沙箱 ----------
DANGER = ["import os","import subprocess","__import__","eval(","exec(","open(",
          "system(","os.system","subprocess","shutil","pathlib","builtins",
          "globals(","locals(","compile(","socket","requests","urllib"]
def run_code(code):
    low = code.lower()
    for d in DANGER:
        if d in low:
            return (False, "unsafe:"+d)
    try:
        r = subprocess.run([PY,"-c",code], capture_output=True, text=True, timeout=10,
                           creationflags=0x08000000)
        if r.returncode != 0:
            return (False, "err:"+r.stderr.strip()[:160])
        return (True, r.stdout.strip())
    except subprocess.TimeoutExpired:
        return (False, "timeout")
    except Exception as e:
        return (False, str(e)[:120])

def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    return text.strip()

# ---------- 打分器 ----------
def score_numeric(text, accepts):
    m = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",",""))
    nums = [float(x) for x in m]
    for acc in accepts:
        try:
            f = float(acc)
        except Exception:
            f = None
        for n in nums:
            if f is not None and abs(n-f) < 1e-6:
                return 1.0
            # 分数形如 3/4
        # 分数匹配
        fm = re.search(r"(\d+)\s*/\s*(\d+)", text)
        if fm and f is not None:
            val = int(fm.group(1))/int(fm.group(2))
            if abs(val-f) < 1e-6:
                return 1.0
    # 文字分数
    if isinstance(accepts[0], str) and "/" in accepts[0]:
        fm = re.search(r"(\d+)\s*/\s*(\d+)", text)
        if fm:
            exp = accepts[0].split("/")
            if int(fm.group(1))==int(exp[0]) and int(fm.group(2))==int(exp[1]):
                return 1.0
    return 0.0

def score_code(text, expected):
    exp = str(expected).strip()
    stripped = text.strip()
    # 直接给出数字答案
    if stripped == exp:
        return 1.0, "直接答案"
    # 文本中含期望数字(独立数字,不被其他数字粘连)
    if re.search(r"(?<![\d.])"+re.escape(exp)+r"(?![\d.])", stripped):
        return 1.0, "含期望数字"
    # 有代码块则执行比对
    code = extract_code(text)
    if code and code != stripped:
        ok, out = run_code(code)
        if ok:
            outn = out.strip()
            if outn == exp or re.search(r"(?<![\d.])"+re.escape(exp)+r"(?![\d.])", outn):
                return 1.0, out
            return 0.0, out
    return 0.0, (code if code else stripped)

def score_keyword(text, kws):
    t = text.lower()
    hit = sum(1 for k in kws if k.lower() in t)
    return hit/len(kws)

def score_cjk_count(text, target):
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    n = len(cjk)
    if n == target:
        return 100.0
    diff = abs(n-target)
    return max(0.0, 100.0 - diff*15.0)

def judge_write(question, rubric, answer):
    prompt = (f"你是严格的评分员。根据评分标准对回答打分(0-100整数)，只输出一个数字分数，不要解释。\n"
              f"问题：{question}\n评分标准：{rubric}\n回答：{answer}\n分数：")
    out, st, _ = chat_simple(JUDGE_MODEL, prompt, max_tokens=8, timeout=60, temperature=0)
    if st != 200:
        return None
    m = re.search(r"\d+", out)
    if m:
        return max(0, min(100, int(m.group(0))))
    return None

# ---------- 题库 ----------
QUESTIONS = [
    # 数学与逻辑
    {"id":"m1","dim":"math","type":"numeric","max":1024,
     "q":"计算：17 × 23 = ? 只回答数字。","accepts":[391]},
    {"id":"m2","dim":"math","type":"numeric","max":1024,
     "q":"求 1 到 100 所有整数的和。只回答数字。","accepts":[5050]},
    {"id":"m3","dim":"math","type":"numeric","max":1024,
     "q":"解方程 2x + 5 = 13，求 x 的值。只回答数字。","accepts":[4]},
    {"id":"m4","dim":"math","type":"numeric","max":1024,
     "q":"抛两枚均匀硬币，至少出现一枚正面的概率是多少？用最简分数回答，例如 3/4。","accepts":["3/4",0.75]},
    # 编程
    {"id":"c1","dim":"code","type":"code","max":1536,
     "q":"用 Python 计算并只打印：1 到 100 中所有偶数的和。","expected":"2550"},
    {"id":"c2","dim":"code","type":"code","max":1536,
     "q":"用 Python 计算并只打印：前 10 个 Fibonacci 数的最后一个数（数列从 1, 1 开始）。","expected":"55"},
    {"id":"c3","dim":"code","type":"code","max":1536,
     "q":"用 Python 计算并只打印：100 以内（含100）所有 3 的倍数之和。","expected":"1683"},
    # 系统与 Linux
    {"id":"l1","dim":"linux","type":"keyword","max":1024,
     "q":"在 Linux 终端中，用什么命令可以查看当前系统的 IP 地址？给出一个常见命令。","kws":["ip","ifconfig"]},
    {"id":"l2","dim":"linux","type":"keyword","max":1024,
     "q":"要让一个命令在后台运行、且退出终端后继续运行，通常使用什么命令或符号？（如 nohup 或 &）","kws":["nohup","&","setsid"]},
    # 知识事实
    {"id":"k1","dim":"knowledge","type":"keyword","max":1024,
     "q":"中国的首都是哪座城市？","kws":["北京"]},
    {"id":"k2","dim":"knowledge","type":"keyword","max":1024,
     "q":"光在真空中的传播速度约为多少？请给出一个常见数值或科学计数法（如 3×10^8）。","kws":["10^8","10⁸","3e8","300000000","30万","3×10"]},
    {"id":"k3","dim":"knowledge","type":"keyword","max":1024,
     "q":"《红楼梦》的作者是谁？","kws":["曹雪芹"]},
    {"id":"k4","dim":"knowledge","type":"keyword","max":1024,
     "q":"Python 中用于表示只读有序序列(元组)的内置类型名是什么？","kws":["tuple","元组"]},
    # 中文与指令
    {"id":"z1","dim":"chinese","type":"cjkcount","max":1024,"target":20,
     "q":"请用恰好 20 个汉字介绍 Ming OS（一个面向老电脑的 Linux 发行版）。只输出这 20 个汉字，不要多余内容。"},
    {"id":"z2","dim":"chinese","type":"keyword","max":1024,
     "q":"把下面的句子翻译成英文，只输出译文，不要解释：'今天天气真好'。","kws":["weather","today","good","nice"]},
    {"id":"z3","dim":"chinese","type":"judge","max":600,"rubric":"评判中文短文质量：是否有画面感、是否用了比喻、字数是否接近80字(±30)。优秀90-100，良好70-89，一般50-69，差<50。",
     "q":"写一篇约 80 字的小短文，描写夏夜海边，要求有画面感并且包含一句比喻。使用中文。"},
    {"id":"z4","dim":"chinese","type":"judge","max":600,"rubric":"评判劝说文字：语气是否亲切、是否说清备份电脑数据的重要性、字数是否接近100字(±40)。优秀90-100，良好70-89，一般50-69，差<50。",
     "q":"给你的好友写一段约 100 字的劝说，劝他定期备份电脑数据，语气要亲切。使用中文。"},
]
DIM_NAME = {"math":"数学与逻辑","code":"编程","linux":"系统与Linux","knowledge":"知识事实","chinese":"中文与指令"}
DIMS = ["math","code","linux","knowledge","chinese"]

# ---------- 续测存储 ----------
RESULT_FILE = "cap_results.jsonl"
LOG_FILE = "cap_test.log"

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE,"a",encoding="utf-8") as f:
        f.write(line+"\n")

def load_done():
    done = {}
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE,"r",encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    o=json.loads(line)
                    done[(o["model"],o["qid"])]=o
                except Exception:
                    pass
    return done

def save_result(rec):
    with open(RESULT_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(rec,ensure_ascii=False)+"\n")

# ---------- 评分单题 ----------
def score_question(q, text):
    t = q["type"]
    if t == "numeric":
        s = score_numeric(text, q["accepts"])
        return s*100.0, f"数值匹配 {s:.0%}"
    if t == "code":
        s, dbg = score_code(text, q["expected"])
        return s*100.0, dbg
    if t == "keyword":
        s = score_keyword(text, q["kws"])
        return s*100.0, f"关键词命中 {s:.0%}"
    if t == "cjkcount":
        s = score_cjk_count(text, q["target"])
        return s, f"汉字数计分"
    if t == "judge":
        s = judge_write(q["q"], q["rubric"], text)
        if s is None:
            return 0.0, "裁判失败"
        return float(s), f"裁判 {s}"
    return 0.0, "未知类型"

# ---------- 主流程 ----------
def run_model(model, questions, done):
    log(f"===== 开始模型 {model} =====")
    for q in questions:
        key=(model,q["id"])
        rec_done = done.get(key)
        if rec_done:
            st = rec_done.get("status")
            # ok 永远跳过; 网关级不可用模型(oc/*)的 unavailable 也跳过;
            # 其余模型(如 42 间歇性后端)的 unavailable 会重试, 保证可用模型结果完整
            if st == "ok" or (st == "unavailable" and model in GATEWAY_UNAVAILABLE):
                log(f"  跳过已完成 {q['id']} ({st})")
                continue
        # 重试
        for attempt in range(6):
            # 推理型模型(42/grok 等)需较大 max_tokens 才能吐出最终答案
            mt = max(q.get("max",2048), 3000)
            text, ttft, el, st, err = chat_stream(model, q["q"], max_tokens=mt,
                                                  timeout=200, temperature=0.3)
            if st == 200 and text.strip():
                sc, dbg = score_question(q, text)
                rec = {"model":model,"qid":q["id"],"dim":q["dim"],"score":round(sc,1),
                       "ttft":round(ttft,2) if ttft else None,"elapsed":el,
                       "status":"ok","detail":dbg,"answer":text[:400]}
                save_result(rec)
                log(f"  {q['id']} 得分 {sc:.0f}  TTFT {rec['ttft']}s  {dbg}")
                break
            elif st == 429 or "429" in str(err):
                wait = 45*(attempt+1)
                log(f"  {q['id']} 429 限流, 等待 {wait}s 后重试(第{attempt+1}次)")
                time.sleep(wait)
            elif st == 503 or "503" in str(err) or "model_not_found" in str(err):
                rec = {"model":model,"qid":q["id"],"dim":q["dim"],"score":None,
                       "status":"unavailable","detail":str(err)[:120]}
                save_result(rec)
                log(f"  {q['id']} 不可用(503/no channel): {err[:80]}")
                break
            elif st in (400,401) or "not supported" in str(err).lower() or "not available" in str(err).lower():
                # 42(muse-spark)/oc/* 等后端间歇性不可用: 不是限流, 快速放弃避免空耗
                if attempt < 2:
                    log(f"  {q['id']} {st} 后端暂不可用, 10s 后重试(第{attempt+1}次)")
                    time.sleep(10)
                else:
                    rec = {"model":model,"qid":q["id"],"dim":q["dim"],"score":None,
                           "status":"unavailable","detail":f"{st} {str(err)[:100]}"}
                    save_result(rec)
                    log(f"  {q['id']} 后端不可用({st}): {err[:80]}")
                    break
            else:
                wait = 10*(attempt+1)
                log(f"  {q['id']} 错误 st={st} err={err[:80]} 等待 {wait}s 重试")
                time.sleep(wait)
        else:
            rec = {"model":model,"qid":q["id"],"dim":q["dim"],"score":None,
                   "status":"failed","detail":"max retries"}
            save_result(rec)
            log(f"  {q['id']} 多次失败, 标记 failed")
        time.sleep(0.6)  # 限速节拍

def main():
    args = sys.argv[1:]
    smoke = "--smoke" in args
    models = [a for a in args if not a.startswith("--")]
    if not models:
        models = ALL_MODELS
    if smoke:
        qs = [QUESTIONS[0], QUESTIONS[4], QUESTIONS[8], QUESTIONS[10], QUESTIONS[12]]
    else:
        qs = QUESTIONS
    done = load_done()
    log(f"模型: {models}")
    log(f"题目数: {len(qs)}  已完成缓存: {len(done)}")
    for m in models:
        try:
            run_model(m, qs, done)
        except Exception as e:
            log(f"!! 模型 {m} 运行异常: {type(e).__name__} {e}  (继续下一模型)")
            continue
    log("===== 全部模型跑完, 调用报告生成 =====")
    try:
        import gen_cap_report
        gen_cap_report.build(RESULT_FILE, ALL_MODELS)
    except Exception as e:
        log(f"!! 报告生成失败: {e}")

if __name__ == "__main__":
    main()
