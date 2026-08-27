# -*- coding: utf-8 -*-
"""
capability_test_final.py —— 最终 80 题 / 150 分评测执行器
数据源: final80_qs.json (唯一), 自建题判分器: self_bank_final.py
用法:
  python capability_test_final.py [model ...] [--smoke] [--limit N]
特性: 流式/断点续测(final80_results.jsonl)/(model,qid)去重/429退避/503快速失败/推理模型大token
"""
import urllib.request, os, json, gzip, time, sys, re, subprocess, shutil, ast, tempfile

KEY = os.environ.get("RELAY_KEY", "YOUR_RELAY_API_KEY")
BASE = os.environ.get("RELAY_BASE", "https://YOUR_RELAY.example.com/v1")
# 裁判(judge)独立通道: 默认跟随被测通道; 跨通道评测时用 JUDGE_BASE/JUDGE_KEY 指定
# (如 gpuhome 跑模型 + de5 跑裁判, 因 gpuhome 无 ministral-8b-latest)
JUDGE_BASE = os.environ.get("JUDGE_BASE", BASE)
JUDGE_KEY = os.environ.get("JUDGE_KEY", KEY)
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
PY = "sys.executable"
BASH = None
for cand in ("C:/Program Files/Git/bin/bash.exe", "C:/Program Files/Git/usr/bin/bash.exe", "C:/Program Files/Git/git-bash.exe"):
    if os.path.exists(cand): BASH = cand; break
if BASH is None: BASH = shutil.which("bash") or "bash"
JUDGE = "ministral-8b-latest"
HERE = os.path.dirname(os.path.abspath(__file__))
QFILE = os.path.join(HERE, "final80_qs.json")
RESULT_FILE = os.path.join(HERE, "final80_results.jsonl")
LOG_FILE = os.path.join(HERE, "final80_test.log")

ALL_MODELS = ["oc/hy-3", "nvidia/minimax-m3", "nvidia/deepseek-v4-flash-0731", "gpt-4.1",
              "anthropic/claude-sonnet-4.6", "gpt-4o", "gpt-oss-120b", "gemini-3.1-pro-preview",
              "grok-4.6", "grok-chat-fast", "kimi-k3", "mimo-v2.5",
              "nvidia/nemotron-3-ultra-550b-a55b", "qwen3.8-max", "stealth/ox-alpha", "42"]
SMOKE_IDS = ["P01", "OB-C1", "OB-K1", "MH1", "SW1"]

# 统一思考强度(公平对比): 所有支持 reasoning_effort 的模型一律 high, 保证评测口径一致
REASONING_EFFORT = os.environ.get("REASONING_EFFORT", "high")

def _mk_body(model, content, max_tokens, temperature, stream, with_reasoning=True):
    b = {"model": model, "messages": [{"role": "user", "content": content}],
         "max_tokens": max_tokens, "stream": stream, "temperature": temperature}
    if with_reasoning and REASONING_EFFORT:
        b["reasoning_effort"] = REASONING_EFFORT
    return json.dumps(b).encode()

def _reasoning_unsupported(err_text):
    """400 错误信息是否指向 reasoning_effort 参数不支持(而非其他 400)。"""
    e = (err_text or "").lower()
    return any(k in e for k in ("reasoning_effort", "reasoning effort", "unknown parameter",
                                "unknown argument", "unsupported parameter", "not supported",
                                "invalid parameter", "unknown field"))

import self_bank_final as SBF

_op = None
def opener():
    global _op
    if _op is None:
        hd = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}) if PROXY else None
        _op = urllib.request.build_opener(hd) if hd else urllib.request.build_opener()
    return _op

