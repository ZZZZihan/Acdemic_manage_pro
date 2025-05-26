<template>
  <div class="edit-meeting-container">
    <div class="page-header">
      <h2>编辑会议</h2>
      <div>
        <el-button @click="$router.go(-1)">返回</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
      </div>
    </div>

    <el-card v-if="loading" class="loading-card">
      <el-skeleton :rows="10" animated />
    </el-card>

    <el-form 
      v-else
      ref="meetingFormRef" 
      :model="meetingForm" 
      :rules="rules" 
      label-width="100px"
      class="meeting-form"
    >
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
          </div>
        </template>
        
        <el-form-item label="会议标题" prop="title">
          <el-input v-model="meetingForm.title" placeholder="请输入会议标题" />
        </el-form-item>
        
        <el-form-item label="关联项目" prop="project_id">
          <el-select 
            v-model="meetingForm.project_id" 
            placeholder="请选择关联项目（可选）" 
            filterable 
            clearable
            @change="handleProjectChange"
          >
            <el-option 
              v-for="project in projects" 
              :key="project.id" 
              :label="project.name" 
              :value="project.id" 
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="会议时间" required>
          <div class="time-range-picker">
            <el-form-item prop="start_time" class="time-item">
              <el-date-picker
                v-model="meetingForm.start_time"
                type="datetime"
                placeholder="开始时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm"
                :disabled-date="disablePastDates"
              />
            </el-form-item>
            <span class="time-separator">至</span>
            <el-form-item prop="end_time" class="time-item">
              <el-date-picker
                v-model="meetingForm.end_time"
                type="datetime"
                placeholder="结束时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm"
                :disabled-date="disablePastDates"
              />
            </el-form-item>
          </div>
        </el-form-item>
        
        <el-form-item label="会议地点" prop="location">
          <el-input v-model="meetingForm.location" placeholder="请输入会议地点（线上会议可填写会议平台或链接）" />
        </el-form-item>
        
        <el-form-item label="会议状态" prop="status">
          <el-select v-model="meetingForm.status" placeholder="请选择会议状态">
            <el-option label="未开始" value="pending" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已结束" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-card>
      
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>会议内容</span>
          </div>
        </template>
        
        <el-form-item label="会议内容" prop="content">
          <el-input 
            v-model="meetingForm.content" 
            type="textarea" 
            :rows="6" 
            placeholder="请输入会议内容，包括会议描述和会议议程等信息" 
          />
        </el-form-item>
      </el-card>
      
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>参会人员</span>
          </div>
        </template>
        
        <div class="participants-header">
          <el-button type="primary" @click="showAddParticipantDialog" plain size="small" class="add-participant-btn">
            添加参会人员
          </el-button>
        </div>
        
        <el-empty v-if="participants.length === 0" description="暂无参会人员" />
        
        <el-table v-else :data="participants" style="width: 100%">
          <el-table-column label="姓名" min-width="180">
            <template #default="{ row }">
              <div class="user-info">
                <el-avatar :size="30" :src="row.avatar">{{ row.name.substring(0, 1) }}</el-avatar>
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="100">
            <template #default="{ row, $index }">
              <el-button type="danger" size="small" @click="removeParticipant($index)" text>
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>会议材料</span>
          </div>
        </template>
        
        <el-upload
          :action="`${baseUrl}/api/v1/meetings/attachments/upload`"
          :headers="uploadHeaders"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :file-list="attachments"
          multiple
        >
          <el-button type="primary" plain>点击上传</el-button>
          <template #tip>
            <div class="el-upload__tip">
              可以上传任意类型文件作为会议材料
            </div>
          </template>
        </el-upload>
      </el-card>
    </el-form>
    
    <!-- 添加参会人员对话框 -->
    <el-dialog v-model="participantDialogVisible" title="添加参会人员" width="500px">
      <el-form :model="participantForm" label-width="80px">
        <el-form-item label="选择用户">
          <div v-if="users.length === 0" class="empty-users">
            <el-empty description="暂无可选用户" />
          </div>
          <el-select
            v-else
            v-model="participantForm.selectedUsers"
            multiple
            filterable
            placeholder="请选择要添加的用户"
            style="width: 100%"
          >
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="user.name || user.username"
              :value="user.id"
              :disabled="isUserSelected(user.id)"
            >
              <div class="user-option">
                <el-avatar :size="30">{{ (user.name || user.username).substring(0, 1) }}</el-avatar>
                <span>{{ user.name || user.username }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="participantDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="addParticipants">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from '@/utils/axios'  // 导入配置好的axios实例
import { useUserStore } from '@/stores/user'

export default {
  name: 'MeetingEdit',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const meetingId = route.params.id
    const userStore = useUserStore()
    const meetingFormRef = ref(null)
    const loading = ref(true)  // 初始设置为true，表示正在加载
    
    // 基本数据
    const meetingForm = reactive({
      title: '',
      project_id: null,
      start_time: '',
      end_time: '',
      location: '',
      status: 'pending',
      content: '',
      participants: [],
      attachments: []
    })
    
    // 关联数据
    const projects = ref([])
    const users = ref([])
    const participants = ref([])
    const attachments = ref([])
    const submitting = ref(false)
    
    // 参会人员对话框
    const participantDialogVisible = ref(false)
    const participantForm = reactive({
      selectedUsers: []
    })
    
    // 上传相关
    const baseUrl = import.meta.env.VITE_API_URL || ''  // 使用和axios相同的baseURL
    const uploadHeaders = computed(() => ({
      Authorization: `Bearer ${userStore.token}`
    }))
    
    // 表单规则
    const rules = {
      title: [
        { required: true, message: '请输入会议标题', trigger: 'blur' },
        { min: 2, max: 100, message: '长度在2到100个字符之间', trigger: 'blur' }
      ],
      start_time: [
        { required: true, message: '请选择开始时间', trigger: 'change' }
      ],
      end_time: [
        { required: true, message: '请选择结束时间', trigger: 'change' },
        { 
          validator: (rule, value, callback) => {
            if (value && meetingForm.start_time && new Date(value) <= new Date(meetingForm.start_time)) {
              callback(new Error('结束时间必须晚于开始时间'))
            } else {
              callback()
            }
          }, 
          trigger: 'change' 
        }
      ],
      location: [
        { required: true, message: '请输入会议地点', trigger: 'blur' }
      ],
      status: [
        { required: true, message: '请选择会议状态', trigger: 'change' }
      ],
      content: [
        { required: true, message: '请输入会议内容', trigger: 'blur' }
      ]
    }
    
    // 计算属性
    const availableUsers = computed(() => {
      return users.value.filter(user => {
        // 过滤掉已经添加的参会者
        return !participants.value.some(p => p.id === user.id)
      })
    })
    
    // 方法
    // 禁用过去的日期
    const disablePastDates = (date) => {
      return date < new Date(new Date().setHours(0, 0, 0, 0))
    }
    
    // 处理项目变化
    const handleProjectChange = async (projectId) => {
      if (!projectId) return
      
      try {
        const response = await axios.get(`/api/v1/projects/${projectId}/members`)
        console.log('获取项目成员成功:', response.data)
        
        const members = response.data.members || response.data || []
        const projectMembers = members.map(member => {
          const user = member.user || member
          return {
            id: user.id,
            name: user.name || user.username,
            avatar: user.avatar || ''
          }
        })
        
        // 更新参会人员，避免重复
        participants.value = mergeParticipants(participants.value, projectMembers)
      } catch (error) {
        console.error('获取项目成员失败:', error)
      }
    }
    
    // 合并参会人员，避免重复
    const mergeParticipants = (currentParticipants, newParticipants) => {
      const merged = [...currentParticipants]
      
      newParticipants.forEach(newP => {
        if (!merged.some(p => p.id === newP.id)) {
          merged.push(newP)
        }
      })
      
      return merged
    }
    
    // 上传前验证
    const beforeUpload = (file) => {
      const maxSize = 20 * 1024 * 1024 // 20MB
      if (file.size > maxSize) {
        ElMessage.error('文件大小不能超过20MB')
        return false
      }
      return true
    }
    
    // 上传成功
    const handleUploadSuccess = (response, file) => {
      ElMessage.success('上传成功')
      attachments.value.push({
        name: file.name,
        url: response.url,
        file_path: response.file_path
      })
    }
    
    // 上传失败
    const handleUploadError = () => {
      ElMessage.error('上传失败')
    }
    
    // 显示添加参会人员对话框
    const showAddParticipantDialog = () => {
      participantForm.selectedUsers = []
      participantDialogVisible.value = true
    }
    
    // 判断用户是否已选择
    const isUserSelected = (userId) => {
      return participants.value.some(p => p.id === userId)
    }
    
    // 添加参会人员
    const addParticipants = () => {
      if (participantForm.selectedUsers.length === 0) {
        ElMessage.warning('请选择至少一名用户')
        return
      }
      
      const selectedUserObjects = users.value.filter(user => 
        participantForm.selectedUsers.includes(user.id)
      ).map(user => ({
        id: user.id,
        name: user.name || user.username,
        avatar: user.avatar || ''
      }))
      
      participants.value = mergeParticipants(participants.value, selectedUserObjects)
      participantDialogVisible.value = false
    }
    
    // 移除参会人员
    const removeParticipant = (index) => {
      participants.value.splice(index, 1)
    }
    
    // 提交表单
    const submitForm = async () => {
      await meetingFormRef.value.validate(async (valid) => {
        if (!valid) {
          ElMessage.error('请填写必填项')
          return
        }
        
        // 验证开始时间和结束时间
        if (new Date(meetingForm.end_time) <= new Date(meetingForm.start_time)) {
          ElMessage.error('结束时间必须晚于开始时间')
          return
        }
        
        // 验证至少有一名参会人员
        if (participants.value.length === 0) {
          ElMessage.error('请至少添加一名参会人员')
          return
        }
        
        submitting.value = true
        
        try {
          const meetingData = {
            ...meetingForm,
            // 将content字段映射到后端需要的字段
            description: meetingForm.content,
            agenda: meetingForm.content,
            // 使用当前用户作为主持人
            host_id: userStore.user?.id,
            participants: participants.value.map(p => ({
              user_id: p.id
            })),
            attachments: attachments.value.map(a => ({
              name: a.name,
              file_path: a.file_path
            }))
          }
          

          
          const response = await axios.put(`/api/v1/meetings/${meetingId}`, meetingData)
          
          ElMessage.success('会议更新成功')
          router.push(`/meetings/${meetingId}`)
        } catch (error) {
          console.error('更新会议失败:', error)
          ElMessage.error('更新会议失败：' + (error.response?.data?.message || '未授权，请重新登录后再试'))
        } finally {
          submitting.value = false
        }
      })
    }
    
    // 加载会议数据
    const loadMeeting = async () => {
      loading.value = true
      try {
        const response = await axios.get(`/api/v1/meetings/${meetingId}`)
        const meeting = response.data
        
        // 填充表单数据
        meetingForm.title = meeting.title
        meetingForm.project_id = meeting.project_id
        meetingForm.start_time = meeting.start_time
        meetingForm.end_time = meeting.end_time
        meetingForm.location = meeting.location
        meetingForm.status = meeting.status
        // 使用description或agenda填充content字段
        meetingForm.content = meeting.description || meeting.agenda || ''
        
        // 加载参会人员
        if (meeting.participants && meeting.participants.length > 0) {
          participants.value = meeting.participants.map(p => ({
            id: p.user.id,
            name: p.user.name || p.user.username,
            avatar: p.user.avatar || ''
          }))
        }
        
        // 加载附件
        if (meeting.attachments && meeting.attachments.length > 0) {
          attachments.value = meeting.attachments
        }
        
        console.log('会议数据加载成功:', meeting)
      } catch (error) {
        console.error('加载会议详情失败:', error)
        ElMessage.error('加载会议详情失败，请稍后再试')
        router.push('/meetings')
      } finally {
        loading.value = false
      }
    }
    
    // 加载数据
    const loadProjects = async () => {
      try {
        const response = await axios.get('/api/v1/projects', { 
          params: { limit: 100, tab: 'my' } 
        })
        console.log('获取项目数据成功:', response.data)
        // API返回格式调整
        projects.value = response.data.projects || response.data || []
      } catch (error) {
        console.error('获取项目列表失败:', error)
      }
    }
    
    const loadUsers = async () => {
      try {
        const response = await axios.get('/api/v1/users')
        
        // 调试输出API返回数据
        console.log('获取用户数据成功:', response.data)
        
        // API返回的是数组而不是{users: [...]}对象
        users.value = response.data || []
      } catch (error) {
        console.error('获取用户列表失败:', error)
        ElMessage.error('获取用户列表失败，请刷新重试')
      }
    }
    
    onMounted(() => {
      // 首先加载会议数据
      loadMeeting()
      // 然后加载其他相关数据
      loadProjects()
      loadUsers()
    })
    
    return {
      meetingFormRef,
      meetingForm,
      rules,
      projects,
      users,
      participants,
      attachments,
      loading,
      submitting,
      participantDialogVisible,
      participantForm,
      baseUrl,
      uploadHeaders,
      availableUsers,
      
      disablePastDates,
      handleProjectChange,
      beforeUpload,
      handleUploadSuccess,
      handleUploadError,
      showAddParticipantDialog,
      isUserSelected,
      addParticipants,
      removeParticipant,
      submitForm
    }
  }
}
</script>

<style scoped>
.edit-meeting-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.meeting-form {
  max-width: 1000px;
  margin: 0 auto;
}

.form-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.time-range-picker {
  display: flex;
  align-items: center;
  gap: 10px;
}

.time-item {
  margin-bottom: 0;
}

.time-separator {
  color: #606266;
}

.participants-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 20px;
}

.add-participant-btn {
  margin-left: 16px;
}

.user-option,
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.empty-users {
  padding: 20px;
  text-align: center;
}

:deep(.el-upload-list__item) {
  transition: all 0.3s;
}

.loading-card {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style> 