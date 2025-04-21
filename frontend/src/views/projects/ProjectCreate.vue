<template>
  <div class="project-create-container">
    <div class="header-section">
      <h1 class="page-title">创建新项目</h1>
    </div>

    <div class="card">
      <div class="card-body">
        <form @submit.prevent="createProject">
          <div class="mb-3">
            <label for="projectName" class="form-label">项目名称 <span class="text-danger">*</span></label>
            <input 
              type="text" 
              class="form-control" 
              id="projectName" 
              v-model="projectData.name" 
              required
              placeholder="输入项目名称"
            >
          </div>

          <div class="mb-3">
            <label for="projectDescription" class="form-label">项目描述</label>
            <textarea 
              class="form-control" 
              id="projectDescription" 
              v-model="projectData.description" 
              rows="5"
              placeholder="输入项目描述"
            ></textarea>
          </div>

          <div class="row mb-3">
            <div class="col-md-6">
              <label for="projectStatus" class="form-label">项目状态</label>
              <select class="form-select" id="projectStatus" v-model="projectData.status">
                <option value="进行中">进行中</option>
                <option value="已完成">已完成</option>
                <option value="已取消">已取消</option>
              </select>
            </div>
            <div class="col-md-6">
              <label for="projectPriority" class="form-label">优先级</label>
              <select class="form-select" id="projectPriority" v-model="projectData.priority">
                <option value="高">高</option>
                <option value="中">中</option>
                <option value="低">低</option>
              </select>
            </div>
          </div>

          <div class="row mb-3">
            <div class="col-md-6">
              <label for="startDate" class="form-label">开始日期</label>
              <input 
                type="date" 
                class="form-control" 
                id="startDate" 
                v-model="projectData.start_date"
              >
            </div>
            <div class="col-md-6">
              <label for="endDate" class="form-label">结束日期</label>
              <input 
                type="date" 
                class="form-control" 
                id="endDate" 
                v-model="projectData.end_date"
              >
            </div>
          </div>

          <div class="mb-4">
            <label class="form-label">项目成员</label>
            <div v-if="loading" class="text-center py-2">
              <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
              </div>
              <span class="ms-2">加载用户列表...</span>
            </div>
            <div v-else-if="users.length === 0" class="alert alert-info">
              暂无其他用户可添加为项目成员
            </div>
            <div v-else>
              <div class="member-list border rounded p-3">
                <div v-for="user in users" :key="user.id" class="form-check mb-2">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    :id="`member-${user.id}`" 
                    :value="user.id"
                    v-model="selectedMembers"
                  >
                  <label class="form-check-label" :for="`member-${user.id}`">
                    {{ user.username }} ({{ user.email }})
                  </label>
                </div>
              </div>
              <small class="text-muted">选中的用户将被添加为项目成员</small>
            </div>
          </div>

          <div class="form-buttons mt-4 d-flex justify-content-between">
            <router-link :to="{ name: 'ProjectList' }" class="btn btn-secondary">
              取消
            </router-link>
            <button type="submit" class="btn btn-primary" :disabled="creating">
              <span v-if="creating" class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
              创建项目
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { useToast } from 'vue-toastification'

export default {
  name: 'ProjectCreate',
  setup() {
    const router = useRouter()
    const toast = useToast()
    
    const loading = ref(false)
    const creating = ref(false)
    const users = ref([])
    const selectedMembers = ref([])
    
    // 项目数据
    const projectData = reactive({
      name: '',
      description: '',
      status: '进行中',
      priority: '中',
      start_date: '',
      end_date: ''
    })
    
    // 加载用户列表
    const loadUsers = async () => {
      loading.value = true
      
      try {
        const response = await axios.get('/api/v1/users')
        users.value = response.data.filter(user => user.id !== getCurrentUserId())
      } catch (err) {
        console.error('加载用户列表失败:', err)
        toast.error('加载用户列表失败，将使用空列表')
        
        // 如果API不存在、未授权或其他错误，使用空数组
        users.value = []
      } finally {
        loading.value = false
      }
    }
    
    // 获取当前用户ID
    const getCurrentUserId = () => {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        try {
          const user = JSON.parse(userStr)
          return user.id
        } catch (e) {
          return null
        }
      }
      return null
    }
    
    // 创建项目
    const createProject = async () => {
      creating.value = true
      
      try {
        // 处理项目成员
        const members = selectedMembers.value.map(userId => ({
          user_id: userId,
          role: '成员'
        }))
        
        // 构建提交数据
        const submitData = {
          ...projectData,
          members
        }
        
        // 获取token并添加到请求头
        const token = localStorage.getItem('token')
        
        // 在请求配置中手动添加Authorization头
        const config = {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
        
        // 发送请求，添加config参数
        const response = await axios.post('/api/v1/projects', submitData, config)
        toast.success('项目创建成功')
        
        // 跳转到项目详情页
        router.push({ name: 'ProjectDetail', params: { id: response.data.id } })
      } catch (err) {
        console.error('创建项目失败:', err)
        toast.error(err.response?.data?.message || '创建项目失败')
      } finally {
        creating.value = false
      }
    }
    
    onMounted(() => {
      loadUsers()
    })
    
    return {
      projectData,
      loading,
      creating,
      users,
      selectedMembers,
      createProject
    }
  }
}
</script>

<style scoped>
.project-create-container {
  padding: 1.5rem;
}

.header-section {
  margin-bottom: 1.5rem;
}

.page-title {
  font-size: 1.75rem;
}

.member-list {
  max-height: 200px;
  overflow-y: auto;
}
</style> 