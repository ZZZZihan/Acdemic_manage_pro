# 审计与 RAG Agent 路线图

日期：2026-11-04。对象：当前 `main`（`97af286`）上的 Flask + Vue 3 实验室知识管理系统。

这是一次只读审计。结论来自阅读源码、核对 git 跟踪内容，以及在本环境实际安装和发请求。README、`backend/README_RAG.md` 里的架构图和示例类没有当作事实。

本文件只记录发现和建议。密钥、调试器 PIN、用户邮箱不写入本文。

## 1. 先看结论

实验室业务接口在补齐运行环境后能工作。技术总结、成果、项目、会议、注册登录背后是真实的 SQLAlchemy 模型和一份有数据的 SQLite。`GET /api/v1/tech_summaries` 返回 12 篇总结，`GET /api/v1/achievements` 与 `GET /api/v1/projects` 也能返回数据。

README 描述的「混合 AI 架构」超前于代码。没有统一的供应商路由器，没有按可用性或延迟自动切换，也没有接入中国人民大学的 FlashRAG 库。接到 `POST /api/v1/rag/chat` 的是自写类 `FlashRAGService`：进程启动时加载 `paraphrase-multilingual-MiniLM-L12-v2`，用内存里的 FAISS `IndexFlatL2` 做向量检索，再把命中片段塞进一次聊天补全。另一套写了混合检索和模拟回答的 `RAGService` 没有任何路由引用。

当前这次 RAG 调用检索不到任何文档。`backend/app/knowledge_base.json` 留着未解决的 git 合并冲突，JSON 解析失败后内存知识库是空的。接口因此回答「知识库中没有找到相关信息，且 DeepSeek API 密钥未设置」。关掉前端 RAG 开关后，另一条关键词路径会以 `success: true` 返回一段与文档无关的学习建议，提供商标成 `fallback_deepseek`。

离一个能演示、能写进简历的 RAG Agent 还差四件事：仓库能被别人干净地装起来；语料、索引和数据库是同一份数据；回答带可核对的引用，并用评测集衡量；在此之上再做工具调用和多轮记忆。建议按文末 P0 → P3 做，不要先加 Agent 循环。

## 2. 审计怎么做的

| 项 | 实际情况 |
| --- | --- |
| 默认解释器 | Python 3.12.3、Node.js 22.23.4 |
| 文档指定的后端运行时 | `backend/Dockerfile` 使用 `python:3.10-slim` |
| 对照运行时 | 另装 CPython 3.10.22，用独立虚拟环境安装依赖，不改仓库文件 |
| 后端 | 先按 `requirements.txt` 安装，再补缺失导入、钉住兼容的 `huggingface_hub`，启动 `python run.py`（监听 5003），对主要接口发请求 |
| 前端 | 仓库里已提交的 `node_modules` 直接跑 Vite 失败；在副本目录执行 `npm ci` 后，Vite 4.5.9 能提供页面壳 |
| 未覆盖 | 没有配置真实的 OpenAI / DeepSeek / Ollama，因此没有打到外部大模型。没有做登录后的浏览器点击走查 |

## 3. 文档说法和代码

| 文档说法 | 代码与运行结果 |
| --- | --- |
| 多供应商：OpenAI、DeepSeek、本地 Ollama，统一封装 | 四套各自拼 HTTP 的客户端：`llm_api.py`、`flashrag_service.py`、`rag_service.py`、`chat_with_doc.py`，外加 `ollama_chat.py`。模型名互相不一致：Ollama 聊天用 `qwen:7b-q4_0`，FlashRAG 用 `llama2`，`RAGService` 用 `llama3`，README 写 `qwen:7b` |
| `AIService` 按可用性与历史延迟选择供应商，故障自动转移 | 仓库里没有这个类，也没有 `/api/v1/ai/providers`、`/api/v1/ai/switch_provider`、`/api/v1/ai/status`。前端只是一个下拉框，把 `provider` 字段传给后端。`network_check.py` 只探测 DeepSeek 首页，没有被任何路由调用 |
| Flash RAG：SentenceTransformer + FAISS，自动索引、自动更新 | 类名借用了 FlashRAG 的说法，`requirements.txt` 没有 `flashrag` 包。嵌入模型和 FAISS 只在 `FlashRAGService` 里真正用于在线请求。新增技术总结只改 JSON，不更新已经建好的 FAISS。要重建得重启进程，或调用未鉴权的 `POST /api/v1/rag/init_flashrag` |
| 混合检索（向量 + 关键词）、语义分块、结果缓存、优雅降级 | 这些逻辑写在 `rag_service.py`，全仓库没有第二处 import。在线 RAG 只有向量检索。关键词检索是另一条接口。缓存是进程内字典。所谓降级会把模板文案当成成功回答 |
| `POST /api/v1/knowledge_base/query` | 不存在，返回 404。对应实现是 `POST /api/v1/knowledge_base/chat` |
| `POST /api/v1/ai/chat` | 存在，在 `tech_summaries.py`，不走知识库。无密钥时返回 HTTP 500 |
| 上下文保持、流式输出 | 前端自己堆聊天记录，请求体只有当前一句 `query`。`RAGService` 把 `stream=True` 的响应在服务器收完再一次性返回 JSON，浏览器看不到 token 流。这条类还没有被路由使用 |
| 引用信息来源 | FlashRAG 的 `sources` 只有 `title` 和文档 `id`，没有原文片段、偏移或 URL。聊天页只显示「来源: N 个」，不列出标题。非 RAG 路径的提示词写明「不需要引用文档编号」，响应里也没有 `sources` |
| 检索命中率、API 成功率、缓存命中率，日志在 `backend/logs/app.log` | 没有该目录，没有指标埋点，没有请求 ID |
| 向量库路径 `VECTOR_DB_PATH` | `.env.example` 写了这个变量，代码不读它 |
| Flask-Login 做用户管理 | 依赖列表里有，`LoginManager` 从未初始化。`decorators.py` 使用 `current_user.is_admin`，模型上的方法叫 `is_administrator()`，而且这两个装饰器没有被任何视图使用。实际鉴权是 JWT |
| 人员管理、角色权限 | 有 `Role` / `Permission` 和删除技术总结时的管理员判断。用户接口只有三个 GET。侧边栏「系统管理」指向 `/admin`，路由表没有这一项。`AdminTest.vue` 没有挂到路由上 |
| 首次启动自动初始化 Flash RAG，或 `curl` 一下 `init_flashrag` | 导入 `rag.py` 时就会构造 `FlashRAGService()`，模型加载失败则整个进程起不来。`DISABLE_VECTOR_MODEL` 只影响没被路由使用的 `VectorKnowledgeBase` |

