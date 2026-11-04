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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
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
  if (!loginForm.value || loading.value) return
  const valid = await loginForm.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(loginData)
    ElMessage.success('登录成功')
    const candidate = route.query.redirect
    const redirect = typeof candidate === 'string' && candidate.startsWith('/') &&
      !candidate.startsWith('//') && !candidate.includes('\\') ? candidate : '/workspace'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '登录失败，请检查邮箱、密码或网络')
  } finally {
    loading.value = false
  }
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
