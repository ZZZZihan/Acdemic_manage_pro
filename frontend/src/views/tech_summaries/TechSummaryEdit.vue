<template>
  <div class="tech-summary-edit">
    <div class="page-header">
      <h2 class="page-title">编辑技术总结</h2>
      <div class="header-actions">
        <el-button @click="$router.push('/tech_summaries')">返回列表</el-button>
        <el-button @click="$router.push(`/tech_summaries/${id}`)">查看详情</el-button>
      </div>
    </div>
    
    <el-card v-loading="loading">
      <el-form 
        ref="formRef" 
        :model="summaryData" 
        :rules="rules" 
        label-width="100px"
        class="summary-form"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="summaryData.title" placeholder="请输入技术总结标题" />
        </el-form-item>
        
        <el-form-item label="类型" prop="summary_type">
          <el-select v-model="summaryData.summary_type" placeholder="请选择类型" style="width: 100%">
            <el-option label="算法" value="算法" />
            <el-option label="工具" value="工具" />
            <el-option label="方法" value="方法" />
            <el-option label="经验" value="经验" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="标签" prop="tags">
          <el-input 
            v-model="summaryData.tags" 
            placeholder="请输入标签，多个标签用逗号分隔" 
          />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <markdown-editor v-model="summaryData.content" placeholder="请输入技术总结内容，支持Markdown格式" />
        </el-form-item>
        
        <el-form-item label="来源网址">
          <el-input 
            v-model="summaryData.source_url" 
            placeholder="内容来源的网址（可选）" 
          />
        </el-form-item>
        
        <el-form-item label="附件">
          <file-upload 
            :initial-files="initialFiles"
            @file-uploaded="handleFileUploaded" 
            @file-removed="handleFileRemoved"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm">保存</el-button>
          <el-button @click="resetForm">重置</el-button>
          <el-button type="danger" @click="confirmDelete">删除</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id
const formRef = ref(null)
const loading = ref(false)
const originalData = ref(null)

const summaryData = reactive({
  title: '',
  summary_type: '',
  tags: '',
  content: '',
  file_path: '',
  original_file_name: '',
  source_url: ''
})

const initialFiles = computed(() => {
  if (summaryData.file_path && summaryData.original_file_name) {
    return [{
      file_path: summaryData.file_path,
      original_name: summaryData.original_file_name
    }]
  }
  return []
})

const rules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  summary_type: [
    { required: true, message: '请选择类型', trigger: 'change' }
  ],
  content: [
    { required: true, message: '请输入内容', trigger: 'blur' }
  ]
}

const fetchSummary = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/v1/tech_summaries/${id}`)
    const data = response.data
    
    summaryData.title = data.title
    summaryData.summary_type = data.summary_type
    summaryData.tags = data.tags
    summaryData.content = data.content
    summaryData.file_path = data.file_path
    summaryData.original_file_name = data.original_file_name
    summaryData.source_url = data.source_url
    
    originalData.value = { ...data }
  } catch (error) {
    console.error('获取技术总结详情失败:', error)
    ElMessage.error('获取技术总结详情失败')
  } finally {
    loading.value = false
  }
}

// 处理文件上传成功
const handleFileUploaded = (fileInfo) => {
  summaryData.file_path = fileInfo.file_path
  summaryData.original_file_name = fileInfo.original_name
}

// 处理文件移除
const handleFileRemoved = () => {
  summaryData.file_path = ''
  summaryData.original_file_name = ''
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await axios.put(`/api/v1/tech_summaries/${id}`, summaryData)
        ElMessage.success('技术总结更新成功')
        router.push(`/tech_summaries/${id}`)
      } catch (error) {
        console.error('更新技术总结失败:', error)
        ElMessage.error('更新技术总结失败')
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.warning('请完善表单信息')
      return false
    }
  })
}

const resetForm = () => {
  if (originalData.value) {
    summaryData.title = originalData.value.title
    summaryData.summary_type = originalData.value.summary_type
    summaryData.tags = originalData.value.tags
    summaryData.content = originalData.value.content
    summaryData.file_path = originalData.value.file_path
    summaryData.original_file_name = originalData.value.original_file_name
    summaryData.source_url = originalData.value.source_url
  }
}

const confirmDelete = () => {
  ElMessageBox.confirm(
    '确定要删除这个技术总结吗？此操作不可恢复。',
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    deleteSummary()
  }).catch(() => {
    // 用户取消删除
  })
}

const deleteSummary = async () => {
  loading.value = true
  try {
    await axios.delete(`/api/v1/tech_summaries/${id}`)
    ElMessage.success('技术总结已删除')
    router.push('/tech_summaries')
  } catch (error) {
    console.error('删除技术总结失败:', error)
    ElMessage.error('删除技术总结失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSummary()
})
</script>

<style scoped>
.tech-summary-edit {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.page-title {
  margin: 0;
}

.summary-form {
  max-width: 800px;
  margin: 0 auto;
}
</style> 