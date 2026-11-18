"""The standalone, embeddable agent0 runtime.

The backend/tool protocols, structured events, sessions, lifecycle, and plugins
are independent of terminal interfaces and application-owned policy.
"""

import logging

__version__ = "0.1.1"

from .backend import BackendRegistry, ModelBackend, ModelInfo, ModelRequest
from .builtin_tools import (
    BUILTIN_TOOL_SCHEMAS,
    BuiltinToolsConfig,
    create_builtin_registry,
)
from .capabilities import MODEL_CAPABILITIES, ModelCapability
from .client import (
    OpenAIClient,
    OpenAISyncClient,
    make_openai_client,
    make_openai_sync_client,
)
from .credentials import FileCredentialStore
from .events import (
    EventBus,
    EventEmitter,
    EventListener,
    ListenerError,
    RuntimeEvent,
    RuntimeEventKind,
)
from .filesystem import ImageReader, VisionSupport, WorkspacePolicy
from .history import ResponsesHistoryPolicy
from .images import PillowImageReader, supports_vision
from .lifecycle import (
    LifecycleContext,
    LifecycleEvent,
    LifecycleHooks,
    LifecycleKind,
    LifecycleListenerError,
    emit_lifecycle,
    run_with_lifecycle,
)
from .loop import DEFAULT_MAX_TURNS, Agent, HistoryPolicy
from .managed import ManagedProvider
from .openai_backend import OpenAIResponsesBackend
from .plugins import (
    PLUGIN_API_VERSION,
    PLUGIN_ENTRY_POINT,
    Plugin,
    PluginContext,
    PluginError,
    PluginInfo,
    PluginManager,
    discover_plugins,
)
from .providers import (
    BUILTIN_PROVIDERS,
    Credential,
    ProviderSpec,
    default_model_for,
    get_provider,
    list_providers,
    resolve_all_env,
)
from .routing import AUTO_REF, FailoverRoute, RouteSelection, RouteTarget, build_auto_route
from .routing_backend import RoutedResponsesBackend, stream_response_failover
from .search import SearchProvider
from .session import MemorySessionStore, RunContext, RuntimeSession, SessionStore
from .shell import Shell
from .tools import (
    DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    Tool,
    ToolContext,
    ToolExecution,
    ToolExecutor,
    ToolRegistry,
    tool,
)
from .types import (
    TOOL_ATTACHMENTS_KEY,
    AgentInterrupted,
    Attachment,
    CancellationToken,
    GenerationConfig,
    Message,
    ModelTurn,
    Recovery,
    RunResult,
    RunStatus,
    ToolCall,
    ToolResult,
    new_run_id,
)
from .web_search import DeepSeekSearchProvider

# Library default: stay silent unless the embedding application configures
# logging for the "agent0_runtime" logger tree.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "Agent",
    "AgentInterrupted",
    "Attachment",
    "AUTO_REF",
    "BackendRegistry",
    "BUILTIN_PROVIDERS",
    "BUILTIN_TOOL_SCHEMAS",
    "BuiltinToolsConfig",
    "CancellationToken",
    "Credential",
    "DEFAULT_MAX_TURNS",
    "DEFAULT_MAX_TOOL_OUTPUT_CHARS",
    "DeepSeekSearchProvider",
    "EventBus",
    "EventEmitter",
    "EventListener",
    "FileCredentialStore",
    "FailoverRoute",
    "GenerationConfig",
    "HistoryPolicy",
    "ImageReader",
    "OpenAIResponsesBackend",
    "OpenAIClient",
    "OpenAISyncClient",
    "LifecycleContext",
    "LifecycleEvent",
    "LifecycleHooks",
    "LifecycleKind",
    "LifecycleListenerError",
    "ListenerError",
    "Message",
    "ModelBackend",
    "ModelCapability",
    "MODEL_CAPABILITIES",
    "ModelInfo",
    "ModelRequest",
    "MemorySessionStore",
    "ManagedProvider",
    "ModelTurn",
    "PLUGIN_API_VERSION",
    "PLUGIN_ENTRY_POINT",
    "Plugin",
    "ProviderSpec",
    "PluginContext",
    "PluginError",
    "PluginInfo",
    "PluginManager",
    "PillowImageReader",
    "Recovery",
    "RunContext",
    "RunResult",
    "RunStatus",
    "ResponsesHistoryPolicy",
    "RouteSelection",
    "RouteTarget",
    "RoutedResponsesBackend",
    "RuntimeEvent",
    "RuntimeEventKind",
    "RuntimeSession",
    "TOOL_ATTACHMENTS_KEY",
    "SearchProvider",
    "SessionStore",
    "Shell",
    "Tool",
    "ToolCall",
    "ToolContext",
    "ToolExecution",
    "ToolExecutor",
    "ToolRegistry",
    "ToolResult",
    "VisionSupport",
    "WorkspacePolicy",
    "build_auto_route",
    "create_builtin_registry",
    "default_model_for",
    "discover_plugins",
    "emit_lifecycle",
    "get_provider",
    "list_providers",
    "make_openai_client",
    "make_openai_sync_client",
    "new_run_id",
    "resolve_all_env",
    "run_with_lifecycle",
    "stream_response_failover",
    "supports_vision",
    "tool",
]
