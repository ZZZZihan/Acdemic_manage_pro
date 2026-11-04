from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from .db import Base, create_session_factory
from .mcp.registry import build_registry
from .schemas import (
    ApprovalDecisionRequest,
    CreateThreadRequest,
    KnowledgeAssetIngestRequest,
    McpResourceReadRequest,
    McpToolCallRequest,
    PostMessageRequest,
)
from .services import AppServices
from .providers import build_provider_registry


def default_database_url() -> str:
    return f"sqlite+pysqlite:///{Path(__file__).resolve().parents[1] / 'data-v2.sqlite'}"


def create_app(database_url: str | None = None, testing: bool = False) -> FastAPI:
    app = FastAPI(
        title='Academic Manage Pro 2.0',
        version='2.0.0',
        docs_url='/docs' if testing else '/docs',
    )

    engine, session_factory = create_session_factory(database_url or default_database_url())
    Base.metadata.create_all(bind=engine)

    services = AppServices(
        provider_registry=build_provider_registry(),
        mcp_registry=build_registry(),
    )
    with session_factory() as session:
        services.seed_defaults(session)

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.services = services

    def get_session(request: Request):
        session = request.app.state.session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_services(request: Request) -> AppServices:
        return request.app.state.services

    @app.get('/health')
    def health():
        return {'status': 'ok', 'version': '2.0.0'}

    @app.get('/api/v2/providers')
    def list_providers(
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        return {'providers': app_services.list_provider_payload(session)}

    @app.get('/api/v2/external-accounts')
    def list_external_accounts(
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        return {'items': app_services.list_external_accounts(session)}

    @app.get('/api/v2/user-context')
    def get_user_context(
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        return app_services.read_resource(session, 'lab://users/me')

    @app.get('/api/v2/interview/architecture')
    def interview_architecture():
        return {
            'project_version': '2.0.0',
            'highlights': [
                'dual_core_orchestration',
                'mcp_capability_plane',
                'approval_control_plane',
                'provider_routing_trace',
                'local_privacy_fallback',
            ],
            'layers': [
                'workspace_ui',
                'api_v2_orchestration',
                'mcp_tools_resources_prompts',
                'providers_and_retrieval',
                'audit_and_approvals',
            ],
        }

    @app.post('/api/v2/chat/threads', status_code=201)
    def create_thread(
        body: CreateThreadRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        thread = app_services.create_thread(session, body.title)
        return {'thread': app_services.serialize_thread(thread)}

    @app.get('/api/v2/chat/threads/{thread_id}')
    def get_thread(
        thread_id: str,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        try:
            payload = app_services.read_resource(session, f'lab://threads/{thread_id}')
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return payload

    @app.post('/api/v2/chat/messages')
    def post_message(
        body: PostMessageRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        try:
            result = app_services.post_message(
                session,
                thread_id=body.thread_id,
                provider=body.provider,
                content=body.content,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return result

    @app.get('/api/v2/approvals')
    def list_approvals(
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        return {'items': app_services.list_approvals(session)}

    @app.post('/api/v2/approvals/{approval_id}/decision')
    def decide_approval(
        approval_id: str,
        body: ApprovalDecisionRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        try:
            approval, activity = app_services.decide_approval(session, approval_id, body.decision)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            'approval': app_services.serialize_approval(approval),
            'activity': app_services.serialize_activity(activity),
        }

    @app.post('/api/v2/knowledge/assets', status_code=201)
    def ingest_knowledge(
        body: KnowledgeAssetIngestRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        asset = app_services.ingest_knowledge(
            session,
            title=body.title,
            content=body.content,
            source_type=body.source_type,
            tags=body.tags,
            metadata=body.metadata,
        )
        return {'asset': app_services.serialize_knowledge_asset(asset)}

    @app.get('/mcp')
    def mcp_manifest(app_services: AppServices = Depends(get_services)):
        return app_services.mcp_registry.manifest()

    @app.post('/mcp/resources/read')
    def read_resource(
        body: McpResourceReadRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        try:
            resource = app_services.read_resource(session, body.uri)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {'resource': {'uri': resource['uri']}, 'contents': resource['contents']}

    @app.post('/mcp/tools/call')
    def call_tool(
        body: McpToolCallRequest,
        session: Session = Depends(get_session),
        app_services: AppServices = Depends(get_services),
    ):
        try:
            return app_services.call_tool(session, body.name, body.arguments)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
