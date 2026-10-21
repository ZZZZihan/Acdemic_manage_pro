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
        redirect: '/workspace'
      },
      {
        path: 'workspace',
        name: 'WorkspaceCopilot',
        component: () => import('@/views/WorkspaceCopilot.vue'),
        meta: { title: '智能工作台', requiresAuth: true }
      },
      {
        path: 'overview',
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
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/projects/ProjectList.vue'),
        meta: { title: '项目管理', requiresAuth: true }
      },
      {
        path: 'projects/create',
        name: 'ProjectCreate',
        component: () => import('@/views/projects/ProjectCreate.vue'),
        meta: { title: '创建项目', requiresAuth: true }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetail.vue'),
        meta: { title: '项目详情', requiresAuth: true }
      },
      {
        path: 'projects/:id/edit',
        name: 'ProjectEdit',
        component: () => import('@/views/projects/ProjectEdit.vue'),
        meta: { title: '编辑项目', requiresAuth: true }
      },
      {
        path: 'meetings',
        name: 'MeetingList',
        component: () => import('@/views/meetings/MeetingList.vue'),
        meta: { title: '会议管理', requiresAuth: true }
      },
      {
        path: 'meetings/create',
        name: 'MeetingCreate',
        component: () => import('@/views/meetings/CreateMeeting.vue'),
        meta: { title: '创建会议', requiresAuth: true }
      },
      {
        path: 'meetings/:id',
        name: 'MeetingDetail',
        component: () => import('@/views/meetings/MeetingDetail.vue'),
        meta: { title: '会议详情', requiresAuth: true }
      },
      {
        path: 'meetings/:id/edit',
        name: 'MeetingEdit',
        component: () => import('@/views/meetings/MeetingEdit.vue'),
        meta: { title: '编辑会议', requiresAuth: true }
      },
      {
        path: 'admin/users',
        name: 'UserRoles',
        component: () => import('@/views/user/UserRoles.vue'),
        meta: { title: '角色管理', requiresAuth: true, requiresAdmin: true }
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

router.beforeEach(async (to) => {
  document.title = to.meta.title ? `${to.meta.title} - 实验室知识管理系统` : '实验室知识管理系统'
  const auth = useAuthStore()
  try {
    await auth.initialize()
    if (to.meta.requiresAdmin && auth.isLoggedIn) await auth.fetchUserProfile()
  } catch {
    if (to.meta.requiresAuth) return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) return { name: 'Login', query: { redirect: to.fullPath } }
  if (to.meta.requiresAdmin && !auth.isAdmin) return { name: 'Profile' }
})

window.addEventListener('auth:expired', () => {
  const current = router.currentRoute.value
  if (current.meta.requiresAuth) {
    router.replace({ name: 'Login', query: { redirect: current.fullPath } })
  }
})

export default router
