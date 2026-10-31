# 三号视觉训练工程

## 草莓病虫害检测（独立数据与模型）

`train.py`、`test.py`、`predict.py` 和原有成熟度 `data.yaml` 均无需修改。新增数据准备脚本将原始病害分割多边形转换为目标检测外接框，输出到独立的 `dataset_disease/`；七类包含果实白粉病（ID 5）和叶片白粉病（ID 6）。病害与成熟度必须分别训练、分别使用自己的权重，病害模型不自动接入业务平台。

在 `strawberry_vision` 目录运行（原包路径、授权和核验情况见 [草莓病虫害数据集说明](草莓病虫害数据集说明.md)）：

```powershell
.\.venv\Scripts\python.exe prepare_disease_dataset.py
.\.venv\Scripts\python.exe train.py --data data_disease.yaml --model weights/yolo26n.pt --device cpu --name disease_v1
.\.venv\Scripts\python.exe test.py --data data_disease.yaml --model runs/disease_v1/train/weights/best.pt --name disease_v1_test
.\.venv\Scripts\python.exe predict.py --model runs/disease_v1/train/weights/best.pt --source dataset_disease/images/test/实际图片.jpg --name disease_v1_image
```

将单图命令中的 `实际图片.jpg` 换成真实路径；每次实验 `--name` 必须唯一。确认 CUDA 可用后可将训练/评估的 `--device cpu` 改为 `--device 0`。原包尚未提供给学生，学生需在授权允许的范围内独立取得并核对数据资源，代码更新不得覆盖其现有数据、权重或训练记录。脚本遇到已有 `dataset_disease/` 会停止，不覆盖它；`conversion_report.json` 记录各类实例数和 4 行被裁剪的坐标。转换后的外接框可能包含较多背景，应人工抽检、检查跨划分近重复和类别语义，再做正式训练。本包只包含七种病害，没有昆虫虫害类别；若要识别虫害，还需要另找合规的虫害图片和标注，另行训练或扩充数据。尚无经正式训练和独立测试验收的病害权重；上述命令是操作方法，不代表模型已达到实用精度。

## 桌面工作台

在本目录运行 `.\.venv\Scripts\python.exe vision_gui.py`。界面包含数据准备、训练图表与摄像头检测三个标签页。数据准备选择已解压的图片与 Pascal VOC XML 文件夹，先检查配对、图片尺寸、框边界及类别，然后逐类确认映射；生成后图片和 YOLO TXT 分别进入 `dataset/images/{train,val,test}` 与 `dataset/labels/{train,val,test}`，默认 `data.yaml` 可以直接供 `train.py` 使用。固定随机种子按 7:2:1 划分，完全相同图片保持同组；少于 10 个独立组、缺标、空 XML 或已经存在 `dataset` 时拒绝写入。原件不变，生成 `dataset/manifest.csv` 留存文件哈希和划分。对于同植株连续帧、近似重复或多个批次，应在正式训练前人工检查跨集合泄漏；目前只自动隔离字节相同的图片。

训练完成后在图表页选择 `runs/<实验名>/train`，查看框架生成的 `results.png`、PR/F1/召回率图、混淆矩阵等 PNG。模型权重本身不含完整训练曲线。摄像头页选择自己训练的 `runs/<实验名>/train/weights/best.pt`，设置编号、阈值与 CPU/GPU，启动或停止实时预览，也可以保存当前检测截图。仅加载可信的 `.pt` 文件；摄像头演示不是测试集精度评估。已有 `test.py` 继续负责独立测试。GUI 不替代训练命令，也不会写入或覆盖已有模型、数据集与实验记录。

## 学生从这里开始

公开数据集更新：已从 Kaggle 下载 566 张草莓图片及 566 个多边形标签，实际共 1,734 个目标。下载包没有类别编号表或正式划分，且与论文统计有差异；当前保持原始文件独立，不直接套用下方教学三类编号。来源、许可、本地路径及接入前检查见 [公开数据集下载说明](公开数据集下载说明.md)。

