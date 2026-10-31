# -*- coding: utf-8 -*-
"""
把最终版 docx 中所有"（翻页）"标记变成红色（无背景）：
- 独立"（翻页）"run：直接设红色
- 嵌在台词 run 中：拆分为"台词 run（保留原背景）" + "（翻页）run（红色无背景）"
"""
import copy
import os

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.text.run import Run

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "vibe", "最终版-53分定向修改.docx")

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
    # 先处理纯"（翻页）"或含标记的 run；从后往前拆，避免索引错乱
    runs = list(p.runs)
    for run in runs:
        text = run.text
        if MARKER not in text:
            continue
        if text.strip() == MARKER:
            make_red(run)
            changed += 1
            continue
        # 嵌在台词中：拆分
        parts = text.split(MARKER)
        # parts = [before, after1, after2, ...] 若标记出现多次
        # 保留 before 在原 run
        run.text = parts[0]
        cursor = run._r
        for k in range(1, len(parts)):
            seg = MARKER + parts[k] if k < len(parts) else MARKER
            # 复制原 run 元素作为新 run
            new_el = copy.deepcopy(run._r)
            cursor.addnext(new_el)
            new_run = Run(new_el, run._parent)
            new_run.text = seg if k > 1 else MARKER
            make_red(new_run)
            cursor = new_el
            changed += 1

try:
    doc.save(SRC)
    print("saved:", SRC)
except PermissionError:
    DST = SRC.replace(".docx", "-红翻页.docx")
    doc.save(DST)
    print("原文件被占用，另存为:", DST)
print("处理的（翻页）run 数:", changed)