## 4. 仓库里实际有什么

跟踪文件 10432 个。工作区约 136MB，`.git` 约 31MB。其中：

| 路径 | 跟踪文件数 | 说明 |
| --- | --- | --- |
| `frontend/node_modules` | 10211 | `.gitignore` 写了 `node_modules/`，但这些文件在忽略规则之前已经被跟踪，规则不会再把它们移出历史 |
| `frontend/dist` | 58 | 构建产物。`.gitignore` 没有忽略 `dist/`，`.dockerignore` 忽略了 |
| `backend/app/static/uploads` | 21 | 含 pptx、pdf、docx 和项目图片。最大的 pptx 约 9.7MB，另有约 2.5MB 的 pdf |
| `backend/data-dev.sqlite` | 1 | 160KB。7 个用户、12 篇技术总结、26 条成果、1 个项目、4 场会议、3 个角色 |
| `backend/instance/data-dev.sqlite` | 1 | 另一份库，表结构和上面那份对不上 |

`.gitignore` 忽略了 `venv/`、`*.pyc`、`.env`、`*.log`，没有忽略 `dist/`、`*.sqlite`、上传目录、`.env.backup`。因此开发库、上传文件和一份环境备份都在版本库里。

其他卫生问题：

- `backend/.env.backup` 被跟踪，里面有一个非占位的 DeepSeek 密钥。`.env.tmp` 是空文件，同样被跟踪。
- 死文件：`ollama_chat.py.bak`、`.clean`、`.new`、`.tmp`，`vector_knowledge_base.py.new`，以及嵌套目录 `backend/backend/`（又一份 mock 数据和测试）。
- 前端 `RagChat.vue` 只有「加载中...」，未注册路由。`OllamaKnowledgeChat.vue`、`AdminTest.vue`、`views/meetings/MeetingCreate.vue` 没有被引用。路由实际使用的是 `CreateMeeting.vue`。
- 没有 `.github` 工作流，没有 lint/test 门禁。
- 根目录 `tests/` 下四个 `test_*.py` 各 1 字节。`backend/tests/` 里多数用例是 `assertTrue(True)`。

两份 SQLite 也不能互相替代：

- `backend/data-dev.sqlite` 的 Alembic 版本是 `24318d21ae1d`。`tech_summaries.source_url` 列已经存在，而添加该列的迁移是更后面的 `23a8bb636e7e`。版本号和表结构不一致。
- `backend/instance/data-dev.sqlite` 记录的版本 `1189e8f4925e` 不在 `migrations/versions/` 里。它还有 `project_budgets`、`project_tasks`、`project_milestones` 等表，当前 `Project` 模型没有这些类。

上传的 pdf/docx/pptx 只是附件。解析入库的代码不存在，依赖里也没有 PDF 或 Office 解析库。

## 5. 安装和启动

### 5.1 后端

按 README 在 **Python 3.12** 上执行 `pip install -r requirements.txt` 失败。`numpy==1.23.5` 没有 cp312 轮子，源码构建报 `No module named 'distutils'`。加上 `--only-binary=:all:` 时，更早卡在 `SQLAlchemy==1.4.46`：该精确版本没有 cp312 轮子。

在 **Python 3.10.22**（与 Dockerfile 一致）上，同一份 `requirements.txt` 可以装完，包括 `torch==2.0.0`、`faiss-cpu==1.7.4`、`sentence-transformers==2.2.2`。这一步会拉下 CUDA 11 的 `nvidia-*` 包（cuDNN、cuBLAS 等，合计超过 1GB），不是 CPU 轮子。`python:3.10-slim` 镜像会因此变得很大，也更容易在构建时把磁盘或内存打满。

装完仍不能启动，按导入顺序会撞上：

1. `crawler.py` 在模块顶层 `import bs4`，`beautifulsoup4` 不在 `requirements.txt`。进程在注册技术总结路由时退出。
2. 补上 BeautifulSoup 之后，`llm_api.py` 顶层 `from openai import OpenAI`，`openai` 也不在依赖里。
3. 再补上当前的 `openai` 包，解析器会把钉死的 `pydantic==1.10.8` 升到 2.x。同时未钉死的 `huggingface_hub` 会被解析到 0.36，而 `sentence-transformers==2.2.2` 仍在调用已删除的 `cached_download`，导入直接失败。
4. 把 `huggingface_hub` 钉回 `0.16.4`、把 `pydantic` 装回 `1.10.8` 之后，进程可以起来：日志显示向量维度 384，FAISS 加载成功，随即报知识库 JSON 无法解析。调试模式的重载器会把模型再加载一遍。

