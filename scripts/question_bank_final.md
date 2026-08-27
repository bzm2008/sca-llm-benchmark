# 多模型能力评测题库 V4：70 题 / 满分 150

> 状态：**V4 已重构**（2026-08-27），基于 V1-V3 的 19 模型实测得分率迭代：V2 删除 10 道满分率≥84.7% 的过易题并加权超难题；V3 写作题换代码推理选择题；V4 参考开源基准 **BIG-Bench Hard（BBH）** 替换剩余偏易题（MMLU 3 + OpenCompass 4 + MATH-500 3），知识/数学维度难度整体提升。
>
> 定位：高难度、权威基准主导的横向评测。权威基准题 38 题 / 90 分（占 60%）；自建工程题 32 题 / 60 分考察真实工程落地。
> 所有权威题均为**真实基准题**（seed=20260824 固定抽取落盘；BBH 为官方仓库原题，seed=20260827），非编造、非改编。

## 1. 总览

| 题组 | 来源 | 题数 | 分值 | 单题分 | 难度 |
|---|---:|---:|---:|---:|---|
| 自建工程题 | 自定义（隐藏测试/rubric） | 32 | 60 | 0.5~5 | 低6 中8 高10 超难8 |
| OpenBench 核心 | HumanEval 4 + GPQA-Diamond 4 + **BBH 7** | 15 | 34 | 1~6 | 高/超难 |
| SWE-bench Lite | 真实仓库 issue 修复 | 7 | 27 | 3~4 | 超难 |
| MATH-500 + BBH 数学 | 竞赛数学 4 + BBH 数学推理 3 | 7 | 14 | 2 | 高/超难 |
| AIME 2025 | 竞赛数学（I/II 卷） | 3 | 9 | 3 | 超难 |
| MMLU-Pro | 知识推理（6 学科） | 6 | 6 | 1 | 高 |
| **合计** | — | **70** | **150** | — | 高难度为主 |

### V1→V2 变更
- **删除 10 题**（满分率≥84.7%，无区分度）：OB-C4(编程100%) / OB-K4,OB-K6(GPQA 94.7%) / OB-M1,OB-M3,OB-M6(MMLU 94.7%) / OC3(CMMLU 94.7%) / AI2(AIME 94.7%) / MP1,MP8(MMLU-Pro 94.7%)
- **超难题加权**（+19 分）：P16/P17/P18(3→4) / SW1-SW6(3→4) / L06(3→5) / M02/M03/M04(3→4) / W04(3→5) / OB-K5(4→6) / OB-K3(4→5)
- **维度占比调整**：编程 37%→42%（↑区分度），知识科学 23%→21%（↓过易题）
- **V3 变更**：W01-W04 主观写作题 → R01-R04 代码推理选择题（客观唯一答案，程序化判分），写作维度移除（4 维）
- **V4 变更**（难度提升，参考开源基准）：MMLU 剩余 3 题 + OpenCompass 4 题 + MATH-500 偏易 3 题（满分率高、区分度低）→ **BIG-Bench Hard（BBH）10 题**：知识科学 7（BK01-07）+ 数学推理 3（BM01-03）。BBH 是公认比 MMLU 难一个量级的开源推理基准（GPT-3.5 few-shot 仅 ~55%）。分值保持维度平衡不变（知识 32 / 数学 36.5）

## 2. 分值明细

### 2.1 自建工程题 32 题 = 60 分（V2 超难题加权：低 0.5 / 中 1 / 高 1.5 / 超难 4-5）

