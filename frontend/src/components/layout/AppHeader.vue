<template>
  <div class="app-header">
    <div class="container header-container">
      <div class="logo">
        <router-link to="/">实验室知识管理系统</router-link>
      </div>
      <div class="nav-menu">
        <el-menu
          mode="horizontal"
          :ellipsis="false"
          background-color="#409EFF"
          text-color="#fff"
          active-text-color="#fff"
          :router="true"
        >
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/achievements">成果展示</el-menu-item>
        </el-menu>
      </div>
      <div class="user-actions">
        <template v-if="authStore.isLoggedIn">
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown-link">
              {{ authStore.user?.username || '用户' }}
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <router-link to="/auth/login" class="login-btn">登录</router-link>
          <router-link to="/auth/register" class="register-btn">注册</router-link>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const router = useRouter()

const handleCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-header {
  width: 100%;
  height: 100%;
}

.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.logo {
  font-size: 20px;
  font-weight: bold;
}

.logo a {
  color: #fff;
  text-decoration: none;
}

.nav-menu {
  flex: 1;
  margin-left: 30px;
}

:deep(.el-menu) {
  border-bottom: none;
}

:deep(.el-menu-item) {
  color: #fff;
}

:deep(.el-menu-item.is-active) {
  background-color: rgba(255, 255, 255, 0.1);
}

.user-actions {
  margin-left: 20px;
}

.user-dropdown-link {
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.login-btn, .register-btn {
  color: #fff;
  margin-left: 15px;
}
</style> 