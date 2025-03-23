<template>
  <div class="achievement-list">
    <div class="page-header">
      <h2 class="page-title">成果展示</h2>
      <el-button type="primary" @click="$router.push('/achievements/create')">添加成果</el-button>
    </div>
    
    <el-card class="filter-card mb-20">
      <el-form :inline="true" :model="filterForm" class="filter-form" @submit.prevent="searchAchievements">
        <el-form-item label="成果类型">
          <el-select v-model="filterForm.type" placeholder="全部类型" clearable>
            <el-option label="论文" value="论文" />
            <el-option label="专利" value="专利" />
            <el-option label="项目" value="项目" />
            <el-option label="奖项" value="奖项" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="搜索标题或作者" clearable @keyup.enter="searchAchievements" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchAchievements">搜索</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card v-loading="loading">
      <template v-if="achievements && achievements.length > 0">
        <el-table :data="achievements" style="width: 100%">
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="achievement_type" label="类型" width="100" />
          <el-table-column prop="authors" label="作者" min-width="150" />
          <el-table-column prop="publish_date" label="发布日期" width="120">
            <template #default="scope">
              {{ formatDate(scope.row.publish_date) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button
                size="small"
                @click="viewAchievement(scope.row.id)"
              >
                查看
              </el-button>
              <el-button
                size="small"
                type="primary"
                @click="editAchievement(scope.row.id)"
              >
                编辑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </template>
      
      <el-empty v-else description="暂无成果数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const achievements = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filterForm = reactive({
  type: '',
  keyword: ''
})

const fetchAchievements = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      only_mine: 'false'
    }
    
    if (filterForm.type) {
      params.type = filterForm.type
    }
    
    if (filterForm.keyword) {
      params.keyword = filterForm.keyword
    }
    
    console.log('请求参数:', params)
    const response = await axios.get('/api/v1/achievements', { params })
    console.log('成果列表响应:', response.data)
    
    // 检查响应数据的格式
    if (response.data && Array.isArray(response.data)) {
      // 如果响应是一个数组，直接使用
      achievements.value = response.data
      total.value = response.data.length
    } else if (response.data && response.data.items && Array.isArray(response.data.items)) {
      // 如果响应是一个包含items数组的对象
      achievements.value = response.data.items
      total.value = response.data.total || response.data.items.length
    } else {
      // 如果响应格式不符合预期，设置为空数组
      achievements.value = []
      total.value = 0
      console.warn('响应数据格式不符合预期:', response.data)
    }
  } catch (error) {
    console.error('获取成果列表失败:', error)
    ElMessage.error('获取成果列表失败')
    achievements.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filterForm.type = ''
  filterForm.keyword = ''
  currentPage.value = 1
  fetchAchievements()
}

const searchAchievements = () => {
  currentPage.value = 1
  fetchAchievements()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchAchievements()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchAchievements()
}

const viewAchievement = (id) => {
  router.push(`/achievements/${id}`)
}

const editAchievement = (id) => {
  router.push(`/achievements/${id}/edit`)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString()
}

onMounted(() => {
  fetchAchievements()
})
</script>

<style scoped>
.achievement-list {
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

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style> 