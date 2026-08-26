# -*- coding: utf-8 -*-
"""
中转站编程+Linux 深度能力评测 (capability_test_deep.py)
- 维度: 编程(Python 12题, 沙箱执行) / Linux命令(10题) / Bash脚本(3题, Git Bash 真实执行)
- 全客观打分, 无裁判依赖
- 特性: 流式抽取、断点续测、429/400/401/503/524 分类退避、快速失败、推理模型大 token
用法:
    python capability_test_deep.py                     # 全部6个可用模型
    python capability_test_deep.py oc/hy-3 42          # 指定模型
    python capability_test_deep.py minimax --smoke     # 冒烟
"""
import urllib.request, os, json, gzip, time, sys, re, subprocess, threading, shutil

KEY = "YOUR_RELAY_API_KEY"
BASE = "https://YOUR_RELAY.example.com/v1"
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
PY = sys.executable

# Git Bash 路径 (Windows 下需真实路径)
BASH = None
for cand in ("C:/Program Files/Git/bin/bash.exe", "C:/Program Files/Git/usr/bin/bash.exe",
             "C:/Program Files/Git/git-bash.exe"):
    if os.path.exists(cand):
        BASH = cand
        break
if BASH is None:
    BASH = shutil.which("bash") or "bash"

JUDGE_MODEL = None  # 深度测试全客观打分, 不用裁判
ALL_MODELS = ["oc/hy-3","nvidia/minimax-m3","grok-4.6","nvidia/deepseek-v4-flash-0731",
              "nvidia/nemotron-3-ultra-550b-a55b","42"]
GATEWAY_UNAVAILABLE = {"oc/big-pickle","oc/mimo-v2.5"}

# ---------- HTTP ----------
_op = None
def opener():
    global _op
    if _op is None:
        hd = urllib.request.ProxyHandler({"http":PROXY,"https":PROXY}) if PROXY else None
        _op = urllib.request.build_opener(hd) if hd else urllib.request.build_opener()
    return _op

def chat_stream(model, content, max_tokens=3000, timeout=200, temperature=0.3):
    body = json.dumps({"model":model,"messages":[{"role":"user","content":content}],
                       "max_tokens":max_tokens,"stream":True,"temperature":temperature}).encode()
    req = urllib.request.Request(BASE+"/chat/completions", data=body,
        headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","User-Agent":UA,"Accept":"text/event-stream"},
        method="POST")
    t0=time.time(); first=None; buf=[]; status=200; err=""
    try:
        r = opener().open(req, timeout=timeout)
        for raw in r:
            if raw.strip()==b"": continue
            line = raw.decode("utf-8","replace")
            if not line.startswith("data:"): continue
            payload = line[5:].strip()
            if payload=="[DONE]": break
            try: obj=json.loads(payload)
            except Exception: continue
            if "error" in obj:
                err=str(obj["error"]); status=obj.get("error",{}).get("code","err"); break
            try: d=obj["choices"][0]["delta"].get("content","")
            except Exception: d=""
            if d:
                if first is None: first=time.time()-t0
                buf.append(d)
        return ("".join(buf), (first or time.time()-t0), round(time.time()-t0,2), status, err)
    except urllib.error.HTTPError as e:
        try: b=e.read().decode("utf-8","replace")
        except Exception: b=""
        return ("", None, round(time.time()-t0,2), e.code, b[:300])
    except Exception as e:
        return ("", None, round(time.time()-t0,2), "EXC_"+type(e).__name__, str(e)[:200])

# ---------- 沙箱 ----------
DANGER = ["import os","import subprocess","__import__","eval(","exec(","open(",
          "system(","os.system","subprocess","shutil","pathlib","builtins",
          "globals(","locals(","compile(","socket","requests","urllib"]
BASH_DANGER = ["rm -rf","rm -fr","mkfs","shutdown","reboot","dd ","sudo","curl ","wget ",
               ":(){","/dev/sd","python","node ","chmod -r","chown -r","crontab -r","> /etc"]

def run_code(code):
    low=code.lower()
    for d in DANGER:
        if d in low: return (False, "unsafe:"+d)
    try:
        r=subprocess.run([PY,"-c",code],capture_output=True,text=True,timeout=10,creationflags=0x08000000)
        if r.returncode!=0: return (False, "err:"+r.stderr.strip()[:160])
        return (True, r.stdout.strip())
    except subprocess.TimeoutExpired: return (False,"timeout")
    except Exception as e: return (False,str(e)[:120])

