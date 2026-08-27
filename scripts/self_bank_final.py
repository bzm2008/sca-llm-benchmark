# -*- coding: utf-8 -*-
"""
自建工程题 32 题: 完整题面(PROMPTS) + 判分器(GRADERS)
判分器统一签名: def grade(code_or_text, run) -> (score0_100, detail)
run: 由执行器注入的可执行环境 (run_code/run_bash/judge)
"""
import re

# ---------------- 工具: 把模型代码转成模块并跑测试 ----------------
def make_runner(run):
    """run: {'code': fn(code,timeout), 'bash': fn(code,timeout), 'judge': fn(q,rubric,ans)}"""
    return run

# ---------------- 题面 ----------------
PROMPTS = {
"P01": """实现函数 parse_size(text: str) -> int，把容量字符串转换为字节数。
规则：大小写不敏感（B/KB/KiB/MB/MiB/GB/GiB 均合法）；允许前后空格；KB=1000, KiB=1024, MB=10^6, MiB=2^20, GB=10^9, GiB=2^30；
数字可以是整数或小数，结果四舍五入到整数（round-half-to-even 或 round-half-up 均可）。
非法输入（空串、纯空白、负数、未知单位、多余数字字符）必须抛出 ValueError。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P02": """实现 stable_unique(items) -> list：删除重复元素但保留第一次出现的顺序。
元素可能是整数、字符串、元组，也可能是不可哈希的嵌套列表或嵌套字典。
字典比较按键值内容（键顺序无关）；嵌套结构按内容深比较。不能把元素强制转成字符串。
输入为空时返回空列表。不要修改传入的列表。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P03": """实现 top_k_counts(words: list[str], k: int) -> list[tuple[str,int]]：返回出现次数最多的前 k 个单词（词频降序）。
大小写不敏感（"Apple" 与 "apple" 同词）；输出单词使用该词第一次出现时的拼写；
词频相同时按第一次出现的位置升序。k<=0 返回空列表。不要用 Counter.most_common 的隐含并列顺序。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P04": """实现 merge_intervals(intervals) -> list[tuple[int,int]]：合并闭区间 [start,end]。
输入可以无序、允许重复和负数；start>end 必须抛出 ValueError；
相邻区间 [1,2] 与 [3,4] 不合并（合并条件为 next_start <= current_end）。
不得修改调用者传入的列表。只输出完整 Python 代码（含函数定义），不要解释。""",

"P05": """实现 parse_jsonl_metrics(lines: list[str]) -> dict。
逐行解析 JSONL：忽略空行；非法 JSON 计入 invalid；合法记录必须含字符串 service、数值 latency_ms、数值 status，缺字段或类型错误计入 invalid。
返回 {"invalid": N, "<service>": {"count": n, "ok_rate": r, "p95_latency_ms": v}, ...}，键按服务名排序。
ok_rate = 200<=status<300 的比例（0-1 浮点）；p95 定义为排序后下标 ceil(0.95*n)-1 处的值（n 为该服务样本数，n=0 时 p95=None），不使用插值。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P06": """实现 dependency_plan(nodes: list[str], edges: list[tuple[str,str]]) -> list[str]：对任务依赖图拓扑排序。
edges 中 (a,b) 表示 a 必须先于 b；有多个可选节点时取字典序最小者；重复边去重。
存在环时抛出 CycleError（需要自定义异常类），异常对象必须带 cycle 属性，为一条实际环路（首尾节点相同）。
输入含未知节点（不在 nodes 中）时抛 ValueError；自环视为环。
只输出完整 Python 代码（含函数定义和异常类），不要解释。""",

"P07": """实现 streaming_group_sum(rows) -> 可迭代对象：处理只能遍历一次的输入流。
每行 (timestamp, key, value)；按 key 汇总 value，按 key 首次出现顺序产出 (key, total)。
不得把 rows 转成列表缓存；value 可为 int/float；格式错误行或 value 非数值的行跳过，并计入对象属性 invalid_count。
返回对象必须是可迭代（list(g) 能得到结果），且调用方可在迭代后读取 g.invalid_count。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P08": """实现 retry_call(fn, attempts, retry_if, *, base_delay=0.01, sleep=time.sleep)。
调用 fn() 抛异常时：retry_if(exception) 为真且还有次数则重试，否则立即抛出；
最终失败抛最后一次异常；attempts 必须 >0 否则抛 ValueError。
退避：第 n 次重试前等待 base_delay * 2**(n-1)。sleep 参数可注入用于测试，不得真实长时间等待。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P09": """实现 apply_patch_ops(document: dict, operations) -> dict：对嵌套字典执行事务式更新。
operations 为 (op, path, value) 三元组列表，path 形如 "user.profile.age"（点分路径）。
op 支持：set（设值）、delete（删除，不存在路径不报错）、increment（只接受 int/float，路径值必须是数值）。
要求：深拷贝输入，不得原地修改调用者文档；任一步失败时整体回滚并抛出异常（不返回部分结果）；
成功后返回新文档。只输出完整 Python 代码（含函数定义），不要解释。""",

"P10": """实现线程安全缓存 TTLCache(maxsize: int, ttl: float, *, clock=time.time)。
接口：get(key, default=None)、set(key, value)、delete(key)、__len__()。
- 同一 key 的 TTL 从最后一次成功 set 开始计算；过期读取返回 default 并删除条目；
- 超过 maxsize 时淘汰最近最少使用（LRU）且未过期的条目；
- 所有公共方法必须可被多线程同时安全调用；不得在锁内执行用户回调；
- get 命中会更新 LRU 顺序；clock 可注入用于测试。
只输出完整 Python 代码（含类定义），不要解释。""",

"P11": """实现 SingleFlightTTLCache，接口同 TTLCache（get/set/delete/__len__），并增加 get_or_load(key, loader)。
get_or_load：缓存未命中时，同一 key 同时只允许一个线程执行 loader，其他线程等待并共享其结果；
loader 抛异常时所有等待者收到同一异常，失败结果不得写入缓存；不同 key 可并行加载；
等待者被唤醒后不得重复执行 loader。线程安全。只输出完整 Python 代码（含类定义），不要解释。""",

"P12": """实现异步函数 run_with_deadline(coros, limit: int, timeout: float)。
- 最多同时运行 limit 个协程，某个完成（成功或失败）后调度下一个；
- 整体达到 timeout 后取消所有未完成任务；
- 返回按原始输入顺序排列的结果列表，每项为 (status, value/error) 其中 status in {"ok","error","cancelled"}；
- 已完成任务不得误标 cancelled；必须 await 或显式回收创建过的任务，不留 pending 警告。
只输出完整 Python 代码（含函数定义），不要解释。""",

"P13": """实现线程安全 IdempotentEventProcessor，接口 process(event_id, payload) 和 result(event_id)。
- 同一 event_id 重复调用必须只产生一次副作用（副作用为注入的 apply(payload) 回调，可能成功/抛异常/耗时）；
- 并发重复调用必须返回同一结果；处理失败允许后续重试，失败不得永久占用 event_id；
- 不同 event_id 可并行；result(event_id) 返回已成功事件的结果，未成功抛 KeyError；
- 避免死锁。只输出完整 Python 代码（含类定义），不要解释。""",

"P14": """下面的 BoundedQueue 实现有多个并发 bug，请修复后只返回完整修复版实现（可改动类内部实现，不改接口）：

```python
class BoundedQueue:
    def __init__(self, capacity):
        self._q = []           # NOT thread-safe
        self._cap = capacity

    def put(self, item):
        while len(self._q) >= self._cap:
            time.sleep(0.001)  # busy-wait, 会死锁/漏唤醒
        self._q.append(item)

    def get(self):
        while len(self._q) == 0:
            time.sleep(0.001)
        return self._q.pop(0)

    def close(self):
        self._closed = True    # 竞态: 与 put/get 检查不同步
```

要求：多生产者/多消费者安全；满时 put 阻塞、空时 get 阻塞；close() 后唤醒所有阻塞的 put/get；
close 后 put 抛异常、已入队元素仍可被 get 取完；close 重复调用幂等；异常不得永久持锁；禁止 busy-wait。
只输出完整 Python 代码（含类定义），不要解释。""",

"P15": """实现线程安全 VersionedStore：read(key)、compare_and_set(key, expected_version, value) -> bool、
delete(key, expected_version) -> bool、snapshot() -> dict。
- 每次成功写（CAS 成功/delete 成功）该 key 版本号 +1；
- CAS 时 expected_version 不匹配则返回 False 且不改变数据；
- snapshot() 返回某个一致时刻的完整深拷贝视图（不能是部分更新的中间态）；
- 读操作不得返回被并发写破坏的结构；值可为嵌套可变对象，调用方不能通过返回值反向修改存储。
只输出完整 Python 代码（含类定义），不要解释。""",

"P16": """用纯 Python 标准库实现可恢复任务队列 DurableTaskQueue：
submit(task_id, payload)、claim(worker_id, lease_seconds) -> (task_id,payload)|None、
ack(task_id, worker_id)、fail(task_id, worker_id)、recover(now)、pending_count()。
- task_id 幂等提交（重复 submit 不生成重复任务）；claim 返回租约，租约过期任务可被其他 worker 重新领取；
- 只有当前租约持有者能 ack/fail，旧 worker 迟到 ack 不得确认新租约；
- 状态必须持久化到本地 SQLite 或 append-only WAL 文件，进程重启（重新实例化同一文件）后任务与状态完整恢复；
- recover(now) 可重复执行，不得产生重复任务；代码内注释说明 crash 在"写入前/写入后/返回前"三种窗口的行为。
只输出完整 Python 代码（含类定义），不要解释。""",

"P17": """实现简化复制日志状态机 ReplicatedLog（单进程可测，不要求网络/选举）：
append(command) -> index、receive_append(term, prev_index, prev_term, entries, leader_commit)、
commit_to(index)、apply_committed() -> list[command]、current_index()、current_term()。
- term 不匹配时 receive_append 返回 False 并给出冲突位置；匹配后覆盖冲突 suffix；
- commit 不能超过本地最后一项；已 apply 的 index 不得回退；
- 重复接收相同 entries 必须幂等；apply_committed 返回按序新提交的命令，幂等可重入。
最后用注释列出 5 条最能暴露错误的测试用例。只输出完整 Python 代码（含类定义），不要解释。""",

"P18": """下面的 HTTP 风格任务服务伪实现存在至少 8 类问题（并发竞态、重试重复副作用、超时未取消、
异常吞掉、队列无限增长、缓存未过期、日志泄露 token、关闭丢任务）。请输出：
1) 修复后的核心代码（完整可运行或最小实现）；
2) 按严重性列出发现的问题：触发条件与修复理由；
3) 一组覆盖正常/超时/重试/重复请求/关闭/恢复的测试计划。

