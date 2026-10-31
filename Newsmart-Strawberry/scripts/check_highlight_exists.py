# -*- coding: utf-8 -*-
"""检查 run 中是否有 w:highlight 元素及其值"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v4-颜色修复.docx"
d = docx.Document(PATH)
for idx in (9, 10, 21, 31, 34, 36, 37, 55, 57, 214, 215, 232, 242, 243, 254, 259, 263):
    p = d.paragraphs[idx]
    t = p.text.strip()[:24]
    info = []
    for j, r in enumerate(p.runs):
        m = re.search(r'<w:highlight[^/]*w:val="([^"]+)"[^/]*/>', r._r.xml)
        has = "有" if m else "无"
        val = m.group(1) if m else "-"
        info.append(f"r{j}({has},{val})")
    print(f"段{idx} [{t}] {' '.join(info)}")
