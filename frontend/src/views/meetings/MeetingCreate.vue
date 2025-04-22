<template>
  <div class="meeting-create-container">
    <div class="page-header">
      <h2>创建会议</h2>
      <div>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">保存</el-button>
      </div>
    </div>
    
    <el-form 
      ref="formRef" 
      :model="form" 
      :rules="rules" 
      label-position="top" 
      class="meeting-form"
      v-loading="loading"
    >
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
          </div>
        </template>
        
        <el-form-item label="会议标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入会议标题" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始时间" prop="start_time">
              <el-date-picker
                v-model="form.start_time"
                type="datetime"
                placeholder="选择开始时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:ss"
                :disabled-date="disablePastDates"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" prop="end_time">
              <el-date-picker
                v-model="form.end_time"
                type="datetime"
                placeholder="选择结束时间"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm:ss"
                :disabled-date="disablePastDates"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="会议地点" prop="location">
          <el-input v-model="form.location" placeholder="请输入会议地点" />
        </el-form-item>
        
        <el-form-item label="会议状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择会议状态" style="width: 100%">
            <el-option label="未开始" value="pending" />
            <el-option label="进行中" value="in_progress" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="关联项目" prop="project_id">
          <el-select
            v-model="form.project_id"
            filterable
            clearable
            placeholder="选择关联项目（可选）"
            style="width: 100%"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
      </el-card>
      
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>参会人员</span>
          </div>
        </template>
        
        <el-form-item label="参会人员" prop="participants">
          <el-select
            v-model="form.participants"
            multiple
            filterable
            remote
            :remote-method="searchUsers"
            placeholder="搜索并选择参会人员"
            style="width: 100%"
            :loading="searchingUsers"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.name"
              :value="user.id"
            >
              <div class="user-option">
                <el-avatar :size="24" :src="user.avatar">{{ user.name.substring(0, 1) }}</el-avatar>
                <span>{{ user.name }}</span>
                <span class="user-email">{{ user.email }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-card>
      
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>会议内容</span>
          </div>
        </template>
        
        <el-form-item label="会议议程" prop="agenda">
          <el-input
            v-model="form.agenda"
            type="textarea"
            :rows="5"
            placeholder="请输入会议议程"
          />
        </el-form-item>
        
        <el-form-item label="会议备注" prop="notes">
          <el-input
            v-model="form.notes"
            type="textarea"
            :rows="3"
            placeholder="请输入会议备注（可选）"
          />
        </el-form-item>
        
        <el-form-item label="文件附件" prop="attachments">
          <el-upload
            class="attachment-uploader"
            :action="`/api/meetings/attachments`"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :on-remove="handleFileRemove"
            multiple
          >
            <el-button type="primary">上传文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持任意类型文件，单个文件不超过10MB</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-card>
    </el-form>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import axios from 'axios'
import _ from 'lodash'
import { useUserStore } from '@/stores/user'

export default {
  name: 'MeetingCreate',
  setup() {
    const router = useRouter()
    const userStore = useUserStore()
    const formRef = ref(null)
    const loading = ref(false)
    const submitting = ref(false)
    const searchingUsers = ref(false)
    
    const form = reactive({
      title: '',
      start_time: '',
      end_time: '',
      location: '',
      status: 'pending',
      project_id: null,
      participants: [],
      agenda: '',
      notes: '',
      attachments: []
    })
    
    const rules = {
      title: [
        { required: true, message: '请输入会议标题', trigger: 'blur' },
        { min: 3, max: 100, message: '长度在 3 到 100 个字符', trigger: 'blur' }
      ],
      start_time: [
        { required: true, message: '请选择开始时间', trigger: 'change' }
      ],
      end_time: [
        { required: true, message: '请选择结束时间', trigger: 'change' }
      ],
      location: [
        { required: true, message: '请输入会议地点', trigger: 'blur' }
      ],
      status: [
        { required: true, message: '请选择会议状态', trigger: 'change' }
      ],
      agenda: [
        { required: true, message: '请输入会议议程', trigger: 'blur' }
      ]
    }
    
    const users = ref([])
    const projects = ref([])
    
    const uploadHeaders = computed(() => {
      return {
        Authorization: `Bearer ${userStore.token}`
      }
    })
    
    // 获取用户创建的项目列表
    const loadProjects = async () => {
      try {
        const response = await axios.get('/api/projects', { 
          params: { filter: 'created', limit: 100 } 
        })
        projects.value = response.data.items
      } catch (error) {
        console.error('加载项目失败:', error)
        ElMessage.error('加载项目列表失败')
      }
    }
    
    // 搜索用户
    const searchUsers = async (query) => {
      if (query.length < 2) return
      
      searchingUsers.value = true
      try {
        const response = await axios.get('/api/users/search', {
          params: { query }
        })
        users.value = response.data
      } catch (error) {
        console.error('搜索用户失败:', error)
      } finally {
        searchingUsers.value = false
      }
    }
    
    // 禁用过去的日期
    const disablePastDates = (date) => {
      return date < new Date(new Date().setHours(0, 0, 0, 0))
    }
    
    // 处理文件上传成功
    const handleUploadSuccess = (response, file) => {
      form.attachments.push({
        id: response.id,
        name: file.name,
        size: file.size,
        url: response.url
      })
      ElMessage.success('文件上传成功')
    }
    
    // 处理文件上传失败
    const handleUploadError = () => {
      ElMessage.error('文件上传失败，请重试')
    }
    
    // 处理文件移除
    const handleFileRemove = (file) => {
      const index = form.attachments.findIndex(
        attachment => attachment.name === file.name && attachment.size === file.size
      )
      if (index !== -1) {
        form.attachments.splice(index, 1)
      }
    }
    
    // 提交表单
    const submitForm = async () => {
      if (!formRef.value) return
      
      await formRef.value.validate(async (valid) => {
        if (!valid) {
          ElMessage.error('请检查表单填写是否正确')
          return false
        }
        
        // 验证结束时间是否晚于开始时间
        if (new Date(form.end_time) <= new Date(form.start_time)) {
          ElMessage.error('结束时间必须晚于开始时间')
          return false
        }
        
        submitting.value = true
        try {
          const response = await axios.post('/api/meetings', form)
          ElMessage.success('会议创建成功')
          router.push(`/dashboard/meetings/${response.data.id}`)
        } catch (error) {
          console.error('创建会议失败:', error)
          ElMessage.error('创建会议失败，请重试')
        } finally {
          submitting.value = false
        }
      })
    }
    
    onMounted(() => {
      loadProjects()
    })
    
    return {
      formRef,
      form,
      rules,
      loading,
      submitting,
      users,
      projects,
      searchingUsers,
      uploadHeaders,
      submitForm,
      searchUsers,
      disablePastDates,
      handleUploadSuccess,
      handleUploadError,
      handleFileRemove
    }
  }
}
</script>

<style scoped>
.meeting-create-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.meeting-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-card {
  margin-bottom: 20px;
}

.card-header {
  font-weight: bold;
}

.user-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-email {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

.attachment-uploader {
  width: 100%;
}

.el-upload__tip {
  margin-top: 5px;
  color: #909399;
}
</style> 