def chat_stream(model, content, max_tokens=4000, timeout=300, temperature=0.3):
    def _stream(body):
        req = urllib.request.Request(BASE + "/chat/completions", data=body,
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                     "User-Agent": UA, "Accept": "text/event-stream"}, method="POST")
        t0 = time.time(); first = None; buf = []; status = 200; err = ""
        try:
            r = opener().open(req, timeout=timeout)
            for raw in r:
                if raw.strip() == b"": continue
                line = raw.decode("utf-8", "replace")
                if not line.startswith("data:"): continue
                p = line[5:].strip()
                if p == "[DONE]": break
                try: obj = json.loads(p)
                except Exception: continue
                if "error" in obj:
                    err = str(obj["error"]); status = obj.get("error", {}).get("code", "err"); break
                try: d = obj["choices"][0]["delta"].get("content", "")
                except Exception: d = ""
                if d:
                    if first is None: first = time.time() - t0
                    buf.append(d)
            return ("".join(buf), (first or time.time() - t0), round(time.time() - t0, 2), status, err)
        except urllib.error.HTTPError as e:
            try: b = e.read().decode("utf-8", "replace")
            except Exception: b = ""
            return ("", None, round(time.time() - t0, 2), e.code, b[:300])
        except Exception as e:
            return ("", None, round(time.time() - t0, 2), "EXC_" + type(e).__name__, str(e)[:200])
    body = _mk_body(model, content, max_tokens, temperature, True)
    out, ttft, el, st, err = _stream(body)
    # 400 且指向 reasoning_effort 不支持 → 降级去掉该参数重试一次(其余模型仍统一 high)
    if st == 400 and _reasoning_unsupported(err):
        out2, ttft2, el2, st2, err2 = _stream(_mk_body(model, content, max_tokens, temperature, True, with_reasoning=False))
        if st2 == 200:
            return out2, ttft2, el2, 200, err2 or "no-reasoning_effort"
    return out, ttft, el, st, err

def chat_simple(model, content, max_tokens=10, timeout=60, temperature=0, base=BASE, key=KEY):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": content}],
                       "max_tokens": max_tokens, "stream": False, "temperature": temperature}).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": UA, "Accept": "application/json"}, method="POST")
    try:
        r = opener().open(req, timeout=timeout); data = r.read()
        if "gzip" in r.headers.get("Content-Encoding", "").lower(): data = gzip.decompress(data)
        obj = json.loads(data)
        return obj["choices"][0]["message"]["content"].strip(), 200
    except urllib.error.HTTPError as e:
        return "", e.code
    except Exception:
        return "", 500

# ---------------- 安全执行 ----------------
CODE_DANGER = ["os.system", "subprocess", "__import__", "socket", "requests",
               "urllib", "ctypes", "win32", "globals(", "builtins"]
BASH_DANGER = ["rm -rf", "rm -fr", "mkfs", "shutdown", "reboot", "dd ", "sudo", "curl ", "wget ",
               ":(){", "/dev/sd", "chmod -r", "chown -r", "crontab -r", "> /etc", "kill -9"]

def run_code(code, timeout=15):
    low = code.lower()
    for d in CODE_DANGER:
        if d in low: return (False, "unsafe:" + d)
    try:
        r = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=timeout,
                           creationflags=0x08000000, cwd=tempfile.gettempdir())
        if r.returncode != 0: return (False, "err:" + r.stderr.strip()[:200])
        return (True, r.stdout.strip())
    except subprocess.TimeoutExpired: return (False, "timeout")
    except Exception as e: return (False, str(e)[:120])

def run_bash(code, timeout=15, cwd=None):
    # 剥离 markdown 代码围栏(模型常包裹 ```bash ... ```)
    m = re.search(r"```(?:bash|sh|shell|python|py)?\s*(.*?)```", code, re.S)
    if m: code = m.group(1).strip()
    else: code = code.strip()
    low = code.lower()
    for d in BASH_DANGER:
        if d in low: return (False, "unsafe:" + d.strip())
    try:
        r = subprocess.run([BASH, "-c", code], capture_output=True, text=True, timeout=timeout,
                           creationflags=0x08000000, cwd=cwd or tempfile.gettempdir())
        if r.returncode != 0 and not r.stdout.strip(): return (False, "err:" + r.stderr.strip()[:200])
        return (True, r.stdout.strip())
    except subprocess.TimeoutExpired: return (False, "timeout")
    except Exception as e: return (False, str(e)[:120])

def extract_code(text):
    m = re.search(r"```(?:python|py|bash|sh|shell|diff)?\s*(.*?)```", text, re.S)
    return m.group(1).strip() if m else text.strip()

