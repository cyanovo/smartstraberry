# -*- coding: utf-8 -*-
"""验证红翻页标记"""
import re

import docx

d = docx.Document("docs/vibe/最终版-53分定向修改.docx")
ok = 0
bad = 0
for i, p in enumerate(d.paragraphs):
    for j, r in enumerate(p.runs):
        if "（翻页）" in r.text:
            m = re.search(r'w:color w:val="([0-9A-Fa-f]{6})"', r._r.xml)
            hl = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
            color = m.group(1) if m else "NONE"
            hl_val = hl.group(1) if hl else "无"
            if color == "C00000" and hl_val == "无":
                ok += 1
            else:
                bad += 1
                print(f"  异常 段{i} run{j}: 颜色={color} 高亮={hl_val} 文本={r.text!r}")
print(f"红色无背景（翻页）run: {ok} 个, 异常: {bad} 个")
print("总段落:", len(d.paragraphs))
