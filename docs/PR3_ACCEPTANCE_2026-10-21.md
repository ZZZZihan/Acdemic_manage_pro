# PR #3 独立技术验收（2026-10-21，北京时间）

**结论：本轮修复后的登录、角色与工作台回归达到受控开发验收标准；多用户生产部署 NO-GO。** 合并还须核对本轮修复提交的 GitHub Checks，不能把旧提交的 8 项登录成功转用于新提交，也不能把 mergeable=true 当作发布批准。本文件记录本地候选证据；推送后的 CI 以对应 SHA 的 Checks 为准。

## 对象与方法

| 对象 | 初始固定提交 | 关系 |
| --- | --- | --- |
| main | `97af286754dfca752ed73813f814b255210cd04c` | 默认主线 |
| PR #2 | `e45f38a7d6b5d6d8327431a678b37a2b4c842f02` | base=main，Open/Draft，8 commits |
| PR #3 | `2a8da185e64ce71a105a7c96357efd487339da86` | base=codex/lint-test-stabilization，Open/Draft；唯一父提交即 PR #2 HEAD |

先读取此前两份审核记录，再独立审查本次认证、角色、前端客户端和测试入口。使用新克隆、独立 Python 环境、合成账号和临时 SQLite，真实启动 Flask、FastAPI、Vite 与 Chromium。没有连接生产数据库、执行线上迁移、合并 PR、调用付费模型、创建外部日历事件或部署。

本轮修复基于上述 PR #3；下述本地最终测试运行于本提交包含的代码和测试内容。`validation/pr3-2026-10-21/source-sha256.json` 记录修改文件的字节摘要。依赖安装与构建产生的 node_modules/dist 变化没有纳入修复。

## 发现并处理的问题

| 问题 | 独立证据 | 本轮处理 |
| --- | --- | --- |
| 项目物理删除在身份 ID 修正后放通不可信路径 | 普通用户自己的项目，可登记上传目录外临时哨兵路径；原接口注册 201、删除 200，哨兵实际消失。只操作合成文件。 | 保留身份和对象权限检查，随后返回 409 `physical_delete_requires_verified_upload`；原始字节和关联不变，逻辑解绑保持可用。仅限定 realpath 不能阻止删除他人或共享上传，因此暂不开放物理删除。 |
| 会议页面上传绕过 refresh | 创建页真实浏览器上传返回 401，没有 refresh 请求，等待成功超时；共享 FileUpload 的旧测试未覆盖此页面。 | 创建、编辑、详情及旧版组件统一使用共享 Axios；新增 3 个真实浏览器回归。 |
| 退出后旧请求的成功响应仍被接收 | 延迟真实 `/auth/user` 的 200 响应，完成真实 logout 后释放，原实现仍返回 `accepted`。只延迟传输，不伪造响应内容。 | 成功响应也检查会话 epoch，旧响应丢弃；新增浏览器回归，V1/V2 共享客户端实现受益。 |
| 堆叠 PR 漏跑核心 CI | backend-tests/e2e-workspace 的 `pull_request.branches=[main]` 不匹配 PR #3 base。 | 两者覆盖所有 PR，push 仍限定 main；认证 CI 增加 ESLint 与 build；工作台失败保存诊断。 |
| 启动检查仍把受保护接口当匿名 200 | 新认证使 `/api/v2/interview/architecture` 匿名返回 401，旧 `stack.sh check` 据此报错。 | 公共 health 检查 200，受保护入口检查匿名 401；工作台 runner 执行此检查。 |
| 工作台测试容易读到旧对象，启动依赖外部环境 | 原测试按全局卡片 first/count、检索标题判断；MCP 直连硬编码端口。首次本地启动另遭 Vite 网络接口枚举错误，尚未执行断言。 | 审批、知识按本次响应 ID 核验；任务和审批再经 API 读回；MCP 走代理；runner 固定本地地址、严格端口、请求超时及部分启动清理。 |

