<template>
  <div class="register-view">
    <h2 class="page-title">用户注册</h2>
    <el-form
      ref="registerForm"
      :model="registerData"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleRegister"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="registerData.username" placeholder="请输入用户名" />
      </el-form-item>
      
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="registerData.email" placeholder="请输入邮箱" />
      </el-form-item>
      
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="registerData.password"
          type="password"
          placeholder="请输入密码"
          show-password
        />
      </el-form-item>
      
      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input
          v-model="registerData.confirmPassword"
          type="password"
          placeholder="请再次输入密码"
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
          注册
        </el-button>
      </el-form-item>
    </el-form>
    
    <div class="form-footer">
      <p>已有账号？<router-link to="/auth/login">立即登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const registerForm = ref(null)
const loading = ref(false)

const registerData = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerData.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerForm.value) return
  
  await registerForm.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 移除确认密码字段
        const { confirmPassword, ...userData } = registerData
        
        await authStore.register(userData)
        ElMessage.success('注册成功，请登录')
        router.push('/auth/login')
      } catch (error) {
        console.error('注册失败:', error)
        ElMessage.error(error.response?.data?.message || '注册失败，请稍后再试')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.register-view {
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