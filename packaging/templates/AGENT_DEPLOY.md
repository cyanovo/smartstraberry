# 给部署 Agent 的完整任务书

交付版本：`student-2026.10.26`。先阅读本文件，再执行部署。

## 首次部署与旧版更新分流

- 新电脑空目录：使用新版完整 ZIP，按下文首次部署。
- 已使用2026-10-25包：使用配套 `student-update-2026.10.26-01.zip`，先读 UPDATE.md、update-manifest.json 和同步规范。禁止完整包覆盖原项目，禁止重新恢复业务数据库，本地代码修改须三方合并。
- 不确定版本：检查 snapshot.json、manifest.json、报告和实际哈希，不凭目录名判断，不删库重装。
- 比较完整ZIP的 Get-FileHash -Algorithm SHA256 结果与同名 .sha256 文件。包内 manifest.json 用于首次部署前逐文件校验；运行后合法重定位的入口不再等于初始哈希。
- 解压后的根目录直接包含 deploy.cmd、snapshot.json、Newsmart-Strawberry、runtimes。

## 本版功能与教学代码保护

- 病虫害记录选择器显示完整时间；问答引用识别记录、保留自定义问题、逐段输出，工具展示沿用正常问答组件。
- 物联网只显示当前账号最新建议、建议时间和“一键开始”；执行器单滑动开关，不显示继电器编号。
- 照片集支持含子目录的文件夹导入，JPEG/PNG/WebP，进度及失败详情；全部分页原图ZIP下载，同名文件加序号。单张20 MB/2400万像素，同部门相同内容拒绝重复归档。
- 溯源、经营分析页面入口已移除，旧数据库仍保留，不要自动加回菜单。
- 病害引用使用预设白粉病建议，非大模型动态诊断；真实读取记录和设备状态，选中可用知识库才检索。普通智能体聊天仍依赖worker及外部模型，两条链路分别验收，不伪造工具成功。
- 建议须确认，3分钟过期；离线不可执行，发送不等于硬件执行。滑动开关表示本页发送请求，不是设备反馈，不能为通过测试取消安全判断。
- 保护一号 `backend/package/yuxi/services/iot_service.py`、四号 `backend/package/yuxi/services/field_analysis_service.py`、二号 `strawberry_project/strawberry_classifier.py`、三号 `strawberry_vision/train.py`，不为环境问题擅自重写教学核心代码。

## 你的任务

这是草莓智慧种植教学平台的 Windows 原生交付快照，包含 Vue/Vite 前端、FastAPI 后端、独立 AI worker、传感器和设备控制、成熟度及病虫害识别、照片集、共享文件、模型管理、数据清洗和 YOLO26 训练项目。

请直接完成部署，不要只给学生一份安装建议。部署后必须测试，发现问题后定位原因、修复、重新测试，最终提供结果和可点击的本地访问地址。不要把“命令执行完了”当成“功能全部可用”。

只使用 Windows x64，不使用 Docker、WSL。原仓库旧文档提及 Docker 的内容不适用于本交付包。所有服务本机运行，每项依赖服务一个前台命令窗口，关闭对应窗口即结束该服务。没有额外守护进程监视窗口并杀进程。

## 包含与不包含

- `Newsmart-Strawberry/backend`：当前后端源代码、成熟度/病虫害权重及业务文件。
- `Newsmart-Strawberry/web`：当前 Vue 页面源码和依赖快照，保留当前界面，不要重新仿制。
- `.runtime`：PostgreSQL、Redis、Qdrant、SeaweedFS、Neo4j/JRE 的 Windows 二进制。数据库首次部署逻辑恢复，不复制老师正在运行的数据库文件。
- `strawberry_project`：二号工程师的数据清洗项目，包含图片和已有输出。
- `strawberry_vision`：三号工程师训练、验证、预测、摄像头脚本，数据集、划分清单、训练结果和模型权重。
- `backup/business.dump`：用户、部门、模型提供商、智能体配置、识别、传感器、照片集、共享文件元数据、溯源业务的 PostgreSQL 逻辑备份。
- `offline`、`runtimes`：当前安装的依赖快照和解释器，部署时重新生成虚拟环境与命令入口，不依赖老师电脑路径。
- 不包含现有知识库文档、向量、知识图谱数据、聊天历史、队列任务、Ollama 程序及模型。学生自行安装 Ollama、创建知识库；相关页面和空存储服务仍保留。
- 外部模型提供商配置按教学快照保留，可能含 API 凭据和计费配置。仅限授权班级内私下分发，不得上传公开仓库。服务端密钥和本地 MQTT 凭据重新生成。
- 真实摄像头、传感器和控制器不能随压缩包复制。照片集的设备绑定在恢复时清空，采集任务暂停。实际连接设备前必须重新配置，严禁部署测试直接执行真实设备开关。

