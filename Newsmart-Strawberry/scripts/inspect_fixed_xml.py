# -*- coding: utf-8 -*-
"""检查 v4-颜色修复.docx 中段9 等段的 run XML"""
import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v4-颜色修复.docx"
d = docx.Document(PATH)
for idx in (9, 10, 21, 31, 34, 36, 37):
    p = d.paragraphs[idx]
    print(f"=== 段{idx} runs={len(p.runs)} 文本={p.text[:30]!r}")
    for j, r in enumerate(p.runs):
        print(f"  run{j} 文本={r.text[:20]!r}")
        print(f"       XML={r._r.xml[:400]}")
