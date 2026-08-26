# relay-capability-test · 多模型能力横向评测系统

对任意 OpenAI 兼容中转站 / Relay 的多个模型做**横向能力评测**，输出自包含可视化 HTML 报告（排名图 / 逐题热力图 / 维度柱状图 / 雷达图 / 耗时与报错对比 / 性价比指数）。

## 核心特性

- **80 题 / 150 分权威题组**：自建工程题 32（50 分）+ OpenBench 核心 17（40 分）+ SWE-bench Lite 7（21 分）+ AIME 4（12 分）+ MATH-500 7（14 分）+ MMLU-Pro 8（8 分）+ OpenCompass 5（5 分）。高难占比 82.5%。
- **断点续测**：结果按 `(model, qid)` 追加写入 JSONL，天然支持中断恢复、跳过已完成题目。
- **分类退避**：429/402/503/524/400 分策略处理，不空耗配额。
- **错误负载拦截**：识别上游把错误页伪装成 HTTP 200 流回的「假跑」。
- **判分协议**：代码沙箱执行 / 选择题精确匹配 / 数值与 LaTeX 归一化 / 静态 rubric / 轻量 LLM 裁判。
- **自包含报告**：纯内联 SVG，无外部依赖，离线可开。

## 快速开始

```bash
# 1. 配置通道(推荐环境变量, 不写死在代码里)
export RELAY_BASE="https://your-relay.example.com/v1"
export RELAY_KEY="YOUR_RELAY_API_KEY"

# 2. 指定模型跑全量(串行)或指定模型
python scripts/capability_test_final.py                    # 跑默认 ALL_MODELS
python scripts/capability_test_final.py MODEL_A MODEL_B    # 只跑指定模型, 完成后自动出报告
python scripts/capability_test_final.py MODEL --smoke      # 冒烟(每类 1 题)
python scripts/capability_test_final.py M1 M2 M3 --parallel 5   # 按模型并行

# 3. 生成报告
python scripts/capability_report_final.py                  # -> capability_report_final.html
```

裁判模型(LLM judge)可走独立通道: `JUDGE_BASE` / `JUDGE_KEY`（部分中转站无裁判模型时, 可让模型走 A 站、裁判走 B 站）。

## 目录结构

```
SKILL.md                      # 完整方法论与已知坑位(16+ 条实测经验)
scripts/
  capability_test_final.py    # 主执行器(评测 + 判分 + 断点续测)
  self_bank_final.py          # 自建题组与判分器(P/L/W/M 系列)
  final80_qs.json             # 80 题题面/选项/参考答案(唯一数据源)
  question_bank_final.md      # 分值明细与判分协议说明
  capability_report_final.py  # 报告生成(150 分制加权)
  capability_test.py          # 旧 17 题轻量模式(向后兼容)
  gen_cap_report.py / _deep   # 旧报告生成
  regression_check.py         # 判分器回归验证
  final80_results.jsonl       # 示例评测结果(原始数据)
  capability_report_final.html / report.html   # 示例报告
```

## 评分口径

- **实际得分 = 判分器分(0-100) ÷ 100 × 题面分值**，满分 150（**不能**直接累加 JSONL 里的 score 字段）。
- 维度满分：编程 56 / Linux 8.5 / 写作 6 / 数学推理 36.5 / 知识科学 43。
- 性价比指数 CPI = 加权总分(150) ÷ 总耗时(秒) × 100。

## V1.0 变更记录

- **修复 P09 判分器**：测试中 delete 操作误用二元组(与题面「三元组」矛盾)、末行 `ok += ... and {dict}` 产生 `TypeError` —— 两处都会让所有模型判 0，已修复并回归验证(完整正确解 7/7)。
- **修复 OB-C2 HumanEval 判分器**：旧实现只提取 1 个 assert 节点且缺失循环局部变量，官方正确解也得 0/1；改为真正执行 `check(candidate)`。
- **修复 OB-M4 答案键**：并联电阻电流更大，正确答案为 A（原误标 B）；并加固选择题字母提取（优先 "Answer:/答案是/选X"，兜底取正文最后一个孤立字母而非第一个）。
- **答案存储**：`answer[:500]` → `answer[:4000]`，完整代码答案不再被截断丢失。

## 安全说明

- 所有 API key 请通过环境变量 `RELAY_KEY` / `JUDGE_KEY` 注入，**不要**提交到代码仓库。
- 评测脚本会执行模型输出的代码/命令（受限沙箱 + 危险词过滤），仅用于隔离评测环境。

## 局限声明

- SWE-bench 采用静态 rubric 判定（无法在 Windows 环境跑完整容器测试），分数用于横向区分，不等同官方 Verified 成绩。
- MMLU/MMLU-Pro 存在预训练污染风险，解读时适当降权。

## License

MIT
