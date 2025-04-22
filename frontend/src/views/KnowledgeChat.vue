<template>
  <div class="knowledge-chat-page">
    <div class="page-header">
      <h2 class="page-title">知识库聊天</h2>
      <div class="header-actions">
        <el-button @click="goToTechSummaries">返回技术总结</el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="chat-card">
          <global-knowledge-chat />
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="info-card">
          <h3>知识库助手使用说明</h3>
          <div class="info-content">
            <p>知识库助手可以回答关于所有技术总结的问题，您可以：</p>
            <ul>
              <li>询问特定技术的用法和原理</li>
              <li>查询某个概念的解释</li>
              <li>寻找解决特定问题的方法</li>
              <li>了解不同技术之间的比较</li>
            </ul>
            
            <p>示例问题：</p>
            <ul>
              <li>"React和Vue有什么区别？"</li>
              <li>"如何解决Node.js内存泄漏问题？"</li>
              <li>"Docker容器和虚拟机的优缺点是什么？"</li>
              <li>"Python中如何处理异步操作？"</li>
            </ul>
            
            <div class="tips">
              <h4>提示：</h4>
              <p>问题越具体，回答越准确。如果回答不满意，可以尝试重新表述问题或提供更多上下文。</p>
            </div>
          </div>
        </el-card>
        
        <el-card class="stats-card">
          <h3>知识库统计</h3>
          <div class="stats-content">
            <div class="stat-item">
              <div class="stat-label">技术总结数量</div>
              <div class="stat-value">{{ stats.totalSummaries }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">最近更新</div>
              <div class="stat-value">{{ stats.lastUpdate }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import GlobalKnowledgeChat from '@/components/GlobalKnowledgeChat.vue'
import axios from '@/utils/axios'

const router = useRouter()
const stats = ref({
  totalSummaries: 0,
  lastUpdate: '-'
})

// 跳转到技术总结页面
const goToTechSummaries = () => {
  console.log('跳转到技术总结页面')
  try {
    router.push('/tech_summaries')
  } catch (error) {
    console.error('路由跳转错误:', error)
    // 如果正常路由跳转失败，尝试使用window.location
    window.location.href = '/tech_summaries'
  }
}

// 获取知识库统计信息
const fetchStats = async () => {
  try {
    const response = await axios.get('/api/v1/tech_summaries', {
      params: {
        per_page: 1,
        page: 1
      }
    })
    
    if (response.data) {
      stats.value.totalSummaries = response.data.total || 0
      
      // 获取最近更新时间
      if (response.data.items && response.data.items.length > 0) {
        const latestSummary = response.data.items[0]
        stats.value.lastUpdate = new Date(latestSummary.updated_at).toLocaleDateString()
      }
    }
  } catch (error) {
    console.error('获取知识库统计信息失败:', error)
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.knowledge-chat-page {
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

.chat-card {
  margin-bottom: 20px;
}

.info-card, .stats-card {
  margin-bottom: 20px;
}

.info-card h3, .stats-card h3 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 18px;
  color: #409EFF;
}

.info-content {
  font-size: 14px;
  line-height: 1.6;
}

.info-content ul {
  padding-left: 20px;
  margin-bottom: 15px;
}

.info-content li {
  margin-bottom: 5px;
}

.tips {
  background-color: #f8f8f8;
  border-left: 3px solid #409EFF;
  padding: 10px 15px;
  margin-top: 15px;
  border-radius: 0 4px 4px 0;
}

.tips h4 {
  margin-top: 0;
  margin-bottom: 5px;
  font-size: 15px;
  color: #409EFF;
}

.tips p {
  margin: 0;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px dashed #eee;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #409EFF;
}
</style> 