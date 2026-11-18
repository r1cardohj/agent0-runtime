# Headless runtime and plugin API

`agent0_runtime` is a standalone headless runtime for embedding applications. It
has no imports from terminal UIs, host providers, or application-owned session
storage. It contains the generic loop plus optional built-in filesystem/shell/web
tools that applications can select without importing a particular coding product.

## Quick start

The recommended construction path is `Agent.from_env()`. It discovers a configured
DeepSeek or Kimi credential, selects that provider's default model, and installs
the matching Responses backend and history policy:

```python
import asyncio
from agent0_runtime import Agent, tool

@tool("add")
def add(a: float, b: float) -> str:
    """Add two numbers."""
    return str(a + b)

async def main():
    async with Agent.from_env(tools=["add"]) as agent:
        result = await agent.run("Use add to calculate 20 + 22.")
        print(result.text)

asyncio.run(main())
```

Set `DEEPSEEK_API_KEY` or `KIMI_API_KEY` before running. With both configured,
pass an explicit reference such as `Agent.from_env("kimi/kimi-for-coding")`.
`AGENT0_MODEL` supplies the same default reference, and `AGENT0_BASE_URL` overrides
the endpoint. No tools are enabled unless supplied. The executable version of this
example is `examples/minimal_agent.py`.

A run without a session is independent. Reuse a `RuntimeSession` for conversation
history, as shown below. Entering the async context and exiting it closes plugins,
the backend, and its network client; no separate client cleanup is required.

## Typed runs and structured events

Ordinary embedders should prefer `Agent.from_env()`. Applications that already own
an OpenAI-compatible client and route objects can assemble the same typed loop
without transferring resource ownership:

```python
from agent0_runtime import OpenAIResponsesBackend, ResponsesHistoryPolicy, Agent

backend = OpenAIResponsesBackend(
    client,
    "deepseek-flash",
    provider_id="deepseek",
    context_limit=128_000,
)
agent = Agent(
    backend,
    history=ResponsesHistoryPolicy(),
    tools=registry,
    close_backend=False,  # the host keeps ownership of its client
)
result = await agent.run("fix the tests", cwd=workspace, messages=messages)

if result.stop_reason == "max_turns":
    show_blocked(result.turns)
else:
    show_answer(result.text)
await agent.close()
```

`RunResult` contains `status`, `text`, `turns`, `run_id`, `finish_reason`,
`stop_reason`, and `usage`, which is summed over every model round in the run;
`usage_by_turn` keeps the per-round detail in order. Interruption and backend
failures are still exceptions, with corresponding terminal events emitted first.

Each `RuntimeEvent` has a `kind`, per-run sequence number, `run_id`, timestamp,
optional model-turn number, and a transport-safe payload. Event kinds cover
model/text/reasoning deltas, routing, usage, compaction, tool start/preview/end,
and terminal turn states. `event.to_dict()` is suitable for a future JSON-RPC or
WebSocket adapter. `on_event` may be synchronous or asynchronous.

Observer failures never break a run: they go to the `agent0_runtime` logger and to
a bounded `EventBus.errors` deque (`max_errors`, default 100), so a long-lived
agent cannot accumulate them without limit. The runtime logs retries, failovers,
compaction, and tool failures to the same logger tree and installs a
`NullHandler`, so hosts see nothing until they configure logging.

For custom backends, instantiate `agent0_runtime.Agent` directly. The required
backend protocol is only `complete(request, events) -> ModelTurn`; `model`,
`provider_id`, `context_limit`, and `prepare()` are optional metadata/policy.
An owned backend may implement `close()` or `aclose()` to release resources:

```python
class Backend:
    async def complete(self, request, events) -> ModelTurn:
        ...
```

The runtime owns the model integration layer and normally depends on the
`openai` package. `agent0_runtime.OpenAIResponsesBackend` implements one
OpenAI-compatible Responses endpoint, including streaming, function calls,
usage mapping, retry-safe requests, raw Responses history, and client cleanup.
The runtime owns provider metadata, configurable clients, credential storage,
model discovery, and `RoutedResponsesBackend` intent/failover. Embedding
applications inject their credential store, client identity, and provider
selection; other applications can use the default provider registry, their own
router, or a different backend entirely.

