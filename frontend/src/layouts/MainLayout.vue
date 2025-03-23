<template>
  <div class="main-layout">
    <el-container>
      <el-header height="60px">
        <app-header />
      </el-header>
      <el-container>
        <el-aside width="220px">
          <app-sidebar />
        </el-aside>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
      <el-footer height="60px">
        <app-footer />
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.el-header {
  background-color: #409EFF;
  color: #fff;
  line-height: 60px;
  padding: 0;
}

.el-aside {
  background-color: #f5f7fa;
  color: #333;
  border-right: 1px solid #e6e6e6;
}

.el-main {
  background-color: #fff;
  color: #333;
  padding: 20px;
}

.el-footer {
  background-color: #f5f7fa;
  color: #333;
  text-align: center;
  line-height: 60px;
  border-top: 1px solid #e6e6e6;
}
</style> 