也就是说，Dockerfile 的 Python 版本选得对，但锁文件锁不住传递依赖，缺两个被源码直接导入的包。本机默认的 3.12 则连第一步都过不去。

起来之后抽查的接口：

| 请求 | 结果 |
| --- | --- |
| `GET /api/v1/tech_summaries` | 200，`total: 12`，正文完整返回 |
| `GET /api/v1/achievements`、`GET /api/v1/projects` | 200，含创建者邮箱等字段 |
| `GET /api/v1/users` | 200，无需登录，返回邮箱 |
| `GET /api/v1/meetings` | 401，缺少 Authorization |
| `GET /api/v1/meetings/1` | 200，无需登录，返回组织者、参与者和邮箱 |
| `POST /api/v1/rag/chat`，问题「什么是RAG?」 | HTTP 200，正文 `success: false`：知识库无命中，且没有 DeepSeek 密钥 |
| `POST /api/v1/knowledge_base/chat`，同一问题 | HTTP 200，`success: true`，`provider: fallback_deepseek`，内容是通用学习建议 |
| `POST /api/v1/ai/chat` | HTTP 500，DeepSeek 调用失败 |
| `GET /api/v1/ai/providers`、`POST /api/v1/knowledge_base/query` | 404 |
| `POST /api/v1/rag/init_flashrag` | 200，`success: true`。空知识库也会报初始化成功，且不需要登录 |
| `GET /api/v1/files/download/<已跟踪的 txt>` | 200，无需登录，直接返回文件内容 |
| `POST /api/v1/ollama/chat` | HTTP 200，`success: false`，连接 `127.0.0.1:11434` 被拒绝。本环境没有 Ollama |

`run.py` 在找不到 `.env` 时会打印密钥是否存在（布尔值），然后用 `DevelopmentConfig` 启动。该类 `DEBUG = True`，Werkzeug 交互式调试器随之打开。

### 5.2 前端

在 Linux 上直接执行已提交的 `frontend/node_modules` 里的 Vite：`vite/dist/node/cli.js` 不存在。`esbuild` 二进制是 Mach-O arm64（`@esbuild/darwin-arm64`），不是 Linux 可执行文件。这是在 Mac Apple Silicon 上把 `node_modules` 提交进来的结果。

用 `package-lock.json` 在干净目录执行 `npm ci`（255 个包）后，Vite 4.5.9 约 228ms 就绪。`/`、`/auth/login`、`/knowledge_chat` 都返回 200，HTML 标题为「实验室知识管理系统」。这只说明外壳能被托管，没有在浏览器里登录、建数据或走完聊天。

`frontend/Dockerfile` 使用已经停止维护的 `node:16-alpine`，构建阶段会再跑一次 `npm install` 和 `npm run build`。本次没有做镜像构建。`@element-plus/icons-vue` 没有写进 `package.json`，但是 `element-plus` 的依赖，干净安装可以解析到。

`GlobalKnowledgeChat.vue` 默认打开 RAG，请求打到 `/api/v1/rag/chat`。页面挂载时还会 `POST /api/v1/knowledge_base/init`，该接口需要 JWT，未登录用户会得到 401，JSON 知识库不会从数据库重建。聊天组件把多轮消息留在浏览器里，发给服务器的仍然只有最后一句。

## 6. 代码质量和测试

能工作的部分是常规 CRUD：模型、迁移草稿、JWT 登录、技术总结的增删改，以及删除时区分作者和管理员。密码使用 Werkzeug `pbkdf2:sha256`，库里的哈希长度是 102，不是明文。

AI 相关代码是多轮拼接，而不是一条管线：

- `knowledge_base.py`：启动时读写 JSON。解析失败只把内存清空，不修文件。`search_documents` 要求整句查询作为子串出现，中文问句几乎匹配不到。
- `vector_knowledge_base.py`：余弦相似度，阈值 0.3；模型加载失败时退回关键词，仍无命中就随机抽文档并标一个 0.3–0.5 的相似度。单例构造时没有传入知识库文件，pickle 缓存分支不会走到。
- `rag_service.py`（约 760 行）：混合检索、进程内缓存、模拟长文回答。零引用。
- `flashrag_service.py`：在线路径。模块底部 `flashrag_service = FlashRAGService()`，导入即下载并加载模型，失败则抛 `RuntimeError`，Flask 起不来。
- `chat_with_doc.py`：单文档或全库关键词打分，把最多 3 篇**全文**塞进提示词。API 失败时用模板拼一段「回答」，并返回 `success: true`。
- `llm_api.py`：给「爬取 URL 再总结」用。标题提取里写死了 OpenCV、DeepSeek、Docker 等分支。

测试：在 Python 3.10 环境执行 `backend/tests` 下现有用例，6 个 `assertTrue(True)` 通过，`test_mock_data.py` 失败，因为 `from app.utils.mock_data import ...` 的模块不在 `backend/app/utils/`，而在没人使用的 `backend/backend/app/utils/mock_data.py`。没有任何测试启动应用、建索引或检查引用。

