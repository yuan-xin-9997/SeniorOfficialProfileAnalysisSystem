<template>
  <div>
    <div class="toolbar"><div class="stats"><strong>{{ relations.length }}</strong><span>条人物关系</span></div><button class="primary" @click="editor = true">＋ 新建关系</button></div>
    <div class="network-canvas">
      <div class="network-orbit orbit-one"></div><div class="network-orbit orbit-two"></div>
      <div v-if="!officials.length" class="empty network-empty"><b>关系网络尚为空</b><span>先建立人物履历，再添加人物关系。</span></div>
      <div v-for="(o, i) in officials.slice(0, 12)" :key="o.id" class="network-node" :style="nodeStyle(i)"><strong>{{ o.name }}</strong><small>{{ o.organization || '未分类' }}</small></div>
    </div>
    <div class="panel relation-panel"><div class="panel-head"><h2>关系明细</h2><span>{{ relations.length }}</span></div><div v-if="!relations.length" class="empty compact">暂无关系记录</div><div v-for="r in relations" :key="r.id" class="relation-row"><div><strong>{{ r.source_name }}</strong><span>{{ r.relation_type }}</span><strong>{{ r.target_name }}</strong><p>{{ r.description || '暂无说明' }}</p></div><button class="danger" @click="remove(r.id)">删除</button></div></div>
    <div v-if="editor" class="modal" @click.self="editor = false"><form class="modal-card" @submit.prevent="save"><div class="modal-head"><div><p class="eyebrow">RELATION</p><h2>新建人物关系</h2></div><button type="button" @click="editor = false">×</button></div><label>人物 A<select v-model.number="form.source_id" required><option :value="0" disabled>请选择</option><option v-for="o in officials" :key="o.id" :value="o.id">{{ o.name }}</option></select></label><label>关系类型<input v-model="form.relation_type" required placeholder="同事 / 上下级 / 同乡 / 校友" /></label><label>人物 B<select v-model.number="form.target_id" required><option :value="0" disabled>请选择</option><option v-for="o in officials" :key="o.id" :value="o.id">{{ o.name }}</option></select></label><label>关系说明<textarea v-model="form.description" rows="3"></textarea></label><div class="modal-actions"><button type="button" @click="editor = false">取消</button><button class="primary">保存关系</button></div></form></div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { showToast } from '@/composables/toast'
import { createRelationApi, deleteRelationApi, listOfficialsApi, listRelationsApi, type Official, type Relation } from '@/api/officials'
const relations = ref<Relation[]>([]); const officials = ref<Official[]>([]); const editor = ref(false); const form = reactive({ source_id: 0, target_id: 0, relation_type: '', description: '' })
onMounted(load); async function load() { const [r, o] = await Promise.all([listRelationsApi(), listOfficialsApi({ page_size: 100 })]); relations.value = r; officials.value = o.items }
function nodeStyle(i: number) { const count = Math.max(officials.value.slice(0, 12).length, 1); const angle = (i / count) * Math.PI * 2; return { left: `${50 + Math.cos(angle) * 36}%`, top: `${50 + Math.sin(angle) * 36}%` } }
async function save() { await createRelationApi(form); editor.value = false; Object.assign(form, { source_id: 0, target_id: 0, relation_type: '', description: '' }); showToast('关系已创建'); await load() }
async function remove(id: number) { if (!confirm('确认删除这条关系？')) return; await deleteRelationApi(id); await load() }
</script>