物理删除的 409 是有意的功能收缩。恢复该功能需要可信上传 ID、上传所有者、业务归属和共享引用管理，不应直接移除保护。

## 本地实际执行结果

| 验证 | 原始基线 | 修复候选最终结果 | 证明范围 |
| --- | --- | --- | --- |
| V1 auth + mock_data | 32/32 PASS | **36/36 PASS** | 注册不提权、三角色、降权旧 JWT、业务 403、刷新、撤销、其他设备保留、会话重建持久化、迁移测试、物理删除保护 |
| V2 services + API + auth | 23/23 PASS | **23/23 PASS** | 当前编排骨架、鉴权入口、401 传播、身份服务异常 503；部分单测替换身份 transport |
| Chromium 登录回归 | 旧 8 项曾在 GitHub 成功 | **13/13 PASS** | 原 8 项与会议上传 3 项、旧响应 1 项、真实降权 1 项；真实 V1/V2 HTTP |
| 原 Workspace 四个 spec | 本轮第一次启动失败，未进入断言 | **4/4 PASS** | 知识入库与检索、Ollama 只读分支、DeepSeek→OpenAI 路由、审批与任务持久化；并非真实模型/Calendar 联调 |
| 前端全量 ESLint（不带 --fix） | — | **PASS，0 errors** | 全部配置范围内源码 |
| `npm ci` / `npm run build` | — | **退出码 0** | 锁文件安装与前端构建，不等同 Docker 发布验证 |
| shell 语法、差异空白检查 | — | **PASS** | 三份 shell 脚本及最终修复 diff |

浏览器本地使用 Chromium **153.0.8010.0**、Playwright **1.58.2**；Node **24.19.0**、Python **3.11.17**。Playwright 默认 CDN 下载返回损坏的 ZIP，因此通过隔离的 `@sparticuz/chromium@153.0.0` npm 包取得浏览器，使用 `PW_EXECUTABLE_PATH`。没有修改项目依赖锁文件。GitHub 工作流使用自身 setup-node 20 / setup-python 3.11 与 Playwright 安装流程，需独立看其结果。

真实降权用例：管理员 A 先将合成用户 B 提升，再降为 User；B 的原 access token 请求 `/roles` 返回 403，`/auth/user` 和 refresh 均为 User，V2 providers 仍为 200（普通登录允许）；重新进入角色页跳至 Profile、菜单消失、普通会话保留。当前页菜单不会收到服务器主动推送；服务端权限即时生效，导航时重新验证角色。

## 复现命令

以下在干净工作目录执行，V1/V2 使用各自环境，避免 SQLAlchemy 1.x/2.x 混装：

```bash
python3.11 -m venv .venv_auth_v1
.venv_auth_v1/bin/pip install -r backend/requirements-web.txt
python3.11 -m venv .venv_auth_v2
.venv_auth_v2/bin/pip install -r backend/requirements-v2.txt
.venv_auth_v1/bin/python -m unittest backend/tests/test_auth_api.py backend/tests/test_mock_data.py -v
.venv_auth_v2/bin/python -m unittest backend/tests/test_v2_services.py backend/tests/test_v2_api.py backend/tests/test_v2_auth.py -v
cd frontend
npm ci
npx playwright install --with-deps chromium
npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs --ignore-path .gitignore
npm run build
cd ..
bash scripts/test-auth-e2e.sh
cd frontend
npm run e2e -- tests/e2e/workspace-copilot.spec.ts tests/e2e/provider-routing.spec.ts tests/e2e/ollama-local-only.spec.ts tests/e2e/knowledge-ingest.spec.ts
```

工作台 runner 首次创建 `backend_env` 与 `.venv_v2`；本地验收为了复用同样依赖，二者分别链接到前述独立环境。普通环境不需此优化。两个 runner 均创建临时数据库；不要设置 `E2E_ALLOW_REUSE=1` 指向真实服务。受限环境可向两条浏览器命令传入 `PW_EXECUTABLE_PATH=/path/to/chromium`；此选项仅用于隔离测试浏览器，不是生产启动建议。`KEEP_AUTH_E2E_LOGS=1` 可保留合成测试运行目录。

