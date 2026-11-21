"""Regression tests for limits.maxDecisionSliceBytes in wellmanifest/llm v1."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import conformance  # noqa: E402


def _reference_profile() -> dict[str, Any]:
    return json.loads(
        (ROOT / "models" / "subactor-first.v1.json").read_text(encoding="utf-8")
    )


class DecisionSliceBudgetTests(unittest.TestCase):
    def _check(self, profile: dict[str, Any]) -> list[str]:
        with tempfile.TemporaryDirectory(prefix="llm-slice-") as raw_tmp:
            path = Path(raw_tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            errors: list[str] = []
            conformance.check_profile(path, errors)
            return errors

    def test_reference_profile_declares_600b_decision_slice_and_passes(self) -> None:
        profile = _reference_profile()
        self.assertEqual(profile["limits"]["maxDecisionSliceBytes"], 600)
        self.assertEqual(self._check(profile), [])

    def test_legacy_profile_omitting_decision_slice_remains_valid(self) -> None:
        legacy = _reference_profile()
        legacy["limits"].pop("maxDecisionSliceBytes", None)
        self.assertEqual(self._check(legacy), [])

    def test_rejects_out_of_bounds_bool_or_hierarchy_violating_slice(self) -> None:
        for bad_val in (64, 1025, True, False, "600"):
            bad = copy.deepcopy(_reference_profile())
            bad["limits"]["maxDecisionSliceBytes"] = bad_val
            errors = self._check(bad)
            self.assertTrue(
                any("maxDecisionSliceBytes" in err for err in errors),
                f"expected error for {bad_val!r}, got {errors}",
            )

        exceeds_inline = _reference_profile()
        exceeds_inline["limits"]["maxInlineEvidenceBytes"] = 512
        exceeds_inline["limits"]["maxDecisionSliceBytes"] = 600
        errors = self._check(exceeds_inline)
        self.assertTrue(
            any("maxInlineEvidenceBytes" in err for err in errors), errors
        )
