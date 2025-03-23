import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/utils/axios'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  console.log('初始化 Auth Store')
  
  // 从localStorage获取初始状态
  const storedToken = localStorage.getItem('token')
  const storedRefreshToken = localStorage.getItem('refreshToken')
  const storedUser = localStorage.getItem('user')
  
  console.log('从 localStorage 读取的初始数据:', {
    token: !!storedToken,
    refreshToken: !!storedRefreshToken,
    user: !!storedUser
  })
  
  // 状态
  const token = ref(storedToken || '')
  const refreshToken = ref(storedRefreshToken || '')
  const user = ref(storedUser ? JSON.parse(storedUser) : null)
  
  console.log('初始化后的状态:', {
    token: !!token.value,
    refreshToken: !!refreshToken.value,
    user: user.value
  })
  
  // 计算属性
  const isLoggedIn = computed(() => {
    const hasToken = !!token.value
    console.log('检查登录状态:', { hasToken, token: token.value })
    return hasToken
  })
  const isAdmin = computed(() => user.value?.role === 'Administrator')
  
  // 方法
  async function login(credentials) {
    console.log('开始登录流程，凭据:', credentials)
    try {
      const response = await axios.post('/api/v1/auth/login', credentials)
      console.log('登录API响应成功:', response.data)
      
      // 确保响应中包含所需的数据
      if (!response.data.access_token || !response.data.user) {
        console.error('登录响应缺少必要数据:', response.data)
        throw new Error('登录响应缺少必要数据')
      }
      
      // 设置认证数据
      setAuthData(response.data)
      
      // 验证数据是否正确设置
      console.log('登录后状态验证:', {
        token: token.value,
        user: user.value,
        isLoggedIn: isLoggedIn.value
      })
      
      return response.data
    } catch (error) {
      console.error('登录请求失败:', error)
      throw error
    }
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
    console.log('设置认证数据，原始数据：', data)
    
    if (data.access_token) {
      token.value = data.access_token
      localStorage.setItem('token', data.access_token)
      console.log('保存 access_token 到 localStorage 成功')
    }
    
    if (data.refresh_token) {
      refreshToken.value = data.refresh_token
      localStorage.setItem('refreshToken', data.refresh_token)
      console.log('保存 refresh_token 到 localStorage 成功')
    }
    
    if (data.user) {
      user.value = data.user
      localStorage.setItem('user', JSON.stringify(data.user))
      console.log('保存 user 到 localStorage 成功，用户数据：', data.user)
    }
    
    // 验证数据是否正确保存到 localStorage
    console.log('验证 localStorage 数据：', {
      token: localStorage.getItem('token'),
      refreshToken: localStorage.getItem('refreshToken'),
      user: localStorage.getItem('user')
    })
  }
  
  function clearAuthData() {
    console.log('清除认证数据')
    token.value = ''
    refreshToken.value = ''
    user.value = null
    
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
    
    console.log('认证数据已清除')
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