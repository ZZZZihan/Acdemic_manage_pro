<template>
  <div class="meeting-list-container">
    <div class="page-header">
      <h2>会议管理</h2>
      <el-button type="primary" @click="$router.push('/meetings/create')">创建会议</el-button>
    </div>
    
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="我创建的会议" name="created"></el-tab-pane>
      <el-tab-pane label="参与的会议" name="joined"></el-tab-pane>
      <el-tab-pane label="所有会议" name="all"></el-tab-pane>
    </el-tabs>
    
    <div class="filter-section">
      <el-input
        v-model="searchQuery"
        placeholder="搜索会议标题"
        clearable
        @input="debouncedSearch"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadMeetings">
        <el-option label="未开始" value="pending" />
        <el-option label="进行中" value="in_progress" />
        <el-option label="已结束" value="completed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        @change="loadMeetings"
      />
      
      <el-button @click="resetFilters">重置筛选</el-button>
    </div>
    
    <el-card v-if="loading" class="loading-card">
      <el-skeleton :rows="5" animated />
    </el-card>
    
    <div v-else-if="meetings.length === 0" class="empty-state">
      <el-empty description="暂无会议" />
    </div>
    
    <div v-else class="meeting-list">
      <el-card v-for="meeting in meetings" :key="meeting.id" class="meeting-card" @click="viewMeetingDetails(meeting.id)">
        <div class="meeting-header">
          <div class="meeting-title">{{ meeting.title }}</div>
          <el-tag :type="getStatusType(meeting.status)">{{ getStatusText(meeting.status) }}</el-tag>
        </div>
        
        <div class="meeting-info">
          <div class="info-item">
            <el-icon><Calendar /></el-icon>
            <span>{{ formatDateTime(meeting.start_time) }} - {{ formatTime(meeting.end_time) }}</span>
          </div>
          <div class="info-item">
            <el-icon><Location /></el-icon>
            <span>{{ meeting.location || '未指定地点' }}</span>
          </div>
          <div class="info-item">
            <el-icon><User /></el-icon>
            <span>主持人: {{ meeting.host?.name || meeting.host?.username || meeting.organizer?.username || '未知' }}</span>
          </div>
          <div class="info-item">
            <el-icon><Document /></el-icon>
            <span>{{ meeting.project?.name || meeting.project || '无关联项目' }}</span>
          </div>
        </div>
        
        <div class="meeting-footer">
          <div class="participants">
            <el-avatar v-for="(participant, index) in (meeting.participants || []).slice(0, 3)" :key="index" :size="24">
              {{ participant.user?.username?.substring(0, 1) || '?' }}
            </el-avatar>
            <el-tag v-if="(meeting.participants || []).length > 3" size="small" type="info">+{{ meeting.participants.length - 3 }}</el-tag>
          </div>
          
          <div class="meeting-actions" @click.stop>
            <div class="action-buttons">
              <el-button type="primary" size="small" @click.stop="editMeeting(meeting.id)">
                <el-icon><Edit /></el-icon>
                <span>编辑</span>
              </el-button>
              <el-button v-if="canDeleteMeeting(meeting)" type="danger" size="small" @click.stop="confirmDelete(meeting)">
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>
    
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 30, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="totalMeetings"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
    
    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="30%">
      <span>确定要删除会议 "{{ selectedMeeting?.title }}" 吗？</span>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="deleteDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="deleteMeeting">确认删除</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, Location, User, Document, Search, Edit, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import axios from '@/utils/axios'
import _ from 'lodash'

