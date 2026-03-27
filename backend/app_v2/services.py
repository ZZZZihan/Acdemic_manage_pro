from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .mcp.registry import McpRegistry
from .models import (
    ActivityEvent,
    ConversationMessage,
    ConversationThread,
    ExternalAccount,
    KnowledgeAsset,
    ProviderProfile,
    Task,
    ToolApproval,
)
from .providers import ProviderRegistry, build_execution_chain


SCHEDULE_KEYWORDS = ('安排', '会议', '组会', 'calendar', '日程', '评审')
TASK_KEYWORDS = ('任务', '行动项', 'todo', 'to-do', '待办')


@dataclass
class AppServices:
    provider_registry: ProviderRegistry
    mcp_registry: McpRegistry

    def seed_defaults(self, session: Session) -> None:
        existing_profiles = {row.name for row in session.execute(select(ProviderProfile)).scalars()}
        for profile in self.provider_registry.list():
            if profile.name in existing_profiles:
                continue
            session.add(
                ProviderProfile(
                    name=profile.name,
                    tier=profile.tier,
                    default_model=profile.default_model,
                    local_only=profile.local_only,
                    supports_tools=profile.supports_tools,
                    supports_external_write=profile.supports_external_write,
                    supports_google_connectors=profile.supports_google_connectors,
                    description=profile.description,
                )
            )

        existing_accounts = {
            (row.provider, row.account_type)
            for row in session.execute(select(ExternalAccount)).scalars()
        }
        for account_type in ('google_calendar', 'google_drive', 'google_gmail'):
            key = ('google', account_type)
            if key in existing_accounts:
                continue
            session.add(
                ExternalAccount(
                    provider='google',
                    account_type=account_type,
                    status='disconnected',
                    scopes=[],
                    writable=(account_type == 'google_calendar'),
                )
            )
        session.commit()

    def list_provider_payload(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(select(ProviderProfile)).scalars().all()
        by_name = {row.name: row for row in rows}
        payload: list[dict[str, Any]] = []
        for item in self.provider_registry.list():
            profile = by_name.get(item.name)
            if profile is None:
                continue
            payload.append({
                'name': profile.name,
                'tier': profile.tier,
                'default_model': profile.default_model,
                'local_only': profile.local_only,
                'supports_tools': profile.supports_tools,
                'supports_external_write': profile.supports_external_write,
                'supports_google_connectors': profile.supports_google_connectors,
                'description': profile.description,
            })
        return payload

    def list_external_accounts(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(select(ExternalAccount)).scalars().all()
        return [
            {
                'id': row.id,
                'provider': row.provider,
                'account_type': row.account_type,
                'status': row.status,
                'scopes': row.scopes,
                'connected_email': row.connected_email,
                'writable': row.writable,
            }
            for row in rows
        ]

    def create_thread(self, session: Session, title: str) -> ConversationThread:
        thread = ConversationThread(title=title)
        session.add(thread)
        session.commit()
        session.refresh(thread)
        return thread

    def get_thread(self, session: Session, thread_id: str) -> ConversationThread:
        thread = session.get(ConversationThread, thread_id)
        if thread is None:
            raise KeyError(f'Thread {thread_id} not found')
        return thread

    def serialize_thread(self, thread: ConversationThread) -> dict[str, Any]:
        return {
            'id': thread.id,
            'title': thread.title,
            'created_at': thread.created_at.isoformat(),
        }

    def serialize_message(self, message: ConversationMessage) -> dict[str, Any]:
        return {
            'id': message.id,
            'thread_id': message.thread_id,
            'role': message.role,
            'provider': message.provider,
            'content': message.content,
            'metadata': message.payload,
            'created_at': message.created_at.isoformat(),
        }

    def serialize_approval(self, approval: ToolApproval) -> dict[str, Any]:
        return {
            'id': approval.id,
            'thread_id': approval.thread_id,
            'tool_name': approval.tool_name,
            'provider': approval.provider,
            'status': approval.status,
            'arguments': approval.arguments,
            'rationale': approval.rationale,
            'created_at': approval.created_at.isoformat(),
            'decided_at': approval.decided_at.isoformat() if approval.decided_at else None,
        }

    def serialize_activity(self, activity: ActivityEvent) -> dict[str, Any]:
        return {
            'id': activity.id,
            'thread_id': activity.thread_id,
            'event_type': activity.event_type,
            'payload': activity.payload,
            'created_at': activity.created_at.isoformat(),
        }

    def post_message(self, session: Session, thread_id: str, provider: str, content: str) -> dict[str, Any]:
        requested_profile = self.provider_registry.get(provider)
        self.get_thread(session, thread_id)

        lower_content = content.lower()
        requires_external_write = any(keyword in lower_content for keyword in SCHEDULE_KEYWORDS)
        task_intent = any(keyword in lower_content for keyword in TASK_KEYWORDS)
        lock_to_requested = requested_profile.local_only

        chain = build_execution_chain(
            requested_provider=provider,
            registry=self.provider_registry,
            requires_external_write=requires_external_write,
            lock_to_requested=lock_to_requested,
        )
        routing_trace: list[dict[str, str]] = []
        if requires_external_write and not requested_profile.supports_external_write and not lock_to_requested:
            routing_trace.append(
                {
                    'provider': provider,
                    'action': 'skip',
                    'reason': 'capability_mismatch_external_write',
                }
            )
        resolved_provider = provider
        for candidate in chain:
            candidate_profile = self.provider_registry.get(candidate)
            if requires_external_write and not candidate_profile.supports_external_write:
                routing_trace.append(
                    {
                        'provider': candidate,
                        'action': 'skip',
                        'reason': 'capability_mismatch_external_write',
                    }
                )
                continue
            resolved_provider = candidate
            routing_trace.append(
                {
                    'provider': candidate,
                    'action': 'select',
                    'reason': 'first_capable',
                }
            )
            break

        resolved_profile = self.provider_registry.get(resolved_provider)
        user_message = ConversationMessage(
            thread_id=thread_id,
            role='user',
            provider=provider,
            content=content,
            payload={'tier': requested_profile.tier},
        )
        session.add(user_message)

        approval = None
        approval_requested = False
        tool_calls: list[dict[str, Any]] = []
        if requires_external_write:
            if resolved_profile.local_only or not resolved_profile.supports_external_write:
                assistant_content = (
                    '当前执行链被限制在本地/只读能力，已记录你的安排意图。'
                    '如需写入外部日历，请切换到 OpenAI 或 Claude。'
                )
            else:
                approval_requested = True
                approval = ToolApproval(
                    thread_id=thread_id,
                    tool_name='calendar.create_event',
                    provider=resolved_provider,
                    status='pending',
                    arguments={
                        'title': 'Project review meeting',
                        'time_hint': content,
                    },
                    rationale='Detected meeting scheduling intent from the conversation.',
                )
                session.add(approval)
                assistant_content = (
                    f'{resolved_provider} 已分析出这是一个高风险外部协同请求，'
                    '我已生成 Google Calendar 创建审批，待你确认后执行。'
                )
                session.add(
                    ActivityEvent(
                        thread_id=thread_id,
                        event_type='approval.requested',
                        payload={'tool_name': 'calendar.create_event', 'provider': resolved_provider},
                    )
                )
        elif task_intent:
            task = self.create_task(
                session,
                title='跟进任务：项目推进事项',
                description=content,
                source_thread_id=thread_id,
                auto_commit=False,
            )
            tool_calls.append(
                {
                    'tool': 'task.create',
                    'result': {'task': self.serialize_task(task)},
                }
            )
            assistant_content = (
                f'{resolved_provider} 已识别任务意图并触发内部工具 `task.create`，'
                '我已把行动项放入任务收件箱。'
            )
        else:
            assistant_content = (
                f'{resolved_provider} 已接收请求。当前 2.0 工作台可继续使用任务、知识检索和审批流能力。'
            )

        assistant_message = ConversationMessage(
            thread_id=thread_id,
            role='assistant',
            provider=resolved_provider,
            content=assistant_content,
            payload={
                'provider_tier': resolved_profile.tier,
                'approval_requested': approval_requested,
                'routing_trace': routing_trace,
            },
        )
        session.add(assistant_message)
        session.add(
            ActivityEvent(
                thread_id=thread_id,
                event_type='chat.message.created',
                payload={'provider': resolved_provider},
            )
        )
        session.commit()
        session.refresh(assistant_message)
        if approval is not None:
            session.refresh(approval)

        return {
            'assistant': self.serialize_message(assistant_message),
            'approval_requested': approval is not None,
            'approval': self.serialize_approval(approval) if approval is not None else None,
            'tool_calls': tool_calls,
            'routing': {
                'requested_provider': provider,
                'resolved_provider': resolved_provider,
                'requires_external_write': requires_external_write,
                'lock_to_requested': lock_to_requested,
                'trace': routing_trace,
            },
        }

    def list_approvals(self, session: Session) -> list[dict[str, Any]]:
        rows = session.execute(
            select(ToolApproval).order_by(ToolApproval.created_at.desc())
        ).scalars().all()
        return [self.serialize_approval(row) for row in rows]

    def decide_approval(self, session: Session, approval_id: str, decision: str) -> tuple[ToolApproval, ActivityEvent]:
        approval = session.get(ToolApproval, approval_id)
        if approval is None:
            raise KeyError(f'Approval {approval_id} not found')

        normalized = decision.lower()
        if normalized not in {'approved', 'rejected'}:
            raise ValueError('decision must be approved or rejected')

        approval.status = normalized
        approval.decided_at = datetime.now(timezone.utc)
        event = ActivityEvent(
            thread_id=approval.thread_id,
            event_type=f'approval.{normalized}',
            payload={'tool_name': approval.tool_name, 'approval_id': approval.id},
        )
        session.add(event)
        session.commit()
        session.refresh(approval)
        session.refresh(event)
        return approval, event

    def ingest_knowledge(
        self,
        session: Session,
        title: str,
        content: str,
        source_type: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> KnowledgeAsset:
        asset = KnowledgeAsset(
            title=title,
            content=content,
            source_type=source_type,
            tags=tags,
            payload=metadata,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    def serialize_knowledge_asset(self, asset: KnowledgeAsset) -> dict[str, Any]:
        return {
            'id': asset.id,
            'title': asset.title,
            'source_type': asset.source_type,
            'tags': asset.tags,
            'retrieval_backend': asset.retrieval_backend,
            'created_at': asset.created_at.isoformat(),
        }

    def search_knowledge(self, session: Session, query: str, limit: int) -> list[dict[str, Any]]:
        query_lower = query.lower()
        rows = session.execute(select(KnowledgeAsset)).scalars().all()
        matches = []
        for row in rows:
            haystack = f'{row.title}\n{row.content}'.lower()
            if query_lower not in haystack:
                continue
            snippet = row.content[:160]
            matches.append(
                {
                    'id': row.id,
                    'title': row.title,
                    'snippet': snippet,
                    'tags': row.tags,
                    'source_type': row.source_type,
                }
            )
        return matches[:limit]

    def create_task(
        self,
        session: Session,
        title: str,
        description: str = '',
        source_thread_id: str | None = None,
        auto_commit: bool = True,
    ) -> Task:
        task = Task(title=title, description=description, source_thread_id=source_thread_id)
        session.add(task)
        session.add(
            ActivityEvent(
                thread_id=source_thread_id,
                event_type='task.created',
                payload={'title': title},
            )
        )
        session.flush()
        if auto_commit:
            session.commit()
            session.refresh(task)
        return task

    def serialize_task(self, task: Task) -> dict[str, Any]:
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'source_thread_id': task.source_thread_id,
            'metadata': task.payload,
            'created_at': task.created_at.isoformat(),
        }

    def read_resource(self, session: Session, uri: str) -> dict[str, Any]:
        if uri == 'lab://users/me':
            return {
                'uri': uri,
                'contents': {
                    'display_name': 'Lab Copilot Operator',
                    'active_mode': 'workspace',
                    'connected_accounts': self.list_external_accounts(session),
                    'providers': self.list_provider_payload(session),
                },
            }

        if uri == 'lab://calendar/upcoming':
            approved = [
                item for item in self.list_approvals(session)
                if item['tool_name'] == 'calendar.create_event' and item['status'] == 'approved'
            ]
            return {'uri': uri, 'contents': {'events': approved}}

        if uri == 'lab://providers/capabilities':
            return {'uri': uri, 'contents': {'providers': self.list_provider_payload(session)}}

        if uri == 'lab://approvals/pending':
            pending = [item for item in self.list_approvals(session) if item['status'] == 'pending']
            return {'uri': uri, 'contents': {'items': pending}}

        if uri.startswith('lab://threads/'):
            thread_id = uri.split('/')[-1]
            thread = self.get_thread(session, thread_id)
            messages = session.execute(
                select(ConversationMessage).where(ConversationMessage.thread_id == thread_id)
            ).scalars().all()
            return {
                'uri': uri,
                'contents': {
                    'thread': self.serialize_thread(thread),
                    'messages': [self.serialize_message(message) for message in messages],
                },
            }

        if uri.startswith('lab://tasks/'):
            task_id = uri.split('/')[-1]
            task = session.get(Task, task_id)
            if task is None:
                raise KeyError(f'Task {task_id} not found')
            return {'uri': uri, 'contents': self.serialize_task(task)}

        raise KeyError(f'Unsupported resource: {uri}')

    def call_tool(self, session: Session, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.mcp_registry.get_tool(name)

        if name == 'task.create':
            task = self.create_task(
                session,
                title=arguments.get('title', 'Untitled task'),
                description=arguments.get('description', ''),
                source_thread_id=arguments.get('thread_id'),
            )
            return {'tool': tool.name, 'result': {'task': self.serialize_task(task)}}

        if name == 'knowledge.search':
            limit = int(arguments.get('limit', 5))
            limit = max(1, min(limit, 20))
            items = self.search_knowledge(
                session,
                query=arguments.get('query', ''),
                limit=limit,
            )
            return {'tool': tool.name, 'result': {'items': items}}

        if name == 'approval.list_pending':
            pending = [item for item in self.list_approvals(session) if item['status'] == 'pending']
            return {'tool': tool.name, 'result': {'items': pending}}

        if name == 'calendar.create_event':
            if tool.requires_approval:
                approval = ToolApproval(
                    tool_name=tool.name,
                    provider=arguments.get('provider', 'openai'),
                    status='pending',
                    arguments=arguments,
                    rationale='Calendar event creation requires explicit approval.',
                )
                session.add(approval)
                session.commit()
                session.refresh(approval)
                return {
                    'tool': tool.name,
                    'approval_required': True,
                    'approval': self.serialize_approval(approval),
                }
            return {'tool': tool.name, 'result': arguments}

        if name == 'gmail.summarize_thread':
            return {
                'tool': tool.name,
                'result': {
                    'summary': 'Gmail thread summarization is scaffolded. Connect Google account to enable live reads.',
                    'connection_required': True,
                },
            }

        raise KeyError(f'Unsupported tool: {name}')
