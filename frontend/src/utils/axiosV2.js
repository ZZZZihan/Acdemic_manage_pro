import axios from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = import.meta.env.VITE_API_V2_URL || ''

const instance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    const message = error?.response?.data?.message
    const fallback = error?.message || '请求失败'
    ElMessage.error(detail || message || fallback)
    return Promise.reject(error)
  }
)

export default instance