| ID | 题名 | 维度 | 难度 | 分值 |
|---|---|---|---|---|
| P01 | parse_size | 编程 | 低 | 0.5 |
| P02 | stable_unique | 编程 | 低 | 0.5 |
| P03 | top_k_counts | 编程 | 低 | 0.5 |
| P04 | merge_intervals | 编程 | 低 | 0.5 |
| P05 | parse_jsonl_metrics | 编程 | 中 | 1 |
| P06 | dependency_plan | 编程 | 中 | 1 |
| P07 | streaming_group_sum | 编程 | 中 | 1 |
| P08 | retry_call | 编程 | 中 | 1 |
| P09 | apply_patch_ops | 编程 | 中 | 1 |
| P10 | TTLCache | 编程 | 高 | 1.5 |
| P11 | SingleFlightTTLCache | 编程 | 高 | 1.5 |
| P12 | run_with_deadline | 编程 | 高 | 1.5 |
| P13 | IdempotentEventProcessor | 编程 | 高 | 1.5 |
| P14 | repair_bounded_queue | 编程 | 高 | 1.5 |
| P15 | write_through_store | 编程 | 高 | 1.5 |
| P16 | DurableTaskQueue | 编程 | 超难 | **4** |
| P17 | MiniRaftLog | 编程 | 超难 | **4** |
| P18 | review_and_harden_service | 编程 | 超难 | **4** |
| L01 | safe_find_logs | Linux | 低 | 0.5 |
| L02 | log_agg_pipeline | Linux | 中 | 1 |
| L03 | git_recover_keep_changes | Linux | 中 | 1 |
| L04 | cpu_spike_diagnosis | Linux | 高 | 1.5 |
| L05 | disk_space_mismatch | Linux | 高 | 1.5 |
| L06 | network_timeout_decision | Linux | 超难 | **5** |
| R01 | 负索引切片输出预测 | 编程/代码推理 | 低 | 0.5 |
| R02 | 闭包延迟绑定输出预测 | 编程/代码推理 | 中 | 1 |
| R03 | 字典键哈希覆盖输出预测 | 编程/代码推理 | 高 | 1.5 |
| R04 | 生成器异常+next默认值输出预测 | 编程/代码推理 | 超难 | **5** |
| M01 | cache_hit_probability | 数学/推理 | 高 | 1.5 |
| M02 | concurrent_register | 数学/推理 | 超难 | **4** |
| M03 | exactly_once_boundary | 数学/推理 | 超难 | **4** |
| M04 | counterexample_concurrency | 数学/推理 | 超难 | **4** |

> **V3 变更（2026-08-27）**：W01-W04 主观写作题（LLM judge 判分、难易不可测）→ **R01-R04 代码推理选择题**（Python 输出预测，答案唯一、程序化判分）。R 题归入编程维度，写作维度移除（4 维：编程/Linux/数学/知识）。

### 2.2 OpenBench 核心 15 题 = 34 分（V2：删 OB-C4/K4/K6/M1/M3/M6，K3/K5 加权；V4：MMLU 全删换 BBH 知识）

| ID | 来源 | 题数 | 单题分 | 小计 |
|---|---|---:|---:|---:|
| OB-C1,C2,C3,C5 | HumanEval（官方 `check(candidate)` 沙箱判 pass） | 4 | 2 | 8 |
| OB-K1,K2,K3,K5 | GPQA-Diamond（四选一），K3=5 K5=6 其余 4 | 4 | 4~6 | 19 |
| BK01~BK07 | **BBH 知识题（V4）**：date_understanding / hyperbaton / disambiguation_qa / snarks / ruin_names / causal_judgement（Yes-No）/ web_of_lies（Yes-No） | 7 | 1 | 7 |

### 2.3 新增权威 23 题 = 56 分（V2：删 AI2/MP1/MP8/OC3，SWE/AIME 加权；V4：删 MH2/4/7 + OC 全删，换 BBH 数学）

| ID | 来源 | 题数 | 单题分 | 小计 | 判分 |
|---|---|---:|---:|---:|---|
| SW1~SW7 | SWE-bench Lite（7 个真实 repo issue），SW1-6=4 SW7=3 | 7 | 3~4 | 27 | 静态 rubric（文件命中50% + 函数符号30% + patch 结构20%） |
| AI1,AI3,AI4 | AIME 2025 I/II 卷（删 AI2） | 3 | 3 | 9 | 数字精确匹配（000-999） |
| MH1,MH3,MH5,MH6 | MATH-500（Level 4-5，V4 删 MH2/4/7 偏易题） | 4 | 2 | 8 | LaTeX 答案归一化匹配 |
| BM01~BM03 | **BBH 数学（V4）**：multistep_arithmetic_two（数字）/ geometric_shapes / temporal_sequences | 3 | 2 | 6 | 数字 / 单字母精确匹配 |
| MP2~MP7 | MMLU-Pro（6 学科，删 MP1/MP8） | 6 | 1 | 6 | 选项字母精确匹配 |

## 3. 判分协议

| 类型 | 判分方式 | 说明 |
|---|---|---|
| 自建 code/linux（P/L 题） | 隐藏测试 + 沙箱执行 | 独立进程、独立临时目录；并发题注入调度/超时/异常；持久化题测崩溃恢复 |
| 自建代码推理（R 题） | 选择题单字母精确匹配 | Python 输出预测，答案唯一，程序化判分（V3 替代原主观写作题） |
| 自建 math（M 题） | 结论正确性 50% + 推导/反例质量 50% | 主观题按 rubric 双评 |
| HumanEval | 官方 `check(candidate)` 沙箱执行 | 模型补全函数，entry_point 提取，全部断言通过=100 |
| GPQA/MMLU-Pro（单字母）+ BBH 选择题 | 单字母精确匹配 | 输出含解释时先提取 A-J，提取失败计 0 |
| BBH Yes-No（BK06/07） | exact 精确匹配 | 输出含 Yes/No（不区分大小写），提取失败计 0（V4 新增判分类型） |
| AIME | 数字精确匹配 | 000-999 整数 |
| MATH-500 | 答案归一化匹配 | 整数字面 / `\frac{a}{b}`→a/b / 根式化简 |
| BBH 数学（BM01） | 数字精确匹配 | multistep_arithmetic_two 输出整数答案 |
| SWE-bench | 静态 rubric（见下） | 不执行完整 repo 测试（环境限制），局限性单独声明 |

