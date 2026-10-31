# -*- coding: utf-8 -*-
"""检查 docx 各段落 run 的背景色/highlight 分配"""
import re
import sys

import docx


def inspect(path, max_paras=40, out=None):
    d = docx.Document(path)
    lines = []
    for i, p in enumerate(d.paragraphs):
        t = p.text.strip()
        if not t:
            continue
        if i > max_paras:
            break
        lines.append(f"--- 段{i} 样式={p.style.name} runs={len(p.runs)}")
        for j, r in enumerate(p.runs[:3]):
            xml = r._r.xml
            h = re.findall(r'w:highlight w:val="([^"]+)"', xml)
            s = re.findall(r'<w:shd[^>]*w:fill="([^"]+)"', xml)
            color = r.font.color.rgb if (r.font.color and r.font.color.type is not None) else None
            lines.append(
                f"  run{j}: {r.text[:16]!r} highlight={h} shd={s} color={color} bold={r.font.bold}"
            )
    text = "\n".join(lines)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print("written:", out)
    else:
        print(text)


if __name__ == "__main__":
    base = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs"
    inspect(base + r"\8-14商务稿子-微调对齐版.docx", out=r"C:\Users\cyan\AppData\Local\Temp\orig_runs.txt")
    inspect(base + r"\8-14商务稿子-微调对齐版-v4-新.docx", out=r"C:\Users\cyan\AppData\Local\Temp\v4_runs.txt")
