<template>
  <div class="tech-summary-create">
    <div class="page-header">
      <h2 class="page-title">添加技术总结</h2>
      <el-button @click="$router.push('/tech_summaries')">返回列表</el-button>
    </div>
    
    <el-card class="mb-20">
      <div class="card-title">
        <h3>网页内容爬取</h3>
        <p class="description">输入知识所在的网址，系统将自动爬取内容并使用AI进行总结</p>
      </div>
      
      <el-form :inline="true" :model="crawlForm" class="crawl-form">
        <el-form-item label="网址" class="url-input">
          <el-input 
            v-model="crawlForm.url" 
            placeholder="请输入要爬取的网页URL" 
            clearable
          />
        </el-form-item>
        
        <el-form-item label="AI模型">
          <el-select v-model="crawlForm.provider" placeholder="选择AI模型">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="OpenAI" value="openai" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="crawlAndSummarize" 
            :loading="crawling"
          >
            爬取并总结
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-collapse v-if="showAdvanced">
        <el-collapse-item title="高级选项" name="1">
          <el-form :model="crawlForm" label-width="100px">
            <el-form-item label="自定义提示词">
              <el-input 
                v-model="crawlForm.customPrompt" 
                type="textarea" 
                :rows="4" 
                placeholder="自定义提示词，用于指导AI如何总结内容"
              />
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
      
      <div class="toggle-advanced">
        <el-link type="primary" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? '隐藏高级选项' : '显示高级选项' }}
        </el-link>
      </div>
    </el-card>
    
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
            @file-uploaded="handleFileUploaded" 
            @file-removed="handleFileRemoved"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm">提交</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import MarkdownEditor from '@/components/MarkdownEditor.vue'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const crawling = ref(false)
const showAdvanced = ref(false)

const summaryData = reactive({
  title: '',
  summary_type: '',
  tags: '',
  content: '',
  file_path: '',
  original_file_name: '',
  source_url: ''
})

