# 版本变更记录

本页用于记录各版本发布说明（新增、修复与破坏性变更）。

同一版本的多次功能更新时，应以功能为单位进行更新，比如之前添加了 A 功能的更新，在后续的更新中修复了因 A 功能引入的 bug，那么这个修复说明应该和 A 功能描述放在一起，而不是新增一条修复记录，功能更新同理。

## v0.7.0 (开发中)

- 修复照片集分析服务被编辑损坏的括号、函数名与缩进，恢复分析主体在病害选择循环外执行、知识库读取不依赖设备绑定；新增四组编排回归测试。
- 恢复 IoT 服务中误删的停止灌溉和通用执行器控制方法，沿用已交付的五路草莓继电器映射和旧协议行为；未改动学生其他教学代码，也未发送真实设备指令。
- AI病害问答与决策建议的控制发送结果统一显示“已发送”，移除“执行未确认”尾句；底层状态、防重复执行及失败提示不变。
- 设备控制区新增一键关闭全部五路设备，复用既有控制接口逐路发送停止指令并分别显示失败；MQTT连接时允许在缺少近期上报的情况下尝试关闭，发送期间防重复和开关并发，不宣称实际设备停机确认。
- AI决策建议移到传感器历史日志上方；历史不可用建议标记为“暂不可执行”，设备恢复在线时提示重新分析，避免将旧建议状态误读为当前连接状态，不自动恢复过期控制操作。
- 物联网页面改为明确的设备在线/离线提示，展示空气、土壤、执行器通信健康状态；五路滑动开关增加开/关文字，发送成功提示简化为指令已发送。确认开启时重新检查连接状态，不将通信正常或发送成功伪装成设备运行反馈。未修改学生控制核心方法。
- Windows MQTT 取消本机及物理网卡当前 IPv4 子网的账号密码校验，设备任意填写或留空均可连接；其他来源拒绝。启动时自动识别网段，换 Wi-Fi 后需重启 MQTT。旧凭据文件保留但不再读取，禁止映射公网，仅用于可信局域网；重启命令增加监听就绪等待。
- 前端Vite开发服务允许局域网访问，默认端口仍为5179且占用时递增；API继续通过Vite代理访问本机5050，不对外开放后端监听。仅在可信局域网使用开发服务。
- 删除照片集原图时，在同一事务中删除该部门、该图片关联的全部病虫害识别记录；保留成熟度及其他识别记录的原图保护，更新删除确认说明。权限和原图/缩略图清理沿用现有流程，无数据库迁移。

- 2026-10-26 学生Windows交付刷新：累计功能源码、离线环境、570张照片业务快照；增强Agent部署/测试/修复说明、随机初始密码与恢复时控制状态隔离，提供保护学生数据的累计增量更新。隔离库/API与原图ZIP校验通过，完整目标电脑验收仍由学生端执行。

- 草莓照片集支持文件夹批量导入（含子目录 JPEG/PNG/WebP），取消单批30张限制，显示进度、成功/失败/跳过计数和失败详情；支持按当前照片集下载全部分页原图 ZIP，保留部门权限、原始字节、重名文件，临时压缩包响应后清理。无数据库迁移。

- 物联网设备控制移除设备名称下方的继电器编号说明，仅简化展示，不改变控制映射。
- 物联网执行器和灯光控制改为单滑动开关，移除“实际开关状态未知”标签和开启/停止双按钮；成功发送后更新本页请求状态，取消或失败不改变开关，保留开启确认和真实发送结果。

- 物联网 AI 决策建议仅显示最新一条，按钮统一为“一键开始”；执行后、过期或设备不可用时按钮保留但禁用，历史数据不删除。

- 智能温室物联网底部新增 AI 决策建议，展示当前账号最近20条病害分析的建议时间、设备动作与执行结果，每5秒刷新；一键执行复用问答页确认接口与同一记录，保留3分钟有效期、在线检查及原子防重，不重复发送或伪报设备已执行。

- 病害分析保留用户实际输入，随请求传入并保存到历史记录，不再显示固定长问题；旧记录未保存原文时不虚构问题。病害知识库工具不可用时标题改为“暂未获取知识库资料”，保留真实错误状态与工具详情，不影响普通聊天或控制确认。

- 病害分析新增 SSE 流式接口，实时报告读取、检索、整理阶段与工具返回，固定防治正文分段输出；切换对话中止连接，输出完成后才显示确认。顶部增加参考知识库选择，默认优先可访问的草莓知识库；实际检索保留权限校验与失败状态，不生成虚构推理。

- 病害分析整段对话复用 AgentMessageComponent 与 ToolCallsGroupComponent，与正常聊天使用相同用户气泡、工具组和 Markdown 正文；移除独立灰色问题条和整行记录 ID，记录参数仍可在工具详情查看，控制确认流程保持不变。

- 移除产品溯源、经营分析导航及对应页面路由（含公开溯源查询）；保留驾驶舱、后端接口及历史数据，旧页面地址进入未找到页面。

- 病虫害记录选择器统一为分行列表：完整显示识别日期时间、病害数量、照片集及记录短编号；选中项不再折叠省略时间，支持多选、搜索、移除、加载和空状态，顶部与侧栏共用，适配窄屏。

- 病虫害记录选择与普通聊天发送联动：选择记录后发送消息直接进入固定白粉病分析及确认流程，清空选择恢复通用智能体；避免智能体误把数据库记录当作上传文件查找。分析期间禁用重复发送，设备指令仍须按钮确认。

- 新增病虫害记录引用到 AI 问答的白粉病防治流程：真实读取识别记录、实时传感器及可选知识库，展示固定防治内容；四项设备操作合并确认、三分钟有效、防重复发送并保存逐项结果。工具展示复用问答原有折叠汇总组件，显示实际调用数量、名称、失败数及可展开结果，知识库检索状态单独呈现。保持学生控制、估产、清洗、训练核心代码不变。

- 修复照片集分析工具的内部 ToolRuntime 参数参与 JSON Schema 生成，导致智能体初始化失败；工具元数据完整加载后才写入缓存。初始化失败只提示一次，服务器错误提示改为本地后端窗口和日志路径。

- 识别证据标框增加默认开启的演示置信度开关：随机显示 95%～98% 并标注“演示值”，关闭恢复模型真实值。仅影响标框显示，不修改阈值筛选、识别记录和结果表。

- 新增病虫害识别页面及导航入口，沿用成熟度识别布局；支持照片集原图、图片上传、浏览器拍照、检测框及置信度展示、历史追溯，以及管理员模型导入校验和启用。复用现有 disease 服务，不替换成熟度模型。修复摄像头开启后拍照与识别不可用：等待画面就绪，直接识别时先归档当前帧，无照片集时提供就地创建入口，关闭或离开页面释放摄像头；补充模拟视频流回归。

### 破坏性变更

