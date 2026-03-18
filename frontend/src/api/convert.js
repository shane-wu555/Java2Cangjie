import axios from 'axios'

const client = axios.create({
  timeout: 60000
})

export async function convertJavaToCangjie(payload) {
  const { data } = await client.post('/api/convert', payload)
  return data
}

export async function checkHealth() {
  const { data } = await client.get('/api/health', { timeout: 5000 })
  return data
}
