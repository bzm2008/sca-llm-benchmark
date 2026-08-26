# 多模型能力评测题库 FINAL：80 题 / 满分 150

> 状态：**待用户审阅**，确认前不启动正式测试。
>
> 定位：高难度、权威基准主导的横向评测。82.5% 题目落在高/超难档；权威基准题（OpenBench + SWE-bench + AIME + MATH + MMLU-Pro + OpenCompass）48 题 / 100 分，占 2/3 权重；自建工程题 32 题 / 50 分考察真实工程落地。
> 所有权威题均为**真实基准题**（seed=20260824 固定抽取落盘），非编造、非改编。

## 1. 总览

| 题组 | 来源 | 题数 | 分值 | 单题分 | 难度 |
|---|---:|---:|---:|---:|---|
| 自建工程题 | 自定义（隐藏测试/rubric） | 32 | 50 | 0.5~3 | 低6 中8 高10 超难8 |
| OpenBench 核心 | HumanEval 5 + GPQA-Diamond 6 + MMLU 6 | 17 | 40 | 1~4 | 高/超难 |
| SWE-bench Lite | 真实仓库 issue 修复 | 7 | 21 | 3 | 超难 |
| MATH-500 | 竞赛数学（L4-5 为主） | 7 | 14 | 2 | 高 |
| AIME 2025 | 竞赛数学（I/II 卷） | 4 | 12 | 3 | 超难 |
| MMLU-Pro | 知识推理（8 学科） | 8 | 8 | 1 | 高 |
| OpenCompass 体系 | C-Eval 2 + CMMLU 3 | 5 | 5 | 1 | 高 |
| **合计** | — | **80** | **150** | — | 高41 超难25（82.5%） |

## 2. 分值明细

### 2.1 自建工程题 32 题 = 50 分（难度档赋分：低 0.5 / 中 1 / 高 1.5 / 超难 3）

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
| P16 | DurableTaskQueue | 编程 | 超难 | 3 |
| P17 | MiniRaftLog | 编程 | 超难 | 3 |
| P18 | review_and_harden_service | 编程 | 超难 | 3 |
| L01 | safe_find_logs | Linux | 低 | 0.5 |
| L02 | log_agg_pipeline | Linux | 中 | 1 |
| L03 | git_recover_keep_changes | Linux | 中 | 1 |
| L04 | cpu_spike_diagnosis | Linux | 高 | 1.5 |
| L05 | disk_space_mismatch | Linux | 高 | 1.5 |
| L06 | network_timeout_decision | Linux | 超难 | 3 |
| W01 | maintenance_notice | 写作 | 低 | 0.5 |
| W02 | incident_review | 写作 | 中 | 1 |
| W03 | adr_decision | 写作 | 高 | 1.5 |
| W04 | exec_briefing | 写作 | 超难 | 3 |
| M01 | cache_hit_probability | 数学/推理 | 高 | 1.5 |
| M02 | concurrent_register | 数学/推理 | 超难 | 3 |
| M03 | exactly_once_boundary | 数学/推理 | 超难 | 3 |
| M04 | counterexample_concurrency | 数学/推理 | 超难 | 3 |

### 2.2 OpenBench 核心 17 题 = 40 分

| ID | 来源 | 单题分 | 小计 |
|---|---|---|---|
| OB-C1~C5 | HumanEval（官方 test 沙箱判 pass） | 2 | 10 |
| OB-K1~K6 | GPQA-Diamond（四选一） | 4 | 24 |
| OB-M1~M6 | MMLU（四选一） | 1 | 6 |

### 2.3 新增权威 31 题 = 60 分

| ID | 来源 | 题数 | 单题分 | 小计 | 判分 |
|---|---|---:|---:|---:|---|
| SW1~SW7 | SWE-bench Lite（7 个真实 repo issue） | 7 | 3 | 21 | 静态 rubric（文件命中50% + 函数符号30% + patch 结构20%） |
| AI1~AI4 | AIME 2025 I/II 卷 | 4 | 3 | 12 | 数字精确匹配（000-999） |
| MH1~MH7 | MATH-500（Level 4-5） | 7 | 2 | 14 | LaTeX 答案归一化匹配 |
| MP1~MP8 | MMLU-Pro（8 学科） | 8 | 1 | 8 | 选项字母精确匹配 |
| OC1~OC5 | OpenCompass 体系（C-Eval 2 + CMMLU 3） | 5 | 1 | 5 | 选项字母精确匹配 |

## 3. 判分协议