## GitHub CI 与合并依赖

原 HEAD 的 [auth-regression run 39412261343](https://github.com/ZZZZihan/Acdemic_manage_pro/actions/runs/39412261343) 为 success，日志明确 `8 passed (11.8s)`，时间为 2026-10-20 19:03–19:04 北京时间。实际 checkout `ba6b13f512d3afd5d5946d85f6fe98aaf0360cc7`，其 tree 与原 HEAD 均为 `c4fc0cf38878748c98acbf10ad19fcfcfbb04b0d`，内容一致。该 HEAD 只有此一个 check，不能称全套集成通过。

PR #2 的历史 [backend-tests 23631441131](https://github.com/ZZZZihan/Acdemic_manage_pro/actions/runs/23631441131) 与 [e2e-workspace 23631441136](https://github.com/ZZZZihan/Acdemic_manage_pro/actions/runs/23631441136) 均 failure；三个 jobs 的 steps 为空、旧日志 410，因此没有证据判断是安装、额度还是测试断言失败。legacy commit status 的 `pending, total_count=0` 只是没有旧式 status，不代表有检查正在跑。

推荐顺序：确认修复候选的后端、认证/构建、工作台检查全部通过 → **PR #3 合入 PR #2 的开发分支** → PR #2 对 main 的新集成提交重新通过同样检查 → 再决定 PR #2 合入 main。此顺序不会让未带认证修复的 #2 先进入主线。本轮未执行这些合并。

若改用 #2 先合入 main：不要部署中间态，随后把 #3 base 改为 main、复核 diff 和合并提交并重跑。若 #2 squash/rebase merge，旧祖先 SHA 会改变，旧的 mergeable/CI 结果不能替代新的集成验证。

## 剩余安全与产品边界

1. **V2 对象授权仍未实现。** 身份依赖把用户写入 request.state，但会话、任务、知识、审批模型没有 owner/tenant 约束；列表和业务操作尚未按当前用户过滤。有效登录不是跨用户隔离，多用户开放仍阻断。V2 user-context 仍为演示上下文。
2. **旧版内容与文件风险仍在。** 当前 MarkdownRenderer 仍将未净化的 marked 输出交给 v-html；token 存在 localStorage。V1 公开下载/静态上传路径与部分业务对象权限、URL 抓取、模型调用预算和本地 Provider 出域边界不属于本轮完整修复。前次发现不能因登录绿灯自动关闭。
3. **会议附件端到端业务仍有缺口。** 本轮证明文件上传认证和过期重试；不证明 attachments/files DTO、关联保存、下载删除全部协同。资料/密码页面等旧功能亦未做全应用验收。
4. **模型与外部执行仍是骨架。** 工作台固定分支、审批改状态及演示检索通过，不代表真实 LLM、标准 MCP 客户端互操作、Google Calendar 写入、审批幂等或外部副作用已经可用。
5. **生产运行没有验收。** 未做 Docker 镜像、HTTPS/反向代理、真实数据库迁移、备份恢复、多实例共享会话库、生产密钥轮换及并发负载验证。空库 create_all 与 auth migration 测试不能证明完整历史 Alembic 链可安全升级任意现存库。仓库仍跟踪依赖目录、历史数据库/上传和敏感配置形态，需另行治理；本轮没有使用或验证历史密钥。

因此：可以继续受控开发，并在同 SHA CI 通过后推进上述集成顺序；**不批准多用户生产上线**。

## 证据目录

见 [validation/pr3-2026-10-21](validation/pr3-2026-10-21)：后端与浏览器控制台记录、两个修复前失败记录、实际 Python 依赖版本、原 GitHub CI 元信息及修改源码 SHA-256。控制台文本去除了 ANSI 颜色；不提交含会话 token 的浏览器 trace 或临时数据库。