`backend/test_deepseek_api.py` 是手工脚本，不是测试套件的一部分。

## 7. 安全

按严重程度排列。本文不复述秘密。

1. **已入库的 API 密钥。** `backend/.env.backup` 在 git 历史中，`DEEPSEEK_API_KEY` 以 `sk-` 开头，长度符合常见密钥格式，不是 `your-deepseek-api-key` 这种占位符。应在 DeepSeek 控制台作废，并在后续清理历史。同文件里的 `SECRET_KEY`、`JWT_SECRET_KEY` 是短的开发字符串。
2. **JWT 可以伪造。** `config.py` 在环境变量缺失时使用固定的 `SECRET_KEY` 和 `JWT_SECRET_KEY`。访问令牌 8 小时，刷新令牌 30 天。`POST /api/v1/auth/logout` 只返回一句话，服务端不作废令牌。
3. **默认调试模式。** `run.py` 默认 `DevelopmentConfig`，`DEBUG = True`，调试器监听所有地址。生产配置没有单独关掉调试，是否开启取决于进程怎么启动。`docker-compose.yml` 设置了 `FLASK_CONFIG=production`，本地 `python run.py` 没有。
4. **未登录即可读的数据。** 用户列表、项目列表（含成员邮箱）、会议详情、成果列表、技术总结全文、上传文件下载，都不检查 JWT。会议列表反而检查了，同一资源的集合和详情策略不一致。开发库里有 7 个用户的邮箱和密码哈希，以及上传的办公文档，这些都跟着仓库公开。
5. **未登录即可调用模型相关接口。** `/api/v1/rag/chat`、`/api/v1/rag/init_flashrag`、`/api/v1/knowledge_base/chat`、`/api/v1/ai/chat`、`/api/v1/ollama/chat`、单篇技术总结的 `/chat` 都没有 `@jwt_required`。密钥一旦配上，这些接口就是公开的计费口，也没有频率限制。
6. **CORS。** `origins: "*"` 且 `supports_credentials=True`。浏览器对「凭证 + 通配源」的组合会直接拒绝，配置本身也表示没有源白名单。
7. **爬虫 SSRF。** `POST /api/v1/tech_summaries/crawl` 需要登录，但 `crawl_url` 接受任意带 scheme 和 host 的 URL，`requests.get` 默认跟随重定向。可以打到内网和云元数据地址。用户还可以传入 `custom_prompt`，原样进模型。
8. **前端把凭据打进控制台。** `stores/auth.js` 在登录时 `console.log` 整个凭据对象。Axios 拦截器打印请求 URL 和 token 是否存在。登录响应里的 `user` 没有 `role`，`isAdmin` 只看 `user.role === 'Administrator'`，除非另外调用 `/api/v1/auth/user`，管理员菜单不会出现。
9. **上传。** 允许 zip/rar 等类型，大小上限 10MB，保存名做了随机化。下载端用 `..` 做了简单拦截，但是未鉴权。

密码哈希算法本身没有问题。问题是哈希、邮箱和业务数据一起进了版本库，而且多个读接口不认登录状态。

## 8. 现在的 RAG 管线

在线路径可以写成：

```text
技术总结写入 SQLite
    → add_document() 把全文写入 knowledge_base.json
        → 进程启动时 FlashRAGService 读 JSON、按字符分块、编码、放进内存 FAISS
            → POST /api/v1/rag/chat 做 L2 近邻，拼一段 system prompt，调用所选供应商
```

今天第 2 步的文件是坏的，所以第 3 步建出一个空索引。SQLite 里的 12 篇总结不会自动流进 FAISS。

另外两条路径：

- 前端关掉 RAG 时调用 `/api/v1/knowledge_base/chat`，走关键词打分，不经过向量索引。
- `RAGService` + `VectorKnowledgeBase` 实现了文档里的混合检索，运行时不会执行。

### 8.1 摄入

语料只来自技术总结的 Markdown 正文。创建和更新时调用 `add_tech_summary_to_knowledge_base`，删除时 `remove_document`。成果、项目、会议、上传的 pdf/docx/pptx 都不进索引。

爬虫把 HTML 收成纯文本，再交给大模型写成笔记，用户保存后才进入上面的 JSON。没有版面分析，没有表格或扫描件处理。

`knowledge_base.json` 在第 143 行有 `<<<<<<< HEAD`。冲突两侧对同一 id 的正文不一致（一侧是 PyUSB 笔记，另一侧是 CS:APP 笔记，后面还有吴恩达课程笔记）。SQLite 里的 id 17 与 HEAD 一侧一致。文件一旦解析失败，内存文档数为 0，磁盘上的冲突原样保留。

`POST /api/v1/knowledge_base/init` 能按数据库重写 JSON，但需要登录，而且 FlashRAG 不会因为 JSON 被重写就更新索引。

### 8.2 分块

`_chunk_document` 按字符数打包段落，默认 512 字、参数名是 `overlap=50`。重叠只在「单句长于块大小」时使用，普通块之间没有重叠。句子切分看的是 `. `、`! `、`? `，中文的 `。` 不会切开。函数名叫语义分块，实现是长度打包。

`RAGService._create_semantic_chunks` 是另一套 1000 字的段落打包，同样不处理中文句号，而且没有被在线路径调用。

没有按标题层级切，没有保留 heading 路径，没有 token 计数。中文 512 字和英文 512 字符的信息量差一截，嵌入模型的输入长度也没有对齐。

### 8.3 嵌入

