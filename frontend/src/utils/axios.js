import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
console.log('创建Axios实例，baseURL:', import.meta.env.VITE_API_URL)
const instance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 60000, // 默认超时时间增加到60秒
  headers: {
    'Content-Type': 'application/json'
  }
})

console.log('Axios实例创建，baseURL:', import.meta.env.VITE_API_URL || '未设置')

// 请求拦截器
instance.interceptors.request.use(
  config => {
    console.log(`发送${config.method.toUpperCase()}请求到: ${config.baseURL}${config.url}`, config)
    
    // 从localStorage获取token
    const token = localStorage.getItem('token')
    console.log('当前token状态:', { hasToken: !!token, token })
    
    // 如果存在token，则添加到请求头
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
      console.log('请求已添加认证Token')
    } else {
      console.log('无token，不添加认证头')
    }
    
    // 确保所有字段都是字符串
    if (config.data) {
      Object.keys(config.data).forEach(key => {
        if (config.data[key] === null || config.data[key] === undefined) {
          config.data[key] = ''
        }
      })
    }
    
    console.log('最终请求配置:', {
      url: config.url,
      method: config.method,
      headers: config.headers,
      data: config.data
    })
    
    return config
  },
  error => {
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  response => {
    console.log(`收到响应: ${response.config.url}`, response.status, response.data)
    return response
  },
  error => {
    console.error('请求失败:', error)
    
    if (error.code === 'ECONNABORTED') {
      console.error('请求超时')
      ElMessage.error('请求超时，请稍后再试')
      return Promise.reject(error)
    }
    
    if (error.response) {
      console.error('错误响应状态:', error.response.status)
      console.error('错误响应数据:', error.response.data)
      
      // 根据状态码处理错误
      switch (error.response.status) {
        case 400:
          ElMessage.error(error.response.data.message || '请求参数错误')
          break
        case 401:
          console.error('认证失败，需要重新登录')
          // 清除认证数据
          localStorage.removeItem('token')
          localStorage.removeItem('refreshToken')
          localStorage.removeItem('user')
          
          // 如果不是登录页面，则重定向到登录页
          const currentPath = window.location.pathname
          if (!currentPath.includes('/auth/login')) {
            console.log('重定向到登录页')
            ElMessage.error('登录已过期，请重新登录')
            setTimeout(() => {
              window.location.href = '/auth/login'
            }, 1000)
          }
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(`请求失败，状态码: ${error.response.status}`)
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('没有收到响应:', error.request)
      ElMessage.error('服务器无响应，请检查网络连接')
    } else {
      // 请求配置有误
      console.error('请求配置错误:', error.message)
      ElMessage.error(`请求错误: ${error.message}`)
    }
    
    return Promise.reject(error)
  }
)

export default instance 