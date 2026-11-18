"""Plugin prompt fragments: contributed once, never rewritten behind the host."""

import asyncio
import itertools
import unittest

from agent0_runtime import (
    Agent,
    BackendRegistry,
    EventBus,
    LifecycleHooks,
    ModelTurn,
    PluginContext,
    PluginManager,
    PromptFragments,
    ToolRegistry,
)


class RecordingBackend:
    model = "fake-model"
    provider_id = "fake"
    context_limit = None

    def __init__(self, text: str = "done") -> None:
        self.text = text
        self.requests = []

    async def complete(self, request, _events):
        self.requests.append(request)
        return ModelTurn(text=self.text)


def tool_plugin(text: str):
    """A plugin that contributes nothing but prompt text."""

    def register(_self, context: PluginContext) -> None:
        context.prompts.add(text)

    # A distinct class per call: the manager refuses to load one plugin twice.
    return type(f"PromptPlugin{next(_SEQUENCE)}", (), {"api_version": 1, "register": register})()


def system_of(messages):
    return [message for message in messages if message.get("role") == "system"]


_SEQUENCE = itertools.count()


class PromptFragmentTests(unittest.TestCase):
    def test_add_keeps_order_and_separates_paragraphs(self) -> None:
        fragments = PromptFragments()

        fragments.add("first")
        fragments.add("second")

        self.assertEqual(fragments.parts, ("first", "second"))
        self.assertEqual(fragments.render(), "first\n\nsecond")

    def test_blank_text_is_ignored_and_non_strings_are_rejected(self) -> None:
        fragments = PromptFragments()

        fragments.add("   ")
        fragments.add("")
        self.assertFalse(fragments)

        with self.assertRaises(TypeError):
            fragments.add(42)  # type: ignore[arg-type]

    def test_stripped_fragments(self) -> None:
        fragments = PromptFragments()
        fragments.add("\n  spaced  \n")

        self.assertEqual(fragments.render(), "spaced")

    def test_plugin_manager_forwards_the_registration_surface(self) -> None:
        prompts = PromptFragments()
        manager = PluginManager(
            PluginContext(
                tools=ToolRegistry(),
                backends=BackendRegistry(),
                events=EventBus(),
                lifecycle=LifecycleHooks(),
                prompts=prompts,
            )
        )

        manager.load(tool_plugin("from the plugin"))

        self.assertEqual(prompts.render(), "from the plugin")


class AssembledPromptTests(unittest.TestCase):
    def test_a_new_conversation_starts_with_the_fragments(self) -> None:
        backend = RecordingBackend()
        agent = Agent(backend, close_backend=False, plugins=[tool_plugin("use bash carefully")])
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[0], {"role": "system", "content": "use bash carefully"})
        self.assertEqual(backend.requests[0].messages[0]["content"], "use bash carefully")

    def test_two_plugins_are_appended_in_registration_order(self) -> None:
        backend = RecordingBackend()
        agent = Agent(
            backend,
            close_backend=False,
            plugins=[tool_plugin("A"), tool_plugin("B")],
        )
        messages = []

        asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[0]["content"], "A\n\nB")

    def test_the_host_prompt_comes_first_and_fragments_follow(self) -> None:
        backend = RecordingBackend()
        agent = Agent(backend, close_backend=False, plugins=[tool_plugin("plugin text")])
        messages = []

        asyncio.run(agent.run("go", messages=messages, system="host base"))

        self.assertEqual(messages[0]["content"], "host base\n\nplugin text")

    def test_an_existing_prompt_is_not_rewritten(self) -> None:
        backend = RecordingBackend()
        agent = Agent(backend, close_backend=False, plugins=[tool_plugin("plugin text")])
        messages = [{"role": "system", "content": "stored prompt"}]

        with self.assertLogs("agent0_runtime.loop", level="WARNING") as logs:
            asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(system_of(messages), [{"role": "system", "content": "stored prompt"}])
        self.assertIn("fragments are not in this conversation", logs.output[0])

    def test_a_prompt_that_already_contains_the_fragments_is_silent(self) -> None:
        backend = RecordingBackend()
        agent = Agent(backend, close_backend=False, plugins=[tool_plugin("plugin text")])
        messages = [{"role": "system", "content": "host base\n\nplugin text"}]

        with self.assertNoLogs("agent0_runtime.loop", level="WARNING"):
            asyncio.run(agent.run("go", messages=messages))

        self.assertEqual(messages[0]["content"], "host base\n\nplugin text")

    def test_fragments_are_written_once_per_conversation(self) -> None:
        backend = RecordingBackend()
        agent = Agent(backend, close_backend=False, plugins=[tool_plugin("plugin text")])
        messages = []

        with self.assertNoLogs("agent0_runtime.loop", level="WARNING"):
            asyncio.run(agent.run("first", messages=messages))
            asyncio.run(agent.run("second", messages=messages))

        self.assertEqual(system_of(messages), [{"role": "system", "content": "plugin text"}])

    def test_no_fragments_and_no_host_prompt_leaves_history_alone(self) -> None:
        backend = RecordingBackend()
        messages = []

        asyncio.run(Agent(backend, close_backend=False).run("go", messages=messages))

        self.assertEqual(system_of(messages), [])


if __name__ == "__main__":
    unittest.main()
