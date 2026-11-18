# Changelog

## Unreleased

### Added

- `GenerationConfig` (temperature, max output tokens, tool choice, parallel tool
  calls, and a verbatim `extra` escape hatch) for per-run and per-backend
  sampling settings; `Agent.run(generation=...)` overrides a backend default.
- `RunResult.usage` now sums every model round in the run, with the per-round
  detail in `RunResult.usage_by_turn`.
- `WorkspacePolicy` confines `read`/`write`/`edit` to one root (symlink-aware),
  supports a read-only workspace that also disables `bash`, and is injected
  through `BuiltinToolsConfig(policy=...)`.
- `Agent(tool_timeout=..., max_tool_output_chars=...)` bounds one tool call and
  caps tool output before it enters history.
- Stdlib logging under the `agent0_runtime` logger with a `NullHandler`: retries,
  failover, compaction, observer, and tool failures are reported without any host
  configuration.

### Changed

- Only `openai` is a required dependency. Pillow moved to the `images` extra;
  trafilatura, urllib3, and certifi moved to the `web` extra; `all` installs
  every optional capability. Missing extras surface as an install hint on the
  tool that needs them, never as an import failure.
- `EventBus.errors` is a bounded deque (`max_errors=100`) instead of an unbounded
  list.

## 0.1.0

- Initial standalone release of the headless agent runtime.
- Provides the model/tool loop, OpenAI-compatible Responses backend, typed events,
  lifecycle hooks, sessions, cancellation, plugins, provider clients, and generic
  filesystem/shell/web tools.
- Applications own their terminal UI, persistence formats, credentials paths, and
  product-specific recovery guidance.
