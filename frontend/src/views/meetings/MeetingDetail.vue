<template>
  <div class="meeting-detail-container" v-loading="loading">
    <div class="page-header">
      <h2>{{ meeting.title || '会议详情' }}</h2>
      <div>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="editMeeting" v-if="canEdit">编辑</el-button>
        <el-dropdown v-if="canEdit" trigger="click" @command="handleCommand">
          <el-button type="primary" plain>
            <span>更多操作</span>
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="duplicate">复制会议</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除会议</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 会议未找到提示 -->
    <el-empty v-if="notFound" description="会议不存在或已被删除">
      <el-button type="primary" @click="$router.push('/meetings')">返回会议列表</el-button>
    </el-empty>

    <div v-else-if="!loading" class="meeting-detail-content">
      <!-- 基本信息 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-tag :type="statusType" effect="plain">{{ statusText }}</el-tag>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="组织者">
            <div class="user-info">
              <el-avatar :size="24" :src="meeting.organizer?.avatar">
                {{ meeting.organizer?.name?.substring(0, 1) }}
              </el-avatar>
              <span>{{ meeting.organizer?.name }}</span>
            </div>
          </el-descriptions-item>
          
          <el-descriptions-item label="关联项目">
            <router-link 
              v-if="meeting.project" 
              :to="`/projects/${meeting.project.id}`"
              class="project-link"
            >
              {{ meeting.project.name }}
            </router-link>
            <span v-else>无</span>
          </el-descriptions-item>
          
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(meeting.start_time) }}
          </el-descriptions-item>
          
          <el-descriptions-item label="结束时间">
            {{ formatDateTime(meeting.end_time) }}
          </el-descriptions-item>
          
          <el-descriptions-item label="会议地点">
            {{ meeting.location }}
          </el-descriptions-item>
          
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(meeting.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
      
      <!-- 会议内容 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>会议内容</span>
          </div>
        </template>
        
        <div class="content-section">
          <h4>会议议程</h4>
          <div class="content-text">{{ meeting.agenda || '无' }}</div>
        </div>
        
        <div class="content-section" v-if="meeting.notes">
          <h4>会议备注</h4>
          <div class="content-text">{{ meeting.notes }}</div>
        </div>
      </el-card>
      
      <!-- 参会人员 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>参会人员 ({{ meeting.participants?.length || 0 }})</span>
            <el-button 
              type="primary" 
              plain 
              size="small" 
              @click="showAddParticipant"
              v-if="canEdit"
            >
              添加参会人员
            </el-button>
          </div>
        </template>
        
        <div v-if="meeting.participants && meeting.participants.length > 0">
          <el-table :data="meeting.participants" style="width: 100%">
            <el-table-column label="用户">
              <template #default="scope">
                <div class="user-info">
                  <el-avatar :size="30" :src="scope.row.user.avatar">
                    {{ scope.row.user.name.substring(0, 1) }}
                  </el-avatar>
                  <div class="user-details">
                    <div>{{ scope.row.user.name }}</div>
                    <div class="user-email">{{ scope.row.user.email }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column prop="role" label="角色" width="120">
              <template #default="scope">
                <el-tag size="small" effect="plain">
                  {{ scope.row.role }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="150" v-if="canEdit">
              <template #default="scope">
                <el-button 
                  type="danger" 
                  size="small" 
                  plain
                  @click="removeParticipant(scope.row)"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <el-empty v-else description="暂无参会人员" />
      </el-card>
      
      <!-- 会议附件 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>会议附件 ({{ meeting.attachments?.length || 0 }})</span>
            <el-upload
              v-if="canEdit"
              class="upload-attachment"
              :action="`/api/v1/meetings/${meetingId}/attachments`"
              :headers="uploadHeaders"
              :on-success="handleAttachmentSuccess"
              :on-error="handleAttachmentError"
              :show-file-list="false"
            >
              <el-button type="primary" plain size="small">上传附件</el-button>
            </el-upload>
          </div>
        </template>
        
        <div v-if="meeting.attachments && meeting.attachments.length > 0" class="attachment-list">
          <div v-for="attachment in meeting.attachments" :key="attachment.id" class="attachment-item">
            <el-icon><document /></el-icon>
            <div class="attachment-info">
              <div class="attachment-name">{{ attachment.name }}</div>
              <div class="attachment-meta">
                <span>{{ formatFileSize(attachment.size) }}</span>
                <span>{{ formatDateTime(attachment.created_at) }}</span>
              </div>
            </div>
            <div class="attachment-actions">
              <el-button type="primary" size="small" plain @click="downloadAttachment(attachment)">
                下载
              </el-button>
              <el-button 
                v-if="canEdit" 
                type="danger" 
                size="small" 
                plain
                @click="removeAttachment(attachment)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
        
        <el-empty v-else description="暂无会议附件" />
      </el-card>
      
      <!-- 会议纪要 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>会议纪要</span>
            <el-button 
              type="primary" 
              plain 
              size="small" 
              @click="editMinutes"
              v-if="canEdit"
            >
              {{ meeting.minutes ? '编辑' : '添加' }}会议纪要
            </el-button>
          </div>
        </template>
        
        <div v-if="meeting.minutes" class="minutes-content">
          <div v-html="meeting.minutes"></div>
        </div>
        
        <el-empty v-else description="暂无会议纪要" />
      </el-card>
    </div>
    
    <!-- 添加参会人员对话框 -->
    <el-dialog title="添加参会人员" v-model="participantDialogVisible" width="500px">
      <el-form :model="participantForm" label-width="80px">
        <el-form-item label="用户">
          <el-select
            v-model="participantForm.user_id"
            filterable
            remote
            :remote-method="searchUsers"
            placeholder="搜索用户"
            style="width: 100%"
            :loading="searchingUsers"
          >
            <el-option
              v-for="user in userOptions"
              :key="user.id"
              :label="user.name"
              :value="user.id"
            >
              <div class="user-option">
                <el-avatar :size="24" :src="user.avatar">{{ user.name.substring(0, 1) }}</el-avatar>
                <span>{{ user.name }}</span>
                <span class="user-email">{{ user.email }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="角色">
          <el-select v-model="participantForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="参会者" value="参会者" />
            <el-option label="主持人" value="主持人" />
            <el-option label="记录员" value="记录员" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="participantDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="addParticipant" :loading="addingParticipant">
            确认添加
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 编辑会议纪要对话框 -->
    <el-dialog 
      :title="meeting.minutes ? '编辑会议纪要' : '添加会议纪要'" 
      v-model="minutesDialogVisible" 
      width="800px"
    >
      <div class="minutes-editor">
        <!-- 这里可以集成富文本编辑器 -->
        <el-input
          v-model="minutesForm.content"
          type="textarea"
          :rows="15"
          placeholder="请输入会议纪要内容..."
        />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="minutesDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveMinutes" :loading="savingMinutes">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 确认删除对话框 -->
    <el-dialog
      title="确认删除"
      v-model="deleteConfirmVisible"
      width="400px"
    >
      <div>确定要删除会议 "{{ meeting.title }}" 吗？此操作不可撤销。</div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="deleteConfirmVisible = false">取消</el-button>
          <el-button type="danger" @click="confirmDelete" :loading="deleting">
            确认删除
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Document } from '@element-plus/icons-vue'
import axios from '@/utils/axios'
import { useUserStore } from '@/stores/user'
import { formatDate } from '@/utils/format'

export default {
  name: 'MeetingDetail',
  components: { ArrowDown, Document },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const userStore = useUserStore()
    
    const meetingId = computed(() => route.params.id)
    const loading = ref(true)
    const notFound = ref(false)
    
    // 会议数据
    const meeting = ref({
      title: '',
      start_time: '',
      end_time: '',
      location: '',
      status: 'pending',
      project: null,
      agenda: '',
      notes: '',
      organizer: null,
      organizer_id: null,
      participants: [],
      attachments: [],
      minutes: null,
      created_at: ''
    })
    
    // 判断当前用户是否可以编辑会议
    const canEdit = computed(() => {
      // 用户是会议的组织者 - 确保类型一致性比较
      const isOrganizer = (meeting.value.organizer_id && userStore.user?.id && 
                          parseInt(meeting.value.organizer_id) === parseInt(userStore.user.id)) || 
                         (meeting.value.organizer?.id && userStore.user?.id &&
                          parseInt(meeting.value.organizer.id) === parseInt(userStore.user.id))
      // 管理员权限
      const isAdmin = userStore.isAdmin
      
      return isOrganizer || isAdmin
    })
    
    // 根据状态获取类型和文本
    const statusType = computed(() => {
      const statusMap = {
        'pending': 'primary',
        'in_progress': 'success',
        'completed': 'info',
        'cancelled': 'danger'
      }
      return statusMap[meeting.value.status] || 'info'
    })
    
    const statusText = computed(() => {
      const statusMap = {
        'pending': '未开始',
        'in_progress': '进行中',
        'completed': '已结束',
        'cancelled': '已取消'
      }
      return statusMap[meeting.value.status] || '未知状态'
    })
    

    
    // 格式化日期时间
    const formatDateTime = (dateStr) => {
      if (!dateStr) return '未设置'
      return formatDate(new Date(dateStr), 'YYYY-MM-DD HH:mm')
    }
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    // 上传文件所需的headers
    const uploadHeaders = computed(() => {
      return {
        Authorization: `Bearer ${userStore.token}`
      }
    })
    
    // 加载会议详情
    const loadMeetingDetail = async () => {
      loading.value = true
      
      try {
        const response = await axios.get(`/api/v1/meetings/${meetingId.value}`)
        meeting.value = response.data
      } catch (error) {
        console.error('获取会议详情失败:', error)
        
        if (error.response && error.response.status === 404) {
          notFound.value = true
        } else {
          ElMessage.error('获取会议详情失败')
        }
      } finally {
        loading.value = false
      }
    }
    
    // 编辑会议
    const editMeeting = () => {
      router.push(`/meetings/${meetingId.value}/edit`)
    }
    
    // 处理下拉菜单命令
    const handleCommand = (command) => {
      if (command === 'duplicate') {
        duplicateMeeting()
      } else if (command === 'delete') {
        deleteConfirmVisible.value = true
      }
    }
    
    // 复制会议
    const duplicateMeeting = () => {
      router.push({
        path: '/meetings/create',
        query: { duplicate: meetingId.value }
      })
    }
    
    // 参会人员相关
    const participantDialogVisible = ref(false)
    const participantForm = reactive({
      user_id: null,
      role: '参会者'
    })
    const userOptions = ref([])
    const searchingUsers = ref(false)
    const addingParticipant = ref(false)
    
    // 显示添加参会人员对话框
    const showAddParticipant = () => {
      participantForm.user_id = null
      participantForm.role = '参会者'
      participantDialogVisible.value = true
    }
    
    // 搜索用户
    const searchUsers = async (query) => {
      if (query.length < 2) return
      
      searchingUsers.value = true
      try {
        const response = await axios.get('/api/v1/users/search', {
          params: { query }
        })
        userOptions.value = response.data
      } catch (error) {
        console.error('搜索用户失败:', error)
      } finally {
        searchingUsers.value = false
      }
    }
    
    // 添加参会人员
    const addParticipant = async () => {
      if (!participantForm.user_id) {
        ElMessage.warning('请选择用户')
        return
      }
      
      addingParticipant.value = true
      try {
        await axios.post(`/api/v1/meetings/${meetingId.value}/participants`, {
          user_id: participantForm.user_id,
          role: participantForm.role
        })
        
        ElMessage.success('添加参会人员成功')
        loadMeetingDetail()
        participantDialogVisible.value = false
      } catch (error) {
        console.error('添加参会人员失败:', error)
        ElMessage.error('添加参会人员失败')
      } finally {
        addingParticipant.value = false
      }
    }
    
    // 移除参会人员
    const removeParticipant = async (participant) => {
      try {
        await ElMessageBox.confirm(
          `确定移除参会人员 ${participant.user.name} 吗？`,
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        await axios.delete(`/api/v1/meetings/${meetingId.value}/participants/${participant.id}`)
        ElMessage.success('移除参会人员成功')
        loadMeetingDetail()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('移除参会人员失败:', error)
          ElMessage.error('移除参会人员失败')
        }
      }
    }
    
    // 附件相关
    // 处理附件上传成功
    const handleAttachmentSuccess = () => {
      ElMessage.success('附件上传成功')
      loadMeetingDetail()
    }
    
    // 处理附件上传失败
    const handleAttachmentError = () => {
      ElMessage.error('附件上传失败')
    }
    
    // 下载附件
    const downloadAttachment = (attachment) => {
      window.open(attachment.url, '_blank')
    }
    
    // 删除附件
    const removeAttachment = async (attachment) => {
      try {
        await ElMessageBox.confirm(
          `确定删除附件 ${attachment.name} 吗？`,
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        await axios.delete(`/api/v1/meetings/${meetingId.value}/attachments/${attachment.id}`)
        ElMessage.success('删除附件成功')
        loadMeetingDetail()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除附件失败:', error)
          ElMessage.error('删除附件失败')
        }
      }
    }
    
    // 会议纪要相关
    const minutesDialogVisible = ref(false)
    const minutesForm = reactive({
      content: ''
    })
    const savingMinutes = ref(false)
    
    // 编辑会议纪要
    const editMinutes = () => {
      minutesForm.content = meeting.value.minutes || ''
      minutesDialogVisible.value = true
    }
    
    // 保存会议纪要
    const saveMinutes = async () => {
      savingMinutes.value = true
      
      try {
        await axios.put(`/api/v1/meetings/${meetingId.value}/minutes`, {
          content: minutesForm.content
        })
        
        ElMessage.success('保存会议纪要成功')
        loadMeetingDetail()
        minutesDialogVisible.value = false
      } catch (error) {
        console.error('保存会议纪要失败:', error)
        ElMessage.error('保存会议纪要失败')
      } finally {
        savingMinutes.value = false
      }
    }
    
    // 删除会议相关
    const deleteConfirmVisible = ref(false)
    const deleting = ref(false)
    
    // 确认删除会议
    const confirmDelete = async () => {
      deleting.value = true
      
      try {
        await axios.delete(`/api/v1/meetings/${meetingId.value}`)
        ElMessage.success('删除会议成功')
        router.push('/meetings')
      } catch (error) {
        console.error('删除会议失败:', error)
        ElMessage.error('删除会议失败')
      } finally {
        deleting.value = false
        deleteConfirmVisible.value = false
      }
    }
    
    onMounted(() => {
      loadMeetingDetail()
    })
    
    return {
      meetingId,
      meeting,
      loading,
      notFound,
      canEdit,
      statusType,
      statusText,
      formatDateTime,
      formatFileSize,
      uploadHeaders,
      
      editMeeting,
      handleCommand,
      
      participantDialogVisible,
      participantForm,
      userOptions,
      searchingUsers,
      addingParticipant,
      showAddParticipant,
      searchUsers,
      addParticipant,
      removeParticipant,
      
      handleAttachmentSuccess,
      handleAttachmentError,
      downloadAttachment,
      removeAttachment,
      
      minutesDialogVisible,
      minutesForm,
      savingMinutes,
      editMinutes,
      saveMinutes,
      
      deleteConfirmVisible,
      deleting,
      confirmDelete
    }
  }
}
</script>

<style scoped>
.meeting-detail-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.meeting-detail-content {
  max-width: 900px;
  margin: 0 auto;
}

.detail-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info, .user-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-email {
  color: #909399;
  font-size: 12px;
}

.content-section {
  margin-bottom: 20px;
}

.content-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
  font-weight: 600;
  color: #303133;
}

.content-text {
  white-space: pre-line;
  line-height: 1.5;
}

.project-link {
  color: #409eff;
  text-decoration: none;
}

.project-link:hover {
  text-decoration: underline;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.attachment-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  background-color: #f8f8f8;
}

.attachment-info {
  flex: 1;
  margin-left: 10px;
}

.attachment-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.attachment-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 10px;
}

.attachment-actions {
  display: flex;
  gap: 8px;
}

.upload-attachment {
  display: inline-block;
}

.minutes-content {
  padding: 10px;
  border-radius: 4px;
  background-color: #f8f8f8;
  border: 1px solid #ebeef5;
}
</style> 