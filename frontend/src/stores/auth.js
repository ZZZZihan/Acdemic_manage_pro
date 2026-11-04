import { defineStore } from 'pinia'
import { computed, toRefs } from 'vue'
import api, { authTransport, refreshAccessToken } from '@/utils/axios'
import { authSession, sessionEpoch, startSession, updateAuthData, clearAuthData } from '@/utils/authSession'

export const useAuthStore = defineStore('auth', () => {
  const isLoggedIn = computed(() => !!authSession.token && authSession.validated)
  const isAdmin = computed(() => isLoggedIn.value && authSession.user?.is_administrator === true)
  let initialization = null

  async function login(credentials) {
    const response = await authTransport.post('/api/v1/auth/login', credentials)
    if (!response.data.access_token || !response.data.refresh_token || !response.data.user) {
      throw new Error('登录响应缺少必要数据')
    }
    startSession(response.data)
    return response.data
  }

  function register(data) {
    return authTransport.post('/api/v1/auth/register', data)
  }

  async function logout() {
    const credential = authSession.refreshToken || authSession.token
    clearAuthData()
    window.dispatchEvent(new Event('auth:expired'))
    if (credential) {
      try {
        await authTransport.post('/api/v1/auth/logout', {}, {
          headers: { Authorization: `Bearer ${credential}` },
        })
      } catch (error) {
        if (error.response?.status !== 401) throw error
      }
    }
  }

  async function fetchUserProfile() {
    const epoch = sessionEpoch()
    const response = await api.get('/api/v1/auth/user', { silent: true })
    if (epoch === sessionEpoch()) updateAuthData({ user: response.data })
    return response
  }

  async function initialize() {
    if (!authSession.token || authSession.validated) return
    if (!initialization) {
      initialization = fetchUserProfile().finally(() => { initialization = null })
    }
    return initialization
  }

  return { ...toRefs(authSession), isLoggedIn, isAdmin, login, register, logout,
    refreshAccessToken, fetchUserProfile, initialize }
})
