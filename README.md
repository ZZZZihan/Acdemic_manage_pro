# 实验室知识管理系统

Flask 与 Vue 3 的实验室资料应用：技术总结、成果、项目、会议和登录后的知识库问答。问答只在检索到语料且语言模型可用时返回答案。

## 当前能力

- 账户使用 JWT。访问令牌约 8 小时，刷新令牌约 30 天。退出登录由浏览器丢弃令牌，服务端没有令牌吊销表。
- 角色分为普通用户与管理员。索引重建和调试接口需要管理员。
- 技术总结保存在数据库中。正文和上传的 pdf / docx / md / txt 会切块后写入 SQLite 索引（`backend/instance/rag_index.sqlite`，不入库）。创建、修改、删除技术总结时增量更新；全量重建走管理接口或 `python -m app.rag.rebuild`。
- 默认检索是混合检索再加重叠重排（`RAG_RETRIEVER=hybrid_rerank`）。稠密向量默认用确定性哈希，不下载模型。中文生产嵌入把 `RAG_EMBEDDER` 设为 `bge`（`BAAI/bge-small-zh-v1.5`，CPU）后重建索引。`RAG_RERANKER=cross-encoder` 才会加载 `BAAI/bge-reranker-base`。
- `access_scope=private` 的技术总结只有作者和管理员能检索和打开。`lab` 对登录成员可见。
- `RAG_ENABLED` 默认为 `false`。关闭时，RAG 对话返回 HTTP 503 和 `rag_unavailable`，业务 CRUD 仍可启动。
- 证据分数低于 `RAG_SCORE_THRESHOLD` 时返回 `no_grounded_answer`，不会调用语言模型。命中但没有配置模型密钥时返回 HTTP 503 和 `llm_unavailable`，并带上引用。
- 生成走同一个 OpenAI 兼容接口，供应商为 DeepSeek、OpenAI 或 Ollama（`/v1/chat/completions`）。`POST /api/v1/rag/chat/stream` 用 SSE 输出引用和 token。知识库页面会流式显示答案、可点击引用，以及单独的“没有足够依据”状态。
- 每次 RAG 请求写一条 `rag_trace` 审计：检索耗时、命中 id、分数、模型名、token 数。不写问题、提示词或正文。

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

## 检索评测

题集在 `backend/evals/`，版本 `p1-v1`。语料是合成实验记录，`seed_demo.py` 会在空库里写入同一份 `corpus.jsonl`。问题含 40 条可回答和 18 条不可回答。脚本不下载模型，稠密路使用哈希嵌入。

```bash
cd backend
python -m evals.run_eval
python -m evals.run_eval --write-baseline
python -m evals.run_eval --judge
```

`--judge` 才调用语言模型，并且只抽查几条；没有密钥时会跳过。`baseline_results.json` 是哈希嵌入 + BM25 + 重叠重排的实测基线，不是 `bge` 权重跑出来的数。切换到 `RAG_EMBEDDER=bge` 之后需要自行重跑评测，不要把基线数字当成神经模型的召回率。

| 模式 | Recall@5 | MRR | 引用准确率 | 拒答正确率 |
| --- | ---: | ---: | ---: | ---: |
| dense | 0.6750 | 0.5708 | 0.5250 | 1.0000 |
| hybrid | 0.7500 | 0.7500 | 0.7500 | 1.0000 |
| hybrid_rerank | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

拒答正确率是 1，因为这 18 条不可回答问题和语料没有共享词元。它说明阈值能分开这组题，不是线上用户问题的估计。

## 检查

```bash
cd backend
python -m pytest
ruff check ../backend
bash ../scripts/scan-secrets.sh
```

GitHub Actions 会运行全历史密钥扫描、后端 lint 与测试，以及 `npm ci`。

## 主要接口

| 方法 | 路径 | 访问 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 公开，有限流 |
| GET | `/api/v1/users` | 登录；非本人邮箱对普通成员隐藏 |
| POST | `/api/v1/rag/chat` | 登录，有限流 |
| POST | `/api/v1/rag/chat/stream` | 登录，有限流；SSE |
| POST | `/api/v1/rag/init_flashrag` | 管理员；从数据库重建语料和向量索引 |
| POST | `/api/v1/knowledge_base/chat` | 登录，有限流 |
| GET | `/api/v1/files/download/<path>` | 登录 |
| GET | `/api/v1/meetings/<id>` | 登录 |

成果列表和技术总结列表仍可匿名读取。它们的附件下载需要登录。

## 容器

`backend/Dockerfile` 使用 `python:3.11-slim` 并安装上述依赖。运行前仍需注入 `SECRET_KEY`、`JWT_SECRET_KEY` 和 `CORS_ORIGINS`。`docker-compose.yml` 读取 `backend/.env`，该文件不要提交。
