import logging
import time
import random
import hashlib
import json
import requests
import os
from typing import Dict, List, Any, Optional
from .knowledge_base import knowledge_base
from .vector_knowledge_base import vector_knowledge_base

# 配置日志
logger = logging.getLogger(__name__)

# LLM API配置
OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# Ollama配置
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")

class RAGService:
    """
    RAG (Retrieval Augmented Generation) 服务
    结合检索和生成能力，增强问答系统
    """
    
    def __init__(self):
        """初始化RAG服务"""
        self.knowledge_base = knowledge_base
        self.vector_knowledge_base = vector_knowledge_base
        
        # 缓存机制
        self.query_cache = {}
        self.cache_size = 100  # 最大缓存条目数
        
        # 延迟初始化标志
        self._vector_kb_initialized = False
        
        # 记录是否有可用的LLM API
        self.has_openai = bool(OPENAI_API_KEY)
        self.has_deepseek = bool(DEEPSEEK_API_KEY)
        
        # 记录LLM API状态
        if self.has_openai:
            logger.info("OpenAI API 已配置")
        if self.has_deepseek:
            logger.info("DeepSeek API 已配置")
        if not (self.has_openai or self.has_deepseek):
            logger.warning("未配置任何LLM API，将使用模拟回答")
    
    def _ensure_vector_kb_initialized(self):
        """确保向量知识库已初始化（延迟加载）"""
        if self._vector_kb_initialized:
            return
            
        logger.info("正在初始化向量知识库...")
        self._init_vector_knowledge_base()
        self._vector_kb_initialized = True
    
    def _init_vector_knowledge_base(self):
        """初始化向量知识库，导入现有知识库中的所有文档"""
        try:
            # 获取所有文档
            documents = self.knowledge_base.get_all_documents()
            
            # 导入到向量知识库，使用语义分块处理长文档
            for doc_id, doc in documents.items():
                # 对长文档进行分块
                chunks = self._create_semantic_chunks(doc['content'])
                
                # 为每个分块创建一个文档
                for i, chunk in enumerate(chunks):
                    vector_doc = {
                        'id': f"{doc_id}_chunk_{i}",
                        'parent_id': doc_id,
                        'title': doc['title'],
                        'content': chunk
                    }
                    self.vector_knowledge_base.add_document(vector_doc)
                
            logger.info(f"已将{len(documents)}篇文档导入向量知识库")
        except Exception as e:
            logger.exception(f"初始化向量知识库时出错: {str(e)}")
    
    def _create_semantic_chunks(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """
        将长文档内容分割成语义连贯的块
        
        Args:
            content: 文档内容
            max_chunk_size: 每个块的最大字符数
            
        Returns:
            分块后的内容列表
        """
        # 如果内容较短，直接返回
        if len(content) <= max_chunk_size:
            return [content]
        
        # 按段落拆分
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # 如果当前段落加上已有内容不超过最大块大小，则添加到当前块
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # 如果当前块非空，添加到结果中
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 开始新的块
                # 如果单个段落超过最大块大小，则需要进一步分割
                if len(para) > max_chunk_size:
                    # 按句子分割
                    sentences = para.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                            if current_chunk:
                                current_chunk += " " + sentence
                            else:
                                current_chunk = sentence
                        else:
                            chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def answer_question(self, query: str, provider: str = "deepseek") -> Dict[str, Any]:
        """
        使用RAG回答问题
        
        Args:
            query: 用户查询
            provider: AI提供商
            
        Returns:
            包含答案和来源的字典
        """
        try:
            logger.info(f"RAG问答请求: 提供商={provider}, 查询={query[:50]}...")
            
            # 检查缓存
            cache_key = self._generate_cache_key(query, provider)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.info(f"从缓存中获取回答: {query[:30]}...")
                return cached_response
            
            # 1. 从知识库中检索相关文档
            relevant_docs = self._retrieve_relevant_documents(query)
            logger.info(f"检索到{len(relevant_docs)}篇相关文档")
            
            # 2. 生成系统提示，包含检索到的文档
            system_prompt = self._generate_system_prompt(relevant_docs)
            
            # 3. 生成答案
            answer, sources = self._generate_answer(query, system_prompt, provider)
            
            # 构造响应
            response = {
                "success": True,
                "data": {
                    "answer": answer,
                    "sources": sources,
                    "model": f"RAG+{provider}",
                    "retrieved_docs": len(relevant_docs)
                }
            }
            
            # 添加到缓存
            self._add_to_cache(cache_key, response)
            
            logger.info(f"RAG问答完成: 使用{len(relevant_docs)}篇文档，模型={provider}")
            return response
        except Exception as e:
            logger.exception(f"使用RAG回答问题时出错: {str(e)}")
            return {
                "success": False,
                "message": f"处理请求时出错: {str(e)}"
            }
    
    def _generate_cache_key(self, query: str, provider: str) -> str:
        """生成缓存键"""
        key_str = f"{query.lower().strip()}:{provider}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取响应"""
        return self.query_cache.get(cache_key)
    
    def _add_to_cache(self, cache_key: str, response: Dict):
        """添加响应到缓存"""
        # 如果缓存已满，移除最旧的项
        if len(self.query_cache) >= self.cache_size:
            # 简单实现：直接清除一半的缓存
            keys = list(self.query_cache.keys())
            for key in keys[:len(keys)//2]:
                del self.query_cache[key]
        
        self.query_cache[cache_key] = response
    
    def _retrieve_relevant_documents(self, query: str) -> List[Dict]:
        """
        从知识库中检索相关文档 - 使用混合检索策略
        
        Args:
            query: 用户查询
            
        Returns:
            相关文档列表
        """
        results = []
        
        # 1. 首先尝试向量检索（延迟初始化）
        try:
            self._ensure_vector_kb_initialized()
            vector_results = self.vector_knowledge_base.search_documents(query, top_k=5)
            if vector_results:
                logger.info(f"向量检索成功，找到{len(vector_results)}篇相关文档")
                # 添加到结果，并记录检索方法
                for doc in vector_results:
                    doc['retrieval_method'] = 'vector'
                results.extend(vector_results)
        except Exception as e:
            logger.warning(f"向量检索失败: {str(e)}")
        
        # 2. 然后使用关键词检索
        try:
            keyword_results = self.knowledge_base.search_documents(query)
            if keyword_results:
                logger.info(f"关键词检索成功，找到{len(keyword_results)}篇相关文档")
                # 过滤掉已经通过向量检索找到的文档
                existing_ids = {doc.get('parent_id', doc['id']) for doc in results}
                filtered_results = []
                
                for doc in keyword_results:
                    if doc['id'] not in existing_ids:
                        doc['retrieval_method'] = 'keyword'
                        filtered_results.append(doc)
                
                # 合并结果
                results.extend(filtered_results)
        except Exception as e:
            logger.warning(f"关键词检索失败: {str(e)}")
        
        # 对结果进行去重和评分排序
        if results:
            # 去重（可能有重复的文档）
            unique_results = {}
            for doc in results:
                doc_id = doc.get('parent_id', doc['id'])
                
                # 如果是新文档或评分更高，则更新
                if (doc_id not in unique_results or 
                    doc.get('similarity', 0) > unique_results[doc_id].get('similarity', 0)):
                    unique_results[doc_id] = doc
            
            # 转回列表并按相似度排序
            results = list(unique_results.values())
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            # 限制返回数量
            results = results[:5]
        
        return results
    
    def _generate_system_prompt(self, relevant_docs: List[Dict]) -> str:
        """
        生成系统提示
        
        Args:
            relevant_docs: 相关文档列表
            
        Returns:
            系统提示
        """
        if not relevant_docs:
            return """你是一个助手。回答以下问题，如果不知道答案，请详细说明并提供学习建议。

请用中文回答，要准确、详细、全面。即使没有找到相关信息，也要提供：
1. 对问题的理解和分析
2. 可能的解决方向和建议
3. 相关的学习资源推荐
4. 进一步探索的方法

回答应该具有教学性质，帮助用户深入理解相关内容。"""
        
        context_parts = []
        for i, doc in enumerate(relevant_docs):
            # 加入检索方法信息，帮助调试
            retrieval_info = f"[通过{doc.get('retrieval_method', '未知')}检索]" if 'retrieval_method' in doc else ""
            context_parts.append(f"文档{i+1}{retrieval_info}: {doc['title']}\n{doc['content']}")
        
        context = "\n\n".join(context_parts)
        
        return f"""你是一个助手。回答以下问题，仅使用提供的文档内容。如果文档中没有相关信息，请说'我没有找到相关信息'。不要编造信息。

相关文档:
{context}

请用中文回答，要准确、详细、全面。请提供完整的解释和具体的步骤，包括：
1. 详细的概念解释
2. 具体的实施步骤或方法
3. 相关的技术细节
4. 实际应用场景或示例
5. 注意事项或最佳实践

回答应该具有教学性质，帮助用户深入理解相关内容。回答时，引用使用的文档编号。例如：根据文档1，..."""
    
    def _generate_answer(self, query: str, system_prompt: str, provider: str) -> tuple:
        """
        生成答案
        
        Args:
            query: 用户查询
            system_prompt: 系统提示
            provider: AI提供商
            
        Returns:
            (答案, 来源列表)
        """
        # 尝试使用实际的LLM API
        if provider == "deepseek" and self.has_deepseek:
            return self._call_deepseek_api(query, system_prompt)
        elif provider == "openai" and self.has_openai:
            return self._call_openai_api(query, system_prompt)
        elif provider == "ollama":
            return self._call_ollama_api(query, system_prompt)
        
        # 如果没有配置API或发生错误，回退到模拟回答
        logger.warning(f"使用模拟回答，提供商: {provider}")
        return self._mock_generate_answer(query, system_prompt)
    
    def _call_deepseek_api(self, query: str, system_prompt: str) -> tuple:
        """调用DeepSeek API生成回答"""
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                }
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2500  # 临时减少以提高响应速度
                }
                
                response = requests.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=60,  # 增加超时时间到60秒
                    stream=True  # 启用流式传输
                )
                
                if response.status_code != 200:
                    logger.error(f"DeepSeek API请求失败: {response.status_code} {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return self._mock_generate_answer(query, system_prompt)
                
                # 读取完整的响应内容
                full_response = ""
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        full_response += chunk
                
                try:
                    result = json.loads(full_response)
                    answer = result['choices'][0]['message']['content']
                    
                    # 从答案中提取引用的文档
                    sources = self._extract_sources_from_answer(answer, system_prompt)
                    
                    return answer, sources
                except json.JSONDecodeError as e:
                    logger.error(f"解析DeepSeek API响应失败: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return self._mock_generate_answer(query, system_prompt)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"DeepSeek API请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return self._mock_generate_answer(query, system_prompt)
            except Exception as e:
                logger.exception(f"调用DeepSeek API时出错: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return self._mock_generate_answer(query, system_prompt)
        
        return self._mock_generate_answer(query, system_prompt)
    
    def _call_openai_api(self, query: str, system_prompt: str) -> tuple:
        """调用OpenAI API生成回答"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.3,
                "max_tokens": 2500  # 临时减少以提高响应速度
            }
            
            response = requests.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=60  # 增加超时时间到60秒
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API请求失败: {response.status_code} {response.text}")
                return self._mock_generate_answer(query, system_prompt)
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            # 从答案中提取引用的文档
            sources = self._extract_sources_from_answer(answer, system_prompt)
            
            return answer, sources
        except Exception as e:
            logger.exception(f"调用OpenAI API时出错: {str(e)}")
            return self._mock_generate_answer(query, system_prompt)
    
    def _call_ollama_api(self, query: str, system_prompt: str) -> tuple:
        """调用本地Ollama API生成回答"""
        try:
            payload = {
                "model": "llama3",  # 可根据实际配置调整
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2500  # 临时减少以提高响应速度
                }
            }
            
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=60  # Ollama可能需要更长的超时时间
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API请求失败: {response.status_code} {response.text}")
                return self._mock_generate_answer(query, system_prompt)
            
            result = response.json()
            answer = result['message']['content']
            
            # 从答案中提取引用的文档
            sources = self._extract_sources_from_answer(answer, system_prompt)
            
            return answer, sources
        except Exception as e:
            logger.exception(f"调用Ollama API时出错: {str(e)}")
            return self._mock_generate_answer(query, system_prompt)
    
    def _extract_sources_from_answer(self, answer: str, system_prompt: str) -> List[Dict]:
        """从答案中提取引用的文档"""
        sources = []
        
        # 如果没有相关文档
        if "相关文档" not in system_prompt:
            return sources
        
        # 提取文档引用
        # 例如: "根据文档1..."
        import re
        doc_refs = re.findall(r'文档(\d+)', answer)
        
        # 从系统提示中提取文档信息
        doc_pattern = re.compile(r'文档(\d+)(?:\[.*?\])?: (.*?)\n', re.DOTALL)
        docs_in_prompt = doc_pattern.findall(system_prompt)
        
        # 构建文档ID映射
        doc_map = {}
        for num, title in docs_in_prompt:
            doc_map[num] = {"title": title.strip(), "id": f"doc{num}"}
        
        # 添加引用的文档到来源
        for ref in doc_refs:
            if ref in doc_map and not any(s['id'] == doc_map[ref]['id'] for s in sources):
                sources.append(doc_map[ref])
        
        return sources
    
    def _mock_generate_answer(self, query: str, system_prompt: str) -> tuple:
        """
        模拟生成答案
        
        Args:
            query: 用户查询
            system_prompt: 系统提示
            
        Returns:
            (答案, 来源列表)
        """
        # 模拟处理延迟
        time.sleep(random.uniform(1.0, 2.0))
        
        # 如果没有相关文档（检测系统提示）
        if "相关文档" not in system_prompt:
            return """我没有找到与您问题相关的具体信息，但我可以为您提供一些通用的指导：

### 问题分析
您的问题可能涉及到特定的技术领域或概念。虽然当前知识库中没有直接相关的文档，但这并不意味着问题无法解决。

### 建议的解决方向
1. **明确问题范围**：尝试将问题表达得更具体和详细
2. **关键词优化**：使用更准确的技术术语或概念名称
3. **分解复杂问题**：将复杂问题拆分成多个简单的子问题
4. **提供上下文**：说明您的具体使用场景和目标

### 学习资源推荐
- **官方文档**：查阅相关技术的官方文档和API参考
- **技术社区**：在Stack Overflow、GitHub、CSDN等平台寻求帮助
- **在线教程**：寻找相关的视频教程、博客文章或在线课程
- **技术书籍**：阅读权威的技术书籍和实战指南

### 进一步探索方法
- **实验验证**：通过小规模实验来验证您的想法
- **同行交流**：与有经验的同事或朋友讨论
- **持续学习**：关注相关技术的最新发展和最佳实践

如果您能提供更多的背景信息或具体的技术细节，我将能够为您提供更有针对性的帮助。""", []
        
        # 简单的关键词匹配，针对RAG进行的模拟回答
        keywords = {
            "rag": """根据文档1，RAG（检索增强生成）是一种将信息检索系统与生成式AI模型结合的混合架构技术。

### 详细概念解释
RAG技术通过先检索相关文档，然后将这些文档作为上下文提供给大型语言模型，从而生成更准确、更可靠的回答。这种方法解决了传统生成模型可能产生幻觉或过时信息的问题。

### 具体实施步骤
1. **文档预处理**：将知识库中的文档进行分块和向量化
2. **查询处理**：将用户查询转换为向量表示
3. **相似度检索**：计算查询向量与文档向量的相似度，检索最相关的文档
4. **上下文构建**：将检索到的文档组织成结构化的上下文
5. **生成回答**：将上下文和查询一起输入到大型语言模型中生成回答

### 技术细节
- 使用sentence-transformers进行文本向量化
- 采用FAISS进行高效的向量相似度搜索
- 支持多种检索策略（向量检索、关键词检索、混合检索）
- 集成多种LLM（DeepSeek、OpenAI、Ollama）

### 实际应用场景
- 企业知识库问答系统
- 技术文档智能检索
- 客户服务自动化
- 学术研究辅助工具

### 注意事项
- 需要高质量的知识库内容
- 向量模型的选择影响检索效果
- 需要合理设置检索参数以平衡准确性和召回率""",
            "知识库": """根据文档2，知识库是一个结构化的信息存储系统，用于保存和管理实验室的技术知识。

### 详细概念解释
在RAG架构中，知识库是检索阶段的关键组件，它存储了所有可供检索的文档和信息。知识库的质量直接影响RAG系统的回答质量。

### 具体实施步骤
1. **数据收集**：收集相关的技术文档、论文、手册等
2. **数据清洗**：去除无关信息，统一格式
3. **文档分块**：将长文档分割成合适大小的块
4. **索引构建**：为文档创建向量索引和关键词索引
5. **定期更新**：保持知识库内容的时效性

### 技术细节
- 支持多种文档格式（PDF、Word、Markdown等）
- 使用语义分块技术保持内容连贯性
- 建立文档元数据管理系统
- 实现增量更新机制

### 实际应用场景
- 实验室技术文档管理
- 项目知识积累
- 团队经验共享
- 新员工培训资料

### 最佳实践
- 定期审核和更新内容
- 建立文档质量标准
- 实施版本控制
- 设置访问权限管理""",
            "向量": """根据文档1和文档3，在RAG系统中，向量表示（或嵌入）是将文本转换为数字向量的过程。

### 详细概念解释
向量表示使得系统可以计算文本之间的语义相似度，这是检索阶段的基础技术。通过将文本映射到高维向量空间，相似的文本在向量空间中距离较近。

### 具体实施步骤
1. **模型选择**：选择合适的预训练向量模型
2. **文本预处理**：清洗和标准化文本内容
3. **向量生成**：使用模型将文本转换为向量
4. **向量存储**：将向量存储在向量数据库中
5. **相似度计算**：使用余弦相似度等方法计算向量间距离

### 技术细节
- 使用paraphrase-multilingual-MiniLM-L12-v2模型
- 向量维度为384维
- 支持中英文混合文本
- 使用FAISS进行高效向量搜索

### 实际应用场景
- 语义搜索
- 文档聚类
- 相似文档推荐
- 内容去重

### 注意事项
- 向量模型的选择影响检索质量
- 需要考虑计算资源和存储成本
- 定期评估向量质量
- 处理多语言文本时需要选择合适的模型""",
            "检索": """根据文档1，检索是RAG系统的第一个阶段，它负责从知识库中找出与用户查询最相关的文档或文档片段。

### 详细概念解释
检索阶段的目标是快速准确地找到与用户查询相关的信息。系统采用多种检索策略来提高检索的准确性和召回率。

### 具体实施步骤
1. **查询分析**：理解用户查询的意图和关键信息
2. **向量检索**：使用向量相似度进行语义检索
3. **关键词检索**：使用传统的关键词匹配
4. **混合检索**：结合多种检索方法
5. **结果排序**：根据相关性对检索结果进行排序

### 技术细节
- 支持向量相似度搜索和稀疏检索
- 实现混合检索策略
- 使用缓存机制提高检索效率
- 支持多语言查询处理

### 实际应用场景
- 智能问答系统
- 文档搜索引擎
- 知识发现
- 信息推荐

### 最佳实践
- 合理设置检索参数
- 定期评估检索效果
- 优化查询预处理
- 实施结果去重和过滤""",
            "生成": """根据文档1，生成是RAG系统的第二个阶段，它使用大型语言模型基于检索到的相关上下文生成回答。

### 详细概念解释
生成阶段将检索到的文档作为上下文，结合用户查询，使用大型语言模型生成准确、相关的回答。这个过程确保了回答的准确性和可靠性。

### 具体实施步骤
1. **上下文构建**：将检索到的文档组织成结构化的上下文
2. **提示工程**：设计合适的系统提示
3. **模型调用**：调用大型语言模型API
4. **回答生成**：基于上下文和查询生成回答
5. **后处理**：对生成的回答进行格式化和验证

### 技术细节
- 支持多种LLM（DeepSeek、OpenAI、Ollama）
- 实现流式响应处理
- 设置合理的温度参数控制创造性
- 限制最大token数量避免过长回答

### 实际应用场景
- 智能客服
- 技术支持
- 教育辅导
- 内容创作辅助

### 注意事项
- 需要设计合适的提示模板
- 控制生成内容的准确性
- 处理API调用失败的情况
- 监控生成质量和成本"""
        }
        
        # 检查查询中是否包含关键词
        matched_keywords = [k for k in keywords if k in query.lower()]
        
        if matched_keywords:
            # 使用匹配到的第一个关键词的回答
            answer = keywords[matched_keywords[0]]
            # 模拟来源
            sources = [{"title": f"关于{matched_keywords[0]}的技术文档", "id": "doc1"}]
        else:
            # 通用回答
            answer = """根据相关文档，您的问题涉及到实验室知识管理系统的功能。

### 系统概述
本系统使用混合AI架构，结合了检索增强生成（RAG）技术，能够基于实验室的知识库提供准确的回答。

### 主要功能特性
1. **智能问答**：基于RAG技术的智能问答系统
2. **知识管理**：结构化的技术文档管理
3. **多模型支持**：集成DeepSeek、OpenAI、Ollama等多种AI模型
4. **混合检索**：结合向量检索和关键词检索
5. **实时更新**：支持知识库的动态更新

### 技术架构
- **前端**：Vue 3 + Element Plus
- **后端**：Flask + Python
- **向量数据库**：FAISS
- **AI模型**：多种大型语言模型
- **检索技术**：sentence-transformers

### 使用场景
- 技术问题咨询
- 项目经验查询
- 学习资料检索
- 团队知识共享

### 使用建议
如果您有更具体的问题，比如关于RAG技术、知识库管理、向量检索等方面，我可以提供更详细的技术信息和实施指导。"""
            sources = [{"title": "实验室知识管理系统概述", "id": "doc1"}]
        
        return answer, sources

# 创建RAG服务实例
rag_service = RAGService()