| 类型 | 判分方式 | 说明 |
|---|---|---|
| 自建 code/linux（P/L 题） | 隐藏测试 + 沙箱执行 | 独立进程、独立临时目录；并发题注入调度/超时/异常；持久化题测崩溃恢复 |
| 自建 writing（W 题） | 硬约束自动检查 + 双裁判取中位数 | 字数/标题/分段/必备字段自动判；内容逻辑双次独立评分 |
| 自建 math（M 题） | 结论正确性 50% + 推导/反例质量 50% | 主观题按 rubric 双评 |
| HumanEval | 官方 `check(candidate)` 沙箱执行 | 模型补全函数，entry_point 提取，全部断言通过=100 |
| GPQA/MMLU/MMLU-Pro/C-Eval/CMMLU | 单字母精确匹配 | 输出含解释时先提取 A-J，提取失败计 0 |
| AIME | 数字精确匹配 | 000-999 整数 |
| MATH-500 | 答案归一化匹配 | 整数字面 / `\frac{a}{b}`→a/b / 根式化简 |
| SWE-bench | 静态 rubric（见下） | 不执行完整 repo 测试（环境限制），局限性单独声明 |

### SWE-bench 静态评分细则（SW1~SW7）

题面 = 真实 issue 描述 + repo/instance_id + FAIL_TO_PASS 测试名。模型输出统一 diff 格式 patch：

1. **修改文件命中 50%**：patch 触及 gold patch 修改的同一文件（解析 `diff --git a/...`）
2. **函数/符号命中 30%**：patch 中出现 gold patch 的 def/class 符号
3. **patch 结构合理性 20%**：格式合法、上下文行存在、无删除大段无关代码

> **局限声明**：SWE-bench 官方正确判分需在隔离容器中安装依赖并运行 FAIL_TO_PASS 测试；本评测环境（Windows + Git Bash）无法完整复现，采用静态判定，其分数用于横向区分"能否定位正确文件与函数"，不等同于 SWE-bench Verified 官方成绩。

## 4. 难度与权威性说明

- 难度档：低 6 / 中 8 / 高 41 / 超难 25。高 + 超难 = 66/80 = **82.5%**。
- 权威基准题 48 题占 100 分（66.7%），全部来自社区公认基准，可与官方公开成绩对照（GPQA/MMLU/HumanEval/MATH/AIME 均有模型官方分）。
- 新增来源选型理由：
  - **SWE-bench Lite**：真实 GitHub 仓库修复，当前 agentic 能力评测金标准（7 题跨 django/astropy/sympy/scikit-learn 等）
  - **AIME 2025**：竞赛级数学，区分推理上限
  - **MATH-500**：L4-5 高难竞赛题，覆盖代数/数论/计数/几何
  - **MMLU-Pro**：比 MMLU 更难的推理型知识题（比 MMLU 少 ~15% 正确率）
  - **OpenCompass 体系**：C-Eval（高等数学/计算机网络）+ CMMLU 中文权威题，覆盖中文能力维度

## 5. 执行与公平性

- 16 模型 × 80 题 ≈ 1280 次调用；按 de5.net 实测限流（188 req/min）预计 3~4 小时，断点续测 + 自动恢复。
- 每模型每题最多重试 5 次；429/524/503 分开记录，网关故障不计能力分。
- 题目按模型随机打乱、顺序落盘；先 16 模型 × 3 题冒烟，再全量。
- 慢模型（42/kimi/grok/qwen3.8-max 等）max_tokens 给足（≥3000），防止 reasoning 占满输出。
- 结果 JSONL 按 `(model, qid)` 取最后一条成功记录。

## 6. 报告输出

- `final80_results.jsonl`：逐模型逐题得分/耗时/TTFT/错误分类/答案摘要
- `capability_report_final.html`：
  - 综合排名（150 分制）与不加权均分对比
  - 七题组得分条形图 + 难度档得分
  - 编程专项（自建 + HumanEval + SWE）与知识专项（GPQA + MMLU + MMLU-Pro + OpenCompass）与数学专项（AIME + MATH）
  - 实测 vs 官方成绩对照表（识别中转站模型与官方同名模型偏差）
  - 逐题热力图 + 耗时分布 + 模型适用场景分析
- `question_bank_final.md`：本题库与评分协议

## 7. 局限声明

1. SWE-bench 采用静态判定（见 3 节），非官方环境成绩。
2. MMLU/MMLU-Pro 有预训练污染风险，解读时降权；GPQA 为最接近无污染的硬知识题。
3. 单次采样，选择题正确率波动 ±10% 内视为并列；对总分相近模型，SWE/GPQA/P16-P18 做第二次采样标注方差。
4. GPQA 含 LaTeX 公式，题面 UTF-8 原文传输，不做公式转图。
5. OpenCompass 题来自 C-Eval/CMMLU 公开数据集，与 OpenCompass 榜单同源，非其私有内部题。

---

**请审阅本最终题库。确认后我会编写执行器 `capability_test_final.py` 并开始冒烟 + 全量测试。**