```python
tasks = {}
cache = {}
queue = []
running = False

def handle(payload):
    global running
    try:
        if payload["id"] in cache:
            return cache[payload["id"]]
        queue.append(payload)
        if not running:
            running = True
            while queue:
                p = queue.pop(0)
                r = do_work(p)
                cache[p["id"]] = r          # 无限增长
                print("DEBUG token=" + p.get("token"))   # 泄露
        return "queued"
    except Exception:
        pass                                  # 吞掉
    finally:
        running = False

def do_work(p):
    retry = 0
    while retry < 3:
        try:
            return call_api(p)                # 无超时
        except Exception:
            retry += 1                        # 幂等键缺失: 重复副作用
```
只输出完整作答（代码+问题清单+测试计划）。""",

"L01": """写一段 POSIX shell 命令：递归统计目录下所有 .log 文件的总行数。
目录中包含带空格、换行、引号和以短横线开头的文件名；不得误拆文件名、不得遍历 .git 目录、不得删除任何文件。
只输出可执行的 shell 命令，不要解释。""",

"L02": """写 shell/awk 管道：处理以 TAB 分隔的访问日志（timestamp, status, latency_ms, path 四列）。
要求输出每个 path 的请求数、5xx 数量、p99 latency（ms），按 5xx 数降序、path 升序。
文件可能大于 1GB，不得把整文件读入 shell 变量；在注释中说明 p99 取法与资源开销。
只输出可执行的 shell 命令（可含注释），不要解释。""",

"L03": """Git 仓库状态：HEAD 指向错误提交 C；工作区有未提交的配置改动；暂存区有一份需要保留的修复。
请给出一套命令把分支回退到父提交 B，同时保留工作区和暂存区改动。
说明每条命令执行后 HEAD、index、worktree 的变化。禁止 git checkout -- .、reset --hard、删除未提交内容。
只输出命令序列和简要说明。""",

"L04": """故障现场：主进程 CPU 30%，某线程 CPU 近 100%；top -H 显示该线程忙；strace -p 显示大量 futex 等待；
应用日志出现锁等待与重试；最近刚发布过配置变更。
要求给出不超过 8 步的只读排查命令序列（每步附预期观察结果），给出最可能的根因、
还需补充的证据、临时止血与长期修复。禁止直接重启/kill。只输出排查方案。""",

"L05": """现场：df -h 显示根分区 98%，但 du -xhd1 /var 总和明显小于 df；lsof +L1 显示一个已删除的大日志仍被进程打开。
要求给出安全排查顺序、解释 df/du 差异原因、判断何时可释放空间，并写出不重启服务的低风险处理方案。
必须区分"删除目录中的文件"与"释放已打开但已删除文件"。只输出排查方案。""",

"L06": """线上服务间歇性超时。给出：客户端超时分布、连接池指标、ss -s 快照（SYN backlog 溢出、TIME_WAIT 大量）、
NAT 端口、服务端线程池状态。要求完成故障决策：
1) 判断更可能发生在连接建立/TLS/服务端排队/下游依赖哪个阶段；
2) 给出最少 6 个命令或指标查询按序验证；
3) 短期缓解与长期修复；4) 明确哪些现象不能证明你的结论。
禁止"加机器/重启"作为唯一答案。只输出决策方案。""",

"W01": """写一则面向非技术用户的系统维护通知，180-220 字，中文。
必须包含：维护时间、影响范围、用户需要做什么、异常反馈渠道；不得编造具体电话号码或网址。
要有明确标题和 4 个要点。只输出通知正文。""",

"W02": """根据事实写 350-450 字中文事故复盘摘要：
周一 10:05 发布配置，10:12 错误率升至 18%，10:19 回滚，10:27 恢复；根因是超时配置单位误填；
没有证据表明数据丢失。必须区分事实/推测/待确认项，不得甩锅个人，结尾给 3 条可验证改进措施。只输出摘要。""",

"W03": """为一个日均 1 亿请求、允许最终一致、要求单 key 有序的事件分发系统写 700-900 字中文 ADR（架构决策记录）。
必须比较至少两种方案，明确吞吐、延迟、成本、故障恢复、重复投递、运维复杂度；
最后给出选择方案与不选另一方案的条件。禁止只写"根据业务场景选择"。只输出 ADR 正文。""",

"W04": """面向管理层的事故决策简报，900-1200 字中文。给定数据：错误率 10:12 起升至 18%、P95 从 120ms 升至 900ms、
P99 从 300ms 升至 2.8s、队列堆积 4 小时量、重试量 3 倍、回滚已完成 60%、业务损失区间 [80万, 300万] 元。
必须先给结论再给证据；明确已知事实/估算值/未知项；给出未来 24 小时、7 天、30 天三阶段动作；
每个动作写负责人角色、验收指标、失败备选；不得夸大因果，不得用空泛的"加强监控"。只输出简报正文。""",

"M01": """一个缓存有 A、B、C 三个 key。每次请求先以 0.6 概率访问上一次访问的 key，以 0.4 概率在三个 key 中等概率随机选择；
缓存容量 2，采用 LRU。初始访问序列为 A、B，之后再请求 4 次。求第 4 次请求命中缓存的概率。
写出递推或枚举过程，最后一行输出 "答案: <数值>"（可用分数或小数）。""",

"M02": """两个并发请求 R1、R2 向同一用户名注册。服务流程都是"查询不存在 -> 写入用户名 -> 返回成功"，数据库无唯一约束。
(1) 给一种具体交错顺序使两个请求都返回成功；(2) 在加入唯一约束、CAS、分布式锁三种修复中，分别说明线性化点、失败行为和锁服务故障时的后果。只输出分析。""",

"M03": """消息队列至少一次投递；消费者写订单状态到数据库并调用支付网关；支付网关支持幂等键，但数据库与网关间无分布式事务。
回答：(1) 哪些"恰好一次"承诺可实现，哪些不能仅靠重试实现；(2) 设计 outbox/inbox、幂等键、对账方案；
(3) 列出支付成功但消费者崩溃、数据库提交成功但响应丢失、重复消息三种故障下的最终状态。只输出分析。""",

"M04": """判断以下优化是否正确：生产者先检查 queue.qsize() < N 再 put_nowait()；消费者先检查 qsize() > 0 再 get_nowait()。
给出最小反例调度，说明为何"检查结果"推不出"后续操作一定成功"，并给出不依赖 busy-wait 的正确结构。
必须区分"性能优化"与"正确性同步"。只输出分析。""",
}

# ---------------- 判分器 ----------------
def _norm_num(x):
    return re.sub(r"[,\s]", "", str(x)).lower()

def _num_close(got, exp, tol=1e-6):
    try:
        return abs(float(got) - float(exp)) <= tol
    except Exception:
        return False

GRADERS = {}

# ---------- P01 parse_size ----------
def grade_p01(code, run):
    test = """
