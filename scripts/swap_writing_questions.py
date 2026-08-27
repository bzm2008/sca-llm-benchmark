# -*- coding: utf-8 -*-
"""V3: 删 W01-W04 主观写作题, 替换为 R01-R04 客观代码推理选择题。"""
import json

p = "final80_qs.json"
d = json.load(open(p, encoding="utf-8"))

# 1) 删除 W 题
W = {f"W0{i}" for i in range(1, 5)}
d["questions"] = [q for q in d["questions"] if q["qid"] not in W]

# 2) 新增 R01-R04 代码推理选择题
R = [
    {
        "qid": "R01", "src": "自建/代码推理", "lvl": "低", "type": "choice",
        "question": "以下 Python 代码的输出是什么？\n\n```python\na = [1, 2, 3, 4, 5]\nprint(a[-2:])\n```",
        "expected": "[4, 5]",
        "answer_key": "A",
        "options": [["A", "[4, 5]"], ["B", "[3, 4]"], ["C", "[2, 3, 4]"], ["D", "IndexError"]],
    },
    {
        "qid": "R02", "src": "自建/代码推理", "lvl": "中", "type": "choice",
        "question": "以下 Python 代码的输出是什么？\n\n```python\nfuncs = []\nfor i in range(3):\n    funcs.append(lambda: i)\nprint([f() for f in funcs])\n```",
        "expected": "[2, 2, 2]",
        "answer_key": "B",
        "options": [["A", "[0, 1, 2]"], ["B", "[2, 2, 2]"], ["C", "[0, 0, 0]"], ["D", "运行报错"]],
    },
    {
        "qid": "R03", "src": "自建/代码推理", "lvl": "高", "type": "choice",
        "question": "以下 Python 代码的输出是什么？\n\n```python\nd = {True: 'yes', 1: 'no', 1.0: 'maybe'}\nprint(d[True], len(d))\n```",
        "expected": "maybe 1",
        "answer_key": "B",
        "options": [["A", "yes 3"], ["B", "maybe 1"], ["C", "no 3"], ["D", "maybe 3"]],
    },
    {
        "qid": "R04", "src": "自建/代码推理", "lvl": "超难", "type": "choice",
        "question": "以下 Python 代码逐行输出是什么？\n\n```python\ndef gen():\n    yield 1\n    raise ValueError('boom')\n    yield 2\n\ng = gen()\nprint(next(g))\ntry:\n    print(next(g, 'fallback'))\nexcept ValueError as e:\n    print('caught', e)\nprint(list(g))\n```",
        "expected": "1\ncaught boom\n[]",
        "answer_key": "A",
        "options": [["A", "1 / caught boom / []"], ["B", "1 / fallback / []"],
                    ["C", "1 / caught boom / 运行报错"], ["D", "1 / fallback / 运行报错"]],
    },
]
d["questions"].extend(R)

json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"题库: {len(d['questions'])} 题 (W 删 4, R 增 4)")