模型是 `paraphrase-multilingual-MiniLM-L12-v2`，本次启动日志确认维度 384。它是 2021 年前后的通用句向量，不是面向检索训练的模型，也没有 query/passage 指令前缀。

`SentenceTransformer.encode` 默认不归一化。FlashRAG 用裸 L2 距离排序。相似度又写成 `max(0, 1 - distance / 100)`，100 是写死的「最大距离」。这个分数不能当成概率，也不能和另一条路径里的余弦阈值 0.3 比较。

`VectorKnowledgeBase` 用的是余弦相似度，而且只在未接线的类里。

### 8.4 索引持久化

FAISS 索引只活在进程内存里。重启就重新编码全部块。没有把 index 写到磁盘，也没有用 `VECTOR_DB_PATH`。

`document_map` 用 Python 字典的插入顺序对应 FAISS 行号。`_init_index` 重建时新建了 `IndexFlatL2`，却不清空 `document_map`。文档集合一旦变化，行号和块 id 会错位。空索引调用该接口仍返回成功。

未接线的 `VectorKnowledgeBase` 可以把向量 pickle 到 `app/cache/`，但单例创建时没有知识库路径，在线代码也不会调用它。

### 8.5 检索

在线检索是「对空索引做 top-k L2」。无命中时 `rag_query` 丢掉供应商参数，改打 DeepSeek；没有密钥就失败。没有元数据过滤，没有权限过滤（技术总结列表本身对访客开放），没有重排序。

关键词路径按空格分词，中文整句往往就是一个 token，再在标题和正文里做子串计数。这不是 BM25，也没有倒排。

`VectorKnowledgeBase.search_documents` 在向量失败时，可能返回随机文档。若这条路径将来被接上而又不改掉随机回退，评测会被污染。

### 8.6 提示词

FlashRAG 的系统提示要求模型只依据给定文档，不知道就说不知道，并引用「文档1」这种编号。温度 0.7，偏高，检索问答里更容易脱离上下文。

无命中时的后备提示不再附带文档，模型可以自由发挥，响应里 `sources` 为空。调用方无法从 `success: true` 区分「有依据」和「模型自己编的」。

`chat_with_knowledge_base` 把最多三篇全文塞进提示，并明确说不用标文档编号。全文进上下文在 12 篇短笔记时还能跑，笔记变长后会顶满窗口，而且和分块检索互相矛盾。

没有对话历史，没有查询改写，没有「先判断是否需要检索」。

### 8.7 引用

FlashRAG 返回的来源是文档标题和 id，同一文档的多个块会重复出现，没有字符区间，也没有把 `metadata.source_url` 带出来。前端不渲染标题和链接。

`RAGService._extract_sources_from_answer` 用正则找「文档N」，id 写成 `doc1` 这种合成值，对不上数据库主键。该函数当前不会执行。

非 RAG 聊天在失败时仍返回 `success: true`。用户看到的是一段结构完整的学习建议，接口层面无法判断它没有查到资料。

### 8.8 评测

没有问题集，没有相关性标注，没有 Recall、MRR、忠实度或引用精确率。现有单元测试不断言检索结果。改分块或换模型之后，没有自动办法知道变好还是变差。

### 8.9 多轮、流式、可观测性、Agent

| 能力 | 现状 |
| --- | --- |
| 多轮记忆 | 只在浏览器数组里。服务端无会话、无摘要记忆 |
| 流式 | 无 SSE。前端超时 60 秒，一直等到整段 JSON |
| 工具调用 | 无。模型不能主动查项目、会议、成果或再次检索 |
| Agent 循环 | 无规划、无观察、无停止条件 |
| 可观测性 | 标准库 logging。无 trace id，无检索日志结构，无延迟直方图 |
| 供应商策略 | 调用方指定名字。密钥为空或网络失败时，各文件的回退行为不同 |

## 9. 和可用 RAG Agent 的差距

下面这些是后续要补的能力，按依赖关系而不是按热闹程度排：

1. **一份可信语料。** JSON、SQLite、FAISS 三者指向同一批文档。坏文件不能在启动时被静默当成空库。
2. **持久向量库。** 重启不重新编码；单篇技术总结更新时只重嵌入该篇的块。FAISS 可以继续用，但要落盘并保存 id 映射；也可以换成 SQLite 扩展或专用向量库。重点是 id 稳定、可删除。
3. **混合检索和重排。** 中文关键词（BM25 或等价的稀疏检索）加上向量，再用一个小的 cross-encoder 或供应商重排接口取 top-k。去掉随机回退。
4. **句子级引用。** 每个论据对应块 id、标题、`source_url` 和原文短句。模型被要求只使用这些短句；没有短句就拒答，HTTP 与 `success` 字段和「编造的学习建议」区分开。
5. **评测集。** 从现有技术总结出几十道可回答题和不可回答题，固定 Recall@5、拒答是否正确、引用是否支持答案。每次改检索都跑同一套。
6. **工具与循环。** 检索稳定之后，再让模型调用「搜知识库、查成果、查项目、查会议、受控抓取网页」。每一步留下输入输出，便于演示和排错。
7. **多轮。** 服务端保存会话，把历史压缩进下一次检索查询，避免只拿最后一句去嵌入。
8. **流式和观测。** SSE 输出 token；日志里能看到检索到的 id、分数、模型名和耗时。

## 10. 现有非 AI 模块怎么处理

