# 实验室知识管理系统

Flask 与 Vue 3 的实验室资料应用：技术总结、成果、项目、会议和登录后的知识库问答。问答只在检索到语料且语言模型可用时返回答案。

## 当前能力

- 账户使用 JWT。访问令牌约 8 小时，刷新令牌约 30 天。退出登录由浏览器丢弃令牌，服务端没有令牌吊销表。
- 角色分为普通用户与管理员。索引重建和调试接口需要管理员。
- 技术总结保存在数据库中。正文和上传的 pdf / docx / md / txt 会切块后写入 SQLite 索引（`backend/instance/rag_index.sqlite`，不入库）。创建、修改、删除技术总结时增量更新；全量重建走管理接口或 `python -m app.rag.rebuild`。
- 默认检索是混合检索再加重叠重排（`RAG_RETRIEVER=hybrid_rerank`）。稠密向量默认用确定性哈希，不下载模型。中文生产嵌入把 `RAG_EMBEDDER` 设为 `bge`（`BAAI/bge-small-zh-v1.5`，CPU）后重建索引。`RAG_RERANKER=cross-encoder` 才会加载 `BAAI/bge-reranker-base`。
- `access_scope=private` 的技术总结只有作者和管理员能检索和打开。`lab` 对登录成员可见。
- `RAG_ENABLED` 默认为 `false`。关闭时，RAG 对话返回 HTTP 503 和 `rag_unavailable`，业务 CRUD 仍可启动。
- 拒答阈值按嵌入器分开。哈希嵌入比较词元重叠和 `RAG_SCORE_THRESHOLD`（默认 0.12）。`RAG_EMBEDDER=bge` 时比较稠密余弦：dense 默认 0.60（`RAG_DENSE_SCORE_THRESHOLD`），hybrid 默认 0.62（`RAG_HYBRID_DENSE_SCORE_THRESHOLD`）。`RAG_RERANKER=cross-encoder` 时比较交叉编码器分数，默认 0.8981（`RAG_RERANK_SCORE_THRESHOLD`）。bge 的三个数来自 p1-v2 的 dev 划分。低于阈值时返回 `no_grounded_answer`，不会调用语言模型。命中但没有配置模型密钥时返回 HTTP 503 和 `llm_unavailable`，并带上引用。
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

两套题都是合成实验记录，没有真实个人数据。`seed_demo.py` 只写入 `p1-v1` 的 `corpus.jsonl`。CI 只跑哈希嵌入，不会下载 `bge` 权重。`baseline_results.json` 和 `baseline_p1v2_hash.json` 是哈希基线。`baseline_p1v2_bge.json` 才是本机 CPU 上 `BAAI/bge-small-zh-v1.5` 与 `BAAI/bge-reranker-base` 的实测，pytest 不重算这份文件。

```bash
cd backend
python -m evals.run_eval                  # p1-v1，哈希，可在 CI 中复现
python -m evals.run_v2 --embedder hash    # p1-v2 测试划分，哈希
python -m evals.run_v2 --embedder bge     # p1-v2，真实模型；需要本地权重，脚本设置 HF_HUB_OFFLINE=1
```

`python -m evals.run_eval --judge` 才会抽查语言模型，没有密钥时跳过。

### p1-v1 哈希基线（整集，不是 bge）

40 条可回答、18 条不可回答。稠密路是哈希嵌入，`hybrid_rerank` 是词重叠重排，不是交叉编码器。拒答看词元重叠，阈值 0.12。

| 模式 | Recall@5 | MRR | 引用准确率 | 拒答正确率 |
| --- | ---: | ---: | ---: | ---: |
| hash dense | 0.6750 | 0.5708 | 0.5250 | 1.0000 |
| hash hybrid | 0.7500 | 0.7500 | 0.7500 | 1.0000 |
| hash hybrid_rerank | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

拒答正确率是 1，因为这 18 条不可回答问题和语料没有共享词元。它只说明阈值能分开这组题。

### p1-v2 测试划分（哈希基线 vs 真实模型）

42 篇文档（14 个主题，每题 1 篇金文档 + 2 篇近义干扰），66 题：28 条改写、14 条多块答案、24 条与语料共享词汇的不可回答题。dev 28 / test 38，按问题 id 的 MD5 固定划分。下表只报告 test（24 条可回答、14 条不可回答）。bge 的余弦和交叉编码器阈值只在 dev 上选择，测试集没有参与选阈值。哈希的 0.12 没有重调。

延迟是索引建好、权重已加载之后，单条查询的检索时间（CPU）。交叉编码器那一行含 15 条候选的重排。

| 模式 | 证据 / 阈值 | Recall@5 | MRR | 引用准确率 | 拒答正确率 | p50 | p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hash dense | 词重叠 0.12 | 0.1250 | 0.0625 | 0.0000 | 0.2632 | 8.64 ms | 15.18 ms |
| hash hybrid | 词重叠 0.12 | 0.3750 | 0.2049 | 0.0833 | 0.2368 | 11.34 ms | 11.65 ms |
| bge dense | 余弦 0.60 | 0.7500 | 0.4931 | 0.2917 | 0.7105 | 16.87 ms | 17.71 ms |
| bge hybrid | 融合首条的余弦 0.62 | 0.4167 | 0.3056 | 0.2083 | 0.5526 | 19.84 ms | 22.18 ms |
| bge hybrid + cross-encoder | 分数 0.8981 | 0.7083 | 0.5278 | 0.3750 | 0.8158 | 2760.50 ms | 3207.25 ms |

bge 查询加了模型卡要求的检索前缀，文档侧不加。交叉编码器分数经过 sigmoid，落在 (0, 1)，不是原始 logit。融合分数做了 min-max，首条经常接近 1，所以不能拿来做拒答阈值。

这组数字说明：p1-v1 的拒答满分换到共享词汇的改写题上不成立；0.12 的词重叠同时漏掉改写题、又放进不可回答题。bge 稠密检索明显好于哈希，但 BM25 权重 0.62 的混合把改写题拉向同主题干扰文档，hybrid 低于 dense。交叉编码器把测试集上的不可回答题全部拒掉，引用和 MRR 也好于 hybrid，但 p50 约 2.8 秒，而且金文档必须先进入 hybrid 的 15 条候选。引用准确率仍然低，因为要点只写在文末「判定」节，前部块就能算进 Recall@5。

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
