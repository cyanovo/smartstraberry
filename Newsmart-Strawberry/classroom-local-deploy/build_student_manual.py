from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "classroom-local-deploy" / "番茄温室智能管控平台-学生本地部署操作手册.docx"
ASSETS = ROOT / "deliverables" / "manual-assets"

NAVY = "17324D"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
PALE_BLUE = "E8EEF5"
PALE_GREEN = "EAF4EC"
PALE_GOLD = "FFF4CE"
PALE_RED = "FDECEC"
GRAY = "5F6B76"
LIGHT_GRAY = "F2F4F7"
WHITE = "FFFFFF"
BLACK = "222222"


def set_run_font(run, name="Microsoft YaHei", size=11, color=BLACK, bold=False, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold
    run.italic = italic


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa):
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths_dxa[idx] / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=9, color=GRAY)


def add_para(doc, text="", *, bold=False, italic=False, color=BLACK, size=11,
             align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=6, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.keep_with_next = keep
    run = p.add_run(text)
    set_run_font(run, size=size, color=color, bold=bold, italic=italic)
    return p


def add_rich_para(doc, parts, *, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.25
    for text, opts in parts:
        run = p.add_run(text)
        set_run_font(run, **opts)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(text, style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.left_indent = Inches(0.375 + level * 0.25)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.add_run(text)
    for run in p.runs:
        set_run_font(run)
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.left_indent = Inches(0.375)
    p.paragraph_format.first_line_indent = Inches(-0.188)
    p.add_run(text)
    for run in p.runs:
        set_run_font(run)
    return p


def add_code(doc, code):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    shade_cell(cell, "F6F8FA")
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    for idx, line in enumerate(code.splitlines() or [""]):
        if idx:
            p.add_run().add_break()
        set_run_font(p.add_run(line), name="Consolas", size=9.2, color="1F2328")
    add_para(doc, "", after=1)
    return table


def add_callout(doc, label, text, fill=PALE_BLUE, color=NAVY):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    shade_cell(cell, fill)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.2
    r = p.add_run(label + "  ")
    set_run_font(r, bold=True, color=color)
    set_run_font(p.add_run(text), color=color)
    add_para(doc, "", after=1)


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        shade_cell(cell, PALE_BLUE)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_font(p.add_run(header), bold=True, size=9.5, color=NAVY)
    set_repeat_table_header(table.rows[0])
    for row_data in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row_data):
            p = cells[idx].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            set_run_font(p.add_run(value), size=9.3)
    set_table_geometry(table, widths)
    add_para(doc, "", after=1)
    return table


def add_figure(doc, image_path, caption, width=6.15):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(8)
    set_run_font(cap.add_run(caption), size=9, color=GRAY, italic=True)


def page_break(doc):
    doc.add_page_break()


doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5)
sec.page_height = Inches(11)
sec.top_margin = Inches(1)
sec.right_margin = Inches(1)
sec.bottom_margin = Inches(1)
sec.left_margin = Inches(1)
sec.header_distance = Inches(0.492)
sec.footer_distance = Inches(0.492)
sec.different_first_page_header_footer = True

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Microsoft YaHei"
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
normal.font.size = Pt(11)
normal.font.color.rgb = RGBColor.from_string(BLACK)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.25

for name, size, color, before, after in (
    ("Heading 1", 16, BLUE, 18, 10),
    ("Heading 2", 13, BLUE, 14, 7),
    ("Heading 3", 12, DARK_BLUE, 10, 5),
):
    st = styles[name]
    st.font.name = "Microsoft YaHei"
    st._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = RGBColor.from_string(color)
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True

header = sec.header
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
set_run_font(hp.add_run("番茄温室智能管控平台  |  学生本地部署操作手册"), size=8.5, color=GRAY)
footer = sec.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
set_run_font(fp.add_run("学生版  ·  第 "), size=9, color=GRAY)
field(fp, "PAGE")
set_run_font(fp.add_run(" 页"), size=9, color=GRAY)

# Cover: editorial_cover pattern, calibrated for a technical student handbook.
add_para(doc, "STUDENT DEPLOYMENT HANDBOOK", size=10, bold=True, color=BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, before=54, after=24)
add_para(doc, "番茄温室智能管控平台", size=28, bold=True, color=NAVY,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=8)
add_para(doc, "学生本地部署操作手册", size=21, bold=True, color=BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=16)
add_para(doc, "PyCharm 后端 + VS Code 前端", size=14, color=DARK_BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=46)
add_callout(doc, "核心方案", "普通学生在自己的 Windows 电脑运行 FastAPI、任务 Worker 和 Vue 前端；数据库及中间件继续使用 172.168.1.184 上已经部署好的 Docker 节点。Docker 宿主机不做任何修改。", fill=PALE_GREEN, color=NAVY)
add_para(doc, "适用对象：首次接触本项目的普通学生", size=10.5, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER, before=28, after=4)
add_para(doc, "文档版本：2026-09-03", size=10.5, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
add_para(doc, "当前 Docker 节点 IP：172.168.1.184", size=10.5, bold=True, color=DARK_BLUE,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
add_para(doc, "项目示例路径：D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main", size=9, color=GRAY,
         align=WD_ALIGN_PARAGRAPH.CENTER, before=24, after=0)

page_break(doc)
add_heading(doc, "使用前先读", 1)
add_callout(doc, "一句话说明", "你只需要修改 backend\\classroom.env 中的一个 IP，首次双击编译脚本，然后分别用 PyCharm 启动两个后端进程、用 VS Code 启动前端。", fill=PALE_GREEN)
add_heading(doc, "本手册能解决什么", 2)
for item in (
    "准确告诉你应该打开哪个文件夹，而不是笼统地说“打开项目”。",
    "准确告诉你 PyCharm 选择哪个 Python 解释器、运行哪两个 .py 文件。",
    "准确告诉你 VS Code 打开哪个目录、在哪个终端输入什么命令。",
    "说明学生本机与 Docker 节点各自运行什么，避免在学生电脑重复装数据库。",
    "提供启动验证、停止方法、端口冲突处理和按现象排查步骤。",
):
    add_bullet(doc, item)
add_heading(doc, "目录", 2)
for item in (
    "1. 部署架构与学生需要运行的内容",
    "2. 软件和网络准备",
    "3. 只修改一个 IP",
    "4. 首次编译前后端",
    "5. PyCharm 启动后端 API 与 Worker",
    "6. VS Code 启动前端",
    "7. 启动验证与每天的启动顺序",
    "8. 停止、重启和端口冲突",
    "9. 常见问题逐项排查",
    "10. 命令速查与验收清单",
):
    add_bullet(doc, item)
add_callout(doc, "重要", "项目文件夹可以放在别的位置；只要内部的 backend、web、classroom-local-deploy 相对结构不变即可。文中绝对路径是当前电脑上的示例。", fill=PALE_GOLD, color="6A4B00")

page_break(doc)
add_heading(doc, "1. 部署架构与学生需要运行的内容", 1)
add_para(doc, "本方案不是把 Docker 内容拆到每台学生电脑，而是让学生运行会频繁修改和调试的前后端代码；共享状态服务继续集中在已经部署好的 Docker 节点。")
add_table(doc, ["位置", "由谁运行", "具体内容", "是否需要学生安装"], [
    ("学生电脑", "每名普通学生", "FastAPI API、ARQ Worker、Vue/Vite 前端、摄像头与成熟度模型", "需要"),
    ("Docker 节点 172.168.1.184", "已完成 Docker 部署的同学", "PostgreSQL、Redis、MinIO、Milvus、Neo4j、Sandbox；可选 MinerU/PaddleX", "不需要"),
], [1800, 1700, 4100, 1760])
add_heading(doc, "为什么 SQLite 不适合多人共享", 2)
add_para(doc, "SQLite 是单文件数据库，适合单机和轻量场景。多人通过网络共享同一个 SQLite 文件时，容易出现锁竞争、文件损坏风险和权限问题。本方案把共享业务数据、溯源数据统一写入 Docker 节点上的 PostgreSQL；Redis 负责队列，每台学生电脑自动生成独立队列名，避免互相抢任务。")
add_heading(doc, "学生本地进程关系", 2)
add_table(doc, ["进程", "入口", "作用", "默认地址/端口"], [
    ("后端 API", "backend\\run_classroom_api.py", "接收前端请求，连接共享数据库和中间件", "127.0.0.1:5050"),
    ("后端 Worker", "backend\\run_classroom_worker.py", "处理当前学生提交的智能体异步任务", "独立学生队列"),
    ("前端", "web 目录执行 pnpm run dev", "提供浏览器界面，代理到本机后端", "127.0.0.1:5173"),
], [1700, 2850, 3250, 1560])
add_callout(doc, "不允许的操作", "普通学生不要在自己的电脑启动本项目 Docker Compose，也不要修改 172.168.1.184 上的 Compose、容器、镜像或环境变量。", fill=PALE_RED, color="7A1F1F")

page_break(doc)
add_heading(doc, "2. 软件和网络准备", 1)
add_heading(doc, "2.1 必装软件", 2)
add_table(doc, ["软件", "要求", "验证命令", "用途"], [
    ("Python", "3.12 x64", "py -3.12 --version", "后端与模型"),
    ("Node.js", "24 x64 或更高", "node --version", "前端工具链"),
    ("Git", "可用版本", "git --version", "获取/更新代码"),
    ("PyCharm", "Community/Professional 均可", "打开后端目录", "运行 API 与 Worker"),
    ("VS Code", "当前稳定版", "打开 web 目录", "运行和编辑前端"),
], [1500, 1850, 2300, 3710])
add_heading(doc, "2.2 网络前提", 2)
add_para(doc, "学生电脑与 172.168.1.184 必须处于可以互相访问的局域网。节点需允许学生访问以下 TCP 端口：")
add_table(doc, ["服务", "端口", "用途", "基础启动是否必须"], [
    ("PostgreSQL", "5432", "共享业务数据与溯源数据", "是"),
    ("Redis", "6379", "任务队列与状态", "是"),
    ("MinIO", "9000", "共享对象文件", "是"),
    ("Milvus", "19530", "向量检索", "是"),
    ("Neo4j", "7687", "知识图谱", "是"),
    ("Sandbox", "8002", "代码沙盒分配", "是"),
    ("MinerU", "30001", "可选文档解析", "否"),
    ("PaddleX", "8080", "可选 OCR", "否"),
], [1900, 1200, 4100, 2160])
add_callout(doc, "当前实测（2026-09-03）", "172.168.1.184 的 5432、6379、9000、19530、7687、8002 均不可达。生成本手册时节点处于离线或端口未开放状态；学生启动前必须先让 Docker 节点恢复在线。", fill=PALE_GOLD, color="6A4B00")

page_break(doc)
add_heading(doc, "3. 第一次拿到项目：只修改一个 IP", 1)
add_heading(doc, "3.1 找到配置文件", 2)
add_para(doc, "打开项目根目录，再进入 backend 文件夹，打开下面这个文件：")
add_code(doc, r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend\classroom.env")
add_para(doc, "文件只保留一项配置：")
add_code(doc, "CLASSROOM_NODE_HOST=172.168.1.184")
add_heading(doc, "3.2 修改规则", 2)
for item in (
    "如果 Docker 节点 IP 仍是 172.168.1.184，不需要改任何内容。",
    "如果老师通知节点 IP 已变化，只替换等号右侧的 IPv4 地址。",
    "不要填写 http://，不要加端口，不要加引号，不要添加空格。",
    "不要手工修改前端地址、数据库地址、Redis 地址或其他源码。",
):
    add_bullet(doc, item)
add_heading(doc, "3.3 系统会自动完成的配置", 2)
add_para(doc, "后端读取这个 IP 后，会自动生成 PostgreSQL、Redis、MinIO、Milvus、Neo4j、OCR 与 Sandbox 地址；学生实例 ID 与任务队列名根据本机自动生成；前端默认只连接学生本机的 5050 端口。")
add_callout(doc, "检查点", "保存文件后重新打开，确认没有变成 classroom.env.txt。Windows 资源管理器建议开启“文件扩展名”显示。", fill=PALE_GOLD, color="6A4B00")

page_break(doc)
add_heading(doc, "4. 首次编译前后端", 1)
add_heading(doc, "4.1 打开正确文件夹", 2)
add_para(doc, "在 Windows 文件资源管理器打开：")
add_code(doc, r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\classroom-local-deploy")
add_heading(doc, "4.2 双击编译脚本", 2)
add_code(doc, "student-compile.cmd")
add_para(doc, "也可以从 PowerShell 执行：")
add_code(doc, "cd D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\n.\\classroom-local-deploy\\student-compile.cmd")
add_heading(doc, "4.3 编译脚本具体做什么", 2)
for item in (
    "验证 Python 3.12 和 Node.js 24+。",
    "安装 uv 0.7.2，并在 backend\\.venv 创建 Python 虚拟环境。",
    "按 backend\\uv.lock 安装后端依赖。",
    "如本机没有 pnpm，安装 pnpm 10.11.0。",
    "按前端锁文件安装 web\\node_modules，并执行一次生产构建。",
):
    add_number(doc, item)
add_callout(doc, "耗时提示", "首次安装包含 PyTorch、OCR 和文档解析依赖，下载量较大，可能持续十几分钟或更久。必须等到窗口显示成功提示，不能中途关闭。", fill=PALE_GOLD, color="6A4B00")
add_para(doc, "成功标志：", bold=True, color=DARK_BLUE)
add_code(doc, "Backend dependencies and frontend production build are ready.")

page_break(doc)
add_heading(doc, "5. 编译完成后先做环境检查", 1)
add_para(doc, "仍在 classroom-local-deploy 文件夹中双击：")
add_code(doc, "student-doctor.cmd")
add_para(doc, "或者在项目根目录运行：")
add_code(doc, ".\\classroom-local-deploy\\student-doctor.cmd")
add_heading(doc, "5.1 正常结果", 2)
add_para(doc, "PostgreSQL、Redis、MinIO、Milvus、Neo4j、Sandbox 都应显示 [OK]，并且本机 backend\\.venv 与 web\\node_modules 存在。")
add_heading(doc, "5.2 全部显示 [FAIL] 时", 2)
for item in (
    "确认 172.168.1.184 对应电脑已经开机，Docker 服务已经由负责同学启动。",
    "确认学生电脑与节点电脑在同一个可互访网络，不是访客 Wi-Fi 或隔离网络。",
    "确认 backend\\classroom.env 的 IP 没有抄错。",
    "让负责 Docker 的同学检查主机防火墙和端口开放；普通学生不要自行改节点。",
):
    add_number(doc, item)
add_callout(doc, "停止条件", "只要 PostgreSQL 或 Redis 不通，就不要继续启动 PyCharm 后端。网络/节点问题无法靠重复运行 Python 解决。", fill=PALE_RED, color="7A1F1F")

page_break(doc)
add_heading(doc, "6. 用 PyCharm 启动后端", 1)
add_heading(doc, "6.1 PyCharm 必须打开 backend 文件夹", 2)
for item in (
    "启动 PyCharm，点击 File → Open。",
    "选择 D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\\backend。",
    "点击 Open as Project；若出现安全提示，选择 Trust Project。",
):
    add_number(doc, item)
add_para(doc, "左侧项目树顶层应直接看到：")
add_code(doc, "package\nserver\ntest\nrun_classroom_api.py\nrun_classroom_worker.py\nclassroom.env\npyproject.toml")
add_callout(doc, "层级判断", "如果 PyCharm 左侧最上层显示 test1-main，说明打开层级过高。关闭项目，重新只打开 backend 文件夹。", fill=PALE_GOLD, color="6A4B00")
add_heading(doc, "6.2 选择正确解释器", 2)
for item in (
    "点击 File → Settings → Project → Python Interpreter。",
    "点击 Add Interpreter → Add Local Interpreter。",
    "选择 Existing environment。",
    "定位到 backend\\.venv\\Scripts\\python.exe，保存。",
):
    add_number(doc, item)
add_code(doc, r"D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend\.venv\Scripts\python.exe")

page_break(doc)
add_heading(doc, "7. PyCharm 启动后端 API 与 Worker", 1)
add_heading(doc, "7.1 启动 API", 2)
for item in (
    "在 PyCharm 左侧找到 run_classroom_api.py。",
    "右键文件，选择 Run 'run_classroom_api'。",
    "保持下方 Run 窗口打开，等待 Application startup complete。",
    "浏览器打开健康检查地址，确认返回 status=ok。",
):
    add_number(doc, item)
add_code(doc, "http://127.0.0.1:5050/api/system/health\nhttp://127.0.0.1:5050/docs")
add_para(doc, "不用右键时，也可以在 PyCharm Terminal 中运行：")
add_code(doc, "cd D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\\backend\n.\\.venv\\Scripts\\python.exe .\\run_classroom_api.py")
add_heading(doc, "7.2 启动 Worker", 2)
add_para(doc, "API 保持运行，再在项目树中右键 run_classroom_worker.py，选择 Run 'run_classroom_worker'。PyCharm 下方应同时保留 API 和 Worker 两个运行标签。")
add_code(doc, ".\\.venv\\Scripts\\python.exe .\\run_classroom_worker.py")
add_callout(doc, "必须同时运行", "只有 API 没有 Worker 时，登录和普通查询可能正常，但智能体异步任务会一直停在 pending。", fill=PALE_RED, color="7A1F1F")

page_break(doc)
add_heading(doc, "8. 用 VS Code 启动前端", 1)
add_heading(doc, "8.1 VS Code 必须打开 web 文件夹", 2)
for item in (
    "启动 VS Code，点击 File → Open Folder。",
    "选择 D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\\web。",
    "点击 Select Folder。",
    "点击 Terminal → New Terminal，确认提示符路径最后是 \\web。",
):
    add_number(doc, item)
add_heading(doc, "8.2 运行前端", 2)
add_code(doc, "pnpm run dev")
add_para(doc, "终端会显示类似下面的地址：")
add_code(doc, "Local: http://127.0.0.1:5173/")
add_para(doc, "浏览器打开终端实际显示的 Local 地址。如果 5173 已占用，Vite 可能改用 5174 或 5175，以终端输出为准。")
add_callout(doc, "后端地址无需再改", "前端已经默认代理到学生本机 http://127.0.0.1:5050。不要把前端 API 地址改成 172.168.1.184；共享节点不运行学生前端 API。", fill=PALE_GREEN)
if (ASSETS / "frontend-login.png").exists():
    add_figure(doc, ASSETS / "frontend-login.png", "图 1  本次实际启动的前端登录页（页面主体已正常渲染；顶部 502 提示来自当前 Docker 节点离线）", width=6.15)

page_break(doc)
add_heading(doc, "9. 启动验证与每天的启动顺序", 1)
add_heading(doc, "9.1 三层验证", 2)
add_table(doc, ["层次", "检查方法", "通过标准", "失败时先查"], [
    ("节点", "student-doctor.cmd", "6 个基础服务均为 [OK]", "节点开机、同一网络、IP、防火墙"),
    ("后端", "访问 /api/system/health", "返回 status: ok", "API 日志、解释器、节点服务"),
    ("前端", "打开 Vite Local 地址", "登录页正常，且无服务连接失败", "API 是否运行、前端代理、端口"),
    ("异步任务", "提交一次智能体任务", "状态能从 pending 继续变化", "Worker 是否运行"),
], [1300, 2450, 2500, 3110])
add_heading(doc, "9.2 每天启动顺序", 2)
for item in (
    "确认 Docker 节点电脑已由负责同学启动。",
    "双击 student-doctor.cmd，确认节点在线。",
    "PyCharm 运行 run_classroom_api.py。",
    "等待 Application startup complete。",
    "PyCharm 运行 run_classroom_worker.py。",
    "VS Code 的 web 终端执行 pnpm run dev。",
    "打开终端显示的前端 Local 地址。",
):
    add_number(doc, item)
add_heading(doc, "9.3 首次安装与日常启动的区别", 2)
add_table(doc, ["操作", "首次拿到项目", "每天启动", "代码依赖变化后"], [
    ("student-compile.cmd", "需要", "不需要", "建议重新运行"),
    ("student-doctor.cmd", "需要", "需要", "需要"),
    ("API + Worker + 前端", "需要", "需要", "需要"),
], [2700, 2100, 2100, 2460])

page_break(doc)
add_heading(doc, "10. 停止、重启和端口冲突", 1)
add_heading(doc, "10.1 正确停止", 2)
for item in (
    "在 PyCharm 中分别点击 Stop，停止 API 和 Worker。",
    "在 VS Code Terminal 中按 Ctrl+C，停止 Vite 前端。",
    "关闭学生本机进程不会停止 Docker 节点，也不会影响其他学生。",
):
    add_bullet(doc, item)
add_heading(doc, "10.2 5050 或 5173 被占用", 2)
add_para(doc, "优先关闭占用端口的旧进程。普通学生不要同时运行 Docker 版后端和 PyCharm 版后端。确实需要临时换端口时，后端与前端必须成对修改：")
add_code(doc, "# PyCharm/PowerShell 后端临时使用 15050\ncd D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\\backend\n$env:API_PORT=\"15050\"\n.\\.venv\\Scripts\\python.exe .\\run_classroom_api.py")
add_code(doc, "# VS Code 前端同时指向 15050，并临时使用 15173\ncd D:\\work\\strawberry\\Newsmart-Strawberry\\test2\\test1-main\\web\n$env:VITE_API_URL=\"http://127.0.0.1:15050\"\npnpm run dev -- --port 15173")
add_para(doc, "此时访问 http://127.0.0.1:15173。关闭对应 Terminal 后，临时环境变量自动失效，不会改动仓库文件。")

page_break(doc)
add_heading(doc, "11. 常见问题逐项排查", 1)
add_heading(doc, "11.1 前端显示“服务连接失败”或 502", 2)
add_para(doc, "这表示前端页面本身已启动，但本机 FastAPI 没有正常响应。依次检查：")
for item in (
    "PyCharm 的 run_classroom_api.py 是否仍在运行。",
    "API 日志是否已经出现 Application startup complete。",
    "http://127.0.0.1:5050/api/system/health 是否能打开。",
    "student-doctor.cmd 是否存在 [FAIL]。",
    "如果改了 API_PORT，VS Code 是否同步设置 VITE_API_URL。",
):
    add_number(doc, item)
if (ASSETS / "frontend-backend-offline.png").exists():
    add_figure(doc, ASSETS / "frontend-backend-offline.png", "图 2  本次实际启动时出现的后端不可达页面；当前 172.168.1.184 节点离线会触发此现象", width=6.15)
add_heading(doc, "11.2 PyCharm 提示 No module named uvicorn / arq", 2)
add_para(doc, "原因通常是解释器选错，或 student-compile.cmd 没成功。把解释器改回 backend\\.venv\\Scripts\\python.exe；没有 .venv 时重新运行编译脚本。")
add_heading(doc, "11.3 智能体任务一直 pending", 2)
add_para(doc, "确认 run_classroom_worker.py 正在运行，并且 API 与 Worker 来自同一份项目、使用同一个 .venv。")

page_break(doc)
add_heading(doc, "12. 更多故障现象", 1)
add_table(doc, ["现象", "最可能原因", "处理方法"], [
    ("doctor 全部 [FAIL]", "节点关机、IP 错误、网络隔离或防火墙", "恢复节点；确认同网；检查 classroom.env；联系节点同学"),
    ("只有某个端口 [FAIL]", "对应容器未运行或端口未开放", "让 Docker 负责人检查对应服务；学生端不改 Compose"),
    ("后端启动后很久没有完成", "首次导入重依赖、加载模型，或等待节点连接", "继续看日志；先确认 doctor 全绿；等待完成标志"),
    ("前端页面能开但登录失败", "API 未完成启动、节点数据库不可达", "先访问健康检查，再看 PyCharm API 日志"),
    ("找不到 .venv", "首次编译未成功", "重新运行 student-compile.cmd，保留完整错误信息"),
    ("pnpm 不是内部命令", "Node/npm 未正确安装或环境变量未刷新", "重装 Node.js 24 x64；重开终端；再运行编译脚本"),
    ("classroom.env 修改无效", "文件扩展名变成 .txt，或运行了另一份项目", "显示扩展名；核对 PyCharm 打开的 backend 绝对路径"),
    ("5173 打不开", "Vite 没运行或自动换了端口", "查看 VS Code 终端 Local 行，按实际端口访问"),
], [2500, 3000, 3860])
add_callout(doc, "提交问题时请带上", "student-doctor.cmd 完整输出、PyCharm API 最后 50 行日志、Worker 最后 50 行日志、VS Code 终端错误、backend\\classroom.env（只包含节点 IP）以及项目绝对路径。", fill=PALE_BLUE)

page_break(doc)
add_heading(doc, "13. 命令速查", 1)
add_heading(doc, "首次编译（项目根目录）", 2)
add_code(doc, ".\\classroom-local-deploy\\student-compile.cmd")
add_heading(doc, "节点与本地环境检查（项目根目录）", 2)
add_code(doc, ".\\classroom-local-deploy\\student-doctor.cmd")
add_heading(doc, "后端 API（PyCharm 打开 backend）", 2)
add_code(doc, ".\\.venv\\Scripts\\python.exe .\\run_classroom_api.py")
add_heading(doc, "后端 Worker（PyCharm 第二个运行标签/终端）", 2)
add_code(doc, ".\\.venv\\Scripts\\python.exe .\\run_classroom_worker.py")
add_heading(doc, "前端（VS Code 打开 web）", 2)
add_code(doc, "pnpm run dev")
add_heading(doc, "常用访问地址", 2)
add_table(doc, ["用途", "地址"], [
    ("前端", "http://127.0.0.1:5173"),
    ("后端健康检查", "http://127.0.0.1:5050/api/system/health"),
    ("后端接口文档", "http://127.0.0.1:5050/docs"),
], [2600, 6760])

page_break(doc)
add_heading(doc, "14. 最终验收清单", 1)
for item in (
    "□ backend\\classroom.env 只配置了 CLASSROOM_NODE_HOST=172.168.1.184。",
    "□ student-compile.cmd 已显示成功提示。",
    "□ backend\\.venv\\Scripts\\python.exe 存在。",
    "□ web\\node_modules 存在。",
    "□ student-doctor.cmd 的 6 个基础服务全部 [OK]。",
    "□ PyCharm 只打开 backend 文件夹。",
    "□ PyCharm 解释器是 backend\\.venv\\Scripts\\python.exe。",
    "□ run_classroom_api.py 已出现 Application startup complete。",
    "□ run_classroom_worker.py 保持运行。",
    "□ VS Code 只打开 web 文件夹，并执行 pnpm run dev。",
    "□ /api/system/health 返回 status=ok。",
    "□ 前端登录页无“服务连接失败”提示。",
    "□ 提交智能体任务后不再长期停留在 pending。",
):
    add_bullet(doc, item)
add_heading(doc, "完成标准", 2)
add_callout(doc, "部署成功", "节点检测全绿、API 健康检查正常、Worker 在运行、前端可以访问并完成一次真实业务操作。达到这四项后，学生本地部署才算完成。", fill=PALE_GREEN)
add_para(doc, "本方案对 Docker 宿主机零改动；所有新增入口、配置与启动脚本均位于普通学生拿到的项目副本中。", bold=True, color=NAVY, before=18, after=4)

doc.core_properties.title = "番茄温室智能管控平台 - 学生本地部署操作手册"
doc.core_properties.subject = "PyCharm 后端与 VS Code 前端本地部署"
doc.core_properties.author = "项目教学部署组"
doc.core_properties.keywords = "学生部署, PyCharm, VS Code, FastAPI, Vue, Docker共享节点"
update_fields = OxmlElement("w:updateFields")
update_fields.set(qn("w:val"), "true")
doc.settings.element.append(update_fields)

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