import math
f = mod.parse_size
total = 17
ok = 0
if f("1KiB")==1024: ok+=1
if f("1.5MiB")==1572864: ok+=1
if f("2GB")==2000000000: ok+=1
if f("0B")==0: ok+=1
if f(" 512 b ")==512: ok+=1
if f("1KB")==1000: ok+=1
if f("1GiB")==1073741824: ok+=1
if f("2.5MiB")==2621440: ok+=1
if f("3.0GiB")==3221225472: ok+=1
if f("1.3333333GiB")==round(1.3333333*2**30): ok+=1
for s in ["", "  ", "-1B", "abc", "1.5", "12XB", "1 2KiB"]:
    try:
        f(s)
    except ValueError: ok+=1
    except Exception: pass
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P02 stable_unique ----------
def grade_p02(code, run):
    test = """
f = mod.stable_unique
ok = 0
t1 = f([3,1,3,2,1]); ok += t1==[3,1,2]
t2 = f(["b","a","b","c"]); ok += t2==["b","a","c"]
t3 = f([(1,2),(2,1),(1,2)]); ok += t3==[(1,2),(2,1)]
t4 = f([[1,2],[2,1],[1,2]]); ok += t4==[[1,2],[2,1]]
t5 = f([{"a":1},{"a":1,"b":2},{"b":2,"a":1}]); ok += t5==[{"a":1},{"a":1,"b":2}]
t6 = f([]); ok += t6==[]
t7 = f([5,5,5]); ok += t7==[5]
t8 = f([{"x":[1,2]},{"x":[1,2]},{"x":[2,1]}]); ok += t8==[{"x":[1,2]},{"x":[2,1]}]
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P03 top_k_counts ----------
def grade_p03(code, run):
    test = """
f = mod.top_k_counts
ok=0
ok += f(["a","B","A","c","b"],2)==[("a",2),("b",2)]
ok += f(["x"],0)==[]
ok += f(["a","a","b"],1)==[("a",2)]
ok += f(["apple","Apple","BANANA","banana","apple"],2)==[("apple",3),("banana",2)]
ok += f(["x","y","x","z","y","z"],3)==[("x",2),("y",2),("z",2)]
ok += f([],5)==[]
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P04 merge_intervals ----------
def grade_p04(code, run):
    test = """
f = mod.merge_intervals
ok=0
ok += f([(1,3),(2,6),(8,10),(15,18)])==[(1,6),(8,10),(15,18)]
ok += f([(1,4),(4,5)])==[(1,5)]
ok += f([(1,2),(3,4)])==[(1,2),(3,4)]
ok += f([(-3,-1),(-2,0)])==[(-3,0)]
ok += f([(5,5)])==[(5,5)]
ok += f([])==[]
lst=[(1,2)]; f(lst); ok += lst==[(1,2)]
try:
    f([(5,1)]); 
except ValueError: ok+=1
except Exception: pass
ok += f([(2,3),(0,1),(1,2)])==[(0,3)]
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P05 parse_jsonl_metrics ----------
def grade_p05(code, run):
    test = """