## 环境版本

| 项目 | 解释器/运行时 | 启动入口 |
| --- | --- | --- |
| 平台后端、worker | Python 3.12.14 | backend/run_local.py，worker 加 --worker |
| MQTT broker | Python 3.12.14 | scripts/windows/mqtt_broker.py |
| YOLO 训练 | Python 3.12.14，Ultralytics 8.4.183 | strawberry_vision/train.py |
| 图片清洗 | Python 3.10.11 | strawberry_project/strawberry_classifier.py |
| 前端 | Node.js 22.19.0，随包 pnpm 11.21.0 | pnpm dev |

推荐 Windows 10/11 x64、NTFS 分区、16 GB 内存、至少 50 GB 可用空间。优先解压到 `D:\StrawberryStudent` 这类较短的英文路径。不要在压缩包里直接运行，不要放 OneDrive 同步目录。无 GPU 可先使用 CPU；不能假设学生 CUDA 驱动和老师相同。PyCharm、VS Code、Git 不在包内，可由 Agent 按学生需求从官方安装。

## 第一步：预检和部署

1. 记录操作系统、解压路径、可用空间、内存及 GPU。确认是完整解压到新的目录。
2. 在根目录运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy.ps1`，或学生双击 `deploy.cmd`。
3. 首次运行会验证 SHA256 清单、重建四个虚拟环境及前端 junction 链接、初始化空服务数据库、恢复业务、重定位数据库中的绝对路径、生成登录说明，然后启动 worker/API/前端并执行基础测试。
4. 前端入口 `start-web.cmd` 会临时将随包 Node/pnpm 放到 PATH，不修改系统环境变量。普通 VS Code 终端若需要直接 `pnpm dev`，将本包 `runtimes\node` 加到该终端 PATH，或配置 VS Code 终端环境。package.json 的 pnpm 版本声明与快照不同；启动器禁用版本自动切换，避免不必要联网下载。
5. 从 `LOGIN.txt` 获取登录 UID 和随机初始密码，不再假定 admin/123456。登录用 UID，不是昵称。仅重设新交付库的第一个有效超级管理员，不改老师库。修改密码后复测可在当前终端设置 STRAWBERRY_TEST_UID、STRAWBERRY_TEST_PASSWORD，不在报告公开密码。
6. 重新运行部署不会重复恢复有标记的数据库；若没有恢复标记但库中已有表，脚本停止，不覆盖。遇到这种情况必须先备份并判断是否部分部署，禁止直接删库“解决”。

默认端口：PostgreSQL 15432、Redis 16379、Qdrant 16333/16334、Neo4j 17687/17474、SeaweedFS S3 19000（内部 19333/19340/18888）、MQTT 11883/1883、API 5050、Vite 5179。Vite 占用自动顺延；以窗口显示的 URL 为准。其他端口冲突先查看 PID/路径归属，不得随意杀进程。更改 API 端口需要同步 run_local.py、Vite 代理和测试地址，不能只改一个位置。

## 第二步：自动检查和修复闭环

运行 `verify.cmd`，读取 `DEPLOY_TEST_REPORT.json`。自动检查监听、健康、真实登录、全部可访问非空照片集ZIP的原图数量与SHA256、病害建议读取、清洗环境、YOLO26权重及566张数据集哈希。它只是基础冒烟，不是完整验收。检查时不要同时上传或删除图片，大照片集需额外内存与时间。

每个故障遵循：复现并保存完整报错 → 检查进程/端口/配置/日志 → 确认根因 → 最小修改 → 重启受影响服务 → 重跑该项与关联测试 → 写入最终报告。对同一问题最多尝试三轮不同的、有证据的修复；仍失败则明确阻塞原因和需要用户提供的条件，不循环重装。

可自动处理：缺失的本包环境或入口运行 `deploy.py prepare` 重建；错误解释器改为对应 `.venv\Scripts\python.exe`；旧目录路径按 snapshot.json 检查重定位；服务未启动打开对应服务窗口；API 修改后显式重启。禁止通过随机置信度、假接口成功、关闭鉴权、跳过失败测试、删除数据掩盖问题。

常见失败：
- Python DLL/VC runtime 缺失：确认 x64，从微软官方安装 Visual C++ 2015–2022 x64 运行库，记录安装与重测结果。
- 端口占用：查询归属；只停止已确认属于本次交付的服务，或协调调整端口。
- 数据库 timeout：检查 PostgreSQL 窗口、15432 和 local.env，不是 Python 版本问题。
- pnpm dev 报错或白屏：核对 Node 版本、junction 新路径、浏览器控制台及 API 代理；不要重新生成 UI。
- 网络/云 API 失败：区分网络、额度、API key、模型名称；不能凭空生成有效密钥。记录为外部依赖阻塞。
- 摄像头不可用：检查 Windows 摄像头隐私权限、浏览器 localhost 权限、被其他程序占用及设备编号；无设备标记未测。
- 杀毒软件阻止服务：核对发布者与本包哈希，向学生说明拦截内容，不关闭全局安全防护。

## 第三步：必须完成的功能验收

Agent 有浏览器工具时直接操作并保存截图；无浏览器工具则安装可用的测试工具，或明确标记未执行，不伪造截图。将截图放 `acceptance/screenshots`。

1. 打开欢迎页、登录页，真实登录；依次访问首页、照片集、成熟度识别、病虫害识别、共享空间、设备页、AI 问答、知识库/图谱页；检查控制台与网络错误。知识库应为空，不要求已有图谱。
2. 用包内真实图片运行成熟度、病虫害检测，检查框、类别、原始置信度、模型版本、识别记录持久化。若页面有演示置信度开关，验收必须关闭，不能把随机展示数当真实性能。
3. 新建测试照片集、上传照片、关联识别，重启 API 后检查记录和图片仍可读。测试对象使用 DEPLOY_TEST 前缀，不删除老师原始业务。
4. 共享空间上传小文件、另一个有权限账号下载并比较 SHA256，验证跨账号共享、权限边界。文件交换只用共享空间，不使用 FTP。
5. 传感器历史查询/导出 CSV；离线硬件要明确显示离线。设备建议与人工确认链路用模拟/断开设备测试，禁止直接对真实执行器发送控制请求。
6. AI 初始化、选择照片集和病虫害记录、发起问题，确认 worker 实际消费请求。外部大模型需联网且有有效凭据；知识库缺失是设计范围，不应伪造检索内容。
7. 模型上传/校验/启用/回退应使用测试版本，回退到原启用版本。对不可信 .pt 不直接反序列化；先确认来源。
8. 清洗项目运行前备份已有 output，使用测试输入，检查损坏图片处理、分类输出。现有逻辑属于读取校验及颜色/形状启发式，不宣称具备完整去重和自动正确标注能力。
9. YOLO 执行下面的短训练与验证，检查真实曲线/指标文件，再做单图预测。摄像头有设备时测试，没设备标记未测。
10. 关闭并重新启动项目，检查业务数据、共享文件和模型配置持久化。记录实际前端端口。

11. 文件夹专项：DEPLOY_TEST照片集导入含子目录32张不同内容图片、一个文本文件和一个损坏PNG。验证成功数、跳过与失败详情，翻页后下载全部图片，解压逐张比对SHA256。不能用32份相同内容测试成功数，系统会拒绝重复。子目录不保留，ZIP用编号前缀避免重名覆盖。
12. 病害专项：引用真实病害识别记录输入自定义问题，检查原文、可展开工具结果、逐段正文。无库不伪造检索；物联网只显示最新一条和时间，离线按钮禁用。禁止自动点击真实控制。通用AI另测worker，不能用预设病害正文冒充云模型通过。

SQL与文件不是跨介质原子快照；发现缺图/模型应记录ID、文件并恢复对应资源或报告阻塞，禁止删记录隐藏问题。

## YOLO 逐行命令

在解压目录下的 `strawberry_vision` 打开 PowerShell，每次复制执行一行。不要把所有命令粘成一行。

```powershell
.\.venv\Scripts\python.exe -c "import ultralytics; print(ultralytics.__version__)"
```

```powershell
.\.venv\Scripts\python.exe tests/verify_maturity_split.py
```

```powershell
.\.venv\Scripts\python.exe train.py --help
```

```powershell
.\.venv\Scripts\python.exe train.py --model weights/yolo26n.pt --data data_maturity_platform.yaml --epochs 1 --batch 2 --imgsz 320 --device cpu --name deployment_smoke
```

训练目录如已存在，换一个唯一 name，不覆盖之前结果。请根据程序输出定位 `best.pt`、results.csv、results.png、混淆矩阵及验证曲线；某些指标受数据量和模型结果影响，不保证每个版本产生相同文件名。使用 `test.py --help`、`predict.py --help`、`camera_predict.py --help` 核对参数后运行，不凭空猜参数。

`weights/yolo26n.pt` 是官方通用 80 类预训练权重，不是已经训练好的草莓模型。566 张成熟度图片已按 396/113/57 划分，1734 个框；现有类别映射仍需人工语义抽检。一次 epoch 仅验证训练链路，不能宣称达到成熟度识别精度。病虫害训练须核对独立数据集与类别，不用成熟度标签替代。

## IDE 配置

PyCharm 打开对应项目，Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Existing，分别选该项目 `.venv\Scripts\python.exe`。平台和训练为 3.12.14，清洗为 3.10.11。平台运行 `backend/run_local.py`，Working directory 为 backend。VS Code 打开 web，使用随包 Node/pnpm 启动。无需为识别成“FastAPI 项目”额外更换工程类型。

## 数据保护和交付报告

不删库、不覆盖用户数据、不修改不相关项目、不上传密钥。备份业务数据后才做数据库迁移。端口开放到局域网、防火墙规则、接入实际 MQTT 设备需要说明范围并得到用户确认；默认 API 和 Web 只监听 loopback。

最终写 `DEPLOY_RESULT.md`，内容包括：机器与安装目录、版本、实际 URL、登录凭据文件位置、每项 PASS/FAIL/BLOCKED/NOT_TESTED、命令和报告路径、截图、修复前后差异、数据保留情况、外部依赖、后续启动/关闭方法。只有所有必测项目真正通过才能写“完整验收通过”；不能把知识库/Ollama 排除项算成失败，也不能把未测的 AI/硬件写通过。

本包不承诺任意 Windows 电脑零适配完全相同。CPU/GPU、驱动、摄像头、云服务额度、网络、端口和安全软件存在差异；你的职责就是检测这些差异并完成可验证的适配。

## 结果与后续同步

按 DEPLOY_RESULT_TEMPLATE.md 输出 DEPLOY_RESULT.md，区分基础通过、完整验收、外部依赖阻塞。验收后写 student-version.json，包含 release、archive_sha256、installed_at、last_accepted_release、report、local_patches；有阻塞不能冒填完整通过。

后续遵守 `学生版本同步/AI代码同步规范.md`，不覆盖 .runtime/data、backend/saves、数据集/runs/weights、.venv、local.env、LOGIN.txt 和学生自建知识库。保存本地修复，增量包base文件用于三方合并。
