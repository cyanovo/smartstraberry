# -*- coding: utf-8 -*-
"""全面检查最终版 docx"""
import re

import docx

d = docx.Document("docs/vibe/最终版-53分定向修改.docx")
lines = []

lines.append("=== 1. 段落与表格 ===")
lines.append(f"段落: {len(d.paragraphs)} 表格: {len(d.tables)} 有文字段: {sum(1 for p in d.paragraphs if p.text.strip())}")

lines.append("\n=== 2. 翻页标记统计 ===")
total = sum(p.text.count("（翻页）") for p in d.paragraphs)
lines.append(f"段落中（翻页）总数: {total}")

lines.append("\n=== 3. 角色颜色检查 ===")
ROLE = {
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
    for pfx in ROLE:
        if t.startswith(pfx):
            role = pfx
            break
    if role is None:
        continue
    checked += 1
    m = re.search(r'w:highlight w:val="([^"]+)"', p.runs[0]._r.xml) if p.runs else None
    actual = m.group(1) if m else None
    if actual != ROLE[role]:
        bad += 1
        lines.append(f"  错位: [{role}] 期望={ROLE[role]} 实际={actual} | {t[:24]}")
lines.append(f"角色段: {checked}, 错位: {bad}")

lines.append("\n=== 4. 开头/结尾抽查 ===")
for i, p in enumerate(d.paragraphs[:12]):
    if p.text.strip():
        lines.append(f"  开头 {i}: {p.text.strip()[:40]}")
tail = [p.text.strip() for p in d.paragraphs if p.text.strip()][-3:]
for t in tail:
    lines.append(f"  结尾: {t[:40]}")

lines.append("\n=== 5. 关键内容存在性 ===")
full = "\n".join(p.text for p in d.paragraphs)
for kw in ("Git进行代码版本管理", "异常场景", "GB/T 42755-2023", "轻量级本地区块链", "风险与挑战", "缺陷跟踪",
           "0.23", "0.96", "96.0%", "2.8 万元", "番茄展会"):
    lines.append(f"  {'OK' if kw in full else 'MISSING'} | {kw}")

with open(r"C:\Users\cyan\AppData\Local\Temp\final_check.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written")