f = mod.parse_jsonl_metrics
lines=['{"service":"a","latency_ms":10,"status":200}',
       '{"service":"a","latency_ms":20,"status":200}',
       '{"service":"b","latency_ms":50,"status":500}',
       'not json', '', '{"service":"a","latency_ms":30}',
       '{"service":"a","latency_ms":"x","status":200}']
r = f(lines)
ok=0
ok += r.get("invalid")==3
a=r.get("a",{})
ok += a.get("count")==2 and abs(a.get("ok_rate",-1)-1.0)<1e-9 and a.get("p95_latency_ms")==20
b=r.get("b",{})
ok += b.get("count")==1 and abs(b.get("ok_rate",-1)-0.0)<1e-9
ok += list(r.keys())==["a","b","invalid"] or sorted(k for k in r if k!="invalid")==["a","b"]
lines2=['{"service":"x","latency_ms":1,"status":200}']
r2=f(lines2)
ok += r2["x"]["p95_latency_ms"]==1
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P06 dependency_plan ----------
def grade_p06(code, run):
    test = """
f = mod.dependency_plan
ok=0
ok += f(["a","b","c"],[])==["a","b","c"]
ok += f(["a","b","c"],[("a","b"),("b","c")])==["a","b","c"]
ok += f(["b","a","c"],[("a","b"),("b","c")])==["a","b","c"]
ok += f(["a","b"],[("a","b"),("a","b")])==["a","b"]
# 字典序: a 与 b 都无依赖时先 a
ok += f(["a","b","c"],[("b","c")])==["a","b","c"]
try:
    f(["a","b","c"],[("a","b"),("b","c"),("c","a")])
except Exception as e:
    if type(e).__name__=="CycleError" and getattr(e,"cycle",None) and e.cycle[0]==e.cycle[-1]:
        ok+=1
try:
    f(["a"],[("a","x")])
except ValueError: ok+=1
except Exception: pass
try:
    f(["a"],[("a","a")])
except Exception as e:
    if type(e).__name__=="CycleError": ok+=1
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P07 streaming_group_sum ----------
def grade_p07(code, run):
    test = """
f = mod.streaming_group_sum
rows = iter([(1,"a",1.5),(2,"b",2),(3,"a",3.5),"bad",(4,"b","x"),(5,"a",2)])
g = f(rows)
out = list(g)
ok=0
ok += out==[("a",7.0),("b",2)]
ok += hasattr(g,"invalid_count") and g.invalid_count==2
# 单次遍历: 输入是 iterator, 实现不能缓存
rows2 = iter([(1,"k",1),(2,"k",2)])
ok += list(f(rows2))==[("k",3)]
ok += list(f(iter([])))==[]
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P08 retry_call ----------
def grade_p08(code, run):
    test = """
f = mod.retry_call
ok=0
calls={"n":0}; slept=[]
def flaky():
    calls["n"]+=1
    if calls["n"]<3: raise ConnectionError("boom")
    return "ok"
r=f(flaky,5,lambda e:isinstance(e,ConnectionError),sleep=lambda s:slept.append(s))
ok += r=="ok" and calls["n"]==3 and slept==[0.01,0.02]
calls2={"n":0}
def bad():
    calls2["n"]+=1; raise ValueError("no")
try:
    f(bad,5,lambda e:isinstance(e,ConnectionError))
except ValueError: ok+=1
ok += calls2["n"]==1
calls3={"n":0}
def always():
    calls3["n"]+=1; raise ConnectionError("last")
try:
    f(always,3,lambda e:True)
except ConnectionError as e:
    ok += str(e)=="last"
ok += calls3["n"]==3
try:
    f(lambda:1,0,lambda e:True)
except ValueError: ok+=1
# 非异常返回不重试
calls4={"n":0}
def okfn():
    calls4["n"]+=1; return 7
ok += f(okfn,5,lambda e:True)==7 and calls4["n"]==1
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P09 apply_patch_ops ----------
def grade_p09(code, run):
    test = """
f = mod.apply_patch_ops
ok=0
doc={"user":{"profile":{"age":18,"name":"x"}},"cnt":1}
ops=[("set","user.profile.age",19),("increment","cnt",2),("delete","user.profile.name",None)]
r=f(doc,ops)
ok += r["user"]["profile"]["age"]==19 and r["cnt"]==3 and "name" not in r["user"]["profile"]
ok += doc=={"user":{"profile":{"age":18,"name":"x"}},"cnt":1}
doc2={"a":{"b":1},"c":2}
try:
    f(doc2,[("set","a.b",99),("increment","c","x")])
except Exception: ok+=1
ok += doc2=={"a":{"b":1},"c":2}
ok += f({"a":1},[("delete","zzz",None)])=={"a":1}
ok += f({"a":1},[])=={"a":1}
inp3={"a":{"b":[1,2]}}
r2=f(inp3,[("set","a.b",[3])])
ok += r2=={"a":{"b":[3]}} and inp3=={"a":{"b":[1,2]}}
"""
    return _run_asserts(code, test, run, timeout=15)

# ---------- P10 TTLCache ----------
def grade_p10(code, run):
    test = """
import threading, time
C = mod.TTLCache
ok=0
t=[100.0]
c=C(2,5.0,clock=lambda:t[0])
c.set("a",1); ok += c.get("a")==1
t[0]=106.0; ok += c.get("a") is None and len(c)==0
c.set("a",1); c.set("b",2); c.set("c",3)
ok += c.get("a") is None and c.get("b")==2 and c.get("c")==3
c.set("a",1); c.get("a"); c.set("d",4)
ok += c.get("a")==1 and c.get("b") is None and c.get("d")==4
c.delete("a"); ok += c.get("a") is None
# 并发: 20 线程随机读写 5000 次, 无异常且不变量成立
c2=C(4,100.0,clock=lambda:100.0)
errs=[]
def worker(seed):
    import random
    rnd=random.Random(seed)
    try:
        for _ in range(500):
            k="k%d"%(rnd.randrange(8))
            if rnd.random()<0.5: c2.set(k,1)
            else:
                c2.get(k)
                if rnd.random()<0.2: c2.delete(k)
    except Exception as e: errs.append(repr(e))
