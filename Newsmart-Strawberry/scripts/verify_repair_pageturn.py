# -*- coding: utf-8 -*-
"""验证 逐字稿修复版-翻页标记.docx：数量、红色、内容未变"""
import re

import docx

ORIG = "逐字稿修复版.docx"
NEW = "逐字稿修复版-翻页标记.docx"

o = docx.Document(ORIG)
n = docx.Document(NEW)
r1 = [p.text for p in o.paragraphs]
r2 = [p.text for p in n.paragraphs]

print("原段落数:", len(r1), "新段落数:", len(r2))
c1 = sum(t.count("（翻页）") for t in r1 if t.strip())
c2 = sum(t.count("（翻页）") for t in r2 if t.strip())
print("原翻页:", c1, "新翻页:", c2)

red = 0
not_red = 0
for p in n.paragraphs:
    for r in p.runs:
        if "（翻页）" in r.text:
            m = re.search(r'w:color w:val="([0-9A-Fa-f]{6})"', r._r.xml)
            hl = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
            if m and m.group(1) == "C00000" and not hl:
                red += 1
            else:
                not_red += 1
print("红色无背景（翻页）run:", red, "其他:", not_red)

# 内容对比：除了追加的（翻页），其余应一致
diff = 0
for a, b in zip(r1, r2):
    if a == b:
        continue
    # 允许的差异：a 无翻页、b 有且 b 去掉翻页后 == a
    if "（翻页）" not in a and b == a + "（翻页）":
        continue
    diff += 1
    print("非预期差异:", a[:36], "||", b[:46])
print("非预期内容差异段:", diff)
