# -*- coding: utf-8 -*-
"""
把 逐字稿修复版-翻页标记.docx 中所有"（翻页）"统一为深红(C00000)+加粗+无背景。
文本内容完全不变；只拆出/标记（翻页）run 的视觉样式。
"""
import copy
import os

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.text.run import Run

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "逐字稿修复版-翻页标记.docx")
DST = os.path.join(BASE, "逐字稿修复版-翻页标记.docx")

MARKER = "（翻页）"
RED = RGBColor(0xC0, 0x00, 0x00)


def clear_highlight(run):
    rPr = run._r.get_or_add_rPr()
    hl = rPr.find(qn("w:highlight"))
    if hl is not None:
        rPr.remove(hl)


def make_red(run):
    run.font.color.rgb = RED
    run.font.bold = True
    clear_highlight(run)


doc = Document(SRC)
changed = 0
for p in doc.paragraphs:
    runs = list(p.runs)
    for run in runs:
        text = run.text
        if MARKER not in text:
            continue
        if text.strip() == MARKER:
            make_red(run)
            changed += 1
            continue
        # 嵌在台词中：拆分（翻页）为独立 run
        parts = text.split(MARKER)
        run.text = parts[0]
        cursor = run._r
        for k in range(1, len(parts)):
            new_el = copy.deepcopy(run._r)
            cursor.addnext(new_el)
            new_run = Run(new_el, run._parent)
            new_run.text = MARKER if k == 1 else MARKER + parts[k]
            if k > 1:
                # 有尾部内容（罕见），尾部保留原样式由下方 make_red 只对标记生效
                pass
            make_red(new_run)
            cursor = new_el
            changed += 1

doc.save(DST)
print("统一标红的（翻页）run 数:", changed)
print("saved:", DST)