const crawlForm = reactive({
  url: '',
  provider: 'deepseek',
  customPrompt: ''
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

// 爬取网页并使用AI总结
const crawlAndSummarize = async () => {
  if (!crawlForm.url) {
    ElMessage.warning('请输入要爬取的网页URL')
    return
  }
  
  crawling.value = true
  try {
    const requestData = {
      url: crawlForm.url,
      provider: crawlForm.provider
    }
    
    // 如果有自定义提示词，添加到请求数据中
    if (crawlForm.customPrompt) {
      requestData.custom_prompt = crawlForm.customPrompt
    }
    
    console.log('开始爬取和总结，请求数据:', requestData)
    
    // 设置超时提示
    const timeoutMsg = setTimeout(() => {
      ElMessage.info('总结处理中，API调用可能需要较长时间，请耐心等待...')
    }, 5000) // 5秒后提示用户请求可能较慢
    
    try {
      // 增加请求超时时间
      const response = await axios.post('/api/v1/tech_summaries/crawl', requestData, {
        timeout: 120000 // 2分钟超时
      })
      
      // 清除超时提示
      clearTimeout(timeoutMsg)
      
      if (response.data.success) {
        const data = response.data.data
        
        // 添加调试日志
        console.log('爬取结果数据:', data)
        console.log('返回的标签:', data.tags)
        
        // 填充表单数据
        summaryData.title = data.title || '技术总结'
        summaryData.content = data.content
        summaryData.source_url = data.url
        
        // 如果API返回了标签，则使用API返回的标签
        if (data.tags) {
          console.log('使用API返回的标签:', data.tags)
          summaryData.tags = data.tags
        } else {
          // 否则根据内容自动推断类型和标签
          console.log('API未返回标签，使用自动推断')
          inferTypeAndTags(data.content)
        }
        
        ElMessage.success('网页内容爬取和总结成功')
      } else {
        ElMessage.error(response.data.message || '爬取失败')
      }
    } catch (error) {
      // 清除超时提示
      clearTimeout(timeoutMsg)
      
      console.error('爬取和总结失败:', error)
      
      // 检查是否是超时错误
      if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
        ElMessage.error('API调用超时，服务响应时间过长')
        
        // 如果是DeepSeek超时，询问用户是否尝试使用OpenAI
        if (crawlForm.provider === 'deepseek') {
          ElMessageBox.confirm(
            'DeepSeek API响应超时，是否尝试使用OpenAI进行总结？',
            '切换AI提供商',
            {
              confirmButtonText: '使用OpenAI',
              cancelButtonText: '取消',
              type: 'warning',
            }
          )
            .then(() => {
              // 切换到OpenAI并重试
              crawlForm.provider = 'openai'
              ElMessage.info('已切换到OpenAI，正在重新尝试...')
              crawlAndSummarize() // 递归调用自身重试
            })
            .catch(() => {
              ElMessage.info('已取消操作')
            })
        }
      } else if (error.response) {
        // 服务器返回了错误状态码
        console.error('错误响应状态:', error.response.status)
        console.error('错误响应数据:', error.response.data)
        
        // 根据状态码给出更具体的错误信息
        if (error.response.status === 400) {
          const errorMsg = error.response.data.message || '请求参数错误'
          ElMessage.error(`爬取失败: ${errorMsg}`)
          
          // 如果是DeepSeek API错误，提示用户尝试OpenAI
          if (crawlForm.provider === 'deepseek' && errorMsg.includes('DeepSeek API')) {
            ElMessageBox.confirm(
              'DeepSeek API调用失败，是否尝试使用OpenAI进行总结？',
              '切换AI提供商',
              {
                confirmButtonText: '使用OpenAI',
                cancelButtonText: '取消',
                type: 'warning',
              }
            )
              .then(() => {
                // 切换到OpenAI并重试
                crawlForm.provider = 'openai'
                ElMessage.info('已切换到OpenAI，正在重新尝试...')
                crawlAndSummarize() // 递归调用自身重试
              })
              .catch(() => {
                ElMessage.info('已取消操作')
              })
          }
        } else if (error.response.status === 401) {
          ElMessage.error('未授权，请重新登录')
          // 可以在这里添加重定向到登录页面的逻辑
        } else if (error.response.status === 500) {
          ElMessage.error('服务器内部错误，请稍后再试')
        } else {
          ElMessage.error(`请求失败，状态码: ${error.response.status}`)
        }
      } else {
        // 网络错误或其他错误
        ElMessage.error(`请求失败: ${error.message}`)
      }
    }
  } catch (e) {
    console.error('爬取过程中发生未知错误:', e)
    ElMessage.error('爬取过程中发生未知错误')
  } finally {
    crawling.value = false
  }
}

// 根据内容推断类型和标签
const inferTypeAndTags = (content) => {
  // 这里可以实现一个简单的推断逻辑
  // 例如，根据内容中的关键词来推断类型和标签
  const contentLower = content.toLowerCase()
  
  // 推断类型
  if (contentLower.includes('算法') || contentLower.includes('algorithm')) {
    summaryData.summary_type = '算法'
  } else if (contentLower.includes('工具') || contentLower.includes('tool')) {
    summaryData.summary_type = '工具'
  } else if (contentLower.includes('方法') || contentLower.includes('method')) {
    summaryData.summary_type = '方法'
  } else if (contentLower.includes('经验') || contentLower.includes('experience')) {
    summaryData.summary_type = '经验'
  } else {
    summaryData.summary_type = '其他'
  }
  
  // 提取可能的标签
  const possibleTags = []
  const keywords = [
    '人工智能', 'AI', '机器学习', 'ML', '深度学习', 'DL',
    '前端', 'Frontend', '后端', 'Backend', '全栈', 'Fullstack',
    '数据库', 'Database', 'SQL', 'NoSQL',
    'Python', 'Java', 'JavaScript', 'C++', 'Go', 'Rust',
    'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask',
    '云计算', 'Cloud', '容器', 'Container', 'Docker', 'Kubernetes',
    '大数据', 'Big Data', '数据分析', 'Data Analysis',
    '网络安全', 'Security', '加密', 'Encryption',
    // 添加计算机视觉相关标签
    'OpenCV', '计算机视觉', 'Computer Vision', '图像处理', 'Image Processing',
    '摄像头', 'Camera', 'USB设备', 'USB Device', 'VID', 'PID',
    '动态库', 'DLL', '设备驱动', 'Device Driver',
    // 添加其他常见技术标签
    'API', 'RESTful', 'GraphQL', 'WebSocket', 'HTTP',
    '微服务', 'Microservices', '分布式系统', 'Distributed Systems',
    '算法', 'Algorithm', '数据结构', 'Data Structure',
    '操作系统', 'OS', 'Linux', 'Windows', 'MacOS',
    '嵌入式', 'Embedded', '物联网', 'IoT'
  ]
  
  for (const keyword of keywords) {
    if (contentLower.includes(keyword.toLowerCase())) {
      possibleTags.push(keyword)
    }
  }
  
  // 限制标签数量，最多5个
  summaryData.tags = possibleTags.slice(0, 5).join(', ')
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
        const response = await axios.post('/api/v1/tech_summaries', summaryData)
        ElMessage.success('技术总结创建成功')
        router.push(`/tech_summaries/${response.data.id}`)
      } catch (error) {
        console.error('创建技术总结失败:', error)
        ElMessage.error('创建技术总结失败')
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
  if (formRef.value) {
    formRef.value.resetFields()
  }
  summaryData.file_path = ''
  summaryData.original_file_name = ''
  summaryData.source_url = ''
}
</script>

<style scoped>
.tech-summary-create {
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

.mb-20 {
  margin-bottom: 20px;
}

.card-title {
  margin-bottom: 20px;
}

.card-title h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.description {
  color: #666;
  margin: 0;
}

.crawl-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
}

.url-input {
  width: 400px;
  max-width: 100%;
}

.toggle-advanced {
  margin-top: 10px;
  text-align: right;
}

.summary-form {
  max-width: 800px;
  margin: 0 auto;
}
</style> 