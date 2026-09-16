<template>
  <div class="profile-page">
    <el-card class="card" header="修改密码">
      <el-form label-width="90px" style="max-width: 420px">
        <el-form-item label="原密码">
          <el-input v-model="oldPwd" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPwd" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="confirmPwd" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="changePwd">确认修改</el-button>
          <el-button @click="$router.push('/')">返回问答</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')

async function changePwd() {
  if (newPwd.value.length < 6) return ElMessage.warning('新密码至少6位')
  if (newPwd.value !== confirmPwd.value) return ElMessage.warning('两次输入的新密码不一致')
  try {
    await api.post('/auth/change-password', {
      old_password: oldPwd.value,
      new_password: newPwd.value,
    })
    ElMessage.success('密码修改成功')
    oldPwd.value = newPwd.value = confirmPwd.value = ''
  } catch (e) {
    /* 已统一提示 */
  }
}
</script>

<style scoped>
.profile-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}
.card {
  width: 520px;
}
</style>
