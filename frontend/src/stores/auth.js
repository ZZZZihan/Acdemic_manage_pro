import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/utils/axios'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const storedToken = localStorage.getItem('token')
  const storedRefreshToken = localStorage.getItem('refreshToken')
  const storedUser = localStorage.getItem('user')

  const token = ref(storedToken || '')
  const refreshToken = ref(storedRefreshToken || '')
  const user = ref(storedUser ? JSON.parse(storedUser) : null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'Administrator')

  async function login(credentials) {
    const response = await axios.post('/api/v1/auth/login', credentials)
    if (!response.data.access_token || !response.data.user) {
      throw new Error('登录响应缺少必要数据')
    }
    setAuthData(response.data)
    return response.data
  }
  
  async function register(userData) {
    try {
      const response = await axios.post('/api/v1/auth/register', userData)
      return response
    } catch (error) {
      throw error
    }
  }
  
  async function logout() {
    try {
      await axios.post('/api/v1/auth/logout')
    } catch (error) {
      console.error('登出时发生错误:', error)
    } finally {
      clearAuthData()
      router.push({ name: 'Login' })
    }
  }
  
  async function refreshAccessToken() {
    try {
      const response = await axios.post('/api/v1/auth/refresh', {}, {
        headers: {
          'Authorization': `Bearer ${refreshToken.value}`
        }
      })
      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      return response
    } catch (error) {
      clearAuthData()
      throw error
    }
  }
  
  async function fetchUserProfile() {
    try {
      const response = await axios.get('/api/v1/auth/user')
      user.value = response.data
      localStorage.setItem('user', JSON.stringify(user.value))
      return response
    } catch (error) {
      throw error
    }
  }
  
  function setAuthData(data) {
    if (data.access_token) {
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
    }
    if (data.refresh_token) {
      refreshToken.value = data.refresh_token
      localStorage.setItem('refreshToken', data.refresh_token)
    }
    if (data.user) {
      user.value = data.user
      localStorage.setItem('user', JSON.stringify(data.user))
    }
  }

  function clearAuthData() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }
  
  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    isAdmin,
    login,
    register,
    logout,
    refreshAccessToken,
    fetchUserProfile
  }
}) 