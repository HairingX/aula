"""Tests of the repository's workflows."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

GITHUB = Path(__file__).parents[1]
WORKFLOWS = sorted((GITHUB / "workflows").glob("*.yml"))
BRANCH_TEST_BUILDS = GITHUB / "scripts" / "branch_test_builds.jq"

BASH = "defaults:\n  run:\n    shell: bash\n"


class TestWorkflows(unittest.TestCase):
    def test_the_workflows_are_found(self) -> None:
        self.assertTrue(WORKFLOWS)

    def test_a_step_fails_when_a_command_piped_into_another_fails(self) -> None:
        """GitHub runs a step as `bash -eo pipefail` only when the shell is given; without one it
        runs `bash -e`, where a failing command piped into another fails nothing."""
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                self.assertIn(BASH, workflow.read_text(encoding="utf-8"))

    def test_no_step_pipes_into_a_command_that_stops_reading(self) -> None:
        """With pipefail, the command before `head` fails when head stops reading its output."""
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                self.assertNotIn("| head", workflow.read_text(encoding="utf-8"))

    def test_every_workflow_states_its_token_permissions(self) -> None:
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                self.assertIn("\npermissions:", workflow.read_text(encoding="utf-8"))


@unittest.skipUnless(shutil.which("jq"), "jq is not installed")
class TestBranchTestBuilds(unittest.TestCase):
    RELEASES = [
        {
            "tag_name": "v0.2.9b1",
            "prerelease": True,
            "body": "notes\r\ntest-build-branch: fix/a\r\n",
        },
        {
            "tag_name": "v0.2.9b2",
            "prerelease": True,
            "body": "test-build-branch: fix/ab",
        },
        {
            "tag_name": "v0.2.9b3",
            "prerelease": True,
            "body": "test-build-branch: fix/a-2\n",
        },
        {
            "tag_name": "v0.2.9b4",
            "prerelease": True,
            "body": "x test-build-branch: fix/a",
        },
        {"tag_name": "v0.2.9", "prerelease": False, "body": "test-build-branch: fix/a"},
        {"tag_name": "v0.2.9b5", "prerelease": True, "body": None},
        {
            "tag_name": "v0.2.9b6",
            "prerelease": True,
            "body": "built\n\ntest-build-branch: fix/a",
        },
    ]

    def _select(self, branch: str) -> list[str]:
        result = subprocess.run(
            ["jq", "-r", "-f", str(BRANCH_TEST_BUILDS)],
            input=json.dumps(self.RELEASES),
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "BRANCH": branch},
        )
        return result.stdout.split()

    def test_only_the_branchs_own_test_builds_are_selected(self) -> None:
        self.assertEqual(self._select("fix/a"), ["v0.2.9b1", "v0.2.9b6"])

    def test_a_branch_whose_name_starts_another_does_not_select_it(self) -> None:
        self.assertEqual(self._select("fix/ab"), ["v0.2.9b2"])
        self.assertEqual(self._select("fix/"), [])


if __name__ == "__main__":
    unittest.main()
