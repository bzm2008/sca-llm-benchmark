---
name: relay-capability-test
description: 对任意 OpenAI 兼容中转站/Relay 的多个模型做横向能力评测。主流程使用 80 题 / 150 分权威题组（自建工程题 + OpenBench HumanEval/GPQA/MMLU + SWE-bench + AIME + MATH-500 + MMLU-Pro + OpenCompass 体系），输出自包含 HTML 报告（内联 SVG 排名图/分组柱状图/雷达图/逐题热力图/耗时与报错对比）+ 文字分析（各模型优缺点 + 时间性价比总结）。含断点续测、429/400/401/402/503/524 分类退避与快速失败、代码沙箱执行、轻量裁判打分。当用户要求"测这几个模型的能力/跑一遍能力测试/对比模型强弱/出图表报告"时使用。与 relay-probe（边界探测）互补。
---

# relay-capability-test 多模型能力评测

## 适用场景
给定中转站 endpoint + key + 一批模型名，要横向对比各模型真实能力并出"图表+文字报告"。

## 快速开始（新题组：80 题 / 150 分）
```bash
python scripts/capability_test_final.py                          # 跑 ALL_MODELS 全量(串行)
python scripts/capability_test_final.py MODEL_A MODEL_B          # 指定模型; 跑完自动生成报告
python scripts/capability_test_final.py MODEL --smoke            # 冒烟(每类 1 题, 5 题)
python scripts/capability_test_final.py MODEL --limit 10         # 只跑前 10 题
python scripts/capability_test_final.py M1 M2 M3 --parallel 5    # 并行: 线程池按模型分 worker
```
- **并行模式**：`--parallel N` 用 `ThreadPoolExecutor` 按模型分组调度（每模型 1 个 worker，worker 内保持题目顺序，同模型不乱序）。de5.net 实测限流 188 req/min / 625k tokens/min，60+ 并发可成功，而串行只用到 ~0.5%——**瓶颈是模型生成延迟而非中转站**，10 路并发约提速 10 倍仍远低于上限。fixture 用 `tempfile.mkdtemp()` 每调用独立目录，线程安全；`log`/`save_result` 已加锁。429 各 worker 独立退避互不阻塞。
- 改脚本顶部 `KEY / BASE / ALL_MODELS / JUDGE` 适配新中转站（当前默认 de5.net）。
- **唯一数据源**：`scripts/final80_qs.json`（80 道真实题，seed 固定，选项已打乱落盘）。审阅看到的题 = 实际跑的题。
- **题组规格**：`scripts/question_bank_final.md`（分值明细、判分协议、难度与权威性、局限声明）。
- 原始数据：`final80_results.jsonl`（按 model+qid 追加，天然断点续测）。每条含 `score`(判分器 0-100 率)/`elapsed`(单题耗时)/`ttft`(首字延迟)/`status`(ok 或 错误分类)/`detail`/`answer`。
- 报告生成：`python scripts/capability_report_final.py` → `capability_report_final.html`（自包含，无外部依赖，离线可开）。注意：报告聚合时**实际得分 = 判分器分/100 × 题面分值**，不能直接累加 jsonl 里的 score 字段。

## 关键设计（勿随意删改）
- **题组构成（80 题 / 150 分，高难占比 82.5%）**：
  - 自建工程题 32（50 分）：并发/异步/幂等/持久化/故障恢复/代码审查/多文件项目，按隐藏测试通过率判分。
  - OpenBench 核心 17（40 分）：HumanEval×5（官方 test 沙箱）、GPQA-Diamond×6（四选一）、MMLU×6（四选一）。
  - SWE-bench Lite 7（21 分）：真实 repo issue + gold patch 元数据，静态 rubric（文件命中 50% + 函数符号 30% + patch 结构 20%）。
  - AIME 2025 4（12 分）：竞赛数学，数字精确。
  - MATH-500 7（14 分）：LaTeX 归一化。
  - MMLU-Pro 8（8 分）/ OpenCompass 体系 5（5 分）：四选一。
