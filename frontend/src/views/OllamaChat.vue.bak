<template>
  <div class="ollama-chat">
    <el-card class="chat-card">
      <template #header>
        <div class="card-header">
          <span>Ollama 聊天</span>
          <el-switch
            v-model="useMock"
            active-text="模拟模式"
            inactive-text="真实模式"
          />
        </div>
      </template>
      
      <div class="chat-container">
        <div class="chat-messages" ref="messagesContainer">
          <div v-for="(message, index) in messages" :key="index" 
               :class="['message', message.role]">
            <div class="message-content">
              <el-icon v-if="message.role === 'user'"><User /></el-icon>
              <el-icon v-else><ChatDotRound /></el-icon>
              <span>{{ message.content }}</span>
            </div>
          </div>
        </div>
        
        <div class="chat-input">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="请输入您的问题..."
            @keyup.enter.ctrl="sendMessage"
            :disabled="isLoading"
          />
          <el-button
            type="primary"
            @click="sendMessage"
            :loading="isLoading"
            :disabled="!inputMessage.trim()"
          >
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { User, ChatDotRound } from '@element-plus/icons-vue'
import axios from 'axios'

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const useMock = ref(true)
const messagesContainer = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return
  
  const userMessage = inputMessage.value.trim()
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  
  inputMessage.value = ''
  isLoading.value = true
  
  try {
    const response = await axios.post('http://localhost:5003/api/v1/ollama/chat', {
      query: userMessage,
      use_mock: useMock.value
    })
    
    if (response.data.success) {
      messages.value.push({
        role: 'assistant',
        content: response.data.data.answer
      })
    } else {
      ElMessage.error(response.data.message || '获取回答失败')
      messages.value.push({
        role: 'assistant',
        content: '很抱歉，处理您的请求时出错：' + (response.data.message || '未知错误')
      })
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败，请稍后重试')
    
    // 添加错误消息到聊天窗口
    messages.value.push({
      role: 'assistant',
      content: '很抱歉，我无法处理您的请求。可能是因为服务器正在重启或者Ollama服务未启动。请确保后端服务正常运行并稍后重试。'
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.ollama-chat {
  padding: 20px;
  height: 100%;
}

.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 80%;
}

.message.user .message-content {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-content .el-icon {
  font-size: 20px;
  color: #409eff;
}

.message.assistant .message-content .el-icon {
  color: #67c23a;
}

.chat-input {
  display: flex;
  gap: 10px;
}

.chat-input .el-input {
  flex: 1;
}
</style> 