`Agent(backend)` owns and closes its backend by default. Pass
`close_backend=False` when a host shares that backend or its network client across
runs. `Agent.close()` and async-context exit are idempotent.

Hosts that already own an OpenAI-compatible client should use the same default
assembly as `from_env()` without transferring client ownership:

```python
agent = Agent.from_openai(
    client,
    model,
    provider_id=provider_id,
    context_limit=context_limit,
    tools=registry,
)
```

This factory installs `OpenAIResponsesBackend` and `ResponsesHistoryPolicy`.
It defaults to `close_backend=False`; the host remains responsible for closing
the injected client.

## Generation settings

`GenerationConfig` carries per-run or per-backend sampling and output settings.
Every field is optional, so one backend default can be overridden per run:

```python
from agent0_runtime import Agent, GenerationConfig

agent = Agent.from_openai(
    client,
    "deepseek-chat",
    generation=GenerationConfig(temperature=0.2, max_output_tokens=4096),
)
result = await agent.run("summarize this", generation=GenerationConfig(temperature=0.0))
```

The run config is merged over the backend default: here `temperature=0.0` wins and
`max_output_tokens=4096` is inherited. Unset fields are not sent at all. `extra`
is merged last and verbatim, so provider-specific parameters (for example a
`text` format object) reach the request without growing the neutral field list.
A backend that does not understand generation settings may ignore them; the
protocol still requires only `complete()`.

## Tool registry

`@tool` derives names, JSON schemas, required arguments, and descriptions from a
Python signature and docstring. It works bare as `@tool`, as `@tool("name")`,
and configured as `@tool(name="...", description="...")`; synchronous and
asynchronous functions are supported. Common scalar, list, dictionary, literal,
and optional annotations are supported. Defaults become optional tool arguments.
The decorated value remains the original Python function, so tests and normal
calls can use it unchanged.

`Agent.from_env()` may receive decorated tool names such as `tools=["add"]`. The
constructor reflects the calling scope and resolves uniquely named tools. No
process-global registry is created; an ambiguous or invisible name raises a
clear error. Function objects remain the best choice for dynamically generated
or shadowed tools. Use `Tool.define()` when a tool needs an explicit schema or
`ToolContext`:

```python
from agent0_runtime import Agent, OpenAIResponsesBackend, Tool, create_builtin_registry

registry = create_builtin_registry()
registry.register(
    Tool.define(
        "echo",
        "Return text",
        {"text": {"type": "string"}},
        lambda context, args: args["text"],
        required=["text"],
    )
)

backend = OpenAIResponsesBackend(client, "model")
agent = Agent(backend, tools=registry, close_backend=False)
result = await agent.run("try echo", cwd=workspace, messages=[])
await agent.close()
```

Handlers receive a `ToolContext` and a decoded argument dictionary. They may be
synchronous or asynchronous and return `str` or `ToolResult`. Synchronous
handlers run in a worker thread so they do not block the event loop.

`Agent(tool_timeout=..., max_tool_output_chars=...)` bounds one handler call and
caps what enters history, so a hung or chatty tool cannot stall a run or blow up
the next prompt. Defaults: no timeout, 64,000 characters per result. A timed-out
handler returns `error: <name> timed out after Ns`; an oversized result is
truncated with a `[truncated N chars]` marker. Attachments and private state
survive truncation. Pass `None` to disable either limit.

## Generic built-in tools

The runtime includes provider-neutral `read`, `write`, `edit`, `bash`, `fetch`,
and `search` definitions. Optional behavior is injected rather than imported:

```python
from agent0_runtime import BuiltinToolsConfig, create_builtin_registry, Shell

registry = create_builtin_registry(
    BuiltinToolsConfig(
        shell=Shell("bash", ("/bin/bash", "-lc")),
        search_provider=my_search_provider,  # any SearchProvider
    )
)
agent = Agent(backend, tools=registry)
```

