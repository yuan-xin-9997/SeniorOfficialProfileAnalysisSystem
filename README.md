# 中国高级官员履历分析系统

这是一个面向个人内部研究的高级官员公开履历采集、存储、分析和展示系统。一期范围从最近一届中国共产党中央委员会委员、候补委员开始。

当前代码已经包含：

1. FastAPI 后端骨架。
2. PostgreSQL 数据模型。
3. 默认管理员初始化。
4. 默认关系权重模板。
5. 官员、数据源、关系、分析任务基础 API。
6. React 前端基础界面。
7. Docker Compose 和 minikube/Kubernetes 初始部署清单。

## 快速启动

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

请先修改 `.env` 里的密码和 `JWT_SECRET`，不要使用模板里的默认值部署长期环境。

使用 Docker Compose 启动：

```powershell
docker compose -f deploy/docker-compose.yml --env-file .env up --build
```

访问：

```text
前端: http://localhost:8080
后端文档: http://localhost:8000/api/docs
```

默认管理员由环境变量 `INITIAL_ADMIN_USERNAME` 和 `INITIAL_ADMIN_PASSWORD` 初始化。首次登录后应尽快修改。

## 本地开发

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

## 部署到 minikube

先构建镜像并加载到 minikube：

```powershell
docker build -t sopa-backend:0.1.0 .\backend
docker build -t sopa-frontend:0.1.0 .\frontend
minikube image load sopa-backend:0.1.0
minikube image load sopa-frontend:0.1.0
```

部署：

```powershell
kubectl apply -f deploy/k8s/
```

查看服务：

```powershell
kubectl get pods,svc -n sopa
```

## 安全注意

1. 不要把 `env.md`、`.env` 或真实服务器密码提交到公开仓库。
2. 不要把 LLM API Key、数据库密码、JWT Secret 写入代码。
3. 当前系统按个人内部研究场景设计，默认不建议公网暴露。
4. 抓取模块后续接入真实网站时，需要遵守目标网站访问规则和频率限制。

## 下一阶段开发建议

1. 实现中央委员/候补委员名单导入脚本。
2. 实现真实网页抓取和页面快照保存。
3. 接入规则解析和 LLM JSON 解析。
4. 完成审核队列页面。
5. 从履历事件自动生成关系边。
6. 将关系图谱列表替换为可交互图画布。

