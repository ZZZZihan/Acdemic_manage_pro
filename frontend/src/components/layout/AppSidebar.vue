<template>
  <div class="app-sidebar">
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      :router="true"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </el-menu-item>
      
      <el-sub-menu index="/achievements">
        <template #title>
          <el-icon><Trophy /></el-icon>
          <span>成果管理</span>
        </template>
        <el-menu-item index="/achievements">成果列表</el-menu-item>
        <el-menu-item index="/achievements/create">添加成果</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="/tech_summaries">
        <template #title>
          <el-icon><Document /></el-icon>
          <span>技术总结</span>
        </template>
        <el-menu-item index="/tech_summaries">总结列表</el-menu-item>
        <el-menu-item index="/tech_summaries/create">添加总结</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="/projects">
        <template #title>
          <el-icon><Histogram /></el-icon>
          <span>项目管理</span>
        </template>
        <el-menu-item index="/projects">项目列表</el-menu-item>
        <el-menu-item index="/projects/create">添加项目</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="/meetings">
        <template #title>
          <el-icon><Calendar /></el-icon>
          <span>会议管理</span>
        </template>
        <el-menu-item index="/meetings">会议列表</el-menu-item>
        <el-menu-item index="/meetings/create">添加会议</el-menu-item>
      </el-sub-menu>
      
      <el-menu-item index="/knowledge_chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>知识库聊天</span>
      </el-menu-item>
      
      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <span>个人中心</span>
      </el-menu-item>
      
      <el-menu-item v-if="authStore.isAdmin" index="/admin">
        <el-icon><Setting /></el-icon>
        <span>系统管理</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeFilled,
  Trophy,
  Document,
  Histogram,
  Calendar,
  User,
  Setting,
  ChatDotRound
} from '@element-plus/icons-vue'

const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  return route.path
})
</script>

<style scoped>
.app-sidebar {
  height: 100%;
}

.sidebar-menu {
  height: 100%;
  border-right: none;
}
</style> 