def run_bash(code):
    low=code.lower()
    for d in BASH_DANGER:
        if d in low: return (False,"unsafe:"+d.strip())
    try:
        r=subprocess.run([BASH,"-c",code],capture_output=True,text=True,timeout=12,creationflags=0x08000000)
        # 退出码非0但仍有 stdout 时不以退出码判死(如 && 短路的循环退出码为1)
        if r.returncode!=0 and not r.stdout.strip():
            return (False,"err:"+r.stderr.strip()[:160])
        return (True,r.stdout.strip())
    except subprocess.TimeoutExpired: return (False,"timeout")
    except Exception as e: return (False,str(e)[:120])

def extract_code(text, lang=None):
    pat = r"```(?:python|bash|sh|shell)?\s*(.*?)```" if lang is None else \
          r"```(?:%s)\s*(.*?)```" % lang
    m = re.search(pat, text, re.S)
    if m: return m.group(1).strip()
    return text.strip()

# ---------- 输出匹配 ----------
def norm(s):
    return re.sub(r"\s+","",s).strip().lower()

def match_output(out, exp):
    if isinstance(exp,str): exp=[exp]
    on=norm(out)
    first = (out.strip().splitlines()[0] if out.strip() else "").strip()
    fn = norm(first)
    for e in exp:
        en=norm(e)
        if on==en: return True
        # 首行匹配: 答案以正确结果开头(允许后跟解释); 数字空格序列用 norm 归一
        if fn and fn==en: return True
        if fn and fn.startswith(en) and len(fn)>len(en) and not fn[len(en)].isalnum():
            return True
        no=re.findall(r"-?\d+",out); ne=re.findall(r"-?\d+",e)
        if no and ne and no==ne: return True
        wo=re.findall(r"[A-Za-z0-9]+",out); we=re.findall(r"[A-Za-z0-9]+",e)
        if wo and we and wo==we: return True
    return False

def score_code(text, expected, lastnum=False):
    exp=[expected] if isinstance(expected,str) else expected
    if match_output(text, exp): return 100.0, "直接答案"
    if lastnum:
        m=re.findall(r"-?\d+", text.replace(",",""))
        if m:
            last=m[-1]
            for e in exp:
                if re.fullmatch(r"-?\d+",e) and last==e:
                    return 100.0, "末位数字匹配"
    code=extract_code(text)
    if code and code.strip()!=text.strip():
        ok,out=run_code(code)
        if ok:
            if match_output(out,exp): return 100.0, "代码执行"
            return 0.0, out
        return 0.0, out
    return 0.0, (code if code else text.strip()[:80])

def score_bash(text, expected):
    exp=[expected] if isinstance(expected,str) else expected
    if match_output(text, exp): return 100.0, "直接答案"
    code=extract_code(text)
    ok,out=run_bash(code)
    if ok:
        if match_output(out,exp): return 100.0, "bash执行"
        return 0.0, out
    return 0.0, out

def score_kwany(text, kws):
    t=text.lower()
    return 100.0 if any(k.lower() in t for k in kws) else 0.0

