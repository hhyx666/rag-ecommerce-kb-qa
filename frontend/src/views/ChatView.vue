<template>
  <div class="chat-layout">
    <!-- 左侧:会话列表 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="app-name">🛒 电商知识库问答</span>
        <el-button type="primary" circle size="small" title="新建会话" @click="createSession">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId }"
          @click="openSession(s)"
        >
          <span class="session-title">{{ s.title }}</span>
          <el-dropdown trigger="click" @command="(cmd) => onSessionCmd(cmd, s)">
            <el-icon class="more" @click.stop><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除会话</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-empty v-if="!sessions.length" description="暂无会话" :image-size="60" />
      </div>
      <div class="sidebar-footer">
        <el-dropdown @command="onUserCmd">
          <span class="user-chip">
            👤 {{ user?.username }}
            <el-tag v-if="user?.role === 'admin'" size="small" type="warning">管理员</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="user?.role === 'admin'" command="admin">📚 知识库管理</el-dropdown-item>
              <el-dropdown-item command="profile">🔑 修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>🚪 退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 右侧:聊天区 -->
    <main class="chat-main">
      <div ref="msgListEl" class="message-list">
        <div v-if="!messages.length && !streaming" class="welcome">
          <h2>👋 你好,我是电商智能客服</h2>
          <p>我可以回答商品参数、价格、售后政策等问题,回答会引用知识库资料。</p>
          <p>试试问我:</p>
          <div class="suggestions">
            <el-tag v-for="q in suggestions" :key="q" class="sug" @click="quickAsk(q)">{{ q }}</el-tag>
          </div>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
          <div class="bubble">
            <div v-if="m.role === 'assistant'" class="md-body" v-html="renderMd(m.content)"></div>
            <div v-else class="plain-body">{{ m.content }}</div>
            <div v-if="m.citations?.length" class="citations">
              <el-collapse>
                <el-collapse-item :title="`📎 引用知识库片段 (${m.citations.length})`">
                  <div v-for="c in m.citations" :key="c.index" class="citation-item">
                    <div class="citation-head">
                      <b>[{{ c.index }}]</b> 来源:{{ c.source }} · 相关度 {{ (c.score * 100).toFixed(1) }}%
                    </div>
                    <div class="citation-content">{{ c.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
        <div v-if="streaming" class="msg-row assistant">
          <div class="bubble">
            <div class="md-body" v-html="renderMd(streamText)"></div><span class="cursor">▌</span>
            <div v-if="streamCitations?.length" class="citations">
              <el-collapse>
                <el-collapse-item :title="`📎 引用知识库片段 (${streamCitations.length})`">
                  <div v-for="c in streamCitations" :key="c.index" class="citation-item">
                    <div class="citation-head">
                      <b>[{{ c.index }}]</b> 来源:{{ c.source }} · 相关度 {{ (c.score * 100).toFixed(1) }}%
                    </div>
                    <div class="citation-content">{{ c.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>
      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="请输入问题,Enter 发送,Shift+Enter 换行"
          :disabled="streaming"
          @keydown.enter.exact.prevent="send"
        />
        <el-button type="primary" class="send-btn" :loading="streaming" :disabled="!question.trim()" @click="send">
          {{ streaming ? '回答中…' : '发送' }}
        </el-button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, MoreFilled } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const user = computed(() => auth.user)

const md = new MarkdownIt({ breaks: true, linkify: true })

const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const question = ref('')
const streaming = ref(false)
const streamText = ref('')
const streamCitations = ref(null)
const msgListEl = ref(null)

const suggestions = [
  '星云X1 Pro手机有什么亮点?',
  '飞翼F16游戏本多少钱?',
  '买电视支持上门安装吗?',
  '手机激活了还能退货吗?',
]

function renderMd(text) {
  return md.render(text || '')
}

function scrollBottom() {
  nextTick(() => {
    if (msgListEl.value) msgListEl.value.scrollTop = msgListEl.value.scrollHeight
  })
}

async function loadSessions() {
  const { data } = await api.get('/sessions')
  sessions.value = data
}

async function createSession() {
  const { data } = await api.post('/sessions')
  sessions.value.unshift(data)
  currentSessionId.value = data.id
  messages.value = []
}

async function openSession(s) {
  if (streaming.value) return
  currentSessionId.value = s.id
  const { data } = await api.get(`/sessions/${s.id}/messages`)
  messages.value = data
  scrollBottom()
}

async function onSessionCmd(cmd, s) {
  if (cmd === 'rename') {
    const { value } = await ElMessageBox.prompt('输入新的会话标题', '重命名', {
      inputValue: s.title,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    if (value) {
      await api.patch(`/sessions/${s.id}`, { title: value })
      await loadSessions()
    }
  } else if (cmd === 'delete') {
    await ElMessageBox.confirm(`删除会话「${s.title}」及其全部消息?`, '确认删除', { type: 'warning' })
    await api.delete(`/sessions/${s.id}`)
    if (currentSessionId.value === s.id) {
      currentSessionId.value = null
      messages.value = []
    }
    await loadSessions()
  }
}

function onUserCmd(cmd) {
  if (cmd === 'admin') router.push('/admin')
  else if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

function quickAsk(q) {
  question.value = q
  send()
}

async function send() {
  const q = question.value.trim()
  if (!q || streaming.value) return
  question.value = ''

  // 没有会话时自动创建一个
  if (!currentSessionId.value) await createSession()

  messages.value.push({ role: 'user', content: q })
  streaming.value = true
  streamText.value = ''
  streamCitations.value = null
  scrollBottom()

  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${auth.token}`,
    },
    body: JSON.stringify({ session_id: currentSessionId.value, question: q }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    ElMessage.error(err.detail || '请求失败')
    streaming.value = false
    return
  }

  // 解析 SSE 流
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  let citations = null
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop()
    let event = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        event = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const payload = line.slice(6)
        try {
          const data = JSON.parse(payload)
          if (event === 'citations') {
            citations = data
            streamCitations.value = data
          } else if (event === 'delta') {
            streamText.value += data
          } else if (event === 'error') {
            streamText.value += `\n\n> ⚠️ ${data}`
          }
        } catch (e) {
          /* 忽略解析失败的行 */
        }
      }
    }
    scrollBottom()
  }

  // 收尾:落库当前回答,刷新会话列表(标题/时间会变)
  messages.value.push({ role: 'assistant', content: streamText.value, citations })
  streaming.value = false
  streamText.value = ''
  streamCitations.value = null
  loadSessions()
  scrollBottom()
}

// 登录用户发生变化时:清空界面状态,重新加载新用户的会话
// 防止上一个账号的对话残留显示
watch(
  () => auth.user?.id,
  async (newId, oldId) => {
    if (!newId || newId === oldId) return
    currentSessionId.value = null
    messages.value = []
    sessions.value = []
    await loadSessions()
    if (sessions.value.length) openSession(sessions.value[0])
  },
)

onMounted(async () => {
  // 以服务端为准校验当前登录身份,防止本地缓存令牌与界面错位
  try {
    const { data } = await api.get('/auth/me')
    auth.user = data
  } catch (e) {
    return // 令牌无效时拦截器已跳转登录页
  }
  await loadSessions()
  if (sessions.value.length) openSession(sessions.value[0])
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
}
.sidebar {
  width: 260px;
  background: #1e293b;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  border-bottom: 1px solid #334155;
}
.app-name {
  font-size: 15px;
  font-weight: 600;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #cbd5e1;
  margin-bottom: 4px;
}
.session-item:hover {
  background: #334155;
}
.session-item.active {
  background: #3b82f6;
  color: #fff;
}
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.more {
  opacity: 0.5;
}
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #334155;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 13px;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
}
.welcome {
  text-align: center;
  margin-top: 80px;
  color: #64748b;
}
.welcome h2 {
  margin-bottom: 12px;
  color: #334155;
}
.suggestions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}
.sug {
  cursor: pointer;
  padding: 8px 14px;
  height: auto;
}
.msg-row {
  display: flex;
  margin-bottom: 16px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.bubble {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
}
.user .bubble {
  background: #3b82f6;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.assistant .bubble {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  border-bottom-left-radius: 4px;
}
.md-body :deep(p) {
  margin: 6px 0;
}
.md-body :deep(ul),
.md-body :deep(ol) {
  padding-left: 22px;
}
.md-body :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}
.cursor {
  animation: blink 1s infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
.citations {
  margin-top: 10px;
  background: #f8fafc;
  border-radius: 8px;
}
.citation-item {
  padding: 8px 0;
  border-bottom: 1px dashed #e2e8f0;
  font-size: 12px;
}
.citation-head {
  color: #2563eb;
  margin-bottom: 4px;
}
.citation-content {
  color: #64748b;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}
.input-area {
  display: flex;
  gap: 10px;
  padding: 16px 40px 20px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  align-items: flex-end;
}
.send-btn {
  height: 74px;
  width: 100px;
}
</style>
