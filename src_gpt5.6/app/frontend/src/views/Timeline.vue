<template>
  <div class="timeline-page">
    <div class="panel timeline-controls">
      <div class="selector-heading">
        <div>
          <h2>选择人物</h2>
          <p>横向选择人物，最多可同时对比 8 份履历档案。</p>
        </div>
        <button class="primary" :disabled="!selectedIds.length || loading" @click="updateTimeline">
          {{ loading ? '载入中…' : '更新时间线' }}
        </button>
      </div>
      <div class="person-picker">
        <label v-for="official in officials" :key="official.id" :class="{ selected: selectedIds.includes(official.id) }">
          <input v-model="selectedIds" type="checkbox" :value="official.id" :disabled="!selectedIds.includes(official.id) && selectedIds.length >= 8">
          <span><b>{{ official.name }}</b><small>{{ official.current_position || official.organization || '履历待完善' }}</small></span>
        </label>
        <span v-if="!officials.length" class="muted">暂无可选人物，请先在履历档案中新增人物。</span>
      </div>
      <p class="selection-summary">已选择 {{ selectedIds.length }} 人<span v-if="loadedAt"> · 最近更新 {{ loadedAt }}</span></p>
    </div>

    <div v-if="!timelineOfficials.length" class="panel empty timeline-empty">
      <b>选择人物并更新时间线</b>
      <span>系统将载入所选人物的完整任职履历，并按年月对齐展示。</span>
    </div>

    <div v-else-if="!chartCareers.length" class="panel empty timeline-empty">
      <b>所选人物暂无可识别的任职时间</b>
      <span>请在履历档案中补充“YYYY.MM”格式的任职起止时间。</span>
    </div>

    <div v-else class="panel timeline-chart-panel">
      <div class="timeline-scroll">
        <div class="timeline-chart" :style="chartStyle">
          <div class="axis-corner">年月</div>
          <div v-for="person in timelineOfficials" :key="person.id" class="person-head">
            <div class="profile-avatar small-avatar">{{ person.name.slice(0, 1) }}</div>
            <span><b>{{ person.name }}</b><small>{{ person.current_position || person.organization || '—' }}</small></span>
          </div>

          <div class="axis-column" :style="{ height: `${chartHeight}px` }">
            <div v-for="tick in ticks" :key="tick.index" class="axis-tick" :class="{ year: tick.month === 1 }" :style="{ top: `${tick.index * rowHeight}px` }">
              <span>{{ tick.label }}</span>
            </div>
          </div>
          <div v-for="person in timelineOfficials" :key="`lane-${person.id}`" class="person-lane" :style="{ height: `${chartHeight}px` }">
            <div v-for="tick in ticks" :key="tick.index" class="month-line" :class="{ year: tick.month === 1 }" :style="{ top: `${tick.index * rowHeight}px` }"></div>
            <article v-for="career in careersFor(person.id)" :key="career.key" class="career-block" :style="careerStyle(career)">
              <strong>{{ career.position }}</strong>
              <span>{{ career.organization || '机构未知' }}</span>
              <time>{{ career.startLabel }} — {{ career.endLabel }}</time>
              <small v-if="career.location">{{ career.location }}</small>
            </article>
            <div v-if="!careersFor(person.id).length" class="lane-empty">暂无有效时间记录</div>
          </div>
        </div>
      </div>
      <p v-if="ignoredCount" class="timeline-warning">有 {{ ignoredCount }} 条任职记录因缺少可识别的开始年月而未显示。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listTimelineCandidatesApi, loadTimelineApi, type Career, type Official } from '@/api/officials'
import { showToast } from '@/composables/toast'

interface ParsedCareer extends Career {
  key: string
  officialId: number
  startMonth: number
  endMonth: number
  startLabel: string
  endLabel: string
}

const rowHeight = 22
const officials = ref<Official[]>([])
const selectedIds = ref<number[]>([])
const timelineOfficials = ref<Official[]>([])
const loading = ref(false)
const loadedAt = ref('')

onMounted(async () => { officials.value = await listTimelineCandidatesApi() })

async function updateTimeline() {
  loading.value = true
  try {
    const result = await loadTimelineApi(selectedIds.value)
    timelineOfficials.value = result.officials
    loadedAt.value = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(new Date())
    showToast(`已载入 ${result.officials.length} 份人物履历`)
  } finally {
    loading.value = false
  }
}

function parseMonth(value: string, current = false): number | null {
  if (current && (!value || /至今|现在|现任/.test(value))) {
    const now = new Date()
    return now.getFullYear() * 12 + now.getMonth()
  }
  const match = String(value || '').match(/(19|20)\d{2}/)
  if (!match) return null
  const year = Number(match[0])
  const rest = String(value).slice((match.index || 0) + 4)
  const monthMatch = rest.match(/(?:[.\-/年]\s*)(\d{1,2})/)
  const month = monthMatch ? Math.min(12, Math.max(1, Number(monthMatch[1]))) : 1
  return year * 12 + month - 1
}

function monthLabel(monthIndex: number) {
  return `${Math.floor(monthIndex / 12)}.${String(monthIndex % 12 + 1).padStart(2, '0')}`
}

