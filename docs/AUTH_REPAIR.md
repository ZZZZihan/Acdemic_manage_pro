# JWT、登录及角色修复

本补丁基于 PR #2，修复 V1/V2 共用登录状态、令牌刷新、退出撤销和角色管理。未部署或改动线上数据。

## 行为

- 注册一律获得 User；邮箱或请求中的角色字段不能授予管理员。
- 登录返回当前数据库角色；鉴权每次读取数据库，降权无需等待 JWT 过期。
- 管理员在“角色管理”分配 User、Moderator、Administrator，不能在页面撤销自己的管理员身份。资源所有者权限仍按各业务接口执行。
- 访问令牌过期时并发请求共用一次刷新；403 不清空登录，失效会话返回登录页。上传与 V2 使用同一刷新逻辑。
- 退出撤销当前会话的访问和刷新令牌，其他设备会话不受影响。
- V2 除健康检查外通过 V1 验证身份。该补丁没有实现 V2 全量资源的用户/租户隔离。
- 登录启动不再加载可选 RAG 模型；AI 功能仍需要独立安装原有完整依赖。

## 升级

先备份数据库，在停止写入的维护窗口执行。以下命令在 `backend` 目录运行，使用 V1 Python 环境；先安装 `requirements-web.txt`，AI 功能另需完整依赖。

生产环境必须设置 `FLASK_CONFIG=production` 和至少 32 字符的随机 `JWT_SECRET_KEY`，所有 V1 实例使用同一值。可用 `python -c 'import secrets; print(secrets.token_urlsafe(48))'` 生成并存入部署密钥配置。开发环境自动生成本地持久密钥，勿提交该文件。

已纳入 Alembic 版本管理的数据库：

```bash
export FLASK_APP=run.py
flask db upgrade
flask init-auth
```

新建或尚未使用 Alembic 管理的数据库可以执行以下非破坏性初始化，创建缺失表、补齐角色，并保留已有业务数据与已分配角色。不要对未知数据库直接执行 Alembic stamp。

```bash
python init_db.py
```

新增 `auth_sessions` 表。旧版令牌没有会话标识，升级后用户需要重新登录。请确认实际部署环境的数据库地址正确；脚本读取环境变量，Flask CLI 的 `run.py` 也加载 `backend/.env`。

显式创建首位管理员（交互输入密码，无默认密码）：

```bash
python create_admin.py --email you@example.org --username administrator
```

提升已有账号而不重置密码：

```bash
export FLASK_APP=run.py
flask set-role existing_username Administrator
```

V2 环境配置 `AUTH_SERVICE_URL` 指向 V1 内部服务地址，默认 `http://127.0.0.1:5003`；Compose 已设置为 `http://backend:5003`。身份服务不可用时 V2 拒绝访问并返回 503。

## 验证记录

- V1：32 项单元/集成回归通过，覆盖注册提权、角色分配、撤销、过期、伪造令牌、迁移保留数据与管理员初始化。
- V2：23 项回归通过，包含鉴权、过期错误传播和身份服务故障。
- 真实 Chromium：8 项登录回归通过，覆盖登录/刷新页面、错误密码、管理员分配角色、并发刷新、过期后上传、退出撤销、损坏存储与无效刷新令牌。
- 初始化脚本在全新临时 SQLite 数据库运行成功。
- 本次修改的前端源码 ESLint 与生产构建通过。
- 原有 4 项 workspace E2E 已适配登录前置条件，但此次没有重跑；不计入上述通过数量。

可复现浏览器回归：安装 frontend npm 依赖及 Playwright Chromium 后，在仓库根目录执行 `bash scripts/test-auth-e2e.sh`。脚本使用临时数据库与虚构账号；新增 auth-regression CI 工作流运行相同验证。
