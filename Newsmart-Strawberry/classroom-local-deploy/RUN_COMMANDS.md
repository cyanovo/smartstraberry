# 学生本地前后端运行命令

本方案只操作学生电脑，不需要在 Docker 宿主机执行任何命令。

## 一、目录位置

项目根目录：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main
```

PyCharm 打开的后端目录：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend
```

VS Code 打开的前端目录：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\web
```

学生电脑上的实际项目路径可以不同，但必须保持项目内部目录结构不变。

## 二、修改 Docker 节点 IP

打开：

```text
backend\classroom.env
```

当前配置为：

```env
CLASSROOM_NODE_HOST=172.168.1.184
```

学生只需要修改这一处 IP。前端地址、数据库地址、Redis地址等不需要手工修改。

## 三、学生从零开始的完整操作

下面按学生实际操作顺序执行，不要跳步。

### 第1步：修改唯一的节点IP

1. 打开项目根目录。
2. 进入 `backend` 文件夹。
3. 用记事本或 PyCharm 打开 `classroom.env`。
4. 确认文件内容是：

```env
CLASSROOM_NODE_HOST=172.168.1.184
```

这个文件只保留这一项配置，不需要修改其他后端地址。

### 第2步：首次编译前后端

在Windows文件资源管理器中打开：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\classroom-local-deploy
```

双击：

```text
student-compile.cmd
```

等待窗口显示：

```text
Backend dependencies and frontend production build are ready.
```

首次编译可能需要较长时间。没有看到成功提示时，不要继续启动项目。

### 第3步：检查Docker节点

仍然在 `classroom-local-deploy` 文件夹中双击：

```text
student-doctor.cmd
```

必须至少确认以下项目显示 `[OK]`：

```text
PostgreSQL
Redis
MinIO
Milvus
Neo4j
Sandbox
```

如果全部是 `[FAIL]`，不要启动PyCharm，先确认 `172.168.1.184` 对应电脑已经开机并且处于同一网络。

### 第4步：PyCharm打开后端项目

1. 启动 PyCharm。
2. 点击 `File` → `Open`。
3. 选择下面这个文件夹，注意不是选择整个项目根目录：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend
```

4. 点击 `OK` 或 `Open as Project`。
5. 如果出现安全提示，选择信任该项目。

PyCharm左侧项目树顶层应该能直接看到：

```text
package
server
test
run_classroom_api.py
run_classroom_worker.py
classroom.env
pyproject.toml
```

如果左侧最上层显示的是 `test1-main`，说明打开的文件夹层级不对，应关闭后重新打开 `backend` 文件夹。

### 第5步：PyCharm选择Python解释器

1. 点击 `File` → `Settings`。
2. 打开 `Project` → `Python Interpreter`。
3. 点击 `Add Interpreter` → `Add Local Interpreter`。
4. 选择 `Existing environment`。
5. 选择下面的解释器：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend\.venv\Scripts\python.exe
```

6. 保存设置。

如果找不到 `.venv` 文件夹，说明 `student-compile.cmd` 没有成功执行。

### 第6步：PyCharm启动后端API

1. 在PyCharm左侧找到 `run_classroom_api.py`。
2. 右键该文件。
3. 点击 `Run 'run_classroom_api'`。
4. 不要关闭下方的Run窗口。
5. 等待日志出现：

```text
Application startup complete.
```

6. 浏览器访问：

```text
http://127.0.0.1:5050/api/system/health
```

正常响应示例：

```json
{"status":"ok","message":"服务正常运行"}
```

还可以打开接口文档：

```text
http://127.0.0.1:5050/docs
```

### 第7步：PyCharm启动后端Worker

API保持运行，不要停止。

1. 在PyCharm左侧找到 `run_classroom_worker.py`。
2. 右键该文件。
3. 点击 `Run 'run_classroom_worker'`。
4. PyCharm下方会出现第二个运行标签。
5. API和worker两个运行标签都必须保持运行状态。

如果只运行API而没有运行worker，登录和普通查询可能正常，但智能体任务会一直显示 `pending`。

### 第8步：VS Code打开前端项目

1. 启动 VS Code。
2. 点击 `File` → `Open Folder`。
3. 只选择下面的 `web` 文件夹：

```text
D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\web
```

4. 点击 `Select Folder`。
5. 点击 `Terminal` → `New Terminal`。
6. 确认终端当前目录最后是：

```text
...\test1-main\web
```

7. 执行：

```powershell
pnpm run dev
```

8. 等待终端显示：

```text
Local: http://127.0.0.1:5173/
```

9. 浏览器打开终端实际显示的地址。

如果5173被占用，Vite可能自动使用5174或5175，应以终端显示的 `Local` 地址为准。

### 第9步：每天的启动顺序

首次编译成功以后，每天只需要：

1. 双击 `student-doctor.cmd`，确认节点在线。
2. PyCharm右键运行 `run_classroom_api.py`。
3. 等待 `Application startup complete`。
4. PyCharm右键运行 `run_classroom_worker.py`。
5. VS Code在 `web` 终端执行 `pnpm run dev`。
6. 打开前端页面。

## 四、首次编译命令说明

需要提前安装：

- Python 3.12 x64
- Node.js 24 x64
- Git

在项目根目录双击：

```text
classroom-local-deploy\student-compile.cmd
```