- Provider 与模型配置收敛：移除旧版 v1 模型配置与 Ollama 支持，运行时模型统一使用 `provider_id:model_id` 与独立 provider 模块；自定义 provider 实现逻辑从文件移动到数据库，并从 config 文件迁移到 provider 模块。
- 智能体运行时语义收敛：用户可见的 `AgentConfig` 收敛为数据库持久化的一级 `Agent`，内置 Python Agent 改为智能体后端；聊天、运行任务、恢复审批和文件预览均从线程绑定的 Agent 解析运行时上下文，前端只提交 `agent_id`。
- 知识库能力边界收敛：移除 Upload 与 LightRAG 知识库/图谱能力，知识库类型收敛为 Milvus 与只读连接器；知识库 API 统一使用 `/databases/{kb_id}/xxx` 形式，并整合 mindmap / eval 等子接口。
- Agent 资源默认选择与权限过滤：未显式配置工具、知识库、MCP、Skills、子智能体时默认启用当前用户可访问/可用的全部资源，显式选择后按允许列表过滤；Agent 创建前统一完成最终资源权限过滤、知识库 `kb_id` 可见范围派生和 Skill prompt/readable 依赖闭包派生。
- Skill 安装与权限模型收敛：Skill 元数据使用 `source_type/share_config/enabled` 表达来源、生效范围与启用状态；内置 Skill 启动或同步时自动写入数据库并默认全局启用，上传和远程添加统一改为解析草稿后确认安装，不保留旧直接安装兼容路径。
- 历史兼容层精简：移除 sandbox provisioner `local` 后端别名、ask_user_question 单问题旧协议、JWT 历史默认密钥特殊判断、内置 Skill `SKILLS.md` 文件名回退、运行事件数字 seq 兼容和前端旧字段回退。
- 用户身份命名收敛：原业务登录标识统一改为 `uid`，Agent/LangGraph runtime、conversation、agent_run、sandbox 路径和前端用户态均使用字符串 `uid`；`user_id` 仅保留给外部响应中的数值 `users.id` 或真实外键场景。

### 开发记录

- 资料中心启用“共享空间 → 团队工作区”，复用部门共享存储，与采集工作台文件互通。支持分层目录、目录搜索、多文件上传、版本说明、版本校验详情、下载及上传者/管理员删除；同名文件保留独立版本，未新增公开文件访问权限。

- AI 照片集分析增加病虫害识别记录多选（最多 20 条）：按来源照片集、时间和识别结果搜索；分析接口和智能体工具接收记录 ID，后端验证部门权限及成功病虫害任务类型，保存所选证据与跨照片集来源限制。

- 修复 Windows 开发前端菜单无法跳转：显式扫描所有 Vue 页面依赖，重建未完成的 Vite 预构建缓存，解决懒加载页面依赖返回 504。补充真实临时账号浏览器回归，逐一点击 13 个主菜单并检查路由、页面内容、HTTP 错误及未捕获异常；不调用拍照或设备控制。

- Windows 启动器简化：`start-services.cmd` 为每个依赖打开独立可见窗口，PostgreSQL 直接运行 `postgres.exe`，其他服务同样前台运行；删除 `service_window.py` 及其监控退出清理链路。启动器结束不停止服务，关闭单个服务窗口停止该服务，日志直接在各自窗口查看。重复启动复用已有窗口，FastAPI/Vite 仍由 IDE 管理。

- 草莓技能展示业务链路（2026-10-22）：增加自动采集、时间范围 ZIP 备份及 SHA-256 清单、部门团队共享目录和版本说明、管理员可信 PT/ONNX 模型验证/启用/回退、照片集识别和失败追溯。新增“采集与模型”工作台，AI 问答增加照片集证据分析、实测单果重计算和人工确认设备建议；草莓助手不直接执行控制，重复确认只发布一次，无回执显示已发送未确认。成熟度页面接入版本化模型，移除固定单果重及失败后自动用大模型替换结果的行为。硬件、真实自训模型准确率和完整大模型对话仍需现场验收。

- 草莓照片集归档：部门内唯一草莓簇、分页列表、权限原图、SHA-256、静态图片校验及缩略图；重复原图冲突提示，数据库写入失败清理文件。上传者/管理员可删除无识别关联原图，已有证据拒绝删除。显式使用 JPEG/PNG/WebP 解码器，避免 Ultralytics 图片补丁对损坏上传触发自动安装插件。

- 草莓传感器历史日志首版：MQTT 空气/土壤读数写入 PostgreSQL，保留实际字段和时区信息；新增登录保护的设备、时间、类型筛选及 CSV 导出，设备页增加历史表格和分页。通过单元测试、真实数据库存取、前端构建及桌面/手机浅暗色模拟浏览器回归；真实 MQTT 与重启持久性仍待现场验收。完整任务进度见 `docs/vibe/草莓平台-功能开发验收清单.md`。

- 智能问答增加常驻知识库检索状态、知识库名称、真实来源文件名与片段数量，工具详情折叠后仍可见；区分检索中、完成、无结果与失败。保留纯文本检索结果，未提供文件名时不伪造来源。补充检索工具单元测试和桌面/手机组件消息顺序验证。

- 设备控制页恢复引用原有 LESS 与概览、环境监测、执行器、灯光分区结构；保留五路协议及未知实际状态/发送结果展示，补充桌面和手机浅暗色模拟浏览器回归检查，不修改公共样式。

- Windows 草莓知识库：新增 Qdrant 存储适配和原生 Neo4j 服务，使用本机 Ollama `nomic-embed-text:latest` 导入 12 份全流程中文种植资料；支持向量、中文稀疏及混合检索，保留来源与适用限制。修复管理器未加载已有知识库元数据的问题，增加 Nomic 检索前缀及真实语料检索测试。思维导图默认使用知识库模型并读取已索引正文，本地 Ollama 使用 JSON 输出和扩展上下文，校验异常节点、重复分支与输出截断；修复模型重试日志掩盖原始错误。已通过本地模型生成并保存草莓导图，浏览器展示、知识图谱抽取和网页 AI 回答仍需单独验收。

- 草莓设备控制：按五路 RS485 继电器固件对齐 MQTT 主题；移除不支持的调光、模式和自动 AI 执行入口，区分连接、上报新鲜度和未知执行状态，发布失败不再报成功。原番茄协议需显式设置 `MQTT_PROTOCOL=tomato_v11`，草莓页面只启用草莓协议。本地 MQTT 纳入一键服务窗口：后台使用回环 11883，硬件使用认证 1883；自动生成持久账号，提供仅限本地子网的管理员防火墙脚本及独立 MQTT 重启入口。

- 修复 PostgreSQL 重启后 AI worker 复用失效 checkpoint 连接：连接池取用前检查连接有效性；增加仅终止测试自身连接的恢复集成测试。

- Windows 功能适配：依赖窗口自动启动 AI worker，修复 worker 的 Windows 事件循环；智能体文件工具改用目录受限的本地后端并保持上传原件只读，不开放宿主机 shell；开放知识库/图谱管理路由，缺少云模型密钥时前置报错。资料中心上传下载和列表接口已集成验证，实际模型回答及向量库/图谱生成仍待配置与部署。

- 按用户要求撤销 Windows 首版的导航隐藏、强制页面跳转和统一接口拦截，恢复原有 AI、资料中心、知识库及悬浮按钮；保留原权限控制和 LITE 启动配置，未部署依赖的能力仍待适配。

- 本地依赖改为窗口托管：`start-services.cmd` 持续显示状态，关闭窗口后由独立监控进程停止本项目依赖，并用文件锁阻止多个托管窗口同时运行。

- Windows 开发便利性：前端 `pnpm dev` 默认使用本机 5179 端口；后端提供 PyCharm `FastAPI Local` 运行配置，沿用现有 Python 3.12 环境和 Windows 启动入口。

- 新增纯 Windows 本地部署入口：Python 3.12 独立虚拟环境、隔离端口与数据目录、依赖下载及启停脚本，绕过课堂远程配置；保留公司 UI，首版关闭尚未部署的知识库与沙盒相关入口。验收进度见 `docs/vibe/2026-10-22-native-windows.md`。

- 前后端方案切换：恢复公司原有 Vue 入口、登录、侧栏、路由与应用初始化，使用配套 FastAPI `/api` 接口；移除旧 Java 代理，旧草莓适配代码留存但不再挂载。保留既有检测、溯源及后端修改；新后端运行与真实登录待 Docker 环境启动后验收。