最新数据准备状态：已参考公开数据集定义 `unripe / turning / ripe` 三类，并在 `annotation_review_v01` 生成 7 张本地图片的 YOLO 标注草稿与画框预览。详细依据、14 个框的统计、去重和数据授权边界见 [类别与标注规范](类别与标注规范.md)。这批数据尚待人工复核，未划分正式训练/验证/测试集。

已确认学生没有独立的训练入口、测试脚本、数据配置或依赖说明。因此直接使用本目录新建的 `train.py`、`test.py`、`data.yaml` 和 `requirements.txt`，不再等待学生提供旧工程。代码依据下面所列原 PPT 截图整理。

配套材料：[模型权重路径说明](模型权重路径说明.md)、[评估报告模板](评估报告模板.md)。前者说明初始权重、训练结果和评估输出放在哪里；后者是待实测填写的模板，不是已完成评估报告。数据类别仍需与二号确认，训练结果必须由实际运行产生。

## 先看了什么，再生成什么

2026-10-21 重新核查时发现：完整 Python 训练工程尚未找到，但原 PPT 中有三号的实际代码截图。此前“完全没有训练代码”的判断不准确，应改为“找到了截图，未找到对应源文件、权重和数据配置”。

- 原训练截图：`../.green-build/old/image101.png`，来自原演示材料第 18 页，包含 `YOLO("yolov8n.pt")`、`model.train(...)`、`model.val()` 和 Windows 入口保护。
- 原测试截图：`../.green-build/old/image105.png`，来自原演示材料第 19 页，包含 YAML 路径读取、`weights/bch.pt`、`YOLO(...).val(split="test")` 和指标写入。
- 原逐字稿提取：`../.green-build/script.txt`，P21—P24。
- 前端接口：`../Smart-Strawberry-front/src/views/system/starryCluster/index.vue`，包含模型切换与 Base64 图片检测调用。Python 服务端仍未找到。
- 同级其他项目中找到的 `jzg/yolo-training/scripts/train.py` 是金针菇工程，不是本项目三号代码，没有拿它替代草莓工程。

这次生成的是**依据截图还原调用结构并修正后的新源文件**，不是找回了完整原工程，也不是已经训练成功的成品。

## 选 YOLO11 还是更新版本

建议：**YOLO26n 作为新训练的候选主线，YOLO11n 作为兼容对照；先进行小规模环境验证，再用固定数据评估定版。** 如果已有部署环境仅验证过 YOLO11，则先维持该部署版本，待 YOLO26 通过同样验收后再切换。模型更新不自动代表草莓识别更好。

本次在线核对 Ultralytics 官方文档及包信息：YOLO26 已有正式训练、验证和推理用法；YOLO27 在当前文档中仍标记为未发布预览，不作为本次比赛主线。Ultralytics 包版本与模型代际不同：`ultralytics==8.4.183` 可以包含 YOLO26，包名中的 8 不表示只能使用 YOLOv8。

| 方案 | 与现有代码的关系 | 本次安排 |
|---|---|---|
| YOLO11n | 沿用 `YOLO`、`train`、`val` API | 参数 `--model weights/yolo11n.pt` 切换，用于对照 |
| YOLO26n | 同样保留上述调用结构；模型及导出内部不同 | 默认本地权重 `weights/yolo26n.pt` |
| 未发布预览或其他研究分支 | 不能仅凭版本编号判断兼容性 | 不引入当前教学工程 |

官方报告的通用数据集精度、CPU 加速等指标不是本项目实测指标。YOLO26 的推理头与导出设置应按固定版本文档核查，不能假定与 YOLO11 的原始 ONNX 输出完全一样。本工程使用 Ultralytics 高层 API，不手写解码，不修改现有前端 HTTP 协议。

官方来源：

