# agent0-runtime

A small, headless, embeddable agent runtime for Python. It provides the model/tool
loop, OpenAI-compatible Responses backends, tools, sessions, structured events,
cancellation, lifecycle hooks, and plugins. Terminal UI, persistence formats, and
application policy belong to consumers.

## Install

```bash
python -m pip install agent0-runtime
```

Python 3.10 through 3.13 are supported. The package is typed and ships `py.typed`.

## Minimal agent

Set `DEEPSEEK_API_KEY` or `KIMI_API_KEY`, then run:

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

`Agent.from_env()` creates and owns the provider client, backend, and matching history
policy. Exiting the async context closes plugins and network resources. Pass an explicit
`provider/model` when more than one provider is configured.

Hosts with an existing OpenAI-compatible client can share the same backend/history
assembly without transferring ownership:

```python
from agent0_runtime import Agent

agent = Agent.from_openai(client, model, provider_id=provider_id, tools=registry)
```

The runtime also includes provider-neutral built-in tools for filesystem, shell, fetch,
and search. Optional behavior is injected through `BuiltinToolsConfig`; hosts provide
workspace policy, credentials, persistence, and UI.

## Documentation

- [Embedding guide](docs/runtime.md)
- [Minimal example](examples/minimal_agent.py)
- [Changelog](CHANGELOG.md)

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip install ruff==0.12.12 build twine
ruff check .
ruff format --check .
python -m build
python -m twine check --strict dist/*
```

## License

[MIT](LICENSE)
