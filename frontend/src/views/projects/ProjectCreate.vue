<template>
  <div class="project-create">
    <div class="page-header">
      <h2 class="page-title">创建新项目</h2>
      <router-link :to="{ name: 'ProjectList' }">
        <el-button>返回</el-button>
      </router-link>
    </div>

    <el-card>
      <el-form 
        ref="projectForm"
        :model="projectData"
        label-width="100px"
        @submit.prevent="createProject"
      >
        <el-form-item label="项目名称" prop="name">
          <el-input 
            v-model="projectData.name" 
            placeholder="输入项目名称" 
            required
          />
        </el-form-item>

        <el-form-item label="项目描述" prop="description">
          <el-input 
            v-model="projectData.description" 
            type="textarea" 
            :rows="5"
            placeholder="输入项目描述"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="项目状态" prop="status">
              <el-select v-model="projectData.status" placeholder="选择项目状态" style="width: 100%">
                <el-option label="进行中" value="进行中" />
                <el-option label="已完成" value="已完成" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="projectData.priority" placeholder="选择优先级" style="width: 100%">
                <el-option label="高" value="高" />
                <el-option label="中" value="中" />
                <el-option label="低" value="低" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker
                v-model="projectData.start_date"
                type="date"
                placeholder="选择开始日期"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期" prop="end_date">
              <el-date-picker
                v-model="projectData.end_date"
                type="date"
                placeholder="选择结束日期"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="项目成员">
          <div v-if="loading" class="loading-container">
            <el-icon :size="24" class="is-loading"><Loading /></el-icon>
            <span>加载用户列表...</span>
          </div>
          
          <el-empty v-else-if="users.length === 0" description="暂无其他用户可添加为项目成员" />
          
          <div v-else class="member-list">
            <div 
              v-for="user in users" 
              :key="user.id" 
              class="member-item"
            >
              <el-checkbox v-model="selectedMembers" :label="user.id">
                <span class="member-name">{{ user.username }}</span>
                <span class="member-email">({{ user.email }})</span>
              </el-checkbox>
            </div>
            <div class="selected-count">已选择 {{ selectedMembers.length }} 名成员</div>
          </div>
        </el-form-item>

        <el-form-item label="项目文件">
          <file-upload 
            ref="fileUploadRef"
            @file-uploaded="handleFileUploaded"
            @file-removed="handleFileRemoved"
          />
          
          <div v-if="projectFiles.length > 0" class="file-list-info mt-2">
            已上传 {{ projectFiles.length }} 个文件
          </div>
        </el-form-item>

        <el-form-item class="form-buttons">
          <el-button type="primary" native-type="submit" :loading="creating">创建项目</el-button>
          <el-button @click="$router.push({ name: 'ProjectList' })">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import { Loading } from '@element-plus/icons-vue'

export default {
  name: 'ProjectCreate',
  components: {
    FileUpload,
    Loading
  },
  setup() {
    const router = useRouter()
    const projectForm = ref(null)
    
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
    
    // 文件相关状态
    const fileUploadRef = ref(null)
    const projectFiles = ref([])
    
    // 加载用户列表
    const loadUsers = async () => {
      loading.value = true
      
      try {
        const response = await axios.get('/api/v1/users')
        users.value = response.data.filter(user => user.id !== getCurrentUserId())
      } catch (err) {
        console.error('加载用户列表失败:', err)
        ElMessage.error('加载用户列表失败，将使用空列表')
        
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
    
    // 处理文件上传成功
    const handleFileUploaded = (fileInfo) => {
      projectFiles.value.push(fileInfo)
    }
    
    // 处理文件移除
    const handleFileRemoved = (fileInfo) => {
      const index = projectFiles.value.findIndex(file => 
        file.file_path === fileInfo.file_path
      )
      
      if (index !== -1) {
        projectFiles.value.splice(index, 1)
      }
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
        
        // 发送请求
        const response = await axios.post('/api/v1/projects', submitData)
        
        // 如果有文件，上传文件关联到项目
        if (projectFiles.value.length > 0) {
          const projectId = response.data.id
          const token = localStorage.getItem('token')
          
          // 关联所有上传的文件到项目
          for (const file of projectFiles.value) {
            try {
              await axios.post(`/api/v1/projects/${projectId}/files`, {
                file_path: file.file_path,
                original_name: file.original_name,
                file_size: file.file_size,
                file_type: file.file_type
              }, {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              })
            } catch (err) {
              console.error('关联文件到项目失败:', err)
            }
          }
        }
        
        ElMessage.success('项目创建成功')
        
        // 跳转到项目详情页
        router.push({ name: 'ProjectDetail', params: { id: response.data.id } })
      } catch (err) {
        console.error('创建项目失败:', err)
        ElMessage.error(err.response?.data?.message || '创建项目失败')
      } finally {
        creating.value = false
      }
    }
    
    onMounted(() => {
      loadUsers()
    })
    
    return {
      projectForm,
      projectData,
      loading,
      creating,
      users,
      selectedMembers,
      fileUploadRef,
      projectFiles,
      handleFileUploaded,
      handleFileRemoved,
      createProject
    }
  }
}
</script>

<style scoped>
.project-create {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
}

.form-buttons {
  margin-top: 20px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 15px 0;
}

.member-list {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 10px;
  max-height: 200px;
  overflow-y: auto;
}

.member-item {
  padding: 8px;
  margin-bottom: 5px;
  border-radius: 4px;
}

.member-item:hover {
  background-color: #f5f7fa;
}

.member-name {
  font-weight: 500;
}

.member-email {
  color: #909399;
  margin-left: 5px;
}

.selected-count {
  margin-top: 10px;
  color: #909399;
  font-size: 13px;
}

.file-list-info {
  color: #909399;
  font-size: 13px;
}

.mt-2 {
  margin-top: 10px;
}
</style> 