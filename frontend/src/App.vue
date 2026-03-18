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

      <section class="sidebar-section">
        <p class="sidebar-title">当前状态</p>
        <article class="sidebar-card active">
          <strong>{{ statusTitle }}</strong>
          <span>{{ shortStatusText }}</span>
        </article>
        <article class="sidebar-card" :class="'health-' + healthStatus">
          <strong>
            <span class="health-dot"></span>
            后端服务
          </strong>
          <span v-if="healthStatus === 'checking'">检测中...</span>
          <span v-else-if="healthStatus === 'online'">在线 · {{ healthInfo?.modelName || '未知模型' }}</span>
          <span v-else>离线或不可达</span>
        </article>
      </section>

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
          <strong>会话 #{{ pastSessions.length - idx }} · {{ session.messages.length }} 条消息</strong>
          <span class="history-preview">{{ session.preview }}</span>
          <span class="history-time">{{ session.time }}</span>
          <button class="delete-session-btn" @click="deleteSession(session, $event)">×</button>
        </article>
      </section>

    </aside>

    <section class="workspace">
      <header class="workspace-header">
        <div>
          <p class="eyebrow">Chat-style Workspace</p>
          <h2>Java To Cangjie</h2>
        </div>

        <div class="status-chip" :class="statusToneClass">
          <span class="status-dot"></span>
          <div>
            <strong>{{ statusTitle }}</strong>
            <span>{{ statusDescription }}</span>
          </div>
        </div>
      </header>

      <section class="conversation-stage" ref="stageRef">
        <!-- 查看历史会话时的提示横幅 -->
        <div v-if="isViewingHistory" class="history-banner">
          <span>当前查看的是历史会话（只读），无法追加转译</span>
          <button class="secondary-button banner-btn" @click="returnToCurrent">切换到最新会话</button>
        </div>

        <article class="message-row assistant-row intro-card">
          <div class="avatar assistant-avatar">AI</div>
          <div class="message-card assistant-card hero-card">
            <p class="message-role">系统助手</p>
            <h3>Java → Cangjie 代码转译工具</h3>
            <p>粘贴或导入 Java 代码，点击「发送转译请求」即可将其转译为仓颉语言。</p>
          </div>
        </article>

        <!-- 对话消息列表（当前会话或历史会话） -->
        <template v-for="item in displayedMessages" :key="item.id">
          <article class="message-row user-row">
            <div class="message-card user-card">
              <p class="message-role">用户输入 · {{ item.time }}</p>
              <div class="message-toolbar">
                <span>待转译 Java 代码</span>
                <span>{{ item.javaCode.length }} 字符</span>
              </div>
              <pre class="message-code" v-html="item.highlightedJava"></pre>
            </div>
            <div class="avatar user-avatar">你</div>
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
                  <button
                    class="secondary-button"
                    :disabled="!item.cangjieCode"
                    @click="copyCode(item)"
                  >{{ item.copyLabel }}</button>
                  <button
                    class="secondary-button"
                    :disabled="!item.cangjieCode"
                    @click="exportCode(item)"
                  >下载 .cj</button>
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

        <!-- 发送中的 loading 占位泡 -->
        <template v-if="loading">
          <article class="message-row user-row">
            <div class="message-card user-card">
              <p class="message-role">用户输入</p>
              <pre class="message-code" v-html="highlightedJavaCode"></pre>
            </div>
            <div class="avatar user-avatar">你</div>
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { checkHealth, convertJavaToCangjie } from './api/convert'
import { highlightCangjie, highlightJava } from './utils/highlight'

const javaCode = ref('public class Hello {\n    public static void main(String[] args) {\n        System.out.println("hello");\n    }\n}')
const loading = ref(false)
const requestError = ref('')
const status = ref('idle')
const stageRef = ref(null)
const textareaRef = ref(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  const maxH = window.innerHeight * 0.6
  el.style.height = Math.min(el.scrollHeight, maxH) + 'px'
}

watch(javaCode, () => nextTick(autoResize))

// 健康状态
const healthStatus = ref('checking') // 'checking' | 'online' | 'offline'
const healthInfo = ref(null)

// 当前会话的消息列表（持续追加，不会因每次发送而重置）
const currentMessages = ref([])
// 历史会话列表（每次点「新建会话」才将当前会话保存到此）
const pastSessions = ref([])
// 正在查看的历史会话（null = 查看当前会话）
const viewingSession = ref(null)

let nextMsgId = 1
let nextSessionId = 1

// ── localStorage 持久化 ──────────────────────────────────────
const STORAGE_KEY = 'java2cangjie_sessions'