- [YOLO26](https://docs.ultralytics.com/models/yolo26/)
- [YOLO11](https://docs.ultralytics.com/models/yolo11/)
- [训练模式](https://docs.ultralytics.com/modes/train/)
- [验证模式](https://docs.ultralytics.com/modes/val/)
- [本次固定包版本](https://pypi.org/project/ultralytics/8.4.183/)

## 文件说明

| 文件 | 用途 |
|---|---|
| `train.py` | 加载本地初始权重，训练，再加载实际 best.pt 在验证集评估 |
| `test.py` | 保留原截图的独立测试集评估，而不是单图推理 |
| `predict.py` | 新增单图检测展示，与正式评估分开 |
| `common.py` | 本地路径、配置基本检查、新输出目录、指标 JSON |
| `data.yaml` | 数据目录配置及三类教学类别表；正式数据目录仍待准备 |
| `requirements.txt` | 固定 Ultralytics 和 YAML 解析器版本；不是完整依赖锁文件 |
| `tests/test_common.py` | 不依赖真实模型的路径与配置测试 |

## 对原代码做了哪些调整

1. 保留训练截图中的 `epochs=100`、`batch=8`、`imgsz=640` 作为默认值；它们不是已验证最优参数。模型改为可选择本地 YOLO26n/YOLO11n。
2. 保留 `if __name__ == "__main__"`，数据加载 `workers=0` 便于 Windows 初次验证；设备默认 CPU，GPU 需显式指定 `--device 0`。
3. 原训练截图的 `os.makedirs(...)` 只创建目录，不会把 `metrics` 写成报告；新代码从实际 `metrics.save_dir` 保存 `metrics.json`。
4. 原测试截图使用 `if not (目录存在 or 权重存在)`，只会在两个都不存在时报错。新代码分别检查模型和必需数据目录，任意缺失都报错。
5. 原截图把 `save_dir` 直接传给 `val()`；新代码使用公开的 `project` / `name` 参数，并从返回对象读取实际路径。
6. 数据 YAML 中 `path` 相对 YAML 文件解析，再写出本轮绝对路径副本；不依赖 PyCharm 终端恰好处于哪个目录。
7. 原截图按 `enumerate(metrics.names)` 取名字，在字典形式下可能得到编号；现在把原始类别映射写入 JSON，避免误报类别名。
8. 每轮实验名必须唯一，重复会明确报错；权重缺失直接停止，不让正式演示偷偷下载资源。

## 环境配置

使用独立环境，不复用二号的 `.venv_new`。本次创建的 `.venv` 仅用于轻量脚本检查，不代表安装好了 PyTorch 或 Ultralytics。

在本目录终端中执行以下准备命令。已有 `.venv` 时跳过创建；选择 Python 3.10/3.11 等与实际 PyTorch 发行版兼容的版本。

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import torch, ultralytics; print(ultralytics.__version__); print(torch.__version__); print(torch.cuda.is_available())"
```

GPU 版 PyTorch 的安装需按显卡、驱动和 [PyTorch 官方安装选择器](https://pytorch.org/get-started/locally/) 确定，不保证上面的通用安装命令自动得到所需 CUDA 版本。确认可运行后执行 `python -m pip freeze` 留存完整依赖版本。

预训练权重需从 Ultralytics 官方来源预先取得，分别放入 `weights/yolo26n.pt`、`weights/yolo11n.pt`。只加载可信权重；本次没有下载权重或执行大规模训练。

## 准备数据

本工程仅支持本地目录形式的目标检测数据集，结构如下；目录和标签没有伪造或自动补齐：

```text
dataset/
  images/train/  images/val/  images/test/
  labels/train/  labels/val/  labels/test/
```

图片与同名 TXT 标签配对，常见检测标签每行是 `class_id x_center y_center width height`，框坐标归一化。`data.yaml` 已填写本次教学类别 `unripe / turning / ripe`，正式使用前需与二号共同确认名称和编号。不要直接套用二号规则分类的六个目录，也不要假设旧截图里的 `bch.pt` 就是成熟度权重。

原数据的具体类别尚未恢复，本次类别是新拟定的教学方案，不代表旧模型的类别。`annotation_review_v01` 中已有基于现有图片制作的标注草稿，需人工复核；没有生成正式数据划分、权重或精度报告。训练/验证/测试需事先分开，同一植株连续帧避免跨集合；负样本约定也需统一。

`common.py` 只检查目录、候选图片和类别表的基本结构，**不是完整数据验收器**。损坏图片、缺标、错误框、重复样本和划分泄漏仍须二号复核并结合框架扫描日志检查。存在图片不等于标注合格。

## 运行顺序

以下命令在完成依赖、权重和真实数据配置后执行。每次更换 `--name`，示例路径不是已存在的成果。

### 1. 短程训练验证环境

```powershell
.\.venv\Scripts\python.exe train.py --epochs 1 --batch 1 --device cpu --name y26_smoke01
```

需要 GPU 时在验证 CUDA 可用后改为 `--device 0`。短训只证明流程可以运行，不保证识别效果。

### 2. 完整训练与对照

```powershell
.\.venv\Scripts\python.exe train.py --model weights/yolo26n.pt --device 0 --name y26_baseline01
.\.venv\Scripts\python.exe train.py --model weights/yolo11n.pt --device 0 --name y11_baseline01
```

两组采用同一数据划分、输入尺寸与资源条件，保存各自 `args.yaml`。不同架构可能触发不同默认优化行为，比较时必须报告实际训练配置，不能称只有模型名字发生变化的严格消融实验。

旋转与饱和度可通过 `--degrees`、`--hsv-s` 设置，先在验证集选择配置。成熟度依赖颜色，过强色彩增强可能破坏标签语义，不能默认数值越大越好。

### 3. 独立测试集评估

```powershell
.\.venv\Scripts\python.exe test.py --model runs/y26_baseline01/train/weights/best.pt --device 0 --name y26_test01
```

实际权重位置以训练终端输出为准。测试集只用于最终评估，不反复根据测试结果调参。输出 JSON 含指标原名、模型路径、配置路径、版本及框架测速信息；框架测速不等于整个业务接口的端到端延迟。

### 4. 单图展示

```powershell
.\.venv\Scripts\python.exe predict.py --model runs/y26_baseline01/train/weights/best.pt --source dataset/images/test/example.jpg --name y26_predict01
```

将 `example.jpg` 替换为真实文件。检测框上的置信度不是总体准确率。本脚本只生成本地结果，不调用业务接口，不入库，也不代表四号已接收数据。

## 现场编写范围

`train.py` 的参数解析、路径检查、输出目录和入口保护提前保留。现场编写 `LIVE DEMO START` 与 `LIVE DEMO END` 两条注释之间的 39 行代码，覆盖模型加载、训练配置、最佳权重重新加载、验证集评估、JSON 报告保存以及 Precision、Recall、mAP50、mAP50-95 输出。完整训练提前运行留档；现场可用一轮短训展示流程，不把短训成绩当作正式模型效果。正式测试集评估仍使用独立 `test.py`。

`test.py` 现场核对权重路径和 `split="test"`，运行并查看正式指标；单图画面用 `predict.py` 补充。不要为了显示框而把原来的独立测试评估删掉。

## 验证与剩余材料

代码检查与模型效果验证是两回事。本工程可先做语法、命令帮助和无需模型的测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe train.py --help
.\.venv\Scripts\python.exe test.py --help
.\.venv\Scripts\python.exe predict.py --help
```

完整训练、GPU 兼容性、独立测试指标和前后端联调仍待验证。还需确认教学类别表、复核并扩充标注数据、完成独立划分，以及准备可信权重、目标硬件信息和缺失的 Python 推理服务。

Ultralytics 采用 AGPL-3.0 / Enterprise 授权路径；课题展示、发布源代码和后续商业部署应分别核实适用义务。新模型不能替代数据合规、许可证审查或正式实测。
