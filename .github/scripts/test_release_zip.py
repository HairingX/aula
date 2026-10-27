"""Tests of the zip a release publishes for HACS."""

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from release_zip import build

REPOSITORY = Path(__file__).parents[2]


def _integration(root: Path, version: str) -> Path:
    directory = root / "integration"
    (directory / "translations").mkdir(parents=True)
    (directory / "__pycache__").mkdir()
    (directory / "proxy" / "test_messages").mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps({"domain": "x", "version": version}), encoding="utf-8"
    )
    (directory / "__init__.py").write_text("", encoding="utf-8")
    (directory / "translations" / "en.json").write_text("{}", encoding="utf-8")
    (directory / "__pycache__" / "__init__.cpython-314.pyc").write_bytes(b"")
    (directory / "stray.pyc").write_bytes(b"")
    (directory / "proxy" / "client.py").write_text("", encoding="utf-8")
    (directory / "proxy" / "test_client.py").write_text("", encoding="utf-8")
    (directory / "proxy" / "test_messages" / "response.json").write_text(
        "{}", encoding="utf-8"
    )
    (directory / "test_top.py").write_text("", encoding="utf-8")
    return directory


class TestReleaseZip(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_the_integrations_files_are_at_the_zips_root_without_tests(self) -> None:
        build(_integration(self.root, "1.2.3"), self.root / "x.zip", "1.2.3")
        with zipfile.ZipFile(self.root / "x.zip") as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [
                    "__init__.py",
                    "manifest.json",
                    "proxy/client.py",
                    "translations/en.json",
                ],
            )

    def test_a_zip_whose_manifest_says_another_version_is_refused(self) -> None:
        with self.assertRaisesRegex(SystemExit, "says 0.0.0, not 1.2.3"):
            build(_integration(self.root, "0.0.0"), self.root / "x.zip", "1.2.3")

    def test_a_zip_without_a_manifest_at_its_root_is_refused(self) -> None:
        directory = _integration(self.root, "1.2.3")
        (directory / "manifest.json").unlink()
        with self.assertRaisesRegex(SystemExit, "no manifest.json at its root"):
            build(directory, self.root / "x.zip", "1.2.3")

    def test_the_aula_zip_holds_every_tracked_file_but_the_tests(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "custom_components/aula"],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        if not tracked:
            self.skipTest("not a git checkout")
        integration = REPOSITORY / "custom_components" / "aula"
        version = json.loads(
            (integration / "manifest.json").read_text(encoding="utf-8")
        )["version"]
        build(integration, self.root / "aula.zip", version)
        expected = sorted(
            path.removeprefix("custom_components/aula/")
            for path in tracked
            if not any(part.startswith("test_") for part in Path(path).parts)
        )
        with zipfile.ZipFile(self.root / "aula.zip") as archive:
            names = sorted(archive.namelist())
        self.assertEqual(names, expected)
        self.assertIn("aula_proxy/aula_proxy_client.py", names)
        self.assertFalse([name for name in names if "test_" in name])


if __name__ == "__main__":
    unittest.main()
