<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">🛒 电商知识库问答系统</h1>
      <p class="subtitle">RAG 企业级知识库问答 · 毕设项目</p>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" clearable>
            <template #prefix>👤</template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码(至少6位)"
            size="large"
            show-password
            @keydown.enter="submit"
          >
            <template #prefix>🔒</template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>
      <p class="tip">演示账号:管理员 admin / 123456</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || password.value.length < 6) {
    ElMessage.warning('请输入用户名和至少6位的密码')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(username.value, password.value)
      ElMessage.success('登录成功')
    } else {
      await auth.register(username.value, password.value)
      ElMessage.success('注册成功,已自动登录')
    }
    router.push('/')
  } catch (e) {
    // 错误信息已由 api.js 统一弹出
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: 12px;
  padding: 36px 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.title {
  font-size: 22px;
  text-align: center;
  margin-bottom: 6px;
}
.subtitle {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin-bottom: 20px;
}
.submit-btn {
  width: 100%;
}
.tip {
  margin-top: 16px;
  text-align: center;
  color: #bbb;
  font-size: 12px;
}
</style>