或者在 PowerShell 中运行：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main
.\classroom-local-deploy\student-compile.cmd
```

该命令会：

1. 创建 `backend\.venv` Python虚拟环境。
2. 安装后端依赖。
3. 安装前端依赖。
4. 执行一次前端生产构建。

首次安装包含 PyTorch、OCR 和文档解析依赖，下载时间较长。成功后不需要每天重复执行。

## 五、检查节点和本地环境

在项目根目录运行：

```powershell
.\classroom-local-deploy\student-doctor.cmd
```

正常情况下应看到 PostgreSQL、Redis、MinIO、Milvus、Neo4j 和 Sandbox 均显示 `[OK]`。

如果全部显示 `[FAIL]`，检查：

1. Docker电脑是否开机。
2. 学生电脑和Docker电脑是否在同一个网络。
3. `backend\classroom.env` 中的IP是否正确。
4. Docker电脑IP是否发生变化。

## 六、PyCharm启动后端API命令说明

### PyCharm配置

用 PyCharm 打开 `backend` 目录，解释器选择：

```text
backend\.venv\Scripts\python.exe
```

在项目窗口中找到并右键运行：

```text
run_classroom_api.py
```

也可以在 PyCharm Terminal 中运行：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend
.\.venv\Scripts\python.exe .\run_classroom_api.py
```

启动成功后：

```text
后端API：http://127.0.0.1:5050
健康检查：http://127.0.0.1:5050/api/system/health
接口文档：http://127.0.0.1:5050/docs
```

第一次启动需要加载成熟度检测模型，等待时间会比后续启动更长。看到 `Application startup complete` 才表示启动完成。

## 七、PyCharm启动后端Worker命令说明

API启动后，还必须再启动worker。

在项目窗口中找到并右键运行：

```text
run_classroom_worker.py
```

也可以打开第二个 PyCharm Terminal：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend
.\.venv\Scripts\python.exe .\run_classroom_worker.py
```

API和worker必须同时运行。未启动worker时，智能体异步任务会一直显示 `pending`。

建议在 PyCharm 中建立一个 Compound 运行配置，把 `run_classroom_api.py` 和 `run_classroom_worker.py` 放在一起，实现一次启动两个后端进程。

## 八、VS Code启动前端命令说明

用 VS Code 打开 `web` 目录，然后在 Terminal 中运行：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\web
pnpm run dev
```

启动成功后访问：

```text
http://127.0.0.1:5173
```

前端默认代理到学生本机的 `http://127.0.0.1:5050`，不需要把前端地址改成 Docker 节点 IP。

## 九、正确启动顺序

每天运行时按以下顺序：

1. 确认 Docker 节点电脑已经启动。
2. 运行 `student-doctor.cmd` 检查网络。
3. PyCharm运行 `run_classroom_api.py`。
4. PyCharm运行 `run_classroom_worker.py`。
5. VS Code运行 `pnpm run dev`。
6. 浏览器打开 `http://127.0.0.1:5173`。

## 十、停止项目

在 PyCharm 中分别停止 API 和worker运行配置。

在 VS Code Terminal 中按：

```text
Ctrl+C
```

即可停止前端。

停止学生本地项目不会影响 Docker 节点，也不会影响其他学生。

## 十一、本机端口被占用时

普通学生电脑一般直接使用 `5050` 和 `5173`。如果本机已有程序占用端口，可以临时改用其他端口。

后端临时使用 `15050`：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\backend
$env:API_PORT="15050"
.\.venv\Scripts\python.exe .\run_classroom_api.py
```

前端必须同时指向新的后端端口：

```powershell
cd D:\work\strawberry\Newsmart-Strawberry\test2\test1-main\web
$env:VITE_API_URL="http://127.0.0.1:15050"
pnpm run dev -- --port 15173
```

此时访问：

```text
http://127.0.0.1:15173
```

关闭当前 Terminal 后，这些临时端口环境变量自动失效，不会修改项目配置。

## 十二、按现象排查

### PyCharm提示 `No module named uvicorn` 或 `No module named arq`

原因：解释器选择错误，或者后端没有编译完成。

检查PyCharm解释器是否为：

```text
backend\.venv\Scripts\python.exe
```

不是该解释器时重新选择；没有 `.venv` 时重新运行 `student-compile.cmd`。

### 后端提示修改 `CLASSROOM_NODE_HOST`

打开：

```text
backend\classroom.env
```

确认内容是：

```env
CLASSROOM_NODE_HOST=172.168.1.184
```

### `student-doctor.cmd`全部显示 `[FAIL]`

这不是PyCharm代码错误，表示学生电脑无法连接Docker节点。检查节点电脑、局域网和IP地址。

### 后端提示端口5050被占用

先关闭电脑上其他占用5050的程序。普通学生电脑不要同时运行Docker版本和PyCharm版本后端。

如果必须临时换端口，按照上一节同时修改API启动端口和前端 `VITE_API_URL`。

### 前端能打开，但接口请求失败

依次检查：

1. `run_classroom_api.py` 是否仍在运行。
2. `http://127.0.0.1:5050/api/system/health` 是否正常。
3. VS Code是否打开了正确的 `web` 文件夹。
4. 前端终端是否有代理错误。

### 智能体任务一直显示 `pending`

检查 `run_classroom_worker.py` 是否运行。API和worker必须同时启动，并使用同一个项目和同一个 `.venv` 解释器。

### 后端启动很慢

首次启动需要导入文档解析依赖并加载成熟度检测模型。等待出现 `Application startup complete`，不能只看到进程启动就立即打开前端测试。

## 十三、最简命令汇总

首次编译：

```powershell
.\classroom-local-deploy\student-compile.cmd
```

环境检查：

```powershell
.\classroom-local-deploy\student-doctor.cmd
```

后端API：

```powershell
cd backend
.\.venv\Scripts\python.exe .\run_classroom_api.py
```

后端worker（第二个终端）：

```powershell
cd backend
.\.venv\Scripts\python.exe .\run_classroom_worker.py
```

前端：

```powershell
cd web
pnpm run dev
```