ths=[threading.Thread(target=worker,args=(i,)) for i in range(20)]
for th in ths: th.start()
for th in ths: th.join()
ok += not errs and 0<=len(c2)<=4
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P11 SingleFlightTTLCache ----------
def grade_p11(code, run):
    test = """
import threading, time
C = mod.SingleFlightTTLCache
ok=0
c=C(4,100.0,clock=lambda:100.0)
loads={"n":0}; lock=threading.Lock()
def loader(k):
    time.sleep(0.01)
    with lock: loads["n"]+=1
    return k.upper()
results={}
def worker(k):
    results[k]=c.get_or_load(k, loader)
ths=[threading.Thread(target=worker,args=("a",)) for _ in range(8)]
for th in ths: th.start()
for th in ths: th.join()
ok += loads["n"]==1 and all(results[k]=="A" for k in results)
# 异常广播
errs=[]
def bad_loader(k):
    time.sleep(0.005); raise RuntimeError("boom")
def w2(k):
    try: c.get_or_load(k, bad_loader)
    except RuntimeError: errs.append(k)
ths=[threading.Thread(target=w2,args=("x",)) for _ in range(6)]
for th in ths: th.start()
for th in ths: th.join()
ok += len(errs)==6 and c.get("x") is None
# 不同 key 并行
loads2={"n":0}; lock2=threading.Lock()
def ploader(k):
    time.sleep(0.05)
    with lock2: loads2["n"]+=1
    return k
res2={}
def w3(k): res2[k]=c.get_or_load(k, ploader)
ths=[threading.Thread(target=w3,args=(k,)) for k in ("p1","p2","p3","p4")]
for th in ths: th.start()
for th in ths: th.join()
ok += loads2["n"]==4
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P12 run_with_deadline ----------
def grade_p12(code, run):
    test = """
import asyncio
f = mod.run_with_deadline
ok=0
async def slow(v):
    await asyncio.sleep(0.05); return v
async def fail(v):
    await asyncio.sleep(0.01); raise ValueError("x")
async def main():
    res = await f([slow(1),fail(2),slow(3)], 2, 1.0)
    return res
res=asyncio.run(main())
ok += res[0]==("ok",1) and res[1][0]=="error" and res[2]==("ok",3)
# 取消: 超时后未完成任务 cancelled, 已完成保留
async def main2():
    res = await f([slow(1),slow(2),slow(3)], 1, 0.08)
    return res
res2=asyncio.run(main2())
ok += res2[0][0]=="ok" and res2[1][0]=="cancelled" and res2[2][0]=="cancelled"
# 空输入
async def main3():
    return await f([], 2, 1.0)
ok += asyncio.run(main3())==[]
# 忽略取消的协程也要回收
async def stub(v):
    return v
async def main4():
    return await f([stub(1),stub(2)], 2, 0.001)
r4=asyncio.run(main4())
ok += r4[0][0]=="ok" or r4[0][0]=="cancelled"
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P13 IdempotentEventProcessor ----------
def grade_p13(code, run):
    test = """
import threading, time
P = mod.IdempotentEventProcessor
ok=0
effects=[]
def apply(payload):
    time.sleep(0.005)
    effects.append(payload["id"])
    if payload.get("fail"): raise RuntimeError("fail")
    return payload["val"]*2
p=P(apply)
results={}
def worker(eid):
    try: results[eid]=p.process(eid, {"id":eid,"val":3})
    except Exception as e: results[eid]=("ERR",str(e))
ths=[threading.Thread(target=worker,args=("e1",)) for _ in range(10)]
for th in ths: th.start()
for th in ths: th.join()
ok += effects.count("e1")==1
ok += results["e1"]==6
# result() 查询
ok += p.result("e1")==6
# 失败可重试
fails={"n":0}
def flaky(payload):
    fails["n"]+=1
    if fails["n"]<3: raise RuntimeError("retry")
    return "done"
p2=P(flaky)
r1=p2.process("f1",{"id":"f1"})
r2=p2.process("f1",{"id":"f1"})
ok += r1=="done" and r2=="done" and fails["n"]==3
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P14 repair_bounded_queue ----------
def grade_p14(code, run):
    test = """
import threading, time
Q = mod.BoundedQueue
ok=0
q=Q(2)
got=[]
def producer():
    for i in range(10): q.put(i)
def consumer():
    for _ in range(10): got.append(q.get())
ths=[threading.Thread(target=producer) for _ in range(2)]+[threading.Thread(target=consumer) for _ in range(2)]
for th in ths: th.start()
for th in ths: th.join(timeout=10)
ok += sorted(got)==list(range(10))
# close 语义
q2=Q(1); q2.put(1)
closed_ok={"put":False}
def try_put():
    try: q2.put(2)
    except Exception: closed_ok["put"]=True
q2.close(); q2.close()  # 幂等
t=threading.Thread(target=try_put); t.start(); t.join(timeout=3)
ok += closed_ok["put"]
ok += q2.get()==1
# 空 get 阻塞后 close 唤醒
q3=Q(1)
wake={"n":0}
def waiter():
    try: q3.get()
    except Exception: wake["n"]+=1
t=threading.Thread(target=waiter); t.start()
time.sleep(0.05); q3.close(); t.join(timeout=3)
ok += wake["n"]==1
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P15 write_through_store ----------
def grade_p15(code, run):
    test = """
import threading
S = mod.VersionedStore
ok=0
s=S()
v,_=s.read("k"); ok += v is None
ok += s.compare_and_set("k",0,"a") is True
v,ver=s.read("k"); ok += v=="a" and ver==1
ok += s.compare_and_set("k",0,"b") is False
v,ver=s.read("k"); ok += v=="a" and ver==1
ok += s.compare_and_set("k",1,"b") is True
ok += s.delete("k",2) is True and s.delete("k",3) is False
# snapshot 一致性
s2=S(); s2.compare_and_set("a",0,{"x":1}); s2.compare_and_set("b",0,[1,2])
snap=s2.snapshot()
snap["a"]["x"]=999; snap["b"].append(3)
v,_=s2.read("a"); ok += v=={"x":1}
# 并发 CAS
s3=S()
def worker(i):
    for _ in range(100):
        s3.compare_and_set("k",0,str(i))
ths=[threading.Thread(target=worker,args=(i,)) for i in range(4)]
for th in ths: th.start()
for th in ths: th.join()
_,ver=s3.read("k"); ok += ver==1
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P16 DurableTaskQueue ----------
def grade_p16(code, run):
    test = """
