<template>
  <div class="main-layout">
    <el-container>
      <el-header height="60px">
        <app-header :show-menu-button="isNarrow" @toggle-menu="drawer = true" />
      </el-header>
      <el-container>
        <el-aside v-if="!isNarrow" width="220px">
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
    <el-drawer
      v-model="drawer"
      direction="ltr"
      size="240px"
      :with-header="false"
      append-to-body
    >
      <app-sidebar />
    </el-drawer>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

const drawer = ref(false)
const isNarrow = ref(false)
const route = useRoute()
const query = window.matchMedia('(max-width: 768px)')

function syncNarrow() {
  isNarrow.value = query.matches
  if (!isNarrow.value) {
    drawer.value = false
  }
}

onMounted(() => {
  syncNarrow()
  query.addEventListener('change', syncNarrow)
})

onBeforeUnmount(() => {
  query.removeEventListener('change', syncNarrow)
})

watch(() => route.fullPath, () => {
  drawer.value = false
})
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
  min-width: 0;
}

@media (max-width: 768px) {
  .el-main {
    padding: 12px;
  }

  .el-footer {
    line-height: 1.4;
    height: auto;
    padding: 12px;
  }
}

.el-footer {
  background-color: #f5f7fa;
  color: #333;
  text-align: center;
  line-height: 60px;
  border-top: 1px solid #e6e6e6;
}
</style> 