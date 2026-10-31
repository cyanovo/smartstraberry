# -*- coding: utf-8 -*-
"""
v3 补全：给无前缀台词按上下文补角色前缀（不改文字）。
归属规则：
  段 55            -> 项目经理（派活）
  段 106-137       -> AI 视觉工程师（训练/测试/检测演示）
  段 141/142/143/151 -> AI 应用工程师（知识库检索环节）
  段 207-210       -> 项目经理（区块链存证页面操作）
  段 235-241       -> AI 视觉工程师（系统功能列表讲解）
"""
import os

from docx import Document

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v3-新.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v3-新.docx")

doc = Document(SRC)
paras = doc.paragraphs


def set_text(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run(text)


PREFIXES = ("项目经理：", "嵌入式工程师：", "AI视觉工程师：", "AI 视觉工程师：",
            "AI应用工程师：", "AI 应用工程师：", "全体成员：")

assign = {
    55: "项目经理：",
    141: "AI 应用工程师：",
    142: "AI 应用工程师：",
    143: "AI 应用工程师：",
    151: "AI 应用工程师：",
    207: "项目经理：",
    208: "项目经理：",
    209: "项目经理：",
    210: "项目经理：",
}
# AI 视觉训练/测试/检测演示段（106-137 范围内的台词）
for i in range(106, 138):
    assign.setdefault(i, "AI 视觉工程师：")
# 系统功能列表（235-241）
for i in range(235, 242):
    assign.setdefault(i, "AI 视觉工程师：")

changed = 0
for idx, prefix in assign.items():
    t = paras[idx].text.strip()
    if not t:
        continue
    if t.startswith(PREFIXES):
        continue
    if t == "（翻页）":
        continue
    set_text(paras[idx], prefix + t)
    changed += 1

doc.save(DST)
print("补前缀完成，修改段落数:", changed)
