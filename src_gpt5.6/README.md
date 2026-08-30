# 高级官员履历分析系统（SOPAS）

本目录是 `src_gpt5.6` 可部署版本，采用 FastAPI + Vue 3 + SQLite。功能包括履历档案、任职时间轴、人物关系图谱、信息源、智能分析、任务中心、登录、页面权限和系统配置。

## 配置

主配置文件为 `config/app.json`，默认端口 `33380`。环境差异和敏感值可用 `SOPAS_*` 环境变量或 `config/env.local` 覆盖。常用变量：

```text
SOPAS_SERVER_HOST / SOPAS_SERVER_PORT
SOPAS_DB_PATH / SOPAS_PASSWORD_FILE
SOPAS_AUTH_SECRET_KEY
SOPAS_WEB_FETCH_BASE_URL / SOPAS_WEB_FETCH_API_KEY
SOPAS_LLM_BASE_URL / SOPAS_LLM_API_KEY / SOPAS_LLM_MODEL
```

## 首次启动

Windows：

```powershell
./start.ps1
./status.ps1
./stop.ps1
```

Linux：

```bash
chmod +x *.sh
./start.sh
./status.sh
./stop.sh
```

访问 `http://127.0.0.1:33380`，默认账号 `admin / admin123`。首次启动会创建 `data`、`logs` 和缺失的 `data/password.txt`。

## 开发

```bash
python -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.txt
.venv/bin/python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 33380
```

```bash
cd app/frontend
npm ci
npm run dev
npm run build
```

## 测试

```bash
python -m pytest -q
cd app/frontend && npm run build
```

测试使用临时数据库、临时密码文件和 mock 外部服务，不会写入生产数据。

## 页面

- 概览：核心统计、最近履历、数据完整度。
- 履历档案：人物分页检索、按状态（在任/离任/退休/落马/已故）与党内职务（中央政治局常委/中央政治局委员/中央委员/中央候补委员，层级语义）筛选、编辑、详情与任职时间轴。
- 时间线：横向选择最多 8 位人物，按“年”或“月”粒度纵向对齐比较任职履历。
- 关系图谱：选择任意两份履历进行智能关系分析、展示履历依据、保存结果与网络展示。
- 信息源管理：官方网站、本地文件夹、FreshRSS。
- 智能分析：分析任务与分析结果合并页，绑定信息源执行全量/增量智能分析并查看逐条与汇总结果。原「分析任务」「分析结果」权限键在启动时自动合并为 `analysis`，旧路由自动重定向。
- 任务中心：任务状态、摘要、错误和日志。
- 权限管理：管理员配置普通用户页面访问范围。
- 系统配置：脱敏显示运行配置。

## 内置履历数据与导入

系统内置中共二十届中央委员（含递补）与中央候补委员共 376 人的种子数据 `data/seed/officials_20th_cc.json`，并按二十届政治局常委/委员公开名单标注 `party_role` 党内职务字段（常委 7 人、政治局委员 17 人、中央委员 195 人、候补委员 157 人）。向运行中的实例导入（默认跳过同名已有履历）：

```bash
python scripts/import_officials.py --base-url http://127.0.0.1:33380 --username admin --password admin123
```

支持 `--dry-run` 预演与 `--update` 覆盖同名记录。数据溯源与再生成脚本见仓库根 `scripts/ccdata/`。旧库升级时启动过程自动为 `officials` 表补 `party_role` 列，并对空值行按标签回填党内职务；注意 `--update` 会用种子数据整体覆盖同名记录，含手工修改的实例请先备份。

## Jenkins 与 systemd

- Jenkins 脚本路径：`src_gpt5.6/JenkinsConfig/Jenkinsfile`
- systemd 模板：`JenkinsConfig/sopas.service`
- 部署目录：`/opt/SeniorOfficialProfileAnalysisSystem`

流水线执行后端测试和前端构建后再部署，并保留服务器的 `data`、`logs` 和 `config/env.local`。

## 文档

- `docs/需求规格说明书.md`
- `docs/设计说明书.md`
- 仓库根目录 `AGENTS.md`
