import axios from 'axios'

export async function convertJavaToCangjie(payload) {
  const { data } = await axios.post('/api/convert', payload)
  return data
}
