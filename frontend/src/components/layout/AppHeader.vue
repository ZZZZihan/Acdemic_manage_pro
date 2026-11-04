<template>
  <div class="app-header">
    <div class="container header-container">
      <button
        v-if="showMenuButton"
        type="button"
        class="menu-button"
        aria-label="打开菜单"
        @click="$emit('toggle-menu')"
      >
        <el-icon><Menu /></el-icon>
      </button>
      <div class="logo">
        <router-link to="/">
          <span class="logo-full">实验室知识管理系统</span>
          <span class="logo-short">实验室</span>
        </router-link>
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
import { ArrowDown, Menu } from '@element-plus/icons-vue'

defineProps({
  showMenuButton: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle-menu'])

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

.menu-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin-right: 8px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
}

.logo {
  font-size: 20px;
  font-weight: bold;
  min-width: 0;
}

.logo-short {
  display: none;
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

@media (max-width: 768px) {
  .nav-menu {
    display: none;
  }

  .logo {
    font-size: 16px;
  }

  .logo-full {
    display: none;
  }

  .logo-short {
    display: inline;
  }

  .user-actions {
    margin-left: 8px;
  }

  .header-container {
    padding-left: 8px;
    padding-right: 8px;
  }
}
</style> 