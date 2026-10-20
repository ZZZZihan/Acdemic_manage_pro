<template>
  <section>
    <h2>成员角色管理</h2>
    <p>普通成员使用业务功能；协管员拥有编辑权限；管理员可分配系统角色。</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-table v-loading="loading" :data="users" row-key="id">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="系统角色">
        <template #default="{ row }">
          <el-select v-model="drafts[row.id]" :disabled="row.id === auth.user?.id || saving === row.id">
            <el-option v-for="role in roles" :key="role.name" :value="role.name" :label="labels[role.name] || role.name" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button :loading="saving === row.id" :disabled="row.id === auth.user?.id || drafts[row.id] === row.role" @click="save(row)">保存角色</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/axios'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const users = ref([])
const roles = ref([])
const drafts = reactive({})
const loading = ref(false)
const saving = ref(null)
const error = ref('')
const labels = { User: '普通成员', Moderator: '协管员', Administrator: '管理员' }

onMounted(async () => {
  loading.value = true
  try {
    const [members, directory] = await Promise.all([api.get('/api/v1/users'), api.get('/api/v1/roles')])
    users.value = members.data
    roles.value = directory.data
    for (const member of users.value) drafts[member.id] = member.role
  } catch {
    error.value = '无法加载角色信息，请检查登录权限后重试。'
  } finally {
    loading.value = false
  }
})

async function save(user) {
  try {
    await ElMessageBox.confirm(`将 ${user.username} 的角色设为“${labels[drafts[user.id]]}”？`, '确认角色变更')
  } catch { return }
  saving.value = user.id
  try {
    const { data } = await api.put(`/api/v1/users/${user.id}/role`, { role: drafts[user.id] })
    Object.assign(user, data.user)
    ElMessage.success('角色已更新')
  } catch {
    drafts[user.id] = user.role
  } finally {
    saving.value = null
  }
}
</script>