function saveSessions() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      currentMessages: currentMessages.value,
      pastSessions: pastSessions.value,
      nextMsgId,
      nextSessionId
    }))
  } catch {
    // localStorage 额度不足时静默失败
  }
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
  } catch {
    // JSON 解析错误时直接忽略
  }
}

// ── 健康检测 ────────────────────────────────────────────────
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
  nextTick(autoResize)
})

// 当前对话区实际展示的消息
const displayedMessages = computed(() =>
  viewingSession.value ? viewingSession.value.messages : currentMessages.value
)

const isViewingHistory = computed(() => viewingSession.value !== null)

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const validationMessage = computed(() => {
  if (!javaCode.value.trim()) return '请输入需要转译的 Java 代码。'
  if (javaCode.value.length > 20000) return '输入代码过长，请先缩小到 20000 字符以内。'
  return ''
})

const canSubmit = computed(() => !validationMessage.value)

const highlightedJavaCode = computed(() => highlightJava(javaCode.value.trim() || '// 等待输入 Java 代码'))

const statusToneClass = computed(() => `status-${status.value}`)

const shortStatusText = computed(() => {
  switch (status.value) {
    case 'validating': return '输入待修正'
    case 'submitting': return '正在调用后端'
    case 'success':    return '输出已生成'
    case 'error':      return '请检查后端响应'
    default:           return '等待发送'
  }
})

const statusTitle = computed(() => {
  switch (status.value) {
    case 'validating': return '待修正'
    case 'submitting': return '请求进行中'
    case 'success':    return '转换完成'
    case 'error':      return '请求失败'
    default:           return '系统待命'
  }
})

const statusDescription = computed(() => {
  switch (status.value) {
    case 'validating': return validationMessage.value
    case 'submitting': return '前端已提交请求，正在等待后端返回结果。'
    case 'success':    return '结果已返回，可以直接检查输出或复制内容。'
    case 'error':      return requestError.value || '请求失败，请稍后重试。'
    default:           return '可以直接输入 Java 代码并开始转换。'
  }
})

async function submit() {
  if (!canSubmit.value) {
    requestError.value = validationMessage.value
    status.value = 'validating'
    return
  }

  // 历史会话只读，无法追加
  if (isViewingHistory.value) return

  loading.value = true
  requestError.value = ''
  status.value = 'submitting'

  const currentCode = javaCode.value.trim()
  const now = new Date()

  await nextTick()
  scrollToBottom()

  try {
    const data = await convertJavaToCangjie({
      javaCode: currentCode
    })

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
    status.value = 'success'
  } catch (error) {
    const msg = normalizeErrorMessage(error)
    requestError.value = msg
    status.value = 'error'

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

// 下载仓颉结果为 .cj 文件
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

// 从本地文件导入 Java 代码
function importFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    javaCode.value = e.target.result
  }
  reader.readAsText(file)
  // 重置 input，使相同文件可再次触发
  event.target.value = ''
}

// 点击侧边栏历史会话，进入只读浏览
function loadSession(session) {
  viewingSession.value = session
  nextTick(scrollToBottom)
}

// 返回当前会话
function returnToCurrent() {
  viewingSession.value = null
  nextTick(scrollToBottom)
}

// 删除单条历史会话
function deleteSession(session, event) {
  event.stopPropagation()
  pastSessions.value = pastSessions.value.filter(s => s.id !== session.id)
  if (viewingSession.value?.id === session.id) {
    viewingSession.value = null
  }
  saveSessions()
}

// 清空所有历史会话
function clearAllSessions() {
  if (!confirm('确认清空所有历史会话？此操作不可撤销。')) return
  pastSessions.value = []
  viewingSession.value = null
  saveSessions()
}

// 新建会话：将当前会话存入历史，开启空白会话
function newSession() {
  if (currentMessages.value.length > 0) {
    const firstMsg = currentMessages.value[0]
    pastSessions.value.unshift({
      id: nextSessionId++,
      messages: [...currentMessages.value],
      preview: firstMsg.javaCode.slice(0, 40).replace(/\n/g, ' ') + (firstMsg.javaCode.length > 40 ? '…' : ''),
      messageCount: currentMessages.value.length,
      time: firstMsg.time
    })
  }
  currentMessages.value = []
  viewingSession.value = null
  status.value = 'idle'
  requestError.value = ''
  saveSessions()
}

function scrollToBottom() {
  if (stageRef.value) {
    stageRef.value.scrollTop = stageRef.value.scrollHeight
  }
}

function normalizeErrorMessage(error) {
  if (error?.code === 'ECONNABORTED') return '请求超时，请稍后重试。'
  return error?.response?.data?.message || error?.response?.data?.detail || error?.message || '请求失败，请稍后重试。'
}
</script>
