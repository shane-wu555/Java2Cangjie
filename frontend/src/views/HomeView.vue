<template>
  <main class="app-shell">
    <aside class="app-sidebar">
      <div class="brand-block">
        <div class="brand-mark">JC</div>
        <div>
          <p class="eyebrow">Translation Studio</p>
          <h1>Java2Cangjie</h1>
        </div>
      </div>

      <button class="new-chat-button" type="button" @click="newSession">
        <span>+</span>
        <span>新建转译会话</span>
      </button>

      <div class="health-chip" :class="healthStatus">
        <span class="health-chip-dot"></span>
        <span v-if="healthStatus === 'checking'">检测中</span>
        <span v-else-if="healthStatus === 'online'">{{ healthInfo?.modelName || '在线' }}</span>
        <span v-else>服务离线</span>
      </div>

      <section class="sidebar-section history-section">
        <div class="sidebar-title-row">
          <p class="sidebar-title">历史会话 ({{ pastSessions.length }})</p>
          <button v-if="pastSessions.length > 0" class="clear-btn" @click="clearAllSessions">清空</button>
        </div>
        <article
          class="sidebar-card history-card"
          :class="{ active: !isViewingHistory }"
          @click="returnToCurrent"
        >
          <strong>当前会话</strong>
          <span>{{ currentMessages.length > 0 ? currentMessages.length + ' 条消息' : '暂无消息' }}</span>
        </article>
        <div v-if="pastSessions.length === 0" class="sidebar-empty">点击「新建转译会话」后，本次对话将存入历史</div>
        <article
          v-for="(session, idx) in pastSessions"
          :key="session.id"
          class="sidebar-card history-card"
          :class="{ active: viewingSession && viewingSession.id === session.id }"
          @click="loadSession(session)"
        >
          <strong>会话 #{{ pastSessions.length - idx }}  {{ session.messages.length }} 条消息</strong>
          <span class="history-preview">{{ session.preview }}</span>
          <span class="history-time">{{ session.time }}</span>
          <button class="delete-session-btn" @click="deleteSession(session, $event)"></button>
        </article>
      </section>

      <section class="sidebar-footer sidebar-section">
        <div class="user-info-card">
          <div class="user-avatar-small">{{ currentUser?.charAt(0)?.toUpperCase() || 'U' }}</div>
          <div class="user-info-text">
            <span class="user-name">{{ currentUser || '用户' }}</span>
            <span class="user-role">已登录</span>
          </div>
          <button class="logout-btn" title="退出登录" @click="logout"></button>
        </div>
      </section>
    </aside>

    <section class="workspace">
      <header class="workspace-header">
        <div>
          <p class="eyebrow">Chat-style Workspace</p>
          <h2>Java To Cangjie</h2>
        </div>
      </header>

      <section class="conversation-stage" ref="stageRef">
        <div v-if="isViewingHistory" class="history-banner">
          <span>当前查看的是历史会话（只读），无法追加转译</span>
          <button class="secondary-button banner-btn" @click="returnToCurrent">切换到最新会话</button>
        </div>

        <article class="message-row assistant-row intro-card">
          <div class="avatar assistant-avatar">AI</div>
          <div class="message-card assistant-card hero-card">
            <p class="message-role">系统助手</p>
            <h3>Java  Cangjie 代码转译工具</h3>
            <p>粘贴或导入 Java 代码，点击「发送转译请求」即可将其转译为仓颉语言。</p>
          </div>
        </article>

        <template v-for="item in displayedMessages" :key="item.id">
          <article class="message-row user-row">
            <div class="message-card user-card">
              <p class="message-role">用户输入  {{ item.time }}</p>
              <div class="message-toolbar">
                <span>待转译 Java 代码</span>
                <span>{{ item.javaCode.length }} 字符</span>
              </div>
              <pre class="message-code" v-html="item.highlightedJava"></pre>
            </div>
            <div class="avatar user-avatar">{{ currentUser?.charAt(0)?.toUpperCase() || 'U' }}</div>
          </article>

          <article class="message-row assistant-row">
            <div class="avatar assistant-avatar">AI</div>
            <div class="message-card assistant-card result-card">
              <div class="message-toolbar">
                <div>
                  <p class="message-role">转译结果</p>
                  <span class="toolbar-hint">仓颉代码已高亮显示</span>
                </div>
                <div class="toolbar-actions">
                  <button class="secondary-button" :disabled="!item.cangjieCode" @click="copyCode(item)">{{ item.copyLabel }}</button>
                  <button class="secondary-button" :disabled="!item.cangjieCode" @click="exportCode(item)">下载 .cj</button>
                </div>
              </div>

              <div v-if="item.loading" class="loading-state">
                <span class="loading-pulse"></span>
                <span>正在等待后端返回转译结果...</span>
              </div>
              <div v-else-if="item.error" class="error-panel">
                <strong>请求失败</strong>
                <p>{{ item.error }}</p>
              </div>
              <pre v-else-if="item.cangjieCode" class="message-code result-code" v-html="item.highlightedCangjie"></pre>
              <div v-else class="empty-panel">
                <strong>暂无输出</strong>
                <p>结果为空，请检查后端响应。</p>
              </div>
            </div>
          </article>
        </template>

        <template v-if="loading">
          <article class="message-row user-row">
            <div class="message-card user-card">
              <p class="message-role">用户输入</p>
              <pre class="message-code" v-html="highlightedJavaCode"></pre>
            </div>
            <div class="avatar user-avatar">{{ currentUser?.charAt(0)?.toUpperCase() || 'U' }}</div>
          </article>
          <article class="message-row assistant-row">
            <div class="avatar assistant-avatar">AI</div>
            <div class="message-card assistant-card result-card">
              <div class="loading-state">
                <span class="loading-pulse"></span>
                <span>正在等待后端返回转译结果...</span>
              </div>
            </div>
          </article>
        </template>
      </section>

      <section class="composer-shell">
        <div class="composer-card">
          <div class="composer-topbar">
            <label for="java-code">输入 Java 代码</label>
            <div class="composer-topbar-right">
              <label class="import-btn" title="从本地导入 .java 文件">
                导入 .java
                <input type="file" accept=".java,.txt" style="display:none" @change="importFile" />
              </label>
              <button class="send-button topbar-send" :disabled="!canSubmit || loading || isViewingHistory" @click="submit">
                {{ isViewingHistory ? '只读' : loading ? '发送中...' : '发送转译请求' }}
              </button>
            </div>
          </div>
          <textarea
            id="java-code"
            ref="textareaRef"
            v-model="javaCode"
            class="composer-textarea"
            :class="{ 'input-invalid': Boolean(validationMessage) }"
            placeholder="把要转译的 Java 代码粘贴到这里"
          ></textarea>
          <p v-if="validationMessage" class="error-text">{{ validationMessage }}</p>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { checkHealth, convertJavaToCangjie } from '../api/convert'
