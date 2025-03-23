<template>
  <div class="file-upload-container">
    <el-upload
      class="file-uploader"
      :action="uploadUrl"
      :headers="headers"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-exceed="handleExceed"
      :on-remove="handleRemove"
      :before-upload="beforeUpload"
      :file-list="fileList"
      :multiple="true"
      name="file"
      :auto-upload="true"
    >
      <el-button type="primary">选择文件</el-button>
      <template #tip>
        <div class="el-upload__tip">
          支持上传 {{ allowedExtensions.join(', ') }} 格式文件，大小不超过 {{ maxSize }}MB
        </div>
      </template>
    </el-upload>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  initialFiles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['file-uploaded', 'file-removed'])

const authStore = useAuthStore()
const fileList = ref([])
const allowedExtensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png']
const maxSize = 10 // MB

// 计算上传URL
const uploadUrl = computed(() => {
  return `${import.meta.env.VITE_API_URL}/api/v1/files/upload`
})

// 计算请求头，包含认证信息
const headers = computed(() => {
  return {
    Authorization: `Bearer ${authStore.token}`
  }
})

// 监听初始文件变化
watch(() => props.initialFiles, (newFiles) => {
  if (newFiles && newFiles.length > 0) {
    // 将初始文件转换为fileList格式
    fileList.value = newFiles.map(file => ({
      name: file.original_name || '附件',
      url: `${import.meta.env.VITE_API_URL}/api/v1/files/download/${encodeURIComponent(file.file_path)}`,
      // 保存原始文件信息，用于后续处理
      raw: file
    }))
  } else {
    fileList.value = []
  }
}, { immediate: true })

// 组件挂载时初始化文件列表
onMounted(() => {
  if (props.initialFiles && props.initialFiles.length > 0) {
    fileList.value = props.initialFiles.map(file => ({
      name: file.original_name || '附件',
      url: `${import.meta.env.VITE_API_URL}/api/v1/files/download/${encodeURIComponent(file.file_path)}`,
      raw: file
    }))
  }
})

// 上传前检查文件类型和大小
const beforeUpload = (file) => {
  // 检查文件类型
  const extension = file.name.split('.').pop().toLowerCase()
  const isAllowed = allowedExtensions.includes(extension)
  if (!isAllowed) {
    ElMessage.error(`只允许上传 ${allowedExtensions.join(', ')} 格式的文件!`)
    return false
  }
  
  // 检查文件大小
  const isLessThanMaxSize = file.size / 1024 / 1024 < maxSize
  if (!isLessThanMaxSize) {
    ElMessage.error(`文件大小不能超过 ${maxSize}MB!`)
    return false
  }
  
  return true
}

// 处理上传成功
const handleSuccess = (response, file, fileList) => {
  console.log('文件上传成功:', response)
  // 发送文件信息到父组件
  emit('file-uploaded', {
    original_name: file.name,
    file_path: response.file_path,
    file_size: file.size,
    file_type: file.type
  })
  ElMessage.success('文件上传成功')
}

// 处理上传错误
const handleError = (error) => {
  console.error('文件上传失败:', error)
  ElMessage.error('文件上传失败，请重试')
}

// 处理超出文件数量限制
const handleExceed = () => {
  ElMessage.warning('已达到文件上传数量限制')
}

// 处理文件移除
const handleRemove = (file) => {
  console.log('文件被移除:', file)
  // 如果文件有raw属性，说明是初始文件
  if (file.raw) {
    emit('file-removed', file.raw)
  } else {
    // 查找对应的文件信息
    const fileIndex = fileList.value.findIndex(f => f.uid === file.uid)
    if (fileIndex !== -1) {
      emit('file-removed', fileList.value[fileIndex])
    }
  }
}

// 清除文件列表
const clearFiles = () => {
  fileList.value = []
}

// 暴露方法给父组件
defineExpose({
  clearFiles
})
</script>

<style scoped>
.file-upload-container {
  width: 100%;
}
.file-uploader {
  width: 100%;
}
.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 7px;
}
</style> 