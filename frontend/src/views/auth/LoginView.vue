<template>
  <div class="login-view">
    <h2 class="page-title">用户登录</h2>
    <el-form
      ref="loginForm"
      :model="loginData"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleLogin"
    >
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="loginData.email" placeholder="请输入邮箱" />
      </el-form-item>
      
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="loginData.password"
          type="password"
          placeholder="请输入密码"
          show-password
        />
      </el-form-item>
      
      <el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          class="submit-btn"
        >
          登录
        </el-button>
      </el-form-item>
    </el-form>
    
    <div class="form-footer">
      <p>还没有账号？<router-link to="/auth/register">立即注册</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const loginForm = ref(null)
const loading = ref(false)

const loginData = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginForm.value) return
  
  await loginForm.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        console.log('开始登录请求，数据:', loginData)
        const response = await authStore.login(loginData)
        console.log('登录成功，响应数据:', response)
        ElMessage.success('登录成功')
        
        // 检查登录状态
        console.log('登录后状态检查:', {
          isLoggedIn: authStore.isLoggedIn,
          token: !!authStore.token,
          user: authStore.user
        })
        
        // 如果有重定向地址，则跳转到该地址
        const redirectPath = route.query.redirect || '/'
        console.log('准备跳转到:', redirectPath)
        
        // 添加延迟，确保数据已经保存到localStorage
        setTimeout(() => {
          console.log('执行路由跳转前再次检查登录状态:', {
            isLoggedIn: authStore.isLoggedIn,
            token: !!authStore.token,
            user: authStore.user,
            localStorage: {
              token: localStorage.getItem('token'),
              user: localStorage.getItem('user')
            }
          })
          console.log('执行路由跳转到:', redirectPath)
          
          // 使用 window.location.href 而不是 router.push
          window.location.href = redirectPath
        }, 1000) // 增加延迟时间到1秒
      } catch (error) {
        console.error('登录失败:', error)
        console.error('错误详情:', error.response?.data)
        ElMessage.error(error.response?.data?.message || '登录失败，请检查您的凭证')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-view {
  max-width: 100%;
}

.page-title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}

.submit-btn {
  width: 100%;
}

.form-footer {
  margin-top: 20px;
  text-align: center;
}
</style> 