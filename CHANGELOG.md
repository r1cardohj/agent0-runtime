# Changelog

## Unreleased

### Added

- `Agent.run(system=...)` (and `run_in_context`) writes the conversation's system
  prompt: it lands in `messages[0]`, older system messages are removed so exactly
  one remains, and later runs of that session keep it. There is no Agent-level
  prompt, so an omitted `system` never touches a conversation's own prompt.
- `PluginContext.prompts` (`PromptFragments.add(text)`) lets a plugin contribute
  prompt guidance without replacing the host's prompt. Fragments are joined in
  registration order when the runtime writes a conversation's prompt and are
  never written into a conversation that already has one; that case logs a
  warning instead of rewriting history.
- A conversation whose system messages are not `[messages[0]]` logs a warning
  naming the positions: adapters send the last one while compaction protects only
  index 0, so the runtime reports the deviation instead of silently normalizing.

## 0.1.1

### Added

- `GenerationConfig` (temperature, max output tokens, tool choice, parallel tool
  calls, and a verbatim `extra` escape hatch) for per-run and per-backend
  sampling settings; `Agent.run(generation=...)` overrides a backend default.
- `RunResult.usage_by_turn`, the per-round usage detail behind the run total.
- `WorkspacePolicy` confines `read`/`write`/`edit` to one root (symlink-aware),
  supports a read-only workspace that also disables `bash`, and is injected
  through `BuiltinToolsConfig(policy=...)`.
- `Agent(tool_timeout=..., max_tool_output_chars=...)` bounds one tool call and
  caps tool output before it enters history.
- Stdlib logging under the `agent0_runtime` logger with a `NullHandler`: retries,
  failover, compaction, observer, and tool failures are reported without any host
  configuration.

### Changed

- `RunResult.usage` is summed over every model round instead of reporting the
  latest round only, so a host can report one cost per run.
- Only `openai` is a required dependency. Pillow moved to the `images` extra;
  trafilatura, urllib3, and certifi moved to the `web` extra; `pip install
  "agent0-runtime[all]"` restores the previous install footprint. Missing extras
  surface as an install hint on the tool that needs them, never as an import
  failure.
- `EventBus.errors` is a bounded deque (`max_errors=100`) instead of an unbounded
  list.

## 0.1.0

- Initial standalone release of the headless agent runtime.
- Provides the model/tool loop, OpenAI-compatible Responses backend, typed events,
  lifecycle hooks, sessions, cancellation, plugins, provider clients, and generic
  filesystem/shell/web tools.
- Applications own their terminal UI, persistence formats, credentials paths, and
  product-specific recovery guidance.
