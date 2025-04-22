<template>
  <div class="project-edit">
    <el-card v-if="loading" class="loading-card">
      <div class="loading-container">
        <el-icon :size="30" class="is-loading"><Loading /></el-icon>
        <p class="loading-text">加载项目信息...</p>
      </div>
    </el-card>
    
    <el-alert v-else-if="error" type="error" :title="error" :closable="false" />
    
    <template v-else>
      <div class="page-header">
        <h2 class="page-title">编辑项目</h2>
        <router-link :to="{ name: 'ProjectDetail', params: { id: projectId } }">
          <el-button>返回</el-button>
        </router-link>
      </div>

      <el-card>
        <el-form 
          ref="projectForm"
          :model="projectData"
          label-width="100px"
          @submit.prevent="updateProject"
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

          <el-form-item v-if="isCreator" label="项目成员">
            <div v-if="loadingUsers" class="loading-container">
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

          <!-- 添加文件部分 -->
          <el-form-item label="项目文件">
            <div v-if="loadingFiles" class="loading-container">
              <el-spinner />
              <span>加载文件列表...</span>
            </div>
            
            <div v-else>
              <file-upload 
                ref="fileUploadRef"
                :initial-files="projectFiles"
                @file-uploaded="handleFileUploaded"
                @file-removed="handleFileRemoved"
              />
              
              <div v-if="projectFiles.length > 0" class="file-list-info mt-2">
                已上传 {{ projectFiles.length }} 个文件
              </div>
            </div>
          </el-form-item>

          <el-form-item class="form-buttons">
            <el-button type="primary" native-type="submit" :loading="updating">保存修改</el-button>
            <el-button @click="$router.push({ name: 'ProjectDetail', params: { id: projectId } })">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </template>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import { Loading } from '@element-plus/icons-vue'

