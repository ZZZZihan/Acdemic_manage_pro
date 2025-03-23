<template>
  <div class="achievement-create">
    <div class="page-header">
      <h2 class="page-title">添加成果</h2>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    
    <el-card>
      <el-form
        ref="achievementForm"
        :model="achievementData"
        :rules="rules"
        label-width="100px"
        @submit.prevent="submitForm"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="achievementData.title" placeholder="请输入成果标题" />
        </el-form-item>
        
        <el-form-item label="类型" prop="achievement_type">
          <el-select v-model="achievementData.achievement_type" placeholder="请选择成果类型" style="width: 100%">
            <el-option label="论文" value="论文" />
            <el-option label="专利" value="专利" />
            <el-option label="项目" value="项目" />
            <el-option label="奖项" value="奖项" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="作者" prop="authors">
          <el-input v-model="achievementData.authors" placeholder="请输入作者，多个作者用逗号分隔" />
        </el-form-item>
        
        <el-form-item label="发布日期" prop="publish_date">
          <el-date-picker
            v-model="achievementData.publish_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="achievementData.description"
            type="textarea"
            :rows="5"
            placeholder="请输入成果描述"
          />
        </el-form-item>
        
        <el-form-item label="相关链接" prop="url">
          <el-input v-model="achievementData.url" placeholder="请输入相关链接（可选）" />
        </el-form-item>
        
        <el-form-item label="附件" prop="files">
          <file-upload 
            ref="fileUploadRef"
            @file-uploaded="handleFileUploaded"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading">提交</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from '@/utils/axios'
import FileUpload from '@/components/FileUpload.vue'

const router = useRouter()
const achievementForm = ref(null)
const fileUploadRef = ref(null)
const loading = ref(false)

const achievementData = reactive({
  title: '',
  achievement_type: '',
  authors: '',
  publish_date: '',
  description: '',
  url: '',
  files: []  // 存储多个文件信息
})

const rules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  achievement_type: [
    { required: true, message: '请选择成果类型', trigger: 'change' }
  ],
  authors: [
    { required: true, message: '请输入作者', trigger: 'blur' }
  ],
  publish_date: [
    { required: true, message: '请选择发布日期', trigger: 'change' }
  ],
  description: [
    { required: true, message: '请输入描述', trigger: 'blur' }
  ],
  url: [
    { pattern: /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w .-]*)*\/?$/, message: '请输入有效的URL', trigger: 'blur' }
  ]
}

// 处理文件上传成功
const handleFileUploaded = (fileInfo) => {
  // 将新上传的文件添加到文件列表中
  achievementData.files.push(fileInfo)
}

const submitForm = async () => {
  if (!achievementForm.value) return
  
  await achievementForm.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 准备提交数据
        const submitData = {
          title: achievementData.title,
          achievement_type: achievementData.achievement_type,
          authors: achievementData.authors,
          publish_date: achievementData.publish_date,
          description: achievementData.description,
          url: achievementData.url,
        }
        
        // 如果有文件信息，添加文件路径
        if (achievementData.files.length > 0) {
          // 使用第一个文件作为主文件
          submitData.file_path = achievementData.files[0].file_path
          submitData.original_file_name = achievementData.files[0].original_name
          
          // 如果有多个文件，添加附加文件信息
          if (achievementData.files.length > 1) {
            submitData.additional_files = achievementData.files.slice(1)
          }
        }
        
        console.log('提交数据:', submitData)
        
        // 确保所有字段都是字符串类型
        Object.keys(submitData).forEach(key => {
          if (key !== 'additional_files' && submitData[key] !== null && submitData[key] !== undefined && typeof submitData[key] !== 'string') {
            submitData[key] = String(submitData[key])
          }
        })
        
        console.log('处理后的提交数据:', submitData)
        
        const response = await axios.post('/api/v1/achievements', submitData)
        console.log('成功响应:', response.data)
        ElMessage.success('成果添加成功')
        router.push('/achievements')
      } catch (error) {
        console.error('添加成果失败:', error)
        console.error('错误详情:', error.response?.data)
        ElMessage.error(error.response?.data?.message || error.response?.data?.msg || '添加成果失败')
      } finally {
        loading.value = false
      }
    }
  })
}

const resetForm = () => {
  if (!achievementForm.value) return
  achievementForm.value.resetFields()
  if (fileUploadRef.value) {
    fileUploadRef.value.clearFiles()
  }
  achievementData.files = []
}
</script>

<style scoped>
.achievement-create {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
}
</style> 