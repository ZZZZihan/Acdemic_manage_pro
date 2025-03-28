# RAG (检索增强生成) 系统使用指南

本文档介绍了系统中RAG (Retrieval Augmented Generation, 检索增强生成) 功能的使用方法和配置步骤。

## 什么是RAG？

RAG是一种混合架构技术，将信息检索系统与生成式AI模型相结合，以提高问答系统的准确性和可靠性。它的工作流程如下：

1. **检索阶段**：当用户提出问题时，系统首先从知识库中检索与问题最相关的文档或文档片段。
2. **生成阶段**：将检索到的文档内容作为上下文提供给大型语言模型，让模型基于这些上下文生成回答。

相比于传统的纯生成式AI回答，RAG具有以下优势：

- 更准确的回答，减少"幻觉"（编造信息）
- 提供信息来源，增加可靠性和可解释性
- 能够回答知识库中特定领域的问题
- 降低API成本，因为可以使用较小的模型配合知识库

## 系统特点

我们的RAG系统具有以下特点：

- **混合检索策略**：同时使用向量检索和关键词检索，确保找到最相关的文档
- **语义分块处理**：自动将长文档分割成语义连贯的小块，提高检索精度
- **多模型支持**：支持OpenAI、DeepSeek和本地Ollama模型
- **结果缓存**：缓存常见问题的回答，提高响应速度
- **优雅降级**：当API不可用时，自动回退到模拟回答

## 配置方法

### 1. 环境变量配置

在`backend`目录下创建`.env`文件（可以复制`.env.example`），配置以下环境变量：

```
# OpenAI API配置
OPENAI_API_URL=https://api.openai.com/v1/chat/completions
OPENAI_API_KEY=your-openai-api-key

# DeepSeek API配置
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-deepseek-api-key

# Ollama API配置（本地模型）
OLLAMA_API_URL=http://localhost:11434/api/chat
```

至少需要配置一种API才能使用真实的语言模型能力。如果没有配置任何API，系统将使用模拟回答。

### 2. 安装依赖

RAG系统需要以下Python依赖：

```bash
pip install sentence-transformers numpy requests python-dotenv
```

### 3. 知识库准备

系统会自动从现有的技术总结中构建知识库。您也可以手动添加文档：

```python
from app.utils.knowledge_base import knowledge_base

knowledge_base.add_document(
    doc_id="doc123",
    title="文档标题",
    content="文档内容...",
    metadata={"author": "作者", "date": "2023-04-01"}
)
```

## 使用方法

### 前端使用

在前端聊天界面中，您可以：

1. 选择使用的AI模型（DeepSeek/OpenAI/Ollama）
2. 开启或关闭RAG功能（通过切换开关）
3. 输入问题并获取回答

### API调用

您也可以直接调用API：

```bash
curl -X POST http://localhost:5000/api/v1/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是RAG?", "provider": "deepseek"}'
```

响应格式：

```json
{
  "success": true,
  "data": {
    "answer": "根据文档1，RAG（检索增强生成）是一种将信息检索系统与生成式AI模型结合的混合架构技术...",
    "sources": [{"title": "RAG技术概述", "id": "doc1"}],
    "model": "RAG+deepseek"
  }
}
```

## 故障排除

1. **检索不到相关文档**：
   - 确保知识库中已添加相关文档
   - 尝试使用更精确的问题描述

2. **API请求失败**：
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 查看日志文件了解详细错误信息

3. **响应过慢**：
   - 考虑减小文档分块大小
   - 增加缓存大小
   - 使用更快的本地模型（如Ollama）

## 开发扩展

要进一步扩展RAG功能，可以考虑：

1. 添加更多向量索引方法（如FAISS、Pinecone等）
2. 实现更复杂的排序算法（如Reciprocal Rank Fusion）
3. 添加用户反馈机制，持续优化检索质量
4. 支持多模态内容（如图片、表格等）

## 日志和监控

系统会记录各种操作日志，可以通过以下方式查看：

```bash
grep "RAG" backend/logs/app.log
```

关键指标包括：
- 检索命中率
- API调用成功率
- 缓存命中率
- 响应时间 