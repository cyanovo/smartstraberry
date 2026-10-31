# -*- coding: utf-8 -*-
"""v6：项目创新段交给嵌入式工程师（前缀 + 颜色）"""
import os

from docx import Document
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v5-逻辑修复.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v6-创新嵌入式.docx")

doc = Document(SRC)


def find_para(doc, frag):
    for p in doc.paragraphs:
        if frag in p.text:
            return p
    raise SystemExit(f"未找到: {frag!r}")


def set_highlight(run, val):
    rPr = run._r.get_or_add_rPr()
    hl = rPr.find(qn("w:highlight"))
    if hl is None:
        hl = rPr.makeelement(qn("w:highlight"), {})
        rPr.append(hl)
    hl.set(qn("w:val"), val)


def recolor_green(p):
    for r in p.runs:
        if r.text.strip().startswith("（翻页）"):
            continue
        set_highlight(r, "green")


def to_embedded(p):
    t = p.text.strip()
    # 去掉已有角色前缀
    for rp in ("项目经理：", "嵌入式工程师：", "AI视觉工程师：", "AI 视觉工程师：", "AI应用工程师：", "AI 应用工程师：", "全体成员："):
        if t.startswith(rp):
            t = t[len(rp):]
            break
    # 保留缩进风格（原稿创新点带缩进，已由 set_text 处理）
    if p.runs:
        p.runs[0].text = "嵌入式工程师：" + t
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run("嵌入式工程师：" + t)
    recolor_green(p)


# 创新段 5 段
targets = [
    "经过持续的研发与实践，项目在技术、模式与场景上形成了多项创新",
    "建立多维度数据融合的 产量预测模型",
    "构建“感知-认知-控制”三层智能体架构",
    "形成“数据+专家+技术+平台”的协同创新模式",
    "第四，场景创新——我们把系统从“大棚”搬到“场景”",
]
for frag in targets:
    p = find_para(doc, frag)
    to_embedded(p)
    print("改派:", p.text[:40])

doc.save(DST)
print("saved:", DST)
