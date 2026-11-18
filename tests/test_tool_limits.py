"""Tool execution guards: timeout, output cap, and attachments after truncation."""

import asyncio
import unittest

from loop_fakes import ScriptedBackend

from agent0_runtime import Agent, Attachment, ModelTurn, Tool, ToolCall, ToolRegistry, ToolResult


def call_turn(name: str, arguments: str = '{"text":"hi"}') -> ModelTurn:
    return ModelTurn(calls=[ToolCall("call-1", name, arguments)])


class ToolLimitTests(unittest.TestCase):
    def _agent(self, handler, **options):
        tool = Tool.define(
            "slow", "Do work", {"text": {"type": "string"}}, handler, required=["text"]
        )
        backend = ScriptedBackend([call_turn("slow"), ModelTurn(text="done")])
        return Agent(backend, tools=ToolRegistry((tool,)), close_backend=False, **options)

    def test_a_hanging_handler_becomes_a_tool_error(self):
        async def handler(_context, _args):
            await asyncio.sleep(5)
            return "never"

        agent = self._agent(handler, tool_timeout=0.01)
        messages = []

        result = asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(result.text, "done")
        self.assertIn("slow timed out after 0.01s", messages[2]["content"])

    def test_tool_output_is_capped_before_it_enters_history(self):
        def handler(_context, _args):
            return "x" * 500

        agent = self._agent(handler, max_tool_output_chars=100)
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        marker = "\n...[truncated 400 chars]"
        self.assertTrue(messages[2]["content"].endswith(marker))
        self.assertEqual(len(messages[2]["content"]), 100 + len(marker))

    def test_truncation_keeps_attachments(self):
        attachment = Attachment(data="QUJD", mime_type="image/png")

        def handler(_context, _args):
            return ToolResult("y" * 50, attachments=(attachment,))

        agent = self._agent(handler, max_tool_output_chars=10)
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[2]["_attachments"][0]["mime_type"], "image/png")
        self.assertTrue(messages[2]["content"].startswith("y" * 10))

    def test_limits_can_be_disabled(self):
        def handler(_context, _args):
            return "z" * 500

        agent = self._agent(handler, max_tool_output_chars=None, tool_timeout=None)
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[2]["content"], "z" * 500)


if __name__ == "__main__":
    unittest.main()
