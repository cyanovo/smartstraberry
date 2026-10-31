# -*- coding: utf-8 -*-
"""统计 v2 稿各角色台词字数与占比"""
import docx
import re

d = docx.Document("docs/8-14商务稿子-微调对齐版-v5-逻辑修复.docx")
paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]

CODE_PREFIXES = (
    "def ", "async ", "return", "if ", "for ", "elif ", "#", '"""', "    ", "\t",
    "await ", "client.", "uart.", "raw_data", "addr ", "r =", "sm =", "st =",
    "n  =", "p  =", "k  =", "humidity", "temp", "co2", "illum", "output", "result",
    "retriever", "kwargs", "file_name", "kb_id", "query_text", "chain", "block",
    "details", "all_valid", "hash_ok", "prev_ok", "recalc", "index", "nonce",
)
LIST_PREFIXES = ("1.", "2.", "3.", "4.", "5.", "6.", "7.")

roles = {}
other = []
for t in paras:
    if t.startswith("【"):
        continue
    if t.startswith(("项目经理：", "项目经理：")):
        key = "项目经理"
        body = t[len("项目经理："):]
    elif t.startswith(("嵌入式工程师：", "嵌入式工程师：")):
        key = "嵌入式工程师"
        body = t[len("嵌入式工程师："):]
    elif t.startswith(("AI视觉工程师：", "AI 视觉工程师：")):
        key = "AI视觉工程师"
        body = t[len("AI视觉工程师："):]
    elif t.startswith(("AI应用工程师：", "AI 应用工程师：")):
        key = "AI应用工程师"
        body = t[len("AI应用工程师："):]
    elif t.startswith(("全体成员：", "全体成员：")):
        key = "全体成员"
        body = t[len("全体成员："):]
    else:
        if t.startswith(CODE_PREFIXES) or re.match(r"^[a-zA-Z_]", t) or t.startswith(LIST_PREFIXES):
            continue
        key = "（无前缀台词）"
        body = t
    body = re.sub(r"[（翻页）翻页()]", "", body)
    body = re.sub(r"【示例数据[^】]*】", "", body)
    roles[key] = roles.get(key, 0) + len(body)

total = sum(roles.values())
print(f"{'角色':<14}{'字数':>6}{'占比':>8}")
for k, v in sorted(roles.items(), key=lambda x: -x[1]):
    print(f"{k:<14}{v:>6}{v/total*100:>7.1f}%")
print(f"\n总台词字数: {total}")