# ---------- 深度题库 ----------
QUESTIONS = [
    # ===== 编程 Python (12) =====
    {"id":"p1","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 计算并只打印：列表 [1,3,5,7,9,11] 中数字 7 的下标。","expected":"3"},
    {"id":"p2","dim":"code","type":"code","max":1536,
     "q":"用 Python 打印字符串 'hello' 反转后的结果。","expected":"olleh"},
    {"id":"p3","dim":"code","type":"code","max":1536,
     "q":"用 Python 判断字符串 'racecar' 是否为回文，只打印 True 或 False。","expected":["True","true"]},
    {"id":"p4","dim":"code","type":"code","max":1536,
     "q":"用 Python 在 nums=[3,7,1,9] 中找出和为 10 的两个数的下标，只打印两个下标，用空格分隔（例如 0 1）。","expected":["0 1","1 0"]},
    {"id":"p5","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 计算并只打印 gcd(48,36) 的值。","expected":"12"},
    {"id":"p6","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 计算并只打印斐波那契数列第 20 项的值（数列从 1,1 开始）。","expected":"6765"},
    {"id":"p7","dim":"code","type":"code","max":1536,
     "q":"用 Python 将列表 [3,1,3,2,1] 去重并升序排序，打印结果列表。","expected":"[1,2,3]"},
    {"id":"p8","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 统计字符串 'banana' 中字母 'a' 出现的次数，只打印数字。","expected":"3"},
    {"id":"p9","dim":"code","type":"code","max":1536,
     "q":"用 Python 将列表 [5,2,9,1] 升序排序，打印结果列表。","expected":"[1,2,5,9]"},
    {"id":"p10","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 计算并只打印 5! 的值。","expected":"120"},
    {"id":"p11","dim":"code","type":"code","max":1536,"lastnum":True,
     "q":"用 Python 找出列表 [4,9,2,7] 中最大值的下标，只打印数字。","expected":"1"},
    {"id":"p12","dim":"code","type":"code","max":2048,"lastnum":True,
     "q":"下面代码有 bug，修复它使其正确计算 1+2+...+10，并只打印结果：\ndef f(n):\n    s=0\n    for i in range(n):\n        s+=i\n    return s\nprint(f(10))","expected":"55"},
    # ===== Linux 命令知识 (10) =====
    {"id":"l1","dim":"linux","type":"kwany","max":1024,
     "q":"在 Linux 中查看当前所有进程列表的命令是什么？","kws":["ps"]},
    {"id":"l2","dim":"linux","type":"kwany","max":1024,
     "q":"实时跟随查看日志文件末尾新内容的命令是什么？（如 tail 加参数）","kws":["tail -f","tail -F","tail --follow"]},
    {"id":"l3","dim":"linux","type":"kwany","max":1024,
     "q":"把文件权限修改为 rwxr-xr-x（属主可读写执行，组和其他人只读执行）的 chmod 写法是什么？","kws":["chmod 755","chmod 0755","chmod a=rwx"]},
    {"id":"l4","dim":"linux","type":"kwany","max":1024,
     "q":"systemd 下启动/停止/查看系统服务的命令前缀是什么？","kws":["systemctl"]},
    {"id":"l5","dim":"linux","type":"kwany","max":1024,
     "q":"查看磁盘分区空间使用情况的命令是什么？","kws":["df"]},
    {"id":"l6","dim":"linux","type":"kwany","max":1024,
     "q":"统计一个文件有多少行的命令是什么？","kws":["wc -l","wc -n"]},
    {"id":"l7","dim":"linux","type":"kwany","max":1024,
     "q":"在目录中递归按文本内容搜索文件（忽略大小写）的 grep 常用写法是什么？","kws":["grep -r","grep -rn","grep -ri"]},
    {"id":"l8","dim":"linux","type":"kwany","max":1024,
     "q":"把目录打包成 .tar.gz 压缩包的 tar 命令写法是什么？","kws":["tar -zcvf","tar -czvf","tar czf","tar -czf","tar -zcf"]},
    {"id":"l9","dim":"linux","type":"kwany","max":1024,
     "q":"查看本机正在监听的 TCP 端口及其进程的命令有哪些？（给一个即可）","kws":["ss -tlnp","ss -ltnp","ss -tulnp","netstat -tlnp","netstat -anp","lsof -i"]},
    {"id":"l10","dim":"linux","type":"kwany","max":1024,
     "q":"Linux 下设置定时任务（周期执行命令）的命令/服务是什么？","kws":["crontab","cron"]},
    # ===== Bash 脚本 (3, Git Bash 真实执行) =====
    {"id":"b1","dim":"bash","type":"bash","max":1536,
     "q":"写一个 bash 命令或脚本：打印 1 到 10 之间所有偶数的和。只打印结果。","expected":"30"},
    {"id":"b2","dim":"bash","type":"bash","max":1536,
     "q":"写一个 bash 命令或脚本：把字符串 'hello world' 反转后打印（注意：本环境没有 rev 命令，请不要依赖 rev，可用 bash 循环、参数展开或 awk 实现）。只打印结果。","expected":"dlrow olleh"},
    {"id":"b3","dim":"bash","type":"bash","max":1536,
     "q":"写一个 bash 命令或脚本：从 'apple banana cherry' 中找出包含 'an' 的单词并打印。只打印结果。","expected":"banana"},
]
DIM_NAME = {"code":"编程Python","linux":"Linux命令","bash":"Bash脚本"}
DIMS = ["code","linux","bash"]

