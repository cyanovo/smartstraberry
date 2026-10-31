# -*- coding: utf-8 -*-
"""统计 v2 稿台词字数并估算时长"""
import docx
import io
import re

d = docx.Document("docs/8-14商务稿子-微调对齐版-v2-新.docx")
paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]

CODE_PREFIXES = (
    "def ", "async ", "return", "if ", "for ", "elif ", "#", '"""', "    ", "\t",
    "await ", "client.", "uart.", "raw_data", "addr ", "r =", "sm =", "st =",
    "n  =", "p  =", "k  =", "humidity", "temp", "co2", "illum", "output", "result",
    "retriever", "kwargs", "file_name", "kb_id", "query_text", "chain", "block",
    "details", "all_valid", "hash_ok", "prev_ok", "recalc", "index", "nonce",
)
LIST_PREFIXES = ("1.", "2.", "3.", "4.", "5.", "6.", "7.")
IGNORE_PREFIXES = ("【",)

speech_lines = []
action_lines = []
for t in paras:
    if t.startswith(IGNORE_PREFIXES):
        action_lines.append(t)
        continue
    if t.startswith(LIST_PREFIXES):
        speech_lines.append(t)  # 六大功能列表也算台词
        continue
    if t.startswith(CODE_PREFIXES) or re.match(r"^[a-zA-Z_]", t):
        continue
    speech_lines.append(t)

# 去掉翻页标记、括号注释
def clean(s):
    s = re.sub(r"[（翻页）翻页()]", "", s)
    s = re.sub(r"【示例数据[^】]*】", "", s)
    return s

total = sum(len(clean(t)) for t in speech_lines)
print("台词行数:", len(speech_lines))
print("动作/演示行数:", len(action_lines))
print("台词总字数(去翻页/示例标注):", total)
for wpm in (200, 220, 250):
    print(f"  语速 {wpm} 字/分 -> 纯口播 {total / wpm:.1f} 分钟")

# 分段统计：开头(产业/政策/痛点) vs 技能展示 vs 后段
print("\n--- 分段字数 ---")
segments = {
    "开场+分工+目录(P1-3)": (0, 10),
    "项目介绍(产业/政策/来源/痛点/方案 P4-8)": (10, 36),
    "总体思路(目标/方案/技术链/架构/里程碑 P9-13)": (36, 53),
    "嵌入式展示": (53, 104),
    "AI视觉展示": (104, 131),
    "AI应用展示": (131, 156),
    "区块链展示": (156, 214),
    "设备联动+系统功能": (214, 242),
    "创新+成效+未来": (242, 265),
}
for name, (a, b) in segments.items():
    chars = sum(len(clean(t)) for t in speech_lines if False)  # placeholder
# 用段落索引重算
plist = [p.text.strip() for p in d.paragraphs]
def chars_between(a, b):
    total_c = 0
    for t in plist[a:b]:
        if not t.strip():
            continue
        if t.startswith(("【",)):
            continue
        if t.startswith(CODE_PREFIXES) or re.match(r"^[a-zA-Z_]", t) or t.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.")):
            continue
        total_c += len(clean(t))
    return total_c

for name, (a, b) in segments.items():
    c = chars_between(a, b)
    print(f"{name}: {c} 字 / 200字分={c/200:.1f}min / 220字分={c/220:.1f}min")
