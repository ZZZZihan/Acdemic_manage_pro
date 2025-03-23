<template>
  <div class="app-footer">
    <div class="container">
      <p>© {{ currentYear }} 实验室知识管理系统 - 版权所有</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const currentYear = computed(() => new Date().getFullYear())
</script>

<style scoped>
.app-footer {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style> 