"""Local desktop workbench for dataset preparation and YOLO results."""

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from common import ROOT
from dataset_import import CLASSES, inspect, prepare


class Workbench(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("草莓视觉工作台")
        self.geometry("1080x740")
        self.minsize(780, 570)
        self.configure(background="#f4f7f7")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f4f7f7")
        self.style.configure("TLabel", background="#f4f7f7", foreground="#263b3b", font=("Microsoft YaHei UI", 10))
        self.style.configure("Title.TLabel", font=("Microsoft YaHei UI", 17, "bold"), foreground="#153d3b")
        self.style.configure("Section.TLabel", font=("Microsoft YaHei UI", 11, "bold"))
        self.style.configure("Muted.TLabel", foreground="#657575")
        self.style.configure("TButton", padding=(12, 7), font=("Microsoft YaHei UI", 9))
        self.style.configure("Accent.TButton", background="#137b69", foreground="white")
        self.style.map("Accent.TButton", background=[("active", "#0e6558"), ("disabled", "#b7c9c5")])
        self.style.configure("TNotebook", background="#f4f7f7", borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(18, 9), font=("Microsoft YaHei UI", 10))
        self.style.configure("TLabelframe", background="#f4f7f7", padding=10)
        self.style.configure("TLabelframe.Label", background="#f4f7f7", foreground="#263b3b", font=("Microsoft YaHei UI", 10, "bold"))
        self.records = []
        self.mapping = {}
        self.camera_stop = threading.Event()
        self.frames = queue.Queue(maxsize=2)
        self.camera_worker = None
        self.job_events = queue.Queue()
        self.data_busy = False
        self.chart_photo = None
        self.chart_image = None
        self.chart_path = None
        self.chart_resize_job = None
        self.preview_photo = None
        self.camera_size = None
        self.displayed_frame = None
        self.closing = False
        self.protocol("WM_DELETE_WINDOW", self.close)
        heading = ttk.Frame(self, padding=(20, 16, 20, 3))
        heading.pack(fill="x")
        ttk.Label(heading, text="草莓视觉工作台", style="Title.TLabel").pack(side="left")
        ttk.Label(heading, text="数据集  /  训练结果  /  摄像头", style="Muted.TLabel").pack(side="right")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=(6, 4))
        self.data_tab = ttk.Frame(tabs, padding=16)
        self.chart_tab = ttk.Frame(tabs, padding=16)
        self.camera_tab = ttk.Frame(tabs, padding=16)
        tabs.add(self.data_tab, text="数据准备")
        tabs.add(self.chart_tab, text="训练图表")
        tabs.add(self.camera_tab, text="摄像头检测")
        self.build_data()
        self.build_charts()
        self.build_camera()
        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, style="Muted.TLabel", padding=(22, 5)).pack(fill="x", side="bottom")
        self.camera_timer = self.after(50, self.poll_camera)
        self.job_timer = self.after(100, self.poll_jobs)

    def path_row(self, parent, label, variable, action):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=6)
        ttk.Label(row, text=label, width=10).pack(side="left")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="选择...", command=action).pack(side="left")

    def build_data(self):
        ttk.Label(self.data_tab, text="数据准备", style="Title.TLabel").pack(anchor="w")
        self.source = tk.StringVar()
        source_group = ttk.LabelFrame(self.data_tab, text="来源")
        source_group.pack(fill="x", pady=(12, 8))
        self.path_row(source_group, "图片与 XML", self.source, self.choose_source)
        action_row = ttk.Frame(source_group)
        action_row.pack(fill="x", pady=(3, 2))
        self.inspect_button = ttk.Button(action_row, text="检查数据", command=self.scan, style="Accent.TButton")
        self.inspect_button.pack(side="right")
        self.summary = tk.StringVar(value="等待选择数据文件夹")
        ttk.Label(self.data_tab, textvariable=self.summary, style="Section.TLabel").pack(anchor="w", pady=(7, 4))
        body = ttk.Frame(self.data_tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, minsize=250)
        body.columnconfigure(1, weight=3, minsize=280)
        body.rowconfigure(0, weight=1)
        self.map_frame = ttk.LabelFrame(body, text="类别映射")
        self.map_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=6)
        ttk.Label(self.map_frame, text="检查后在此确认类别", style="Muted.TLabel").pack(anchor="w")
        issues_frame = ttk.LabelFrame(body, text="检查结果")
        issues_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=6)
        self.errors = tk.Text(issues_frame, height=8, state="disabled", wrap="word", relief="flat", padx=10, pady=9,
                              background="#ffffff", foreground="#263b3b", font=("Microsoft YaHei UI", 10))
        self.errors.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(issues_frame, command=self.errors.yview)
        scrollbar.pack(side="right", fill="y")
        self.errors.configure(yscrollcommand=scrollbar.set)
        output = ttk.Frame(self.data_tab)
        output.pack(fill="x", pady=(10, 0))
        ttk.Label(output, text=f"输出到  {ROOT / 'dataset'}", style="Muted.TLabel").pack(side="left", fill="x", expand=True)
        self.make_button = ttk.Button(output, text="生成 7:2:1 数据集", command=self.generate, state="disabled", style="Accent.TButton")
        self.make_button.pack(side="right")

    def choose_source(self):
        if self.data_busy:
            return
        chosen = filedialog.askdirectory(title="选择解压后的图片和 XML 文件夹")
        if chosen:
            self.source.set(chosen)
            self.records = []
            self.make_button.configure(state="disabled")

    def scan(self):
        if self.data_busy:
            return
        self.make_button.configure(state="disabled")
        for child in self.map_frame.winfo_children():
            child.destroy()
        self.mapping = {}
        self.summary.set("正在检查图片与标注...")
        self.status.set("正在检查数据")
        self.run_job("scan", inspect, self.source.get())

    def show_scan(self, result):
        self.records, counts, issues = result
        self.summary.set(f"有效图片 {len(self.records)} 张；标注类别：{dict(counts)}；问题 {len(issues)} 项")
        self.status.set(f"检查完成 · {len(issues)} 项问题" if issues else "检查完成 · 请确认类别映射")
        self.errors.configure(state="normal")
        self.errors.delete("1.0", "end")
        self.errors.insert("end", "\n".join(issues) if issues else "检查通过。确认每个来源类别对应的训练类别。")
        self.errors.configure(state="disabled")
        for name, count in sorted(counts.items()):
            row = ttk.Frame(self.map_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=f"{name} ({count} 框)").pack(side="left", fill="x", expand=True)
            value = tk.StringVar(value="请选择")
            ttk.Combobox(row, textvariable=value, values=("请选择",) + CLASSES, state="readonly", width=12).pack(side="right")
            self.mapping[name] = value
        if self.records and not issues:
            self.make_button.configure(state="normal")

    def generate(self):
        if self.data_busy:
            return
        mapping = {name: value.get() for name, value in self.mapping.items()}
        if any(value not in CLASSES for value in mapping.values()):
            messagebox.showwarning("未确认类别", "请为每个来源类别选择目标类别。")
            return
        if not messagebox.askyesno("确认生成", f"将复制图片并转换 XML 到 {ROOT / 'dataset'}。原文件不会修改。\n类别映射：{mapping}\n继续？"):
            return
        self.summary.set("正在生成数据集...")
        self.status.set("正在生成数据集")
        self.run_job("generate", self.generate_dataset, self.source.get(), self.records, mapping)

    @staticmethod
    def generate_dataset(source, records, mapping):
        current, _, issues = inspect(source)
        if issues or [(r[0], r[1], r[4], r[5]) for r in current] != [(r[0], r[1], r[4], r[5]) for r in records]:
            raise ValueError("源数据已变化或存在问题，请重新检查。")
        return prepare(current, mapping)

    def run_job(self, kind, operation, *args):
        self.data_busy = True
        self.inspect_button.configure(state="disabled")
        self.make_button.configure(state="disabled")

        def work():
            try:
                self.job_events.put((kind, operation(*args), None))
            except Exception as exc:
                self.job_events.put((kind, None, exc))

        threading.Thread(target=work, daemon=True).start()

    def poll_jobs(self):
        if self.closing:
            return
        try:
            while True:
                kind, result, error = self.job_events.get_nowait()
                self.data_busy = False
                self.inspect_button.configure(state="normal")
                if error:
                    self.summary.set("操作未完成")
                    self.status.set("操作未完成")
                    messagebox.showerror("处理失败", str(error))
                elif kind == "scan":
                    self.show_scan(result)
                else:
                    self.summary.set(f"已生成：训练 {result['train']} / 验证 {result['val']} / 测试 {result['test']}")
                    self.status.set("数据集已生成")
                    messagebox.showinfo("生成完成", "数据集已生成，可使用默认 data.yaml 训练。")
        except queue.Empty:
            pass
        self.job_timer = self.after(100, self.poll_jobs)

    def build_charts(self):
        ttk.Label(self.chart_tab, text="训练图表", style="Title.TLabel").pack(anchor="w")
        self.run_dir = tk.StringVar()
        controls = ttk.Frame(self.chart_tab)
        controls.pack(fill="x", pady=(12, 10))
        self.path_row(controls, "训练目录", self.run_dir, self.choose_run)
        self.chart_names = tk.StringVar()
        row = ttk.Frame(self.chart_tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="查看图表", width=10).pack(side="left")
        self.chart_box = ttk.Combobox(row, textvariable=self.chart_names, state="readonly", width=48)
        self.chart_box.pack(side="left", padx=6)
        self.chart_box.bind("<<ComboboxSelected>>", lambda _: self.show_chart())
        self.chart_area = ttk.Label(self.chart_tab, anchor="center", text="选择训练目录查看图表")
        self.chart_area.pack(fill="both", expand=True)
        self.chart_area.bind("<Configure>", self.schedule_chart)

    def schedule_chart(self, _event=None):
        if self.chart_resize_job is not None:
            self.after_cancel(self.chart_resize_job)
        self.chart_resize_job = self.after(150, self.show_chart)

    def choose_run(self):
        chosen = filedialog.askdirectory(title="选择 runs/<实验名>/train 目录", initialdir=str(ROOT / "runs"))
        if chosen:
            self.run_dir.set(chosen)
            self.load_charts()

    def load_charts(self):
        directory = Path(self.run_dir.get())
        plots = sorted(directory.glob("*.png"))
        self.chart_box["values"] = [p.name for p in plots]
        if not plots:
            self.chart_names.set("")
            self.chart_area.configure(image="", text="没有找到图表")
            return
        self.chart_names.set("results.png" if (directory / "results.png").exists() else plots[0].name)
        self.show_chart()

    def show_chart(self):
        self.chart_resize_job = None
        path = Path(self.run_dir.get()) / self.chart_names.get()
        if not path.is_file():
            return
        try:
            if path != self.chart_path:
                with Image.open(path) as source:
                    self.chart_image = source.copy()
                self.chart_path = path
            image = self.chart_image.copy()
            width = max(self.chart_area.winfo_width() - 10, 1)
            height = max(self.chart_area.winfo_height() - 10, 1)
            image.thumbnail((width, height))
            self.chart_photo = ImageTk.PhotoImage(image)
            self.chart_area.configure(image=self.chart_photo, text="")
        except OSError as exc:
            self.chart_area.configure(image="", text=str(exc))

    def build_camera(self):
        ttk.Label(self.camera_tab, text="摄像头检测", style="Title.TLabel").pack(anchor="w")
        self.model_path = tk.StringVar()
        self.path_row(self.camera_tab, "模型文件", self.model_path, self.choose_model)
        row = ttk.Frame(self.camera_tab)
        row.pack(fill="x", pady=8)
        self.camera_index = tk.IntVar(value=0)
        self.confidence = tk.DoubleVar(value=0.25)
        self.device = tk.StringVar(value="cpu")
        ttk.Label(row, text="摄像头编号").pack(side="left")
        ttk.Spinbox(row, from_=0, to=20, textvariable=self.camera_index, width=5).pack(side="left", padx=8)
        ttk.Label(row, text="置信度").pack(side="left")
        ttk.Spinbox(row, from_=0.01, to=1, increment=0.05, textvariable=self.confidence, width=6).pack(side="left", padx=8)
        ttk.Label(row, text="设备").pack(side="left")
        ttk.Combobox(row, values=("cpu", "0"), textvariable=self.device, state="readonly", width=6).pack(side="left", padx=8)
        self.start_button = ttk.Button(row, text="启动", command=self.start_camera)
        self.start_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(row, text="停止", command=self.stop_camera, state="disabled")
        self.stop_button.pack(side="left")
        ttk.Button(row, text="保存截图", command=self.save_snapshot).pack(side="left", padx=8)
        self.camera_status = tk.StringVar(value="选择可信的 YOLO 检测权重")
        ttk.Label(self.camera_tab, textvariable=self.camera_status).pack(anchor="w", pady=5)
        self.camera_area = ttk.Label(self.camera_tab, anchor="center", text="等待摄像头画面")
        self.camera_area.pack(fill="both", expand=True)
        self.camera_area.bind("<Configure>", lambda _: self.render_frame())
        self.last_frame = None

    def choose_model(self):
        chosen = filedialog.askopenfilename(title="选择可信的模型", initialdir=str(ROOT / "runs"), filetypes=[("PyTorch weights", "*.pt")])
        if chosen:
            self.model_path.set(chosen)

    def start_camera(self):
        path = Path(self.model_path.get())
        try:
            index, conf = self.camera_index.get(), self.confidence.get()
            if not path.is_file() or path.suffix.lower() != ".pt" or index < 0 or not 0 <= conf <= 1:
                raise ValueError("请选择可信的 .pt 文件、有效摄像头编号和 0-1 置信度")
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("参数错误", str(exc))
            return
        if not messagebox.askyesno("加载模型", "PyTorch 权重可能执行代码。请只加载自己训练或可信来源的模型。继续？"):
            return
        self.camera_stop.clear()
        self.last_frame = None
        self.preview_photo = None
        self.displayed_frame = None
        self.camera_area.configure(image="", text="正在打开摄像头...")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.camera_status.set("正在加载模型并打开摄像头...")
        self.camera_worker = threading.Thread(target=self.camera_loop, args=(path, index, conf, self.device.get()), daemon=True)
        self.camera_worker.start()

    def camera_loop(self, path, index, conf, device):
        import cv2
        from ultralytics import YOLO
        camera = None
        try:
            model = YOLO(str(path))
            if model.task != "detect":
                raise ValueError("模型不是目标检测模型")
            self.post(("status", f"检测中 | 类别：{model.names}"))
            camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not camera.isOpened():
                raise RuntimeError("无法打开摄像头；检查权限、编号及占用")
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            while not self.camera_stop.is_set():
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("摄像头画面读取失败")
                plotted = model.predict(source=frame, device=device, conf=conf, imgsz=640, verbose=False)[0].plot()
                rgb = cv2.cvtColor(plotted, cv2.COLOR_BGR2RGB)
                self.post(("frame", Image.fromarray(rgb)))
        except Exception as exc:
            self.post(("status", f"检测停止：{exc}"))
        finally:
            if camera is not None:
                camera.release()
            self.post(("done", None))

    def post(self, item):
        try:
            self.frames.put_nowait(item)
        except queue.Full:
            if item[0] != "frame":
                try:
                    self.frames.get_nowait()
                except queue.Empty:
                    pass
                self.frames.put_nowait(item)

    def poll_camera(self):
        if self.closing:
            return
        latest = None
        try:
            while True:
                kind, value = self.frames.get_nowait()
                if kind == "frame":
                    latest = value
                elif kind == "status":
                    self.camera_status.set(value)
                elif kind == "done":
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
        except queue.Empty:
            pass
        if latest is not None:
            self.last_frame = latest
            self.render_frame()
        self.camera_timer = self.after(100, self.poll_camera)

    def render_frame(self):
        if self.last_frame is None:
            return
        size = (max(1, self.camera_area.winfo_width() - 10), max(1, self.camera_area.winfo_height() - 10))
        if size == self.camera_size and self.preview_photo is not None and self.last_frame is self.displayed_frame:
            return
        image = self.last_frame.copy()
        image.thumbnail(size)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.camera_size = size
        self.displayed_frame = self.last_frame
        self.camera_area.configure(image=self.preview_photo, text="")

    def stop_camera(self):
        self.camera_stop.set()
        self.camera_status.set("正在停止摄像头...")

    def save_snapshot(self):
        if self.last_frame is None:
            messagebox.showinfo("无画面", "请先启动摄像头。")
            return
        name = filedialog.asksaveasfilename(title="保存检测截图", defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if name:
            try:
                self.last_frame.save(name)
            except OSError as exc:
                messagebox.showerror("保存失败", str(exc))

    def close(self):
        self.closing = True
        self.camera_stop.set()
        for timer in (self.camera_timer, self.job_timer, self.chart_resize_job):
            if timer is not None:
                self.after_cancel(timer)
        self.destroy()


if __name__ == "__main__":
    Workbench().mainloop()
