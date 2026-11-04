<template>
  <div class="global-knowledge-chat">
    <div class="chat-header">
      <h3>知识库问答</h3>
      <p class="description">只根据检索到的技术总结作答。依据不足时会明确说明无法回答。</p>
    </div>
    
    <div class="chat-container">
      <div class="chat-messages" ref="messagesContainer">
        <div v-for="(message, index) in messages" :key="index" 
             :class="['message', message.role === 'user' ? 'user-message' : 'ai-message', { 'error-message': message.isError, 'no-grounded': message.noGrounded }]">
          <div v-if="message.noGrounded" class="no-grounded-banner">没有足够依据</div>
          <div class="message-content">
            <markdown-renderer v-if="message.role === 'ai' && !message.noGrounded" :content="message.content" />
            <div v-else>{{ message.content }}</div>
          </div>

          <div v-if="message.sources && message.sources.length" class="citation-list">
            <button
              v-for="source in message.sources"
              :key="source.doc_id || source.id"
              type="button"
              class="citation-link"
              @click="openCitation(source)"
            >
              <span class="citation-title">{{ source.title || '未命名文档' }}</span>
              <span v-if="source.section" class="citation-section">{{ source.section }}</span>
              <span v-if="source.span" class="citation-span">span {{ source.span[0] }}–{{ source.span[1] }}</span>
            </button>
          </div>
          
          <div v-if="message.role === 'ai' && !message.isError && !message.noGrounded" class="message-meta">
            <span v-if="message.provider" class="provider-tag">{{ message.provider }}</span>
            <span v-if="message.retrievedDocs !== undefined" class="docs-tag">
              引用 {{ message.retrievedDocs }} 篇
            </span>
          </div>
          
          <div class="message-time">{{ formatTime(message.time) }}</div>
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
        
        <el-switch
          v-model="useRag"
          active-text="RAG"
          inactive-text=""
          size="small"
          class="horizontal-switch"
          style="margin-left: 10px;"
        />
      </div>
      
      <el-button size="small" type="danger" @click="clearChat">清空对话</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from '@/utils/axios'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const router = useRouter()
const messagesContainer = ref(null)
const userInput = ref('')
const loading = ref(false)
const provider = ref('deepseek')
const useRag = ref(true)
const messages = reactive([
  {
    role: 'ai',
    content: '我只能根据已检索到的技术总结回答。依据不足时，我会直接说明无法回答。',
    time: new Date()
  }
])

const baseURL = import.meta.env.VITE_API_URL || ''

const sendMessage = async () => {
  const input = userInput.value.trim()
  if (!input || loading.value) return

  messages.push({
    role: 'user',
    content: input,
    time: new Date()
  })
  userInput.value = ''
  await nextTick()
  scrollToBottom()
  loading.value = true
  try {
    if (useRag.value) {
      await sendRag(input)
    } else {
      await sendPlain(input)
    }
  } catch (error) {
    const message = error.response?.data?.message || error.message || '请求失败，请稍后再试'
    ElMessage.error(message)
    messages.push({
      role: 'ai',
      content: message,
      time: new Date(),
      isError: true
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const sendPlain = async (input) => {
  const response = await axios.post('/api/v1/knowledge_base/chat', {
    query: input,
    provider: provider.value
  })
  if (response.data.success) {
    messages.push({
      role: 'ai',
      content: response.data.data.answer,
      time: new Date(),
      provider: response.data.data.provider,
      sources: response.data.data.sources || []
    })
    return
  }
  pushFailure(response.data)
}

const sendRag = async (input) => {
  const token = localStorage.getItem('token')
  const response = await fetch(`${baseURL}/api/v1/rag/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ query: input, provider: provider.value })
  })
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    const body = await response.json()
    pushFailure(body)
    return
  }
  const aiMessage = reactive({
    role: 'ai',
    content: '',
    time: new Date(),
    provider: provider.value,
    sources: [],
    retrievedDocs: 0
  })
  messages.push(aiMessage)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      applyEvent(aiMessage, parseEvent(part))
    }
    await nextTick()
    scrollToBottom()
  }
  if (buffer.trim()) {
    applyEvent(aiMessage, parseEvent(buffer))
  }
}

const pushFailure = (body) => {
  const code = body?.code
  if (code === 'no_grounded_answer') {
    messages.push({
      role: 'ai',
      content: body.message || '知识库中没有足够依据回答该问题。',
      time: new Date(),
      noGrounded: true,
      sources: []
    })
    return
  }
  messages.push({
    role: 'ai',
    content: body?.message || '获取回答失败',
    time: new Date(),
    isError: true
  })
}

const parseEvent = (block) => {
  let event = 'message'
  const dataLines = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  let data = {}
  if (dataLines.length) {
    try {
      data = JSON.parse(dataLines.join('\n'))
    } catch (error) {
      data = {}
    }
  }
  return { event, data }
}

const applyEvent = (aiMessage, parsed) => {
  if (!parsed) return
  if (parsed.event === 'citations') {
    aiMessage.sources = parsed.data.sources || []
    aiMessage.retrievedDocs = aiMessage.sources.length
    aiMessage.provider = parsed.data.model || aiMessage.provider
  } else if (parsed.event === 'token') {
    aiMessage.content += parsed.data.text || ''
  } else if (parsed.event === 'refusal') {
    aiMessage.noGrounded = true
    aiMessage.content = parsed.data.message || '知识库中没有足够依据回答该问题。'
  } else if (parsed.event === 'error') {
    aiMessage.isError = true
    aiMessage.content = parsed.data.message || '生成失败'
  }
}

const openCitation = (source) => {
  const docId = String(source.doc_id || source.id || '')
  if (/^\d+$/.test(docId)) {
    router.push({ name: 'TechSummaryDetail', params: { id: docId } })
  }
}

const clearChat = () => {
  messages.splice(1)
}

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

onMounted(() => {
  scrollToBottom()
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

.error-message {
  background-color: #fef0f0 !important;
  border-left: 4px solid #f56c6c;
}

.no-grounded {
  background-color: #fdf6ec !important;
  border-left: 4px solid #e6a23c;
}

.no-grounded-banner {
  font-size: 12px;
  font-weight: 700;
  color: #b88230;
  margin-bottom: 6px;
}

.citation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.citation-link {
  text-align: left;
  border: 1px solid #d9ecff;
  background: #f5f9ff;
  border-radius: 8px;
  padding: 6px 8px;
  cursor: pointer;
  color: #303133;
}

.citation-title {
  display: block;
  font-weight: 600;
  color: #409EFF;
}

.citation-section,
.citation-span {
  display: block;
  font-size: 12px;
  color: #606266;
}

.message-content {
  word-break: break-word;
}

.message-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.provider-tag, .docs-tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.provider-tag {
  background-color: #e1f3ff;
  color: #409EFF;
}

.docs-tag {
  background-color: #f0f9ff;
  color: #67c23a;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-align: right;
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

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.6; }
  40% { transform: scale(1); opacity: 1; }
}

.horizontal-switch :deep(.el-switch__label) {
  display: inline-block !important;
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
}

.horizontal-switch :deep(.el-switch__label--left) {
  margin-right: 8px !important;
  margin-bottom: 0 !important;
}

.horizontal-switch :deep(.el-switch__label--right) {
  margin-left: 8px !important;
  margin-bottom: 0 !important;
}
</style>