def judge_call(question, rubric, answer):
    prompt = ("你是严格的评分员。根据评分标准对回答打分(0-100整数)，只输出一个数字分数，不要解释。\n"
              f"题目：{question}\n评分标准：{rubric}\n回答：{answer}\n分数：")
    out, st = chat_simple(JUDGE, prompt, max_tokens=8, temperature=0, base=JUDGE_BASE, key=JUDGE_KEY)
    if st != 200: return None, "judge-fail"
    m = re.search(r"\d+", out)
    if m: return max(0, min(100, int(m.group(0)))), "judge"
    return None, "judge-num"

# L01/L02 fixture
def mkfixture_l01():
    d = tempfile.mkdtemp()
    import random
    names = ["a.log", "b.log", "has space.log", "weird#&.log", "quote'x.log", "-dash.log",
             "sub", "sub/c.log", ".git", ".git/head.log"]
    total = 0
    for i, n in enumerate(names[:6]):
        with open(os.path.join(d, n), "w", encoding="utf-8") as f:
            f.write("line1\nline2\n" + "x\n" * (i % 3))
        total += 2 + (i % 3)
    os.makedirs(os.path.join(d, "sub"))
    with open(os.path.join(d, "sub/c.log"), "w") as f: f.write("one\ntwo\nthree\n")
    total += 3
    os.makedirs(os.path.join(d, ".git"))
    with open(os.path.join(d, ".git/head.log"), "w") as f: f.write("hidden\n")
    return {"dir": d, "expected": total}

def mkfixture_l02():
    import random
    d = tempfile.mkdtemp()
    rows = []
    paths = ["/a", "/b", "/a", "/b", "/a"]
    for i, p in enumerate(paths):
        st = 200 if i % 3 else 500
        rows.append(f"2026-01-01T00:00:0{i}\t{st}\t{10 + i * 20}\t{p}")
    rows.append("2026-01-01T00:00:05\t503\t500\t/b")
    f = os.path.join(d, "acc.tsv")
    with open(f, "w") as fh: fh.write("\n".join(rows) + "\n")
    # 期望: 每 path 请求数、5xx 数、p99, 按 5xx 降序
    # /b: 3 请求 2 个 5xx (503,500); /a: 3 请求 1 个 5xx
    return {"dir": d, "file": f, "expected": ("/b", 3, 2)}

# ---------------- 判分分发 ----------------
def grade_question(q, text, env):
    t = q["type"]; src = q["src"]
    if t == "self":
        g = SBF.GRADERS.get(q["qid"])
        if not g: return 0.0, "no-grader"
        return g(text, env)
    if src.startswith("OpenBench/HumanEval") or (t == "code"):
        return grade_humaneval(q, text, env)
    if t == "choice":
        return grade_choice(q, text)
    if t == "exact":
        return grade_exact(q, text)
    if t == "num":
        return grade_num(q, text)
    if t == "math":
        return grade_math(q, text)
    if t == "swe":
        return grade_swe(q, text)
    return 0.0, "unknown-type"

def grade_humaneval(q, text, env):
    code = extract_code(text)
    entry = q.get("entry_point") or ""
    test = q.get("test") or ""
    if not entry or not test:
        return 0.0, "no-test"
    low = code.lower()
    for d in CODE_DANGER:
        if d in low: return 0.0, "unsafe:" + d
    ns = {}
    try:
        exec(code, ns)
        cand = ns.get(entry)
        if cand is None: return 0.0, "entry-not-found"
        ns2 = dict(ns); ns2["candidate"] = cand; ns2["__name__"] = "__main__"
        exec(test, ns2)  # 定义官方 check(candidate)
        check = ns2.get("check")
        if check is None: return 0.0, "no-check"
        # 真正执行官方 check(candidate): 全部断言通过返回 None, 否则抛 AssertionError
        # (旧实现只提取 1 个 assert 节点并 eval, 缺循环局部变量导致正确解也 0 分, 见坑位 17)
        try:
            check(cand)
            return 100.0, "check-pass"
        except AssertionError:
            return 0.0, "check-fail"
        except Exception as e:
            return 0.0, "check-err:" + str(e)[:100]
    except Exception as e:
        return 0.0, "exec-err:" + str(e)[:100]

