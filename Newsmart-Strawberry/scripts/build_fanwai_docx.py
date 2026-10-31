# -*- coding: utf-8 -*-
"""
生成番外版 docx：解析 docs/8-14商务稿子-定向修改版-番外.md
应用原稿的角色背景色体系：
  项目经理=黄 / 嵌入式=绿 / 计算机视觉=青 / AI应用=深青 / 全体=无 / 动作行=无 / 代码=等宽无背景
"""
import os
import re

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-定向修改版-番外.md")
DST = os.path.join(BASE, "docs", "8-14商务稿子-定向修改版-番外.docx")

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
    "计算机视觉工程师": "cyan",
    "AI应用开发工程师": "darkCyan",
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


def add_role_para(text, role, bold_prefix=True):
    """角色台词段：前缀加粗，整段上角色色"""
    p = doc.add_paragraph()
    if role in ROLE_COLOR:
        # 前缀（角色名：）加粗
        m = re.match(r"^(【?[^：]*[工程师]?[^：]*?：)(.*)$", text, re.S)
        if m:
            prefix, body = m.group(1), m.group(2)
            r1 = p.add_run(prefix)
            r1.font.bold = True
            set_highlight(r1, ROLE_COLOR[role])
            r2 = p.add_run(body)
            set_highlight(r2, ROLE_COLOR[role])
        else:
            r = p.add_run(text)
            set_highlight(r, ROLE_COLOR[role])
    else:
        p.add_run(text)
    return p


def add_normal(text, color=None, bold=False, size=11, gray=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.bold = bold
    r.font.size = Pt(size)
    if gray:
        r.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
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
    """rows: list of list[str]"""
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

    # 代码块
    if stripped.startswith("```"):
        in_code = not in_code
        i += 1
        continue
    if in_code:
        add_code(line if line else " ")
        i += 1
        continue

    # 表格
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c.strip("-:")):
            table_buf.append(cells)
        i += 1
        continue
    if table_buf:
        add_table(table_buf)
        table_buf = []

    # 标题
    if stripped.startswith("# "):
        p = doc.add_heading(stripped[2:], level=0)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        i += 1
        continue
    if stripped.startswith("## "):
        p = doc.add_heading(stripped[3:], level=1)
        i += 1
        continue

    # 空行
    if not stripped:
        i += 1
        continue

    # 灰色说明行（修改点/重写/新增标注）
    if stripped.startswith("**【") or re.match(r"^【(修改点|重写|新增|动作|展示|运行|打开|操作|现场|全体)", stripped):
        add_normal(stripped, gray=True)
        i += 1
        continue

    # 角色台词：**角色名：** 正文
    role_match = re.match(r"^\*\*(项目经理|嵌入式工程师|计算机视觉工程师|AI应用开发工程师|全体成员)：\*\*(.*)$", stripped, re.S)
    if role_match:
        role, body = role_match.group(1), role_match.group(2)
        add_role_para(f"{role}：{body}", role)
        i += 1
        continue

    # 动作行（**...**）或（...）
    if re.match(r"^（\*\*?[^）]*）$", stripped) or re.match(r"^\(\*\*?[^)]*\)$", stripped):
        add_normal(stripped, gray=True)
        i += 1
        continue

    # 痛点/创新等加粗要点行（**痛点一：...** 等）
    if stripped.startswith("**") and "**" in stripped[2:]:
        # 整行加粗或含加粗片段
        text = stripped.replace("**", "")
        add_normal(text, bold=False)
        i += 1
        continue

    # 普通段落
    text = line.replace("**", "")
    add_normal(text)
    i += 1

if table_buf:
    add_table(table_buf)

doc.save(DST)
print("saved:", DST)
