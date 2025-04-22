import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useAuthStore } from './auth'

// 这是一个兼容性store，用于提供与旧代码兼容的接口，实际上使用auth store的数据
export const useUserStore = defineStore('user', () => {
  const authStore = useAuthStore()
  
  // 计算属性：从auth store中获取userId
  const userId = computed(() => authStore.user?.id)
  
  // 计算属性：从auth store中获取username
  const username = computed(() => authStore.user?.username)
  
  // 计算属性：从auth store中获取完整的user对象
  const user = computed(() => authStore.user)
  
  return {
    userId,
    username,
    user
  }
}) 