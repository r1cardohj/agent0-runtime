"""System prompts: a conversation's first message, with a default and a per-run override."""

import asyncio
import unittest

from agent0_runtime import Agent, ModelTurn, RunContext, RuntimeSession
from agent0_runtime.openai_backend import completion_kwargs


class RecordingBackend:
    """Record every request and answer with one scripted text turn."""

    model = "fake-model"
    provider_id = "fake"
    context_limit = None

    def __init__(self, text: str = "done") -> None:
        self.text = text
        self.requests = []

    async def complete(self, request, _events):
        self.requests.append(request)
        return ModelTurn(text=self.text)


def system_of(messages) -> list[dict]:
    return [message for message in messages if message.get("role") == "system"]


class SystemPromptOverrideTests(unittest.TestCase):
    def _run(self, backend, messages, **kwargs):
        return asyncio.run(
            Agent(backend, close_backend=False).run("go", messages=messages, **kwargs)
        )

    def test_empty_messages_get_the_prompt_first(self) -> None:
        backend = RecordingBackend()
        messages = []

        self._run(backend, messages, system="You are terse.")

        self.assertEqual(messages[0], {"role": "system", "content": "You are terse."})
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant"])

    def test_an_existing_prompt_is_replaced(self) -> None:
        backend = RecordingBackend()
        messages = [
            {"role": "system", "content": "old prompt"},
            {"role": "user", "content": "earlier"},
        ]

        self._run(backend, messages, system="new prompt")

        self.assertEqual(system_of(messages), [{"role": "system", "content": "new prompt"}])
        self.assertEqual(messages[1], {"role": "user", "content": "earlier"})

    def test_duplicate_prompts_collapse_to_one(self) -> None:
        backend = RecordingBackend()
        messages = [
            {"role": "system", "content": "first"},
            {"role": "user", "content": "hi"},
            {"role": "system", "content": "second"},
        ]

        self._run(backend, messages, system="only")

        self.assertEqual(system_of(messages), [{"role": "system", "content": "only"}])
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(
            [m["role"] for m in messages],
            ["system", "user", "user", "assistant"],
            "the old prompt is gone and the task is appended last",
        )

    def test_the_override_reaches_the_request(self) -> None:
        backend = RecordingBackend()

        self._run(backend, [], system="be brief")

        self.assertEqual(backend.requests[0].messages[0]["content"], "be brief")

    def test_an_empty_prompt_is_a_no_op(self) -> None:
        backend = RecordingBackend()
        messages = []

        self._run(backend, messages, system="")

        self.assertEqual(system_of(messages), [])

    def test_the_prompt_sticks_to_the_session(self) -> None:
        backend = RecordingBackend()
        session = RuntimeSession(id="s1", messages=[])

        asyncio.run(Agent(backend, close_backend=False).run("first", session=session, system="v1"))
        asyncio.run(Agent(backend, close_backend=False).run("second", session=session))

        self.assertEqual(system_of(session.messages), [{"role": "system", "content": "v1"}])

    def test_run_in_context_accepts_a_prompt(self) -> None:
        backend = RecordingBackend()
        session = RuntimeSession(id="s2", messages=[])
        context = RunContext(session=session, run_id="run-x")

        asyncio.run(Agent(backend, close_backend=False).run_in_context(context, "go", system="ctx"))

        self.assertEqual(session.messages[0], {"role": "system", "content": "ctx"})


class SystemPromptIsConversationStateTests(unittest.TestCase):
    def test_no_override_leaves_messages_untouched(self) -> None:
        backend = RecordingBackend()
        messages = [{"role": "user", "content": "earlier"}]

        asyncio.run(Agent(backend, close_backend=False).run("go", messages=messages))

        self.assertEqual(system_of(messages), [])
        self.assertEqual([m["role"] for m in messages], ["user", "user", "assistant"])

    def test_the_agent_holds_no_prompt_of_its_own(self) -> None:
        agent = Agent(RecordingBackend(), close_backend=False)

        self.assertFalse(hasattr(agent, "system_prompt"))

    def test_a_non_string_override_is_rejected(self) -> None:
        backend = RecordingBackend()

        with self.assertRaises(TypeError):
            asyncio.run(Agent(backend, close_backend=False).run("go", messages=[], system=42))

    def test_the_override_is_visible_where_the_conversation_is(self) -> None:
        backend = RecordingBackend()
        session = RuntimeSession(id="s3", messages=[])

        asyncio.run(
            Agent(backend, close_backend=False).run("go", session=session, system="from the host")
        )

        self.assertEqual(session.messages[0]["content"], "from the host")


class SystemPromptWireFormatTests(unittest.TestCase):
    def test_the_prompt_becomes_instructions_not_an_input_item(self) -> None:
        kwargs = completion_kwargs(
            "model",
            [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}],
            None,
            [],
        )

        self.assertEqual(kwargs["instructions"], "be brief")
        self.assertNotIn("system", {item.get("role") for item in kwargs["input"]})


if __name__ == "__main__":
    unittest.main()


class StraySystemMessageTests(unittest.TestCase):
    """The runtime never rewrites a host's prompt layout behind its back."""

    def test_a_stray_prompt_is_left_alone_and_reported(self) -> None:
        backend = RecordingBackend()
        messages = [
            {"role": "system", "content": "base"},
            {"role": "user", "content": "hi"},
            {"role": "system", "content": "appended later"},
        ]

        with self.assertLogs("agent0_runtime.loop", level="WARNING") as logs:
            asyncio.run(Agent(backend, close_backend=False).run("go", messages=messages))

        self.assertEqual(
            system_of(messages),
            [
                {"role": "system", "content": "base"},
                {"role": "system", "content": "appended later"},
            ],
            "history keeps both; the host decides what to do",
        )
        self.assertIn("2 system messages", logs.output[0])
        self.assertIn("[0, 2]", logs.output[0])

    def test_the_canonical_shape_is_not_reported(self) -> None:
        backend = RecordingBackend()
        messages = [{"role": "system", "content": "base"}]

        with self.assertNoLogs("agent0_runtime.loop", level="WARNING"):
            asyncio.run(Agent(backend, close_backend=False).run("go", messages=messages))

    def test_no_prompt_at_all_is_not_reported(self) -> None:
        backend = RecordingBackend()

        with self.assertNoLogs("agent0_runtime.loop", level="WARNING"):
            asyncio.run(Agent(backend, close_backend=False).run("go", messages=[]))

    def test_an_override_canonicalizes_before_the_request(self) -> None:
        backend = RecordingBackend()
        messages = [
            {"role": "system", "content": "base"},
            {"role": "user", "content": "hi"},
            {"role": "system", "content": "later"},
        ]

        with self.assertNoLogs("agent0_runtime.loop", level="WARNING"):
            asyncio.run(
                Agent(backend, close_backend=False).run("go", messages=messages, system="only")
            )

        self.assertEqual(system_of(messages), [{"role": "system", "content": "only"}])
