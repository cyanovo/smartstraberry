# -*- coding: utf-8 -*-
"""验证番外 docx：角色段颜色 + 结构"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-定向修改版-番外.docx"
d = docx.Document(PATH)

EXPECT = {
    "项目经理：": "yellow",
    "嵌入式工程师：": "green",
    "计算机视觉工程师：": "cyan",
    "AI应用开发工程师：": "darkCyan",
    "全体成员：": None,
}

checked = 0
bad = 0
samples = []
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    role = None
    for pfx in EXPECT:
        if t.startswith(pfx):
            role = pfx
            break
    if role is None:
        continue
    checked += 1
    # 取第一个 run 的颜色
    m = re.search(r'w:highlight w:val="([^"]+)"', p.runs[0]._r.xml) if p.runs else None
    actual = m.group(1) if m else None
    if actual != EXPECT[role]:
        bad += 1
        samples.append((i, role, EXPECT[role], actual, t[:30]))

print(f"角色段检查: {checked} 段, 不匹配 {bad} 段")
for s in samples:
    print("  ", s)

# 统计各角色段数
from collections import Counter
cnt = Counter()
for p in d.paragraphs:
    t = p.text.strip()
    for pfx in EXPECT:
        if t.startswith(pfx):
            cnt[pfx] += 1
            break
print("\n角色段数:", dict(cnt))
print("总段落:", len(d.paragraphs))