The runtime ships `PillowImageReader` and `DeepSeekSearchProvider`; hosts may inject
credential resolvers or alternative implementations. Filesystem/shell tools require
a workspace only when selected by the model, so an assistant with no workspace can
still use its own tools. Hosts supply their own credential resolvers without
implementing the search transport itself.

`PillowImageReader` needs the `images` extra and `fetch` needs the `web` extra;
without them the tool returns an install hint instead of failing at import.
`search` uses only the standard library.

### Workspace policy

`WorkspacePolicy` confines the filesystem tools to one root and can make it
read-only. It is injected through `BuiltinToolsConfig`, so a host never has to
fork the tools to sandbox them:

```python
from pathlib import Path
from agent0_runtime import BuiltinToolsConfig, WorkspacePolicy, create_builtin_registry

registry = create_builtin_registry(
    BuiltinToolsConfig(policy=WorkspacePolicy(root=Path("/srv/workspace"), read_only=True))
)
```

Paths are resolved through symlinks and refused when they leave the root, so
`../secrets` and `/etc/passwd` become `error: path escapes the workspace` tool
results. `read_only=True` rejects `write`/`edit` and disables `bash` in the
registry. `allow_outside=True` opts back into unrestricted paths.

`bash` runs in the host process and is **not** confined by this policy: use a
container or an OS sandbox when shell confinement matters. Without a policy the
tools keep their previous permissive behaviour.

## Sessions and stores

The core models only portable runtime state:

```python
from agent0_runtime import MemorySessionStore, RuntimeSession

session = RuntimeSession(
    id="assistant-1",
    messages=[],
    metadata={"persona": "general assistant"},
)
result = await agent.run("hello", session=session)
```

`RuntimeSession` contains an ID, message history, and application metadata.
`SessionStore` is the portable persistence contract; `MemorySessionStore` supports
tests and ephemeral agents. Hosts own durable formats, paths, migration, and
retention policies behind the portable `SessionStore` contract.

For explicit per-run state, use `RunContext` and `Agent.run_in_context()`. The
legacy `cwd` parameter is the filesystem spelling of the optional run workspace;
neither is required for a non-filesystem agent.

## Cancellation

A host can cancel its asyncio task for immediate network-stream cancellation,
or pass a `CancellationToken` for cooperative cancellation:

```python
from agent0_runtime import CancellationToken

token = CancellationToken()
result_task = asyncio.create_task(agent.run(..., cancellation=token))
token.cancel("window closed")
await result_task  # raises AgentInterrupted
```

Tokens are checked between runtime boundaries and tools. A token cannot kill an
arbitrary synchronous plugin already running in a worker thread. On interruption,
all unanswered model tool calls receive an `error: interrupted` tool message so
history remains replayable.

## Lifecycle hooks

`LifecycleHooks` provides ordered, synchronous, read-only observers for session
and turn boundaries. `subscribe()` returns an unsubscribe callback. Observer
failures are isolated and recorded in `hooks.errors`; an optional `on_error`
callback can forward them to a host logger.

Lifecycle events distinguish the real `session_id` from `workspace_id`, and turn
events include the matching `run_id`. Terminal signal handling belongs to the
host; outcome classification lives in
`agent0_runtime.lifecycle.run_with_lifecycle`.

## Plugins

A plugin registers tools, backend factories, or observers during setup:

```python
class MyPlugin:
    api_version = 1

    def register(self, context):
        context.tools.register(make_my_tool())
        context.events.subscribe(log_event, kinds=["tool_finished"])

    async def close(self):  # optional
        ...
```

Load trusted objects directly with `Agent(..., plugins=[MyPlugin()])`.

Installed distributions can advertise an entry point:

```toml
[project.entry-points."agent0.plugins"]
my_plugin = "my_package:MyPlugin"
```

Discovery only reads metadata. Code is imported solely for names explicitly
passed as `plugin_names`:

```python
result = await agent.run(...)
# Construct Agent(..., plugin_names=["my_plugin"]) to load named entry points.
```

There is deliberately no implicit load-all behavior. Python plugins have the
current user's full privileges and are not sandboxed. The first API supports
registration and orderly cleanup, not hot reload, arbitrary mutation of the
loop, or UI-specific hooks.
