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
              <h4>两种问答模式说明：</h4>
              <ul>
                <li><strong>RAG模式</strong>：智能检索增强生成，优先使用向量检索在知识库中查找相关文档，如果向量检索不可用则自动降级到关键词搜索，最后基于检索到的内容生成专业回答。适合查询知识库中的专业内容。</li>
                <li><strong>普通模式</strong>：直接使用AI模型回答问题，不依赖知识库内容。可以回答任何通用问题，基于AI的训练数据，响应速度快。</li>
              </ul>
              
              <h4>使用建议：</h4>
              <ul>
                <li><strong>查询专业技术内容</strong>：推荐使用"RAG模式"，基于您的知识库内容，准确性更高</li>
                <li><strong>通用技术问题</strong>：使用"普通模式"，如"React和Vue有什么区别？"等通用问题</li>
                <li><strong>快速问答</strong>：普通模式响应更快，适合快速获取答案</li>
              </ul>
              
              <h4>使用提示：</h4>
              <p>RAG模式会智能选择最佳的检索方式（向量检索或关键词搜索），确保在各种情况下都能提供准确的回答。如果想要基于知识库的专业回答，选择RAG模式；如果想要快速的通用回答，选择普通模式。</p>
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