- **判分**：数值精确 / 代码沙箱执行比对（HumanEval 官方 test 逐断言）/ 关键词+rubric 裁判（`ministral-8b-latest`，0-100）/ 选择题单字母 / SWE 静态 rubric。
- **断点续测**：启动时加载 `final80_results.jsonl`，`status==ok` 跳过；同 (model,qid) 去重取最后一条。
- **错误分类**：
  - `429` → 限流，指数退避（45s 起步）。
  - `400/401/503` + "not available/not supported/model_not_found/No available channel" → 后端不可用，快速失败（2 次×10s 后标记 unavailable），避免空耗。
  - `402` + "Insufficient Balance/insufficient" → 余额瞬时抖动，快速失败（2 次×30s 后标记 unavailable 跳过），**不要无脑重试浪费时间**。
  - `524`（Cloudflare 网关超时）→ 慢模型常见，普通退避重试即可。
  - `grade_error` → 判分器异常，记一条 status=grade_error 的脏记录并继续，**下次启动会自动重跑该题为正常评分**（不会卡死整轮）。
  - **`200` + 错误正文（伪装成功）**：中转站把不可用模型的错误页当 200 流回（见坑位 8）。`status` 绝不能是 `ok`——用 `is_error_payload()` 检测 `Cursor API`/`<!DOCTYPE`/`HTTP 403/404`/`[Error`，命中则判 `unavailable`（detail=`error-payload-200`）。这是"假跑"的根因，务必拦截。