def grade_choice(q, text):
    key = q.get("answer_key") or ""
    if not key: return 0.0, "no-key"
    # 优先级: "Answer: X"/"答案是 X"/"选X"/"选项X" > 行首独立字母 > 正文最后一个独立 A-J 字母
    low = text.strip()
    for p in (r"[Aa]nswer\s*[:：]\s*([A-Ja-j])",
              r"答案\s*[是为:：]\s*([A-Ja-j])",
              r"(?:选|选择|选项)\s*[（(]?\s*([A-Ja-j])[）)]?"):
        m = re.search(p, text)
        if m:
            return (100.0, "choice") if m.group(1).upper() == key else (0.0, "wrong:" + m.group(1))
    m = re.search(r"^[（(]?\s*([A-Ja-j])[）).:：]?\s*$", low.splitlines()[0] if low.splitlines() else "", re.M)
    if not m:
        lines = [ln.strip() for ln in low.splitlines() if ln.strip()]
        for ln in lines[:5]:
            mm = re.match(r"^[（(]?([A-Ja-j])[）).:：]?\s*\S", ln)
            if mm: m = mm; break
    if not m:
        # 兜底: 取正文最后一个独立 A-J 字母(答案通常在结尾, 避免抓到开头闲谈里的孤立字母)
        ms = list(re.finditer(r"\b([A-Ja-j])\b", text))
        if ms: m = ms[-1]
    if m:
        return (100.0, "choice") if m.group(1).upper() == key else (0.0, "wrong:" + m.group(1))
    return 0.0, "no-letter"

def grade_exact(q, text):
    """BBH 短答案精确匹配(独立词/串, 不区分大小写): Yes/No/词/短语。"""
    exp = str(q.get("expected") or "").strip()
    if not exp:
        return 0.0, "no-expected"
    low = text.lower()
    target = exp.lower()
    if re.search(rf"\b{re.escape(target)}\b", low):
        return 100.0, "exact"
    return 0.0, "exp=" + exp[:30]

def grade_num(q, text):
    exp = str(q.get("expected") or "").strip()
    nums = re.findall(r"\d+", text)
    if nums:
        last = nums[-1]
        if last == exp: return 100.0, "num-match"
        # 允许前导零
        if str(int(last)) == str(int(exp)) if exp.isdigit() and last.isdigit() else False:
            return 100.0, "num-int"
    return 0.0, "exp=" + exp

