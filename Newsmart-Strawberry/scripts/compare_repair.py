# -*- coding: utf-8 -*-
"""对比 逐字稿修复版.docx 与 当前最终版，列出用户修改点 + 结构问题"""
import re

import docx

REPAIR = "逐字稿修复版.docx"
CUR = "docs/vibe/最终版-53分定向修改.docx"

dr = docx.Document(REPAIR)
dc = docx.Document(CUR)

# 修复版段落（有文字）
r_texts = [p.text.strip() for p in dr.paragraphs if p.text.strip()]
c_texts = [p.text.strip() for p in dc.paragraphs if p.text.strip()]

print("=== 修复版 段落数:", len(dr.paragraphs), "有文字:", len(r_texts), "表格:", len(dr.tables))
print("=== 当前最终版 段落数:", len(dc.paragraphs), "有文字:", len(c_texts), "表格:", len(dc.tables))

print("\n=== 1. 分工段检查（修复版开头） ===")
for i, t in enumerate(r_texts[:12]):
    if t.startswith(("项目经理", "嵌入式", "AI视觉", "AI 视觉", "AI应用", "AI 应用", "全体", "【")):
        print(f"  {i}: {t[:44]}")

print("\n=== 2. 用户新增/修改的内容（修复版有、md最终版无的段落） ===")
# 找修复版里以"收到，回到工位"开头的段
for t in r_texts:
    if "回到工位后我将" in t:
        print("  新增:", t[:60])
    if "转色期半熟采摘" in t:
        print("  改写产业分析:", t[:60])
    if "大模型装进手机" in t:
        print("  改未来规划:", t[:60])
    if "现在的页面是番茄驾驶舱" in t:
        print("  重写系统功能:", t[:60])

print("\n=== 3. 疑似结构问题检查 ===")
for t in r_texts:
    if t.startswith("嵌入式：") or t.startswith("嵌入式:"):
        print("  简称'嵌入式：'→", t[:50])
    if "接下来，由" in t:
        print("  转场混乱:", t[:60])
    if "计算机视觉工程师" in t:
        print("  称呼不一致:", t[:50])

print("\n=== 4. 修复版翻页标记数量 ===")
total = sum(t.count("（翻页）") for t in r_texts)
print("  修复版（翻页）总数:", total)
print("  当前最终版（翻页）总数:", sum(t.count("（翻页）") for t in c_texts))
