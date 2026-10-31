# -*- coding: utf-8 -*-
"""v5 完整验证：输出到 UTF-8 文件，不打印中文"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v5-逻辑修复.docx"
OUT = r"C:\Users\cyan\AppData\Local\Temp\v5_verify.txt"
d = docx.Document(PATH)

ROLE_COLOR = {
    "项目经理：": "yellow",
    "嵌入式工程师：": "green",
    "AI视觉工程师：": "cyan",
    "AI 视觉工程师：": "cyan",
    "AI应用工程师：": "darkCyan",
    "AI 应用工程师：": "darkCyan",
    "全体成员：": None,
}
PREFIXES = tuple(ROLE_COLOR.keys())
CODE_PREFIXES = (
    "def ", "async ", "return", "if ", "for ", "elif ", "#", '"""', "    ", "\t",
    "await ", "client.", "uart.", "raw_data", "addr ", "r =", "sm =", "st =",
    "n  =", "p  =", "k  =", "humidity", "temp", "co2", "illum", "output", "result",
    "retriever", "kwargs", "file_name", "kb_id", "query_text", "chain", "block",
    "details", "all_valid", "hash_ok", "prev_ok", "recalc", "index", "nonce",
)
LIST_PREFIXES = ("1.", "2.", "3.", "4.", "5.", "6.", "7.")


def para_highlight(p):
    for r in p.runs:
        if r.text.strip() == "（翻页）":
            continue
        m = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
        return m.group(1) if m else None
    return None


lines = []
# 1. 无前缀台词
noprefix = []
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if not t or t.startswith("【") or t.startswith("（翻页）"):
        continue
    if t.startswith(PREFIXES):
        continue
    if t.startswith(CODE_PREFIXES) or re.match(r"^[a-zA-Z_]", t):
        continue
    noprefix.append((i, t))
lines.append("=== 1. 无前缀台词段 ===")
for i, t in noprefix:
    lines.append(f"  段{i} | {t[:60]}")
lines.append(f"  共 {len(noprefix)} 处（代码/小标题/列表项属正常）\n")

# 2. 颜色匹配
bad = 0
checked = 0
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    role = None
    for pfx in ROLE_COLOR:
        if t.startswith(pfx):
            role = pfx
            break
    if role is None:
        continue
    checked += 1
    expect = ROLE_COLOR[role]
    actual = para_highlight(p)
    if actual != expect:
        bad += 1
        lines.append(f"  颜色错位 段{i} [{role.strip('：')}] 期望={expect} 实际={actual} | {t[:36]}")
lines.append(f"=== 2. 颜色检查: {checked} 段，不匹配 {bad} 段 ===")

# 3. 逻辑残留检查
lines.append("\n=== 3. 逻辑残留检查 ===")
residual = ["三大痛点", "三套解法", "三点创新", "应用价值与未来规划", "函数6", "AI应用开发工程师",
            "秉持着服务产业的理念", "接下来继续进行优化", "近乎绝收", "整棚果实腐烂", "绝收"]
for i, p in enumerate(d.paragraphs):
    t = p.text
    for kw in residual:
        if kw in t:
            lines.append(f"  [残留:{kw}] 段{i} | {t[:60]}")
lines.append("  检查完毕")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written", OUT)