| 模块 | 建议 | 原因 |
| --- | --- | --- |
| 技术总结 | 保留，作为 RAG 主语料 | 有正文、标签、`source_url`、作者。索引应以这张表为准，JSON 只做导出或干脆去掉 |
| 成果 | 保留数据和简单列表，收成 Agent 工具 | 适合回答「实验室发过什么、这篇和哪项成果有关」。继续加展示页对 RAG 帮助不大 |
| 项目 | 保留，收成工具 | 名称、状态、成员、描述能回答「谁在做什么」。当前只有 1 条数据，够做工具样例 |
| 会议 | 保留，收成工具，并合并重复页面 | 时间、地点、参与者对实验室问答有用。`CreateMeeting.vue` 与未引用的 `MeetingCreate.vue` 应合成一个 |
| 用户 / 「人员管理」 | 瘦成认证和目录查询 | 没有完整的人事 CRUD。列表接口先加上管理员鉴权，再暴露给 Agent 做「某人是什么角色」 |
| 爬取并总结 | 保留为受控摄入工具 | 放在 P2，和 SSRF 限制、域名白名单、提示词边界一起做 |
| 三套聊天实现、占位页、备份 py、嵌套 `backend/backend` | P0 之后删除或归档 | 它们让读者以为混合检索和自动切换已经存在 |

不要在 P2 之前重写成果墙、项目甘特图或会议 UI。那些页面已经能完成 CRUD，Agent 只需要稳定的查询函数。

## 11. 分阶段路线图

工作量用改动范围表示，不用日历时间。

- **小**：一个模块内、行为清楚，可以配一条冒烟测试。
- **中**：跨接口或数据流，要回归现有 CRUD。
- **大**：新的子系统（评测框架、持久索引、Agent 循环）。

### P0 清理和能启动

目标：另一个人按文档装依赖、启动进程、打开页面，看到的知识库文档数等于数据库里的技术总结数。失败就是失败，密钥不在仓库里。

| 事项 | 目标 | 涉及位置 | 验收 | 工作量 |
| --- | --- | --- | --- | --- |
| P0-1 作废密钥 | 已提交的 DeepSeek 密钥失效；运行时只从环境变量读密钥和 JWT 密钥 | `backend/.env.backup`、`backend/.env.tmp`、`config.py`。历史清理要单独做，本文件所在的改动不要顺便重写 git 历史 | 仓库当前树和文档中搜不到可用密钥；缺 `JWT_SECRET_KEY` 时进程拒绝启动，而不是使用固定字符串 | 小。历史清理另计，需要协调所有克隆 |
| P0-2 版本库瘦身 | 停止跟踪依赖、构建产物、数据库和个人上传文件 | `.gitignore`、`frontend/node_modules`、`frontend/dist`、两份 sqlite、`backend/app/static/uploads`。用一次专门的提交从索引移除，并保留本地样例的生成脚本 | 新克隆不包含这些路径；`npm ci` 与虚拟环境可以重建依赖；README 说明如何生成空库 | 中。文件多，但逻辑单一。不要和功能改动混在同一次提交 |
| P0-3 依赖能安装 | Python 3.10 与 3.12 至少有一个被文档声明且真正能装完；传递依赖被钉住 | `backend/requirements.txt`、`backend/Dockerfile`、`backend/app/utils/crawler.py`、`llm_api.py`、`flashrag_service.py` | 干净虚拟环境一条命令安装成功。`huggingface_hub` 与 `sentence-transformers` 可同时导入。`beautifulsoup4` 与所选 OpenAI SDK 在依赖清单内，且不把 `pydantic` 升到与钉死版本冲突的主版本。CPU 环境不下载整套 CUDA | 中。要么把栈升到仍维护的 Flask / Torch，要么锁死 3.10 并钉住 2023 年那一组 hub、tokenizers |
| P0-4 启动不再被模型绑死 | 缺模型或坏知识库时，CRUD 仍可启动；RAG 接口返回明确的 503 | `flashrag_service.py` 底部单例、`app/api/v1/__init__.py`、`startup_optimizer.py`、`run.py` | `python run.py` 在不下载模型时监听端口；`GET /api/v1/tech_summaries` 为 200；`POST /api/v1/rag/chat` 为 503 且 `success: false` | 中。把构造移到第一次请求或显式初始化 |
| P0-5 语料以数据库为准 | 去掉无法解析的 JSON，索引文档数等于技术总结行数 | `knowledge_base.json`、`knowledge_base.py`、`tech_summaries.py` 的 init 钩子 | 启动或执行一次重建后，检索器报告的文档数是 12（以当时数据库为准）。冲突标记不再出现。更新一篇总结后，重建能反映新正文 | 中。先修数据，再决定 JSON 是缓存还是删除 |
| P0-6 鉴权与调试 | 模型、文件、用户目录、索引重建需要登录；生产与本地默认配置分开 | `rag.py`、`ollama.py`、`tech_summaries.py`、`users.py`、`files.py`、`projects.py`、`meetings.py`、`config.py`、`run.py` | 未带令牌访问上述接口得到 401；会议详情与列表策略一致；`python run.py` 不打开交互式调试器 | 中 |
| P0-7 失败可见 | 没有密钥、没有命中时，不返回长篇「学习建议」冒充答案 | `chat_with_doc.py`、`rag_service.py` 的 `_mock_generate_answer`、`vector_knowledge_base.py` 的随机回退、`GlobalKnowledgeChat.vue` | 无命中时 `success: false` 或带 `grounded: false`。前端把该状态显示成错误，而不是普通回答 | 小 |
| P0-8 冒烟测试 | 一条不访问外网的测试能导入应用并检查健康与鉴权 | 新建 `backend/tests/test_smoke.py`，可加一个最小 CI 配置 | 测试进程不下载嵌入模型；断言技术总结列表在测试库上可调用；断言无令牌调用 RAG 被拒绝；`test_mock_data` 不再导入缺失模块 | 小 |