### SWE-bench 静态评分细则（SW1~SW7）

题面 = 真实 issue 描述 + repo/instance_id + FAIL_TO_PASS 测试名。模型输出统一 diff 格式 patch：

1. **修改文件命中 50%**：patch 触及 gold patch 修改的同一文件（解析 `diff --git a/...`）
2. **函数/符号命中 30%**：patch 中出现 gold patch 的 def/class 符号
3. **patch 结构合理性 20%**：格式合法、上下文行存在、无删除大段无关代码

> **局限声明**：SWE-bench 官方正确判分需在隔离容器中安装依赖并运行 FAIL_TO_PASS 测试；本评测环境（Windows + Git Bash）无法完整复现，采用静态判定，其分数用于横向区分"能否定位正确文件与函数"，不等同于 SWE-bench Verified 官方成绩。

## 4. 难度与权威性说明

- 难度档：低 6 / 中 8 / 高 29 / 超难 27。高 + 超难 = 56/70 = **80%**（V4 比 V2 高难占比提升）。
- 权威基准题 38 题占 90 分（60%），全部来自社区公认基准，可与官方公开成绩对照（GPQA/BBH/HumanEval/MATH/AIME 均有模型官方分）。
- 新增来源选型理由：
  - **SWE-bench Lite**：真实 GitHub 仓库修复，当前 agentic 能力评测金标准（7 题跨 django/astropy/sympy/scikit-learn 等）
  - **BIG-Bench Hard（V4）**：Google 精选 23 个难任务，公认比 MMLU 难一个量级的开源推理基准（GPT-3.5 few-shot 仅 ~55%）；知识题覆盖日期/反讽/谎言链/因果等深度推理，数学题覆盖多步算术/几何/时序
  - **AIME 2025**：竞赛级数学，区分推理上限
  - **MATH-500**：L4-5 高难竞赛题，覆盖代数/数论/计数/几何
  - **MMLU-Pro**：比 MMLU 更难的推理型知识题（比 MMLU 少 ~15% 正确率）

## 5. 执行与公平性

- 19 模型 × 70 题 ≈ 1330 次调用；按 de5.net 实测限流（188 req/min）预计 3~4 小时，断点续测 + 自动恢复。
- 每模型每题最多重试 5 次；429/524/503 分开记录，网关故障不计能力分。
- 题目按模型随机打乱、顺序落盘；先 19 模型 × 5 题冒烟，再全量。
- 慢模型（42/kimi/grok 等）max_tokens 给足（≥4000），防止高思考档（reasoning_effort=high）占满输出。
- 结果 JSONL 按 `(model, qid)` 取最后一条成功记录。

## 6. 报告输出

- `final80_results.jsonl`：逐模型逐题得分/耗时/TTFT/错误分类/答案摘要
- `capability_report_final.html`：
  - 综合排名（150 分制）与不加权均分对比
  - 七题组得分条形图 + 难度档得分
  - 编程专项（自建 + HumanEval + SWE）与知识专项（GPQA + BBH + MMLU-Pro）与数学专项（AIME + MATH + BBH 数学）
  - 实测 vs 官方成绩对照表（识别中转站模型与官方同名模型偏差）
  - 逐题热力图 + 耗时分布 + 模型适用场景分析
- `question_bank_final.md`：本题库与评分协议

## 7. 局限声明

1. SWE-bench 采用静态判定（见 3 节），非官方环境成绩。
2. MMLU-Pro 有预训练污染风险，解读时降权；GPQA 为最接近无污染的硬知识题；BBH 为 2022 年发布的高难推理基准，污染风险同样存在但低于 MMLU 类。
3. 单次采样，选择题正确率波动 ±10% 内视为并列；对总分相近模型，SWE/GPQA/P16-P18 做第二次采样标注方差。
4. GPQA 含 LaTeX 公式，题面 UTF-8 原文传输，不做公式转图。
5. BBH 题来自 suzgunmirac/BIG-Bench-Hard 官方仓库原题，随机抽取落盘（seed=20260827），非改编。

---

**请审阅本最终题库。确认后我会编写执行器 `capability_test_final.py` 并开始冒烟 + 全量测试。**
