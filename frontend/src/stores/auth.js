import { defineStore } from 'pinia'
import api from '../api'

// 登录状态用 sessionStorage 保存:
// 每个浏览器标签页独立一份,两个标签页分别登录不同账号互不干扰。
// (关闭标签页后需重新登录,但聊天记录都在服务器上,登录后即可找回)
const storage = sessionStorage

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: storage.getItem('token') || '',
    user: JSON.parse(storage.getItem('user') || 'null'),
  }),
  getters: {
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login', { username, password })
      this.token = data.token
      this.user = data.user
      storage.setItem('token', data.token)
      storage.setItem('user', JSON.stringify(data.user))
    },
    async register(username, password) {
      const { data } = await api.post('/auth/register', { username, password })
      this.token = data.token
      this.user = data.user
      storage.setItem('token', data.token)
      storage.setItem('user', JSON.stringify(data.user))
    },
    logout() {
      this.token = ''
      this.user = null
      storage.removeItem('token')
      storage.removeItem('user')
    },
  },
})
