# 实验室知识管理系统
## 基于混合AI架构的智能知识管理平台

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![语言](https://img.shields.io/badge/语言-Python%20%7C%20JavaScript-yellow)
![框架](https://img.shields.io/badge/框架-Flask%20%7C%20Vue%203-green)
![许可证](https://img.shields.io/badge/许可证-MIT-red)

## 项目概述

本项目旨在为科研实验室开发一套基于混合AI架构的智能知识管理系统，主要包括以下模块：

1. 🧠 **智能知识问答**：基于混合AI架构的智能化问答系统，支持多种AI服务提供商
2. 📚 **实验室技术总结**：供实验室成员发布技术总结和经验分享，促进技术交流
3. 🏆 **实验室成果展示**：展示实验室的科研成果，便于查看和管理
4. 📋 **实验室项目管理**：帮助管理科研项目进度，任务分配和进度更新
5. 👥 **实验室人员管理**：管理实验室成员信息，配置角色与权限
6. 📅 **实验室会议管理**：记录会议内容，管理会议安排和议题讨论

## 混合AI架构特色

本系统采用创新的混合AI架构设计，具有以下特点：

### 1. 多源AI服务支持
- **外部API集成**
  - 支持OpenAI API (GPT-3.5/GPT-4)
  - 支持DeepSeek API
  - 统一的API接口封装层

- **本地化部署**
  - 基于Ollama框架的本地LLM部署
  - 支持通义千问等开源模型的本地运行
  - 自定义知识库构建

### 2. 智能服务切换机制
- 服务可用性自动检测
- 故障自动转移
- 基于性能的智能路由
- 平滑的服务切换体验

### 3. 知识库管理
- 结构化和非结构化数据整合
- 自动文本摘要和标签推荐
- 向量化存储和相似度检索
- 知识关联分析

## 项目结构

```
.
├── backend/                # 后端应用
│   ├── app/               # Flask应用
│   │   ├── api/          # API接口
│   │   ├── models/       # 数据模型
│   │   ├── utils/        # 工具类
│   │   │   ├── chat_with_doc.py  # 文档问答工具
│   │   │   └── knowledge_base.py # 知识库管理
│   │   └── ...
│   ├── migrations/        # 数据库迁移文件
│   ├── config.py          # 配置文件
│   ├── run.py             # 应用入口
│   └── requirements.txt   # Python依赖
│
├── frontend/              # 前端应用
│   ├── src/              # 源代码
│   │   ├── components/   # 组件
│   │   │   ├── DocumentChat.vue  # 文档问答组件
│   │   │   └── ...
│   │   ├── views/        # 页面
│   │   ├── router/       # 路由
│   │   ├── stores/       # 状态管理
│   │   └── ...
│   ├── public/           # 静态资源
│   └── ...
│
└── README.md              # 项目说明
```

## 核心功能说明

### 智能问答系统

基于混合AI架构的问答系统具有以下特点：

1. **多模型支持**：同时支持多种AI模型，包括OpenAI、DeepSeek和本地Ollama模型
2. **自动切换**：根据服务可用性和响应时间自动切换最优服务
3. **统一接口**：为所有AI服务提供统一的接口，简化集成
4. **上下文保持**：保持对话上下文，提供连贯的交互体验
5. **知识库增强**：结合实验室知识库，提供更精准的答案

### 技术实现示例

```python
class AIService:
    def __init__(self):
        self.providers = {
            'openai': OpenAIService(),
            'deepseek': DeepSeekService(),
            'ollama': OllamaService()
        }
    
    async def get_response(self, query: str, provider: str = None):
        # 指定服务提供商直接调用
        if provider and provider in self.providers:
            return await self.providers[provider].chat(query)
        
        # 智能选择最佳服务
        return await self._get_best_response(query)
    
    async def _get_best_response(self, query: str):
        # 检查服务可用性并选择最佳服务
        available_providers = await self._check_availability()
        if not available_providers:
            return {"error": "所有AI服务当前不可用"}
        
        # 根据历史响应时间选择最佳服务
        best_provider = self._select_best_provider(available_providers)
        return await self.providers[best_provider].chat(query)
```

## 快速开始

### 后端启动

1. 进入后端目录
```bash
cd backend
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 初始化数据库（如果尚未初始化）
```bash
flask db upgrade
```

5. 运行开发服务器
```bash
python run.py
```

### 前端启动

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 运行开发服务器
```bash
npm run dev
```

### 本地AI服务配置（可选）

1. 安装Ollama
```bash
# MacOS/Linux
curl -fsSL https://ollama.com/install.sh | sh
# 或通过其他平台的安装方式
```

2. 下载所需模型
```bash
ollama pull qwen:7b
# 或其他支持的模型
```

3. 配置后端环境变量
```
# .env文件
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_LOCAL_LLM=true
```

## 功能特点

- 🧠 混合AI架构，支持多种AI服务
- 🔄 智能服务切换机制
- 📚 知识库管理与检索
- 🔐 用户认证与授权
- 📊 成果管理
- 💡 技术总结
- 📋 项目管理
- 👥 人员管理
- 📅 会议管理

## 技术栈

### 后端
- Flask (Web框架)
- SQLAlchemy (ORM)
- Flask-JWT-Extended (身份验证)
- Flask-Login (用户管理)
- Flask-Migrate (数据库迁移)
- Flask-CORS (跨域支持)
- OpenAI API (外部AI服务)
- DeepSeek API (外部AI服务)
- Ollama (本地AI部署)

### 前端
- Vue 3 (框架)
- Vite (构建工具)
- Element Plus (UI组件库)
- Pinia (状态管理)
- Vue Router (路由)
- Axios (HTTP客户端)
- Markdown-it (Markdown渲染)

## 前后端分离架构

本项目采用前后端分离的架构设计，具有以下特点：

### 架构概述
- **后端**：提供RESTful API，负责数据处理、业务逻辑和安全认证
- **前端**：独立部署的单页应用(SPA)，负责用户界面和交互逻辑
- **通信**：通过HTTP/HTTPS协议，使用JSON格式数据交换
- **AI服务层**：包含混合AI架构，支持多种AI服务提供商

### 前后端通信
- 采用RESTful API设计规范
- 使用JWT（JSON Web Token）进行身份验证
- 支持Token刷新机制，提高安全性
- 使用Axios进行HTTP请求，处理拦截和错误

### 开发流程
1. 后端开发API接口并提供文档
2. 前端根据API文档开发界面和功能
3. 前后端并行开发，通过API契约保持一致性
4. 集成测试确保前后端正常通信

### 部署策略
- 前端可独立部署在静态文件服务器或CDN
- 后端部署在应用服务器，可水平扩展
- 本地AI服务独立部署，提供API接口
- 可选择同域或跨域部署，跨域时需配置CORS

### 优势
- 关注点分离，前后端团队可并行开发
- 前端可提供更丰富的用户体验
- 后端可服务多种客户端（Web、移动应用等）
- 混合AI架构提供更高的服务可用性和灵活性
- 更好的可扩展性和可维护性

## API文档

### 认证接口
- POST `/api/v1/auth/login` - 用户登录
- POST `/api/v1/auth/register` - 用户注册
- POST `/api/v1/auth/refresh` - 刷新token
- GET `/api/v1/auth/user` - 获取当前用户信息
- POST `/api/v1/auth/logout` - 用户登出

### 成果接口
- GET `/api/v1/achievements` - 获取成果列表
- GET `/api/v1/achievements/<id>` - 获取成果详情
- POST `/api/v1/achievements` - 创建新成果
- PUT `/api/v1/achievements/<id>` - 更新成果
- DELETE `/api/v1/achievements/<id>` - 删除成果

### 技术总结接口
- GET `/api/v1/tech_summaries` - 获取技术总结列表
- GET `/api/v1/tech_summaries/<id>` - 获取技术总结详情
- POST `/api/v1/tech_summaries` - 创建技术总结
- PUT `/api/v1/tech_summaries/<id>` - 更新技术总结
- DELETE `/api/v1/tech_summaries/<id>` - 删除技术总结
- POST `/api/v1/tech_summaries/<id>/chat` - 基于技术总结内容的智能问答

### AI服务接口
- POST `/api/v1/ai/chat` - 智能问答服务
- GET `/api/v1/ai/providers` - 获取可用的AI服务提供商
- POST `/api/v1/ai/switch_provider` - 切换AI服务提供商
- GET `/api/v1/ai/status` - 获取AI服务状态

## 系统截图

![系统截图](https://via.placeholder.com/800x400?text=知识管理系统截图)

## 未来规划

- [ ] 添加更多AI服务提供商支持
- [ ] 实现知识图谱可视化
- [ ] 添加协作编辑功能
- [ ] 优化本地模型性能
- [ ] 实现移动端应用
- [ ] 添加科研趋势分析功能

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

项目维护者 - [@yourgithub](https://github.com/yourgithub)

项目链接: [https://github.com/yourusername/your-repo-name](https://github.com/yourusername/your-repo-name)