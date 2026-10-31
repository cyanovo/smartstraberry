# -*- coding: utf-8 -*-
"""验证最终版：3 处修复 + 角色颜色 + 假数据标注"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\vibe\最终版-53分定向修改.docx"
d = docx.Document(PATH)
text = "\n".join(p.text for p in d.paragraphs)
# 表格内容也纳入文本（表格内文字不在 paragraphs 中）
for t in d.tables:
    for row in t.rows:
        for cell in row.cells:
            text += "\n" + cell.text

print("=== 1. 修复点检查 ===")
checks = [
    ("旧标准号已清除", "42756" not in text),
    ("新标准号正确", "GB/T 42755-2023" in text),
    ("联盟链已清除", "联盟链" not in text),
    ("轻量级本地链存在", "轻量级本地区块链" in text),
    ("选型表与正文统一(96.0%)", "96.0%" in text),
    ("旧精度0.96保留", "0.96" in text),
    ("GB/T 37093已删", "37093" not in text),
    ("假数据标注-3棚", "3 个合作棚【示例数据，待替换】" in text),
    ("假数据标注-100ms", "100 毫秒以内【示例数据，待替换】" in text),
    ("假数据标注-里程碑", "【示例数据，待替换：按真实开发记录核对】" in text),
    ("假数据标注-番茄展", "番茄展会【示例数据，待替换" in text),
    ("假数据标注-成本", "1.2 万元【示例数据，待替换】" in text),
    ("异常场景演示", "拔掉了土壤传感器的通信线" in text),
    ("技术选型对比表", "ResNet-50" in text),
    ("区块链选型对比", "公有链（以太坊）" in text),
    ("风险与挑战", "运营风险" in text),
    ("质量保障", "缺陷跟踪" in text),
]
for name, ok in checks:
    print(f"  {'✓' if ok else '✗'} {name}")

print("\n=== 2. 角色颜色 ===")
ROLE_COLOR = {
    "项目经理：": "yellow", "嵌入式工程师：": "green",
    "AI视觉工程师：": "cyan", "AI 视觉工程师：": "cyan",
    "AI应用工程师：": "darkCyan", "AI 应用工程师：": "darkCyan",
    "全体成员：": None,
}
bad = 0
checked = 0
for p in d.paragraphs:
    t = p.text.strip()
    if not t:
        continue
    role = None
    for pfx in ROLE_COLOR:
        if t.startswith(pfx):
            role = pfx
            break
    if role is None:
        continue
    checked += 1
    m = re.search(r'w:highlight w:val="([^"]+)"', p.runs[0]._r.xml) if p.runs else None
    actual = m.group(1) if m else None
    if actual != ROLE_COLOR[role]:
        bad += 1
        print(f"  错位: [{role}] 期望={ROLE_COLOR[role]} 实际={actual} | {t[:24]}")
print(f"  检查 {checked} 段，不匹配 {bad} 段")
print("\n总段落:", len(d.paragraphs))