import { highlightCangjie, highlightJava } from '../utils/highlight'
import { clearAuth, getUser } from '../api/auth'

const router = useRouter()
const currentUser = ref(getUser())

const javaCode = ref('')
const loading = ref(false)
const stageRef = ref(null)
const textareaRef = ref(null)

const healthStatus = ref('checking')
const healthInfo = ref(null)

const currentMessages = ref([])
const pastSessions = ref([])
const viewingSession = ref(null)

let nextMsgId = 1
let nextSessionId = 1

const STORAGE_KEY = `java2cangjie_sessions_${currentUser.value || 'guest'}`

function saveSessions() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      currentMessages: currentMessages.value,
      pastSessions: pastSessions.value,
      nextMsgId,
      nextSessionId
    }))
  } catch { /* 静默失败 */ }
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const saved = JSON.parse(raw)
    currentMessages.value = saved.currentMessages || []
    pastSessions.value = saved.pastSessions || []
    nextMsgId = saved.nextMsgId || 1
    nextSessionId = saved.nextSessionId || 1
  } catch { /* 忽略 */ }
}

async function pollHealth() {
  try {
    const data = await checkHealth()
    healthStatus.value = 'online'
    healthInfo.value = data
  } catch {
    healthStatus.value = 'offline'
    healthInfo.value = null
  }
}