- 草莓前端适配：入口、登录、侧栏直接复用现有 Vue 模板与样式，驾驶舱复用原布局；仅连接旧 Java 后端，支持数学验证码登录及业务分页列表，隐藏无旧接口支撑的入口。设备模块补齐详情、增改删查、导出与权限控制；硬件页复用原 IndustrialIot 布局和 LESS，接入环境指标及风扇、滴灌参数控制，明确指令发送与执行状态的区别。已通过真实管理员登录/查询验证及隔离数据的前端流程回归，不改旧后端账户配置，未操作现场硬件。

- 新增纯学生端的 PyCharm + VS Code 部署方案：Docker 节点无需执行脚本或修改 Compose，普通学生只需在 `backend/classroom.env` 填写一次节点 IP，后端会自动连接共享 PostgreSQL、Redis、MinIO、Milvus、Neo4j、OCR 和沙盒，并按学生电脑隔离后台任务与 Agent run 队列；前端默认连接本机 FastAPI，摄像头与成熟度检测统一由学生本机后端提供。
- 更新番茄种植架 MQTT 通信协议至 v1.1：后端订阅 `tomato_hnsw0001/result/state/telemetry/availability`，控制指令统一发布到 `tomato_hnsw0001/set` 并使用 `cmd` 编号；补齐红/蓝光亮度、总灯开关、补光模式、水泵间隔/时长、休息时间和手动/AI 模式命令，前端 IoT 页面、智能体工具、README 与 ESP32 示例脚本同步切换到新版 telemetry/state 字段。
- 优化学生首次部署体验：README 改为快速部署优先结构，补充中国大陆镜像源说明；初始化脚本补充 Mosquitto 预拉取，后端与沙盒镜像构建阶段保留国内 Python 包源，减少大陆网络下首次构建卡顿。
- 调整课堂私有仓库部署流程：仓库内置课堂 `.env`，初始化脚本自动生成本机 JWT 与实例 ID，并预下载公开依赖镜像，学生仅需构建项目自身镜像。
- 新增 Windows 初始化批处理入口：`scripts/init.bat` 使用临时 `ExecutionPolicy Bypass` 调用 PowerShell 初始化脚本，避免学生电脑因脚本执行策略无法运行初始化命令。
- 增强镜像预拉取脚本：区分已在国内 registry 的镜像与 Docker Hub/GHCR/Quay 镜像，优先使用 DaoCloud 国内镜像前缀，失败时自动回退原始镜像地址，避免单个加速源异常导致初始化中断。
- 将 Compose 与 Dockerfile 默认镜像切换为国内镜像地址：公开运行依赖和构建基础镜像默认使用 DaoCloud 前缀，项目自建镜像设置 `pull_policy: build`，避免学生直接 `docker compose up` 时访问 Docker Hub。
- 替换默认登录页背景：将旧草莓背景替换为番茄温室图片，并同步默认站点配置。
- 新增消费者溯源查询页：在溯源管理页添加"消费者查询页"按钮，打开独立公开路由 `/trace-query`（无需登录），消费者可输入溯源码查询完整溯源报告，支持摄像头扫码识别包装上的二维码；页面自适应 PC 和移动端。
- 调整智能体上下文摘要触发阈值默认值：`summary_threshold` 从 100K 提升至 800K，以适配大上下文窗口模型（如 Gemini 2.5 Pro 1M）；管理员可通过 UI 智能体配置页按代理覆盖。
- 新增番茄领域前端改造第一阶段：补充番茄沉浸式图片资产，新增”番茄驾驶舱””生长档案””成熟度管理中心”和”AI 日志”页面，将侧边栏入口调整为番茄业务导航，并把登录后默认入口切换到番茄驾驶舱；”智能工业物联网”升级为”智能温室物联网”路由命名。成熟度管理中心支持展示循迹小车扫描记录、成熟度状态、采摘建议，并在成熟度超过 80% 时展示可执行采摘小车入口。
- 发布版本号更新至 `0.7.0.beta2`，同步 package、Docker 镜像标签与快速开始分支引用。
- 新增内置「深度研究」多智能体：编排器 Agent（`deep-research`，ChatbotAgent 后端）负责澄清、拆解、并行调度子智能体与综合成稿，配套两个子智能体 `research-explorer`（围绕单个子问题多轮检索网页/知识库并返回带引用发现）和 `fact-verifier`（对抗式核验关键论断、标注冲突与置信度）；完整研究方法论沉淀为新增内置 Skill `deep-research`（依赖 `tavily_search`），编排器运行时读取并据此调度。三者随 `lifespan` 启动通过 `AgentRepository.ensure_deep_research_agents` 幂等落库（已存在不覆盖管理员修改）。
- 新增内置 `general-purpose` 通用任务子智能体：使用 `SubAgentBackend` 与空运行配置，作为 `task` 工具的通用委派目标，由启动初始化自动写入数据库。
- 收敛 MCP 创建与编辑入口：前端移除整段配置文本入口和模式切换器，仅保留表单字段提交；后端 MCP 创建/更新请求拒绝额外配置字段，避免绕过表单约束。
- 调整内置 MCP 默认项：移除 `sequentialthinking` 的系统内置同步，启动同步时清理历史系统内置记录，保留用户手动创建的同名 MCP。
- 图片生成能力迁移为 Skill：Qwen-Image 从内置 Python 生成工具迁移到内置 Skill `image-gen`，模型调用与图片下载在 Agent 沙盒中完成，生成结果保存到 outputs 并通过 `present_artifacts` 展示，为多图片生成模型接入复用同一产物展示链路。
- 降低知识库路由与工具模块复杂度：示例问题生成迁移到知识库 utils，文件上传统一 100 MB 限制，URL 预处理入库路径与旧 `content_type=url` 行为收敛，并修复 uid、导出 MIME 与异常透传等路由问题。
- 重构智能体配置语义：用户可见的 `AgentConfig` 收敛为数据库持久化的一级 `Agent`，内置 Python Agent 改为智能体后端；新增 `/api/agent` 管理与运行接口，聊天、运行任务、恢复审批和文件预览均从线程绑定的 Agent 解析运行时上下文，前端只提交 `agent_id`，并在模型配置页新增“智能体”管理页签。
- 删除 Upload 与 LightRAG 图谱/知识库能力：知识库类型收敛为 Milvus 与 Dify，只保留 Milvus 知识库内图谱构建/展示/检索，移除独立 `/graph` 页面和默认上传图谱工具。
- 收敛只读知识源连接器：新增 `ReadOnlyConnectors` 基类，Dify 改为声明自身创建参数与校验规则，新增 Notion Data Source 只读知识库并支持 Search/Find/Open；知识库类型接口返回创建参数 schema，前端新建表单按类型动态渲染非 Milvus 配置并统一保存到 `additional_params`。
- 新增知识库 Chunk 持久化：Milvus 知识库索引/更新流程会将 chunks 双写到 PostgreSQL `knowledge_chunks` 表与 Milvus，文件内容查看优先查询 PostgreSQL，并为位置信息、图谱实体关联、标签和抽取结果预留结构化字段。
- 完善 Milvus 知识库图谱构建：修复 Chunk 图谱写入返回值、Neo4j 同步写入阻塞事件循环、重复构建任务竞态、图谱查询提前终止、Neo4j 连接复用、LLM 抽取超时重试和前端错误详情展示等问题；图谱构建会将 entity/triple 本体与 chunk 引用写入 PostgreSQL，并为唯一 entity/triple 建立 Milvus 语义索引，单文件删除时同步清理图谱引用和孤儿向量。
- 优化图谱抽取器配置：未配置时在图谱中心展示配置入口，抽取方案收敛为 LLM，前端仅保留“更多拓展中”占位；LLM 抽取器使用固定 Prompt + 自定义 Schema，并支持模型参数与并发队列数；已配置后允许修改参数并提示重置重抽风险。修复上传并入库新文件时旧内存 metadata 覆盖数据库图谱配置的问题。
- 新增 Milvus 图谱检索链路：Query 可召回图谱实体和三元组，结合 Chunk 命中实体构造 seed entity，读取 Neo4j 2-hop 子图后用 igraph 执行 PPR，最终以 Chunk 为产物并通过 RRF 与原 Chunk 召回融合；检索配置改为 dataclass 元数据生成，支持 `depend_on` 控制重排序和图检索参数展示。
- 收紧用户管理部门隔离：普通管理员创建用户时固定归属本部门，用户列表、访问选项、详情、更新和删除接口均限制在本部门范围内。
- 调整 Agent 资源默认选择与运行时上下文：未显式配置工具、知识库、MCP、Skills、子智能体时默认启用当前用户可访问/可用的全部资源，显式选择后按允许列表过滤；Agent 创建前统一完成最终资源权限过滤、知识库 `kb_id` 可见范围派生和 Skill prompt/readable 依赖闭包派生，聊天运行时与文件系统预览复用同一结果。
- 重构 Skills 权限与安装流程：Skill 增加 `source_type/share_config/enabled`，内置 Skill 作为启动同步入库的全局资源，不再保留前端安装/更新状态，支持启停但不允许删除；上传和远程添加统一为解析草稿后确认生效范围，安装 slug 优先读取 `SKILL.md` 的 `slug` 字段并保留 `name` 展示名，压缩包名称不参与 slug 校验；管理端支持编辑生效范围与启停；Agent 运行时按当前用户可访问 Skills 派生 prompt/readable 依赖闭包并限制挂载/激活，Skills prompt 改为模型请求级注入以避免污染 runtime context；主智能体恢复 `install_skill` 工具，允许当前用户安装私有 Skill 并激活当前会话，子智能体配置和运行态均禁用该工具。
- 精简历史兼容层：移除 sandbox provisioner `local` 后端别名、ask_user_question 单问题旧协议、JWT 历史默认密钥特殊判断、内置 Skill `SKILLS.md` 文件名回退、运行事件数字 seq 兼容和前端若干旧字段回退。
- 重构知识库共享权限：`share_config` 改为全局共享、部门共享、指定人可访问三档，部门共享必须包含当前用户部门，指定人可访问必须包含当前用户，并补充权限过滤测试。
- 移除知识库沙盒文件系统映射：不再通过 `/home/gem/kbs` 暴露知识库文件树，Agent 继续使用 `query_kb` 与 `open_kb_document` 访问知识库内容。
- 规范 Agent 知识库 Search/Find/Open 工具协议：`resource_id` 统一表示知识库 `kb_id`，Search 返回结构化 `resource_id/file_id/chunk` 结果，新增 `find_kb_document` 在已知文件内做关键词或正则定位，Open 默认窗口扩大到 1800 行。
- 收敛知识库分块配置：分块预设仅表达策略选择，通用分块参数统一通过 `chunk_parser_config` 传递；移除 `chunk_size`、`chunk_overlap`、`qa_separator` 等旧 root 字段兼容。
- 收敛知识库文件解析参数：文件级 `processing_params` 统一保存 `ocr_engine` 与 `ocr_engine_config`，解析阶段直接使用该结构并保留分块参数快照。
- 修复知识库文件大小显示为 0 的问题：文件上传时 `file_sizes` 参数未正确传播或历史数据缺失导致 DB 中 `file_size` 为 `None`；新增 `MinIOClient.stat_file/astat_file` 获取文件大小方法，`add_file_record` 在 `size` 缺失时从 MinIO 回补，`_load_metadata` 加载元数据后自动为缺少 `size` 的文件从 MinIO 补全并持久化。
- 优化评估基准自动生成：生成任务支持配置队列并发数，默认 10，范围 1-20。
- 重梳理知识库评估存储：评估数据集、题目、评估运行和逐题结果统一入库，JSONL 仅作为导入/导出格式；后端和前端 API 统一使用 dataset/run 语义；评估运行支持用户命名，历史记录按名称展示，综合评分只聚合检索指标。
- 扩展知识库上传来源：添加“从工作区上传”模式，后端将当前用户工作区文件预处理上传到 MinIO，前端沿用现有 `addDocuments` 入库链路提交 MinIO URL、内容哈希和文件大小。
- 重构知识库详情页布局：`DatabaseInfo` 改为顶部详情 header + 左侧功能 tab 侧边栏 + 右侧内容区，Milvus 默认进入文件管理，并将检索测试、知识图谱、知识导图、检索配置、RAG 评估和评估基准统一纳入侧边栏导航；只读连接器保留检索测试与检索配置。
- 整合知识导图接口：移除独立 mindmap router 与前端 API 模块，思维导图生成、查询和文件列表接口统一收敛到知识库 API 下。
- 收敛独立模型配置模块运行时：运行时 chat / embedding / rerank 均统一从 provider 模块与模型缓存读取 `provider_id:model_id`；旧版静态模型配置、v1 slash spec、旧模型列表接口和 Ollama 适配已移除；内置 provider 模板补充 XiaomiMiMo、XiaomiMiMo Token Plan CN 与 Kimi Code（`kimi-for-coding`）。
- 调整智能体配置归属与字段权限：`AgentConfig` 从部门共享改为按 `uid` 隔离，所有登录用户可管理自己的配置；`BaseContext` 支持字段级 `auth` 元数据，后端按用户角色过滤可见与可保存的配置项。
- 新增用户级沙盒环境变量：增加 `agent_envs` 表与 `/api/user/agent-env` 接口，设置面板支持当前用户维护 Agent 沙盒环境变量；创建新沙盒时与全局 `sandbox.env` 合并注入，用户变量优先。
- 收敛用户身份命名：原业务登录标识统一改为 `uid`，Agent/LangGraph runtime、conversation、agent_run、sandbox 路径和前端用户态均使用字符串 `uid`；`user_id` 仅保留给外部响应中的数值 `users.id` 或真实外键场景。
- 工作区知识库分类显示：知识库侧边栏按创建者分组为“我的知识库”和“共享知识库”，自己创建的知识库显示在“我的知识库”下，非自己创建的显示在“共享知识库”下；`knowledge_bases` 表新增 `created_by` 字段记录创建者 uid。
- 工作区文件上传支持多选：`/workspace/upload` 与 Viewer 工作区上传统一使用 `files` 多文件字段，一次最多上传 50 个文件，批量上传失败时清理本次已写入文件。
- 聊天附件新增 MinIO tmp 临时上传、可选 PDF/图片解析、确认后加入线程附件的流程；前端改为弹窗内上传、解析与确认。
- 优化智能体对话页细节：状态面板隐藏空 section，待办名称限制为 20 个中文汉字以内，模型选择器展示供应商名称，并收紧附件状态标签与文件编辑浮动操作样式。
- 标准化 Agent run/SSE 执行链路：run 创建时持久化输入消息并提交后入队，worker 统一写入 Redis Stream envelope，SSE 输出 `event/data/id`、心跳注释、`Last-Event-ID` 回放和终止 `end` 事件；前端强制使用 run API 并支持 ask_user_question 中断后以 resume run 恢复；事件 envelope 构造收敛到统一 helper，前端优先使用 envelope 一级 `thread_id` 路由。
- Agent run SSE 新增 `verbose=false` 精简模式：默认仍返回完整事件载荷；精简模式仅在 SSE 输出前重建最小 payload，跳过 `metadata` 和空 `yuxi.agent_state`，将同一 data 内的 `request_id` 外提为单个字段，移除 chunk 中重复的 `meta`、`metadata`、`thread_id`、`response`、空 `namespace` 和图片 base64 等调试字段，保留消息增量、工具调用、工具结果、非空 Agent state、终止状态和 SSE 游标，前端订阅默认使用精简模式。
- 收敛后端模块边界：文档解析从 `plugins.parser` 移动到 `knowledge.parser`，内容审查从 `plugins.guard` 移动到 `services.guard`。
- 收敛文件服务边界：文件预览判断抽为独立服务，Viewer 文件系统的 workspace 分支复用用户 workspace 服务，线程运行时上下文解析从泛化 `filesystem_service` 拆出为 agent runtime helper。
- 升级 DeepAgents 到 0.6.7 并适配新版文件系统协议：SubAgentMiddleware 改为显式 subagent spec，Skills prompt 补齐新版占位符；sandbox/skills backend 复用新版 `ReadResult`、`GlobResult`、`GrepResult` 等协议类型，文件权限在 backend 层明确区分 skills、uploads、outputs 与 workspace，保留最小 `CustomCompositeBackend` 以避免非 route glob 误扫其他 route；Agent 上下文压缩改为复用 DeepAgents SummarizationMiddleware，历史摘要与大工具结果统一 offload 到 outputs。
- 优化聊天输入 @ 文件提及：未创建 Thread 时可搜索用户 workspace，创建 Thread 后按当前对话文件优先、workspace 兜底的来源顺序搜索，并拆分 workspace/thread 缓存避免假 thread 与跨用户缓存污染；输入框与用户消息支持将 raw mention 渲染为带类型图标的引用单元，文件仅显示文件名且保留原始沙盒路径文本。
- 重构子智能体为 Agent-backed 形态：移除旧 `subagents` 表与 `/api/system/subagents` 管理链路，子智能体改为 `agents.is_subagent=true` 且使用 `SubAgentBackend`，创建/编辑统一走 Agent 管理入口；内置后端收敛为 `ChatbotAgent` 与 `SubAgentBackend`，Context 分为 `BaseContext`、`ChatBotContext` 与 `SubAgentContext`；主 Agent 通过 Yuxi task middleware 启动真实子 Agent graph，子智能体不再嵌套调用子智能体。沙盒挂载同步拆分为 child checkpoint thread、父对话 uploads/outputs、用户级 workspace 与子 Agent skills scope；主线程状态记录 `subagent_runs` 并在前端 task 工具中展示子智能体名称、执行状态、child thread 和产物，task 工具结果会暴露 child thread ID 且支持传回 `thread_id` 继续既有子智能体线程；子智能体执行复用 `agent_runs(run_type=subagent)` 记录父 run、child thread 与状态，child thread state 查询以 `agent_runs` 关系为准，不再解析 thread ID 反推父线程；真实流式 E2E 覆盖子智能体输出文件可由父线程文件/Viewer API 读取。流式链路参考 DeepAgents event streaming，后端将 LangGraph v3 raw event 归一化为 Yuxi semantic stream event，按父/子线程归属隔离 run SSE chunk，并支持通过 child thread state 拉取子智能体中间过程。
- 修正评估综合得分计算：`overall_score` 改为有答案准确率时取各题准确率平均，否则取各题 `recall@10` 平均，不再把 recall/f1/各 k 检索指标混合平均；历史已存运行不回填。