P0 完成的标志：新克隆、按 README 安装、启动后，技术总结页面有数据，知识库聊天要么基于这 12 篇回答，要么明确失败。

### P1 一条可评测的 RAG

目标：只保留一条检索实现。用固定问题集证明检索和引用，而不是再写一个服务类。

| 事项 | 目标 | 涉及位置 | 验收 | 工作量 |
| --- | --- | --- | --- | --- |
| P1-1 合并实现 | 删除或停用未接线的 `RAGService` 与在线 FlashRAG 中重复的 HTTP 客户端，只留一个 `retrieve()` 和一个 `answer()` | `app/utils/` 下三个服务、`rag.py`、`chat_with_doc.py`、`GlobalKnowledgeChat.vue`、`DocumentChat.vue` | 全仓库只有一个向量检索入口。前端 RAG 开关不再打到行为完全不同的两套 API | 大 |
| P1-2 中文分块 | 按标题和句子切块，块间重叠，记录标题路径 | 新模块，例如 `app/rag/chunk.py`，由技术总结保存流程调用 | 一篇含 `。` 和 Markdown 标题的样例被切成多块；每块能追溯到来源 id 和标题 | 中 |
| P1-3 持久索引 | 向量和 id 映射落盘，重启不重新编码；改一篇只更新该篇 | `app/rag/index.py` 替换内存 `IndexFlatL2` 单例。可继续用 FAISS 文件，或 SQLite 向量扩展 | 杀进程再启动，文档数不变且不调用嵌入模型；修改一篇后只有该篇的向量变化 | 大 |
| P1-4 混合检索与重排 | 稀疏检索加向量，合并后再取一个更小的 top-k | `app/rag/retrieve.py` | 在评测集上，混合结果的 Recall@5 高于「只做子串」和「只做 MiniLM + L2」的基线。无随机文档 | 大 |
| P1-5 换嵌入模型 | 换成支持中英、面向检索的小模型，查询向量归一化，距离与分数定义写进一处 | 配置项，不要散落在多个类里 | 同一评测集上 Recall@5 不低于 P1-4 的基线；分数单调、可解释 | 中。模型下载放在显式命令，不放在 import |
| P1-6 引用与拒答 | 答案中的每个论断对应一块原文；无支持则拒答 | 提示词、响应 schema、`GlobalKnowledgeChat.vue` | 响应包含 `citations[]`：`doc_id`、`title`、`source_url`、`quote`。前端能点开。评测集中的不可回答题被拒答，且 `success` 与有依据回答不同 | 大 |
| P1-7 评测集与指标 | 人工写一小套题，提交时能跑 | `evals/rag_qa.jsonl`、`backend/tests/test_rag_eval.py` 或独立脚本 | 至少 40 道可回答题、15 道不可回答题，每题标定期望文档 id。输出 Recall@5、拒答正确率、引用精确率（抽到的 quote 是否包含标注要点）。不调用付费 API 的检索部分可在 CI 跑 | 大。标注本身要人看现有 12 篇笔记，代码只是跑分 |
| P1-8 附件进入语料 | pdf/docx 抽文本再分块，失败的文件有记录 | `files.py`、新的 `app/rag/ingest.py` | 上传一份文本型 pdf，重建索引后能被对应问题检索到。扫描件明确标为未支持，而不是静默丢弃 | 中 |

P1 完成的标志：重启后索引还在；评测脚本打印三个数；聊天答案能点回某篇技术总结的某一段。

### P2 Agent 层

目标：模型在一个循环里按需调用工具，工具只读现有业务数据。不做第二套权限系统。

| 事项 | 目标 | 涉及位置 | 验收 | 工作量 |
| --- | --- | --- | --- | --- |
| P2-1 工具协议 | 一个循环：模型输出工具名和参数，服务端执行，把观察写回，直到最终回答或达到步数上限 | 新的 `app/agent/loop.py`、`app/api/v1/agent.py` | 单测用假模型驱动两步调用并停止。超过最大步数返回错误而不是无限请求 | 大 |
| P2-2 知识库搜索工具 | 包装 P1 的 `retrieve()`，返回块和引用，不直接生成最终答案 | `app/agent/tools/kb.py` | Agent 轨迹里能看到查询词、命中 id 和分数 | 小，前提是 P1 接口稳定 |
| P2-3 成果 / 论文工具 | 按标题、作者、类型查询 `Achievement` | `app/agent/tools/achievements.py`，复用 `achievements.py` 的查询条件 | 「有哪些论文或项目成果」类问题走该工具，答案里的 id 能在成果表中找到 | 中 |
| P2-4 项目与会议工具 | 按状态、成员、时间查询 | `projects.py`、`meetings.py` 的查询函数抽出来，避免工具直接拼 SQL | 问题「进行中的项目有哪些、下次会议在哪」返回库里的那 1 个项目和会议字段，且遵守调用者权限 | 中 |
| P2-5 受控网页工具 | 可选。替换开放 SSRF | `crawler.py` | 只允许配置过的域名；重定向后再检查主机；私网地址被拒绝 | 中 |
| P2-6 多轮 | 服务端会话，最近若干轮和一条滚动摘要进入下一次查询改写 | `app/agent/memory.py`、聊天页 | 第二轮使用「它」能检索到第一轮文档。会话存在服务端，刷新页面仍在 | 中 |
| P2-7 供应商适配器 | 一处实现 DeepSeek、OpenAI、Ollama 的聊天与（若使用）工具调用格式 | 替换四处手写 `requests.post` | 换供应商不改工具代码。Ollama 模型名来自配置。无密钥时该供应商标记为不可用，循环选择剩下的或直接 503 | 中 |
| P2-8 流式 | 最终回答走 SSE；工具阶段先推事件 | 前端聊天组件、Agent 接口 | 浏览器在完整回答结束前能看到增量文字；工具事件与正文可区分 | 中 |

