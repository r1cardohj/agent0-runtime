"""Cumulative run usage and bounded observer-error bookkeeping."""

import asyncio
import unittest

from loop_fakes import ScriptedBackend, echo_call, echo_tool, echo_turn

from agent0_runtime import Agent, EventBus, RunStatus, ToolRegistry


class UsageTests(unittest.TestCase):
    def test_usage_is_summed_over_every_model_round(self):
        backend = ScriptedBackend(
            [
                echo_turn(usage={"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}),
                echo_turn(
                    text="done",
                    usage={"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
                ),
            ]
        )
        agent = Agent(backend, tools=ToolRegistry((echo_tool(),)), close_backend=False)

        result = asyncio.run(agent.run("go"))

        self.assertEqual(
            result.usage,
            {"prompt_tokens": 30, "completion_tokens": 7, "total_tokens": 37},
        )
        self.assertEqual(len(result.usage_by_turn), 2)
        self.assertEqual(result.usage_by_turn[1]["total_tokens"], 25)

    def test_blocked_run_still_reports_usage(self):
        backend = ScriptedBackend([echo_turn(usage={"total_tokens": 7})] * 3)
        agent = Agent(backend, tools=ToolRegistry((echo_tool(),)), close_backend=False)

        result = asyncio.run(agent.run("go", max_turns=2))

        self.assertEqual(result.status, RunStatus.BLOCKED)
        self.assertEqual(result.usage, {"total_tokens": 14})

    def test_a_run_without_usage_reports_none(self):
        backend = ScriptedBackend([echo_turn(text="done")])
        agent = Agent(backend, close_backend=False)

        result = asyncio.run(agent.run("go"))

        self.assertIsNone(result.usage)
        self.assertEqual(result.usage_by_turn, ())

    def test_echo_call_is_replayable(self):
        # Guards the shared fixture: the model call must answer with a tool message.
        backend = ScriptedBackend([echo_turn(), echo_turn(text="done")])
        agent = Agent(backend, tools=ToolRegistry((echo_tool(),)), close_backend=False)
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[2]["tool_call_id"], echo_call().id)


class ObserverErrorTests(unittest.TestCase):
    def test_errors_are_bounded_for_long_lived_buses(self):
        bus = EventBus(max_errors=2)

        def fail(_event):
            raise RuntimeError("observer failed")

        bus.subscribe(fail)
        emitter = bus.for_run("run-test")

        async def emit_many():
            for _ in range(5):
                await emitter.emit("text_delta", text="x")

        asyncio.run(emit_many())

        self.assertEqual(len(bus.errors), 2)
        self.assertEqual(str(bus.errors[0].error), "observer failed")


if __name__ == "__main__":
    unittest.main()
