<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  api,
  type AnalysisTask,
  type CareerEvent,
  type CurrentUser,
  type Official,
  type Relationship,
  type SourceConfig,
  type SourceDocument
} from "./api";

type PageKey = "dashboard" | "officials" | "relationships" | "analysis" | "sources";

const pages: Array<{ key: PageKey; label: string; adminOnly?: boolean }> = [
  { key: "dashboard", label: "工作台" },
  { key: "officials", label: "官员档案" },
  { key: "relationships", label: "关系图谱" },
  { key: "analysis", label: "分析任务" },
  { key: "sources", label: "数据源", adminOnly: true }
];

const loading = ref(true);
const busy = ref(false);
const error = ref("");
const message = ref("");
const user = ref<CurrentUser | null>(null);
const page = ref<PageKey>("dashboard");
const loginForm = reactive({ username: "admin", password: "admin123" });

const officials = ref<Official[]>([]);
const relationships = ref<Relationship[]>([]);
const tasks = ref<AnalysisTask[]>([]);
const sourceConfigs = ref<SourceConfig[]>([]);
const documents = ref<SourceDocument[]>([]);
const query = ref("");
const selectedOfficial = ref<Official | null>(null);
const timeline = ref<CareerEvent[]>([]);

const officialForm = reactive({ name: "", profile_summary: "" });
const eventForm = reactive({
  event_type: "appointment",
  start_date: "",
  end_date: "",
  organization_name: "",
  position_name: "",
  location_name: "",
  description: ""
});
const csvText = ref("name,membership_type,rank_order,profile_summary\n张三,member,1,\n李四,alternate_member,2,");
const taskForm = reactive({ name: "关系分析", task_type: "alliance", parameters: "{}" });
const sourceForm = reactive({
  name: "",
  base_url: "",
  source_type: "official",
  trust_level: "A",
  crawl_strategy: "requests",
  frequency_cron: "0 3 * * 1",
  request_interval_seconds: 3,
  max_retry: 3,
  is_enabled: true
});

const visiblePages = computed(() =>
  pages.filter((item) => !item.adminOnly || user.value?.role === "ADMIN")
);

function clearNotice() {
  error.value = "";
  message.value = "";
}

function reportError(value: unknown) {
  error.value = value instanceof Error ? value.message : String(value);
}

async function login() {
  clearNotice();
  busy.value = true;
  try {
    const result = await api.login(loginForm.username, loginForm.password);
    api.setAccessToken(result.access_token);
    user.value = await api.me();
    await refreshAll();
  } catch (value) {
    reportError(value);
  } finally {
    busy.value = false;
  }
}

async function logout() {
  try {
    await api.logout();
  } finally {
    user.value = null;
    page.value = "dashboard";
  }
}

async function refreshAll() {
  if (!user.value) return;
  const [officialRows, relationshipRows, taskRows] = await Promise.all([
    api.listOfficials(),
    api.listRelationships(),
    api.listAnalysisTasks()
  ]);
  officials.value = officialRows;
  relationships.value = relationshipRows;
  tasks.value = taskRows;
  if (user.value.role === "ADMIN") {
    const [configs, docs] = await Promise.all([
      api.listSourceConfigs(),
      api.listSourceDocuments()
    ]);
    sourceConfigs.value = configs;
    documents.value = docs;
  }
}

async function searchOfficials() {
  clearNotice();
  try {
    officials.value = await api.listOfficials(query.value);
  } catch (value) {
    reportError(value);
  }
}

async function createOfficial() {
  if (!officialForm.name.trim()) return;
  clearNotice();
  try {
    await api.createOfficial({
      name: officialForm.name,
      profile_summary: officialForm.profile_summary,
      review_status: "draft",
      birth_date_precision: "unknown"
    });
    officialForm.name = "";
    officialForm.profile_summary = "";
    await searchOfficials();
    message.value = "官员档案已创建。";
  } catch (value) {
    reportError(value);
  }
}

async function selectOfficial(official: Official) {
  clearNotice();
  selectedOfficial.value = official;
  try {
    timeline.value = await api.listTimeline(official.id);
  } catch (value) {
    reportError(value);
  }
}

async function createTimelineEvent() {
  if (!selectedOfficial.value || !eventForm.description.trim()) return;
  clearNotice();
  try {
    await api.createTimelineEvent(selectedOfficial.value.id, {
      ...eventForm,
      start_date: eventForm.start_date || null,
      end_date: eventForm.end_date || null,
      organization_name: eventForm.organization_name || null,
      position_name: eventForm.position_name || null,
      location_name: eventForm.location_name || null
    });
    eventForm.description = "";
    timeline.value = await api.listTimeline(selectedOfficial.value.id);
    message.value = "履历事件已添加。";
  } catch (value) {
    reportError(value);
  }
}

async function importCommittee() {
  clearNotice();
  try {
    const result = await api.importCommitteeMembers({
      term_no: 20,
      term_name: "中国共产党第二十届中央委员会",
      start_year: 2022,
      end_year: 2027,
      csv_text: csvText.value
    });
    await searchOfficials();
    message.value = `导入完成：新增 ${result.created_officials}，更新 ${result.updated_officials}。`;
  } catch (value) {
    reportError(value);
  }
}

