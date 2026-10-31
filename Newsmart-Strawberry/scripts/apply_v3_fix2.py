# -*- coding: utf-8 -*-
"""v3 微修：段39 去重复句号；段113/134 舞台指示去掉角色前缀"""
import os

from docx import Document

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v3-新.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v3-新.docx")

doc = Document(SRC)
paras = doc.paragraphs


def set_text(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run(text)


# 段39：去掉重复句号
t39 = paras[39].text.strip()
t39 = t39.replace("。。", "。")
set_text(paras[39], t39)
print("段39 ->", t39[:60])

# 段113：去掉角色前缀（舞台指示）
t113 = paras[113].text.strip()
for pfx in ("AI 视觉工程师：", "AI视觉工程师："):
    if t113.startswith(pfx):
        t113 = t113[len(pfx):]
        break
set_text(paras[113], t113)
print("段113 ->", t113[:60])

# 段134：去掉角色前缀（动作指示）
t134 = paras[134].text.strip()
for pfx in ("AI 视觉工程师：", "AI视觉工程师："):
    if t134.startswith(pfx):
        t134 = t134[len(pfx):]
        break
set_text(paras[134], t134)
print("段134 ->", t134[:60])

doc.save(DST)
print("saved:", DST)
