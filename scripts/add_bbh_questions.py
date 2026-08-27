# -*- coding: utf-8 -*-
"""V3.1: 用 BBH(BIG-Bench Hard)开源推理题替换偏易题。
- 知识科学: 删 OB-M2/M4/M5(MMLU) + OC1/2/4/5(OpenCompass) 7题 → 加 BK01-07(BBH 常识/逻辑推理)
- 数学: 删 MH2/MH4/MH7(MATH 偏易) 3题 → 加 BM01-03(BBH 算术/几何/时序)
seed 固定, 可复现。"""
import json, re, random

random.seed(20260827)

p = "final80_qs.json"
d = json.load(open(p, encoding="utf-8"))

def load_bbh(task):
    return json.load(open(f"data_bbh/{task}.json", encoding="utf-8"))["examples"]

def pick(examples, k=1):
    return random.sample(examples, k)

def choice_q(qid, task, name, src_note, lvl, idx=0, pts_note=""):
    """BBH 选择题: input 自带 Options, answer_key 从 target '(B)' 提取。"""
    ex = pick(load_bbh(task))[idx]
    inp = ex["input"]
    m = re.search(r"\(([A-J])\)", str(ex["target"]))
    key = m.group(1) if m else "?"
    return {
        "qid": qid, "src": f"BBH/{task}", "lvl": lvl, "type": "choice",
        "question": inp,
        "expected": str(ex["target"]),
        "answer_key": key,
        "options": None,
        "name": name,
    }

def yn_q(qid, task, name, lvl, idx=0):
    """BBH Yes/No 题: type=exact, expected=Yes/No。"""
    ex = pick(load_bbh(task))[idx]
    return {
        "qid": qid, "src": f"BBH/{task}", "lvl": lvl, "type": "exact",
        "question": ex["input"],
        "expected": str(ex["target"]).strip(),
        "answer_key": None,
        "options": None,
        "name": name,
    }

def num_q(qid, task, name, lvl, idx=0):
    """BBH 数字题: type=num, expected 数字。"""
    ex = pick(load_bbh(task))[idx]
    return {
        "qid": qid, "src": f"BBH/{task}", "lvl": lvl, "type": "num",
        "question": ex["input"],
        "expected": str(ex["target"]).strip(),
        "answer_key": None,
        "options": None,
        "name": name,
    }

# 1) 删除旧题
DELETE = {"OB-M2", "OB-M4", "OB-M5", "OC1", "OC2", "OC4", "OC5", "MH2", "MH4", "MH7"}
before = len(d["questions"])
d["questions"] = [q for q in d["questions"] if q["qid"] not in DELETE]

# 2) 新增 BBH 题
NEW = []
# 知识科学 (BK, 1分/题)
NEW.append(choice_q("BK01", "date_understanding", "日期推理", "", "高"))
NEW.append(choice_q("BK02", "hyperbaton", "形容词词序", "", "高"))
NEW.append(choice_q("BK03", "disambiguation_qa", "代词指代消解", "", "高"))
NEW.append(choice_q("BK04", "snarks", "反讽识别", "", "超难"))
NEW.append(choice_q("BK05", "ruin_names", "谐音梗名称", "", "高"))
NEW.append(yn_q("BK06", "causal_judgement", "因果判断", "超难"))
NEW.append(yn_q("BK07", "web_of_lies", "谎言链推理", "超难"))
# 数学 (BM, 2分/题)
NEW.append(num_q("BM01", "multistep_arithmetic_two", "多步算术", "高"))
NEW.append(choice_q("BM02", "geometric_shapes", "几何形状推理", "", "超难"))
NEW.append(choice_q("BM03", "temporal_sequences", "时序推理", "", "超难"))
d["questions"].extend(NEW)

json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"题库: {before} -> {len(d['questions'])} 题 (删 {len(DELETE)}, 增 {len(NEW)})")
for q in NEW:
    print(f"  {q['qid']} [{q['type']}] {q['name']:8} key={q.get('answer_key') or q.get('expected')} | {q['question'][:60]!r}")
