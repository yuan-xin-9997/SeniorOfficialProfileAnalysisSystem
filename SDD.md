# 高级官员履历分析系统 系统设计说明书

**文档版本：** v1.0  
**编写日期：** 2026-06-09  
**项目名称：** SeniorOfficialProfileAnalysisSystem (SOPAS)  
**对应需求文档：** SRS.md v1.0

---

## 目录

1. [引言](#1-引言)
2. [系统总体设计](#2-系统总体设计)
3. [模块详细设计](#3-模块详细设计)
4. [数据库设计](#4-数据库设计)
5. [接口设计](#5-接口设计)
6. [核心算法设计](#6-核心算法设计)
7. [前端设计](#7-前端设计)
8. [安全设计](#8-安全设计)
9. [性能与可靠性设计](#9-性能与可靠性设计)
10. [部署设计](#10-部署设计)
11. [运维与监控设计](#11-运维与监控设计)
12. [附录](#12-附录)

---

## 1. 引言

### 1.1 编写目的

本文档为"高级官员履历分析系统"（SOPAS）的系统设计说明书（SDD），在 [SRS.md](./SRS.md) 需求规格的基础上，给出系统架构、模块划分、数据模型、接口协议、核心算法及部署方案的具体设计，作为开发、测试与运维的实现依据。

### 1.2 设计范围

本设计覆盖 SRS 中定义的四大核心模块：

| 模块 | 职责 |
|------|------|
| 数据抓取模块（Scraper） | 从政府公开网站采集并解析官员履历 |
| 数据存储模块（Storage） | 关系型 + 图数据库双存储，版本管理与导入导出 |
| 数据分析模块（Analysis） | 同盟关系识别、关系强度计算、派系聚类等 |
| 数据展示模块（Display） | Web 可视化界面，关系网络图、时间线、地图等 |

同时涵盖认证授权、任务调度、监控告警等横切能力。

### 1.3 术语与缩写

| 术语/缩写 | 说明 |
|-----------|------|
| SOPAS | SeniorOfficialProfileAnalysisSystem，本系统 |
| RBAC | Role-Based Access Control，基于角色的访问控制 |
| JWT | JSON Web Token，无状态认证令牌 |
| HPA | Horizontal Pod Autoscaler，K8S 水平自动扩展 |
| ER | Entity-Relationship，实体关系 |

### 1.4 参考文档

- SRS.md v1.0 — 软件需求规格说明书
- IEEE 1016-2009 软件设计描述标准

### 1.5 设计原则

1. **分层解耦**：表现层、业务层、数据访问层、基础设施层清晰分离
2. **双库协同**：PostgreSQL 承载结构化事务数据，Neo4j 承载关系图谱与路径查询
3. **异步优先**：抓取、分析等耗时操作通过 Celery 异步执行，API 快速响应
4. **可扩展**：爬虫、分析算法采用插件/策略模式，便于新增数据源与算法
5. **配置外置**：环境差异通过环境变量与 ConfigMap 注入，代码与配置分离

---

## 2. 系统总体设计

### 2.1 逻辑架构

系统采用前后端分离的 B/S 架构，后端以 FastAPI 为统一 API 网关，前端为 Vue 3 SPA。

```
┌─────────────────────────────────────────────────────────────────────┐
│                           表现层 (Presentation)                      │
│  Vue 3 SPA │ 关系网络图 │ 履历时间线 │ 地理分布图 │ 管理后台          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / REST / JSON
┌───────────────────────────────▼─────────────────────────────────────┐
│                           应用层 (Application)                       │
│  Auth │ Officials │ Scraper │ Analysis │ Export │ User Management    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                           领域层 (Domain)                            │
│  OfficialService │ RelationshipEngine │ ScraperOrchestrator          │
│  ClusteringService │ VersionManager │ DataQualityValidator           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                         基础设施层 (Infrastructure)                   │
│  PostgreSQL │ Neo4j │ Redis │ Celery │ Scrapy/Playwright │ MinIO     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 物理部署架构

```
                    ┌──────────────┐
                    │    Nginx     │  ← TLS 终结、静态资源、反向代理
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌──────▼──────┐  ┌─────▼─────┐
    │ Frontend  │   │  Backend    │  │  Backend  │  ← HPA 2+ 副本
    │ (Vue SPA) │   │  (FastAPI)  │  │  (FastAPI)  │
    └───────────┘   └──────┬──────┘  └─────┬─────┘
                           │                │
              ┌────────────┼────────────────┼────────────┐
              │            │                │            │
        ┌─────▼─────┐ ┌────▼────┐    ┌──────▼──────┐ ┌───▼───┐
        │ PostgreSQL│ │  Neo4j  │    │    Redis    │ │Celery │
        │(StatefulSet)│(StatefulSet)│  (Deployment)│ │Worker │
        └───────────┘ └─────────┘    └──────┬──────┘ └───┬───┘
                                             │            │
                                      ┌──────▼────────────▼──┐
                                      │   Scraper Workers    │
                                      │ Scrapy / Playwright  │
                                      └──────────────────────┘
```

### 2.3 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| 后端框架 | FastAPI | 原生 async、自动 OpenAPI 文档、Pydantic 校验 |
| ORM | SQLAlchemy 2.0 + Alembic | 成熟的关系型 ORM 与迁移工具 |
| 图数据库驱动 | neo4j-python-driver | Neo4j 官方驱动，支持 Cypher |
| 前端框架 | Vue 3 + TypeScript + Pinia | 组件化、类型安全、轻量状态管理 |
| UI 组件库 | Element Plus | 管理后台表格、表单、权限菜单 |
| 可视化 | ECharts + D3.js | ECharts 负责统计图与地图，D3 负责力导向关系图 |
| 任务队列 | Celery + Redis | 成熟 Python 异步任务方案 |
| 爬虫 | Scrapy + Playwright | 静态页 Scrapy 高效，动态页 Playwright 渲染 |
| 容器编排 | Docker + Kubernetes | 需求指定，支持水平扩展 |
| 监控 | Prometheus + Grafana | 指标采集与可视化告警 |

### 2.4 项目目录结构

```
SOPAS/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # REST 路由（auth, officials, scraper, analysis, export）
│   │   ├── core/                # 配置、安全、数据库连接池
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── schemas/             # Pydantic 请求/响应模式
│   │   ├── services/            # 业务逻辑
│   │   │   ├── scraper/         # 抓取编排、解析、增量比对
│   │   │   ├── analysis/        # 关系引擎、聚类、相似度
│   │   │   └── storage/         # 双库同步、版本管理、导入导出
│   │   ├── repositories/        # 数据访问层（PG + Neo4j）
│   │   ├── tasks/               # Celery 任务定义
│   │   └── utils/               # 通用工具
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/               # 页面：Dashboard, OfficialDetail, NetworkGraph 等
│   │   ├── components/          # 可复用组件：Timeline, ForceGraph, ChinaMap
│   │   ├── stores/              # Pinia 状态
│   │   ├── api/                 # Axios 封装
│   │   └── router/              # 路由与权限守卫
│   ├── package.json
│   └── Dockerfile
├── scraper/
│   ├── spiders/                 # 各数据源 Spider（people, xinhua, gov）
│   ├── parsers/                 # HTML → 结构化 DTO
│   ├── pipelines/               # 清洗、校验、推送 Backend API
│   └── middlewares/             # 限速、UA 轮换、代理
├── k8s/                         # K8S 清单
├── docker-compose.yml
└── docs/
```

---

## 3. 模块详细设计

### 3.1 数据抓取模块（Scraper）

#### 3.1.1 模块职责

- 维护目标官员名单与数据源配置
- 定时/手动触发抓取任务
- 解析 HTML 为标准化 DTO
- 增量比对并写入存储层
- 记录抓取日志，失败重试与告警

#### 3.1.2 类图（核心组件）

```
┌─────────────────────┐
│  ScraperOrchestrator │  ← 任务编排入口
├─────────────────────┤
│ + run_task(task_id) │
│ + schedule_task()   │
└──────────┬──────────┘
           │ uses
┌──────────▼──────────┐     ┌─────────────────┐
│   SpiderRegistry    │────▶│  BaseSpider      │ (abstract)
├─────────────────────┤     ├─────────────────┤
│ + get_spider(source)│     │ + fetch(url)    │
└─────────────────────┘     │ + parse(html)   │
                            └────────┬────────┘
                                     │ implements
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼──────┐ ┌───────▼──────┐ ┌───────▼──────┐
            │ PeopleSpider │ │ XinhuaSpider │ │  GovSpider   │
            └──────────────┘ └──────────────┘ └──────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│   DataNormalizer    │────▶│  IncrementalComparer │
├─────────────────────┤     ├─────────────────────┤
│ + normalize(raw)    │     │ + diff(existing,new)│
└─────────────────────┘     └─────────────────────┘
```

#### 3.1.3 抓取流程时序

```
Admin/API          Celery Worker       Spider           Backend Storage
    │                   │                │                    │
    │ POST /tasks/run   │                │                    │
    │──────────────────▶│                │                    │
    │                   │ load officials │                    │
    │                   │───────────────▶│                    │
    │                   │                │ fetch + parse      │
    │                   │                │──────┐             │
    │                   │                │◀─────┘             │
    │                   │ normalize+diff │                    │
    │                   │───────────────────────────────────▶│
    │                   │                │         upsert     │
    │                   │ write log      │                    │
    │                   │───────────────────────────────────▶│
    │◀──────────────────│ task result    │                    │
```

#### 3.1.4 增量更新策略

1. 对每个官员计算 `content_hash = SHA256(normalized_json)`
2. 与 PostgreSQL `official_snapshots` 表中最新 hash 比对
3. hash 不变则跳过；变化则写入新版本并触发关系重算 Celery 任务
4. 字段级 diff 记录至 `data_change_logs` 供审计回溯

#### 3.1.5 反爬与容错

| 策略 | 实现 |
|------|------|
| 请求限速 | Scrapy `DOWNLOAD_DELAY` + 令牌桶，默认 2 req/s/域名 |
| UA 轮换 | 预置 User-Agent 池，Middleware 随机选取 |
| 代理池 | 可选配置 `PROXY_LIST`，失败自动切换 |
| 重试 | 最多 3 次指数退避；超限写入失败日志并通知管理员 |
| 健康检查 | 定时 HEAD 请求各数据源，不可用时标记 `source.status=DOWN` |

#### 3.1.6 数据源适配器接口

```python
class BaseSpider(ABC):
    source_id: str

    @abstractmethod
    async def fetch(self, url: str) -> str: ...

    @abstractmethod
    def parse(self, html: str) -> OfficialDTO: ...

    @abstractmethod
    def get_official_urls(self, official: TargetOfficial) -> list[str]: ...
```

新增数据源只需：实现 `BaseSpider` → 注册至 `SpiderRegistry` → 在 `scraper_sources` 表添加配置。

---

### 3.2 数据存储模块（Storage）

#### 3.2.1 双库分工

| 存储 | 承载数据 | 访问模式 |
|------|----------|----------|
| PostgreSQL | 官员详情、履历、用户、任务、日志、版本快照 | CRUD、分页筛选、事务 |
| Neo4j | 官员节点、关系边、路径查询、聚类 | 图遍历、最短路径、社区发现 |

#### 3.2.2 双库同步机制

写入官员或关系数据时，由 `StorageService` 在同一业务事务中协调：

1. **写 PG**：Official / CareerEntry / Education / PoliticalCareer（主数据源）
2. **写 Neo4j**：MERGE Official 节点；MERGE 关系边（含 strength 等属性）
3. **失败补偿**：Neo4j 写入失败时，将事件写入 Redis 重试队列 `sync:neo4j:retry`，Worker 异步补偿；PG 事务不回滚（PG 为权威源）

```
StorageService.upsert_official(dto)
    │
    ├─▶ PostgreSQL UPSERT (transaction)
    │
    └─▶ Neo4j MERGE (async via Celery or sync with retry queue)
            │
            └─ on failure ─▶ Redis retry queue ─▶ SyncWorker
```

#### 3.2.3 版本管理

- 每次官员数据变更创建 `official_version` 记录（version_no 递增）
- 存储完整 JSON 快照 + diff 摘要
- 提供 `GET /officials/{id}/versions` 与 `POST /officials/{id}/rollback/{version}`

#### 3.2.4 数据质量校验

入库前 `DataQualityValidator` 执行：

| 规则 | 说明 |
|------|------|
| 必填字段 | name, birth_date, committee_term 等 |
| 时间一致性 | start_year ≤ end_year；履历无重叠冲突（同学历类型告警） |
| 引用完整性 | secretary_id / colleagues 须指向已存在官员 |
| 完整度评分 | 计算 completeness_score (0-1)，低于 0.5 标记 `quality_flag=LOW` |

---

### 3.3 数据分析模块（Analysis）

#### 3.3.1 模块职责

- 基于履历数据计算官员间关系强度
- 维护 Neo4j 关系边权重
- 提供路径查询、关联网络、派系聚类、相似度分析
- 生成统计聚合数据供前端图表使用

#### 3.3.2 分析流水线

```
[官员数据变更事件]
        │
        ▼
[RelationshipEngine.compute_pairs(official_id)]
        │
        ├─▶ 提取维度特征（部门、地区、上下级、校友、同乡）
        ├─▶ 计算 Strength 分数
        ├─▶ 写入/更新 Neo4j 边
        └─▶ 缓存热点结果至 Redis (TTL 1h)

[用户查询]
        │
        ├─▶ 优先读 Redis 缓存
        └─▶ 缓存 miss → Neo4j Cypher 查询 → 回填缓存
```

#### 3.3.3 分析服务组件

| 组件 | 职责 |
|------|------|
| `RelationshipEngine` | 同盟关系识别与强度计算 |
| `PathFinder` | 两节点间最短/全路径（深度限制） |
| `ClusteringService` | Louvain 社区发现算法派系聚类 |
| `SimilarityService` | 履历向量余弦相似度 |
| `StatisticsAggregator` | 年龄/学历/地域/届次统计 |

#### 3.3.4 插件化扩展

分析算法通过注册表扩展：

```python
class AnalysisPlugin(ABC):
    name: str
    @abstractmethod
    def run(self, context: AnalysisContext) -> AnalysisResult: ...

class PluginRegistry:
    def register(self, plugin: AnalysisPlugin): ...
    def get(self, name: str) -> AnalysisPlugin: ...
```

---

### 3.4 数据展示模块（Display）

#### 3.4.1 页面结构

| 路由 | 页面 | 主要组件 |
|------|------|----------|
| `/login` | 登录 | LoginForm |
| `/dashboard` | 系统概览 | StatCards, QuickSearch |
| `/officials` | 官员列表 | SearchFilter, OfficialTable |
| `/officials/:id` | 官员详情 | ProfileCard, CareerTimeline, ConnectionList |
| `/network` | 关系网络 | ForceGraph (D3), SidePanel |
| `/map` | 地理分布 | ChinaMap (ECharts) |
| `/compare` | 关系对比 | DualTimeline, RelationshipSummary |
| `/admin/scraper` | 抓取管理 | TaskList, LogViewer, SourceConfig |
| `/admin/users` | 用户管理 | UserTable (管理员) |

#### 3.4.2 前后端交互

- Axios 实例统一注入 JWT，`401` 跳转登录
- 关系网络图：首次加载子图（depth=1），点击节点懒加载邻居
- 复杂分析（聚类）：POST 触发后端异步任务，前端轮询 `/analysis/tasks/{id}` 获取结果

---

## 4. 数据库设计

### 4.1 PostgreSQL 逻辑模型

#### 4.1.1 核心表

**users — 用户表**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| username | VARCHAR(64) | UNIQUE, NOT NULL | |
| password_hash | VARCHAR(256) | NOT NULL | bcrypt |
| role | VARCHAR(16) | NOT NULL | admin / user |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**officials — 官员基本信息**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| name | VARCHAR(64) | NOT NULL | |
| birth_date | DATE | NOT NULL | 精确到月，日置 1 |
| birth_place | VARCHAR(128) | NOT NULL | |
| ancestral_home | VARCHAR(128) | | |
| ethnicity | VARCHAR(32) | | |
| political_affiliation | VARCHAR(64) | | |
| gender | VARCHAR(8) | NOT NULL | M/F |
| photo_url | TEXT | | |
| current_position | VARCHAR(256) | | |
| current_level | VARCHAR(64) | | |
| committee_term | VARCHAR(32) | NOT NULL | |
| committee_type | VARCHAR(16) | NOT NULL | member/alternate |
| status | VARCHAR(16) | NOT NULL | active/retired/fallen/deceased |
| content_hash | VARCHAR(64) | | 增量比对 |
| completeness_score | FLOAT | DEFAULT 0 | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

索引：`idx_officials_name`, `idx_officials_term`, `idx_officials_status`

**career_entries — 履历记录**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| official_id | UUID | FK → officials | ON DELETE CASCADE |
| start_year | INT | NOT NULL | |
| end_year | INT | | NULL=至今 |
| entry_type | VARCHAR(16) | NOT NULL | education/political/military/enterprise/other |
| description | TEXT | NOT NULL | |

索引：`idx_career_official`, `idx_career_years`

**education — 教育经历**（1:1 关联 career_entries，entry_type=education）

**political_career — 从政经历**（1:1 关联 career_entries，entry_type=political）

**relationships — 关系边（PG 镜像，权威计算结果）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| source_official_id | UUID | FK | |
| target_official_id | UUID | FK | |
| relationship_type | VARCHAR(32) | NOT NULL | |
| context | TEXT | | |
| start_year | INT | | |
| end_year | INT | | |
| location | VARCHAR(128) | | |
| department | VARCHAR(256) | | |
| strength | FLOAT | NOT NULL | 0-1 |
| computed_at | TIMESTAMPTZ | NOT NULL | |

唯一约束：`UNIQUE(source_official_id, target_official_id, relationship_type, location, department)`

**scraper_tasks / scraper_logs / scraper_sources / official_versions / audit_logs** — 任务、日志、数据源、版本、审计

#### 4.1.2 ER 关系

```
users (独立)

officials 1──N career_entries 1──1 education
                              1──1 political_career

officials N──N officials  (via relationships)

officials 1──N official_versions
officials 1──N data_change_logs
```

### 4.2 Neo4j 图模型

#### 4.2.1 节点

```cypher
(:Official {
  id: String,          // 与 PG UUID 一致
  name: String,
  birth_date: String,
  birth_place: String,
  status: String,
  level: String,
  committee_term: String
})
```

索引：`CREATE INDEX official_id FOR (o:Official) ON (o.id)`

#### 4.2.2 关系

| 类型 | 方向 | 属性 |
|------|------|------|
| COLLEAGUE | 无向（双向各存一条或查询时忽略方向） | strength, start_year, end_year, location, department |
| SUPERIOR_SUBORDINATE | 有向 | strength, start_year, end_year |
| SCHOOLMATE | 无向 | strength, institution |
| HOMETOWN | 无向 | strength, place_type |
| SECRETARY | 有向 (secretary→leader) | start_year, end_year |

#### 4.2.3 典型 Cypher

**查询关联官员（min_strength 过滤）：**

```cypher
MATCH (o:Official {id: $official_id})-[r]-(other:Official)
WHERE r.strength >= $min_strength
RETURN other, r
ORDER BY r.strength DESC
LIMIT 100
```

**最短路径（深度限制）：**

```cypher
MATCH path = shortestPath(
  (a:Official {id: $from_id})-[*..3]-(b:Official {id: $to_id})
)
RETURN path
```

### 4.3 Redis 数据结构

| Key 模式 | 类型 | 用途 | TTL |
|----------|------|------|-----|
| `session:{user_id}` | String | 登录会话 | 24h |
| `cache:relationship:{a}:{b}` | String (JSON) | 关系查询缓存 | 1h |
| `cache:connections:{id}:{min}` | String (JSON) | 关联网络缓存 | 1h |
| `cache:statistics` | String (JSON) | 全局统计 | 30min |
| `celery:*` | — | Celery broker/backend | — |
| `sync:neo4j:retry` | List | Neo4j 同步重试队列 | — |
| `ratelimit:{ip}:{endpoint}` | String | API 限流计数 | 1min |

---

## 5. 接口设计

### 5.1 通用规范

- Base URL：`/api/v1`
- Content-Type：`application/json`
- 认证头：`Authorization: Bearer <JWT>`
- 分页参数：`page`（默认 1）、`page_size`（默认 20，最大 100）
- 时间格式：ISO 8601 UTC

### 5.2 统一响应与错误

**成功响应：**

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2026-06-09T08:00:00Z"
}
```

**分页响应 data 结构：**

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应：**

```json
{
  "code": 400,
  "message": "Invalid parameter: official_id",
  "data": null,
  "timestamp": "2026-06-09T08:00:00Z"
}
```

### 5.3 核心接口详细设计

#### 5.3.1 认证

**POST /api/v1/auth/login**

请求：
```json
{ "username": "admin", "password": "******" }
```

响应 data：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "uuid", "username": "admin", "role": "admin" }
}
```

JWT Payload：`{ sub: user_id, role, exp, iat }`

#### 5.3.2 官员列表

**GET /api/v1/officials**

| 参数 | 类型 | 说明 |
|------|------|------|
| name | string | 姓名模糊搜索 |
| committee_term | string | 届次筛选 |
| status | string | 状态筛选 |
| province | string | 任职省份 |
| page, page_size | int | 分页 |

#### 5.3.3 关系查询

**GET /api/v1/analysis/relationship**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| official_a | UUID | 是 | |
| official_b | UUID | 是 | |

响应 data：
```json
{
  "official_a": { "id": "...", "name": "..." },
  "official_b": { "id": "...", "name": "..." },
  "strength": 0.72,
  "level": "一般同盟",
  "dimensions": [
    { "name": "同一部门共事", "weight": 0.30, "matched": true, "detail": "..." },
    { "name": "同一地区任职", "weight": 0.25, "matched": true, "detail": "..." }
  ],
  "time_overlap_years": 5
}
```

#### 5.3.4 抓取任务

**POST /api/v1/scraper/tasks/{id}/run**

异步执行，响应：
```json
{
  "task_id": "celery-uuid",
  "status": "PENDING"
}
```

**GET /api/v1/scraper/tasks/{id}/status**

```json
{
  "status": "RUNNING|SUCCESS|FAILURE",
  "progress": { "total": 200, "completed": 80, "updated": 5, "failed": 2 },
  "started_at": "...",
  "finished_at": null
}
```

### 5.4 权限矩阵

| 资源 | admin | user |
|------|-------|------|
| 官员 CRUD | 读写 | 只读 |
| 分析查询 | ✓ | ✓ |
| 抓取管理 | ✓ | ✗ |
| 用户管理 | ✓ | ✗ |
| 数据导出 | ✓ | ✓ |

---

## 6. 核心算法设计

### 6.1 同盟关系强度计算

#### 6.1.1 维度匹配

对官员 A、B 分别提取特征集合，逐维度判定 \(S_i \in \{0, 1\}\)：

| 维度 i | 权重 \(W_i\) | 匹配条件 |
|--------|-------------|----------|
| 同一部门共事 | 0.30 | ∃ 从政经历 \(pa, pb\)：department 相同且年份区间交集 ≥ 1 年 |
| 同一地区任职 | 0.25 | location 省级归一化后相同且时间重叠 |
| 上下级关系 | 0.20 | A.superior_id = B 或 B.superior_id = A（或间接一级） |
| 校友关系 | 0.10 | institution 相同（含同期近似，可选 ±3 年） |
| 同乡关系 | 0.10 | birth_place 或 ancestral_home 省级相同 |
| 时间重叠度 | 0.05 | 共用时间因子（见下） |

#### 6.1.2 计算公式

\[
\text{TimeFactor} = \min\left(1,\ \frac{\text{overlap\_years}}{\max(\text{overlap\_years}, 1) + 2}\right)
\]

\[
\text{Strength} = \sum_{i=1}^{6} W_i \times S_i \times \text{TimeFactor}
\]

结果 clamp 至 \([0, 1]\)。

#### 6.1.3 关系等级映射

| Strength | 等级 |
|----------|------|
| [0.8, 1.0] | 密切同盟 |
| [0.5, 0.8) | 一般同盟 |
| [0.3, 0.5) | 弱关联 |
| [0.0, 0.3) | 无明显关联 |

#### 6.1.4 批量计算优化

- 全量重算：Celery 低峰期批处理，按 `committee_term` 分片
- 增量重算：官员更新时，仅对该官员与全量官员的有潜力对（同省、同校、同部门关键词）计算，复杂度约 \(O(k)\)，k << N²
- 结果持久化至 PG `relationships` 与 Neo4j 边

### 6.2 派系聚类（Louvain）

1. 从 Neo4j 导出子图（strength ≥ 0.3 的边）
2. 构建 NetworkX 无向加权图
3. 运行 Louvain 社区发现
4. 返回 `{ cluster_id, officials[], modularity }`
5. 聚类结果缓存 Redis，手动触发或每周定时刷新

### 6.3 履历相似度

将官员履历构造为 multi-hot 特征向量：

- 维度：省份、部门关键词（TF-IDF）、职位级别、学校
- 相似度：余弦相似度 \(\cos(\theta) = \frac{A \cdot B}{\|A\|\|B\|}\)

### 6.4 路径查询

- 算法：Neo4j `shortestPath` + 备选 `allShortestPaths`（limit 10）
- 最大深度：默认 3，可配置至 5
- 路径权重：路径上各边 strength 的几何平均

---

## 7. 前端设计

### 7.1 架构

```
main.ts
  ├── router (guards: auth, role)
  ├── pinia stores
  │     ├── authStore
  │     ├── officialStore
  │     └── analysisStore
  └── api client (axios interceptors)
```

### 7.2 关键组件设计

#### 7.2.1 ForceGraph（关系网络图）

| 属性 | 设计 |
|------|------|
| 渲染 | D3.js force simulation |
| 节点大小 | 映射 `current_level` 行政级别 |
| 节点颜色 | 派系 cluster_id 或 status |
| 边粗细 | 映射 strength |
| 性能 | ≤500 节点；超出时按 strength Top-N 截断 + 提示 |
| 交互 | zoom/pan/drag；点击节点 emit `select`；双击扩展邻居 |

#### 7.2.2 CareerTimeline（履历时间线）

- 按 entry_type 分色：教育/从政/军旅/其他
- 支持垂直/水平布局切换
- hover 显示 detail tooltip

#### 7.2.3 ChinaMap（地理分布）

- ECharts 中国地图 JSON
- 数据：`{ province: count }` 或 `{ province, officials[] }`
- 时间轴 slider 切换年份快照

### 7.3 状态与缓存

- 官员列表：Pinia + 路由级 keep-alive
- 分析结果：sessionStorage 缓存当前会话的关系查询
- 网络图：不持久化 simulation 状态，仅缓存 API 数据

---

## 8. 安全设计

### 8.1 认证流程

```
Client ──POST /login──▶ Backend
         ◀── JWT ──────
Client ──请求 + Bearer Token──▶ Backend
                              ├─ 验证签名与 exp
                              ├─ 加载 user + role
                              └─ RBAC 鉴权
```

- JWT 密钥：`JWT_SECRET` 环境变量，≥256 bit
- Access Token 有效期：24h；可选 Refresh Token（7d，存 Redis）

### 8.2 密码安全

- bcrypt，cost factor = 12
- 登录失败 5 次 / 15 分钟锁定（Redis 计数）

### 8.3 RBAC 实现

FastAPI 依赖注入：

```python
def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403)
        return user
    return checker
```

### 8.4 API 安全

| 措施 | 实现 |
|------|------|
| HTTPS | Nginx TLS 1.2+ |
| 限流 | 100 req/min/IP（Redis sliding window） |
| CORS | 白名单域名 |
| SQL 注入 | ORM 参数化查询 |
| XSS | 前端输出转义；Content-Security-Policy |
| 审计 | 管理员操作、登录、导出写入 audit_logs |

---

## 9. 性能与可靠性设计

### 9.1 性能目标与策略

| 指标 | 目标 | 策略 |
|------|------|------|
| 首屏加载 | ≤ 3s | 前端路由懒加载、Gzip、CDN 静态资源 |
| 普通 API | ≤ 500ms | PG 索引、Redis 缓存、连接池 |
| 复杂分析 | ≤ 5s | 预计算、异步任务、结果缓存 |
| 500 节点图渲染 | ≤ 2s | Canvas 渲染、数据截断 |
| 50 并发 | — | Backend HPA 2-4 副本 |

### 9.2 连接池配置

| 组件 | 配置 |
|------|------|
| PostgreSQL | pool_size=20, max_overflow=10 |
| Neo4j | max_connection_pool_size=50 |
| Redis | max_connections=100 |

### 9.3 可靠性

| 指标 | 设计 |
|------|------|
| 可用性 ≥ 99.5% | 多副本 + 健康检查 + 滚动更新 |
| RTO ≤ 1h | K8S 自动重启；Neo4j/PG 从备份恢复 |
| RPO ≤ 24h | PG 每日 pg_dump；Neo4j 每日 neo4j-admin backup |
| 降级 | Neo4j 不可用时，关系 API 返回 PG 镜像数据（无路径查询） |

### 9.4 备份策略

```
CronJob (K8S, 02:00 UTC)
  ├── pg_dump → MinIO/S3 (保留 30 天)
  └── neo4j-admin backup → MinIO/S3 (保留 30 天)
```

---

## 10. 部署设计

### 10.1 容器规划

| 服务 | 镜像 | 端口 | CPU | Memory |
|------|------|------|-----|--------|
| backend | sopas-backend:latest | 8000 | 1 | 1Gi |
| frontend | sopas-frontend:latest | 80 | 0.5 | 256Mi |
| celery-worker | sopas-backend:latest | — | 1 | 1Gi |
| celery-beat | sopas-backend:latest | — | 0.25 | 256Mi |
| neo4j | neo4j:5 | 7474, 7687 | 2 | 4Gi |
| postgres | postgres:16 | 5432 | 1 | 1Gi |
| redis | redis:7-alpine | 6379 | 0.5 | 512Mi |
| nginx | nginx:alpine | 80, 443 | 0.5 | 256Mi |

### 10.2 K8S 资源清单

| 工作负载 | 类型 | 副本 | 存储 |
|----------|------|------|------|
| backend | Deployment + HPA | min 2, max 4 | — |
| frontend | Deployment | 2 | — |
| celery-worker | Deployment | 1-2 | — |
| celery-beat | Deployment | 1 | — |
| neo4j | StatefulSet | 1 | PVC 20Gi |
| postgres | StatefulSet | 1 | PVC 10Gi |
| redis | Deployment | 1 | PVC 2Gi |
| ingress | Ingress | — | — |

HPA 触发条件：CPU 利用率 > 70% 持续 3 分钟。

### 10.3 环境规划

| 环境 | 用途 | 部署 |
|------|------|------|
| dev | 本地开发 | docker-compose.yml |
| test | 集成测试 | K8S 单节点（192.168.0.111） |
| prod | 生产 | K8S 集群 |

### 10.4 docker-compose 本地开发

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, neo4j, redis]
  frontend:
    build: ./frontend
    ports: ["5173:80"]
  postgres:
    image: postgres:16
  neo4j:
    image: neo4j:5
  redis:
    image: redis:7-alpine
  celery-worker:
    build: ./backend
    command: celery -A app.tasks worker -l info
```

### 10.5 配置管理

| 配置项 | 来源 |
|--------|------|
| 数据库连接 | Secret |
| JWT_SECRET | Secret |
| 爬虫频率/代理 | ConfigMap |
| 日志级别 | ConfigMap |

---

## 11. 运维与监控设计

### 11.1 健康检查

| 端点 | 检查项 |
|------|--------|
| GET /health | 进程存活 |
| GET /health/ready | PG + Neo4j + Redis 连通性 |

K8S：`livenessProbe` → `/health`；`readinessProbe` → `/health/ready`

### 11.2 监控指标（Prometheus）

| 指标 | 类型 | 说明 |
|------|------|------|
| http_requests_total | Counter | 按 path、status 分维度 |
| http_request_duration_seconds | Histogram | API 延迟 |
| scraper_tasks_total | Counter | 抓取成功/失败 |
| scraper_duration_seconds | Histogram | 抓取耗时 |
| neo4j_query_duration_seconds | Histogram | 图查询延迟 |
| celery_queue_length | Gauge | 队列积压 |

### 11.3 告警规则

| 告警 | 条件 | 级别 |
|------|------|------|
| API 高错误率 | 5xx > 5% / 5min | Critical |
| API 高延迟 | P95 > 2s / 5min | Warning |
| 抓取失败 | 连续 3 次任务失败 | Warning |
| 磁盘空间 | PVC > 85% | Warning |
| Neo4j 同步积压 | retry queue > 100 | Warning |

### 11.4 日志规范

- 格式：JSON 结构化日志
- 字段：`timestamp`, `level`, `service`, `trace_id`, `message`, `context`
- 级别：DEBUG（dev）/ INFO（prod 默认）/ WARNING / ERROR
- 采集：stdout → Fluent Bit / Loki（可选）

---

## 12. 附录

### 12.1 需求追溯矩阵（节选）

| 需求 ID | 设计章节 |
|---------|----------|
| SCR-001 ~ SCR-010 | §3.1 |
| STR-001 ~ STR-010 | §3.2, §4 |
| ANA-001 ~ ANA-009 | §3.3, §6 |
| DSP-001 ~ DSP-010 | §3.4, §7 |
| SEC-001 ~ SEC-006 | §8 |
| EXP-001 ~ EXP-004 | §2.1, §3.1.6, §3.3.4 |

### 12.2 开发顺序建议

1. 基础设施：PG/Neo4j/Redis、Backend 骨架、认证
2. 存储层：Official CRUD、双库同步
3. 爬虫：首个数据源（人民网）端到端
4. 分析引擎：关系强度计算 + Neo4j 写入
5. 前端：官员列表/详情/关系图
6. 扩展：更多数据源、聚类、管理后台
7. 部署：K8S 清单、监控、备份 CronJob

### 12.3 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-06-09 | 初始版本，基于 SRS v1.0 | SOPAS Team |
