# SeniorOfficialProfileAnalysisSystem

高级官员履历分析系统（SOPAS）用于集中维护公开人物履历、任职轨迹、信息来源、分析任务与人物关系。当前重构版本位于 `src_gpt5.6`，采用 FastAPI + Vue 3 + SQLite，界面视觉和交互参考 InformationSmartAnalysisSystem。

## 页面介绍

- 概览：履历、在任官员、机构、任职经历和关系统计。
- 履历档案：分页检索、新建、编辑、删除履历，按状态与党内职务（中央政治局常委/中央政治局委员/中央委员/中央候补委员，层级语义）筛选，查看人物概述与任职时间轴；支持一键「履历刷新」，后台增量抓取全部官员来源页面并用专用解析器（不调用 LLM）更新履历。
- 时间线：横向选择多位人物，载入完整履历后按“年”或“月”粒度纵向对齐展示任职轨迹。
- 关系图谱：选择任意两份履历进行智能关系分析，保存分析结果并以网络视图展示。
- 信息源管理：接入官方网站、本地文件夹和 FreshRSS，网页内容统一由 WebFetch 服务抓取。
- 智能分析：分析任务与分析结果合并页，绑定信息源执行全量/增量智能分析，并在同页按任务筛选查看逐条与汇总结果。
- 任务中心：查看后台任务状态与逐条日志，覆盖采集、分析与履历刷新任务。
- 权限管理：管理员为普通用户分配页面权限。
- 系统配置：查看脱敏后的运行配置与健康状态。

## 快速开始

```powershell
cd src_gpt5.6
./start.ps1
```

```bash
cd src_gpt5.6
chmod +x *.sh
./start.sh
```

默认访问地址为 `http://127.0.0.1:33380`，首次部署账号为 `admin / admin123`。首次启动前可从 `AGENTS.md` 的模板创建 `data/password.txt`；启动脚本也会在文件不存在时创建它。

## 配置

主配置为 `src_gpt5.6/config/app.json`。所有路径可使用相对路径，敏感值和环境差异可通过 `SOPAS_*` 环境变量或 `config/env.local` 覆盖。主要变量包括：

- `SOPAS_SERVER_HOST`、`SOPAS_SERVER_PORT`
- `SOPAS_DB_PATH`、`SOPAS_PASSWORD_FILE`
- `SOPAS_AUTH_SECRET_KEY`
- `SOPAS_WEB_FETCH_BASE_URL`、`SOPAS_WEB_FETCH_API_KEY`
- `SOPAS_LLM_BASE_URL`、`SOPAS_LLM_API_KEY`、`SOPAS_LLM_MODEL`

配置文件可按本次需求随代码更新；Jenkins 增量部署会保留服务器 `data`、`logs` 和 `config/env.local`。

## 开发与测试

```bash
cd src_gpt5.6
python -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.txt
.venv/bin/python -m pytest -q

cd app/frontend
npm ci
npm run build
```

## 部署与运维

Jenkins 流水线文件为 `src_gpt5.6/JenkinsConfig/Jenkinsfile`，包含检出、后端测试、前端构建、停止、增量部署、启动与健康检查。Linux systemd 模板为 `src_gpt5.6/JenkinsConfig/sopas.service`。

```bash
./start.sh
./status.sh
./stop.sh
curl http://127.0.0.1:33380/api/health
```

生产访问地址：`https://seniorprofile.yuan-xin.top`。

## 目录结构

```text
src_gpt5.6/
├── app/backend/        FastAPI API、模型、服务
├── app/frontend/       Vue 3 前端
├── config/app.json     主配置
├── data/               SQLite、密码文件和下载数据
├── docs/               需求与设计文档
├── JenkinsConfig/      Jenkinsfile、systemd 模板
├── logs/               运行日志（不入库）
├── tests/              单元与冒烟测试
├── start.ps1|start.sh
├── status.ps1|status.sh
└── stop.ps1|stop.sh
```

## 内置履历数据

系统内置中国共产党第二十届中央委员会委员（含递补 219 人）与候补委员（157 人）共 376 人的履历种子数据 `src_gpt5.6/data/seed/officials_20th_cc.json`（含逐段任职经历与委员/候补、递补、党和国家领导人、落马、已故、院士等标签，并按二十届政治局常委/委员公开名单标注 `party_role` 党内职务字段），并随附导入脚本 `src_gpt5.6/scripts/import_officials.py`（支持 `--dry-run` 预演、`--update` 覆盖、按姓名幂等跳过已有记录）。数据采集、解析与再生成脚本见 `scripts/ccdata/`。旧库升级时启动过程自动为 `officials` 表补 `party_role` 列，并对空值行按标签回填党内职务（识别中央委员、候补委员与政治局常委/委员标签），不覆盖已有值。

## 相关文档

- [需求规格说明书](SRS.md)
- [设计说明书](SDD.md)
- [项目约束](AGENTS.md)
