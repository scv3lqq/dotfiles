"""Fixture checks for verbatim edit parsing and reusable plan stubs."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import plan_edits


class PlanEditsTests(unittest.TestCase):
    def expected(self, plan: str, source: str) -> tuple[str, int]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.md"
            path.write_text(plan)
            with mock.patch.object(plan_edits, "at_base", return_value=source):
                return plan_edits.expected(str(path), "fixture.md", "fixture-base")

    @staticmethod
    def stub(source: str, ranges: list[str]) -> str:
        output = io.StringIO()
        with (
            mock.patch.object(plan_edits, "at_base", return_value=source),
            contextlib.redirect_stdout(output),
        ):
            plan_edits.stub("fixture.md", "fixture-base", ranges)
        return output.getvalue()

    def test_legacy_multiple_edits_preserve_tilde_fences_and_blank_lines(self) -> None:
        source = "First old.\n\n~~~sh\nold command\n~~~\n\nFirst tail.\n\nSecond old.\n"
        result = "First new.\n\n~~~sh\nnew command\n~~~\n\nNew tail.\n\nSecond new.\n"
        plans = (
            """```md E1-old
First old.

~~~sh
old command
~~~

First tail.
```

```md E1-new
First new.

~~~sh
new command
~~~

New tail.
```

```md E2-old
Second old.
```

```md E2-new
Second new.
```
""",
            """# Replacement plan

**E1.** Update the first paragraph and command.

```md E1-old
First old.

~~~sh
old command
~~~

First tail.
```

```md E1-new
First new.

~~~sh
new command
~~~

New tail.
```

**E2.** Update the last paragraph.

```md E2-old
Second old.
```

```md E2-new
Second new.
```
""",
        )
        for plan in plans:
            with self.subTest(headings=plan.startswith("#")):
                self.assertEqual(self.expected(plan, source), (result, 2))

    def test_longer_fences_preserve_inner_fences_and_both_tails(self) -> None:
        source = (
            "Before.\n```sh\nold triple\n```\nOld triple tail.\n\n"
            "````text\nold quadruple\n````\nOld quadruple tail.\nAfter.\n"
        )
        plan = """`````md E1-old
Before.
```sh
old triple
```
Old triple tail.

````text
old quadruple
````
Old quadruple tail.
`````

`````md E1-new
Updated.
```sh
new triple
```
New triple tail.

````text
new quadruple
````
New quadruple tail.
`````
"""
        result = (
            "Updated.\n```sh\nnew triple\n```\nNew triple tail.\n\n"
            "````text\nnew quadruple\n````\nNew quadruple tail.\nAfter.\n"
        )
        self.assertEqual(self.expected(plan, source), (result, 1))

    def test_adaptive_stub_round_trip_uses_five_backticks(self) -> None:
        source = "Start.\n````sh\nkeep command\n````\nTail.\n"
        expected_stub = """**E1.** (lines 1-5)

`````md E1-old
Start.
````sh
keep command
````
Tail.
`````

`````md E1-new
Start.
````sh
keep command
````
Tail.
`````
"""
        actual_stub = self.stub(source, ["1-5"])
        self.assertEqual(actual_stub, expected_stub)
        self.assertEqual(self.expected(actual_stub, source), (source, 1))

    def test_multiple_stub_ranges_have_one_separator_and_final_newline(self) -> None:
        source = "Alpha.\nBeta.\nGamma.\nDelta.\n"
        expected_stub = """**E1.** (lines 1-2)

````md E1-old
Alpha.
Beta.
````

````md E1-new
Alpha.
Beta.
````

**E2.** (lines 4-4)

````md E2-old
Delta.
````

````md E2-new
Delta.
````
"""
        self.assertEqual(self.stub(source, ["4", "1-2"]), expected_stub)


if __name__ == "__main__":
    unittest.main()