async function rebuildRelationships() {
  clearNotice();
  try {
    const result = await api.rebuildRelationships();
    relationships.value = await api.listRelationships();
    message.value = `关系重算完成，共生成 ${result.generated_relationships} 条关系。`;
  } catch (value) {
    reportError(value);
  }
}

async function createTask() {
  clearNotice();
  try {
    const parameters = JSON.parse(taskForm.parameters) as Record<string, unknown>;
    await api.createAnalysisTask({
      name: taskForm.name,
      task_type: taskForm.task_type,
      parameters
    });
    tasks.value = await api.listAnalysisTasks();
    message.value = "分析任务已创建。";
  } catch (value) {
    reportError(value);
  }
}

async function createSource() {
  clearNotice();
  try {
    await api.createSourceConfig({ ...sourceForm });
    sourceForm.name = "";
    sourceForm.base_url = "";
    sourceConfigs.value = await api.listSourceConfigs();
    message.value = "数据源已创建。";
  } catch (value) {
    reportError(value);
  }
}

async function crawlSource(id: string) {
  clearNotice();
  try {
    await api.crawlSourceConfig(id);
    documents.value = await api.listSourceDocuments();
    message.value = "抓取完成。";
  } catch (value) {
    reportError(value);
  }
}

async function parseDocument(id: string) {
  clearNotice();
  try {
    const result = await api.parseSourceDocument(id);
    documents.value = await api.listSourceDocuments();
    message.value = result.message;
  } catch (value) {
    reportError(value);
  }
}

watch(page, clearNotice);

