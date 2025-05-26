# API超时配置说明

## 问题描述

知识库问答普通模式出现超时问题，主要表现为：
- 连接到 `api.deepseek.com` 时发生读取超时
- 错误信息：`requests.exceptions.ConnectionError: HTTPSConnectionPool(host='api.deepseek.com', port=443): Read timed out.`

## 已实施的优化

### 1. 超时配置优化
- **连接超时**：10秒（可通过环境变量 `API_CONNECT_TIMEOUT` 配置）
- **读取超时**：90秒（可通过环境变量 `API_READ_TIMEOUT` 配置）
- **最大重试次数**：3次（可通过环境变量 `API_MAX_RETRIES` 配置）

### 2. 重试机制改进
- 递增延迟策略：2秒、4秒、6秒
- 分别处理超时和连接错误
- 详细的错误日志记录

### 3. 网络连接优化
- 使用连接池复用连接
- 添加 `Connection: close` 头部避免连接复用问题
- 配置HTTP适配器和重试策略
- 确保SSL验证

### 4. 响应优化
- 减少 `max_tokens` 到1500以提高响应速度
- 禁用流式响应（`stream: false`）
- 降低温度参数到0.3

## 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# DeepSeek API配置
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# OpenAI API配置
OPENAI_API_URL=https://api.openai.com/v1/chat/completions
OPENAI_API_KEY=your_openai_api_key_here

# API超时配置（秒）
API_CONNECT_TIMEOUT=10
API_READ_TIMEOUT=90
API_MAX_RETRIES=3

# 是否优先使用后备方案（true/false）
USE_FALLBACK_FIRST=false
```

## 故障排除

### 1. 如果仍然超时
- 增加 `API_READ_TIMEOUT` 到120秒或更高
- 检查网络连接稳定性
- 考虑使用代理服务器

### 2. 如果API密钥无效
- 检查 `DEEPSEEK_API_KEY` 是否正确设置
- 验证API密钥是否有效且有足够余额

### 3. 如果需要更快响应
- 设置 `USE_FALLBACK_FIRST=true` 优先使用本地后备方案
- 减少 `max_tokens` 参数
- 使用更快的模型

### 4. 如果遇到urllib3版本问题
如果启动时出现 `TypeError: Retry.__init__() got an unexpected keyword argument 'method_whitelist'` 错误：

- 这是因为urllib3版本差异导致的
- 新版本使用 `allowed_methods` 参数
- 旧版本使用 `method_whitelist` 参数
- 当前代码已适配新版本，如需支持旧版本请更新urllib3：

```bash
pip install --upgrade urllib3
```

## 监控和日志

系统会记录详细的API调用日志：
- 每次API调用的尝试次数
- 具体的错误信息和响应状态
- 成功调用的确认信息

查看日志以诊断问题：
```bash
tail -f backend/logs/app.log
```

## 后备方案

如果API调用失败，系统会自动使用基于关键词匹配的后备方案：
- 在文档中搜索相关关键词
- 提供基于文档内容的回答
- 给出学习建议和指导

这确保了即使在网络问题或API服务不可用时，用户仍能获得有用的回答。 