export default {
  name: 'MeetingList',
  components: {
    Calendar,
    Location,
    User,
    Document,
    Search,
    Edit,
    Delete
  },
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    const userId = computed(() => authStore.user?.id)
    
    console.log('当前用户ID:', userId.value)
    
    const activeTab = ref('created')
    const meetings = ref([])
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalMeetings = ref(0)
    const searchQuery = ref('')
    const filterStatus = ref('')
    const dateRange = ref(null)
    const deleteDialogVisible = ref(false)
    const selectedMeeting = ref(null)
    
    const debouncedSearch = _.debounce(() => {
      loadMeetings()
    }, 300)
    
    const loadMeetings = async () => {
      loading.value = true
      try {
        const startDate = dateRange.value ? dateRange.value[0] : null
        const endDate = dateRange.value ? dateRange.value[1] : null
        
        const params = {
          page: currentPage.value,
          per_page: pageSize.value,
          q: searchQuery.value,
          status: filterStatus.value,
          date_from: startDate,
          date_to: endDate,
          tab: activeTab.value
        }
        
        console.log('加载会议，参数:', params)
        
        const response = await axios.get('/api/v1/meetings', { params })
        console.log('会议数据响应:', response.data)
        
        // 确保格式一致 
        meetings.value = response.data.meetings || response.data || []
        totalMeetings.value = response.data.total || meetings.value.length || 0
        
        console.log('处理后的会议数据:', meetings.value)
      } catch (error) {
        console.error('加载会议失败:', error)
        ElMessage.error('加载会议失败，请稍后重试')
      } finally {
        loading.value = false
      }
    }
    
    const handleTabChange = () => {
      currentPage.value = 1
      loadMeetings()
    }
    
    const handleSizeChange = (val) => {
      pageSize.value = val
      loadMeetings()
    }
    
    const handleCurrentChange = (val) => {
      currentPage.value = val
      loadMeetings()
    }
    
    const resetFilters = () => {
      searchQuery.value = ''
      filterStatus.value = ''
      dateRange.value = null
      loadMeetings()
    }
    
    const viewMeetingDetails = (id) => {
      router.push(`/meetings/${id}`)
    }
    
    const editMeeting = (id) => {
      console.log('编辑会议:', id)
      router.push(`/meetings/${id}/edit`)
    }
    
    const confirmDelete = (meeting) => {
      console.log('确认删除会议:', meeting)
      selectedMeeting.value = meeting
      deleteDialogVisible.value = true
    }
    
    const deleteMeeting = async () => {
      if (!selectedMeeting.value || !selectedMeeting.value.id) {
        ElMessage.error('无效的会议ID')
        return
      }
      
      console.log('删除会议ID:', selectedMeeting.value.id)
      
      try {
        await axios.delete(`/api/v1/meetings/${selectedMeeting.value.id}`)
        ElMessage.success('会议已删除')
        loadMeetings()
        deleteDialogVisible.value = false
      } catch (error) {
        console.error('删除会议失败:', error)
        ElMessage.error('删除会议失败: ' + (error.response?.data?.message || '服务器错误'))
      }
    }
    
    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      const date = new Date(dateTime)
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }
    
    const formatTime = (dateTime) => {
      if (!dateTime) return '-'
      const date = new Date(dateTime)
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }
    
    const getStatusType = (status) => {
      switch (status) {
        case '计划中': return 'info'
        case '进行中': return 'success'
        case '已完成': return ''
        case '已取消': return 'danger'
        default: return 'info'
      }
    }
    
    const getStatusText = (status) => {
      return status || '未知状态'
    }
    
    const canDeleteMeeting = (meeting) => {
      console.log('检查删除权限:', { 
        meeting, 
        organizerId: meeting.organizer_id,
        currentUserId: userId.value 
      })
      
      // 只保留组织者身份判断
      const isOrganizer = meeting.organizer_id === userId.value
      
      // 管理员权限
      const isAdmin = authStore.isAdmin
      
      return isOrganizer || isAdmin
    }
    
    onMounted(() => {
      loadMeetings()
    })
    
    return {
      userId,
      activeTab,
      meetings,
      loading,
      currentPage,
      pageSize,
      totalMeetings,
      searchQuery,
      filterStatus,
      dateRange,
      deleteDialogVisible,
      selectedMeeting,
      debouncedSearch,
      loadMeetings,
      handleTabChange,
      handleSizeChange,
      handleCurrentChange,
      resetFilters,
      viewMeetingDetails,
      editMeeting,
      confirmDelete,
      deleteMeeting,
      formatDateTime,
      formatTime,
      getStatusType,
      getStatusText,
      canDeleteMeeting
    }
  }
}
</script>

<style scoped>
.meeting-list-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-section {
  display: flex;
  gap: 15px;
  margin: 20px 0;
  flex-wrap: wrap;
}

.search-input {
  width: 250px;
}

.loading-card,
.empty-state {
  margin: 30px 0;
}

.meeting-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.meeting-card {
  cursor: pointer;
  transition: all 0.3s;
}

.meeting-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.meeting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.meeting-title {
  font-size: 18px;
  font-weight: bold;
}

.meeting-info {
  margin: 15px 0;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: #606266;
}

.info-item .el-icon {
  margin-right: 8px;
}

.meeting-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.participants {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 2;
}

.meeting-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  flex: 1;
  text-align: right;
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  width: 100%;
}

/* 确保按钮内部文字居中 */
.meeting-actions :deep(.el-button) {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px 15px;
}

/* 调整按钮内部图标和文字对齐 */
.meeting-actions :deep(.el-button .el-icon) {
  margin-right: 4px;
  vertical-align: middle;
  display: flex;
  align-items: center;
}

.meeting-actions :deep(.el-button span) {
  vertical-align: middle;
  line-height: 1;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}
</style> 