onMounted(async () => {
  try {
    user.value = await api.me();
    await refreshAll();
  } catch {
    api.setAccessToken(null);
    user.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div v-if="loading" class="page-shell centered">正在加载系统状态...</div>

  <div v-else-if="!user" class="login-screen">
    <form class="login-card" @submit.prevent="login">
      <div class="brand login-brand">
        <span class="brand-mark">履</span>
        <div><strong>高级官员履历分析系统</strong><small>FastAPI + Vue 内部研究版</small></div>
      </div>
      <label>用户名<input v-model="loginForm.username" autocomplete="username" /></label>
      <label>密码<input v-model="loginForm.password" type="password" autocomplete="current-password" /></label>
      <p v-if="error" class="error">{{ error }}</p>
      <button :disabled="busy">{{ busy ? "登录中..." : "登录" }}</button>
      <p class="hint">首次启动默认账号为 admin / admin123，请通过 .env 修改。</p>
    </form>
  </div>

  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">履</span><div><strong>履历分析系统</strong><small>内部研究版</small></div></div>
      <nav>
        <button v-for="item in visiblePages" :key="item.key" :class="{ active: page === item.key }" @click="page = item.key">
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main class="content">
      <header class="topbar">
        <div><strong>{{ user.display_name || user.username }}</strong><span>{{ user.role === "ADMIN" ? "管理员" : "普通用户" }}</span></div>
        <button class="secondary" @click="logout">退出</button>
      </header>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>

      <section v-if="page === 'dashboard'">
        <div class="page-title"><div><h1>工作台</h1><p>公开履历、来源证据和关系分析集中管理。</p></div></div>
        <div class="metric-grid">
          <div class="metric"><span>官员档案</span><strong>{{ officials.length }}</strong></div>
          <div class="metric"><span>关系边</span><strong>{{ relationships.length }}</strong></div>
          <div class="metric"><span>分析任务</span><strong>{{ tasks.length }}</strong></div>
          <div class="metric"><span>当前权限</span><strong>{{ user.role === "ADMIN" ? "管理员" : "普通用户" }}</strong></div>
        </div>
        <div class="panel"><h2>运行方式</h2><p>FastAPI 单进程、SQLite 数据库、Vue 静态页面，无需 Kubernetes、PostgreSQL、Redis 或 Celery。</p></div>
      </section>

      <section v-if="page === 'officials'">
        <div class="page-title"><div><h1>官员档案</h1><p>检索档案并维护逐年履历。</p></div></div>
        <div class="toolbar"><input v-model="query" placeholder="姓名或摘要" @keyup.enter="searchOfficials" /><button @click="searchOfficials">查询</button></div>
        <form v-if="user.role === 'ADMIN'" class="inline-form panel" @submit.prevent="createOfficial">
          <input v-model="officialForm.name" required placeholder="姓名" />
          <input v-model="officialForm.profile_summary" placeholder="简介" />
          <button>新增档案</button>
        </form>
        <div v-if="user.role === 'ADMIN'" class="panel import-panel">
          <h2>导入第二十届中央委员会名单</h2>
          <textarea v-model="csvText" rows="5" />
          <button @click="importCommittee">导入 CSV</button>
        </div>
        <div class="split-view">
          <div class="panel table-wrap"><table><thead><tr><th>姓名</th><th>状态</th><th>摘要</th></tr></thead><tbody>
            <tr v-for="official in officials" :key="official.id" :class="{ 'selected-row': selectedOfficial?.id === official.id }" @click="selectOfficial(official)">
              <td>{{ official.name }}</td><td>{{ official.review_status }}</td><td>{{ official.profile_summary || "-" }}</td>
            </tr>
          </tbody></table><p v-if="!officials.length" class="empty">暂无档案</p></div>
          <div class="panel detail-panel">
            <template v-if="selectedOfficial">
              <h2>{{ selectedOfficial.name }}的履历</h2>
              <div class="timeline-list"><div v-for="event in timeline" :key="event.id" class="timeline-item">
                <strong>{{ event.start_date || "时间不详" }} - {{ event.end_date || "至今" }}</strong>
                <span>{{ event.organization_name }} {{ event.position_name }}</span><small>{{ event.description }}</small>
              </div><p v-if="!timeline.length" class="empty">暂无履历事件</p></div>
              <form v-if="user.role === 'ADMIN'" class="event-form" @submit.prevent="createTimelineEvent">
                <div class="form-row"><input v-model="eventForm.start_date" type="date" /><input v-model="eventForm.end_date" type="date" /></div>
                <div class="form-row"><input v-model="eventForm.organization_name" placeholder="机构" /><input v-model="eventForm.position_name" placeholder="职位" /></div>
                <input v-model="eventForm.location_name" placeholder="地点" /><textarea v-model="eventForm.description" required placeholder="履历描述" /><button>添加履历</button>
              </form>
            </template><p v-else class="empty">选择一名官员查看履历</p>
          </div>
        </div>
      </section>

      <section v-if="page === 'relationships'">
        <div class="page-title"><div><h1>关系图谱</h1><p>根据履历重叠与公开关系生成联系。</p></div><button v-if="user.role === 'ADMIN'" @click="rebuildRelationships">重算关系</button></div>
        <div class="panel table-wrap"><table><thead><tr><th>主体</th><th>关系</th><th>对象</th><th>强度</th><th>可信度</th></tr></thead><tbody>
          <tr v-for="item in relationships" :key="item.id"><td>{{ item.subject_name }}</td><td>{{ item.relationship_type }}</td><td>{{ item.object_name }}</td><td>{{ item.strength_score }}</td><td>{{ item.confidence }}</td></tr>
        </tbody></table><p v-if="!relationships.length" class="empty">暂无关系，请先维护履历并重算。</p></div>
      </section>

      <section v-if="page === 'analysis'">
        <div class="page-title"><div><h1>分析任务</h1><p>记录研究参数和分析任务状态。</p></div></div>
        <form class="inline-form panel" @submit.prevent="createTask"><input v-model="taskForm.name" required placeholder="任务名称" /><input v-model="taskForm.task_type" required placeholder="任务类型" /><input v-model="taskForm.parameters" required placeholder='参数 JSON，例如 {}' /><button>创建任务</button></form>
        <div class="panel table-wrap"><table><thead><tr><th>名称</th><th>类型</th><th>状态</th><th>创建时间</th></tr></thead><tbody>
          <tr v-for="task in tasks" :key="task.id"><td>{{ task.name }}</td><td>{{ task.task_type }}</td><td>{{ task.status }}</td><td>{{ new Date(task.created_at).toLocaleString() }}</td></tr>
        </tbody></table><p v-if="!tasks.length" class="empty">暂无分析任务</p></div>
      </section>

      <section v-if="page === 'sources' && user.role === 'ADMIN'">
        <div class="page-title"><div><h1>数据源</h1><p>配置公开页面、立即抓取并解析履历正文。</p></div></div>
        <form class="inline-form panel" @submit.prevent="createSource"><input v-model="sourceForm.name" required placeholder="数据源名称" /><input v-model="sourceForm.base_url" required type="url" placeholder="https://..." /><input v-model="sourceForm.frequency_cron" placeholder="Cron" /><button>新增数据源</button></form>
        <div class="panel table-wrap"><h2>数据源配置</h2><table><thead><tr><th>名称</th><th>地址</th><th>可信度</th><th>频率</th><th>操作</th></tr></thead><tbody>
          <tr v-for="source in sourceConfigs" :key="source.id"><td>{{ source.name }}</td><td>{{ source.base_url }}</td><td>{{ source.trust_level }}</td><td>{{ source.frequency_cron }}</td><td><button @click="crawlSource(source.id)">立即抓取</button></td></tr>
        </tbody></table></div>
        <div class="panel table-wrap"><h2>抓取文档</h2><table><thead><tr><th>标题</th><th>状态</th><th>抓取时间</th><th>操作</th></tr></thead><tbody>
          <tr v-for="document in documents" :key="document.id"><td>{{ document.title || document.url }}</td><td>{{ document.parse_status }}</td><td>{{ new Date(document.fetched_at).toLocaleString() }}</td><td><button @click="parseDocument(document.id)">解析履历</button></td></tr>
        </tbody></table><p v-if="!documents.length" class="empty">暂无抓取文档</p></div>
      </section>
    </main>
  </div>
</template>
