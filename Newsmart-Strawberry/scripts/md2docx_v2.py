# -*- coding: utf-8 -*-
"""将 8-14商务稿子-微调对齐版-v2.md 转换为 docx（保持基本标题/段落结构）"""
import os
import re

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v2.md")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v2.docx")

doc = Document()

# 默认正文字体（中文）
style = doc.styles["Normal"]
style.font.name = "Microsoft YaHei"
style.font.size = Pt(11)
style._element.rPr.rFonts.set(
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
    "Microsoft YaHei",
)

with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

in_code = False
for raw in lines:
    line = raw.rstrip()
    if not line.strip():
        continue
    if line.strip().startswith("```"):
        in_code = not in_code
        continue
    if in_code:
        # 代码块：等宽字体
        p = doc.add_paragraph()
        run = p.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(9)
        run._element.rPr.rFonts.set(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
            "Microsoft YaHei",
        )
        continue
    if line.startswith("# "):
        p = doc.add_heading(line[2:].strip(), level=0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif line.startswith("## "):
        doc.add_heading(line[3:].strip(), level=1)
    elif line.startswith("### "):
        doc.add_heading(line[4:].strip(), level=2)
    elif line.startswith("> "):
        p = doc.add_paragraph()
        run = p.add_run(line[2:].strip())
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    elif line.startswith("|"):
        # 表格行：以文本形式保留
        doc.add_paragraph(line)
    elif line.startswith("（代码略"):
        p = doc.add_paragraph()
        run = p.add_run(line)
        run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    else:
        p = doc.add_paragraph(line)

doc.save(DST)
print("saved:", DST)
