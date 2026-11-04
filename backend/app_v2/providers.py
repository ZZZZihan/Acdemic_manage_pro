from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProviderProfileSpec:
    name: str
    tier: str
    default_model: str
    local_only: bool
    supports_tools: bool
    supports_external_write: bool
    supports_google_connectors: bool
    description: str


class BaseProviderAdapter:
    def __init__(self, profile: ProviderProfileSpec):
        self.profile = profile

    def build_payload(self, messages: List[dict], tools: List[dict]) -> dict:
        raise NotImplementedError


class OpenAIAdapter(BaseProviderAdapter):
    def build_payload(self, messages: List[dict], tools: List[dict]) -> dict:
        return {
            'model': os.environ.get('OPENAI_MODEL', self.profile.default_model),
            'input': messages,
            'tools': tools,
            'store': False,
        }


class ClaudeAdapter(BaseProviderAdapter):
    def build_payload(self, messages: List[dict], tools: List[dict]) -> dict:
        return {
            'model': os.environ.get('CLAUDE_MODEL', self.profile.default_model),
            'messages': messages,
            'tools': tools,
            'max_tokens': 1024,
        }


class ChatCompletionsAdapter(BaseProviderAdapter):
    def build_payload(self, messages: List[dict], tools: List[dict]) -> dict:
        return {
            'model': self.profile.default_model,
            'messages': messages,
            'tools': tools,
        }


class OllamaAdapter(BaseProviderAdapter):
    def build_payload(self, messages: List[dict], tools: List[dict]) -> dict:
        return {
            'model': os.environ.get('OLLAMA_MODEL', self.profile.default_model),
            'messages': messages,
            'tools': tools,
            'format': {
                'type': 'json_schema',
                'json_schema': {
                    'name': 'assistant_response',
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'summary': {'type': 'string'},
                        },
                        'required': ['summary'],
                    },
                },
            },
        }


class ProviderRegistry:
    def __init__(self, profiles: List[ProviderProfileSpec], adapters: Dict[str, BaseProviderAdapter]):
        self._profiles = {profile.name: profile for profile in profiles}
        self._adapters = adapters

    def list(self) -> List[ProviderProfileSpec]:
        return [self._profiles[name] for name in ['openai', 'claude', 'deepseek', 'minimax', 'ollama']]

    def get(self, name: str) -> ProviderProfileSpec:
        profile = self._profiles.get(name)
        if profile is None:
            raise ValueError(f'Unsupported provider: {name}')
        return profile

    def get_adapter(self, name: str) -> BaseProviderAdapter:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise ValueError(f'Unsupported provider adapter: {name}')
        return adapter

    def names(self) -> List[str]:
        return ['openai', 'claude', 'deepseek', 'minimax', 'ollama']


def build_execution_chain(
    requested_provider: str,
    registry: ProviderRegistry,
    requires_external_write: bool,
    lock_to_requested: bool,
) -> List[str]:
    ordered = registry.names()
    if lock_to_requested:
        return [requested_provider] + [name for name in ordered if name != requested_provider]

    chain: List[str] = []

    requested_profile = registry.get(requested_provider)
    if not requires_external_write or requested_profile.supports_external_write:
        chain.append(requested_provider)

    if requires_external_write:
        for provider_name in ('openai', 'claude'):
            profile = registry.get(provider_name)
            if profile.supports_external_write and provider_name not in chain:
                chain.append(provider_name)

    if requested_provider not in chain:
        chain.append(requested_provider)

    for provider_name in ordered:
        if provider_name not in chain:
            chain.append(provider_name)
    return chain


def build_provider_registry() -> ProviderRegistry:
    profiles = [
        ProviderProfileSpec(
            name='openai',
            tier='A',
            default_model='gpt-5',
            local_only=False,
            supports_tools=True,
            supports_external_write=True,
            supports_google_connectors=True,
            description='Primary orchestration provider for high-risk workflows.',
        ),
        ProviderProfileSpec(
            name='claude',
            tier='A',
            default_model='claude-sonnet-4-5',
            local_only=False,
            supports_tools=True,
            supports_external_write=True,
            supports_google_connectors=True,
            description='Second core orchestrator for long-context planning and approvals.',
        ),
        ProviderProfileSpec(
            name='deepseek',
            tier='B',
            default_model='deepseek-chat',
            local_only=False,
            supports_tools=True,
            supports_external_write=False,
            supports_google_connectors=True,
            description='General chat, RAG, and internal tool use.',
        ),
        ProviderProfileSpec(
            name='minimax',
            tier='B',
            default_model='MiniMax-M1',
            local_only=False,
            supports_tools=True,
            supports_external_write=False,
            supports_google_connectors=True,
            description='General chat, RAG, and internal tool use.',
        ),
        ProviderProfileSpec(
            name='ollama',
            tier='C',
            default_model='qwen3:8b',
            local_only=True,
            supports_tools=True,
            supports_external_write=False,
            supports_google_connectors=False,
            description='Local-only fallback for private and offline workloads.',
        ),
    ]
    adapters = {
        'openai': OpenAIAdapter(profiles[0]),
        'claude': ClaudeAdapter(profiles[1]),
        'deepseek': ChatCompletionsAdapter(profiles[2]),
        'minimax': ChatCompletionsAdapter(profiles[3]),
        'ollama': OllamaAdapter(profiles[4]),
    }
    return ProviderRegistry(profiles=profiles, adapters=adapters)