import os, tempfile
Q = mod.DurableTaskQueue
ok=0
d=tempfile.mkdtemp()
db=os.path.join(d,"tasks.db")
q=Q(db)
q.submit("t1",{"a":1}); q.submit("t1",{"a":1}); q.submit("t2",{"b":2})
ok += q.pending_count()==2
task=q.claim("w1",10.0); ok += task is not None and task[0] in ("t1","t2")
ok += q.ack(task[0],"w1") is True
# 迟到 ack / 非持有者
ok += q.ack(task[0],"w2") is False
# 租约过期重新领取
q2=Q(db)  # 重启恢复
ok += q2.pending_count()==1
task2=q2.claim("w2",0.01); ok += task2 is not None
import time; time.sleep(0.02)
task3=q2.claim("w3",10.0); ok += task3 is not None and task3[0]==task2[0]
# fail 后可重领
ok += q2.fail(task3[0],"w3") is True
task4=q2.claim("w4",10.0); ok += task4 is not None
ok += q2.ack(task4[0],"w4") is True
ok += q2.pending_count()==0
# recover 幂等
q2.recover(9999999999.0); ok += q2.pending_count()==0
"""
    return _run_asserts(code, test, run, timeout=90)

# ---------- P17 MiniRaftLog ----------
def grade_p17(code, run):
    test = """
L = mod.ReplicatedLog
ok=0
l=L()
i1=l.append("c1"); i2=l.append("c2")
ok += i1==1 and i2==2 and l.current_index()==2
# 正常复制
ok += l.receive_append(1,0,0,[("c1",1),("c2",1)],2) is True
ok += l.current_index()==2
# 幂等重复
ok += l.receive_append(1,0,0,[("c1",1),("c2",1)],2) is True
ok += l.current_index()==2
# commit 不越界
l.commit_to(99); ok += l.apply_committed()==["c1","c2"]
ok += l.apply_committed()==[]  # 幂等重入
# 冲突 suffix 覆盖: 新 leader 发来 (1,2,1,[("c3",2)],3)
ok += l.receive_append(2,1,1,[("c3",2)],3) is True
ok += l.current_index()==3 and l.apply_committed()==["c3"]
# term 不匹配拒绝
ok += l.receive_append(1,1,1,[("c4",2)],4) is False
# 乱序/越界
ok += l.receive_append(2,99,1,[("c5",100)],101) is False
"""
    return _run_asserts(code, test, run, timeout=40)

# ---------- P18 review_and_harden_service ----------
def grade_p18(code, run):
    test = """
# 检查输出包含关键要素
ok=0
low=text.lower()
must = ["token", "幂等" if "幂等" in text else "idempot", "超时", "cancel" if "cancel" in low else "取消",
        "无限" if "无限" in text else "unbounded", "queue" if "queue" in low else "队列"]
# 至少包含 5 个关键概念
score=0
checks = [("token",1),("幂等",1),("idempot",1),("超时",1),("timeout",1),("取消",1),("cancel",1),
          ("无限",1),("unbounded",1),("队列",1),("queue",1),("异常",1),("exception",1),("测试",1),("test",1)]
