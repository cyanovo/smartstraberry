# -*- coding: utf-8 -*-
"""打印段31 的完整 rPr XML"""
import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v4-颜色修复.docx"
d = docx.Document(PATH)
p = d.paragraphs[31]
print("文本:", p.text[:50])
for j, r in enumerate(p.runs):
    rPr = r._r.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr"
    )
    print(f"run{j}:")
    print("  完整XML:", r._r.xml[:1200])
