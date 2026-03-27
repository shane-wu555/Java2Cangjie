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
      <p class="auth-tagline">Java 代码转译为仓颉语言的智能平台</p>

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
          <span class="auth-feature-icon">🎯</span>
          <div class="auth-feature-text">
            <strong>高精度输出</strong>
            <span>LoRA 微调，专注 Java / 仓颉语法对齐</span>
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
        <h2 class="auth-title">创建账户</h2>
        <p class="auth-subtitle">注册后即可开始使用代码转译功能</p>

        <form @submit.prevent="handleRegister" novalidate>
          <div class="field-group">
            <label class="field-label" for="username">用户名</label>
            <input
              id="username"
              v-model="username"
              class="field-input"
              :class="{ 'field-error': errors.username }"
              type="text"
              placeholder="3-20 个字符"
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
                placeholder="至少 6 个字符"
                autocomplete="new-password"
              />
              <button type="button" class="toggle-pw" @click="showPassword = !showPassword">
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
            <p v-if="errors.password" class="field-error-text">{{ errors.password }}</p>
          </div>

          <div class="field-group">
            <label class="field-label" for="confirm">确认密码</label>
            <input
              id="confirm"
              v-model="confirm"
              class="field-input"
              :class="{ 'field-error': errors.confirm }"
              :type="showPassword ? 'text' : 'password'"
              placeholder="再次输入密码"
              autocomplete="new-password"
            />
            <p v-if="errors.confirm" class="field-error-text">{{ errors.confirm }}</p>
          </div>

          <p v-if="serverError" class="server-error">{{ serverError }}</p>

          <button class="auth-submit-btn" type="submit" :disabled="submitting">
            {{ submitting ? '注册中...' : '注册' }}
          </button>
        </form>

        <p class="auth-switch">
          已有账户？
          <router-link to="/login" class="auth-link">返回登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register, saveAuth } from '../api/auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const confirm = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const serverError = ref('')
const errors = ref({})

function validate() {
  const e = {}
  if (!username.value.trim() || username.value.trim().length < 3) e.username = '用户名至少 3 个字符'
  if (username.value.trim().length > 20) e.username = '用户名不超过 20 个字符'
  if (!password.value || password.value.length < 6) e.password = '密码至少 6 个字符'
  if (password.value !== confirm.value) e.confirm = '两次密码输入不一致'
  errors.value = e
  return Object.keys(e).length === 0
}

async function handleRegister() {
  serverError.value = ''
  if (!validate()) return
  submitting.value = true
  try {
    const data = await register(username.value.trim(), password.value)
    saveAuth(data.token, data.username)
    router.push('/')
  } catch (err) {
    serverError.value = err?.response?.data?.message || '注册失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>
