"""Generation config: neutral fields, backend defaults, and the escape hatch."""

import asyncio
import unittest

from responses_fakes import FakeClient, text_turn

from agent0_runtime import Agent, GenerationConfig, OpenAIResponsesBackend
from agent0_runtime.openai_backend import completion_kwargs


class GenerationKwargsTests(unittest.TestCase):
    def test_neutral_fields_map_to_request_parameters(self):
        kwargs = completion_kwargs(
            "model",
            [{"role": "user", "content": "hi"}],
            None,
            [],
            generation=GenerationConfig(
                temperature=0.3,
                max_output_tokens=64,
                tool_choice="none",
                parallel_tool_calls=False,
            ),
        )

        self.assertEqual(kwargs["temperature"], 0.3)
        self.assertEqual(kwargs["max_output_tokens"], 64)
        self.assertEqual(kwargs["tool_choice"], "none")
        self.assertIs(kwargs["parallel_tool_calls"], False)

    def test_unset_fields_are_not_sent(self):
        kwargs = completion_kwargs("model", [], None, [], generation=GenerationConfig())

        for key in ("temperature", "max_output_tokens", "tool_choice", "parallel_tool_calls"):
            self.assertNotIn(key, kwargs)

    def test_extra_wins_over_neutral_fields(self):
        kwargs = completion_kwargs(
            "model",
            [],
            None,
            [],
            generation=GenerationConfig(
                temperature=0.1,
                extra={"temperature": 0.9, "text": {"format": {"type": "json_object"}}},
            ),
        )

        self.assertEqual(kwargs["temperature"], 0.9)
        self.assertEqual(kwargs["text"], {"format": {"type": "json_object"}})

    def test_merge_fills_unset_fields_and_overlays_extra(self):
        merged = GenerationConfig(temperature=0.2).merged_over(
            GenerationConfig(max_output_tokens=32, extra={"a": 1})
        )

        self.assertEqual(merged.temperature, 0.2)
        self.assertEqual(merged.max_output_tokens, 32)
        self.assertEqual(merged.extra, {"a": 1})

        override = GenerationConfig(extra={"a": 2}).merged_over(
            GenerationConfig(extra={"a": 1, "b": 3})
        )
        self.assertEqual(override.extra, {"a": 2, "b": 3})


class GenerationBackendTests(unittest.TestCase):
    def test_run_config_overrides_one_field_of_the_backend_default(self):
        client = FakeClient([text_turn("done")])
        backend = OpenAIResponsesBackend(
            client,
            "model",
            generation=GenerationConfig(temperature=0.0, max_output_tokens=1024),
        )
        agent = Agent(backend, close_backend=False)

        result = asyncio.run(agent.run("hi", generation=GenerationConfig(temperature=0.7)))

        self.assertEqual(result.text, "done")
        sent = client.requests[0]
        self.assertEqual(sent["temperature"], 0.7)
        self.assertEqual(sent["max_output_tokens"], 1024)

    def test_backend_default_applies_without_a_run_config(self):
        client = FakeClient([text_turn("done")])
        backend = OpenAIResponsesBackend(
            client, "model", generation=GenerationConfig(max_output_tokens=256)
        )
        agent = Agent(backend, close_backend=False)

        asyncio.run(agent.run("hi"))

        self.assertEqual(client.requests[0]["max_output_tokens"], 256)
        self.assertNotIn("temperature", client.requests[0])

    def test_from_openai_installs_the_backend_default(self):
        client = FakeClient([text_turn("done")])
        agent = Agent.from_openai(client, "model", generation=GenerationConfig(temperature=0.25))

        asyncio.run(agent.run("hi"))

        self.assertEqual(client.requests[0]["temperature"], 0.25)


if __name__ == "__main__":
    unittest.main()
