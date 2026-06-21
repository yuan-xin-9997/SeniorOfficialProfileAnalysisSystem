# Repository Guidelines

中文标题：仓库贡献指南

## Project Structure & Module Organization

This repository contains a senior official profile analysis system.

本仓库是一个高级官员履历采集、存储、分析和展示系统。

- `backend/`: FastAPI application, SQLAlchemy models, Celery workers, and backend tests.
  `backend/`：FastAPI 后端、SQLAlchemy 数据模型、Celery worker 和后端测试。
- `backend/app/modules/`: feature modules such as `auth`, `officials`, `sources`, `relationships`, and `analysis`.
  `backend/app/modules/`：按业务模块组织代码，包括认证、官员、数据源、关系和分析。
- `frontend/`: React + Vite UI. Pages live in `frontend/src/pages`, shared API code in `frontend/src/api`, and global styles in `frontend/src/styles`.
  `frontend/`：React + Vite 前端；页面在 `frontend/src/pages`，API 客户端在 `frontend/src/api`，全局样式在 `frontend/src/styles`。
- `deploy/`: Docker Compose and Kubernetes/minikube manifests.
  `deploy/`：Docker Compose 与 Kubernetes/minikube 部署清单。
- `scripts/`: deployment and smoke-test helpers.
  `scripts/`：部署脚本和 smoke test 辅助脚本。
- `软件需求规格说明书.md` and `系统设计说明书.md`: product and system design references.
  这两个文档是需求和系统设计参考。

## Build, Test, and Development Commands

- `docker compose -f deploy/docker-compose.yml --env-file .env up --build`: run the full local stack.
  启动完整本地环境。
- `cd backend; pip install -e ".[dev]"`: install backend development dependencies.
  安装后端开发依赖。
- `cd backend; uvicorn app.main:app --reload`: run the API locally.
  本地启动后端 API。
- `cd backend; pytest`: run backend tests.
  运行后端测试。
- `python -m compileall backend\app`: quick Python syntax check from the repo root.
  从仓库根目录快速检查 Python 语法。
- `cd frontend; npm install`: install frontend dependencies.
  安装前端依赖。
- `cd frontend; npm run dev`: start the Vite dev server.
  启动 Vite 开发服务器。
- `cd frontend; npm run build`: run TypeScript checks and produce a production build.
  执行 TypeScript 检查并生成生产构建。
- `kubectl apply -f deploy/k8s/`: apply minikube manifests.
  应用 minikube 部署清单。

## Coding Style & Naming Conventions

Use 4-space indentation for Python and keep FastAPI routes, schemas, and services grouped by module. Prefer typed functions and Pydantic models for API boundaries. Use `snake_case` for Python files, functions, and variables.

Python 使用 4 空格缩进。FastAPI 路由、schema 和服务逻辑应按模块归档。API 边界优先使用类型标注和 Pydantic 模型。Python 文件、函数和变量使用 `snake_case`。

Use TypeScript functional React components. Name pages and components in `PascalCase` such as `SourcesPage.tsx`; use `camelCase` for variables and API client methods.

前端使用 TypeScript 函数组件。页面和组件使用 `PascalCase`，例如 `SourcesPage.tsx`；变量和 API 方法使用 `camelCase`。

## Testing Guidelines

Backend tests use `pytest` under `backend/tests`. Name test files `test_*.py` and keep tests focused on observable behavior. For deployment checks, use smoke scripts such as `scripts/smoke_minikube.py`, `scripts/smoke_crawl_minikube.py`, and `scripts/smoke_parse_minikube.py`.

后端测试使用 `pytest`，放在 `backend/tests`。测试文件命名为 `test_*.py`，测试重点应放在可观察行为。部署验证使用 `scripts/smoke_minikube.py`、`scripts/smoke_crawl_minikube.py` 和 `scripts/smoke_parse_minikube.py`。

## Commit & Pull Request Guidelines

The current Git history uses short Chinese summaries and has no strict convention yet. Prefer concise, imperative messages, for example: `实现履历解析接口` or `Fix crawler encoding detection`.

当前 Git 历史主要使用简短中文摘要，还没有严格提交规范。建议使用简洁、祈使式提交信息，例如 `实现履历解析接口` 或 `Fix crawler encoding detection`。

Pull requests should include a short purpose statement, key changes, verification commands, and screenshots for UI changes. Link related issues or design notes when available.

Pull Request 应包含目的说明、关键改动、验证命令；涉及 UI 时应附截图。如有关联 issue 或设计说明，也应一并链接。

## Security & Configuration Tips

Never commit `.env`, `env.md`, real passwords, JWT secrets, API keys, or downloaded raw data. Start from `.env.example`, rotate generated credentials for real deployments, and keep this system on internal networks unless access control and audit requirements are reviewed.

不要提交 `.env`、`env.md`、真实密码、JWT Secret、API Key 或下载的原始数据。配置应从 `.env.example` 复制生成；正式部署时必须替换默认密钥。除非已审查访问控制和审计要求，否则系统应仅部署在内部网络。
