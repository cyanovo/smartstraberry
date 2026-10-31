# -*- coding: utf-8 -*-
"""分析 docx 中角色前缀与 run 背景色的匹配情况"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v4-颜色修复.docx"

ROLE_COLOR = {
    "项目经理：": "yellow",
    "嵌入式工程师：": "green",
    "AI视觉工程师：": "cyan",
    "AI 视觉工程师：": "cyan",
    "AI应用工程师：": "darkCyan",
    "AI 应用工程师：": "darkCyan",
    "全体成员：": None,  # 无背景
}


def para_highlight(p):
    """返回段落第一个台词 run 的 highlight 值（独立（翻页）run 跳过）"""
    for r in p.runs:
        if r.text.strip() == "（翻页）":
            continue
        m = re.search(r'w:highlight w:val="([^"]+)"', r._r.xml)
        return m.group(1) if m else None
    return None


d = docx.Document(PATH)
mismatch = []
checked = 0
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    role = None
    for pfx in ROLE_COLOR:
        if t.startswith(pfx):
            role = pfx
            break
    if role is None:
        continue  # 无前缀（保持黄色=项目经理），跳过
    checked += 1
    expect = ROLE_COLOR[role]
    actual = para_highlight(p)
    if actual != expect:
        mismatch.append((i, role.strip("："), expect, actual, t[:30]))

print(f"检查带角色前缀的段落: {checked}")
print(f"颜色不匹配: {len(mismatch)}")
for i, role, expect, actual, preview in mismatch:
    print(f"  段{i} [{role}] 期望={expect} 实际={actual} | {preview}")
