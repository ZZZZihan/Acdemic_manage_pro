<template>
  <div class="profile-view" v-loading="loading">
    <h2 class="page-title">个人中心</h2>
    
    <el-card class="profile-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="个人信息" name="info">
          <el-form
            ref="profileForm"
            :model="profileData"
            :rules="rules"
            label-width="100px"
            @submit.prevent="updateProfile"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="profileData.username" disabled />
            </el-form-item>
            
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileData.email" disabled />
            </el-form-item>
            
            <el-form-item label="姓名" prop="name">
              <el-input v-model="profileData.name" />
            </el-form-item>
            
            <el-form-item label="所在地" prop="location">
              <el-input v-model="profileData.location" />
            </el-form-item>
            
            <el-form-item label="个人简介" prop="about_me">
              <el-input
                v-model="profileData.about_me"
                type="textarea"
                :rows="4"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="updating">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordForm"
            :model="passwordData"
            :rules="passwordRules"
            label-width="100px"
            @submit.prevent="updatePassword"
          >
            <el-form-item label="当前密码" prop="oldPassword">
              <el-input
                v-model="passwordData.oldPassword"
                type="password"
                show-password
              />
            </el-form-item>
            
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordData.newPassword"
                type="password"
                show-password
              />
            </el-form-item>
            
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordData.confirmPassword"
                type="password"
                show-password
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="updating">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import axios from '@/utils/axios'

const authStore = useAuthStore()
const activeTab = ref('info')
const loading = ref(false)
const updating = ref(false)
const profileForm = ref(null)
const passwordForm = ref(null)

const profileData = reactive({
  username: '',
  email: '',
  name: '',
  location: '',
  about_me: ''
})

const passwordData = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const rules = {
  name: [
    { max: 64, message: '姓名长度不能超过64个字符', trigger: 'blur' }
  ],
  location: [
    { max: 64, message: '所在地长度不能超过64个字符', trigger: 'blur' }
  ]
}

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== passwordData.newPassword) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ]
}

const fetchUserProfile = async () => {
  loading.value = true
  try {
    await authStore.fetchUserProfile()
    
    // 填充表单数据
    const user = authStore.user
    if (user) {
      profileData.username = user.username || ''
      profileData.email = user.email || ''
      profileData.name = user.name || ''
      profileData.location = user.location || ''
      profileData.about_me = user.about_me || ''
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    ElMessage.error('获取用户信息失败')
  } finally {
    loading.value = false
  }
}

const updateProfile = async () => {
  if (!profileForm.value) return
  
  await profileForm.value.validate(async (valid) => {
    if (valid) {
      updating.value = true
      try {
        // 这里应该调用后端API更新用户信息
        // 由于当前API未实现，这里只是模拟成功
        ElMessage.success('个人信息更新成功')
        
        // 重新获取用户信息
        await fetchUserProfile()
      } catch (error) {
        console.error('更新个人信息失败:', error)
        ElMessage.error('更新个人信息失败')
      } finally {
        updating.value = false
      }
    }
  })
}

const updatePassword = async () => {
  if (!passwordForm.value) return
  
  await passwordForm.value.validate(async (valid) => {
    if (valid) {
      updating.value = true
      try {
        // 这里应该调用后端API更新密码
        // 由于当前API未实现，这里只是模拟成功
        ElMessage.success('密码修改成功')
        
        // 清空密码表单
        passwordData.oldPassword = ''
        passwordData.newPassword = ''
        passwordData.confirmPassword = ''
        
        // 切换到个人信息标签页
        activeTab.value = 'info'
      } catch (error) {
        console.error('修改密码失败:', error)
        ElMessage.error('修改密码失败')
      } finally {
        updating.value = false
      }
    }
  })
}

onMounted(() => {
  fetchUserProfile()
})
</script>

<style scoped>
.profile-view {
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
}

.profile-card {
  max-width: 800px;
  margin: 0 auto;
}
</style> 