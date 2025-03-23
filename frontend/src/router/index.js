import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由配置
const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/HomeView.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'achievements',
        name: 'Achievements',
        component: () => import('@/views/achievements/AchievementList.vue'),
        meta: { title: '成果展示', requiresAuth: false }
      },
      {
        path: 'achievements/create',
        name: 'AchievementCreate',
        component: () => import('@/views/achievements/AchievementCreate.vue'),
        meta: { title: '添加成果', requiresAuth: true }
      },
      {
        path: 'achievements/:id',
        name: 'AchievementDetail',
        component: () => import('@/views/achievements/AchievementDetail.vue'),
        meta: { title: '成果详情', requiresAuth: true }
      },
      {
        path: 'achievements/:id/edit',
        name: 'AchievementEdit',
        component: () => import('@/views/achievements/AchievementEdit.vue'),
        meta: { title: '编辑成果', requiresAuth: true }
      },
      {
        path: 'tech_summaries',
        name: 'TechSummaries',
        component: () => import('@/views/tech_summaries/TechSummaryList.vue'),
        meta: { title: '技术总结', requiresAuth: false }
      },
      {
        path: 'tech_summaries/create',
        name: 'TechSummaryCreate',
        component: () => import('@/views/tech_summaries/TechSummaryCreate.vue'),
        meta: { title: '添加技术总结', requiresAuth: true }
      },
      {
        path: 'tech_summaries/:id',
        name: 'TechSummaryDetail',
        component: () => import('@/views/tech_summaries/TechSummaryDetail.vue'),
        meta: { title: '技术总结详情', requiresAuth: false }
      },
      {
        path: 'tech_summaries/:id/edit',
        name: 'TechSummaryEdit',
        component: () => import('@/views/tech_summaries/TechSummaryEdit.vue'),
        meta: { title: '编辑技术总结', requiresAuth: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/user/ProfileView.vue'),
        meta: { title: '个人中心', requiresAuth: true }
      },
      {
        path: 'knowledge_chat',
        name: 'KnowledgeChat',
        component: () => import('@/views/KnowledgeChat.vue'),
        meta: { title: '知识库聊天', requiresAuth: false }
      },
      {
        path: 'ollama_chat',
        name: 'OllamaChat',
        component: () => import('@/views/OllamaChat.vue'),
        meta: { title: 'Ollama聊天', requiresAuth: false }
      }
    ]
  },
  {
    path: '/auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { title: '登录' }
      },
      {
        path: 'register',
        name: 'Register',
        component: () => import('@/views/auth/RegisterView.vue'),
        meta: { title: '注册' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  console.log('路由守卫触发：', { 
    to: { path: to.path, name: to.name, meta: to.meta, query: to.query },
    from: { path: from.path, name: from.name }
  })
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 实验室知识管理系统` : '实验室知识管理系统'
  
  // 检查是否需要登录
  const authStore = useAuthStore()
  console.log('当前登录状态：', { 
    isLoggedIn: authStore.isLoggedIn, 
    token: !!authStore.token,
    user: authStore.user
  })
  
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    // 需要登录但未登录，重定向到登录页
    console.log('需要登录但未登录，重定向到登录页，携带重定向路径：', to.fullPath)
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    console.log('允许访问路由：', to.path)
    next()
  }
})

export default router 