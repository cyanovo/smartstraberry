# -*- coding: utf-8 -*-
"""
生成"最终版-53分定向修改"docx：解析 md，应用角色背景色体系。
项目经理=黄 / 嵌入式=绿 / AI视觉=青 / AI应用=深青 / 全体=无
"""
import os
import re

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "vibe", "最终版-53分定向修改.md")
DST = os.path.join(BASE, "docs", "vibe", "最终版-53分定向修改.docx")

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Microsoft YaHei"
style.font.size = Pt(11)
style._element.rPr.rFonts.set(
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
    "Microsoft YaHei",
)

ROLE_COLOR = {
    "项目经理": "yellow",
    "嵌入式工程师": "green",
    "AI视觉工程师": "cyan",
    "AI 视觉工程师": "cyan",
    "AI应用工程师": "darkCyan",
    "AI 应用工程师": "darkCyan",
    "全体成员": None,
}


def set_highlight(run, val):
    rPr = run._r.get_or_add_rPr()
    hl = rPr.find(qn("w:highlight"))
    if val is None:
        if hl is not None:
            rPr.remove(hl)
        return
    if hl is None:
        hl = rPr.makeelement(qn("w:highlight"), {})
        rPr.append(hl)
    hl.set(qn("w:val"), val)


RED = RGBColor(0xC0, 0x00, 0x00)
MARKER = "（翻页）"

def _add_run_with_color(p, text, color):
    r = p.add_run(text)
    set_highlight(r, color)
    return r

def add_role_para(text, role):
    p = doc.add_paragraph()
    color = ROLE_COLOR.get(role)
    m = re.match(r"^(【?[^：]*[工程师]?[^：]*?：)(.*)$", text, re.S)
    if m and color is not None:
        prefix, body = m.group(1), m.group(2)
        # 拆分（翻页）部分
        parts = body.split(MARKER)
        # 第一部分（台词）
        r1 = p.add_run(prefix + parts[0])
        r1.font.bold = True
        set_highlight(r1, color)
        # 后续部分（翻页标记 + 可能的尾部台词）
        for i in range(1, len(parts)):
            # 翻页标记：红色、加粗、无高亮
            r_marker = p.add_run(MARKER)
            r_marker.font.bold = True
            r_marker.font.color.rgb = RED
            # 翻页后的剩余文字
            if parts[i]:
                _add_run_with_color(p, parts[i], color)
    else:
        # 非角色文本或 color 为 None
        parts2 = (text or "").split(MARKER)
        r = p.add_run(parts2[0])
        if color is not None:
            set_highlight(r, color)
        for i in range(1, len(parts2)):
            r_m = p.add_run(MARKER)
            r_m.font.bold = True
            r_m.font.color.rgb = RED
            if parts2[i]:
                r2 = p.add_run(parts2[i])
                if color is not None:
                    set_highlight(r2, color)
    return p


def add_normal(text, gray=False, bold=False, size=11):
    p = doc.add_paragraph()
    parts = text.split(MARKER)
    r = p.add_run(parts[0])
    r.font.bold = bold
    r.font.size = Pt(size)
    if gray:
        r.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    for k in range(1, len(parts)):
        r_m = p.add_run(MARKER)
        r_m.font.bold = True
        r_m.font.color.rgb = RED
        if parts[k]:
            r2 = p.add_run(parts[k])
            r2.font.size = Pt(size)
            if gray:
                r2.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    return p


def add_code(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    r._element.rPr.rFonts.set(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia",
        "Microsoft YaHei",
    )
    return p


def add_table(rows):
    ncols = max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows), cols=ncols)
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = t.cell(i, j)
            cell.text = row[j] if j < len(row) else ""
            if i == 0:
                for pr in cell.paragraphs:
                    for r in pr.runs:
                        r.font.bold = True
    doc.add_paragraph()


with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

in_code = False
table_buf = []
i = 0
while i < len(lines):
    raw = lines[i]
    line = raw.rstrip()
    stripped = line.strip()

    if stripped.startswith("```"):
        in_code = not in_code
        i += 1
        continue
    if in_code:
        add_code(line if line else " ")
        i += 1
        continue

    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c.strip("-:")):
            table_buf.append(cells)
        i += 1
        continue
    if table_buf:
        add_table(table_buf)
        table_buf = []

    if stripped.startswith("# "):
        p = doc.add_heading(stripped[2:], level=0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        i += 1
        continue
    if stripped.startswith("## "):
        doc.add_heading(stripped[3:], level=1)
        i += 1
        continue

    if not stripped:
        i += 1
        continue

    if stripped.startswith("> "):
        add_normal(stripped[2:].replace("**", ""), gray=True)
        i += 1
        continue

    if stripped.startswith("**【") or re.match(r"^【(新增|修改点|重写|动作|运行|打开|操作|展示|执行|选择|点击|修改|现场|全体|拔掉|重新)", stripped):
        add_normal(stripped.replace("**", ""), gray=True)
        i += 1
        continue

    role_match = re.match(
        r"^\*\*(项目经理|嵌入式工程师|AI视觉工程师|AI 视觉工程师|AI应用工程师|AI 应用工程师|全体成员)：\*\*(.*)$",
        stripped, re.S,
    )
    if role_match:
        role, body = role_match.group(1), role_match.group(2)
        add_role_para(f"{role}：{body}", role)
        i += 1
        continue

    if re.match(r"^（\*\*?[^）]*）$", stripped) or re.match(r"^\(\*\*?[^)]*\)$", stripped):
        add_normal(stripped, gray=True)
        i += 1
        continue

    text = line.replace("**", "")
    add_normal(text)
    i += 1

if table_buf:
    add_table(table_buf)

doc.save(DST)
print("saved:", DST)
