import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建axios实例
// 在开发环境中，如果没有设置VITE_API_URL，则使用空字符串（依赖Vite代理）
const baseURL = import.meta.env.VITE_API_URL || ''
console.log('创建Axios实例，baseURL:', baseURL)
const instance = axios.create({
  baseURL: baseURL,
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
    
    // 从localStorage获取token - 确保每次都获取最新的token
    const token = localStorage.getItem('token')
    console.log('当前token状态:', { hasToken: !!token, tokenLength: token ? token.length : 0 })
    
    // 如果存在token，则添加到请求头
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
      console.log('请求已添加认证Token')
    } else {
      console.log('无token，不添加认证头')
      
      // 检查是否是需要认证的请求路径
      const publicPaths = ['/auth/login', '/auth/register', '/auth/forgot-password']
      const isAuthRequired = !publicPaths.some(path => config.url.includes(path))
      
      if (isAuthRequired) {
        console.warn('警告: 访问需要认证的路径但无token')
      }
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
      hasAuthHeader: !!config.headers['Authorization'],
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
  async error => {
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
          ElMessage.error(error.response.data.message || error.response.data.msg || '请求参数错误')
          break
        case 401:
          console.error('认证失败，检查错误类型')
          
          // 检查错误信息，区分token过期和权限不足
          const errorMessage = error.response.data?.message || ''
          const isPermissionDenied = errorMessage.includes('无权') || errorMessage.includes('权限') || 
                                   errorMessage.includes('unauthorized') && !errorMessage.includes('过期') && 
                                   !errorMessage.includes('expired') && !errorMessage.includes('invalid token')
          
          if (isPermissionDenied) {
            // 这是权限问题，不是token过期，直接显示错误信息
            console.log('权限不足，不尝试刷新token')
            ElMessage.error(errorMessage || '您没有权限执行此操作')
            break
          }
          
          // 可能是token过期，尝试刷新
          console.log('可能是token过期，尝试刷新token')
          const refreshToken = localStorage.getItem('refreshToken')
          
          if (refreshToken && !error.config._retry) {
            error.config._retry = true
            
            try {
              console.log('尝试刷新访问令牌')
              const refreshResponse = await axios.post('/api/v1/auth/refresh', {}, {
                headers: {
                  'Authorization': `Bearer ${refreshToken}`
                }
              })
              
              const newToken = refreshResponse.data.access_token
              localStorage.setItem('token', newToken)
              console.log('Token刷新成功，重试原请求')
              
              // 更新原请求的认证头并重试
              error.config.headers['Authorization'] = `Bearer ${newToken}`
              return instance(error.config)
              
            } catch (refreshError) {
              console.error('Token刷新失败:', refreshError)
              // 刷新失败，清除所有认证数据并跳转登录页
              localStorage.removeItem('token')
              localStorage.removeItem('refreshToken')
              localStorage.removeItem('user')
              
              const currentPath = window.location.pathname
              if (!currentPath.includes('/auth/login')) {
                console.log('Token刷新失败，重定向到登录页')
                ElMessage.error('登录已过期，请重新登录')
                setTimeout(() => {
                  router.push('/auth/login')
                }, 500)
              }
            }
          } else {
            // 没有refresh token或已经重试过，清除认证数据并跳转登录页
            console.log('无refresh token或已重试，清除认证数据')
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            localStorage.removeItem('user')
            
            const currentPath = window.location.pathname
            if (!currentPath.includes('/auth/login')) {
              console.log('重定向到登录页')
              ElMessage.error('登录已过期，请重新登录')
              setTimeout(() => {
                router.push('/auth/login')
              }, 500)
            }
          }
          break
        case 403:
          // 详细说明权限问题
          const errorMsg = error.response.data.msg || '没有权限执行此操作'
          console.error('权限错误:', errorMsg)
          ElMessage.error(errorMsg)
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