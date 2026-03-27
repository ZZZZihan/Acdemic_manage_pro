<template>
  <div class="workspace-view">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Acdemic Manage Pro 2.0</p>
        <h1 data-testid="workspace-title">智能工作台</h1>
        <p class="subtitle">
          用一个线程统筹任务、会议、知识和外部协同。当前骨架已经接上多 provider
          目录、审批流、知识入库和 MCP 能力目录。
        </p>
      </div>
      <div class="hero-stats">
        <div class="stat">
          <span class="stat-label">Providers</span>
          <strong>{{ providers.length }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Pending approvals</span>
          <strong>{{ approvals.length }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Google links</span>
          <strong>{{ connectedAccountCount }}</strong>
        </div>
      </div>
    </section>

    <div class="workspace-grid">
      <aside class="context-column">
        <el-card class="panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>调度 Provider</span>
              <el-tag type="info">{{ selectedProfile?.tier || '-' }} tier</el-tag>
            </div>
          </template>
          <el-select v-model="selectedProvider" class="full-width" data-testid="provider-select">
            <el-option
              v-for="provider in providers"
              :key="provider.name"
              :label="provider.name"
              :value="provider.name"
            />
          </el-select>
          <p class="panel-copy">{{ selectedProfile?.description || '正在加载能力说明。' }}</p>
          <div class="capability-tags">
            <el-tag effect="plain" :type="selectedProfile?.supports_tools ? 'success' : 'info'">tools</el-tag>
            <el-tag effect="plain" :type="selectedProfile?.supports_external_write ? 'warning' : 'info'">external writes</el-tag>
            <el-tag effect="plain" :type="selectedProfile?.local_only ? 'danger' : 'success'">local mode</el-tag>
          </div>
        </el-card>

        <el-card class="panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>外部系统</span>
              <el-tag type="warning">{{ connectedAccountCount }}/{{ externalAccounts.length }}</el-tag>
            </div>
          </template>
          <div class="account-list">
            <div v-for="account in externalAccounts" :key="account.id" class="account-row">
              <div>
                <strong>{{ account.account_type }}</strong>
                <p>{{ account.status }}</p>
              </div>
              <el-tag :type="account.status === 'connected' ? 'success' : 'info'">
                {{ account.writable ? 'write' : 'read' }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <el-card class="panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>快捷动作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button class="action-button" plain data-testid="quick-action-seed-knowledge" @click="seedKnowledge">
              预置一条 MCP 知识
            </el-button>
            <el-button class="action-button" plain @click="applyPrompt('请安排下周二下午三点的项目评审会议，并通知大家。')">
              会议安排
            </el-button>
            <el-button
              class="action-button"
              plain
              data-testid="quick-action-task"
              @click="applyPrompt('请把这周需要推进的项目任务整理成行动项。')"
            >
              任务梳理
            </el-button>
          </div>
        </el-card>
      </aside>

      <main class="chat-column">
        <el-card class="thread-card" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>统一线程</span>
              <el-tag type="success">{{ threadId ? 'ready' : 'booting' }}</el-tag>
            </div>
          </template>

          <div class="message-stack">
            <div
              v-for="message in messages"
              :key="message.id"
              class="message-item"
              :class="message.role"
              data-testid="thread-message"
              :data-role="message.role"
            >
              <div class="message-meta">
                <span>{{ message.role === 'assistant' ? 'Copilot' : 'You' }}</span>
                <small data-testid="message-provider">{{ message.provider || 'workspace' }}</small>
              </div>
              <p data-testid="message-content">{{ message.content }}</p>
            </div>
            <div v-if="!messages.length" class="message-empty">
              这里会汇总线程消息、工具动作和审批结果。先发送一条指令试运行 2.0 骨架。
            </div>
          </div>

          <div class="composer">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="5"
              resize="none"
              placeholder="例如：请安排下周二下午三点的项目评审会议，并通知大家。"
            />
            <div class="composer-actions">
              <span class="composer-hint">当前 provider: {{ selectedProvider }}</span>
              <el-button type="primary" :loading="sending" data-testid="send-message-button" @click="sendMessage">
                发送到工作台
              </el-button>
            </div>
          </div>
        </el-card>
      </main>

      <aside class="ops-column">
        <el-card class="panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>待审批</span>
              <el-tag type="danger">{{ approvals.length }}</el-tag>
            </div>
          </template>
          <div v-if="approvals.length" class="approval-list">
            <div v-for="approval in approvals" :key="approval.id" class="approval-card" data-testid="approval-card">
              <strong>{{ approval.tool_name }}</strong>
              <p>{{ approval.rationale }}</p>
              <small>{{ approval.provider }} · {{ approval.status }}</small>
              <div class="approval-actions">
                <el-button
                  size="small"
                  type="primary"
                  data-testid="approval-approve-button"
                  @click="decideApproval(approval.id, 'approved')"
                >
                  批准
                </el-button>
                <el-button size="small" plain @click="decideApproval(approval.id, 'rejected')">拒绝</el-button>
              </div>
            </div>
          </div>
          <div v-else class="message-empty">
            暂无审批。发送带有外部协同意图的消息后，这里会出现 Calendar 审批卡片。
          </div>
        </el-card>

        <el-card class="panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>架构提示</span>
            </div>
          </template>
          <ul class="insight-list">
            <li>OpenAI / Claude 是高风险工作流的双核心编排器。</li>
            <li>DeepSeek / MiniMax 复用同一工具目录，优先承担普通操作和总结。</li>
            <li>Ollama 用于本地隐私和离线兜底，不默认开放外部写操作。</li>
            <li>Google 日历与邮件通过统一审批流进入业务系统，不直接暴露给前端。</li>
          </ul>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/axiosV2'

type Provider = {
  name: string
  tier: string
  default_model: string
  local_only: boolean
  supports_tools: boolean
  supports_external_write: boolean
  supports_google_connectors: boolean
  description: string
}

type ExternalAccount = {
  id: string
  account_type: string
  status: string
  writable: boolean
}

type Message = {
  id: string
  role: 'user' | 'assistant'
  provider: string | null
  content: string
}

type Approval = {
  id: string
  tool_name: string
  provider: string
  status: string
  rationale: string
}

const providers = ref<Provider[]>([])
const externalAccounts = ref<ExternalAccount[]>([])
const approvals = ref<Approval[]>([])
const messages = ref<Message[]>([])
const selectedProvider = ref('openai')
const draft = ref('请安排下周二下午三点的项目评审会议，并通知大家。')
const threadId = ref<string | null>(null)
const sending = ref(false)

const selectedProfile = computed(() => {
  return providers.value.find((item) => item.name === selectedProvider.value) || null
})

const connectedAccountCount = computed(() => {
  return externalAccounts.value.filter((item) => item.status === 'connected').length
})

async function bootstrap() {
  await Promise.all([
    loadProviders(),
    loadExternalAccounts(),
    ensureThread(),
    loadApprovals(),
  ])
}

async function loadProviders() {
  const response = await request.get('/api/v2/providers')
  providers.value = response.data.providers
}

async function loadExternalAccounts() {
  const response = await request.get('/api/v2/external-accounts')
  externalAccounts.value = response.data.items
}

async function loadApprovals() {
  const response = await request.get('/api/v2/approvals')
  approvals.value = response.data.items
}

async function ensureThread() {
  if (threadId.value) {
    return
  }
  const response = await request.post('/api/v2/chat/threads', {
    title: 'Workspace Copilot',
  })
  threadId.value = response.data.thread.id
}

async function refreshThread() {
  if (!threadId.value) {
    return
  }
  const response = await request.get(`/api/v2/chat/threads/${threadId.value}`)
  messages.value = response.data.contents.messages
}

function applyPrompt(value: string) {
  draft.value = value
}

async function sendMessage() {
  if (!draft.value.trim()) {
    ElMessage.warning('请输入一条工作台指令')
    return
  }

  sending.value = true
  try {
    await ensureThread()
    await request.post('/api/v2/chat/messages', {
      thread_id: threadId.value,
      provider: selectedProvider.value,
      content: draft.value,
    })
    draft.value = ''
    await Promise.all([refreshThread(), loadApprovals()])
  } finally {
    sending.value = false
  }
}

async function decideApproval(id: string, decision: 'approved' | 'rejected') {
  await request.post(`/api/v2/approvals/${id}/decision`, { decision })
  await Promise.all([loadApprovals(), refreshThread()])
  ElMessage.success(`审批已${decision === 'approved' ? '批准' : '拒绝'}`)
}

async function seedKnowledge() {
  await request.post('/api/v2/knowledge/assets', {
    title: 'MCP 设计笔记',
    content: '内部工具要区分 tools、resources、prompts 三类能力，并统一经过审批和策略层。',
    source_type: 'note',
    tags: ['mcp', 'architecture'],
  })
  ElMessage.success('已写入一条示例知识，可供后端 MCP 搜索能力使用')
}

onMounted(async () => {
  await bootstrap()
  await refreshThread()
})
</script>

<style scoped>
:root {
  --workspace-ink: #10212b;
  --workspace-muted: #5b6c77;
  --workspace-accent: #0f8b8d;
  --workspace-accent-soft: #dff5f1;
  --workspace-paper: rgba(255, 255, 255, 0.86);
  --workspace-line: rgba(16, 33, 43, 0.08);
  --workspace-shadow: 0 24px 60px rgba(14, 47, 61, 0.12);
}

.workspace-view {
  min-height: 100vh;
  padding: 28px;
  color: var(--workspace-ink);
  background:
    radial-gradient(circle at top left, rgba(15, 139, 141, 0.18), transparent 35%),
    radial-gradient(circle at top right, rgba(237, 201, 72, 0.16), transparent 30%),
    linear-gradient(160deg, #f6fbfa 0%, #f2f1ea 100%);
  font-family: 'IBM Plex Sans', 'PingFang SC', sans-serif;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
  padding: 28px 30px;
  border: 1px solid var(--workspace-line);
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(246, 251, 250, 0.78));
  box-shadow: var(--workspace-shadow);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--workspace-accent);
}

.hero h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.05;
}

.subtitle {
  max-width: 720px;
  margin: 14px 0 0;
  font-size: 16px;
  line-height: 1.7;
  color: var(--workspace-muted);
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 12px;
  min-width: 320px;
}

.stat {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 116px;
  padding: 18px;
  border-radius: 20px;
  background: rgba(15, 139, 141, 0.08);
}

.stat-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--workspace-muted);
}