- **推理模型坑**：`max_tokens` 取 max(题干值, 3000)，否则推理模型把预算花在 reasoning 上、内容为空导致误判 0 分。全量固定 `temperature=0` 保证可复现（权威评测不要开温度）。
- **判分健壮性**（Windows 实测踩过的坑，已在 runner 固化）：
  - 模型常把代码包在 ```` ```python ```` 围栏里——`run_code`/`run_bash`/HumanEval 提取器都先剥围栏再执行。
  - `run_bash` 对 Linux 实测题须支持 `cwd=`，否则模型命令在临时根目录执行、把整盘文件数进去导致误判（L01 曾返回 2000 而非 21）。
  - `CODE_DANGER` 只保留真正逃逸/外联风险词（`os.system`/`subprocess`/`__import__`/`socket`/`ctypes`/`win32` 等）；`compile(`/`eval(`/`exec(`/`open(`/`import os`/`pathlib` 是合法解题代码，误杀会团灭正则/表达式类题。

## 已知坑位（Windows 环境实测）
1. **Bash 后台子进程会被杀**（会话句柄丢失），须用分离进程方式重启（如 `Start-Process -WindowStyle Hidden`），子进程才能长期存活；被杀后靠 jsonl 断点续测即可无损恢复。
2. **重试成功后旧记录残留**：同一 (model,qid) 可能既有 unavailable 又有 ok 记录，报告聚合必须按 (model,qid) 去重取最后一条，否则维度均分虚高。
3. **网关级不存在的模型**（如某中转站的 oc/* 别名返回 400 "not available"/401 "not supported"）：先探测确认后，标记 unavailable 并预填记录，可跳过整模型免扫。
4. 中转站 `/v1` 请求需带浏览器 UA，gzip 响应需手动解压（urllib 无 --compressed）。
5. **Windows 文件名禁含 `\n`/`\t` 等控制字符**：fixture 用 `line\nbreak.log` 这类名会抛 `OSError` 直接杀进程——fixture 文件名只用合法但刁钻的字符（如 `weird#&.log`、`quote'x.log`、`-dash.log`）。
6. 报告生成函数（如 `capability_report_final.py`）以读取 `final80_results.jsonl` 的方式产出 HTML，需与 runner 同目录。
7. **DeepSeek 官方 V4 深推理坑（实测 api.deepseek.com）**：`deepseek-v4-flash/pro/vision-exp` 是深推理模型，`max_tokens<32000` 时思考耗尽预算、`content` 永远为空（全部输出进 `reasoning_content`）；必须 `max_tokens=40000 + reasoning_effort=high + max_reasoning_tokens=40000` 才有答案输出。**不要**把 `reasoning_content` 兜底进答案——思考文本 9 万字符会污染判分并触发 Windows `[WinError 206] 命令行过长`。官方 API 直连 TTFT 0.6-1.5s（非流式），流式先发 reasoning 后发 content。执行器已支持 `--base URL --key KEY` 切换 endpoint。
8. **上游把错误页当 200 流回（致命的"假跑"）**：部分中转站（实测 de5.net 的 `anthropic/claude-sonnet-4.6` 经 Cursor API 代理）对不可用模型返回 **HTTP 200 + 错误 HTML/JSON 正文**（如 `[Error: Cursor API 错误: HTTP 403/404 ...]` 或 `<!DOCTYPE html>`），而非返回 4xx/5xx。若执行器只判 `st==200 and text.strip()` 就标 `ok`，会把 80 条报错存成"成功作答"，**看起来秒完、分数却几乎全 0**。识别信号：重模型比轻模型还快、answer 字段含 `Cursor API`/`<!DOCTYPE`/`HTTP 403/404`/`[Error`/`model_not_found`。修复：`chat_stream` 后加 `is_error_payload(text)`（检测上述签名），`run_model` 把"200 但错误负载"判为 `unavailable`（detail=`error-payload-200`）；报告 `load_data` 也需把 status=ok 但 answer 是错误负载的记录降级为 unavailable，否则旧数据仍会漏进分数。重跑前先 `probe` 确认该模型名在 relay 上真有可用通道（其他 claude 名在 de5 free 组均 503 model_not_found，说明该 relay 无 claude 通道，重跑纯浪费额度）。
   - **⚠️ `is_error_payload` 签名必须高特异性，否则会误伤真答案**：曾因用了裸 `"forbidden"` / `"429"` / `"503"` / `"http"` 等宽签名，把真实作答误判为错误页——物理题答案里的 "forbidden decays"、Python 代码注释里的 `"HTTP 层可映射为 503/429"` 都会被误杀，导致真答案被排除出分数（报告里该模型分被压低）。正确签名应只命中 relay 错误页特有串：`[error` / `cursor api` / `model_not_found` / `no available channel` / `upstream connect error` / `bad gateway` / `gateway timeout` / `service unavailable` / `request failed` / `429 too many` / `rate limit` / `<!doctype` / `<html` / `{"error"` / `http 403` / `http 404` / `http error` / `403 forbidden` / `504 gateway` / `502 `。**绝对不要**用裸 `forbidden` / `429` / `503` / `http` 做匹配。执行器与报告生成器的两处 `is_error_payload` 必须保持一致。
9. **裁判(LLM judge)失败会崩整条 worker 线程（致命的"假死"）**：`grade_question` 在 LLM 裁判（`JUDGE="ministral-8b-latest"`）调用失败时返回 `(None, "judge-fail")` / `(None, "judge-num")`（非异常、不抛错），而 `run_model` 直接 `round(score, 1)` 对 `None` 抛 `type NoneType doesn't define __round__ method`，被 `main()` 的 `except` 捕获记成"线程异常"，**该模型 worker 当场死亡、剩余题全成缺失、永不补全**。识别信号：日志出现 `线程异常 <模型>: type NoneType doesn't define __round__ method`，该模型随后不再有作答记录。修复：`run_model` 在 `score, detail = grade_question(...)` 后加 `if score is None:` 分支，记 `status="grade_error"`（detail=`judge-none:...`）并 `break`——grade_error 不是 ok，下次续测会自动重跑该题，不会崩线程。注意这与坑位 8 的 `error-payload-200` 不同：那是 200 错误页（上游挂），这是裁判 API 抖动（间歇失败），二者都该落 grade_error/unavailable 而非崩溃。
10. **中转站 free 组模型可用性边界（实测 de5.net）**：`/v1/models` 在 de5 被 403 拦截，无法列目录；只能用候选模型名直接探测。该 key 属 **free 组（distributor 分组）**，绝大多数旗舰模型返回 `503 model_not_found: No available channel for model X under group free (distributor)`——包括 `o3`/`o4-mini`/`gpt-4.5`/`gpt-4.1-mini`/`gemini-2.5-pro`/`gemini-2.5-flash`/`llama-4-maverick`/`llama-4-scout`/`glm-4.5`/`grok-3`/`deepseek-r1`/`mistral-large-latest`(裸名)/`command-r-plus`/`yi-large`/`hunyuan-large`/`claude-opus-4`，**带厂商前缀（`openai/o3`、`google/gemini-2.5-pro`、`anthropic/claude-opus-4`、`mistral/mistral-large-latest`、`meta/llama-4-maverick`）同样是 503**。实测 free 组可用强模型 = 已在测的 `gpt-4.1`/`gemini-3.1-pro-preview`/`grok-4.6` 等 + 本次新探到的 **`mistral-large-latest`（200 OK 正常应答，强通用模型，可加入评测）**。结论：**free 组通道极其有限，别指望 o3/gpt-4.5/gemini-2.5-pro 等旗舰**；要测这些需换付费组 key 或不同 endpoint。探测时每个候选发 1 条 "reply with exactly: OK" 短请求即可，注意探测会占用 relay 配额（与在跑评测竞争），宜少量、必要时才做。

## 续测 / 补做跳过题工作流
- **单遍执行器不会自动重做跳过题**：`capability_test_final.py` 的 `main()` 每模型只过一遍 80 题（`status==ok` 跳过；`unavailable` 重试 6 次仍失败就留下）。看门狗 `watch_final.py` 只出报告、不重跑。因此"跳过的题（unavailable/grade_error）"必须等本轮跑完后再单独续测一轮才会被重做。
- **推荐做法**：写 `monitor_redo.py`（工作区根目录）后台常驻 —— 轮询 `final80_results.jsonl` 修改时间，静默 ≥20 分钟判定后台单遍进程已结束，然后**动态读取结果里出现过的真实模型（排除已确认死的 `anthropic/claude-sonnet-4.6`/`gpt-4o`/`qwen3.8-max`）** 追加新模型（如 `mistral-large-latest`），调用 `capability_test_final.py <models> --parallel 8`（其 resume 逻辑跳过 ok、重做 unavailable/缺失 = 即"补跳过题"），最后 `capability_report_final.py` 出报告。这样不干扰在跑评测、且自动补全。
- **死模型别重跑**：`sonnet-4.6`（de5 无 claude 通道，Cursor API 404/403 伪装 200）、`gpt-4o`（上游空 content）、`qwen3.8-max`（WAF 风控拦截）已确认上游不可用，重跑纯烧额度，续测列表务必排除。

## 输出
- `capability_report_final.html`：自包含 HTML（内联 SVG，无外部依赖，离线可开）。
- `final80_results.jsonl`：逐题原始结果（分数/耗时/TTFT/错误分类/答案节选），按 (model,qid) 去重取最后一条。

### 报告必含项（用户指定，缺一不可）
1. **得分总览**：各模型总得分（满分 150）+ 每小题得分明细（80 题逐题可查）。
2. **能力分维图表**：每方面（编程/Linux/写作/数学推理等维度）得分的分组柱状图 + 各模型多维度**雷达图**。
3. **优缺点总结**：为每个模型单独写优缺点文字总结（结合正确率/鲁棒性/延迟表现，落到适用场景）。
4. **耗时与报错对比**：每模型总耗时、每题平均耗时、TTFT 均值、报错次数（按错误类型分类：429/402/503/524/grade_error/unavailable），做横向对比图表。
5. **时间性价比结论**：综合"速度（快）+ 得分（高）+ 报错（少）"三指标，明确点名性价比最优模型（可给性价比指数 = 得分 / 总耗时，或 得分×成功率 / 耗时 等，需在报告中写清公式）。

## 附注：旧 17 题轻量模式（向后兼容）
`scripts/capability_test.py`（17 题，数学/编程/Linux/知识/中文 5 维）+ `scripts/gen_cap_report.py` 仍可用，适合快速冒烟；新题组为默认推荐。


### 坑位 11 · 模型列表完整性（致命遗漏坑）
`ALL_MODELS` 默认**不含** `deepseek-v4-flash` / `deepseek-v4-pro` / `deepseek-v4-flash-vision-exp`（这些是后加的 deepseek 官方推理模型）。若续测只传 `ALL_MODELS` 或沿用某次显式列表而漏掉它们，这些模型会**永久停在已有进度（如 21/80）永远补不上**——因为它们不在进程模型列表内，resume 永远不会碰。
**统一续测必须显式传完整非隔离模型列表 + 新发现模型**，不要依赖 `ALL_MODELS` 默认。当前完整可用集（排除已隔离的 `anthropic/claude-sonnet-4.6` / `gpt-4o` / `qwen3.8-max` 三个死模型）：
```
oc/hy-3 nvidia/minimax-m3 nvidia/deepseek-v4-flash-0731 gpt-4.1 gpt-oss-120b gemini-3.1-pro-preview \
  grok-4.6 grok-chat-fast kimi-k3 mimo-v2.5 nvidia/nemotron-3-ultra-550b-a55b stealth/ox-alpha 42 \
  deepseek-v4-flash deepseek-v4-pro deepseek-v4-flash-vision-exp mistral-large-latest
```
（共 17 个；`mistral-large-latest` 是实测 free 组唯一新可用的强模型，`o3`/`gpt-4.5`/`gemini-2.5-pro`/`llama-4`/`claude-opus`/`grok-3`/`deepseek-r1` 等在 free 组均 `503 model_not_found`。）

### 坑位 12 · relay 524 限流 + 接管工作流
de5 中转上游频繁返回 `524`（Cloudflare 网关超时，**非 rate limit**，是上游推理慢；日志形如 `SW6 错误 st=524 err=<!DOCTYPE html>`），深推理模型（ds-v4 系列 `max_tokens=40000`）单题慢更易触发。若发现旧评测受限流极慢 / 某模型 worker 崩溃卡死 / 模型列表不全，**接管流程**：
1. `cp final80_results.jsonl 备份.jsonl`（已有 ok 记录靠 resume 保留，不丢）；
2. 用 PowerShell `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` 取 `CommandLine` 识别旧进程 PID（**wmic / tasklist /v 被安全策略禁用**；Read 工具故障时用 Python 读临时 proc 文件），`Stop-Process -Id <pid> -Force` 终止旧评测+旧看门狗+monitor（**保留 live_dash.py 面板**）；
3. 立即用新代码 `python capability_test_final.py <完整模型列表> --parallel 8` 续测（resume 自动跳已 ok、重做缺失+unavailable）。
**环境特性**：Start-Process 每个脚本起双进程，终止要杀两个 PID。

### 坑位 13 · 8 并发槽占位导致队尾模型"假卡死"（现象：面板某模型长时间不动）
`--parallel 8` = 最多 8 个模型同时跑，其余排队。若槽内是深推理+易 524 的重模型（gemini-3.1-pro / grok-4.6 / gpt-oss-120b / hy-3），它们单题撞 524 退避（旧逻辑 `wait=10*(attempt+1)` 递增到 40s，单题放弃高达 210s）会长期占住槽位，导致排在列表后面的模型（如 ds-v4 三款、mistral）**几十分钟拿不到槽、面板毫无变化**——但进程其实活着，不是真死。
**识别**：`tasklist` 有 python 进程 + dash(8899) 在 + jsonl mtime 仍在涨，但目标模型 dist 长期不变 → 队列占位，不是崩。（注：已 80/80 的模型 resume 会秒跳过所有旧 ok 题，面板同样"不动"，属正常完成。）
**干预（两步，不破坏已有数据）**：
1. **改短退避再重启**：把 `capability_test_final.py` 第 501 行通用退避 `wait = 10 * (attempt + 1)` 改为 `min(8, 4 * (attempt + 1))`（524/502 上限 8s，单题放弃从 210s 降到 ~44s）；第 470 行 `200 空正文` 30s→8s；第 484 行 `402` 30s→10s。改完**必须重启进程**才生效（运行中进程已加载旧代码）。
2. **重排模型顺序**：重启时把要保的模型（如 ds-v4 三款 + mistral）**放到命令行最前面**，立即占 slots 1–N，绝不被重模型堵在队尾。单进程重排比双进程分跑更干净（避免 dash 端口冲突、避免同模型双跑写重）。
**注意**：ds-v4 等部分题偶发 `503 No available channel`（中继该通道暂无），记 `unavailable` 属正常，不影响其它题续跑；最终报告如实反映 unavailable 数。

### 坑位 14 · 官方 DeepSeek V4 的 max_tokens 预算语义（空正文真根因）
对**官方** `api.deepseek.com/v1`（模型 `deepseek-v4-flash/-pro/-flash-vision-exp`）实测（P12 高难 async 题探针）：
- `max_tokens` = **推理(reasoning_content)+答案(content) 的总预算**；`max_reasoning_tokens` **并未被官方严格执行**（同题 mt=16000/mrt=16000 时 reasoning 流了 69852 字符、content=0）。
- 后果：若 `max_tokens == max_reasoning_tokens`，难题思考一旦吃满总预算 → **无 token 留给答案 → 返回 200 空正文**（触发"空正文重试"，6 次后记 unavailable）。mt 越大，能答的难题越多，但推理允许跑更久（更慢）。
- 探针同题对比（deepseek-v4-pro, P12）：
  - `mt=16000,mrt=16000` → cont_len=0, reason_len=69852, dt=260.1s（空正文）
  - `mt=24000,mrt=16000` → cont_len=3642(完整 asyncio 答案), reason_len=18282, dt=99.5s ✅
- **定稿配置**：`mt = max(mt, 32000)`，`extra = {"reasoning_effort":"high","max_reasoning_tokens":16000}`（推理预算与其他模型一致 16000，总预算留足答案空间）。实测 flash P15 从"一直空正文"→得分 44.4；仅极难题目仍可能偶发空正文，记 unavailable 计 0 分可接受。
- 验证方法：`/v1/chat/completions` 流式抓 `delta.content` 与 `delta.reasoning_content` 各自长度，对比不同 mt。

### 坑位 15 · 后台启动命令严禁带 `rm`（safe-delete 拦截坑）
Windows 环境后台任务（`run_in_background`）的 `rm -f` 走 safe-delete shim（回收站），若目标文件已不存在，回收失败 → 整条 `&&` 链命令失败（`status=failed`），**后续 python 根本没启动**——日志上表现为"起了新任务但没有任何产出"。
- 教训：**后台启动命令不要内嵌 `rm`/清理步骤**；清理临时文件用前台 Bash 单独执行。
- 判别：TaskOutput 显示 `[safe-delete][SAFE_DELETE_FAIL_CLOSED]` + `Duration` 很短(如 22s) + Stdout 空 → 任务在启动即死，检查命令开头是否带了 rm。

### 坑位 16 · WorkBuddy 自动化调度不可靠 → 用本机看门狗保活
本环境实测：WorkBuddy 的自动化任务（每小时巡检，RRULE 正确、状态 ACTIVE）**从未真正执行过**——`automation_runs` 表无该任务任何记录，`automation_runtime_state` 表无 last_run/next_run 行（调度 orchestrator 根本没在排程；历史仅有的 2 条 run 记录也全是失败/中断）。**结论：长时间跑批的"兜底"不能依赖 WorkBuddy 调度**。
**替代方案（定稿）**：本机常驻看门狗 `watchdog.py`（`run_in_background` 启动，写 watchdog.log）：
- 每 45 分钟（INTERVAL 可调）自巡一次，启动即跑首轮；
- ① 全部模型完成且无空值 → 跑 `finalize_report.py` 生成报告后 `sys.exit(0)`；
- ② 进程死且模型未完成 → `subprocess.Popen` 重启对应跑批（stdout 重定向 watchdog_launch.log；`creationflags=CREATE_NEW_PROCESS_GROUP` 隔离进程组）；
- ③ 进程活着但结果文件 mtime 停滞 >20min → `taskkill /F` 后重启。
- 进程检测复用坑位：`Get-CimInstance` + `Name -like 'python*'` 限定（防 powershell 自匹配）。
**首轮误杀教训**：看门狗启动时若结果文件早已停滞（旧进程死后的遗留 mtime），会把**刚由人重启的进程**误判为卡死杀掉（resume 跳过阶段不写文件，mtime 判断失真）。修复：`proc_alive` 返回最年轻进程的 `CreationDate`，进程创建 <STALE_MIN 分钟则跳过卡死判定（日志"进程刚启动不判卡死"）。
**建议**：WorkBuddy 自动化任务可保留 ACTIVE 作双保险（prompt 需含"进程存活则不起"防重复拉起），但主可靠性以本机看门狗为准。
