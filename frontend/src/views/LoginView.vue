<template>
  <div class="auth-shell">
    <div class="auth-panel">
      <div class="auth-brand">
        <div class="brand-mark">JC</div>
        <div>
          <p class="eyebrow">Translation Studio</p>
          <h1>Java2Cangjie</h1>
        </div>
      </div>
      <p class="auth-tagline">Java 代码  仓颉语言的智能转译平台</p>

      <div class="auth-features">
        <div class="auth-feature-item">
          <span class="auth-feature-icon">⚡</span>
          <div class="auth-feature-text">
            <strong>智能转译</strong>
            <span>基于微调大语言模型，精准理解 Java 语义</span>
          </div>
        </div>
        <div class="auth-feature-item">
          <span class="auth-feature-icon">💬</span>
          <div class="auth-feature-text">
            <strong>对话式工作台</strong>
            <span>历史会话持久化，随时回顾每次转译过程</span>
          </div>
        </div>
        <div class="auth-feature-item">
          <span class="auth-feature-icon">🔒</span>
          <div class="auth-feature-text">
            <strong>账户隔离</strong>
            <span>独立的历史记录，数据不互相干扰</span>
          </div>
        </div>
      </div>

      <div class="auth-code-preview">
        <span class="cc">// Java → 仓颉</span>
        <br/>
        <span class="ck">public class</span> <span class="ct">Hello</span> {
        <br/>
        &nbsp;&nbsp;<span class="ck">func</span> <span class="ct">main</span>() {
        <br/>
        &nbsp;&nbsp;&nbsp;&nbsp;println(<span class="cs">"Hello, 仓颉!"</span>)
        <br/>
        &nbsp;&nbsp;}
        <br/>
        }
      </div>
    </div>

    <div class="auth-form-panel">
      <div class="auth-form-card">
        <h2 class="auth-title">欢迎回来</h2>
        <p class="auth-subtitle">登录以继续使用转译工具</p>

        <form @submit.prevent="handleLogin" novalidate>
          <div class="field-group">
            <label class="field-label" for="username">用户名</label>
            <input
              id="username"
              v-model="username"
              class="field-input"
              :class="{ 'field-error': errors.username }"
              type="text"
              placeholder="输入用户名"
              autocomplete="username"
            />
            <p v-if="errors.username" class="field-error-text">{{ errors.username }}</p>
          </div>

          <div class="field-group">
            <label class="field-label" for="password">密码</label>
            <div class="field-input-wrap">
              <input
                id="password"
                v-model="password"
                class="field-input"
                :class="{ 'field-error': errors.password }"
                :type="showPassword ? 'text' : 'password'"
                placeholder="输入密码"
                autocomplete="current-password"
              />
              <button type="button" class="toggle-pw" @click="showPassword = !showPassword">
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
            <p v-if="errors.password" class="field-error-text">{{ errors.password }}</p>
          </div>

          <p v-if="serverError" class="server-error">{{ serverError }}</p>

          <button class="auth-submit-btn" type="submit" :disabled="submitting">
            {{ submitting ? '登录中...' : '登录' }}
          </button>
        </form>

        <p class="auth-switch">
          还没有账户？
          <router-link to="/register" class="auth-link">立即注册</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, saveAuth } from '../api/auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const serverError = ref('')
const errors = ref({})

function validate() {
  const e = {}
  if (!username.value.trim()) e.username = '请输入用户名'
  if (!password.value) e.password = '请输入密码'
  errors.value = e
  return Object.keys(e).length === 0
}

async function handleLogin() {
  serverError.value = ''
  if (!validate()) return
  submitting.value = true
  try {
    const data = await login(username.value.trim(), password.value)
    saveAuth(data.token, data.username)
    router.push('/')
  } catch (err) {
    serverError.value = err?.response?.data?.message || '登录失败，请检查用户名和密码。'
  } finally {
    submitting.value = false
  }
}
</script>
