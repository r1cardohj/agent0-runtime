"""Small fakes shared by loop-level tests that need a scripted backend."""

from agent0_runtime import ModelTurn, Tool, ToolCall


class ScriptedBackend:
    """Minimal backend protocol implementation returning a scripted turn list."""

    def __init__(self, script):
        self.script = list(script)

    async def complete(self, _request, _events):
        return self.script.pop(0)


def echo_tool():
    return Tool.define(
        "echo",
        "Return text",
        {"text": {"type": "string"}},
        lambda _context, args: args["text"],
        required=["text"],
    )


def echo_call(text: str = "hi") -> ToolCall:
    return ToolCall("call-1", "echo", f'{{"text":"{text}"}}')


def echo_turn(*, usage: dict[str, int] | None = None, text: str = "") -> ModelTurn:
    return ModelTurn(text=text, calls=[] if text else [echo_call()], usage=usage)
