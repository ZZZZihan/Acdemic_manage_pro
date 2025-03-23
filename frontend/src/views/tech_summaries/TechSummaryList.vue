<template>
  <div class="tech-summary-list">
    <div class="page-header">
      <h2 class="page-title">技术总结</h2>
      <div class="button-group">
        <el-button type="primary" @click="$router.push('/tech_summaries/create')">添加总结</el-button>
      </div>
    </div>
    
    <el-card class="filter-card mb-20">
      <el-form :inline="true" :model="filterForm" class="filter-form" @submit.prevent="searchSummaries">
        <el-form-item label="总结类型">
          <el-select v-model="filterForm.type" placeholder="全部类型" clearable>
            <el-option label="算法" value="算法" />
            <el-option label="工具" value="工具" />
            <el-option label="方法" value="方法" />
            <el-option label="经验" value="经验" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="filterForm.tags" placeholder="输入标签，多个用逗号分隔" clearable />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="搜索标题或内容" clearable @keyup.enter="searchSummaries" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchSummaries">搜索</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card v-loading="loading">
      <template v-if="summaries && summaries.length > 0">
        <el-table :data="summaries" style="width: 100%">
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="summary_type" label="类型" width="100" />
          <el-table-column prop="tags" label="标签" min-width="150" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button
                size="small"
                @click="viewSummary(scope.row.id)"
              >
                查看
              </el-button>
              <el-button
                size="small"
                type="primary"
                @click="editSummary(scope.row.id)"
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
      
      <el-empty v-else description="暂无技术总结" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const summaries = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filterForm = reactive({
  type: '',
  tags: '',
  keyword: ''
})

const fetchSummaries = async () => {
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
    
    if (filterForm.tags) {
      params.tags = filterForm.tags
    }
    
    if (filterForm.keyword) {
      params.keyword = filterForm.keyword
    }
    
    console.log('请求参数:', params)
    console.log('发送请求到:', '/api/v1/tech_summaries')
    const response = await axios.get('/api/v1/tech_summaries', { params })
    console.log('技术总结列表响应状态:', response.status)
    console.log('技术总结列表响应数据类型:', typeof response.data)
    console.log('技术总结列表响应数据:', JSON.stringify(response.data, null, 2))
    
    // 检查响应数据的格式
    if (response.data && Array.isArray(response.data)) {
      // 如果响应是一个数组，直接使用
      console.log('响应是数组，长度:', response.data.length)
      summaries.value = response.data
      total.value = response.data.length
    } else if (response.data && response.data.items && Array.isArray(response.data.items)) {
      // 如果响应是一个包含items数组的对象
      console.log('响应是包含items数组的对象，items长度:', response.data.items.length)
      summaries.value = response.data.items
      total.value = response.data.total || response.data.items.length
    } else {
      // 如果响应格式不符合预期，设置为空数组
      console.warn('响应数据格式不符合预期:', response.data)
      summaries.value = []
      total.value = 0
    }
    console.log('处理后的summaries:', summaries.value)
    console.log('处理后的total:', total.value)
  } catch (error) {
    console.error('获取技术总结列表失败:', error)
    console.error('错误详情:', error.response ? error.response.data : error.message)
    ElMessage.error('获取技术总结列表失败')
    summaries.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filterForm.type = ''
  filterForm.tags = ''
  filterForm.keyword = ''
  currentPage.value = 1
  fetchSummaries()
}

const searchSummaries = () => {
  currentPage.value = 1
  fetchSummaries()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchSummaries()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchSummaries()
}

const viewSummary = (id) => {
  console.log('查看技术总结，ID:', id)
  console.log('跳转路径:', `/tech_summaries/${id}`)
  router.push(`/tech_summaries/${id}`)
}

const editSummary = (id) => {
  router.push(`/tech_summaries/${id}/edit`)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString()
}

onMounted(() => {
  fetchSummaries()
})
</script>

<style scoped>
.tech-summary-list {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.button-group {
  display: flex;
  gap: 10px;
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