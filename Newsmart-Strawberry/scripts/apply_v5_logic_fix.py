# -*- coding: utf-8 -*-
"""
v5 逻辑修复（基于用户修改后的 v4-颜色修复.docx）：
A. 删除 P10 整段 + 两个空段
B. 补角色前缀（同步设置背景色）
C. 微调文字（衔接/语病/称呼/数字残留）
"""
import copy
import os
import re

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v4-颜色修复.docx")
DST = os.path.join(BASE, "docs", "8-14商务稿子-微调对齐版-v5-逻辑修复.docx")

ROLE_COLOR = {
    "项目经理": "yellow",
    "嵌入式工程师": "green",
    "AI视觉工程师": "cyan",
    "AI应用工程师": "darkCyan",
}


def find_para(doc, *fragments):
    """按多个文本片段之一定位段落（返回第一个匹配）"""
    for p in doc.paragraphs:
        t = p.text.strip()
        for frag in fragments:
            if frag in t:
                return p
    raise SystemExit(f"未找到段落: {fragments[0]!r}")


def find_all(doc, frag):
    return [p for p in doc.paragraphs if frag in p.text]


def delete_para(p):
    p._p.getparent().remove(p._p)


def set_text(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        p.add_run(text)


def set_highlight(run, val):
    rPr = run._r.get_or_add_rPr()
    hl = rPr.find(qn("w:highlight"))
    if val is None:
        if hl is not None:
            rPr.remove(hl)
        return
    if hl is None:
        hl = rPr.makeelement(qn("w:highlight"), {})
        rPr.append(hl)
    hl.set(qn("w:val"), val)


def recolor(p, color):
    for r in p.runs:
        if r.text.strip().startswith("（翻页）"):
            continue
        set_highlight(r, color)


def prefix(p, role, extra=None):
    """补角色前缀 + 可选附加文字，并上色"""
    t = p.text.strip()
    for rp in ("项目经理", "嵌入式工程师", "AI视觉工程师", "AI应用工程师"):
        if t.startswith(rp + "：") or t.startswith("AI " + rp + "："):
            return  # 已有前缀
    new_text = role + "：" + (extra or "") + t
    set_text(p, new_text)
    recolor(p, ROLE_COLOR[role])
    return p


doc = Document(SRC)

# ============ A. 删除 ============
# A1. 删除 P10 整段：从"下面有请我们团队AI应用工程师针对发现的痛点"到"解决方案与三大痛点一一对应"
start = find_para(doc, "下面有请我们团队AI应用工程师针对发现的痛点")
end = find_para(doc, "解决方案与三大痛点一一对应")
# 收集 [start, end] 之间的所有段落（含 start/end）
to_delete = []
in_range = False
for p in doc.paragraphs:
    if p._p is start._p:
        in_range = True
    if in_range:
        to_delete.append(p)
    if p._p is end._p:
        break
for p in to_delete:
    delete_para(p)
print("A1 删除 P10 段数:", len(to_delete))

# A2. 删除空段："AI应用工程师：" 和 "AI视觉工程师："（文本恰好等于角色名的段）
for frag in ("AI应用工程师：", "AI视觉工程师："):
    for p in find_all(doc, frag):
        t = p.text.strip()
        if t in ("AI应用工程师：", "AI 应用工程师：", "AI视觉工程师：", "AI 视觉工程师："):
            delete_para(p)
            print("A2 删除空段:", t)

# ============ B. 补角色前缀（含颜色） ============
# 项目经理（yellow）
prefix(find_para(doc, "为了系统性破解番茄种植的共性难题"), "项目经理")
prefix(find_para(doc, "“识土”是对番茄生长环境"), "项目经理")
prefix(find_para(doc, "嵌入式工程师，请接收任务，开始传感器数据采集"), "项目经理")
prefix(find_para(doc, "接下来AI视觉工程师请接收环境数据和标注数据"), "项目经理")
prefix(find_para(doc, "点击右上角的 “+新增地块”"), "项目经理")
prefix(find_para(doc, "在“地块管理”中，可以查看所有地块"), "项目经理")
prefix(find_para(doc, "切换到“种子列表”"), "项目经理")
prefix(find_para(doc, "有了地块和种子，我们就可以开始种植了"), "项目经理")
prefix(find_para(doc, "建立多维度数据融合的 产量预测模型"), "项目经理")
prefix(find_para(doc, "构建“感知-认知-控制”三层智能体架构"), "项目经理")
prefix(find_para(doc, "形成“数据+专家+技术+平台”的协同创新模式"), "项目经理")

# AI 视觉工程师（cyan）：训练/测试/检测讲解段
for frag in (
    "我已经将图片集按照7：2：1",
    "接下来我将实现yolo模块的开发",
    "第一步，加载yolo默认模型",
    "第二步，配置训练模型的相关参数",
    "模型训练开发完成",
    "(详细介绍并编写test.py文件的代码)",
    "我们需要测试模型的性能",
    "添加路径配置",
    "为了提升程序的健壮性",
    "测试前先做有效性校验",
    "选择最佳计算设备",
    "接下来配置模型的关键参数",
    "模型测试模块开发完成",
    "点击运行测试模块",
    "首先，我们来看一下我们最初构建模型的性能表现",
    "从提供的精确度曲线中",
    "为了解决问题，我们引入了多模态数据",
    "同样通过我们的评估曲线",
    "接下来启用训练好的模型进行成熟度识别",
    "本项目基于YOLO算法成功开发",
    "我已完成模型在真实环境下的验证",
):
    prefix(find_para(doc, frag), "AI视觉工程师")

# AI 应用工程师（darkCyan）
prefix(find_para(doc, "收到。痛点三由我解决"), "AI应用工程师")
prefix(find_para(doc, "在前期，我已收集整理番茄种植领域"), "AI应用工程师")
prefix(find_para(doc, "代码完成权限校验、知识库检索"), "AI应用工程师")

# ============ C. 微调文字 ============
# C1. 目录句补"项目介绍"
p = find_para(doc, "首先进入第一部分")
set_text(p, "项目经理：首先进入第一部分，项目介绍。（翻页）")
recolor(p, ROLE_COLOR["项目经理"])

# C2. P6 衔接（删校园标牌后）
p = find_para(doc, "秉持着服务产业的理念，我们意识到这些种植难题可能具有普遍性")
set_text(p, "项目经理：我们把这些烦恼带到调研中，发现这类种植难题可能具有普遍性。")
recolor(p, ROLE_COLOR["项目经理"])

# C3. 嵌入式汇报语病
p = find_para(doc, "接下来继续进行优化传感器数据")
set_text(p, "嵌入式工程师：报告项目经理，我已完成RS485传感器读取、Modbus数据解析和MQTT数据上传，数据已上传至系统，请验收。")
recolor(p, ROLE_COLOR["嵌入式工程师"])

# C4. 称呼统一：AI应用开发工程师 -> AI应用工程师
p = find_para(doc, "接下来有请AI应用开发工程师完成番茄知识库权限验证")
set_text(p, "AI视觉工程师：接下来有请AI应用工程师完成番茄知识库权限验证、向量检索、来源标注和大模型辅助分析任务。")
recolor(p, ROLE_COLOR["AI视觉工程师"])

# C5. 知识库检索函数删"6"
p = find_para(doc, "下面由我来向大家展示知识库检索函数")
set_text(p, "AI应用工程师：下面由我来向大家展示知识库检索函数。（翻页）")
recolor(p, ROLE_COLOR["AI应用工程师"])

# C6. 创新段"三点创新"->"多项创新"（后面有第四点场景创新）
p = find_para(doc, "项目形成了以下三点创新")
set_text(p, "项目经理：经过持续的研发与实践，项目在技术、模式与场景上形成了多项创新。（翻页）")
recolor(p, ROLE_COLOR["项目经理"])

# C7. 成效段衔接：删P10后"进入应用价值与未来规划"改为"以上是实践成效，下面进入未来规划"
p = find_para(doc, "下面进入应用价值与未来规划")
set_text(p, "项目经理：以上是项目的实践成效，下面进入未来规划。（翻页）")
recolor(p, ROLE_COLOR["项目经理"])

doc.save(DST)
print("saved:", DST)
