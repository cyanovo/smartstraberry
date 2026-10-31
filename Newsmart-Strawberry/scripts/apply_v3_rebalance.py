# -*- coding: utf-8 -*-
"""
v3：基于 v2-新.docx 重平衡角色分工。
原则：人岗匹配（谁讲的内容贴近谁的岗位）、项目经理减负（他还有区块链实操+指令下发）。
只改角色前缀/拆段，不动台词文字。
"""
import copy
import os

from docx import Document
from docx.text.paragraph import Paragraph

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v2-新.docx")
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


def insert_after(anchor, text):
    new_el = copy.deepcopy(anchor._p)
    anchor._p.addnext(new_el)
    np = Paragraph(new_el, anchor._parent)
    set_text(np, text)
    return np


def strip_prefix(t, prefix):
    return t[len(prefix):] if t.startswith(prefix) else t


# ============ 锚点校验 ============
checks = [
    (11, "项目经理：在介绍项目之前"),
    (12, "项目经理：番茄是全球消费量最大的蔬菜之一"),
    (14, "项目经理：河南省"),
    (17, "项目经理：刚入校园"),
    (18, "项目经理：项目的起点"),
    (19, "项目经理：我们看在眼里"),
    (20, "项目经理：在老师和省农科院专家"),
    (24, "为了系统性破解番茄种植的共性难题"),
    (37, "“识土”是对番茄生长环境"),
    (38, "项目经理：面向落地"),
    (45, "项目经理：“工欲善其事，必先利其器”"),
    (46, "项目经理：基于搭建的技术链"),
    (47, "项目经理：第二层，传输层"),
    (48, "项目经理：第三层，服务层"),
    (49, "项目经理：第四层，决策层"),
    (50, "项目经理：第五层，应用层"),
    (51, "项目经理：这个项目我们按项目化方式推进"),
    (243, "建立多维度数据融合"),
    (244, "构建“感知-认知-控制”"),
    (245, "形成“数据+专家+技术+平台”"),
    (246, "项目经理：第四，场景创新"),
    (252, "项目经理：合作赋能方面"),
    (254, "项目经理：如何证明我们种出的番茄好吃"),
    (255, "项目经理：成本方面"),
    (256, "项目经理：商业模式上"),
]
for idx, expect in checks:
    actual = paras[idx].text.strip()
    if expect not in actual:
        raise SystemExit(f"锚点校验失败 idx={idx}: 期望含 {expect!r}，实际 {actual[:40]!r}")
print("锚点校验全部通过（%d 处）" % len(checks))

# ============ 第二幕：产业分析 / 政策 / 校园故事 分流 ============
# P4 产业分析：开场句留项目经理（主持），产业分析两段给 AI 应用工程师（知识性内容）
set_text(paras[12], "AI 应用工程师：" + strip_prefix(paras[12].text.strip(), "项目经理："))
set_text(paras[13], "AI 应用工程师：" + strip_prefix(paras[13].text.strip(), "项目经理："))
# P5 政策背景：给 AI 应用工程师（标准/政策归知识岗）
set_text(paras[14], "AI 应用工程师：" + strip_prefix(paras[14].text.strip(), "项目经理："))
set_text(paras[15], "AI 应用工程师：" + strip_prefix(paras[15].text.strip(), "项目经理："))
set_text(paras[16], "AI 应用工程师：" + strip_prefix(paras[16].text.strip(), "项目经理："))
# P6 校园故事：标牌/家菜园/功勋感召 给 AI 视觉工程师（故事性，呼应他"识图看世界"）
set_text(paras[17], "AI 视觉工程师：" + strip_prefix(paras[17].text.strip(), "项目经理："))
set_text(paras[18], "AI 视觉工程师：" + strip_prefix(paras[18].text.strip(), "项目经理："))
set_text(paras[19], "AI 视觉工程师：" + strip_prefix(paras[19].text.strip(), "项目经理："))
# 调研句补前缀（原无前缀）
set_text(paras[24], "项目经理：" + paras[24].text.strip())

# ============ 第三幕：识土识图使谱 拆分三人 + 目标/技术链/架构/里程碑 分流 ============
# P9 识土识图使谱：1 段拆 3 段，按领域归人
t37 = paras[37].text.strip()
t37 = strip_prefix(t37, "项目经理：")
parts = [s for s in t37.split("；") if s.strip()]
# 期望 3 段：识土 / 识图 / 使谱
if len(parts) >= 3:
    set_text(paras[37], "嵌入式工程师：" + parts[0] + "；")
    p2 = insert_after(paras[37], "AI 视觉工程师：" + parts[1] + "；")
    insert_after(p2, "AI 应用工程师：" + parts[2] + "。")
else:
    raise SystemExit("识土识图使谱拆分失败，parts=%r" % parts)
# P9 短/长期目标 → AI 应用工程师
set_text(paras[38], "AI 应用工程师：" + strip_prefix(paras[38].text.strip(), "项目经理："))
# P11 技术链 → AI 应用工程师（RAG/大模型领域）
set_text(paras[45], "AI 应用工程师：" + strip_prefix(paras[45].text.strip(), "项目经理："))
# P12 架构五层：感知/传输→嵌入式，服务→AI应用，决策→AI视觉，应用→AI应用
set_text(paras[46], "嵌入式工程师：" + strip_prefix(paras[46].text.strip(), "项目经理："))
set_text(paras[47], "嵌入式工程师：" + strip_prefix(paras[47].text.strip(), "项目经理："))
set_text(paras[48], "AI 应用工程师：" + strip_prefix(paras[48].text.strip(), "项目经理："))
set_text(paras[49], "AI 视觉工程师：" + strip_prefix(paras[49].text.strip(), "项目经理："))
set_text(paras[50], "AI 应用工程师：" + strip_prefix(paras[50].text.strip(), "项目经理："))
# P13 里程碑 → AI 应用工程师（项目化管理/进度）
set_text(paras[51], "AI 应用工程师：" + strip_prefix(paras[51].text.strip(), "项目经理："))

# ============ 第九幕 创新：三点按领域归人 ============
set_text(paras[243], "AI 视觉工程师：" + paras[243].text.strip().lstrip())
set_text(paras[244], "AI 应用工程师：" + paras[244].text.strip().lstrip())
set_text(paras[245], "项目经理：" + paras[245].text.strip().lstrip())
# 场景创新 → AI 应用工程师
set_text(paras[246], "AI 应用工程师：" + strip_prefix(paras[246].text.strip(), "项目经理："))

# ============ 第十幕 成效：合作赋能→嵌入式 / 番茄展→AI视觉 / 成本→嵌入式 / 商业模式→AI应用 ============
set_text(paras[252], "嵌入式工程师：" + strip_prefix(paras[252].text.strip(), "项目经理："))
set_text(paras[254], "AI 视觉工程师：" + strip_prefix(paras[254].text.strip(), "项目经理："))
set_text(paras[255], "嵌入式工程师：" + strip_prefix(paras[255].text.strip(), "项目经理："))
set_text(paras[256], "AI 应用工程师：" + strip_prefix(paras[256].text.strip(), "项目经理："))

doc.save(DST)
print("saved:", DST)