def norm_math(s):
    s = s.replace("\\left", "").replace("\\right", "").replace("\\,", "").replace(" ", "")
    s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", s)
    s = re.sub(r"\\dfrac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = s.replace("\\pm", "+-").replace("\\infty", "inf").replace("\\times", "*")
    s = s.replace("\\,", "").replace("_", "")
    return s

def safe_math_value(s):
    """尝试把归一化后的数学表达式求值为数值(仅限纯数值表达式)。"""
    import math as _m
    src = s.replace("sqrt(", "math.sqrt(").replace("^", "**")
    try:
        ns = {"math": _m, "__builtins__": {}}
        v = eval(src, ns)
        if isinstance(v, (int, float)):
            return float(v)
    except Exception:
        pass
    return None

def grade_math(q, text):
    exp = norm_math(str(q.get("expected") or ""))
    blocks = re.findall(r"```(?:latex|text)?\s*(.*?)```", text, re.S)
    ans_part = blocks[-1].strip() if blocks else text.strip()
    # 剥离 $$ 或 \[ \] 包裹
    m = re.search(r"\$\$(.*?)\$\$", ans_part, re.S)
    if m: ans_part = m.group(1)
    m = re.search(r"\\\[(.*?)\\\]", ans_part, re.S)
    if m: ans_part = m.group(1)
    got = norm_math(ans_part)
    if got and got == exp: return 100.0, "norm-match"
    # 纯数值 expected: 计算期望数值并与模型答案中的数字比较
    ev = safe_math_value(exp)
    if ev is not None:
        nums = re.findall(r"-?\d+\.?\d*", got)
        if nums:
            for n in nums:
                try:
                    if abs(float(n) - ev) < 1e-6 or (abs(ev) > 1e-9 and abs(float(n) - ev) / abs(ev) < 0.01):
                        return 100.0, "num-eval"
                except Exception:
                    pass
    # 分数/根式等包含匹配
    if exp and (exp in got or got in exp):
        return 80.0, "contain"
    return 0.0, "exp=" + str(q.get("expected"))[:40]

def grade_swe(q, text):
    # 提取 diff 块
    patch = ""
    blocks = re.findall(r"```(?:diff|patch)?\s*(.*?)```", text, re.S)
    for b in blocks:
        if "diff --git" in b or ("+++" in b and "---" in b):
            patch = b; break
    if not patch and "diff --git" in text:
        patch = text
    if not patch:
        patch = " ".join(blocks)
    files = set(re.findall(r"diff --git a/(\S+?)(?:\s|$)", patch))
    files |= set(re.findall(r"^---\s+a/(\S+)", patch, re.M))
    funcs = set(re.findall(r"(?:^|\n)\s*[+-]?\s*(?:def|class)\s+([A-Za-z_]\w*)", patch))
    gold_files = set(q.get("gold_files") or [])
    gold_funcs = set(q.get("gold_funcs") or [])
    f_hit = len(files & gold_files) / max(1, len(gold_files))
    fn_hit = len(funcs & gold_funcs) / max(1, len(gold_funcs))
    struct = 1.0 if ("+" in patch and "-" in patch and len(patch) > 80) else (0.5 if len(patch) > 40 else 0.0)
    score = 50 * f_hit + 30 * fn_hit + 20 * struct
    return round(score, 1), "files:%d/%d funcs:%d/%d" % (len(files & gold_files), len(gold_files), len(funcs & gold_funcs), len(gold_funcs))

# ---------------- 运行环境 ----------------
def build_env():
    env = {
        "code": run_code,
        "bash": run_bash,
        "judge": judge_call,
        "mkfixture_l01": mkfixture_l01,
        "mkfixture_l02": mkfixture_l02,
    }
    return env

# ---------------- 调度 ----------------
def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(line + "\n")

def load_done():
    done = {}
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    o = json.loads(line); done[(o["model"], o["qid"])] = o
                except Exception: pass
    return done

def save_result(rec):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def build_prompt(q):
    if q["type"] == "self":
        return SBF.PROMPTS.get(q["qid"], q["question"])
    if q["type"] == "swe":
        return (f"你是资深工程师。请修复下面这个真实仓库 issue。\n仓库: {q.get('repo')}  "
                f"实例: {q.get('title')}\n\n问题描述:\n{q['question']}\n\n"
                f"必须通过的测试: {q.get('fail_to_pass')}\n"
                f"回归测试: {q.get('pass_to_pass')}\n\n"
                f"请只输出一个完整 diff patch（含 diff --git 头部），定位到正确的文件和函数。")
    if q["type"] == "choice":
        opts = "\n".join(f"{L}. {t}" for L, t in (q.get("options") or []))
        return f"{q['question']}\n\n{opts}\n\n只回答选项字母（如 A）。"
    if q["type"] == "num":
        return f"{q['question']}\n\n只回答数字（000-999 三位整数格式，如前导零保留）。"
    if q["type"] == "math":
        return f"{q['question']}\n\n只输出最终答案（可用 LaTeX 或普通文本）。"
    if q["type"] == "code":
        return f"补全以下 Python 函数，只输出完整可运行的代码（含 import 和函数定义），不要解释：\n\n{q['question']}"
    return q["question"]

def run_model(model, questions, done, env, smoke=False):
    log(f"===== 开始模型 {model} =====")
    for q in questions:
        key = (model, q["qid"]); rd = done.get(key)
        if rd:
            st = rd.get("status")
            if st == "ok":
                log(f"  跳过 {q['qid']} (ok {rd.get('score')})"); continue
        for attempt in range(6):
            mt = max(q.get("max", 4000), 4000)  # 统一高思考强度: 推理预算下限 4000
            prompt = build_prompt(q)
            text, ttft, el, st, err = chat_stream(model, prompt, max_tokens=mt, timeout=300, temperature=0.0)
            if st == 200 and text.strip():
                try:
                    score, detail = grade_question(q, text, env)
                except Exception as e:
                    rec = {"model": model, "qid": q["qid"], "src": q["src"], "lvl": q.get("lvl", ""),
                           "score": None, "status": "grade_error",
                           "detail": f"grader-exc:{type(e).__name__}:{str(e)[:120]}"}
                    save_result(rec); log(f"  {q['qid']} 判分异常 {type(e).__name__}: {e}"); break
                rec = {"model": model, "qid": q["qid"], "src": q["src"], "lvl": q.get("lvl", ""),
                       "score": round(score, 1), "ttft": round(ttft, 2) if ttft else None,
                       "elapsed": el, "status": "ok", "detail": detail, "answer": text[:4000],
                       "reasoning": REASONING_EFFORT or None}
                save_result(rec); log(f"  {q['qid']}({q.get('lvl','')}) 得分 {score:.1f}  {detail}")
                break
            elif st == 429 or "429" in str(err):
                wait = 45 * (attempt + 1); log(f"  {q['qid']} 429, 等待 {wait}s"); time.sleep(wait)
            elif st == 402 or "402" in str(err) or "Insufficient Balance" in str(err) or "insufficient" in str(err).lower():
                if attempt < 2:
                    log(f"  {q['qid']} 402 余额瞬时错误, 30s 重试({attempt+1})"); time.sleep(30)
                else:
                    rec = {"model": model, "qid": q["qid"], "src": q["src"], "lvl": q.get("lvl", ""),
                           "score": None, "status": "unavailable", "detail": f"402 {str(err)[:100]}"}
                    save_result(rec); log(f"  {q['qid']} 余额不足(402): {err[:80]}"); break
            elif st == 503 or "503" in str(err) or "model_not_found" in str(err) or "No available channel" in str(err):
                rec = {"model": model, "qid": q["qid"], "src": q["src"], "lvl": q.get("lvl", ""),
                       "score": None, "status": "unavailable", "detail": str(err)[:120]}
                save_result(rec); log(f"  {q['qid']} 不可用(503): {err[:80]}"); break
            elif st in (400, 401) or "not supported" in str(err).lower() or "not available" in str(err).lower() or "exhausted" in str(err).lower():
                if attempt < 2:
                    log(f"  {q['qid']} {st} 后端暂不可用, 10s 重试"); time.sleep(10)
                else:
                    rec = {"model": model, "qid": q["qid"], "src": q["src"], "lvl": q.get("lvl", ""),
                           "score": None, "status": "unavailable", "detail": f"{st} {str(err)[:100]}"}
                    save_result(rec); log(f"  {q['qid']} 后端不可用({st}): {err[:80]}"); break
            else:
                wait = 10 * (attempt + 1); log(f"  {q['qid']} 错误 st={st} err={err[:80]} 等待 {wait}s"); time.sleep(wait)
    log(f"===== 完成模型 {model} =====")

def main():
    args = sys.argv[1:]
    models = [a for a in args if not a.startswith("--")]
    smoke = "--smoke" in args
    limit = None
    if "--limit" in args:
        try: limit = int(args[args.index("--limit") + 1])
        except Exception: pass
    if not models:
        models = ALL_MODELS
    data = json.load(open(QFILE, encoding="utf-8"))
    questions = data["questions"]
    if smoke:
        questions = [q for q in questions if q["qid"] in SMOKE_IDS]
        log(f"冒烟模式: {len(questions)} 题/模型")
    if limit:
        questions = questions[:limit]
    done = load_done()
    env = build_env()
    for m in models:
        run_model(m, questions, done, env, smoke)
    # 汇总
    agg = {}
    for m in models:
        rows = [o for o in done.values() if o.get("model") == m and o.get("status") == "ok"]
        if not rows: continue
        total = sum(o["score"] for o in rows)
        agg[m] = (len(rows), round(total, 1))
    log("===== 本轮汇总 (只含已成功题目) =====")
    for m, (n, s) in sorted(agg.items(), key=lambda x: -x[1][1]):
        log(f"  {m}: {n} 题 得分 {s}")

if __name__ == "__main__":
    main()
