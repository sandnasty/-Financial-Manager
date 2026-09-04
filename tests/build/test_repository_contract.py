from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class RepositoryContractTest(unittest.TestCase):
    def test_required_make_targets_exist(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for target in ("build", "test", "validate", "format", "lint", "doctor"):
            self.assertIn(f"{target}:", makefile)

    def test_wrong_runtime_is_rejected(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/check_toolchain.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if sys.version_info[:3] == (3, 12, 11):
            self.assertEqual(result.returncode, 0)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Python 3.12.11 is required", result.stderr)

    def test_local_secrets_and_outputs_are_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", ignore)
        self.assertIn("dist/", ignore)


if __name__ == "__main__":
    unittest.main()
