<template>
  <div class="tech-summary-detail" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">技术总结详情</h2>
      <div class="header-actions">
        <el-button @click="$router.push('/tech_summaries')">返回列表</el-button>
        <el-button type="primary" @click="$router.push(`/tech_summaries/${id}/edit`)">编辑</el-button>
      </div>
    </div>
    
    <el-card v-if="summary">
      <div class="summary-header">
        <h1 class="summary-title">{{ summary.title }}</h1>
        <div class="summary-meta">
          <el-tag>{{ summary.summary_type }}</el-tag>
          <span class="meta-item">创建时间: {{ formatDate(summary.created_at) }}</span>
          <span class="meta-item">更新时间: {{ formatDate(summary.updated_at) }}</span>
        </div>
        <div class="summary-tags" v-if="summary.tags">
          <el-tag
            v-for="tag in summary.tags.split(',')"
            :key="tag"
            size="small"
            class="tag-item"
          >
            {{ tag.trim() }}
          </el-tag>
        </div>
        <div class="source-url" v-if="summary.source_url">
          <span class="meta-item">来源: </span>
          <a :href="summary.source_url" target="_blank" class="source-link">{{ summary.source_url }}</a>
        </div>
      </div>
      
      <div class="summary-content">
        <markdown-renderer :content="summary.content" />
      </div>
      
      <div class="summary-attachment" v-if="summary.file_path">
        <h3>附件</h3>
        <el-button type="primary" size="small" @click="downloadFile">
          下载附件: {{ summary.original_file_name || '附件' }}
        </el-button>
      </div>
          <!-- 添加聊天功能 -->
      <el-divider content-position="center">与文档对话</el-divider>
      
      <el-collapse>
        <el-collapse-item title="打开聊天" name="1">
          <document-chat :document-id="id" />
        </el-collapse-item>
      </el-collapse>
    </el-card>
    
    <el-empty v-else description="未找到技术总结" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import DocumentChat from '@/components/DocumentChat.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id
const summary = ref(null)
const loading = ref(false)

const fetchSummary = async () => {
  loading.value = true
  try {
    console.log('获取技术总结详情ID:', id)
    console.log('请求URL:', `/api/v1/tech_summaries/${id}`)
    const response = await axios.get(`/api/v1/tech_summaries/${id}`)
    console.log('技术总结详情响应状态:', response.status)
    console.log('技术总结详情响应数据:', JSON.stringify(response.data, null, 2))
    summary.value = response.data
    console.log('处理后的summary:', summary.value)
  } catch (error) {
    console.error('获取技术总结详情失败:', error)
    console.error('错误详情:', error.response ? error.response.data : error.message)
    ElMessage.error('获取技术总结详情失败')
  } finally {
    loading.value = false
  }
}

const downloadFile = () => {
  if (!summary.value || !summary.value.file_path) return
  
  const fileUrl = `${import.meta.env.VITE_API_URL}/api/v1/files/download/${encodeURIComponent(summary.value.file_path)}`
  window.open(fileUrl, '_blank')
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString()
}

onMounted(() => {
  console.log('技术总结详情页面已挂载，ID:', id)
  if (id) {
    fetchSummary()
  } else {
    console.error('未找到技术总结ID')
    ElMessage.error('未找到技术总结')
    router.push('/tech_summaries')
  }
})
</script>

<style scoped>
.tech-summary-detail {
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

.summary-header {
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 20px;
}

.summary-title {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 24px;
}

.summary-meta {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 15px;
}

.meta-item {
  color: #666;
  font-size: 14px;
}

.summary-tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag-item {
  margin-right: 5px;
}

.summary-content {
  line-height: 1.6;
  margin-bottom: 30px;
}

.summary-attachment {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.source-url {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.source-link {
  color: #666;
  text-decoration: none;
}

.source-link:hover {
  text-decoration: underline;
}

.empty-content {
  color: #999;
  font-style: italic;
  padding: 20px 0;
}

.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  font-size: 16px;
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
}

:deep(.notion-like-preview) {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

:deep(.md-editor-preview-wrapper) {
  padding: 0;
  background-color: transparent;
  border: none;
}

:deep(.md-editor-preview) {
  font-size: 16px;
  line-height: 1.8;
  color: #333;
}

:deep(.md-editor-preview h1) {
  font-size: 28px;
  margin-top: 28px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.3;
  border-bottom: none;
  padding-bottom: 0;
}

:deep(.md-editor-preview h2) {
  font-size: 24px;
  margin-top: 24px;
  margin-bottom: 14px;
  font-weight: 600;
  line-height: 1.3;
  border-bottom: none;
  padding-bottom: 0;
}

:deep(.md-editor-preview h3) {
  font-size: 20px;
  margin-top: 20px;
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.3;
}

:deep(.md-editor-preview p) {
  margin-bottom: 16px;
  line-height: 1.7;
}

:deep(.md-editor-preview ul, .md-editor-preview ol) {
  padding-left: 24px;
  margin-bottom: 16px;
}

:deep(.md-editor-preview li) {
  margin-bottom: 6px;
}

:deep(.md-editor-preview code) {
  background-color: rgba(135, 131, 120, 0.15);
  color: #eb5757;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}

:deep(.md-editor-preview pre) {
  margin-bottom: 16px;
  border-radius: 4px;
}

:deep(.md-editor-preview blockquote) {
  border-left: 3px solid #dfe2e5;
  padding: 0.6em 1.2em;
  color: #6a737d;
  margin: 0 0 16px;
  background-color: #f6f8fa;
  border-radius: 0 4px 4px 0;
}

:deep(.md-editor-preview table) {
  border-collapse: collapse;
  margin-bottom: 16px;
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.md-editor-preview table th, .md-editor-preview table td) {
  border: 1px solid #dfe2e5;
  padding: 8px 12px;
}

:deep(.md-editor-preview table th) {
  background-color: #f6f8fa;
  font-weight: 600;
}

:deep(.md-editor-preview table tr:nth-child(2n)) {
  background-color: #f8f8f8;
}

:deep(.md-editor-preview a) {
  color: #0366d6;
  text-decoration: none;
}

:deep(.md-editor-preview a:hover) {
  text-decoration: underline;
}

:deep(.md-editor-preview img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 16px 0;
}

:deep(.md-editor-preview hr) {
  height: 1px;
  background-color: #e1e4e8;
  border: none;
  margin: 24px 0;
}

:deep(.md-editor-preview .task-list-item) {
  list-style-type: none;
}

:deep(.md-editor-preview .task-list-item-checkbox) {
  margin-right: 8px;
}
</style> 