# ---------- 存储 ----------
RESULT_FILE="cap_deep.jsonl"; LOG_FILE="cap_deep.log"
def log(msg):
    line=f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line,flush=True)
    with open(LOG_FILE,"a",encoding="utf-8") as f: f.write(line+"\n")

def load_done():
    done={}
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE,encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try:
                    o=json.loads(line); done[(o["model"],o["qid"])]=o
                except Exception: pass
    return done

def save_result(rec):
    with open(RESULT_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(rec,ensure_ascii=False)+"\n")

def score_question(q, text):
    t=q["type"]
    if t=="code": s,d=score_code(text,q["expected"],lastnum=q.get("lastnum",False)); return s,d
    if t=="bash": s,d=score_bash(text,q["expected"]); return s,d
    if t=="kwany": s=score_kwany(text,q["kws"]); return s, f"关键词 {s:.0f}"
    return 0.0,"未知"

def run_model(model, questions, done):
    log(f"===== 开始模型 {model} =====")
    for q in questions:
        key=(model,q["id"])
        rec_done=done.get(key)
        if rec_done:
            st=rec_done.get("status")
            if st=="ok" or (st=="unavailable" and model in GATEWAY_UNAVAILABLE):
                log(f"  跳过 {q['id']} ({st})"); continue
        for attempt in range(6):
            mt=max(q.get("max",2048),3000)
            text,ttft,el,st,err=chat_stream(model,q["q"],max_tokens=mt,timeout=200,temperature=0.3)
            if st==200 and text.strip():
                sc,dbg=score_question(q,text)
                rec={"model":model,"qid":q["id"],"dim":q["dim"],"score":round(sc,1),
                     "ttft":round(ttft,2) if ttft else None,"elapsed":el,"status":"ok",
                     "detail":dbg,"answer":text[:300]}
                save_result(rec)
                log(f"  {q['id']} 得分 {sc:.0f}  TTFT {rec['ttft']}s  {dbg}")
                break
            elif st==429 or "429" in str(err):
                wait=45*(attempt+1)
                log(f"  {q['id']} 429 限流, 等待 {wait}s 重试(第{attempt+1}次)"); time.sleep(wait)
            elif st==503 or "503" in str(err) or "model_not_found" in str(err):
                rec={"model":model,"qid":q["id"],"dim":q["dim"],"score":None,"status":"unavailable","detail":str(err)[:120]}
                save_result(rec); log(f"  {q['id']} 不可用(503/no channel): {err[:80]}"); break
            elif st in (400,401) or "not supported" in str(err).lower() or "not available" in str(err).lower():
                if attempt<2:
                    log(f"  {q['id']} {st} 后端暂不可用, 10s 后重试(第{attempt+1}次)"); time.sleep(10)
                else:
                    rec={"model":model,"qid":q["id"],"dim":q["dim"],"score":None,"status":"unavailable","detail":f"{st} {str(err)[:100]}"}
                    save_result(rec); log(f"  {q['id']} 后端不可用({st}): {err[:80]}"); break
            else:
                wait=10*(attempt+1)
                log(f"  {q['id']} 错误 st={st} err={err[:80]} 等待 {wait}s 重试"); time.sleep(wait)
        else:
            rec={"model":model,"qid":q["id"],"dim":q["dim"],"score":None,"status":"failed","detail":"max retries"}
            save_result(rec); log(f"  {q['id']} 多次失败, 标记 failed")
        time.sleep(0.6)

def main():
    args=sys.argv[1:]
    smoke="--smoke" in args
    models=[a for a in args if not a.startswith("--")]
    if not models: models=ALL_MODELS
    if smoke:
        qs=[QUESTIONS[0],QUESTIONS[12],QUESTIONS[22]]
    else:
        qs=QUESTIONS
    done=load_done()
    log(f"模型: {models}  题目: {len(qs)}  缓存: {len(done)}  bash={BASH}")
    for m in models:
        try: run_model(m,qs,done)
        except Exception as e:
            log(f"!! 模型 {m} 异常: {type(e).__name__} {e} 继续下一模型"); continue
    log("===== 全部跑完, 生成深度报告 =====")
    try:
        import gen_cap_report_deep
        gen_cap_report_deep.build(RESULT_FILE, ALL_MODELS)
    except Exception as e:
        log(f"!! 报告生成失败: {e}")

if __name__=="__main__":
    main()
