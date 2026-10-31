# -*- coding: utf-8 -*-
"""对比 修复版 与 最终版md 的翻页标记位置，列出修复版缺失的标记"""
import re

import docx

REPAIR = "逐字稿修复版.docx"
CUR = "docs/vibe/最终版-53分定向修改.md"

dr = docx.Document(REPAIR)
repair_items = []
for i, p in enumerate(dr.paragraphs):
    t = p.text.strip()
    if "（翻页）" in t:
        repair_items.append((i, t))

with open(CUR, "r", encoding="utf-8") as f:
    cur_items = []
    for ln, line in enumerate(f, 1):
        t = line.strip()
        if "（翻页）" in t:
            cur_items.append((ln, t))

print(f"修复版现有翻页: {len(repair_items)} 处")
for i, t in repair_items:
    # 提取该段的前 34 字作为标识
    print(f"  [段{i}] {t[:42]}")

print(f"\n最终版md翻页: {len(cur_items)} 处")
print("\n=== 修复版缺少的翻页标记（需补的位置）===")
# 用"前 12 字"作为锚点粗匹配
missing = []
cur_anchors = [(ln, re.sub(r"[（翻页）\s]", "", t)[:14]) for ln, t in cur_items]
repair_anchors = [re.sub(r"[（翻页）\s]", "", t)[:14] for _, t in repair_items]
for ln, anchor in cur_anchors:
    if anchor not in repair_anchors:
        missing.append((ln, anchor))
for ln, a in missing:
    print(f"  [md行{ln}] 锚点={a}")
