<template>
  <div class="achievement-detail" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">成果详情</h2>
      <div class="header-actions">
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="editAchievement" v-if="canEdit">编辑</el-button>
        <el-button type="danger" @click="confirmDelete" v-if="canEdit">删除</el-button>
      </div>
    </div>
    
    <el-card v-if="achievement">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="标题">{{ achievement.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ achievement.achievement_type }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ achievement.authors }}</el-descriptions-item>
        <el-descriptions-item label="发布日期">{{ formatDate(achievement.publish_date) }}</el-descriptions-item>
        <el-descriptions-item label="描述">
          <div class="description-content">{{ achievement.description || '暂无描述' }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="相关链接" v-if="achievement.url">
          <a :href="achievement.url" target="_blank">{{ achievement.url }}</a>
        </el-descriptions-item>
        <el-descriptions-item label="附件" v-if="achievement.file_path">
          <el-button size="small" type="primary" @click="downloadFile">
            下载附件 {{ achievement.original_file_name ? `(${achievement.original_file_name})` : '' }}
          </el-button>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(achievement.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(achievement.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
    
    <el-empty v-else-if="!loading" description="成果不存在或已被删除" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from '@/utils/axios'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const achievement = ref(null)
const loading = ref(false)

const canEdit = computed(() => {
  if (!achievement.value || !authStore.user) return false
  return authStore.isAdmin || achievement.value.user_id === authStore.user.id
})

const fetchAchievement = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/v1/achievements/${route.params.id}`)
    achievement.value = response.data
  } catch (error) {
    console.error('获取成果详情失败:', error)
    ElMessage.error('获取成果详情失败')
  } finally {
    loading.value = false
  }
}

const editAchievement = () => {
  router.push(`/achievements/${achievement.value.id}/edit`)
}

const confirmDelete = () => {
  ElMessageBox.confirm(
    '确定要删除这个成果吗？此操作不可逆。',
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(() => {
      deleteAchievement()
    })
    .catch(() => {
      // 用户取消删除
    })
}

const deleteAchievement = async () => {
  loading.value = true
  try {
    await axios.delete(`/api/v1/achievements/${achievement.value.id}`)
    ElMessage.success('成果已成功删除')
    router.push('/achievements')
  } catch (error) {
    console.error('删除成果失败:', error)
    ElMessage.error('删除成果失败')
  } finally {
    loading.value = false
  }
}

const downloadFile = () => {
  if (!achievement.value || !achievement.value.file_path) return
  
  // 构建下载URL
  const downloadUrl = `${import.meta.env.VITE_API_URL}/api/v1/files/download/${achievement.value.file_path}`
  
  // 添加原始文件名参数（如果有）
  const urlWithParams = achievement.value.original_file_name 
    ? `${downloadUrl}?original_name=${encodeURIComponent(achievement.value.original_file_name)}`
    : downloadUrl
  
  // 创建一个隐藏的a标签并触发点击
  const link = document.createElement('a')
  link.href = urlWithParams
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

const formatDateTime = (dateTimeString) => {
  if (!dateTimeString) return '-'
  const date = new Date(dateTimeString)
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
}

onMounted(() => {
  fetchAchievement()
})
</script>

<style scoped>
.achievement-detail {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.description-content {
  white-space: pre-line;
}
</style> 