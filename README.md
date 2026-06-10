# SeniorOfficialProfileAnalysisSystem (SOPAS)

基于 AI 的高级官员履历分析系统 — 采集、存储、分析与可视化展示高级官员公开履历及关系网络。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + Neo4j + Celery + Redis
- **前端**: Vue 3 + TypeScript + Element Plus + ECharts
- **部署**: Docker Compose / Kubernetes (Minikube)

## 快速开始（本地）

```bash
# 启动全部服务
docker compose up -d --build

# 访问
# 前端: http://localhost
# API 文档: http://localhost:8000/docs
# 默认账号: admin / admin123
```

## 开发模式

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 部署到 Linux 服务器

服务器信息见 [env.md](./env.md)。在项目根目录执行：

```bash
# Docker Compose 部署（推荐首次使用）
bash scripts/deploy.sh compose

# Minikube K8S 部署
bash scripts/deploy.sh k8s
```

部署完成后访问 `http://192.168.0.111`（Compose）或 `http://<minikube-ip>:30080`（K8S）。

## 项目结构

```
backend/     FastAPI 后端
frontend/    Vue 3 前端
scraper/     爬虫扩展（独立模块）
k8s/         Kubernetes 清单
scripts/     部署脚本
SRS.md       需求规格说明书
SDD.md       系统设计说明书
```

## 文档

- [SRS.md](./SRS.md) — 软件需求规格说明书
- [SDD.md](./SDD.md) — 系统设计说明书
