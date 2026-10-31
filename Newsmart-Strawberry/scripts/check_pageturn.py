# -*- coding: utf-8 -*-
"""检查最终版 docx 中（翻页）的格式现状"""
import re

import docx

d = docx.Document("docs/vibe/最终版-53分定向修改.docx")
cnt = 0
samples = []
for i, p in enumerate(d.paragraphs):
    for j, r in enumerate(p.runs):
        if "（翻页）" in r.text:
            m = re.search(r'w:color w:val="([0-9A-Fa-f]{6})"', r._r.xml)
            hl = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
            cnt += 1
            if len(samples) < 8:
                samples.append((i, j, m.group(1) if m else "默认", hl.group(1) if hl else "无", r.text[:24]))
for s in samples:
    print(f"段{s[0]} run{s[1]} 颜色={s[2]} 高亮={s[3]} 文本={s[4]!r}")
print("含（翻页）的 run 总数:", cnt)
