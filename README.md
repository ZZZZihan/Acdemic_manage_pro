# 实验室知识管理系统

Flask 与 Vue 3 的实验室资料应用：技术总结、成果、项目、会议和登录后的知识库问答。问答只在检索到语料且语言模型可用时返回答案。

## 当前能力

- 账户使用 JWT。访问令牌约 8 小时，刷新令牌约 30 天。退出登录由浏览器丢弃令牌，服务端没有令牌吊销表。
- 角色分为普通用户与管理员。索引重建和调试接口需要管理员。
- 技术总结保存在数据库中。对话前从这些行重建内存语料。可选的向量检索使用 `sentence-transformers` 与 FAISS，模型在第一次向量检索时才加载。
- `RAG_ENABLED` 默认为 `false`。关闭时，RAG 对话返回 HTTP 503 和 `rag_unavailable`，业务 CRUD 仍可启动。
- 没有命中语料时返回 `no_grounded_answer`，不会返回通用学习建议。命中但没有配置模型密钥时返回 HTTP 503 和 `llm_unavailable`，并带上命中文档的 id 与标题。
- 生成后端只使用环境变量中的 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。Ollama 是单独的 `/api/v1/ollama/chat` 接口，需要本机 Ollama，不会自动切换供应商。

不提供的能力：自动故障转移、多供应商路由、`/api/v1/ai/providers`、`/api/v1/knowledge_base/query`。README 里不再描述这些接口。

## 安全基线

密钥、CORS、审计、上传和历史泄露的处理见 [SECURITY.md](SECURITY.md)。应用在 `SECRET_KEY` 或 `JWT_SECRET_KEY` 缺失、过短或仍是占位符时拒绝启动。调试模式默认关闭。

## 本地运行

后端使用 Python 3.11（3.10 也可安装同一份依赖）。前端使用锁文件安装。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：替换两个密钥，按需填写模型密钥
export ADMIN_PASSWORD='choose-a-long-demo-password'
export MEMBER_PASSWORD='choose-another-long-password'
python seed_demo.py
python run.py
```

`requirements.txt` 通过 PyTorch CPU 索引安装 `torch`，默认不安装 CUDA 轮子。向量检索不是启动 CRUD 的前提。

```bash
cd frontend
npm ci
npm run dev
```

Vite 把 `/api` 代理到 `http://localhost:5003`。浏览器来源需在 `CORS_ORIGINS` 中。

演示库只包含 `example.com` 账户和合成记录，不包含真实个人数据，也不包含上传文件。已有的 SQLite 文件和 `backend/app/static/uploads/` 被 git 忽略。初始迁移没有建 `tech_summaries` 表；新鲜数据库会在迁移 `23a8bb636e7e` 中创建它。已经执行过该迁移的旧库不会重跑这一步。

## 检查

```bash
cd backend
python -m pytest
ruff check ../backend
bash ../scripts/scan-secrets.sh
```

GitHub Actions 会运行工作区密钥扫描、后端 lint 与测试，以及 `npm ci`。工作区扫描不会检查 git 历史。

## 主要接口

| 方法 | 路径 | 访问 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 公开，有限流 |
| GET | `/api/v1/users` | 登录；非本人邮箱对普通成员隐藏 |
| POST | `/api/v1/rag/chat` | 登录，有限流 |
| POST | `/api/v1/rag/init_flashrag` | 管理员；从数据库重建语料 |
| POST | `/api/v1/knowledge_base/chat` | 登录，有限流 |
| GET | `/api/v1/files/download/<path>` | 登录 |
| GET | `/api/v1/meetings/<id>` | 登录 |

成果列表和技术总结列表仍可匿名读取。它们的附件下载需要登录。

## 容器

`backend/Dockerfile` 使用 `python:3.11-slim` 并安装上述依赖。运行前仍需注入 `SECRET_KEY`、`JWT_SECRET_KEY` 和 `CORS_ORIGINS`。`docker-compose.yml` 读取 `backend/.env`，该文件不要提交。
