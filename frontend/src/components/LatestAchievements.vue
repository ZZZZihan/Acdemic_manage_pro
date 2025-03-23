<template>
  <div class="latest-achievements">
    <h2 class="section-title">最新科研成果</h2>
    
    <el-skeleton :rows="3" animated v-if="loading" />
    
    <el-empty description="暂无最新成果" v-else-if="!achievements || achievements.length === 0" />
    
    <!-- 带图片的成果（轮播图展示） -->
    <div v-else-if="achievementsWithImages.length > 0" class="image-carousel-container">
      <el-carousel :interval="4000" type="card" height="280px">
        <el-carousel-item v-for="item in achievementsWithImages" :key="item.id">
          <div class="carousel-item" @click="viewDetails(item.id)">
            <div class="image-container">
              <img :src="getImageUrl(item)" :alt="item.title" class="carousel-image">
            </div>
            <div class="carousel-content">
              <div class="type-tag">{{ item.achievement_type }}</div>
              <h3 class="item-title">{{ item.title }}</h3>
              <div class="item-info">
                <span class="item-author">{{ item.authors }}</span>
                <span class="item-date">{{ formatDate(item.publish_date) }}</span>
              </div>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </div>
    
    <!-- 所有成果列表 -->
    <div class="achievement-list">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" v-for="item in achievements" :key="item.id" class="mb-20">
          <el-card shadow="hover" class="achievement-card" @click="viewDetails(item.id)">
            <div v-if="hasImage(item)" class="card-image">
              <img :src="getImageUrl(item)" :alt="item.title">
            </div>
            <div class="card-header">
              <span class="type-tag">{{ item.achievement_type }}</span>
              <span class="date">{{ formatDate(item.publish_date) }}</span>
            </div>
            <h3 class="card-title">{{ item.title }}</h3>
            <div class="card-authors">{{ item.authors }}</div>
            <p class="card-description">{{ truncateText(item.description, 100) }}</p>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <div class="view-more">
      <router-link to="/achievements">
        <el-button type="primary">查看更多成果</el-button>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const achievements = ref([])
const loading = ref(false)

// 筛选有图片的成果
const achievementsWithImages = computed(() => {
  return achievements.value.filter(item => hasImage(item))
})

// 获取最新成果
const fetchLatestAchievements = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/v1/achievements/latest?limit=10')
    
    // 检查响应数据格式
    if (Array.isArray(response.data)) {
      achievements.value = response.data
    } else if (response.data && response.data.items && Array.isArray(response.data.items)) {
      achievements.value = response.data.items
    } else {
      console.warn('响应数据格式不符合预期:', response.data)
      achievements.value = []
    }
  } catch (error) {
    console.error('获取最新成果失败:', error)
    ElMessage.error('获取最新成果失败，请稍后再试')
    achievements.value = []
  } finally {
    loading.value = false
  }
}

// 判断成果是否有图片
const hasImage = (achievement) => {
  if (!achievement.file_path) return false
  
  const fileExt = achievement.file_path.split('.').pop().toLowerCase()
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp']
  
  return imageExts.includes(fileExt)
}

// 获取图片URL
const getImageUrl = (achievement) => {
  if (!achievement.file_path) return ''
  
  return `${import.meta.env.VITE_API_URL || ''}/api/v1/files/download/${achievement.file_path}`
}

// 截断文本
const truncateText = (text, length) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

// 查看详情
const viewDetails = (id) => {
  router.push(`/achievements/${id}`)
}

onMounted(() => {
  fetchLatestAchievements()
})
</script>

<style scoped>
.latest-achievements {
  margin: 30px 0;
}

.section-title {
  font-size: 24px;
  margin-bottom: 25px;
  color: #333;
  text-align: center;
  position: relative;
}

.section-title:after {
  content: '';
  display: block;
  width: 50px;
  height: 3px;
  background: #409EFF;
  margin: 10px auto 0;
}

.image-carousel-container {
  margin-bottom: 40px;
}

.carousel-item {
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  cursor: pointer;
  background: #f5f7fa;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-container {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.carousel-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.carousel-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 15px;
}

.item-title {
  font-size: 18px;
  margin: 8px 0;
}

.item-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.achievement-card {
  height: 100%;
  transition: transform 0.3s, box-shadow 0.3s;
  cursor: pointer;
}

.achievement-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.card-image {
  height: 160px;
  overflow: hidden;
  margin: -20px -20px 15px;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.type-tag {
  background: #409EFF;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.card-title {
  font-size: 18px;
  margin: 10px 0;
  color: #303133;
}

.card-authors {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.card-description {
  font-size: 14px;
  color: #909399;
  line-height: 1.5;
  margin-bottom: 15px;
  max-height: 60px;
  overflow: hidden;
}

.view-more {
  text-align: center;
  margin-top: 30px;
}

.mb-20 {
  margin-bottom: 20px;
}

.date {
  color: #909399;
  font-size: 13px;
}

.el-carousel__item:nth-child(2n) {
  background-color: #99a9bf;
}
  
.el-carousel__item:nth-child(2n+1) {
  background-color: #d3dce6;
}
</style> 