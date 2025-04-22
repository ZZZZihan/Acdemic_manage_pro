<template>
  <div class="project-list">
    <div class="page-header">
      <h2 class="page-title">项目管理</h2>
      <router-link :to="{ name: 'ProjectCreate' }">
        <el-button type="primary">创建新项目</el-button>
      </router-link>
    </div>
    
    <!-- 筛选栏 -->
    <el-card class="mb-4">
      <div class="filter-container">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input 
              v-model="filters.searchTerm"
              placeholder="搜索项目名称..." 
              clearable
              @input="debounceSearch"
            />
          </el-col>
          <el-col :span="5">
            <el-select v-model="filters.status" placeholder="项目状态" style="width: 100%" @change="loadProjects()">
              <el-option label="所有状态" value="" />
              <el-option label="进行中" value="进行中" />
              <el-option label="已完成" value="已完成" />
              <el-option label="已取消" value="已取消" />
            </el-select>
          </el-col>
          <el-col :span="5">
            <el-select v-model="filters.priority" placeholder="优先级" style="width: 100%" @change="loadProjects()">
              <el-option label="所有优先级" value="" />
              <el-option label="高" value="高" />
              <el-option label="中" value="中" />
              <el-option label="低" value="低" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-button type="info" @click="resetFilters">重置筛选</el-button>
          </el-col>
        </el-row>
      </div>
    </el-card>
    
    <!-- 项目标签页 -->
    <el-card>
      <el-tabs v-model="activeTab" @tab-click="handleTabClick">
        <!-- 我的项目 标签 -->
        <el-tab-pane label="我的项目" name="myProjects">
          <div v-if="loading.myProjects" class="loading-container">
            <el-icon :size="24" class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          
          <el-empty v-else-if="myProjects.length === 0" description="您还没有创建任何项目，点击右上角创建按钮开始" />
          
          <el-row v-else :gutter="20">
            <el-col v-for="project in myProjects" :key="project.id" :xs="24" :sm="12" :md="8" :lg="8">
              <el-card class="project-card" shadow="hover">
                <div class="card-header">
                  <h4 class="project-title">
                    <router-link :to="{ name: 'ProjectDetail', params: { id: project.id } }">
                      {{ project.name }}
                    </router-link>
                  </h4>
                  <el-tag :type="getStatusTagType(project.status)">{{ project.status }}</el-tag>
                </div>
                
                <p class="project-desc">{{ project.description || '暂无描述' }}</p>
                
                <div class="card-tags">
                  <el-tag type="info" effect="plain" size="small" class="mr-1">优先级: {{ project.priority }}</el-tag>
                  <el-tag v-if="project.members && project.members.length" type="info" effect="plain" size="small">
                    {{ project.members.length }} 名成员
                  </el-tag>
                </div>
                
                <div class="card-footer">
                  <div v-if="project.start_date">开始: {{ formatDate(project.start_date) }}</div>
                  <div v-if="project.end_date">结束: {{ formatDate(project.end_date) }}</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
        
        <!-- 参与的项目 标签 -->
        <el-tab-pane label="参与的项目" name="joinedProjects">
          <div v-if="loading.joinedProjects" class="loading-container">
            <el-icon :size="24" class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          
          <el-empty v-else-if="joinedProjects.length === 0" description="您还没有参与任何其他人创建的项目" />
          
          <el-row v-else :gutter="20">
            <el-col v-for="project in joinedProjects" :key="project.id" :xs="24" :sm="12" :md="8" :lg="8">
              <el-card class="project-card" shadow="hover">
                <div class="card-header">
                  <h4 class="project-title">
                    <router-link :to="{ name: 'ProjectDetail', params: { id: project.id } }">
                      {{ project.name }}
                    </router-link>
                  </h4>
                  <el-tag :type="getStatusTagType(project.status)">{{ project.status }}</el-tag>
                </div>
                
                <p class="project-desc">{{ project.description || '暂无描述' }}</p>
                
                <div class="card-tags">
                  <el-tag type="info" effect="plain" size="small" class="mr-1">优先级: {{ project.priority }}</el-tag>
                  <el-tag type="dark" effect="plain" size="small">创建者: {{ project.creator?.username || '未知' }}</el-tag>
                </div>
                
                <div class="card-footer">
                  <div v-if="project.start_date">开始: {{ formatDate(project.start_date) }}</div>
                  <div v-if="project.end_date">结束: {{ formatDate(project.end_date) }}</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
        
        <!-- 所有项目 标签 -->
        <el-tab-pane label="所有项目" name="allProjects">
          <div v-if="loading.allProjects" class="loading-container">
            <el-icon :size="24" class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          
          <el-empty v-else-if="allProjects.length === 0" description="暂无符合条件的项目" />
          
          <div v-else>
            <el-table :data="allProjects" style="width: 100%" border stripe>
              <el-table-column prop="name" label="项目名称">
                <template #default="scope">
                  <router-link :to="{ name: 'ProjectDetail', params: { id: scope.row.id } }">
                    {{ scope.row.name }}
                  </router-link>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="scope">
                  <el-tag :type="getStatusTagType(scope.row.status)">{{ scope.row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="priority" label="优先级" width="100" />
              <el-table-column prop="creator.username" label="创建者" width="120" />
              <el-table-column label="开始日期" width="120">
                <template #default="scope">
                  {{ formatDate(scope.row.start_date) }}
                </template>
              </el-table-column>
              <el-table-column label="结束日期" width="120">
                <template #default="scope">
                  {{ formatDate(scope.row.end_date) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="scope">
                  <el-button 
                    type="primary" 
                    link
                    size="small" 
                    @click="$router.push({ name: 'ProjectDetail', params: { id: scope.row.id } })"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            
            <!-- 分页 -->
            <div v-if="pagination.total > 0" class="pagination-container">
              <el-pagination
                background
                layout="prev, pager, next" 
                :current-page="pagination.currentPage"
                :page-size="pagination.perPage"
                :total="pagination.total"
                @current-change="goToPage"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import { useRouter, useRoute } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'

export default {
  name: 'ProjectList',
  components: {
    Loading
  },
  setup() {
    // 获取路由实例
    const router = useRouter()
    const route = useRoute()
    
    // 数据状态
    const myProjects = ref([])
    const joinedProjects = ref([])
    const allProjects = ref([])
    const loading = reactive({
      myProjects: false,
      joinedProjects: false,
      allProjects: false
    })
    
    // 活动标签页
    const activeTab = ref('myProjects')
    
    // 筛选条件
    const filters = reactive({
      searchTerm: '',
      status: '',
      priority: ''
    })
    
    // 分页信息
    const pagination = reactive({
      currentPage: 1,
      total: 0,
      perPage: 10
    })
    
    // 加载用户创建的项目
    const loadMyProjects = async () => {
      loading.myProjects = true
      
      try {
        const response = await axios.get('/api/v1/projects/user')
        myProjects.value = response.data.created
      } catch (error) {
        console.error('加载我的项目失败:', error)
        ElMessage.error('加载我的项目失败，请稍后重试')
      } finally {
        loading.myProjects = false
      }
    }
    
    // 加载用户参与的项目
    const loadJoinedProjects = async () => {
      loading.joinedProjects = true
      
      try {
        const response = await axios.get('/api/v1/projects/user')
        joinedProjects.value = response.data.joined
      } catch (error) {
        console.error('加载参与的项目失败:', error)
        ElMessage.error('加载参与的项目失败，请稍后重试')
      } finally {
        loading.joinedProjects = false
      }
    }
    
    // 加载所有项目列表
    const loadProjects = async () => {
      loading.allProjects = true
      
      try {
        const params = {
          page: pagination.currentPage,
          per_page: pagination.perPage,
          status: filters.status,
          priority: filters.priority
        }
        
        if (filters.searchTerm) {
          params.q = filters.searchTerm
        }
        
        const response = await axios.get('/api/v1/projects', { params })
        
        allProjects.value = response.data.projects
        pagination.total = response.data.total
        pagination.currentPage = response.data.current_page
      } catch (error) {
        console.error('加载项目列表失败:', error)
        ElMessage.error('加载项目列表失败，请稍后重试')
      } finally {
        loading.allProjects = false
      }
    }
    
    // 处理标签页点击
    const handleTabClick = (tab) => {
      const tabName = tab.props.name
      
      if (tabName === 'myProjects' && myProjects.value.length === 0) {
        loadMyProjects()
      } else if (tabName === 'joinedProjects' && joinedProjects.value.length === 0) {
        loadJoinedProjects()
      } else if (tabName === 'allProjects' && allProjects.value.length === 0) {
        loadProjects()
      }
    }
    
    // 防抖搜索
    let searchTimeout = null
    const debounceSearch = () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout)
      }
      
      searchTimeout = setTimeout(() => {
        pagination.currentPage = 1
        loadProjects()
      }, 500)
    }
    
    // 重置筛选条件
    const resetFilters = () => {
      filters.searchTerm = ''
      filters.status = ''
      filters.priority = ''
      pagination.currentPage = 1
      
      // 根据当前活动标签页重新加载数据
      if (activeTab.value === 'myProjects') {
        loadMyProjects()
      } else if (activeTab.value === 'joinedProjects') {
        loadJoinedProjects()
      } else {
        loadProjects()
      }
    }
    
    // 跳转到指定页
    const goToPage = (page) => {
      pagination.currentPage = page
      loadProjects()
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
    
    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '未设置'
      
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN')
    }
    
    // 页面挂载时加载数据
    onMounted(() => {
      // 根据URL参数设置默认标签页
      const tabParam = route.query.tab
      if (tabParam && ['myProjects', 'joinedProjects', 'allProjects'].includes(tabParam)) {
        activeTab.value = tabParam
      }
      
      // 加载默认标签页数据
      if (activeTab.value === 'myProjects') {
        loadMyProjects()
      } else if (activeTab.value === 'joinedProjects') {
        loadJoinedProjects()
      } else {
        loadProjects()
      }
    })
    
    return {
      myProjects,
      joinedProjects,
      allProjects,
      loading,
      activeTab,
      filters,
      pagination,
      loadProjects,
      loadMyProjects,
      loadJoinedProjects,
      handleTabClick,
      debounceSearch,
      resetFilters,
      goToPage,
      getStatusTagType,
      formatDate
    }
  }
}
</script>

<style scoped>
.project-list {
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

.filter-container {
  margin-bottom: 10px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 30px;
}

.project-card {
  margin-bottom: 15px;
  height: 100%;
  transition: all 0.3s;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.project-title {
  margin: 0;
  font-size: 16px;
}

.project-desc {
  color: #666;
  margin-bottom: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-tags {
  margin-bottom: 15px;
}

.card-footer {
  color: #909399;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
}

.mr-1 {
  margin-right: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>