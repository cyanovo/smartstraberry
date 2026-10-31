# -*- coding: utf-8 -*-
"""
修复 v4 的角色背景色错位：
按段落角色前缀重设台词 run 的 highlight 背景色，独立（翻页）红字 run 不动。
规则：项目经理=yellow / 嵌入式=green / AI视觉=cyan / AI应用=darkCyan / 全体成员=无背景
"""
import os

from docx import Document
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v4-新.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v4-颜色修复.docx")

ROLE_COLOR = [
    ("项目经理：", "yellow"),
    ("嵌入式工程师：", "green"),
    ("AI视觉工程师：", "cyan"),
    ("AI 视觉工程师：", "cyan"),
    ("AI应用工程师：", "darkCyan"),
    ("AI 应用工程师：", "darkCyan"),
    ("全体成员：", None),
]


def set_highlight(run, val):
    """val=None 清除高亮；否则设置 w:highlight"""
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


def is_page_turn_run(run):
    return run.text.strip().startswith("（翻页）")


doc = Document(SRC)
fixed = 0
for p in doc.paragraphs:
    t = p.text.strip()
    if not t:
        continue
    role_color = None
    matched = False
    for pfx, color in ROLE_COLOR:
        if t.startswith(pfx):
            role_color = color
            matched = True
            break
    if not matched:
        continue  # 无角色前缀（保持项目经理黄色），跳过
    for r in p.runs:
        if is_page_turn_run(r):
            continue  # 独立（翻页）红字 run 不动
        set_highlight(r, role_color)
        fixed += 1

doc.save(DST)
print("已保存:", DST)
print("修复完成，共设置/清除高亮 run 数:", fixed)
