# 高级官员履历分析系统设计说明书

版本：2.0（`src_gpt5.6`）
更新日期：2026-07-16

## 1. 总体架构

系统采用单机优先的模块化单体架构。FastAPI 同时提供 REST API 和构建后的 Vue SPA；SQLite 保存业务数据；线程池执行同步与分析任务；WebFetch 和 OpenAI 兼容接口作为可配置外部依赖。

```text
Browser → Vue 3 SPA → FastAPI API → SQLAlchemy → SQLite
                         ├→ background worker → WebFetch
                         └→ background worker → LLM API
```

选择 SQLite 的理由是当前部署为单节点个人应用，写并发有限，SQLite 可降低部署和运维成本，不需要额外数据库服务。

## 2. 后端设计

- `core/config.py`：读取 `config/app.json`，接受 `SOPAS_*` 环境变量覆盖。
- `core/security.py`：密码文件同步、哈希校验、JWT 签发与页面权限计算。
- `core/database.py`：SQLAlchemy 会话、建表、SQLite 外键启用。
- `api/officials.py`：履历 CRUD、统计、机构、批量时间线和人物关系 API。
- `api/info_sources.py`：信息源与采集条目 API。
- `api/analysis_tasks.py`：分析任务、运行和结果 API。
- `api/task_center.py`：统一任务和日志查询。
- `services/worker.py`：进程内有界线程池。

API 以 `/api` 为前缀，认证使用 Bearer Token。页面级接口通过 `require_page` 校验；管理员接口通过 `require_admin` 校验。

时间线使用 `POST /api/officials/timeline` 批量加载人物及任职经历，去重后保持选择顺序。前端将常见年月格式归一为月份序号；月模式直接使用月份序号，年模式映射为年份，并在点击更新后以相应粒度重新生成纵向网格和人物任职区间。

## 3. 数据设计

核心表：

- `users`、`page_permissions`：用户与页面授权。
- `officials`：人物基本履历。
- `careers`：人物一对多任职经历，人物删除时级联删除。
- `official_relations`：人物间有向关系，人物对、关系类型唯一。
- `info_sources`、`info_items`：信息源和采集内容。
- `analysis_tasks`、`task_sources`、`analysis_results`：分析定义、来源绑定和结果。
- `task_runs`、`task_logs`：后台运行审计。
- 内置种子数据：`data/seed/officials_20th_cc.json` 存放二十届中央委员/候补委员履历（与 `OfficialCreate` 结构一致），由 `scripts/import_officials.py` 按姓名幂等导入；采集与解析脚本（维基名单/条目抓取、简历抽取、种子生成）保留在仓库根 `scripts/ccdata/` 以便追溯与再生成。

数据时间保存为 UTC naive datetime，Pydantic 输出时转换为 `Asia/Shanghai`。SQLite 连接打开 `PRAGMA foreign_keys=ON`。

## 4. 前端设计

前端采用 Vue 3、TypeScript、Pinia、Vue Router、Axios。视觉继承参考系统的深蓝侧栏、白色工作区、低饱和蓝色强调、卡片和药丸状态标签，并扩展：

- 人物履历双列卡片与详情时间轴。
- 关系图谱环形网络视图与关系清单。
- 统计卡、最近更新履历和暗色数据洞察卡。
- 900px 和 700px 两级响应式布局。

路由元数据保存页面权限键；全局守卫负责认证和无权路由重定向。Axios 拦截器注入 Token、处理 401 并统一展示错误。

## 5. 配置与安全

`config/app.json` 保存可交付默认配置，真实密钥优先放在不入库的 `config/env.local` 或 Jenkins 凭据中。系统配置 API 通过递归敏感字段识别进行脱敏。密码文件仅在登录同步时读取，数据库保存哈希。

WebFetch 客户端只调用配置的集中抓取服务；API Key 通过请求头传递，不写入日志。CORS 当前允许同源部署兼容的全来源访问，若拆分部署应在配置层收紧来源。

## 6. 运行与部署

启动脚本读取配置端口、创建 `.venv`、安装后端依赖、构建前端、创建数据和日志目录并启动 Uvicorn。状态脚本同时校验 PID 和健康接口。systemd 模板调用 `run.sh` 前台运行。

Jenkins 流程：检出主分支 → 后端测试 → 前端构建 → 停止旧服务 → rsync `src_gpt5.6` → 首次创建密码文件 → 启动 → 状态与健康检查。增量部署排除 `data`、`logs`、虚拟环境、缓存、`node_modules` 和 `config/env.local`。

## 7. 测试设计

- 单元测试：配置、安全、时间、适配器、分析引擎、信息源、履历 CRUD、人物关系。
- 冒烟测试：登录、信息源、分析任务、运行结果和健康接口。
- 前端：`vue-tsc --noEmit` 与 Vite production build。
- 部署：脚本状态检查和 Jenkins 健康检查。

测试使用临时 SQLite、临时密码文件和 mock 外部服务，不访问生产数据。
