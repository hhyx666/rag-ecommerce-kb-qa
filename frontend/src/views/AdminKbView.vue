<template>
  <div class="admin-layout">
    <!-- 左侧:知识库列表 -->
    <aside class="kb-sidebar">
      <div class="kb-header">
        <span>📚 知识库管理</span>
        <el-button type="primary" circle size="small" title="新建知识库" @click="createKb">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="kb-list">
        <div
          v-for="kb in kbs"
          :key="kb.id"
          class="kb-item"
          :class="{ active: kb.id === currentKbId }"
          @click="selectKb(kb)"
        >
          <div class="kb-name">{{ kb.name }}</div>
          <div class="kb-desc">{{ kb.description || '暂无描述' }}</div>
        </div>
        <el-empty v-if="!kbs.length" description="暂无知识库" :image-size="60" />
      </div>
      <div class="kb-footer">
        <el-button size="small" @click="$router.push('/')">← 返回问答</el-button>
        <el-button size="small" type="danger" plain :disabled="!currentKbId" @click="deleteKb">
          删除知识库
        </el-button>
      </div>
    </aside>

    <!-- 右侧:内容 -->
    <main class="kb-main">
      <template v-if="currentKbId">
        <el-tabs v-model="tab">
          <!-- 文档管理 -->
          <el-tab-pane label="文档管理" name="docs">
            <el-upload
              class="upload-area"
              drag
              multiple
              :http-request="uploadDoc"
              :show-file-list="false"
              accept=".pdf,.docx,.xlsx,.txt,.md"
            >
              <div class="upload-inner">
                <p class="upload-icon">📄</p>
                <p>点击或拖拽文件上传(支持 PDF / Word / Excel / TXT / Markdown)</p>
              </div>
            </el-upload>
            <el-table :data="docs" stripe style="margin-top: 16px" v-loading="loadingDocs">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'ready' ? 'success' : row.status === 'error' ? 'danger' : 'info'">
                    {{ row.status === 'ready' ? '已就绪' : row.status === 'error' ? '失败' : '处理中' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="chunk_count" label="切片数" width="90" />
              <el-table-column prop="created_at" label="上传时间" width="180">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" @click="previewChunks(row)">切片预览</el-button>
                  <el-button size="small" type="danger" plain @click="deleteDoc(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 检索调试 -->
          <el-tab-pane label="检索调试" name="debug">
            <div class="debug-bar">
              <el-input v-model="debugQuery" placeholder="输入问题,查看系统检索到了哪些片段(不经过大模型)" clearable
                        @keydown.enter="debugSearch" />
              <el-button type="primary" @click="debugSearch" :loading="debugLoading">检索</el-button>
            </div>
            <el-empty v-if="!debugResults.length && !debugLoading" description="输入问题试试,例如:空调安装收费吗" />
            <div v-for="r in debugResults" :key="r.score + r.source" class="debug-item">
              <div class="debug-head">
                来源:{{ r.source }} · 得分 <b>{{ r.score }}</b>
              </div>
              <div class="debug-content">{{ r.content }}</div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
      <el-empty v-else description="请先选择或创建一个知识库" style="margin-top: 100px" />
    </main>

    <!-- 切片预览弹窗 -->
    <el-dialog v-model="chunkDialog" :title="`切片预览:${chunkDoc?.filename}`" width="70%" top="5vh">
      <div v-for="c in chunkList" :key="c.index" class="chunk-block">
        <div class="chunk-index">第 {{ c.index + 1 }} 片</div>
        <div class="chunk-text">{{ c.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../api'

const kbs = ref([])
const currentKbId = ref(null)
const tab = ref('docs')
const docs = ref([])
const loadingDocs = ref(false)
const debugQuery = ref('')
const debugResults = ref([])
const debugLoading = ref(false)
const chunkDialog = ref(false)
const chunkDoc = ref(null)
const chunkList = ref([])

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

async function loadKbs() {
  const { data } = await api.get('/kb')
  kbs.value = data
  if (data.length && !currentKbId.value) selectKb(data[0])
}

function selectKb(kb) {
  currentKbId.value = kb.id
  loadDocs()
}

async function createKb() {
  const { value } = await ElMessageBox.prompt('输入知识库名称', '新建知识库', {
    confirmButtonText: '创建',
    cancelButtonText: '取消',
  })
  if (!value) return
  await api.post('/kb', { name: value, description: '' })
  ElMessage.success('知识库已创建')
  await loadKbs()
}

async function deleteKb() {
  const kb = kbs.value.find((k) => k.id === currentKbId.value)
  await ElMessageBox.confirm(`删除知识库「${kb.name}」?里面所有文档和向量都会被删除!`, '危险操作', {
    type: 'error',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  })
  await api.delete(`/kb/${currentKbId.value}`)
  ElMessage.success('知识库已删除')
  currentKbId.value = null
  docs.value = []
  await loadKbs()
}

async function loadDocs() {
  if (!currentKbId.value) return
  loadingDocs.value = true
  try {
    const { data } = await api.get(`/kb/${currentKbId.value}/documents`)
    docs.value = data
  } finally {
    loadingDocs.value = false
  }
}

async function uploadDoc({ file }) {
  const form = new FormData()
  form.append('file', file)
  try {
    const { data } = await api.post(`/kb/${currentKbId.value}/upload`, form)
    ElMessage.success(`「${data.filename}」上传成功,切片 ${data.chunk_count} 片`)
    loadDocs()
  } catch (e) {
    /* 已统一提示 */
  }
}

async function deleteDoc(row) {
  await ElMessageBox.confirm(`删除文档「${row.filename}」?`, '确认删除', { type: 'warning' })
  await api.delete(`/kb/${currentKbId.value}/documents/${row.id}`)
  ElMessage.success('文档已删除')
  loadDocs()
}

async function previewChunks(row) {
  chunkDoc.value = row
  const { data } = await api.get(`/kb/documents/${row.id}/chunks`)
  chunkList.value = data
  chunkDialog.value = true
}

async function debugSearch() {
  if (!debugQuery.value.trim()) return
  debugLoading.value = true
  try {
    const { data } = await api.post(`/kb/${currentKbId.value}/debug-search`, {
      query: debugQuery.value,
    })
    debugResults.value = data
  } finally {
    debugLoading.value = false
  }
}

onMounted(loadKbs)
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100%;
}
.kb-sidebar {
  width: 280px;
  background: #1e293b;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  border-bottom: 1px solid #334155;
  font-size: 15px;
  font-weight: 600;
}
.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.kb-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
}
.kb-item:hover {
  background: #334155;
}
.kb-item.active {
  background: #3b82f6;
}
.kb-name {
  font-size: 14px;
  font-weight: 600;
}
.kb-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kb-footer {
  padding: 12px;
  border-top: 1px solid #334155;
  display: flex;
  justify-content: space-between;
}
.kb-main {
  flex: 1;
  padding: 20px 28px;
  overflow-y: auto;
  background: #f5f7fa;
}
.upload-area {
  width: 100%;
}
.upload-inner {
  padding: 12px;
  color: #64748b;
}
.upload-icon {
  font-size: 34px;
  margin: 4px;
}
.debug-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.debug-item {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.debug-head {
  color: #2563eb;
  font-size: 13px;
  margin-bottom: 6px;
}
.debug-content {
  font-size: 13px;
  color: #475569;
  white-space: pre-wrap;
}
.chunk-block {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 10px;
}
.chunk-index {
  color: #2563eb;
  font-size: 12px;
  margin-bottom: 4px;
}
.chunk-text {
  font-size: 13px;
  color: #334155;
  white-space: pre-wrap;
}
</style>
