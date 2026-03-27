from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    requires_approval: bool


@dataclass(frozen=True)
class ResourceSpec:
    uri: str
    description: str


@dataclass(frozen=True)
class PromptSpec:
    name: str
    description: str


class McpRegistry:
    def __init__(self, tools: List[ToolSpec], resources: List[ResourceSpec], prompts: List[PromptSpec]):
        self._tools: Dict[str, ToolSpec] = {tool.name: tool for tool in tools}
        self._resources = resources
        self._prompts = prompts

    def manifest(self) -> dict:
        return {
            'tools': [asdict(tool) for tool in self._tools.values()],
            'resources': [asdict(resource) for resource in self._resources],
            'prompts': [asdict(prompt) for prompt in self._prompts],
        }

    def get_tool(self, name: str) -> ToolSpec:
        return self._tools[name]


def build_registry() -> McpRegistry:
    tools = [
        ToolSpec(name='task.create', description='Create a task in the workspace inbox.', requires_approval=False),
        ToolSpec(name='knowledge.search', description='Search ingested knowledge assets and return citations.', requires_approval=False),
        ToolSpec(name='calendar.create_event', description='Create a Google Calendar event.', requires_approval=True),
        ToolSpec(name='gmail.summarize_thread', description='Summarize a Gmail thread into workspace context.', requires_approval=False),
        ToolSpec(name='approval.list_pending', description='List pending approval requests.', requires_approval=False),
    ]
    resources = [
        ResourceSpec(uri='lab://users/me', description='Current workspace user context and connected systems.'),
        ResourceSpec(uri='lab://calendar/upcoming', description='Upcoming approved calendar events.'),
        ResourceSpec(uri='lab://providers/capabilities', description='Capability matrix for all configured providers.'),
        ResourceSpec(uri='lab://approvals/pending', description='Pending approval requests.'),
        ResourceSpec(uri='lab://threads/{id}', description='Conversation thread history.'),
        ResourceSpec(uri='lab://tasks/{id}', description='Task details.'),
    ]
    prompts = [
        PromptSpec(name='meeting.plan', description='Plan a meeting, create approvals, and capture follow-up tasks.'),
        PromptSpec(name='weekly.review', description='Review tasks, approvals, and knowledge for the week.'),
        PromptSpec(name='mail.to.tasks', description='Turn a Gmail thread into structured action items.'),
    ]
    return McpRegistry(tools=tools, resources=resources, prompts=prompts)