## v0.6.2 (2026-05-22)

### 新增

- 新增个人工作区预览与管理：提供独立于对话 thread 的用户级 workspace API，并增加“工作区”页面，用于浏览、预览、编辑、上传、下载、删除个人 workspace 文件；默认创建 `agents/AGENTS.md`，并在 Agent 执行时将其内容追加到系统提示词。
- 新增独立模型配置模块：增加 `model_providers` 表、独立管理接口和“模型配置”页面，支持 provider 基础信息、远端候选模型、enabled models 配置和手动添加模型能力。
- 新增远程 Skill 批量安装能力：后端新增 `install_remote_skills_batch()` 与 `POST /remote/install-batch`，前端补充批处理安装 API 和 UI 逻辑。

### 优化

- 下放扩展管理权限：普通管理员现在可进入扩展管理并完整管理 Tools、MCP、SubAgent、Skills；同步放开 Skill 管理接口权限并补充权限测试。
- 调整 Agent 知识库默认选择：未显式配置知识库时默认启用当前用户可访问的全部知识库，显式保存空列表仍表示不启用知识库。
- 优化评估基准自动生成：仅支持 commonrag/Milvus 知识库，默认参考 chunks 数量改为 1；多 chunk 场景复用知识库向量检索选择相似 chunks，不再对全量 chunks 重新计算 embedding。
- 优化 Agent 输入框文件 mention：用户级 workspace 文件候选改为从独立 workspace API 递归加载，不再依赖 active thread；插入时仍转换为 `/home/gem/user-data/workspace/` 沙盒虚拟路径。
- 调整知识库思维导图后端结构：将思维导图路由文件重命名为知识库语义更明确的 router，并把文件列表整理、提示词构建、AI JSON 解析等纯逻辑下沉到知识库 utils。
- 收敛知识库评估后端结构：将评估指标、单题评估、答案生成提示词和自动基准生成算法下沉到 `knowledge/eval`，`EvaluationService` 保留任务、文件和持久化编排职责。
- 扩展管理界面交互逻辑重构：MCP / Subagents / Skills 从“左侧边栏 + 右侧详情面板”调整为“卡片式网格布局 + 路由跳转二级页面”，工具标签页改为卡片网格布局 + 弹窗详情。
- 统一卡片样式：`ExtensionCard` 新增 `tags` prop 并复用于知识库列表页，知识库列表改用 `ExtensionCard` + `ExtensionCardGrid` 替代原有自定义卡片。
- 调整应用主导航：`AppLayout` 升级为默认展开的侧边栏，保留折叠态图标导航，并统一导航项、任务中心、GitHub、用户信息的图标与文字对齐。
- 合并智能体对话导航：移除 `AgentChatComponent` 内部聊天侧边栏，将新建对话入口和对话历史移动到 `AppLayout` 主侧边栏，并通过共享线程 store 统一管理。
- 统一前端 Markdown 预览渲染：新增共享 `MarkdownPreview` 组件与 `markdown_preview` 渲染工具，替换 Agent 消息、文件预览、知识库 chunk、任务工具结果、聊天导出等场景中的旧预览实现。

