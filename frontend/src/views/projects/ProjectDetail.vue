<template>
  <div class="project-detail">
    <el-card v-if="loading" class="loading-card">
      <div class="loading-container">
        <el-icon :size="30" class="is-loading"><Loading /></el-icon>
        <p class="loading-text">加载项目信息...</p>
      </div>
    </el-card>
    
    <el-alert v-else-if="error" type="error" :title="error" :closable="false" />
    
    <template v-else>
      <!-- 项目头部 -->
      <div class="page-header">
        <div class="title-section">
          <h2 class="page-title">{{ project.name }}</h2>
          <div class="status-tags">
            <el-tag :type="getStatusTagType(project.status)">{{ project.status }}</el-tag>
            <el-tag type="info" class="ml-2">优先级: {{ project.priority }}</el-tag>
          </div>
        </div>
        
        <div class="action-buttons">
          <router-link v-if="canEdit" :to="{ name: 'ProjectEdit', params: { id: project.id } }">
            <el-button type="primary">编辑项目</el-button>
          </router-link>
          <el-button 
            v-if="isCreator" 
            type="danger" 
            @click="confirmDelete"
            class="ml-2"
          >
            删除项目
          </el-button>
        </div>
      </div>
      
      <div class="meta-info">
        <span class="text-muted">
          创建于 {{ formatDateTime(project.created_at) }} 
          <template v-if="project.updated_at && project.updated_at !== project.created_at">
            · 更新于 {{ formatDateTime(project.updated_at) }}
          </template>
        </span>
      </div>
      
      <!-- 项目内容 -->
      <el-row :gutter="20">
        <el-col :span="16">
          <!-- 项目描述 -->
          <el-card class="content-card">
            <template #header>
              <div class="card-header">
                <h3>项目描述</h3>
              </div>
            </template>
            <div class="card-body">
              <p v-if="project.description">{{ project.description }}</p>
              <el-empty v-else description="暂无项目描述" />
            </div>
          </el-card>
          
          <!-- 项目成员 -->
          <el-card class="content-card">
            <template #header>
              <div class="card-header">
                <h3>项目成员</h3>
              </div>
            </template>
            <div class="card-body">
              <div v-if="project.members && project.members.length > 0">
                <el-table :data="project.members" style="width: 100%">
                  <el-table-column label="用户名">
                    <template #default="scope">
                      <div class="user-info">
                        <el-avatar 
                          :size="32" 
                          :class="['member-avatar', `bg-${getColorByUsername(scope.row.user?.username)}`]"
                        >
                          {{ getInitials(scope.row.user?.username) }}
                        </el-avatar>
                        <div class="user-details">
                          <div class="username">{{ scope.row.user?.username || '未知用户' }}</div>
                          <div class="email">{{ scope.row.user?.email || '' }}</div>
                        </div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="role" label="角色" width="120" />
                  <el-table-column label="加入时间" width="180">
                    <template #default="scope">
                      {{ formatDateTime(scope.row.created_at) }}
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <el-empty v-else description="暂无项目成员" />
            </div>
          </el-card>
          
          <!-- 项目文件（新增） -->
          <el-card class="content-card">
            <template #header>
              <div class="card-header">
                <h3>项目文件</h3>
                <div v-if="canEdit">
                  <el-button v-if="!showUploader" size="small" type="primary" @click="showUploader = true">
                    上传文件
                  </el-button>
                  <el-button v-else size="small" @click="showUploader = false">
                    取消上传
                  </el-button>
                </div>
              </div>
            </template>
            
            <div v-if="showUploader && canEdit" class="uploader-section">
              <file-upload
                ref="fileUploadRef"
                @file-uploaded="handleFileUploaded"
                @file-removed="handleFileRemoved"
              />
            </div>
            
            <div v-if="projectFiles.length > 0" class="file-list">
              <el-table :data="projectFiles" style="width: 100%">
                <el-table-column label="文件名" min-width="200">
                  <template #default="scope">
                    <div class="file-name">
                      <el-icon class="file-icon"><Document /></el-icon>
                      <span>{{ scope.row.original_name || '未命名文件' }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="大小" width="120">
                  <template #default="scope">
                    {{ formatFileSize(scope.row.file_size) }}
                  </template>
                </el-table-column>
                <el-table-column label="上传时间" width="180">
                  <template #default="scope">
                    {{ formatDateTime(scope.row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150">
                  <template #default="scope">
                    <el-button 
                      type="primary" 
                      size="small" 
                      @click="downloadFile(scope.row)"
                      class="mr-1"
                    >
                      下载
                    </el-button>
                    <el-button 
                      v-if="canEdit" 
                      type="danger" 
                      size="small" 
                      @click="confirmDeleteFile(scope.row)"
                    >
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无项目文件" />
          </el-card>
        </el-col>
        
        <el-col :span="8">
          <!-- 项目信息卡片 -->
          <el-card class="content-card">
            <template #header>
              <div class="card-header">
                <h3>项目信息</h3>
              </div>
            </template>
            <div class="project-info">
              <el-descriptions :column="1" border>
                <el-descriptions-item label="创建者">
                  {{ project.creator?.username || '未知' }}
                </el-descriptions-item>
                <el-descriptions-item label="开始日期">
                  {{ formatDate(project.start_date) }}
                </el-descriptions-item>
                <el-descriptions-item label="结束日期">
                  {{ formatDate(project.end_date) }}
                </el-descriptions-item>
                <el-descriptions-item label="项目状态">
                  <el-tag :type="getStatusTagType(project.status)">{{ project.status }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="优先级">
                  {{ project.priority }}
                </el-descriptions-item>
                <el-descriptions-item label="成员数量">
                  {{ project.members?.length || 0 }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>
          
          <!-- 操作按钮 -->
          <el-card class="content-card">
            <template #header>
              <div class="card-header">
                <h3>操作</h3>
              </div>
            </template>
            <div class="action-list">
              <router-link :to="{ name: 'ProjectList' }">
                <el-button type="info" class="full-width-btn">返回项目列表</el-button>
              </router-link>
              <el-button 
                v-if="canEdit" 
                type="primary" 
                class="full-width-btn mt-2"
                @click="changeStatus"
              >
                {{ getNextStatusText() }}
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 确认删除对话框 -->
      <el-dialog
        v-model="showDeleteConfirm"
        title="确认删除"
        width="30%"
      >
        <span>确定要删除项目 <strong>{{ project.name }}</strong> 吗？这个操作不可撤销。</span>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showDeleteConfirm = false">取消</el-button>
            <el-button
              type="danger"
              :loading="deleting"
              @click="deleteProject"
            >
              {{ deleting ? '删除中...' : '确认删除' }}
            </el-button>
          </span>
        </template>
      </el-dialog>
      
      <!-- 确认删除文件对话框 -->
      <el-dialog
        v-model="showDeleteFileConfirm"
        title="确认删除文件"
        width="30%"
      >
        <span>确定要删除文件 <strong>{{ fileToDelete?.original_name }}</strong> 吗？这个操作不可撤销。</span>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showDeleteFileConfirm = false">取消</el-button>
            <el-button
              type="danger"
              :loading="deletingFile"
              @click="deleteFile"
            >
              {{ deletingFile ? '删除中...' : '确认删除' }}
            </el-button>
          </span>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import { Document, Loading } from '@element-plus/icons-vue'

export default {
  name: 'ProjectDetail',
  components: {
    FileUpload,
    Document,
    Loading
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    // 状态
    const project = ref({})
    const loading = ref(true)
    const error = ref(null)
    const showDeleteConfirm = ref(false)
    const deleting = ref(false)
    
    // 文件相关状态
    const fileUploadRef = ref(null)
    const showUploader = ref(false)
    const projectFiles = ref([])
    const fileToDelete = ref(null)
    const showDeleteFileConfirm = ref(false)
    const deletingFile = ref(false)
    
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
    
    // 计算当前用户是否为创建者
    const isCreator = computed(() => {
      if (!currentUser.value || !project.value) return false;
      
      // 更严格的创建者判断逻辑
      const isCreatorById = currentUser.value.id === project.value.creator_id;
      const isCreatorByObject = project.value.creator && 
                              currentUser.value.id === project.value.creator.id;
      
      console.log("当前用户ID:", currentUser.value.id);
      console.log("项目信息:", project.value);
      console.log("项目创建者ID:", project.value.creator_id);
      console.log("通过ID判断是否为创建者:", isCreatorById);
      console.log("通过对象判断是否为创建者:", isCreatorByObject);
      
      return isCreatorById || isCreatorByObject;
    })
    
    // 计算当前用户是否可以编辑项目
    const canEdit = computed(() => {
      if (!currentUser.value || !project.value || !project.value.members) return false
      
      // 创建者可以编辑
      if (isCreator.value) return true
      
      // 检查是否为项目成员
      return project.value.members.some(member => 
        member.user_id === currentUser.value.id
      )
    })
    
    // 加载项目数据
    const loadProject = async () => {
      const projectId = route.params.id
      if (!projectId) {
        error.value = '项目ID无效'
        loading.value = false
        return Promise.reject('项目ID无效');
      }
      
      loading.value = true
      
      try {
        // 添加认证令牌
        const token = localStorage.getItem('token')
        
        const response = await axios.get(`/api/v1/projects/${projectId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        project.value = response.data
        
        console.log("项目详情加载完成:", project.value)
        console.log("当前用户:", currentUser.value)
        console.log("项目创建者ID:", project.value.creator_id)
        
        // 项目加载成功后加载文件
        await loadProjectFiles();
        
        return Promise.resolve(project.value);
      } catch (err) {
        console.error('加载项目详情失败:', err)
        error.value = '加载项目详情失败，请稍后重试'
        return Promise.reject(err);
      } finally {
        loading.value = false
      }
    }
    
    // 确认删除
    const confirmDelete = () => {
      showDeleteConfirm.value = true
    }
    
    // 删除项目
    const deleteProject = async () => {
      if (!isCreator.value) {
        ElMessage.error('只有项目创建者可以删除项目');
        showDeleteConfirm.value = false;
        return;
      }
      
      deleting.value = true;
      
      try {
        // 添加认证刷新逻辑，确保令牌是最新的
        const token = localStorage.getItem('token');
        console.log("准备删除项目:", project.value.id);
        console.log("使用的认证令牌:", token ? "令牌已提供" : "令牌缺失");
        
        await axios.delete(`/api/v1/projects/${project.value.id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        ElMessage.success('项目已成功删除');
        showDeleteConfirm.value = false;
        
        // 跳转回项目列表
        router.push({ name: 'ProjectList' });
      } catch (err) {
        console.error('删除项目失败:', err);
        
        if (err.response) {
          console.error('服务器响应:', err.response.status, err.response.data);
          if (err.response.status === 403) {
            ElMessage.error(err.response.data.msg || '您没有权限删除此项目');
          } else {
            ElMessage.error(err.response.data.msg || '删除项目失败，请稍后重试');
          }
        } else {
          ElMessage.error('删除项目失败，请检查网络连接');
        }
      } finally {
        deleting.value = false;
      }
    }
    
    // 更改项目状态
    const changeStatus = async () => {
      if (!canEdit.value) return
      
      const currentStatus = project.value.status
      let newStatus = '进行中'
      
      // 状态转换: 进行中 -> 已完成 -> 已取消 -> 进行中
      if (currentStatus === '进行中') {
        newStatus = '已完成'
      } else if (currentStatus === '已完成') {
        newStatus = '已取消'
      } else if (currentStatus === '已取消') {
        newStatus = '进行中'
      }
      
      try {
        const response = await axios.put(`/api/v1/projects/${project.value.id}`, {
          status: newStatus
        })
        
        project.value = response.data
        ElMessage.success(`项目状态已更新为: ${newStatus}`)
      } catch (err) {
        console.error('更新项目状态失败:', err)
        ElMessage.error('更新项目状态失败，请稍后重试')
      }
    }
    
    // 获取下一个状态的文本
    const getNextStatusText = () => {
      const currentStatus = project.value.status
      
      switch (currentStatus) {
        case '进行中':
          return '标记为已完成'
        case '已完成':
          return '标记为已取消'
        case '已取消':
          return '重新激活项目'
        default:
          return '更改状态'
      }
    }
    
    // 获取状态对应的标签类型
    const getStatusTagType = (status) => {
      switch (status) {
        case '进行中':
          return 'success'
        case '已完成':
          return 'primary'
        case '已取消':
          return 'danger'
        default:
          return 'info'
      }
    }
    
    // 根据用户名获取颜色
    const getColorByUsername = (username) => {
      if (!username) return 'secondary'
      
      const colors = ['primary', 'success', 'warning', 'danger', 'info']
      const index = username.charCodeAt(0) % colors.length
      return colors[index]
    }
    
    // 获取用户名首字母
    const getInitials = (username) => {
      if (!username) return '?'
      
      return username.charAt(0).toUpperCase()
    }
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '未设置'
      
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN')
    }
    
    // 格式化日期时间
    const formatDateTime = (dateTimeString) => {
      if (!dateTimeString) return '未设置'
      
      const date = new Date(dateTimeString)
      return date.toLocaleString('zh-CN')
    }
    
    // 加载项目文件
    const loadProjectFiles = async () => {
      // 确保项目ID存在
      if (!project.value || !project.value.id) {
        console.warn('无法加载项目文件：项目ID未定义');
        return;
      }
      
      try {
        // 使用确定存在的项目ID
        const projectId = project.value.id;
        console.log(`尝试加载项目 ${projectId} 的文件`);
        
        const response = await axios.get(`/api/v1/projects/${projectId}/files`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        projectFiles.value = response.data || []
      } catch (err) {
        console.error('加载项目文件失败:', err)
        ElMessage.error('加载项目文件失败')
      }
    }
    
    // 处理文件上传成功
    const handleFileUploaded = async (fileInfo) => {
      try {
        // 将文件关联到项目
        await axios.post(`/api/v1/projects/${project.value.id}/files`, {
          file_path: fileInfo.file_path,
          original_name: fileInfo.original_name,
          file_size: fileInfo.file_size,
          file_type: fileInfo.file_type
        }, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        // 重新加载项目文件列表
        await loadProjectFiles()
        ElMessage.success('文件已成功添加到项目')
      } catch (err) {
        console.error('关联文件到项目失败:', err)
        ElMessage.error('关联文件到项目失败')
      }
    }
    
    // 处理文件移除
    const handleFileRemoved = (fileInfo) => {
      console.log('文件已移除', fileInfo)
    }
    
    // 确认删除文件
    const confirmDeleteFile = (file) => {
      fileToDelete.value = file
      showDeleteFileConfirm.value = true
    }
    
    // 删除文件
    const deleteFile = async () => {
      if (!fileToDelete.value || !fileToDelete.value.id) {
        showDeleteFileConfirm.value = false
        return
      }
      
      deletingFile.value = true
      
      try {
        await axios.delete(`/api/v1/projects/${project.value.id}/files/${fileToDelete.value.id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        ElMessage.success('文件已成功删除')
        await loadProjectFiles()
      } catch (err) {
        console.error('删除文件失败:', err)
        ElMessage.error('删除文件失败，请稍后重试')
      } finally {
        deletingFile.value = false
        showDeleteFileConfirm.value = false
      }
    }
    
    // 下载文件
    const downloadFile = (file) => {
      if (!file || !file.file_path) return
      
      const downloadUrl = `${import.meta.env.VITE_API_URL || ''}/api/v1/files/download/${file.file_path}`
      window.open(downloadUrl, '_blank')
    }
    
    // 格式化文件大小
    const formatFileSize = (size) => {
      if (!size) return '未知大小'
      
      if (size < 1024) {
        return size + ' B'
      } else if (size < 1024 * 1024) {
        return (size / 1024).toFixed(2) + ' KB'
      } else if (size < 1024 * 1024 * 1024) {
        return (size / 1024 / 1024).toFixed(2) + ' MB'
      } else {
        return (size / 1024 / 1024 / 1024).toFixed(2) + ' GB'
      }
    }
    
    // 页面加载时获取项目数据和文件
    onMounted(() => {
      loadProject().then(() => {
        // 只有在项目加载成功后才加载文件
        if (project.value && project.value.id) {
          loadProjectFiles();
        }
      });
    })
    
    return {
      project,
      loading,
      error,
      isCreator,
      canEdit,
      showDeleteConfirm,
      deleting,
      confirmDelete,
      deleteProject,
      changeStatus,
      getNextStatusText,
      getStatusTagType,
      getColorByUsername,
      getInitials,
      formatDate,
      formatDateTime,
      
      // 文件相关
      fileUploadRef,
      showUploader,
      projectFiles,
      fileToDelete,
      showDeleteFileConfirm,
      deletingFile,
      handleFileUploaded,
      handleFileRemoved,
      confirmDeleteFile,
      deleteFile,
      downloadFile,
      formatFileSize
    }
  }
}
</script>

<style scoped>
.project-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.title-section {
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0 0 10px 0;
  font-size: 22px;
}

.status-tags {
  margin-bottom: 10px;
}

.meta-info {
  color: #909399;
  margin-bottom: 20px;
}

.content-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
}

.card-body {
  padding: 5px 0;
}

.user-info {
  display: flex;
  align-items: center;
}

.member-avatar {
  margin-right: 10px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 500;
}

.email {
  font-size: 12px;
  color: #909399;
}

.action-list {
  display: flex;
  flex-direction: column;
}

.full-width-btn {
  width: 100%;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 0;
}

.loading-text {
  margin-top: 15px;
  color: #909399;
}

.bg-primary {
  background-color: #409EFF;
}

.bg-success {
  background-color: #67C23A;
}

.bg-warning {
  background-color: #E6A23C;
}

.bg-danger {
  background-color: #F56C6C;
}

.bg-info {
  background-color: #909399;
}

.bg-secondary {
  background-color: #909399;
}

.ml-2 {
  margin-left: 8px;
}

.mt-2 {
  margin-top: 8px;
}

.project-info {
  padding: 5px 0;
}

.uploader-section {
  margin-bottom: 20px;
  padding: 10px;
  border: 1px dashed #ccc;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.file-list {
  margin-top: 10px;
}

.file-name {
  display: flex;
  align-items: center;
}

.file-icon {
  margin-right: 8px;
  font-size: 18px;
  color: #909399;
}

.mr-1 {
  margin-right: 8px;
}
</style> 