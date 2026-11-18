"""Optional extras: the core imports and runs without Pillow, trafilatura, or urllib3."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from agent0_runtime.images import PillowImageReader

ROOT = Path(__file__).resolve().parents[1]


class OptionalDependencyTests(unittest.TestCase):
    def test_core_imports_without_optional_extras(self):
        code = (
            "import sys\n"
            "for name in ('PIL', 'trafilatura', 'urllib3', 'certifi'):\n"
            "    sys.modules[name] = None\n"
            "import agent0_runtime\n"
            "from agent0_runtime import Agent\n"
            "print(agent0_runtime.__version__)\n"
        )
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

        completed = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
            timeout=60,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_missing_pillow_is_reported_as_a_tool_error(self):
        reader = PillowImageReader()
        with patch.dict(sys.modules, {"PIL": None}):
            from agent0_runtime import images

            images._pillow.cache_clear()
            try:
                result = reader.read(Path(__file__), "image/png")
            finally:
                images._pillow.cache_clear()

        self.assertIn("agent0-runtime[images]", result.text)


if __name__ == "__main__":
    unittest.main()
