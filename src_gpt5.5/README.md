# 高级官员履历分析系统：FastAPI + Vue 简化版

本目录是当前推荐实现。系统不依赖 Kubernetes、PostgreSQL、Redis 或 Celery，适合个人和内部研究环境：FastAPI 提供 API、认证和静态文件服务，Vue 提供单页界面，SQLite 保存全部业务数据，生产环境仅运行一个 Uvicorn 进程。

## 实现方式

```text
浏览器
  -> FastAPI/Uvicorn :33380
     -> /api/*              后端 API
     -> /assets 和 /        Vue 构建产物
     -> data/sopa.db        SQLite 数据库
     -> data/raw-docs/      抓取正文
```

- `backend/app/modules/`：认证、中央委员会、官员履历、关系、分析和数据源模块。
- `frontend/src/App.vue`：Vue 3 单页界面；未引入路由、状态库或 UI 框架。
- `frontend/src/api.ts`：统一 API 客户端和 TypeScript 类型。
- `.env`：端口、数据库及运行路径的统一配置，不提交 Git。
- `data/`：数据库、原始正文、PID 和运行端口。
- `logs/`：运行日志。
- `JenkinsConfig/Jenkinsfile`：Linux Jenkins 自动部署流水线。

## 环境要求

- Python 3.11 或更高版本
- Node.js 20 或更高版本
- Windows PowerShell 5.1+，或常见 Linux 发行版
- Linux 额外需要 `curl`；Jenkins 部署需要 `git`、`rsync` 和 `openssl`

## 配置

首次安装时复制模板：

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
chmod 600 .env
```

至少修改以下配置：

```env
APP_HOST=0.0.0.0
APP_PORT=33380
DATABASE_URL=sqlite:///./data/sopa.db
DATA_DIR=./data
LOG_DIR=./logs
FRONTEND_DIST_DIR=./frontend/dist
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30
JWT_SECRET=足够长的随机字符串
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=首次管理员密码
```

相对路径以应用目录为基准，也可以配置为绝对路径。启动脚本的命令参数优先于环境变量，环境变量优先于 `.env`。管理员账号只在数据库中不存在时初始化；数据库已经生成后，再修改 `INITIAL_ADMIN_PASSWORD` 不会修改现有账号密码。

## Windows 安装与运行

在 `src_gpt5.5` 目录执行：

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Set-Location frontend
npm install
npm run build
Set-Location ..
```

启停和检查：

```powershell
.\start.ps1
.\status.ps1
.\stop.ps1
```

指定端口：

```powershell
.\start.ps1 -Port 8080
.\status.ps1
```

端口和所有运行路径均可覆盖：

```powershell
.\start.ps1 `
  -AppDir "D:\apps\sopa" `
  -Port 8080 `
  -DataDir "D:\sopa-data" `
  -LogDir "D:\sopa-logs" `
  -FrontendDistDir "D:\apps\sopa\frontend\dist"
```

若 PowerShell 禁止执行本地脚本，可仅对当前进程放开：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Windows 和 Linux 均由 Python 日志处理器写入 `LOG_DIR`，不依赖控制台重定向。

## Linux 安装与运行

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -e './backend[dev]'
cd frontend
npm install
npm run build
cd ..
chmod +x start.sh stop.sh status.sh
```

启停和检查：

```bash
./start.sh
./status.sh
./stop.sh
```

指定端口：

```bash
PORT=8080 ./start.sh
./status.sh
```

端口和路径也可以通过环境变量覆盖：

```bash
APP_DIR=/srv/sopa \
APP_PORT=8080 \
DATA_DIR=/var/lib/sopa \
LOG_DIR=/var/log/sopa \
FRONTEND_DIST_DIR=/srv/sopa/frontend/dist \
/srv/sopa/start.sh
```

## 访问地址

- 系统界面：`http://127.0.0.1:33380`
- 健康检查：`http://127.0.0.1:33380/api/health`
- API 文档：`http://127.0.0.1:33380/api/docs`

开发环境默认管理员是 `admin / admin123`。正式部署必须在首次启动前修改 `.env`。

## 开发模式

后端热更新：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

前端热更新需另开终端：

```powershell
Set-Location frontend
npm run dev
```

Vite 在 `http://127.0.0.1:5173` 启动，并将 `/api` 代理到 FastAPI 的 `33380` 端口。

## 手工部署