### 修复

- 修复聊天中普通用户 `@` 提及出不来技能和 MCP 列表的问题：放宽技能列表与 MCP 服务器列表读取接口至已登录用户，并对普通用户请求的 MCP 列表进行敏感连接参数脱敏。
- 修复知识库文档入库状态回退：当已解析文件缺失 `markdown_file` 解析产物时，索引流程会将文件状态恢复为未解析，便于重新解析。
- 修复附件上传后未立即刷新 mention 候选的问题。
- 加固 JWT 鉴权安全：移除历史默认密钥回退，初始化脚本支持生成并持久化 `JWT_SECRET_KEY` 与 `YUXI_INSTANCE_ID`，签发和验证令牌时校验 `iss/aud`，并拒绝已删除或登录锁定用户继续使用旧令牌访问系统。
- 修复模型配置路由请求模型未接收 `embedding_base_url` / `rerank_base_url` 导致前端已填写仍被后端校验拦截的问题。
- 修复番茄溯源溯源码数据完整性校验误报篡改：数据哈希原先基于全量实时数据，包装之后追加采摘/质检/环境/农事记录（或更新批次状态）会误判为篡改。现改为锁定「包装时刻快照」——生成溯源码时记录该批次当时的采摘/质检/环境/农事记录 ID 集合，校验时仅对锁定的记录重新哈希：包装后合法追加不参与校验，包装前记录被修改仍能检测到篡改；历史溯源码沿用旧哈希公式，不破坏既有扫码。
- 修复番茄溯源空包装可创建：添加包装时未校验必填字段，空包装仍会生成溯源码；现要求包装日期、重量（>0）、生产批号均必填，缺失时返回 422。

