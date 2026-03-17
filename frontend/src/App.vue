<template>
  <main class="container">
    <h1>Java → 仓颉 代码转译</h1>
    <p class="desc">输入 Java 代码后，系统会调用量化模型生成仓颉代码。</p>

    <section class="panel">
      <label>Java 代码</label>
      <textarea v-model="javaCode" rows="12" placeholder="请输入 Java 代码"></textarea>

      <div class="row">
        <label>
          max_new_tokens
          <input type="number" v-model.number="maxNewTokens" min="16" max="4096" />
        </label>
        <label>
          temperature
          <input type="number" v-model.number="temperature" min="0" max="2" step="0.1" />
        </label>
      </div>

      <button :disabled="loading" @click="submit">
        {{ loading ? '转换中...' : '开始转换' }}
      </button>
    </section>

    <section class="panel">
      <h2>仓颉代码输出</h2>
      <pre>{{ result || '暂无结果' }}</pre>
      <small v-if="meta">模型: {{ meta.modelName }} | 量化: {{ meta.quantization }} | 延迟: {{ meta.latencyMs }}ms</small>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { convertJavaToCangjie } from './api/convert'

const javaCode = ref('public class Hello {\n    public static void main(String[] args) {\n        System.out.println("hello");\n    }\n}')
const maxNewTokens = ref(512)
const temperature = ref(0.1)
const loading = ref(false)
const result = ref('')
const meta = ref(null)

async function submit() {
  loading.value = true
  result.value = ''
  try {
    const data = await convertJavaToCangjie({
      javaCode: javaCode.value,
      maxNewTokens: maxNewTokens.value,
      temperature: temperature.value
    })
    result.value = data.cangjieCode
    meta.value = data
  } catch (error) {
    result.value = `请求失败: ${error?.response?.data?.message || error.message}`
  } finally {
    loading.value = false
  }
}
</script>
