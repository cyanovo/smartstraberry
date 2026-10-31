# 学生 PyCharm + VS Code 本地部署

Docker 同学的宿主机、Compose、容器和环境变量全部保持不变。普通学生只在自己的 Windows 电脑上编译并运行前后端。

完整运行命令见 [`RUN_COMMANDS.md`](RUN_COMMANDS.md)。

## 到手后的三步

### 1. 只修改一个 IP

打开 `backend/classroom.env`，将：

```env
CLASSROOM_NODE_HOST=CHANGE_ME
```

改成运行 Docker 的同学电脑的局域网 IPv4，例如：

```env
CLASSROOM_NODE_HOST=192.168.1.20
```

不要修改其他源码或数据库地址。后端会自动生成 PostgreSQL、Redis、MinIO、Milvus、Neo4j、OCR 和沙盒地址；学生实例 ID 和 ARQ 队列名根据本机自动生成。

### 2. 编译前后端

安装 Python 3.12 x64 和 Node.js 24 x64，然后双击：

```text
classroom-local-deploy/student-compile.cmd
```

该脚本会创建 `backend/.venv`、安装后端和前端依赖，并执行一次前端生产构建。编译完成后可以运行 `student-doctor.cmd` 检查节点连接。

### 3. 在 IDE 中运行

#### PyCharm 后端

打开项目的 `backend` 目录，解释器选择：

```text
backend/.venv/Scripts/python.exe
```

分别右键运行：

```text
backend/run_classroom_api.py
backend/run_classroom_worker.py
```

两个进程都属于后端：API 监听 `http://127.0.0.1:5050`，worker 处理当前学生提交的智能体异步任务。可以在 PyCharm 中建立 Compound 配置同时启动这两个脚本。

#### VS Code 前端

用 VS Code 打开 `web` 目录，在终端运行：

```powershell
pnpm run dev
```

浏览器打开 `http://127.0.0.1:5173`。前端已经默认代理到本机 `5050`，不需要修改前端后端地址。

## 学生本地与共享节点的分工

- 学生本地：Vue/Vite、FastAPI、ARQ worker、摄像头与成熟度检测模型。
- Docker 节点：PostgreSQL、Redis、MinIO、Milvus、Neo4j、MinerU、PaddleX、sandbox-provisioner。
- MQTT 在学生后端自动关闭，避免多人重复采集。
- 每台学生电脑自动使用独立任务队列，互不抢任务。
- 共享业务数据和溯源数据写入节点 PostgreSQL；学生首次启动只会通过应用连接补齐兼容表结构，不修改节点文件、Compose 或容器配置。
- 沙盒服务返回的内部主机名由学生后端替换为填写的节点 IP，不要求修改 Docker 节点。

## 网络前提

现有 Docker 节点必须已经能从学生电脑访问以下端口：

```text
5432  PostgreSQL
6379  Redis
9000  MinIO
19530 Milvus
7687  Neo4j
8002  sandbox-provisioner
```

如果 `student-doctor.cmd` 报端口不通，说明现有节点网络或防火墙没有开放。这个问题无法仅靠修改学生代码绕过。

MinerU `30001`、PaddleX `8080` 只在 Docker 节点启用了对应 Compose profile 时可用，不影响基础前后端启动。