## v0.6.1 (2026-04-24)

### 新增

- 合并知识库导航入口：左侧导航仅保留"知识库"，文档知识库与图知识库在页面 header 中通过同一组轻量切换入口切换
- 抽象页面轻量切换 header：知识库与扩展管理页直接共用 `ViewSwitchHeader`，收敛文档知识库、知识图谱、Tools、MCP、Subagents、Skills 等入口的信息层级
- 调整任务中心交互：入口移动到 GitHub 按钮下方，并将右侧抽屉展示改为居中弹窗
- 将 `yuxi` 从 uv workspace 成员调整为 `backend/package` 下可独立构建的本地 Python 包，backend 通过 path dependency 以已安装包形式发现依赖
- 新增 Skills 远程安装能力：Skills 管理页支持填写 `owner/repo` 或 GitHub URL，后端通过隔离的临时 `HOME` 调用 `npx skills add` 下载指定 skill
- 调整部门删除语义：删除部门时不再要求用户数为 0，而是将部门下用户迁移到默认部门
- 扩展 viewer 工作区文件操作：`/home/gem/user-data/workspace` 支持从文件系统面板新建文件夹和上传文件
- 为历史线程补充前端本地配置变更提示：当已有历史消息的对话中切换 Agent、切换配置或编辑配置项时，插入非持久化的信息提示
- 调整 Worker run 模式下的消息首屏反馈：前端发送消息时先乐观渲染用户消息，再将前端生成的 `request_id` 透传给 `/api/chat/runs` 与服务端 `init` 对账
- 调整聊天首页的智能体切换入口：当智能体数量 `>= 4` 或内容区宽度小于 `380px` 时自动收敛为"当前智能体 + 下拉按钮"形式
- 调整智能体对话中的工具调用展示：连续工具调用默认折叠为"调用了 N 个工具"的轻量摘要
- 调整输入框配置入口与侧边栏头尾交互：输入区配置按钮改为轻量 dropdown 触发器

### 修复

- 修复沙盒 `workspace` 隔离粒度：宿主机目录从共享 `saves/threads/shared/workspace` 收敛为用户级 `saves/threads/shared/<user_id>/workspace`
- 收紧文件系统安全边界：viewer/chat 下载与删除路径统一基于解析后的真实路径做允许目录校验，阻止通过软链接逃逸工作区/线程目录
- 修复 OIDC 原始用户名绑定中的占位用户解析：解析目标用户 ID 时改为从右侧拆分，避免 `sub` 中包含冒号时把已绑定账号误判成冲突账号
- 修复 DOCX 解析中的图片回插顺序：Docling 导出的多个 `<!-- image -->` 占位符现在按文档图片顺序替换
- 修复前端依赖安全告警：通过 `pnpm.overrides` 将传递依赖 `flatted` 锁定到 `3.4.2`、`lodash-es` 锁定到 `4.18.1`
- 修复对话摘要中间件的工具结果卸载链路：摘要触发时改为将大体积 `ToolMessage` 写入当前 agent 可见的 sandbox outputs 路径
- 修复 agents 页对话侧边栏在 `keep-alive` 路由切换后的误关闭问题
- 调整 Milvus 混合检索实现：集合 schema 增加 BM25 稀疏向量字段、BM25 函数和中文 analyzer 配置
- 重构 MCP 运行时配置加载模型：移除 `MCP_SERVERS` 作为运行正确性前提的设计，改为每次直接从数据库读取最新 MCP 配置
- 为知识库检索工具补充 `metadata.filepath` 注入：在 `query_kb` 统一出口基于会话可见知识库构建 `file_id -> /home/gem/kbs/...` 映射并回填 Milvus 检索结果
- 移除知识库沙盒文件系统映射：Agent 不再通过 `/home/gem/kbs` 遍历知识库文件，继续通过 `query_kb` 和 `open_kb_document` 检索与打开文档。

## v0.6.0 (2026-04-01)


### 新增
- 重构后端代码 src -> backend/package/yuxi
- 重构文档解析，统一文档解析体验，并新增 Parser 类
- 新增 LITE 模式启动，启动时不加载知识库、知识图谱相关模块，可以使用 make up-lite 快捷启动
- 新增沙盒环境，详见后续文档更新，统一沙盒虚拟路径前缀默认值为 `/home/gem/user-data`
- 新增基于沙盒的文件系统，前端工作台可以查看文件系统，支持预览（文本、图片、PDF、HTML）、下载文件
- 新增 `present_artifacts` 内置工具：Agent 可将 `/home/gem/user-data/outputs/` 下的结果文件显式写入 LangGraph state 的 `artifacts` 字段，前端支持在输入框顶部以默认折叠的堆叠卡片展示本轮交付物文件，并保持可下载、可预览能力
- 交付物卡片新增“保存到工作区”能力：支持将单个交付物复制到共享目录 `workspace/saved_artifacts/`，并复用现有文件树/预览/mention 体系立即可见
- 新增基于沙盒的知识库只读映射，按“用户可访问知识库 ∩ 当前 Agent 已启用知识库”暴露原始文件与解析后的 Markdown
- 重构附件系统，直接集成在了沙盒文件系统中，附件上传后直接落盘到沙盒挂载目录
- 优化前端流式消息体验：新增通用 `useStreamSmoother` 调度层，统一平滑 Agent runs SSE、普通聊天流与审批恢复流中的 `loading` chunk
- 优化项目文档说明，并添加贡献指南
- 重构前端 Agent 路由结构，体验更加顺畅，切换更加自然（类 chatgpt 体验）
- 新增 API Key 认证功能，支持外部系统通过 API Key 调用系统服务
- 新增 subagents 的支持，支持在 web 中添加 subagents，以及两个内置的子智能体
- 新增内置Skills reporter，并移除内置 Agent reporter，数据库报表将由 Skills 完成
- 新增内置 Skills `deep-reporter`，用于指导生成科研报告、行业调研和其他深度分析类长报告
- 重构内置 Skills/MCP/Subagents 安装/添加/移除机制：内置 skill 支持按需安装、基于 `version + content_hash` 的更新提示与覆盖确认，不再使用服务器级开关切换
- 新增知识库 PDF、图片的预览功能
- 重构后端测试目录结构：按 `unit / integration / e2e` 分层迁移现有测试，拆分全局 `conftest.py`，统一测试入口为 `uv run --group test pytest`，并新增独立测试规范文档 `docs/develop-guides/testing-guidelines.md`
- 新增工具元数据 `config_guide` 字段：后端工具列表接口现在可返回“给人看的配置说明”，前端工具详情页会展示该说明，用于提示工具使用前需要配置的环境变量或入口；首批为 MySQL 工具和 `Qwen-Image` 补充了配置指引
- 补充 Langfuse 集成方案文档：明确采用“云端优先、先 tracing 后 feedback”的接入路径，并约定 Yuxi 的 `user/thread` 到 Langfuse `user_id/session_id` 的映射关系
- 新增面向用户的 Langfuse 集成文档：在“智能体开发”分组中说明 Langfuse 的定位、能力、配置方式与查看路径，并与当前 `LANGFUSE_BASE_URL` 配置保持一致

