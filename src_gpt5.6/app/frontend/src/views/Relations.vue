<template>
  <div>
    <div class="toolbar"><div class="stats"><strong>{{ relations.length }}</strong><span>条人物关系</span></div><button class="primary" @click="openAnalyzer">关系分析</button></div>
    <div class="network-canvas">
      <div class="network-orbit orbit-one"></div><div class="network-orbit orbit-two"></div>
      <div v-if="!officials.length" class="empty network-empty"><b>关系网络尚为空</b><span>先建立人物履历，再分析人物关系。</span></div>
      <div v-for="(o, i) in officials.slice(0, 12)" :key="o.id" class="network-node" :style="nodeStyle(i)"><strong>{{ o.name }}</strong><small>{{ o.organization || '未分类' }}</small></div>
    </div>
    <div class="panel relation-panel"><div class="panel-head"><h2>关系明细</h2><span>{{ relations.length }}</span></div><div v-if="!relations.length" class="empty compact">暂无关系记录</div><div v-for="r in relations" :key="r.id" class="relation-row"><div><strong>{{ r.source_name }}</strong><span>{{ r.relation_type }}</span><strong>{{ r.target_name }}</strong><p>{{ r.description || '暂无说明' }}</p></div><button class="danger" @click="remove(r.id)">删除</button></div></div>

    <div v-if="analyzerOpen" class="modal" @click.self="closeAnalyzer">
      <div class="modal-card large">
        <div class="modal-head"><div><p class="eyebrow">RELATION ANALYSIS</p><h2>人物关系分析</h2></div><button type="button" @click="closeAnalyzer">×</button></div>
        <div class="form-grid">
          <label>人物 A<select v-model.number="form.source_id" :disabled="analyzing"><option :value="0" disabled>请选择</option><option v-for="o in officials" :key="o.id" :value="o.id" :disabled="o.id === form.target_id">{{ o.name }} · {{ o.organization || '机构未知' }}</option></select></label>
          <label>人物 B<select v-model.number="form.target_id" :disabled="analyzing"><option :value="0" disabled>请选择</option><option v-for="o in officials" :key="o.id" :value="o.id" :disabled="o.id === form.source_id">{{ o.name }} · {{ o.organization || '机构未知' }}</option></select></label>
        </div>
        <div v-if="analysis" class="relation-analysis-result">
          <div class="analysis-heading"><div><p class="eyebrow">ANALYSIS RESULT</p><h3>{{ analysis.source_name }} 与 {{ analysis.target_name }}</h3></div><span class="pill active">置信度：{{ analysis.confidence }}</span></div>
          <div class="analysis-type">{{ analysis.relation_type }}</div>
          <p>{{ analysis.summary }}</p>
          <h4>履历依据</h4>
          <ul v-if="analysis.evidence.length"><li v-for="item in analysis.evidence" :key="item">{{ item }}</li></ul>
          <p v-else class="muted">模型未列出明确的履历依据。</p>
        </div>
        <div class="modal-actions"><button type="button" @click="closeAnalyzer">取消</button><button v-if="analysis" type="button" @click="saveAnalysis">保存关系</button><button class="primary" type="button" :disabled="!canAnalyze || analyzing" @click="analyze">{{ analyzing ? '分析中…' : analysis ? '重新分析' : '开始分析' }}</button></div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { showToast } from '@/composables/toast'
import { analyzeRelationApi, createRelationApi, deleteRelationApi, listOfficialsApi, listRelationsApi, type Official, type Relation, type RelationAnalysis } from '@/api/officials'
const relations = ref<Relation[]>([]); const officials = ref<Official[]>([]); const analyzerOpen = ref(false); const analyzing = ref(false); const analysis = ref<RelationAnalysis | null>(null)
const form = reactive({ source_id: 0, target_id: 0 }); const canAnalyze = computed(() => form.source_id > 0 && form.target_id > 0 && form.source_id !== form.target_id)
onMounted(load)
async function load() { const [r, o] = await Promise.all([listRelationsApi(), loadAllOfficials()]); relations.value = r; officials.value = o }
async function loadAllOfficials() { const first = await listOfficialsApi({ page: 1, page_size: 100 }); const items = [...first.items]; const pages = Math.ceil(first.total / first.page_size); for (let page = 2; page <= pages; page++) items.push(...(await listOfficialsApi({ page, page_size: 100 })).items); return items }
function nodeStyle(i: number) { const count = Math.max(officials.value.slice(0, 12).length, 1); const angle = (i / count) * Math.PI * 2; return { left: `${50 + Math.cos(angle) * 36}%`, top: `${50 + Math.sin(angle) * 36}%` } }
function openAnalyzer() { analysis.value = null; analyzerOpen.value = true }
function closeAnalyzer() { if (analyzing.value) return; analyzerOpen.value = false }
async function analyze() { if (!canAnalyze.value) return; analyzing.value = true; analysis.value = null; try { analysis.value = await analyzeRelationApi(form) } finally { analyzing.value = false } }
async function saveAnalysis() { if (!analysis.value) return; await createRelationApi({ source_id: analysis.value.source_id, target_id: analysis.value.target_id, relation_type: analysis.value.relation_type, description: `${analysis.value.summary}\n依据：${analysis.value.evidence.join('；')}` }); analyzerOpen.value = false; showToast('分析结果已保存为人物关系'); await load() }
async function remove(id: number) { if (!confirm('确认删除这条关系？')) return; await deleteRelationApi(id); await load() }
</script>
<style scoped>
.relation-row p { white-space: pre-wrap; }
.relation-analysis-result { margin-top: 20px; padding: 18px; border: 1px solid #dfe5f2; border-radius: 12px; background: #f8faff; }
.analysis-heading { display: flex; align-items: start; justify-content: space-between; gap: 12px; }
.analysis-heading h3 { margin: 0; }
.analysis-type { display: inline-block; margin: 16px 0 5px; padding: 6px 11px; border-radius: 999px; background: #e8edff; color: #425ec4; font-size: 12px; font-weight: 800; }
.relation-analysis-result > p, .relation-analysis-result li { color: #56627a; font-size: 13px; line-height: 1.7; }
.relation-analysis-result h4 { margin-bottom: 6px; }
.relation-analysis-result ul { margin: 0; padding-left: 20px; }
</style>