1. 将仓库同步到服务器，例如 `/opt/SeniorOfficialProfileAnalysisSystem`。
2. 进入 `src_gpt5.5`，创建并保护 `.env`。
3. 创建 `.venv`，安装后端依赖。
4. 在 `frontend` 中执行 `npm install` 和 `npm run build`。
5. 执行 `./start.sh`，再执行 `./status.sh`。
6. 如需局域网访问，开放所选端口；公网环境应在前方配置 HTTPS 反向代理和访问限制。

发布新版本时按以下顺序操作：停止服务、更新代码、重新安装依赖、重新构建前端、启动并检查健康状态。`data/`、`logs/` 和 `.env` 不应被发布过程覆盖。

## Jenkins 部署

流水线文件为 `JenkinsConfig/Jenkinsfile`，Jenkins 任务的 Script Path 设置为：

```text
src_gpt5.5/JenkinsConfig/Jenkinsfile
```

流水线参数均可在 Jenkins 任务或单次构建中修改：

| 参数 | 用途 |
| --- | --- |
| `SOURCE_DIR` | 工作区中的源码目录。 |
| `DEPLOY_DIR` | 服务器绝对部署目录。 |
| `APP_HOST` | HTTP 监听地址。 |
| `APP_PORT` | HTTP 监听端口。 |
| `DATA_DIR` | 数据、PID 和初始密码目录。 |
| `LOG_DIR` | 应用日志目录。 |
| `FRONTEND_DIST_DIR` | Vue 构建产物目录。 |
| `DATABASE_URL` | SQLAlchemy 数据库地址。 |
| `LOG_RETENTION_DAYS` | 日志保留天数。 |

流水线会：

1. 从 SCM 检出代码。
2. 停止旧服务。
3. 使用 `rsync` 更新代码，同时保留 `.env`、`.venv`、`data/` 和 `logs/`。
4. 安装 Python 依赖并执行 `npm ci && npm run build`。
5. 启动服务并检查健康接口和首页。

首次 Jenkins 部署会生成随机 JWT Secret 和管理员密码。初始管理员密码保存在配置的 `DATA_DIR/initial-admin-password.txt`。

默认参数下对应路径为：

```text
/opt/SeniorOfficialProfileAnalysisSystem/src_gpt5.5/data/initial-admin-password.txt
```

## 运维

### 状态与日志

应用日志按自然日午夜轮转，并保留 `LOG_RETENTION_DAYS` 天。当前日志和轮转日志均以 `.log` 结尾：

```text
app.log
app.2026-06-21.log
access.log
access.2026-06-21.log
```

`app.log` 保存应用和错误日志，`access.log` 保存 HTTP 访问日志。

Windows：

```powershell
.\status.ps1
Get-Content .\logs\app.log -Tail 100
Get-Content .\logs\access.log -Tail 100
```

Linux：

```bash
./status.sh
tail -n 100 logs/app.log
tail -n 100 logs/access.log
```

脚本使用 `data/app.pid` 记录进程号、`data/app.port` 记录端口。不要手工复用这些文件中的旧进程号。

### 备份与恢复

SQLite 单机版建议停止服务后备份：

```powershell
.\stop.ps1
New-Item -ItemType Directory backups -Force
Copy-Item data\sopa.db ("backups\sopa-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".db")
.\start.ps1
```

```bash
./stop.sh
mkdir -p backups
cp data/sopa.db "backups/sopa-$(date +%Y%m%d-%H%M%S).db"
./start.sh
```

恢复时先停止服务，将备份文件复制为 `data/sopa.db`，再重新启动。抓取证据需要同时备份 `data/raw-docs/`。

### 常见问题

- `Python environment not found`：先创建 `.venv` 并安装后端依赖。
- `Vue build not found`：进入 `frontend` 执行 `npm install && npm run build`。
- 健康检查失败：检查端口占用、`.env` 格式以及 `LOG_DIR/app.log`。
- 修改 `.env` 后未生效：执行停止和启动，不要只刷新浏览器。
- 修改初始密码后仍无法登录：已有密码保存在数据库哈希中，初始密码变量不会覆盖已有用户。
- 端口被占用：使用 `start.ps1 -Port 8080` 或 `PORT=8080 ./start.sh`。

## 安全注意

- 不提交 `.env`、数据库、日志、原始抓取数据或 API Key。
- 正式部署使用随机 `JWT_SECRET` 和强管理员密码。
- 当前实现面向个人内部研究；公网开放前应增加 HTTPS、反向代理、访问控制、备份和审计策略。
