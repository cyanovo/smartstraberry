# 本地镜像站接入与构建指南

> 本项目的 Python 包、npm 依赖、系统包和 Docker 基础镜像都可以通过**局域网镜像站**（cyanpypi）统一加速缓存，
> 构建不再依赖公网速度。本文说明从零接入到构建启动的完整流程。
> **镜像站地址默认 `192.168.31.83`**（以老师提供为准，下文用 `IP` 代替）。

---

## 一、这是什么

镜像站提供 4 类服务，全部跑在老师那台机器上：

| 端口 | 服务 | 用途 |
|---|---|---|
| 8088 | PyPI 镜像 | pip / uv 安装 Python 包 |
| 4873 | npm 镜像 | npm / pnpm / yarn 安装前端依赖 |
| 3142 | APT 代理 | Docker 构建时安装 Debian 系统包 |
| 5000 | Docker Registry | 项目基础镜像（python / node / postgres / redis / neo4j 等） |

配置脚本会一次性把项目所有下载位置指到镜像站；镜像站没开或配置没生效时，构建工具还会**自动回退公网**，不会卡死。

## 二、使用前提

1. 与镜像站在**同一局域网**（能 ping 通 `IP`）。
2. Windows + **Docker Desktop**（已安装并登录过）。
3. 镜像站已启动（老师确认 4 个端口都通；自己可测：浏览器打开 `http://IP:8088/` 能看到首页）。

## 三、三步接入

### 第 1 步：克隆项目

```bash
git clone <项目仓库地址>
cd <项目目录>        # 含 backend/ web/ docker/ docker-compose.yml 的目录
```

### 第 2 步：运行配置脚本（一次性）

**双击 `setup-strawberry-mirrors.bat`**，输入镜像站 IP（如 `192.168.31.83`），回车。

脚本会自动完成三件事（会弹一次管理员授权，点"是"）：

1. 写 `hosts`：`pypi.strawberry.lan`、`npm.strawberry.lan`、`apt.strawberry.lan`、`registry.strawberry.lan` → IP
2. 写 Docker Desktop 的 `daemon.json`（**两个位置都写**，兼容新旧版本 Docker Desktop），添加本地 registry 为 insecure
3. 在项目 `.env` 写入镜像配置块（PyPI / npm / APT / 所有镜像变量 → 本地站）

> 也可以用命令行版（管理员 PowerShell，可批量处理多个项目）：
> ```powershell
> powershell -ExecutionPolicy Bypass -File D:\cyanproject\cyanpypi\scripts\configure-client.ps1 -MirrorHostIp 192.168.31.83 -ProjectsBaseDir D:\work\strawberry
> ```

脚本提示"重启 Docker Desktop"时，**手动重启一次**（或者直接用第 3 步的 build-with-fallback，它会自动重启）。

### 第 3 步：构建启动（推荐）

**双击 `build-with-fallback.bat`**（等价于 `docker compose up -d --build`），或命令行：

```powershell
# 构建并启动全部
powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -Up

# 只构建指定服务
powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -Up -Services api,web

# 只检测不构建
powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -DryRun
```

配置已确认生效后，也可以直接：

```bash
docker compose up -d
```

## 四、build-with-fallback 做了什么（自动检测 + 自愈 + 回退）

1. **探测镜像站** 4 个端口（8088 / 4873 / 3142 / 5000）。
2. **自愈配置**：检查 Docker 的 insecure-registry，缺失时自动写入两个 `daemon.json` 位置并自动重启 Docker Desktop，避免 "HTTPS 访问 HTTP registry" 这类错误。
3. **本地优先**：镜像站可达 → 全部走本地镜像。
4. **自动回退**：镜像站不可达 → 镜像走 Docker Hub/公共镜像、Python 走 pypi.org、npm 走 npmmirror、apt 不走代理，构建不中断。
5. **localhost 兜底**：如果本机就是镜像站且配置实在无法修复，自动改用 `localhost:5000`（该地址永不需要 insecure 配置）。

## 五、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| `http: server gave HTTP response to HTTPS client` | insecure-registry 配置没生效（Docker Desktop 版本不同，读的配置文件位置不同） | 用 `build-with-fallback.bat` 构建（自动修复并重启）；或管理员运行 `docker-doctor.ps1`；或手动重启 Docker Desktop |
| 拉取镜像失败 / 连接被拒绝 | 镜像站没启动，或不在同一局域网 | 确认 4 个端口可访问；让老师启动镜像站；期间用 build-with-fallback 会自动走公网 |
| `registry.strawberry.lan` 无法解析 | hosts 没写入 | 重跑 `setup-strawberry-mirrors.bat`（需管理员） |
| pip / uv 报 403 | 清华源被当前网络屏蔽 | 无需处理，镜像站会自动回退 pypi.org |
| 首次构建很慢（20-30 分钟） | uv sync 300+ 个包 + pnpm + 5 个镜像的解压编译，大头在 CPU/磁盘 | 正常现象；第二次起有缓存会快很多 |
| `docker compose up` 直接构建失败 | 配置还没生效 / 镜像站没开 | 统一改用 `build-with-fallback.bat` 构建 |

## 六、单独排障工具

```powershell
# 自检 + 自动修复 Docker 本地仓库配置
powershell -ExecutionPolicy Bypass -File docker-doctor.ps1 -MirrorHostIp 192.168.31.83
```

## 七、注意事项

- **`.env` 含个人密钥，不要提交到 git**（已在 `.gitignore` 中）。每个人第一次跑配置脚本时，会用自己的 IP 重新生成 `.env`。
- **paddlex / mineru** 属于 `profile: all`（需要 GPU + 外网下载模型），默认 `docker compose up -d` 不会构建它们。
- 镜像站网页 `http://IP:8088/` 上有"使用教程"和"旧项目改造"说明，也可以直接下载配置脚本。
