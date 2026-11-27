#!/usr/bin/env python3
"""Negative controls for case discovery: a wrong case must fail, a misplaced one must be refused.

Each test copies the kit to a temporary directory, so the checked-in cases are never changed.

Run: python3 test-kit/test_discovery.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent
SEED_CASE = "effects-receipt-missing"


def run(kit: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(KIT / "run.py"), "--kit", str(kit)],
                          capture_output=True, text=True, check=False)


class Discovery(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.kit = self.tmp / "kit"
        shutil.copytree(KIT / "cases", self.kit / "cases")
        shutil.copytree(KIT / "trust", self.kit / "trust")
        self.total = len(list((self.kit / "cases").iterdir()))

    def _copy_seed(self, dest: Path, expected_effect: str | None = None) -> None:
        shutil.copytree(self.kit / "cases" / SEED_CASE, dest)
        if expected_effect is not None:
            path = dest / "expected.json"
            data = json.loads(path.read_text())
            data["effect"] = expected_effect
            path.write_text(json.dumps(data))

    def test_unchanged_kit_passes(self) -> None:
        result = run(self.kit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"{self.total} of {self.total} cases answered as expected", result.stdout)

    def test_added_correct_case_is_discovered(self) -> None:
        self._copy_seed(self.kit / "cases" / "probe-correct")
        result = run(self.kit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok   probe-correct", result.stdout)
        self.assertIn(f"{self.total + 1} of {self.total + 1} cases", result.stdout)

    def test_added_wrong_case_is_discovered_and_fails(self) -> None:
        self._copy_seed(self.kit / "cases" / "probe-wrong", expected_effect="confirmed")
        result = run(self.kit)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DIFF probe-wrong", result.stdout)

    def test_fixture_under_contributions_is_refused(self) -> None:
        self._copy_seed(self.kit / "contributions" / "review-probe", expected_effect="confirmed")
        result = run(self.kit)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("contributions/review-probe", result.stderr)
        self.assertNotIn("ok  ", result.stdout)

    def test_mapping_only_contribution_is_allowed(self) -> None:
        (self.kit / "contributions" / "some-sdk").mkdir(parents=True)
        (self.kit / "contributions" / "some-sdk" / "mapping.md").write_text("# Source mapping\n")
        result = run(self.kit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