export default {
  name: 'ProjectEdit',
  components: {
    FileUpload,
    Loading
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const projectForm = ref(null)
    
    // 状态
    const loading = ref(true)
    const loadingUsers = ref(false)
    const updating = ref(false)
    const error = ref(null)
    const users = ref([])
    const selectedMembers = ref([])
    const projectId = route.params.id
    
    // 项目数据
    const projectData = reactive({
      name: '',
      description: '',
      status: '进行中',
      priority: '中',
      start_date: '',
      end_date: ''
    })
    
    // 当前用户信息
    const currentUser = computed(() => {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        try {
          return JSON.parse(userStr)
        } catch (e) {
          return null
        }
      }
      return null
    })
    
    // 是否为创建者
    const isCreator = ref(false)
    
    // 文件相关状态
    const fileUploadRef = ref(null)
    const projectFiles = ref([])
    const loadingFiles = ref(false)
    const filesToDelete = ref([]) // 存储要删除的文件ID
    
    // 加载项目数据
    const loadProject = async () => {
      if (!projectId) {
        error.value = '项目ID无效'
        loading.value = false
        return
      }
      
      loading.value = true
      
      try {
        // 添加最新的认证信息
        const token = localStorage.getItem('token')
        
        const response = await axios.get(`/api/v1/projects/${projectId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        const project = response.data
        
        // 填充表单数据
        projectData.name = project.name
        projectData.description = project.description || ''
        projectData.status = project.status
        projectData.priority = project.priority
        
        // 处理日期格式 (将ISO格式转换为YYYY-MM-DD格式)
        if (project.start_date) {
          projectData.start_date = formatDateForInput(project.start_date)
        }
        
        if (project.end_date) {
          projectData.end_date = formatDateForInput(project.end_date)
        }
        
        // 检查当前用户是否为创建者
        const isCreatorById = currentUser.value && project.creator_id === currentUser.value.id
        const isCreatorByObject = currentUser.value && project.creator && project.creator.id === currentUser.value.id
        isCreator.value = isCreatorById || isCreatorByObject
        
        console.log("当前用户ID:", currentUser.value?.id)
        console.log("项目创建者ID:", project.creator_id)
        console.log("是否为创建者:", isCreator.value)
        
        // 如果是创建者，提取已有成员ID
        if (project.members) {
          console.log("项目成员:", project.members)
          
          // 确保成员数据格式正确
          const memberUserIds = project.members
            .filter(member => member.user_id && (currentUser.value && member.user_id !== currentUser.value.id))
            .map(member => {
              // 可能是直接的user_id或者嵌套在user对象中
              return typeof member.user_id === 'number' ? member.user_id : member.user_id
            })
          
          console.log("提取的成员ID:", memberUserIds)
          selectedMembers.value = memberUserIds
        }
      } catch (err) {
        console.error('加载项目详情失败:', err)
        error.value = '加载项目详情失败，请稍后重试'
      } finally {
        loading.value = false
      }
    }
    
    // 加载用户列表
    const loadUsers = async () => {
      if (!isCreator.value) return
      
      loadingUsers.value = true
      
      try {
        const response = await axios.get('/api/v1/users')
        // 排除当前用户
        users.value = response.data.filter(user => user.id !== currentUser.value?.id)
      } catch (err) {
        console.error('加载用户列表失败:', err)
        ElMessage.error('加载用户列表失败')
      } finally {
        loadingUsers.value = false
      }
    }
    
    // 加载项目文件
    const loadProjectFiles = async () => {
      if (!projectId) return
      
      loadingFiles.value = true
      
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get(`/api/v1/projects/${projectId}/files`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        projectFiles.value = response.data || []
      } catch (err) {
        console.error('加载项目文件失败:', err)
        ElMessage.error('加载项目文件失败')
      } finally {
        loadingFiles.value = false
      }
    }
    
    // 处理文件上传成功
    const handleFileUploaded = async (fileInfo) => {
      try {
        // 添加到文件列表，等待保存时一并提交
        projectFiles.value.push(fileInfo)
      } catch (err) {
        console.error('添加文件失败:', err)
      }
    }
    
    // 处理文件移除
    const handleFileRemoved = (fileInfo) => {
      // 如果是已存在的文件（有ID），添加到删除列表
      if (fileInfo.id) {
        filesToDelete.value.push(fileInfo.id)
      }
      
      // 从当前文件列表中移除
      const index = projectFiles.value.findIndex(file => 
        (file.id && file.id === fileInfo.id) || 
        (file.file_path && file.file_path === fileInfo.file_path)
      )
      
      if (index !== -1) {
        projectFiles.value.splice(index, 1)
      }
    }
    
    // 更新项目时处理文件
    const updateProjectFiles = async () => {
      const token = localStorage.getItem('token')
      
      // 处理要删除的文件
      for (const fileId of filesToDelete.value) {
        try {
          await axios.delete(`/api/v1/projects/${projectId}/files/${fileId}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
        } catch (err) {
          console.error(`删除文件 ${fileId} 失败:`, err)
        }
      }
      
      // 处理新上传的文件
      const newFiles = projectFiles.value.filter(file => !file.id)
      for (const file of newFiles) {
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
    
    // 修改更新项目的方法，在更新成功后处理文件
    const updateProject = async () => {
      updating.value = true
      
      try {
        // 构建更新数据
        const updateData = {
          name: projectData.name,
          description: projectData.description,
          status: projectData.status,
          priority: projectData.priority,
          start_date: projectData.start_date || null,
          end_date: projectData.end_date || null
        }
        
        // 如果是创建者，添加成员信息
        if (isCreator.value) {
          // 确保当前用户始终是成员
          const memberIds = [...selectedMembers.value]
          
          updateData.members = memberIds.map(userId => ({
            user_id: userId,
            role: '成员'
          }))
        }
        
        // 添加最新的认证信息
        const token = localStorage.getItem('token')
        
        // 发送更新请求
        const response = await axios.put(`/api/v1/projects/${projectId}`, updateData, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        // 更新文件
        await updateProjectFiles()
        
        ElMessage.success('项目已成功更新')
        
        // 跳转到项目详情页
        router.push({ name: 'ProjectDetail', params: { id: projectId } })
      } catch (err) {
        console.error('更新项目失败:', err)
        if (err.response?.status === 403) {
          ElMessage.error(err.response.data.msg || '您没有权限编辑此项目')
        } else {
          ElMessage.error(err.response?.data?.message || '更新项目失败，请稍后重试')
        }
      } finally {
        updating.value = false
      }
    }
    
    // 将ISO日期格式转换为Input日期格式
    const formatDateForInput = (isoDate) => {
      if (!isoDate) return ''
      
      const date = new Date(isoDate)
      const year = date.getFullYear()
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const day = date.getDate().toString().padStart(2, '0')
      
      return `${year}-${month}-${day}`
    }
    
    // 页面加载时获取数据
    onMounted(() => {
      loadProject()
      loadUsers()
      loadProjectFiles()
    })
    
    return {
      projectForm,
      projectId,
      projectData,
      loading,
      loadingUsers,
      updating,
      error,
      users,
      selectedMembers,
      isCreator,
      fileUploadRef,
      projectFiles,
      loadingFiles,
      handleFileUploaded,
      handleFileRemoved,
      updateProject
    }
  }
}
</script>

<style scoped>
.project-edit {
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px 0;
}

.loading-text {
  margin-top: 15px;
  color: #909399;
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