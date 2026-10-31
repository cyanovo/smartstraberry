# -*- coding: utf-8 -*-
"""v6 验证：创新段归属 + 颜色 + 角色分布"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v6-创新嵌入式.docx"
d = docx.Document(PATH)

print("=== 创新段归属 ===")
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if any(k in t for k in ("多项创新", "产量预测模型", "感知-认知-控制", "协同创新模式", "场景创新——")):
        m = re.search(r'w:highlight w:val="([^"]+)"', p.runs[0]._r.xml) if p.runs else None
        print(f"  段{i} 颜色={m.group(1) if m else '?'} | {t[:44]}")

# 角色分布
paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
CODE_PREFIXES = ("def ", "async ", "return", "if ", "for ", "elif ", "#", '"""', "    ", "\t")
roles = {}
for t in paras:
    if t.startswith("【"):
        continue
    matched = False
    for pfx, key in (("项目经理：", "项目经理"), ("嵌入式工程师：", "嵌入式"),
                     ("AI视觉工程师：", "AI视觉"), ("AI 视觉工程师：", "AI视觉"),
                     ("AI应用工程师：", "AI应用"), ("AI 应用工程师：", "AI应用"),
                     ("全体成员：", "全体")):
        if t.startswith(pfx):
            body = t[len(pfx):]
            matched = True
            break
    if not matched:
        if t.startswith(CODE_PREFIXES) or re.match(r"^[a-zA-Z_]", t) or t.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.")):
            continue
        key = "无前缀"
        body = t
    body = re.sub(r"[（翻页）翻页()]", "", body)
    body = re.sub(r"【示例数据[^】]*】", "", body)
    roles[key] = roles.get(key, 0) + len(body)
total = sum(roles.values())
print("\n=== 角色分布 ===")
for k, v in sorted(roles.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({v/total*100:.1f}%)")
