<template>
  <div class="auth-layout">
    <div class="auth-container">
      <div class="auth-header">
        <h1 class="auth-title">实验室知识管理系统</h1>
      </div>
      <div class="auth-content">
        <router-view />
      </div>
      <div class="auth-footer">
        <p>© {{ currentYear }} 实验室知识管理系统 - 版权所有</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const currentYear = computed(() => new Date().getFullYear())
</script>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}

.auth-container {
  width: 100%;
  max-width: 450px;
  padding: 20px;
}

.auth-header {
  text-align: center;
  margin-bottom: 30px;
}

.auth-title {
  color: #409EFF;
  font-size: 24px;
}

.auth-content {
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 30px;
  margin-bottom: 20px;
}

.auth-footer {
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style> 