const parsed = computed(() => timelineOfficials.value.flatMap(person => (person.careers || []).map((career, index) => {
  const startMonth = parseMonth(career.start_date)
  if (startMonth === null) return null
  const parsedEnd = parseMonth(career.end_date, true)
  const endMonth = Math.max(startMonth, parsedEnd ?? startMonth)
  return { ...career, key: `${person.id}-${career.id || index}`, officialId: person.id, startMonth, endMonth, startLabel: monthLabel(startMonth), endLabel: /至今|现在|现任/.test(career.end_date || '') ? '至今' : monthLabel(endMonth) }
}).filter((item): item is ParsedCareer => item !== null)))

const ignoredCount = computed(() => timelineOfficials.value.reduce((sum, person) => sum + (person.careers || []).length, 0) - parsed.value.length)
const startMonth = computed(() => parsed.value.length ? Math.min(...parsed.value.map(item => item.startMonth)) : 0)
const endMonth = computed(() => parsed.value.length ? Math.max(...parsed.value.map(item => item.endMonth)) : 0)
const chartCareers = computed(() => parsed.value)
const monthCount = computed(() => Math.max(1, endMonth.value - startMonth.value + 1))
const chartHeight = computed(() => monthCount.value * rowHeight)
const ticks = computed(() => Array.from({ length: monthCount.value }, (_, index) => {
  const value = startMonth.value + index
  const month = value % 12 + 1
  return { index, month, label: month === 1 || index === 0 ? monthLabel(value) : String(month).padStart(2, '0') }
}))
const chartStyle = computed(() => ({ gridTemplateColumns: `86px repeat(${timelineOfficials.value.length}, minmax(210px, 1fr))`, minWidth: `${86 + timelineOfficials.value.length * 210}px` }))
function careersFor(officialId: number) { return parsed.value.filter(item => item.officialId === officialId) }
function careerStyle(career: ParsedCareer) {
  const top = (career.startMonth - startMonth.value) * rowHeight + 3
  const duration = career.endMonth - career.startMonth + 1
  return { top: `${top}px`, height: `${Math.max(68, duration * rowHeight - 6)}px` }
}
</script>

<style scoped>
.timeline-controls{margin-bottom:18px}.selector-heading{display:flex;align-items:center;justify-content:space-between;gap:18px}.selector-heading h2{margin:0}.selector-heading p{margin:5px 0 0;color:#7c879b;font-size:12px}.person-picker{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}.person-picker label{display:flex;align-items:center;gap:8px;min-width:160px;padding:9px 11px;border:1px solid #dfe4ee;border-radius:10px;cursor:pointer;background:#fff}.person-picker label.selected{border-color:#6079dc;background:#f2f5ff}.person-picker input{width:auto;margin:0}.person-picker span,.person-picker b,.person-picker small{display:block}.person-picker small{margin-top:2px;color:#8490a4;font-size:10px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.selection-summary{margin:12px 0 0;color:#68758c;font-size:11px}.timeline-empty{min-height:260px}.timeline-chart-panel{padding:0;overflow:hidden}.timeline-scroll{overflow:auto;max-height:calc(100vh - 260px)}.timeline-chart{display:grid;position:relative;background:#fff}.axis-corner,.person-head{position:sticky;top:0;z-index:6;height:72px;background:#f7f9fc;border-bottom:1px solid #dce2ed}.axis-corner{left:0;display:grid;place-items:center;color:#78859a;font-size:11px}.person-head{display:flex;align-items:center;gap:9px;padding:10px 14px;border-left:1px solid #e4e8f0}.person-head span,.person-head b,.person-head small{display:block;min-width:0}.person-head small{margin-top:3px;color:#7e899c;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.axis-column{position:relative;grid-column:1;position:sticky;left:0;z-index:4;background:#fafbfe;border-right:1px solid #dce2ed}.axis-tick{position:absolute;left:0;right:0;border-top:1px solid #edf0f5;color:#929caf;font-size:9px;padding:2px 7px}.axis-tick.year{border-color:#cbd4e5;color:#52617b;font-weight:800}.person-lane{position:relative;border-right:1px solid #e5e9f1;background:#fff}.month-line{position:absolute;left:0;right:0;border-top:1px solid #f0f2f6}.month-line.year{border-color:#d8dfeb}.career-block{position:absolute;left:8px;right:8px;z-index:2;padding:10px;border-radius:9px;background:linear-gradient(145deg,#405bc5,#617be0);color:#fff;box-shadow:0 5px 14px #344da82b;overflow:hidden;border-left:3px solid #233b9a}.career-block strong,.career-block span,.career-block time,.career-block small{display:block}.career-block strong{font-size:12px}.career-block span{margin-top:3px;font-size:10px;color:#e5eaff}.career-block time,.career-block small{margin-top:5px;font-size:9px;color:#cbd5ff}.lane-empty{padding:22px 12px;color:#a0a8b6;font-size:11px}.timeline-warning{margin:0;padding:10px 16px;background:#fff8e9;color:#98702c;font-size:11px}@media(max-width:700px){.selector-heading{align-items:flex-start;flex-direction:column}.selector-heading button{width:100%}.person-picker label{width:100%}}
</style>
