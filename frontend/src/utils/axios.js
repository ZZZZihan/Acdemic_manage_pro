import axios from 'axios'
import { ElMessage } from 'element-plus'
import { authSession, sessionEpoch, updateAuthData, clearAuthData } from './authSession'

export const authTransport = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
})
let refreshFlight = null

function invalidateSession() {
  const active = !!(authSession.token || authSession.refreshToken)
  clearAuthData()
  if (active) window.dispatchEvent(new Event('auth:expired'))
}

export function refreshAccessToken() {
  const epoch = sessionEpoch()
  if (refreshFlight?.epoch === epoch) return refreshFlight.promise
  const refreshToken = authSession.refreshToken
  if (!refreshToken) return Promise.reject(new Error('请重新登录'))
  const flight = { epoch, promise: null }
  flight.promise = authTransport.post('/api/v1/auth/refresh', {}, {
    headers: { Authorization: `Bearer ${refreshToken}` },
  }).then((response) => {
    if (epoch !== sessionEpoch()) throw new Error('登录会话已经改变')
    if (!response.data.access_token) throw new Error('刷新响应缺少令牌')
    updateAuthData(response.data)
    return response
  }).catch((error) => {
    // Network/server errors do not prove that credentials are invalid.
    if (epoch === sessionEpoch() && [401, 403, 422].includes(error.response?.status)) invalidateSession()
    throw error
  }).finally(() => {
    if (refreshFlight === flight) refreshFlight = null
  })
  refreshFlight = flight
  return flight.promise
}

export function createAuthenticatedClient(baseURL, timeout = 60000) {
  const client = axios.create({ baseURL, timeout })
  client.interceptors.request.use((config) => {
    if (!config.skipAuth) {
      if (config._sessionEpoch !== undefined && config._sessionEpoch !== sessionEpoch()) {
        return Promise.reject(new Error('登录会话已经改变，已取消旧请求'))
      }
      config._sessionEpoch = sessionEpoch()
      config._accessToken = authSession.token
      if (authSession.token) config.headers.Authorization = `Bearer ${authSession.token}`
      else delete config.headers.Authorization
    }
    return config
  })
  client.interceptors.response.use((response) => response, async (error) => {
    const config = error.config || {}
    const status = error.response?.status
    const payload = error.response?.data || {}
    if (status === 401 && !config.skipAuth && config._sessionEpoch === sessionEpoch()) {
      if (!config._retry && payload.code === 'token_expired' && authSession.refreshToken) {
        config._retry = true
        try {
          // A concurrent request may already have refreshed this session.
          if (config._accessToken === authSession.token) await refreshAccessToken()
          return client(config)
        } catch (refreshError) {
          return Promise.reject(refreshError)
        }
      }
      invalidateSession()
    }
    if (!config.silent) {
      const message = payload.message || payload.msg || payload.detail
      ElMessage.error(typeof message === 'string' ? message :
        (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '请求失败，请稍后重试'))
    }
    return Promise.reject(error)
  })
  return client
}

export default createAuthenticatedClient(import.meta.env.VITE_API_URL || '')
