# Acdemic Manage Pro 2.0 面试讲解手册

## 1. 一句话定位
这是一个 `LLM-first` 的实验室工作台系统：用户通过一个线程入口调度任务、会议、知识和外部协同，系统通过统一的 MCP 能力面和多模型路由策略完成执行，并把高风险动作纳入审批闭环。

## 2. 为什么这个项目“有技术含量”
- 双核心编排：`OpenAI + Claude` 作为 Tier A 编排核心，承担高风险外部协同。
- 多 provider 统一能力层：`DeepSeek / MiniMax / Ollama` 复用同一内部工具语义。
- MCP 能力面：按 `tools / resources / prompts` 暴露系统能力，而不是堆叠聊天接口。
- 审批控制平面：所有外部写操作默认审批，动作可追踪、可拒绝、可审计。
- 可解释路由：每次请求返回 `routing trace`，说明请求是如何被模型选路与降级的。

## 3. 你可以这样讲架构
前端工作台（线程 UI）只负责表达意图。后端 `api/v2` 负责会话编排，调用统一 MCP 能力层。MCP 层把结构化状态（资源）和动作（工具）规范化，模型只通过能力层调用业务，不直接碰业务代码。Provider 层负责多模型协议适配和能力分级，审批层负责风险闸门，知识层负责文档入库与检索。

## 4. 面试现场 10 分钟 Demo 脚本
1. 打开 `/workspace`，展示五家 provider 和 tier 分层。
2. 发送“请安排项目评审会议”并选择 `deepseek`。
3. 展示系统自动升级到 Tier A，并生成 `calendar.create_event` 审批卡。
4. 批准审批，展示状态变化和活动流。
5. 发送“请整理任务列表”，展示自动触发 `task.create` 的内部工具调用。
6. 打开 `/mcp` 展示 tools/resources/prompts 目录。
7. 调用 `/api/v2/interview/architecture` 展示架构亮点输出。

## 5. 关键接口（建议背下来）
- `POST /api/v2/chat/messages`：线程消息入口，返回 `assistant + routing + tool_calls + approval`。
- `GET /api/v2/approvals`、`POST /api/v2/approvals/{id}/decision`：审批流闭环。
- `GET /mcp`、`POST /mcp/tools/call`、`POST /mcp/resources/read`：MCP 能力面。
- `GET /api/v2/interview/architecture`：面试演示专用架构摘要。

## 6. 被追问时可讲的工程取舍
- 为什么分层：防止聊天接口吞噬业务边界，保证可维护性和安全策略可控。
- 为什么要审批：LLM 能力强但不可完全信任，外部写操作必须人类在环。
- 为什么多模型：降低单厂商风险，按能力/成本/隐私场景动态选路。
- 为什么有本地模型：处理隐私和离线场景，保证核心功能可降级。

## 7. 当前边界与下一步
- 当前已实现：统一能力骨架、路由 trace、审批闭环、任务自动工具调用、面试演示接口。
- 待实现重点：
  - Provider 真实线上调用（OpenAI/Claude/DeepSeek/MiniMax/Ollama）生产级接入。
  - Google OAuth + Calendar/Drive/Gmail 实时联调。
  - 检索层从样例搜索升级到生产检索链路和评测。