P2 完成的标志：一次提问的响应里带有工具轨迹，例如先 `search_kb`，必要时再 `query_projects`，最后的句子仍能对上 P1 的引用格式。

### P3 演示和可维护性

| 事项 | 目标 | 涉及位置 | 验收 | 工作量 |
| --- | --- | --- | --- | --- |
| P3-1 观测 | 每次请求一个 id，记录检索 id、延迟、模型、是否拒答 | 日志结构或一个轻量 trace | 从一次聊天的 id 能还原工具和检索列表 | 中 |
| P3-2 演示页 | 引用可点击，工具轨迹可展开，空库和未配置密钥有明确空状态 | `KnowledgeChat.vue`、`GlobalKnowledgeChat.vue`，删掉未使用的 `RagChat.vue` | 桌面宽度下完成：登录、提问、看到引用、打开原文、看到拒答。移动宽度下输入框和引用不重叠 | 中 |
| P3-3 镜像 | 后端镜像使用 CPU 版 Torch 或把模型放到可选 profile；前端使用仍维护的 Node | `Dockerfile`、`docker-compose.yml` | `docker compose build` 成功，镜像里没有整套 CUDA 依赖（除非明确打开 GPU profile）。容器启动后冒烟接口通过 | 中 |
| P3-4 文档 | README 只描述已经存在的接口和启动方式 | `README.md`、`backend/README_RAG.md` | 文档中的每个路径都能在路由表里找到。去掉虚构的 `AIService` 示例，或改成指向真实模块 | 小 |

## 12. 简历上可以写的结果

把系统收成「实验室文档上的 RAG Agent」时，建议只写测得出的数字，例如：

- 从实验室技术总结构建评测集（建议 40+ 可回答、15+ 不可回答），报告 **Recall@5**、**拒答正确率**、**引用精确率**。可写目标：Recall@5 ≥ 0.80，不可回答题拒答正确率 ≥ 0.90，抽查引用与标注要点一致的比例 ≥ 0.85。这些数字要以 P1-7 的脚本输出为准，不要提前写进 README。
- 报告延迟：检索 p50 / p95，以及端到端生成 p95。P0 之后冷启动不应再为了 CRUD 加载嵌入模型；P1 之后重启不应全量重嵌入。把「重启后索引文档数 = 技术总结行数」当作正确性指标。
- Agent 演示用一条轨迹说明工具：知识库检索、成果查询、项目或会议查询。简历里写「带引用和工具轨迹的多轮问答」，并附评测表，比写「支持多种大模型智能切换」更站得住。
- 工程项可以写：把依赖从不可复现的 2023 年锁文件收成可安装的环境，补上冒烟测试，并把密钥和用户库移出版本库。这是维护者能复核的结果。

当前仓库还不能声称混合检索、自动故障转移或 FlashRAG 框架集成。那些句子和现有代码对不上。

## 13. 风险（最高的五项）

1. **秘密和个人数据已经在版本库里。** DeepSeek 密钥、用户邮箱、密码哈希、上传的办公文档都可被克隆得到。只改 `.gitignore` 不会从历史消失。
2. **鉴权空洞加上可预测的 JWT 密钥。** 未登录可读用户和文件、可触发索引重建和聊天；默认配置还能开调试器。密钥配上之后，聊天接口没有限额。
3. **RAG 目前是空的，而且有一条路径会假装成功。** 合并冲突让向量索引为空；关掉 RAG 时接口返回 200 和一篇通用建议。继续在这个行为上加 Agent，会把无依据文本写进多轮记忆。
4. **三套实现和未钉死的依赖。** Python 3.12 装不上钉死的科学计算包；Python 3.10 能装上，却会装出不兼容的 `huggingface_hub`，并且缺少源码已经导入的包。`torch==2.0.0` 在 Linux 上拉 CUDA 依赖。下一个人按 README 操作，大概率起不来。
5. **没有评测就无法判断改动是否有效。** 分块、距离函数、随机回退和引用 id 都有明确缺陷。没有问题集时，换模型或接入 Agent 只能靠演示运气，简历数字也无法复核。

## 14. 建议的下一步

先做 P0-1 到 P0-5：作废密钥、让干净环境能启动、让索引读到数据库里的 12 篇技术总结。P0-6 到 P0-8 可以跟在同一次稳定化里，但不要和删历史、换向量库混成一个巨大提交。

P1 的评测集可以在修 JSON 之后立刻开始标，不必等重排模型选定。题目来自现有笔记即可。

本文件所在的改动不修改业务代码，不删除已跟踪的依赖、数据库或上传文件。那些清理应在密钥作废之后单独进行。
