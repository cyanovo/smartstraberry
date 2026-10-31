# -*- coding: utf-8 -*-
"""
在 逐字稿修复版.docx 的 13 处指定位置末尾追加红色"（翻页）"标记。
只追加标记，不修改任何其他内容（保留所有 run、颜色、角色前缀）。
"""
import os

from docx import Document
from docx.shared import RGBColor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "逐字稿修复版.docx")
DST = os.path.join(BASE, "逐字稿修复版-翻页标记.docx")

MARKER = "（翻页）"
RED = RGBColor(0xC0, 0x00, 0x00)

# 13 处锚点：用段落末尾的关键片段匹配（必须存在于修复版当前文本中）
ANCHORS = [
    "我们才能在一个学期内完成从硬件到软件的全链路开发",
    "能不能用技术，把\"靠经验\"变成\"靠数据\"",
    "探索从经验管理向数据驱动、智能决策和可信溯源转变",
    "这让我们明白：土地是可以被技术改变的",
    "生成预期产量、采摘时机和病害防治建议等关键决策",
    "这正是我们区块链溯源的基础",
    "代码讲解完成，现在运行程序",
    "空气温湿度、二氧化碳、光照，以及土壤温湿度、电导率、pH、氮磷钾数值均正常读取",
    "可以部署在低成本边缘设备上",
    "严格遵循《知识元提取与标引》GB/T 45257",
    "对番茄生产过程中的关键数据进行存证",
    "所有农事操作、环境数据等都将被系统自动记录",
    "这说明系统能够检测区块数据内容变化和前后链式异常",
]

doc = Document(SRC)
added = 0
unmatched = []

for anchor in ANCHORS:
    hit = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if anchor in t:
            # 该段已含翻页则跳过
            if MARKER in t:
                print(f"  跳过（已有翻页）: {anchor[:20]}…")
                hit = p
                break
            hit = p
            break
    if hit is None:
        unmatched.append(anchor)
        continue
    # 在段末追加红色（翻页）
    r = hit.add_run(MARKER)
    r.font.bold = True
    r.font.color.rgb = RED
    added += 1

print(f"\n已追加翻页标记: {added} 处")
if unmatched:
    print("未匹配到位置:")
    for a in unmatched:
        print("  -", a)

doc.save(DST)
print("saved:", DST)