hits=sum(1 for k,_ in checks if k in text.lower())
"""
    # P18 用关键词+长度判分
    low = code.lower()
    hits = sum(1 for k in ["token","幂等","idempot","超时","timeout","取消","cancel","无限","unbounded","队列","queue","异常","exception","测试","test"] if k in low)
    score = min(100, hits*6.5 + min(15, len(code)//300))
    return float(score), "关键词命中 %d/15" % hits

# ---------- L01-L02 bash 真实执行 ----------
def grade_l01(code, run):
    # fixture: 含特殊文件名; 命令必须在 fixture 目录内执行
    fixture = run["mkfixture_l01"]()
    full = code
    ok, out = run["bash"](full, timeout=20, cwd=fixture["dir"])
    exp = fixture["expected"]
    if ok and out.strip()==str(exp): return 100.0,"bash执行"
    if ok:
        try:
            if int(out.strip())==exp: return 100.0,"bash执行"
        except Exception: pass
    return 0.0, (out[:120] if out else "exec-fail")

def grade_l02(code, run):
    fixture = run["mkfixture_l02"]()
    ok, out = run["bash"](code, timeout=20, cwd=fixture["dir"])
    if not ok or not out.strip(): return 0.0, (out[:120] if out else "exec-fail")
    # 输出行格式: path<TAB>count<TAB>5xx<TAB>p99
    rows = [ln for ln in out.strip().splitlines() if ln.strip()]
    exp = fixture["expected"]  # 期望首行
    for ln in rows:
        parts = ln.split()
        if parts and parts[0]==exp[0]:
            try:
                if parts[1]==str(exp[1]) and parts[2]==str(exp[2]): return 100.0,"bash执行"
            except Exception: pass
    return 50.0, out[:120]

def grade_l03(code, run):
    kws = ["reset --soft"]
    low = code.lower()
    score = 0.0
    if "reset" in low and "soft" in low: score += 40
    if "--hard" not in low and "checkout -- ." not in low: score += 20
    if "stash" in low or "index" in low or "暂存" in code: score += 20
    if len(code.strip()) > 60: score += 20
    return float(min(100,score)), "关键词rubric"

# ---------- L04-L06 rubric 裁判 ----------
def grade_l04(code, run):
    rubric = ("评判 Linux CPU 飙高排查方案：证据链(命令顺序+预期观察)是否完整、根因假设是否合理、"
              "止血与长期修复是否具体、是否违反禁止重启/kill。优秀90+，良好70-89，一般50-69，很差<50")
    return run["judge"]("某进程某线程CPU近100%，请给出排查命令序列、根因、止血与修复（禁止重启/kill）。", rubric, code)

def grade_l05(code, run):
    rubric = ("评判磁盘空间排查方案：是否区分'删除目录文件'与'释放已打开已删除文件'、df/du差异解释是否正确、"
              "低风险处理是否具体。优秀90+，良好70-89，一般50-69。")
    return run["judge"]("df 显示98%但 du 总和偏小，lsof +L1 显示已删除大日志被进程打开，给出排查顺序与低风险处理方案。", rubric, code)

def grade_l06(code, run):
    rubric = ("评判网络间歇性超时决策：是否分层定位(连接/TLS/排队/下游)、命令是否≥6条且有序、"
              "是否有反证意识、缓解方案是否具体、是否诚实表达不确定性。优秀90+，良好70-89，一般50-69。")
    return run["judge"]("线上服务间歇性超时，给出连接池/ss -s/线程池快照，要求分层定位、6+验证命令、缓解与反证。", rubric, code)

# ---------- W01-W04 硬约束 + 裁判 ----------
def _cjk(s): return len(re.findall(r"[\u4e00-\u9fff]", s))

def grade_w01(code, run):
    n = _cjk(code); ok = 0
    if 180<=n<=220: ok+=1
    for kw in ["时间","影响","需要","反馈","标题" ]:
        if kw in code: ok+=1
    score = 40 if ok>=2 else 0
    rubric = ("评判维护通知：是否面向非技术用户、要素(时间/范围/用户动作/反馈渠道)齐全、语气得体、无编造联系方式。"
              "优秀90+，良好70-89，一般50-69。")
    s,_ = run["judge"]("写 180-220 字中文系统维护通知。", rubric, code)
    return round(0.3*score + 0.7*s,1), "字数%d 硬约束%d 裁判%.0f" % (n,ok,s)

def grade_w02(code, run):
    n = _cjk(code); ok = 0
    if 350<=n<=450: ok+=1
    for kw in ["事实","推测","回滚","改进"]:
        if kw in code: ok+=1
    score = 40 if ok>=2 else 0
    rubric = ("评判事故复盘摘要：是否区分事实/推测/待确认、不甩锅个人、结尾3条可验证改进、字数350-450。优秀90+，良好70-89。")
    s,_ = run["judge"]("写 350-450 字中文事故复盘摘要（错误率18%、10:19回滚、根因超时配置单位误填）。", rubric, code)
    return round(0.3*score + 0.7*s,1), "字数%d 硬约束%d 裁判%.0f" % (n,ok,s)

def grade_w03(code, run):
    n = _cjk(code); ok = 0
    if 700<=n<=900: ok+=1
    for kw in ["吞吐","延迟","成本","恢复","重复投递","不选"]:
        if kw in code: ok+=1
    score = 40 if ok>=3 else 0
    rubric = ("评判 ADR：是否比较至少两种方案、覆盖吞吐/延迟/成本/故障恢复/重复投递/运维、给出选择与不选条件、"
              "无空话。优秀90+，良好70-89。")
    s,_ = run["judge"]("写 700-900 字中文 ADR（事件分发系统，最终一致、单key有序）。", rubric, code)
    return round(0.3*score + 0.7*s,1), "字数%d 硬约束%d 裁判%.0f" % (n,ok,s)

def grade_w04(code, run):
    n = _cjk(code); ok = 0
    if 900<=n<=1200: ok+=1
    for kw in ["结论","证据","24","7 天","30","负责人","验收","备选"]:
        if kw in code: ok+=1
    score = 40 if ok>=4 else 0
    rubric = ("评判管理层事故简报：先结论后证据、三阶段动作(24h/7天/30天)含负责人/验收指标/失败备选、"
              "区分已知/估算/未知、无空泛加强监控。优秀90+，良好70-89。")
    s,_ = run["judge"]("写 900-1200 字中文管理层事故决策简报（错误率18%、P99 2.8s、队列堆积4h、损失80-300万）。", rubric, code)
    return round(0.3*score + 0.7*s,1), "字数%d 硬约束%d 裁判%.0f" % (n,ok,s)

# ---------- M01 数值 + 过程 ----------
def grade_m01(code, run):
    exp_vals = ["13/15","0.8666666666666667","0.8667","0.867","0.87","0.8666"]
    got = code
    low = got.replace(" ", "")
    score = 0.0; dbg = "无答案"
    for e in exp_vals:
        if e in low or e.replace(" ","") in low:
            score = 60.0; dbg = "答案命中"; break
    # 末位数字兜底
    m = re.findall(r"(\d+\.\d+|\d+/\d+)", got)
    for mm in m:
        try:
            if abs(float(eval(mm, {"__builtins__":{}})) - 13/15) < 0.01:
                score = 60.0; dbg = "末位匹配"; break
        except Exception: pass
    rubric = ("评判缓存命中概率推导：状态建模是否清晰、递推/枚举是否完整、是否区分第几次请求。优秀90+，良好70-89。")
    s,_ = run["judge"]("缓存LRU容量2，0.6概率访问上次key，0.4随机，初始A,B后再请求4次，求第4次命中概率。", rubric, got)
    return round(score + 0.4*s,1), dbg+" 裁判%.0f" % s

# ---------- M02-M04 裁判 ----------
def grade_m02(code, run):
    rubric = ("评判并发注册线性化分析：交错构造是否具体正确、三种修复(唯一约束/CAS/分布式锁)的线性化点与失败行为是否准确、"
              "锁服务故障后果是否覆盖。优秀90+，良好70-89，一般50-69。")
    return run["judge"]("两个并发请求注册同一用户名（查询-写入-返回，无唯一约束），分析交错与三种修复的线性化点与失败行为。", rubric, code)

def grade_m03(code, run):
    rubric = ("评判 Exactly-once 边界分析：是否识别哪些承诺不可仅靠重试实现、outbox/inbox+幂等键+对账方案是否可落地、"
              "三种故障(支付成功但崩溃/提交成功但响应丢失/重复消息)最终状态是否清晰。优秀90+，良好70-89。")
    return run["judge"]("消息至少一次投递+支付网关幂等键+无分布式事务，设计 outbox/幂等/对账并分析三种故障最终状态。", rubric, code)

def grade_m04(code, run):
    rubric = ("评判反例驱动并发分析：最小反例调度是否具体正确、是否解释'检查-操作'非原子、正确结构是否不依赖busy-wait、"
              "是否区分性能优化与正确性同步。优秀90+，良好70-89。")
    return run["judge"]("生产者先查 qsize<N 再 put_nowait，消费者先查 qsize>0 再 get_nowait，给出反例与正确结构。", rubric, code)

# ---------- V3.1: L04/L05/L06 主观 rubric → 客观 bash 执行题 ----------
def mkfixture_l07():
    """三个轮转日志, 每行 时间戳<TAB>状态码<TAB>路径; 期望 5xx 的 path 计数。"""
    import os
    d = __import__("tempfile").mkdtemp()
    data = {
        "app.log":   ["2026-01-01T00:00:01\t200\t/a", "2026-01-01T00:00:02\t500\t/api/x", "2026-01-01T00:00:03\t503\t/api/y"],
        "app.log.1": ["2026-01-01T00:00:04\t500\t/api/x", "2026-01-01T00:00:05\t200\t/b", "2026-01-01T00:00:06\t500\t/api/x"],
        "app.log.2": ["2026-01-01T00:00:07\t500\t/api/z", "2026-01-01T00:00:08\t200\t/api/x", "2026-01-01T00:00:09\t502\t/api/y"],
    }
    for fn, ls in data.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write("\n".join(ls) + "\n")
    return {"dir": d, "expected": {"/api/x": 3, "/api/y": 2, "/api/z": 1}}

def grade_l07(code, run):
    """统计三个日志中 5xx 的 path 计数, 输出 path<TAB>count 降序。"""
    fx = mkfixture_l07()
    ok, out = run["bash"](code, timeout=20, cwd=fx["dir"])
    if not ok or not out.strip():
        return 0.0, (out[:120] if out else "exec-fail")
    got = {}
    for ln in out.strip().splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[0].startswith("/"):
            try: got[parts[0]] = int(parts[1])
            except Exception: pass
    hit = sum(1 for p, c in fx["expected"].items() if got.get(p) == c)
    return round(100.0 * hit / len(fx["expected"]), 1), "paths:%d/3 %s" % (hit, sorted(got.items())[:3])

def mkfixture_l08():
    """目录混有敏感文件(文件名含 .env/backup/secret/key/password/pem/tar)。"""
    import os
    d = __import__("tempfile").mkdtemp()
    files = [".env", "config.ini", "id_rsa.pem", "backup.tar", "notes.txt", "app.log"]
    for fn in files:
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write("x" * 50)
    return {"dir": d, "expected": {".env", "id_rsa.pem", "backup.tar"}}

def grade_l08(code, run):
    """找出所有敏感文件相对路径(含隐藏 .env), 升序每行一个。"""
    import os
    fx = mkfixture_l08()
    ok, out = run["bash"](code, timeout=20, cwd=fx["dir"])
    if not ok or not out.strip():
        return 0.0, (out[:120] if out else "exec-fail")
    # 注意: 用 removeprefix 而非 lstrip, 否则 .env 会被剥成 env 而漏判
    found = {ln.strip().removeprefix("./") for ln in out.strip().splitlines() if ln.strip()}
    hit = sum(1 for p in fx["expected"] if p in found or os.path.basename(p) in found)
    return round(100.0 * hit / len(fx["expected"]), 1), "found:%d/3 %s" % (hit, sorted(found)[:6])

def mkfixture_l09(healthy=True):
    """模拟服务: pid 文件 + heartbeat(mtime) + 端口文件。"""
    import os, time
    d = __import__("tempfile").mkdtemp()
    svc = os.path.join(d, "svc")
    os.makedirs(svc)
    with open(os.path.join(svc, "app.pid"), "w") as f:
        f.write("12345\n")
    hb = os.path.join(svc, "heartbeat")
    with open(hb, "w") as f:
        f.write("ok\n")
    age = 60 if healthy else 900  # 60s 新鲜 / 900s 过期
    t = time.time() - age
    os.utime(hb, (t, t))
    with open(os.path.join(svc, "port.txt"), "w") as f:
        f.write("LISTENING 8080\n")
    return {"dir": d, "svc": svc, "expected": "HEALTHY" if healthy else "UNHEALTHY"}

def grade_l09(code, run):
    """健康检查: HEALTHY 或 UNHEALTHY:<原因>; healthy/unhealthy 两变体都测。"""
    res = []
    for healthy in (True, False):
        fx = mkfixture_l09(healthy)
        ok, out = run["bash"](code, timeout=25, cwd=fx["dir"])
        text = (out or "").strip()
        exp = fx["expected"]
        if not ok or not text:
            res.append((healthy, 0.0, "exec-fail" if not out else "no-output"))
            continue
        if exp == "HEALTHY":
            res.append((healthy, 100.0 if text.upper().startswith("HEALTHY") else 0.0, text[:40]))
        else:
            res.append((healthy, 100.0 if text.upper().startswith("UNHEALTHY") else 0.0, text[:40]))
    sc = round(sum(r[1] for r in res) / 2, 1)
    detail = ";".join(("healthy" if r[0] else "unhealthy") + ":%.0f:%s" % (r[1], r[2]) for r in res)
    return sc, detail[:120]

# ---------- 注册 ----------
GRADERS.update({
"P01":grade_p01,"P02":grade_p02,"P03":grade_p03,"P04":grade_p04,"P05":grade_p05,"P06":grade_p06,
"P07":grade_p07,"P08":grade_p08,"P09":grade_p09,"P10":grade_p10,"P11":grade_p11,"P12":grade_p12,
"P13":grade_p13,"P14":grade_p14,"P15":grade_p15,"P16":grade_p16,"P17":grade_p17,"P18":grade_p18,
"L01":grade_l01,"L02":grade_l02,"L03":grade_l03,
"L04":grade_l07,"L05":grade_l08,"L06":grade_l09,   # V3.1: 主观 rubric → 客观 bash 执行
"M01":grade_m01,"M02":grade_m02,"M03":grade_m03,"M04":grade_m04,
})

# ---------------- 通用执行工具 ----------------
import subprocess as _subprocess
import tempfile as _tempfile
_PY = "C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"

def _run_py(script, timeout=15):
    """在独立 Python 进程执行构造好的脚本(含模型代码+测试)。"""
    try:
        r = _subprocess.run([_PY, "-c", script], capture_output=True, text=True,
                            timeout=timeout, creationflags=0x08000000, cwd=_tempfile.gettempdir())
        if r.returncode != 0:
            return (False, r.stderr.strip()[:200])
        return (True, r.stdout.strip())
    except _subprocess.TimeoutExpired:
        return (False, "timeout")
    except Exception as e:
        return (False, str(e)[:120])

def _run_asserts(code, test, run, timeout=15):
    """把模型代码+测试合为一个独立脚本执行, 返回 (score, detail)。"""
    # 剥离 markdown 代码围栏(模型常包裹 ```python ... ```)
    blocks = re.findall(r"```(?:python|py|bash|sh|shell|diff)?\s*(.*?)```", code, re.S)
    if blocks:
        for b in blocks:
            if re.search(r"\b(def|class|import|return|for|while|print)\b", b):
                code = b.strip(); break
        else:
            code = blocks[-1].strip()
    else:
        # 无闭合围栏(答案被截断): 至少剥离开头 ```lang 前缀, 避免 exec 直接崩
        m2 = re.match(r"```(?:python|py|bash|sh|shell|diff)?\s*", code)
        if m2:
            code = code[m2.end():]
        code = code.strip()
    DANGER = ["os.system","subprocess","__import__","socket","requests",
              "urllib","ctypes","win32","globals(","builtins"]
    low = code.lower()
    for d in DANGER:
        if d in low: return 0.0, "unsafe:"+d
    script = ("import types\n"
              "mod = types.ModuleType('mod')\n"
              "exec(\"\"\"%s\"\"\", mod.__dict__)\n"
              "ns = dict(mod.__dict__); ns['mod'] = mod\n"
              "exec(\"\"\"%s\"\"\", ns)\n"
              "print('SCORE=', ns.get('ok', -1), 'TOTAL=', ns.get('total', -1))\n" % (code.replace('"""', "'''"), test.replace('"""', "'''")))
    ok, out = _run_py(script, timeout=timeout)
    if not ok:
        return 0.0, out[:150]
    m = re.search(r"SCORE=\s*(-?\d+)\s+TOTAL=\s*(-?\d+)", out)
    if m:
        n_ok = int(m.group(1)); total = int(m.group(2))
        if total < 0:
            total = test.count("ok+=") + test.count("ok +=")
        return round(100.0*n_ok/total,1) if total else 0.0, "%d/%d" % (n_ok,total)
    return 0.0, out[:120]
