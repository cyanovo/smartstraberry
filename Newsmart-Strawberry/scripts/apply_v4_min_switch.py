# -*- coding: utf-8 -*-
"""
v4：切换最少版。
- 基于 v2-新.docx（项目经理主讲版）
- 成效段 3 段分给上台的人顺带讲（番茄展→AI视觉、成本→嵌入式、商业模式→AI应用）
- 痛点认领改为"四人一同起身，依次汇报，讲完一同回工位"（1 次切换）
"""
import copy
import os

from docx import Document
from docx.text.paragraph import Paragraph

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v2-新.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v4-新.docx")

doc = Document(SRC)
paras = doc.paragraphs


def set_text(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run(text)


def insert_after(anchor, text):
    new_el = copy.deepcopy(anchor._p)
    anchor._p.addnext(new_el)
    np = Paragraph(new_el, anchor._parent)
    set_text(np, text)
    return np


def strip_prefix(t, prefix):
    return t[len(prefix):] if t.startswith(prefix) else t


# ============ 锚点校验 ============
checks = [
    (25, "项目经理：前期调研已经完成"),
    (26, "嵌入式工程师：第一个痛点"),
    (254, "项目经理：如何证明我们种出的番茄好吃"),
    (255, "项目经理：成本方面"),
    (256, "项目经理：商业模式上"),
]
for idx, expect in checks:
    actual = paras[idx].text.strip()
    if expect not in actual:
        raise SystemExit(f"锚点校验失败 idx={idx}: 期望含 {expect!r}，实际 {actual[:40]!r}")
print("锚点校验全部通过（%d 处）" % len(checks))

# 1) 痛点认领：插入"四人一同起身"动作提示（在开场段之后）
insert_after(paras[25], "【动作】四位成员一同起身，站到左屏（PPT 屏）旁，依次汇报各自负责的痛点，讲完一同回到工位。")

# 2) 成效段 3 段分给上台的人（切换最少：他们本来就在成效幕上台）
set_text(paras[254], "AI 视觉工程师：" + strip_prefix(paras[254].text.strip(), "项目经理："))
set_text(paras[255], "嵌入式工程师：" + strip_prefix(paras[255].text.strip(), "项目经理："))
set_text(paras[256], "AI 应用工程师：" + strip_prefix(paras[256].text.strip(), "项目经理："))

doc.save(DST)
print("saved:", DST)