<!-- 添加到这里 -->

### 修复

- 调整聊天首页的智能体切换入口：在无历史对话时，智能体数量 `<= 3` 且 `chat-main` 宽度不小于 `380px` 时继续使用横向 segmented；当智能体数量 `>= 4` 或内容区宽度小于 `380px` 时自动收敛为“当前智能体 + 下拉按钮”形式，避免多智能体或窄屏场景下入口被截断
- 发布前一致性修复：统一 0.6.0 版本号（backend/package/web）、更新 dev/prod 镜像标签语义（`0.6.0.dev` / `0.6.0`），并为 `/api/system/health` 补充 `version` 字段，提升部署可观测性与发版追溯能力
- 收敛“状态工作台”自动弹出规则：前端不再因为共享 `workspace` 或文件系统天然存在内容而默认展开，改为仅在 `/home/gem/user-data/uploads` 或 `/home/gem/user-data/outputs` 下检测到实际文件时自动弹出；手动打开、关闭、刷新和伸缩交互保持不变
- 调整智能体 todo 展示语义：待办状态不再作为 `capabilities` 前端开关，而是直接根据运行态 `agent_state.todos` 渲染；同时将 todo 入口从 Agent Panel 移到输入框内的轻量浮层，并让右侧“状态工作台”收敛为文件系统视图，输入框按钮文案同步由“状态”调整为“文件”
- 优化 Agent 输入框 mention 行为：在保留附件 mention 的同时，将共享 `workspace` 文件纳入候选范围；并将 `@` 空查询时的候选列表改为空，仅在继续输入后再执行筛选，避免工作区文件过多时直接铺满下拉面板
- 为前端工作台文件树补齐文件删除能力：`/api/viewer/filesystem/file` 新增删除接口，`AgentPanel` 文件节点新增删除按钮与确认交互，删除后会同步刷新树与预览状态
- 扩展 Agent Panel 状态工作台删除能力：继续复用 `DELETE /api/viewer/filesystem/file`，在保持接口不变的前提下支持删除文件夹；空目录与非空目录现在都会递归删除，`workspace` 下目录也可直接清理，前端目录节点同步新增删除入口与对应确认文案
- 调整前端工作台文件预览交互：恢复默认侧边/弹窗预览，并新增显式“全屏预览”入口；全屏模式下由预览内容直接覆盖整页，仅保留右上角悬浮关闭按钮；同时修复 HTML 文件首次在弹窗中预览偶现白屏的问题，改为在内容更新后强制重建 `iframe`
- 统一 Agent Panel 文件预览与消息区交付物预览组件：两处改为复用同一套 `AgentFilePreview` 预览实现，并为交付物预览补齐与工作台一致的“全屏预览”入口
- 修复交付物卡片展开后的长列表展示：当单轮交付物文件超过面板可见高度时，卡片内容区改为显示纵向滚动条，避免超过约 10 项后底部文件与操作按钮被裁切
- 兼容旧版已安装的内置 `reporter` 技能记录：`update_builtin_skill` 现在会识别由 `system` 或 `builtin-system` 管理的历史记录，避免更新时误报“技能 `reporter` 不是内置 skill”
- 调整沙盒 user-data 目录隔离策略：`workspace` 改为共享目录 `saves/threads/shared/workspace`，`uploads/outputs` 继续保持 thread 级隔离；同时更新 thread artifact 权限校验、viewer 文件系统列举逻辑，以及对应的 router/E2E 测试
- 重构聊天接口请求模型：流式与非流式聊天统一使用 `query + agent_config_id` 请求体，并移除路径中的 `agent_id`；同时修复非流式接口实际误走流式执行链路的问题，改为调用 `invoke_messages` 一次性执行，并补充对应测试
- 修复对话线程与 Agent 配置错位的问题：发送消息时将当前 `agent_config_id` 绑定到 thread 的 `extra_metadata`，线程列表接口返回该绑定值，前端切换历史 thread 时会自动恢复对应配置
- 为沙盒与 viewer 文件系统补齐知识库只读映射：新增 `/home/gem/kbs` 命名空间，按“用户可访问知识库 ∩ 当前 Agent 已启用知识库”暴露原始文件与解析后的 Markdown，并补充对应后端与 viewer 路由测试
- 优化 viewer 文件系统目录树加载：根目录与 `/home/gem/user-data` 改为直接读取本地线程挂载目录，不再为只读树视图触发 sandbox 冷启动，并补充对应后端测试
- 修复 `/home/gem/user-data` 根目录文件不可见的问题：根目录现在会同时展示 thread 目录下的真实文件和 `workspace` 入口，不再只保留固定命名空间目录
- 修复前端工具图标与渲染匹配不准确的问题：工具管理列表与工具调用结果统一改为基于工具 `id` 的精确映射，避免模糊匹配导致的误渲染，未命中的工具不再显示默认扳手图标
- 修复 GitHub Pages 文档部署工作流失败：移除 `actions/setup-node@v4` 对不存在 `docs/package-lock.json` 的缓存依赖，并将 `docs` 目录安装命令从 `npm ci` 调整为 `npm install`，避免因未提交锁文件导致 CI 在依赖缓存和安装阶段直接失败
- 修正沙盒 provisioner backend 命名与配置说明：统一对外使用 `docker` / `kubernetes`，保留 `local` 作为兼容别名；同步清理 compose 中未生效的 provisioner 环境变量、补齐 K8s 相关变量注释，并更新沙盒架构文档中的默认模式与 backend 描述
- 修复智能体配置列表接口在“无配置自动创建默认配置”路径下的参数缺失：补齐 `get_or_create_default` 的 `agent_id` 入参，避免 `/api/chat/agent/{agent_id}/configs` 返回 500
- 修复 LightRAG 同库写入并发导致的入库失败：为 `index_file` / `update_content` 增加按知识库维度的串行锁，并补齐 `documents` 接口 `auto_index` 阶段对最新解析状态的回写与回归测试，避免长时间入库任务进行中再次选择同库文件时直接并发写入报错

<!-- 添加到这里 -->


---


## v0.5

### 新增