.stat strong {
  font-size: 30px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  gap: 20px;
}

.panel,
.thread-card {
  border: 1px solid var(--workspace-line);
  border-radius: 24px;
  background: var(--workspace-paper);
  backdrop-filter: blur(16px);
  box-shadow: var(--workspace-shadow);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
}

.full-width {
  width: 100%;
}

.panel-copy {
  margin: 14px 0 0;
  color: var(--workspace-muted);
  line-height: 1.6;
}

.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.account-list,
.quick-actions,
.approval-list,
.insight-list {
  display: grid;
  gap: 12px;
}

.account-row,
.approval-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.8);
}

.account-row p,
.approval-card p {
  margin: 6px 0 0;
  color: var(--workspace-muted);
}

.action-button {
  width: 100%;
  justify-content: flex-start;
}

.message-stack {
  display: grid;
  gap: 12px;
  min-height: 420px;
  max-height: 56vh;
  padding-right: 4px;
  overflow-y: auto;
}

.message-item {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--workspace-line);
}

.message-item.assistant {
  background: linear-gradient(135deg, rgba(223, 245, 241, 0.92), rgba(255, 255, 255, 0.92));
}

.message-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--workspace-muted);
}

.message-item p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.65;
}

.message-empty {
  padding: 20px;
  border-radius: 18px;
  color: var(--workspace-muted);
  background: rgba(255, 255, 255, 0.72);
}

.composer {
  margin-top: 18px;
}

.composer-actions,
.approval-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.composer-hint {
  font-size: 13px;
  color: var(--workspace-muted);
}

.insight-list {
  margin: 0;
  padding-left: 18px;
  color: var(--workspace-muted);
  line-height: 1.7;
}

@media (max-width: 1280px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }

  .hero-stats {
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .workspace-view {
    padding: 16px;
  }

  .hero {
    padding: 20px;
  }

  .hero h1 {
    font-size: 30px;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }
}
</style>
