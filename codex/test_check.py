"""Tests for explicit external reviewer validation."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).with_name("check.py")


class ReviewerCheckTests(unittest.TestCase):
    def run_reviewer(self, content: str | None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviewer.toml"
            if content is not None:
                path.write_text(content)
            return subprocess.run(
                [sys.executable, "-B", str(CHECK), "--reviewer", str(path)],
                capture_output=True, text=True, check=False,
            )

    def test_valid_reviewer(self) -> None:
        result = self.run_reviewer(
            'name = "go-code-reviewer"\nmodel = "gpt-6.1-sol"\n'
            'model_reasoning_effort = "high"\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_reviewer(self) -> None:
        valid = {
            "name": 'name = "go-code-reviewer"',
            "model": 'model = "gpt-6.1-sol"',
            "effort": 'model_reasoning_effort = "high"',
        }
        for field in valid:
            for replacement in (None, valid[field].replace('"', '"wrong-', 1)):
                with self.subTest(field=field, replacement=replacement):
                    values = dict(valid)
                    if replacement is None:
                        del values[field]
                    else:
                        values[field] = replacement
                    result = self.run_reviewer("\n".join(values.values()))
                    self.assertNotEqual(result.returncode, 0)

    def test_missing_and_malformed_reviewer(self) -> None:
        for content in (None, "invalid = ["):
            with self.subTest(content=content):
                self.assertNotEqual(self.run_reviewer(content).returncode, 0)


if __name__ == "__main__":
    unittest.main()
