<template>
  <div class="global-knowledge-chat">
    <div class="chat-header">
      <h3>知识库助手</h3>
      <p class="description">您可以向我提问关于所有技术总结的问题</p>
    </div>
    
    <div class="chat-container">
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(message, index) in messages" :key="index" 
             :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']">
          <div class="message-content">
            <markdown-renderer v-if="message.role === 'ai'" :content="message.content" />
            <div v-else>{{ message.content }}</div>
          </div>
          <div class="message-time">
            {{ formatTime(message.time) }}
            <span v-if="message.role === 'ai' && message.provider" class="message-provider">
              {{ message.provider }}
            </span>
            <span v-if="message.role === 'ai' && message.provider && message.provider.includes('FlashRAG')" 
                  class="engine-badge flash-badge">
              闪电⚡
            </span>
          </div>
        </div>
        <div v-if="loading" class="message ai-message">
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="chat-input">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="2"
          placeholder="输入您的问题..."
          @keyup.enter.native="sendMessage"
          :disabled="loading"
        />
        <el-button 
          type="primary" 
          @click="sendMessage" 
          :disabled="loading || !userInput.trim()"
          :loading="loading"
        >
          发送
        </el-button>
      </div>
    </div>
    
    <div class="chat-settings">
      <div class="settings-group">
        <el-select v-model="provider" placeholder="选择AI模型" size="small" style="min-width: 90px;">
          <el-option label="DeepSeek" value="deepseek" />
          <el-option label="OpenAI" value="openai" />
          <el-option label="Ollama" value="ollama" />
        </el-select>
      </div>
      
      <el-button size="small" type="danger" @click="clearChat">清空对话</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import { InfoFilled } from '@element-plus/icons-vue'

const messagesContainer = ref(null)
const userInput = ref('')
const loading = ref(false)
const initLoading = ref(false)
const provider = ref('deepseek')
const messages = reactive([
  {
    role: 'ai',
    content: '您好！我是您的知识库助手，您可以向我提问关于所有技术总结的任何问题。',
    time: new Date()
  }
])

// 初始化FlashRAG
const initFlashRAG = async () => {
  try {
    initLoading.value = true
    const response = await axios.post('/api/v1/rag/init_flashrag')
    if (response.data.success) {
      ElMessage.success('FlashRAG初始化成功')
      // 添加系统消息
      messages.push({
        role: 'ai',
        content: '✅ FlashRAG索引已重建完成，现在可以更高效地查询知识库',
        time: new Date(),
        engine: 'flashrag'
      })
    } else {
      ElMessage.error(response.data.message || 'FlashRAG初始化失败')
    }
  } catch (error) {
    console.error('FlashRAG初始化请求失败:', error)
    ElMessage.error('初始化请求失败，请稍后再试')
  } finally {
    initLoading.value = false
  }
}

// 初始化知识库
const initKnowledgeBase = async () => {
  try {
    const response = await axios.post('/api/v1/knowledge_base/init')
    if (response.data.success) {
      console.log('知识库初始化成功:', response.data.message)
    } else {
      console.error('知识库初始化失败:', response.data.message)
    }
  } catch (error) {
    console.error('知识库初始化请求失败:', error)
  }
}

// 发送消息
const sendMessage = async () => {
  const input = userInput.value.trim()
  if (!input || loading.value) return
  
  // 添加用户消息
  messages.push({
    role: 'user',
    content: input,
    time: new Date()
  })
  
  // 清空输入框
  userInput.value = ''
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  // 发送请求
  loading.value = true
  try {
    // 始终使用RAG API端点
    const endpoint = '/api/v1/rag/chat'
    
    const payload = {
      query: input,
      provider: provider.value
    }
    
    const response = await axios.post(endpoint, payload)
    
    if (response.data.success) {
      // 添加AI回复
      messages.push({
        role: 'ai',
        content: response.data.data.answer,
        time: new Date(),
        provider: response.data.data.model,
        sources: response.data.data.sources || []
      })
    } else {
      ElMessage.error(response.data.message || '获取回答失败')
    }
  } catch (error) {
    console.error('聊天请求失败:', error)
    ElMessage.error('请求失败，请稍后再试')
  } finally {
    loading.value = false
    
    // 滚动到底部
    await nextTick()
    scrollToBottom()
  }
}

// 清空对话
const clearChat = () => {
  messages.splice(1) // 保留第一条欢迎消息
}

// 格式化时间
const formatTime = (date) => {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 监听消息变化，自动滚动到底部
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

onMounted(() => {
  scrollToBottom()
  initKnowledgeBase()
})
</script>

<style scoped>
.global-knowledge-chat {
  display: flex;
  flex-direction: column;
  height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background-color: #f9f9f9;
}

.chat-header {
  padding: 16px;
  background-color: #409EFF;
  color: white;
}

.chat-header h3 {
  margin: 0;
  font-size: 18px;
}

.chat-header .description {
  margin: 5px 0 0;
  font-size: 14px;
  opacity: 0.9;
}

.chat-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  position: relative;
}

.user-message {
  align-self: flex-end;
  background-color: #e1f3ff;
  color: #333;
}

.ai-message {
  align-self: flex-start;
  background-color: #ffffff;
  color: #333;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.message-content {
  word-break: break-word;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.message-provider {
  font-size: 11px;
  padding: 1px 4px;
  background-color: #eaeaea;
  border-radius: 4px;
}

.engine-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}

.flash-badge {
  background-color: #ffed80;
  color: #e67700;
}

.chat-input {
  padding: 12px;
  background-color: #fff;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 10px;
}

.chat-settings {
  padding: 8px 12px;
  background-color: #f0f0f0;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-group {
  display: flex;
  align-items: center;
  gap: 20px;
}

.info-icon {
  color: #909399;
  cursor: help;
  font-size: 15px;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #999;
  border-radius: 50%;
  display: inline-block;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: 0s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.6;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style> 