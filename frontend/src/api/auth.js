import axios from 'axios'

const client = axios.create({ timeout: 10000 })

export async function login(username, password) {
  const { data } = await client.post('/api/auth/login', { username, password })
  return data // { token, username }
}

export async function register(username, password) {
  const { data } = await client.post('/api/auth/register', { username, password })
  return data // { token, username }
}

export function saveAuth(token, username) {
  localStorage.setItem('java2cangjie_token', token)
  localStorage.setItem('java2cangjie_user', username)
}

export function clearAuth() {
  localStorage.removeItem('java2cangjie_token')
  localStorage.removeItem('java2cangjie_user')
}

export function getToken() {
  return localStorage.getItem('java2cangjie_token')
}

export function getUser() {
  return localStorage.getItem('java2cangjie_user')
}