onMounted(() => {
  loadSessions()
  pollHealth()
  setInterval(pollHealth, 30000)
})

const displayedMessages = computed(() =>
  viewingSession.value ? viewingSession.value.messages : currentMessages.value
)

const isViewingHistory = computed(() => viewingSession.value !== null)

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const validationMessage = computed(() => {
  if (javaCode.value.length > 20000) return '输入代码过长，请先缩小到 20000 字符以内。'
  return ''
})

const canSubmit = computed(() => !validationMessage.value && javaCode.value.trim().length > 0)

const highlightedJavaCode = computed(() => highlightJava(javaCode.value.trim() || '// (等待输入)'))

async function submit() {
  if (!canSubmit.value || isViewingHistory.value) return
  loading.value = true
  const currentCode = javaCode.value.trim()
  const now = new Date()
  await nextTick()
  scrollToBottom()
  try {
    const data = await convertJavaToCangjie({ javaCode: currentCode })
    currentMessages.value.push({
      id: nextMsgId++,
      javaCode: currentCode,
      cangjieCode: data.cangjieCode || '',
      highlightedJava: highlightJava(currentCode),
      highlightedCangjie: highlightCangjie(data.cangjieCode || ''),
      meta: data,
      error: null,
      loading: false,
      copyLabel: '复制结果',
      time: formatTime(now)
    })
  } catch (error) {
    const msg = normalizeErrorMessage(error)
    currentMessages.value.push({
      id: nextMsgId++,
      javaCode: currentCode,
      cangjieCode: '',
      highlightedJava: highlightJava(currentCode),
      highlightedCangjie: '',
      meta: null,
      error: msg,
      loading: false,
      copyLabel: '复制结果',
      time: formatTime(now)
    })
  } finally {
    loading.value = false
    saveSessions()
    await nextTick()
    scrollToBottom()
  }
}

async function copyCode(item) {
  if (!item.cangjieCode) return
  try {
    await navigator.clipboard.writeText(item.cangjieCode)
    item.copyLabel = '已复制'
    setTimeout(() => { item.copyLabel = '复制结果' }, 2000)
  } catch {
    item.copyLabel = '复制失败'
    setTimeout(() => { item.copyLabel = '复制结果' }, 2000)
  }
}

function exportCode(item) {
  if (!item.cangjieCode) return
  const blob = new Blob([item.cangjieCode], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `converted_${item.id}.cj`
  a.click()
  URL.revokeObjectURL(url)
}

function importFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => { javaCode.value = e.target.result }
  reader.readAsText(file)
  event.target.value = ''
}

function loadSession(session) {
  viewingSession.value = session
  nextTick(scrollToBottom)
}

function returnToCurrent() {
  viewingSession.value = null
  nextTick(scrollToBottom)
}

function deleteSession(session, event) {
  event.stopPropagation()
  pastSessions.value = pastSessions.value.filter(s => s.id !== session.id)
  if (viewingSession.value?.id === session.id) viewingSession.value = null
  saveSessions()
}

function clearAllSessions() {
  if (!confirm('确认清空所有历史会话？此操作不可撤销。')) return
  pastSessions.value = []
  viewingSession.value = null
  saveSessions()
}

function newSession() {
  if (currentMessages.value.length > 0) {
    const firstMsg = currentMessages.value[0]
    pastSessions.value.unshift({
      id: nextSessionId++,
      messages: [...currentMessages.value],
      preview: firstMsg.javaCode.slice(0, 40).replace(/\n/g, ' ') + (firstMsg.javaCode.length > 40 ? '' : ''),
      messageCount: currentMessages.value.length,
      time: firstMsg.time
    })
  }
  currentMessages.value = []
  viewingSession.value = null
  saveSessions()
}

function scrollToBottom() {
  if (stageRef.value) stageRef.value.scrollTop = stageRef.value.scrollHeight
}

function normalizeErrorMessage(error) {
  if (error?.code === 'ECONNABORTED') return '请求超时，请稍后重试。'
  return error?.response?.data?.message || error?.response?.data?.detail || error?.message || '请求失败，请稍后重试。'
}

function logout() {
  clearAuth()
  router.push('/login')
}
</script>
