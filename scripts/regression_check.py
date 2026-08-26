# -*- coding: utf-8 -*-
"""修复回归验证: P09 三元组 / OB-C2 check() 执行 / OB-M4 key=A / choice 提取器"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capability_test_final as CTF
import self_bank_final as SBF
env = CTF.build_env()
data = json.load(open(CTF.QFILE, encoding="utf-8"))
qmap = {q["qid"]: q for q in data["questions"]}

ok = True

# 1) P09 正确 Python 解(按题面三元组解包)应能通过
P09 = r'''
import copy
def apply_patch_ops(document, operations):
    working = copy.deepcopy(document)
    for op, path, value in operations:
        parts = path.split(".")
        try:
            d = working
            for p in parts[:-1]:
                d = d[p]
            if op == "set":
                d[parts[-1]] = value
            elif op == "increment":
                d[parts[-1]] = d[parts[-1]] + value
            elif op == "delete":
                del d[parts[-1]]
        except Exception:
            pass
    return working
'''
sc, det = SBF.GRADERS["P09"](P09, env)
print(f"[P09] 正确解 -> score={sc} detail={det}")
if sc < 90: ok = False

# 2) OB-C2 官方正确解应 check-pass
CORRECT_C2 = '''
import math
def poly(xs, x):
    return sum(coeff * math.pow(x, i) for i, coeff in enumerate(xs))
def find_zero(xs):
    f = lambda x: poly(xs, x)
    lo, hi = -1.0, 1.0
    while f(lo) * f(hi) > 0:
        lo *= 2; hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return lo
'''
sc, det = CTF.grade_humaneval(qmap["OB-C2"], CORRECT_C2, env)
print(f"[OB-C2] 官方正确解 -> score={sc} detail={det}")
if sc < 90: ok = False

# 3) OB-M4: 答 A 应判对, 答 B 应判错; 且答案键已是 A
q4 = qmap["OB-M4"]
print(f"[OB-M4] answer_key 现在 = {q4.get('answer_key')!r}")
scA, detA = CTF.grade_choice(q4, "A")
scB, detB = CTF.grade_choice(q4, "B")
scI, detI = CTF.grade_choice(q4, "The setup that maximizes current is option A.")  # 正文带闲谈
print(f"[OB-M4] 答A -> {scA} ({detA}) | 答B -> {scB} ({detB}) | 答'...option A.' -> {scI} ({detI})")
if scA != 100 or scB != 0 or scI != 100: ok = False

print("\n" + ("✅ 全部通过" if ok else "❌ 存在失败项"))
