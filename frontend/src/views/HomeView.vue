<template>
  <div class="home-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card mb-20">
          <template #header>
            <div class="card-header">
              <h2>成果展示</h2>
            </div>
          </template>
          <div class="card-content">
            <p>本系统旨在为科研实验室提供一套完整的知识管理解决方案，帮助实验室成员更好地管理科研成果、技术文档、项目进度和会议安排。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最新成果组件 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <LatestAchievements />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import LatestAchievements from '@/components/LatestAchievements.vue'
</script>

<style scoped>
.home-view {
  padding: 20px;
}

.welcome-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mb-20 {
  margin-bottom: 20px;
}
</style>