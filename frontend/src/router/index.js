import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import ChatView from '../views/ChatView.vue'
import AdminKbView from '../views/AdminKbView.vue'
import ProfileView from '../views/ProfileView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: ChatView },
    { path: '/admin', component: AdminKbView, meta: { admin: true } },
    { path: '/profile', component: ProfileView },
  ],
})

// 路由守卫:未登录跳登录页;非管理员访问 /admin 跳回主页
router.beforeEach((to) => {
  const token = sessionStorage.getItem('token')
  if (to.path !== '/login' && !token) return '/login'
  if (to.meta.admin) {
    const user = JSON.parse(sessionStorage.getItem('user') || 'null')
    if (user?.role !== 'admin') return '/'
  }
})

export default router
