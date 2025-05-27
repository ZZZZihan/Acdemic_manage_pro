<template>
  <div class="admin-test">
    <h2>管理员权限测试</h2>
    
    <el-card class="mb-20">
      <h3>当前用户信息</h3>
      <div v-if="userInfo">
        <p><strong>用户名:</strong> {{ userInfo.username }}</p>
        <p><strong>邮箱:</strong> {{ userInfo.email }}</p>
        <p><strong>角色:</strong> {{ userInfo.role }}</p>
        <p><strong>是否管理员:</strong> {{ userInfo.is_administrator ? '是' : '否' }}</p>
      </div>
      <el-button @click="getCurrentUser">获取当前用户信息</el-button>
    </el-card>
    
    <el-card class="mb-20">
      <h3>技术总结权限测试</h3>
      <div class="form-group">
        <label>技术总结ID:</label>
        <el-input v-model="summaryId" placeholder="输入技术总结ID" style="width: 200px;" />
        <el-button @click="checkPermission" type="primary">检查权限</el-button>
      </div>
      
      <div v-if="permissionInfo" class="permission-info">
        <h4>权限检查结果:</h4>
        <pre>{{ JSON.stringify(permissionInfo, null, 2) }}</pre>
      </div>
    </el-card>
    
    <el-card>
      <h3>管理员操作测试</h3>
      <div class="form-group">
        <label>要删除的技术总结ID:</label>
        <el-input v-model="deleteId" placeholder="输入技术总结ID" style="width: 200px;" />
        <el-button @click="testDelete" type="danger">测试删除</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'

const userInfo = ref(null)
const summaryId = ref('')
const deleteId = ref('')
const permissionInfo = ref(null)

const getCurrentUser = async () => {
  try {
    const response = await axios.get('/api/v1/auth/user')
    userInfo.value = response.data
    console.log('当前用户信息:', response.data)
  } catch (error) {
    console.error('获取用户信息失败:', error)
    ElMessage.error('获取用户信息失败')
  }
}

const checkPermission = async () => {
  if (!summaryId.value) {
    ElMessage.warning('请输入技术总结ID')
    return
  }
  
  try {
    const response = await axios.get(`/api/v1/tech_summaries/${summaryId.value}/debug`)
    permissionInfo.value = response.data
    console.log('权限信息:', response.data)
    ElMessage.success('权限检查完成')
  } catch (error) {
    console.error('权限检查失败:', error)
    ElMessage.error('权限检查失败')
    permissionInfo.value = null
  }
}

const testDelete = async () => {
  if (!deleteId.value) {
    ElMessage.warning('请输入技术总结ID')
    return
  }
  
  try {
    const response = await axios.delete(`/api/v1/tech_summaries/${deleteId.value}`)
    console.log('删除成功:', response.data)
    ElMessage.success('删除成功')
  } catch (error) {
    console.error('删除失败:', error)
    if (error.response) {
      ElMessage.error(`删除失败: ${error.response.data.message || error.response.data.msg}`)
    } else {
      ElMessage.error('删除失败')
    }
  }
}

// 页面加载时获取用户信息
getCurrentUser()
</script>

<style scoped>
.admin-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.mb-20 {
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.form-group label {
  min-width: 150px;
  font-weight: bold;
}

.permission-info {
  margin-top: 15px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.permission-info pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style> 