- 优化 OCR 体验并新增对 Deepseek OCR 的支持
- 优化 RAG 检索，支持根据文件 pattern 来检索（Agentic Mode）
- 重构智能体对于“工具变更/模型变更”的处理逻辑，无需导入更复杂的中间件
- 重构知识库的 Agentic 配置逻辑，与 Tools 解耦
- 将工具与知识库解耦，在 context 中就完成解耦，虽然最终都是在 Agent 中的 get_tools 中获取
- 优化chunk逻辑，移除 QA 分割，集成到普通分块中，并优化可视化逻辑
- 重构知识库处理逻辑，分为 上传—解析—入库 三个阶段
- 重构 MCP 相关配置，使用数据库来控制 [#469](https://github.com/xerrors/Yuxi/pull/469)
- 使用 docling 解析 office 文件（docx/xlsx/pptx）
- 优化后端的依赖，减少镜像体积 [#428](https://github.com/xerrors/Yuxi/issues/428)
- 优化 liaghtrag 的知识库调用结果，提供 content/graph/both 多个选项
- 优化数据库查询工具，可通过设计环境变量添加描述，让模型更好的调用
- 优化任务组件，改用 postgresql 存储，并新增删除任务的接口
- 支持更多类型的文档源的导入功能（支持后端配置的白名单的 URL 导入）

### 修复

- 修复文件上传弹窗中 OCR 下拉选项展开时不会自动检查服务状态的问题
- 修复知识图谱上传的向量配置错误，并新增模型选择以及 batch size 选择
- 修复部分场景下获取工具列表报错 [#470](https://github.com/xerrors/Yuxi/pull/470)
- 修改方法备注信息 [#478](https://github.com/xerrors/Yuxi/pull/478)
- 修复多次 human-in-the-loop 的渲染解析问题 [#453](https://github.com/xerrors/Yuxi/issues/453) [#475](https://github.com/xerrors/Yuxi/pull/475)
- 修复沙盒后端接入回归：补齐 composite backend 的 `sandbox_backend` 参数、限制 `/api/sandbox/prepare` 仅允许访问当前用户线程、确保 `release()` 之后的 `destroy()` 会真正停止热池容器，并恢复 docker-compose 的完整模式默认值
- 重构沙盒为 deer-flow 风格的 AIO provider：切换为 thread-local sandbox、统一 `/home/gem/user-data/{workspace,uploads,outputs}` 固定路径、移除公开 `/api/sandbox/*` 生命周期接口，并补充 lite 模式下的 provider 生命周期、filesystem API 与 sandbox 复用/隔离 E2E 验证
- 调整聊天附件存储链路：线程附件改为直接落盘到 `saves/threads/<thread_id>/user-data/uploads`，解析成功后额外生成 `uploads/attachments/*.md`，不再依赖 MinIO 或显式上传到 sandbox
- 修复知识库文件列表包体异常膨胀：上传阶段不再把批次级 `content_hashes` 写入每个文件的 `processing_params`，并从数据库详情列表接口中移除该字段，改为按需读取单文件详情

## v0.4

### 新增
- 新增对于上传附件的智能体中间件，详见[文档](https://xerrors.github.io/Yuxi/advanced/agents-config.html#%E6%96%87%E4%BB%B6%E4%B8%8A%E4%BC%A0%E4%B8%AD%E9%97%B4%E4%BB%B6)
- 新增多模态模型支持（当前仅支持图片），详见[文档](https://xerrors.github.io/Yuxi/advanced/agents-config.html#%E5%A4%9A%E6%A8%A1%E6%80%81%E5%9B%BE%E7%89%87%E6%94%AF%E6%8C%81)
- 新建 DeepAgents 智能体（深度分析智能体），支持 todo，files 等渲染，支持文件的下载。
- 新增基于知识库文件生成思维导图功能（[#335](https://github.com/xerrors/Yuxi/pull/335#issuecomment-3530976425)）
- 新增基于知识库文件生成示例问题功能（[#335](https://github.com/xerrors/Yuxi/pull/335#issuecomment-3530976425)）
- 新增知识库支持文件夹/压缩包上传的功能（[#335](https://github.com/xerrors/Yuxi/pull/335#issuecomment-3530976425)）
- 新增自定义模型支持、新增 dashscope rerank/embeddings 模型的支持
- 新增文档解析的图片支持，已支持 MinerU Officical、Docs、Markdown Zip格式
- 新增暗色模式支持并调整整体 UI（[#343](https://github.com/xerrors/Yuxi/pull/343)）
- 新增知识库评估功能，支持导入评估基准或者自动构建评估基准（目前仅支持Milvus类型知识库）详见[文档](https://xerrors.github.io/Yuxi/intro/evaluation.html)
- 新增同名文件处理逻辑：遇到同名文件则在上传区域提示，是否删除旧文件
- 新增生产环境部署脚本，固定 python 依赖版本，提升部署稳定性
- 优化图谱可视化方式，统一图谱数据结构，统一使用基于 G6 的可视化方式，同时支持上传带属性的图谱文件，详见[文档](https://xerrors.github.io/Yuxi/intro/knowledge-base.html#_1-%E4%BB%A5%E4%B8%89%E5%85%83%E7%BB%84%E5%BD%A2%E5%BC%8F%E5%AF%BC%E5%85%A5)
- 优化 DBManager / ConversationManager，支持异步操作
- 优化 知识库详情页面，更加简洁清晰，增强文件下载功能

### 修复
- 修复 GitHub Actions 的 Ruff CI 在仓库根目录执行 `uv sync` 导致找不到 `backend/pyproject.toml` 的问题，同时统一检查路径为 `backend/package`
- 修复重排序模型实际未生效的问题
- 修复消息中断后消息消失的问题，并改善异常效果
- 修复当前版本如果调用结果为空的时候，工具调用状态会一直处于调用状态，尽管调用是成功的
- 修复检索配置实际未生效的问题
- 修复 sandbox 文件系统 `ls` 在异常输出下触发 `KeyError: 'path'` 的问题，并将工具调用异常降级为错误消息，避免直接中断聊天 stream
- 修复智能体状态面板中文件树仍依赖 `agent_state.files` 的问题，改为通过真实 `/api/filesystem/*` 接口按层懒加载后端可见文件系统，并让输入框下方状态按钮常态化打开工作区视图
- 为工作台新增 viewer-oriented filesystem service 与 `/api/viewer/filesystem/*` 接口，解耦 agent backend 语义，支持真实目录浏览、原始文件读取与下载
- 重写沙盒技术文档，明确 thread-local sandbox、viewer-oriented filesystem service、`/mnt` 命名空间、skills 可见性与当前实现边界，替换过时的 `/api/sandbox/*` 与 user-level 设计描述
- 收紧沙盒遗留代码：修复未注册 `sandbox_router` 中残留的 user/thread 参数错位，改进宿主机挂载路径映射逻辑，并为 remote sandbox provisioner 增加基础 URL 校验与销毁失败日志
- 修复 builtin skill 内容哈希计算对单文件使用 `read_bytes()` 的无上限内存读取问题，改为分块计算并补充回归测试

### 破坏性更新

- 移除 Chroma 的支持，当前版本标记为移除
- 移除模型配置预设的 TogetherAI


## v0.3
### Added
- 添加测试脚本，覆盖最常见的功能（已覆盖API）
- 新建 tasker 模块，用来管理所有的后台任务，UI 上使用侧边栏管理。Tasker 中获取历史任务的时候，仅获取 top100 个 task。
- 优化对文档信息的检索展示（检索结果页、详情页）
- 优化全局配置的管理模型，优化配置管理
- 支持 MinerU 2.5 的解析方法 <Badge type="info" text="0.3.5" />
- 修改现有的智能体Demo，并尽量将默认助手的特性兼容到 LangGraph 的 [`create_agent`](https://docs.langchain.com/oss/python/langchain/agents) 中
- 基于 create_agent 创建 SQL Viewer 智能体 <Badge type="info" text="0.3.5" />
- 优化 MCP 逻辑，支持 common + special 创建方式 <Badge type="info" text="0.3.5" />
- LightRAG 知识库应该可以支持修改 LLM

### Fixed
- 修复本地知识库的 metadata 和 向量数据库中不一致的情况。
- v1 版本的 LangGraph 的工具渲染有问题
- upload 接口会阻塞主进程
- LightRAG 知识库查看不了解析后的文本，偶然出现，未复现
- 智能体的加载状态有问题：（1）智能体加载没有动画；（2）切换对话和加载中，使用同一个loading状态。
- 前端工具调用渲染出现问题
- 当前 ReAct 智能体有消息顺序错乱的 bug，且不会默认调用工具
- 修复文件管理：（1）文件选择的时候会跨数据库；（2）文件校验会算上失败的文件；
