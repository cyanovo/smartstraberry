# -*- coding: utf-8 -*-
"""检查修复版-翻页标记 docx 中未标红的（翻页）run"""
import re

import docx

NEW = "逐字稿修复版-翻页标记.docx"
n = docx.Document(NEW)

for i, p in enumerate(n.paragraphs):
    for j, r in enumerate(p.runs):
        if "（翻页）" in r.text:
            m = re.search(r'w:color w:val="([0-9A-Fa-f]{6})"', r._r.xml)
            hl = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
            color = m.group(1) if m else "NONE"
            hlval = hl.group(1) if hl else "无"
            if not (color == "C00000" and not hl):
                print(f"段{i} run{j}: 颜色={color} 高亮={hlval} 文本={r.text[:30]!r}")
