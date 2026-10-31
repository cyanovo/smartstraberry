# -*- coding: utf-8 -*-
"""打印段31 run0 的 rPr 内部 XML（不含命名空间前缀）"""
import re

import docx

PATH = r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\docs\8-14商务稿子-微调对齐版-v4-颜色修复.docx"
d = docx.Document(PATH)
p = d.paragraphs[31]
r = p.runs[0]
xml = r._r.xml
# 提取 rPr 标签内容
m = re.search(r"<w:rPr>(.*?)</w:rPr>", xml, re.S)
if m:
    inner = m.group(1)
    # 去掉命名空间声明，只保留标签和属性
    print("rPr 内部:")
    print(inner)
else:
    print("未找到 w:rPr，完整XML:")
    print(xml)
