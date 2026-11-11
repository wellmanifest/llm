"""Regression suite for wellmanifest/llm conformance, schema validators, and installer."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "docs" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import conformance  # noqa: E402
import install  # noqa: E402
import schema_validators  # noqa: E402


def _valid_request() -> dict[str, object]:
    return {
        "schema": "wellmanifest.llm-request/v1",
        "requestId": "req-20261111-0001",
        "operation": "knowledge.resolve",
        "intent": {"topic": "subactor-first"},
        "limits": {"maxItems": 5, "maxBytes": 4096, "timeoutSeconds": 30},
        "authority": "read-only",
        "contextRefs": ["knowledge://subactor/llm/v1"],
    }


def _valid_response() -> dict[str, object]:
    return {
        "schema": "wellmanifest.llm-response/v1",
        "requestId": "req-20261111-0001",
        "operation": "knowledge.resolve",
        "status": "ok",
        "results": [
            {
                "ref": "knowledge://subactor/llm/v1",
                "mediaType": "application/json",
                "digest": "sha256:" + ("a" * 64),
                "summary": "Verified canonical Subactor-first profile.",
            }
        ],
        "receipt": {
            "redacted": True,
            "transport": "mcp",
            "route": "subactor://knowledge/resolve",
            "model": "gpt-5",
            "startedAt": "2026-11-11T01:00:00Z",
            "finishedAt": "2026-11-11T01:00:02Z",
        },
    }


class LlmConformanceAndValidatorTests(unittest.TestCase):
    def test_bundled_contracts_pass_conformance(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = conformance.main(["--all"])
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn("PASS wellmanifest/llm v1", out.getvalue())

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaises(schema_validators.DuplicateKeyError):
            schema_validators.loads_strict_json('{"a": 1, "a": 2}')

    def test_marker_extraction_rejects_inverted_and_duplicate_pairs(self) -> None:
        inverted = f"{schema_validators.END}\nbody\n{schema_validators.START}"
        block, err = schema_validators.extract_marked_block(inverted)
        self.assertIsNone(block)
        self.assertIn("inverted", err or "")

        duplicated = (
            f"{schema_validators.START}\na\n{schema_validators.END}\n"
            f"{schema_validators.START}\nb\n{schema_validators.END}"
        )
        dup_block, dup_err = schema_validators.extract_marked_block(duplicated)
        self.assertIsNone(dup_block)
        self.assertIn("malformed", dup_err or "")

    def test_valid_request_and_mutation_grant_rules(self) -> None:
        self.assertEqual(schema_validators.validate_request_document(_valid_request()), [])

        missing_grant = _valid_request()
        missing_grant["authority"] = "mutation-with-grant"
        self.assertTrue(
            any(
                "grantRef" in e
                for e in schema_validators.validate_request_document(missing_grant)
            )
        )

        with_grant = dict(missing_grant, grantRef="grant://subactor/ticket-010/write")
        self.assertEqual(schema_validators.validate_request_document(with_grant), [])

        forbidden_grant = _valid_request()
        forbidden_grant["grantRef"] = "grant://subactor/ticket-010/write"
        self.assertTrue(
            any(
                "forbidden unless authority" in e
                for e in schema_validators.validate_request_document(forbidden_grant)
            )
        )

    def test_request_rejects_bool_limits_unknown_fields_and_duplicate_contexts(self) -> None:
        bool_limit = _valid_request()
        bool_limit["limits"] = {"maxItems": True, "maxBytes": 4096, "timeoutSeconds": 30}
        errors = schema_validators.validate_request_document(bool_limit)
        self.assertTrue(any("request.limits.maxItems" in e for e in errors), errors)

        extra_field = _valid_request()
        extra_field["unexpected"] = 1
        self.assertTrue(
            any(
                "unknown field 'unexpected'" in e
                for e in schema_validators.validate_request_document(extra_field)
            )
        )

        dup_ctx = _valid_request()
        dup_ctx["contextRefs"] = [
            "knowledge://subactor/llm/v1",
            "knowledge://subactor/llm/v1",
        ]
        self.assertTrue(
            any(
                "contextRefs" in e
                for e in schema_validators.validate_request_document(dup_ctx)
            )
        )

    def test_response_validation_enforces_gap_chronology_and_redaction(self) -> None:
        self.assertEqual(
            schema_validators.validate_response_document(_valid_response()), []
        )

        missing_gap = _valid_response()
        missing_gap["status"] = "gap"
        self.assertTrue(
            any(
                "response.gap: required" in e
                for e in schema_validators.validate_response_document(missing_gap)
            )
        )

        valid_gap = dict(
            missing_gap,
            gap={
                "method": "live-observation",
                "query": "inspect branch status",
                "deduplicateAgainst": ["knowledge://subactor/git/v1"],
            },
        )
        self.assertEqual(schema_validators.validate_response_document(valid_gap), [])

        inverted_ts = _valid_response()
        receipt = dict(inverted_ts["receipt"])  # type: ignore[arg-type]
        receipt["startedAt"] = "2026-11-11T02:00:00Z"
        receipt["finishedAt"] = "2026-11-11T01:00:00Z"
        receipt["redacted"] = False
        inverted_ts["receipt"] = receipt
        ts_errors = schema_validators.validate_response_document(inverted_ts)
        self.assertTrue(any("finishedAt precedes startedAt" in e for e in ts_errors))
        self.assertTrue(any("redacted: must be true" in e for e in ts_errors))

    def test_cli_request_and_response_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            req_path = Path(tmp) / "req.json"
            resp_path = Path(tmp) / "resp.json"
            req_path.write_text(json.dumps(_valid_request()), encoding="utf-8")
            resp_path.write_text(json.dumps(_valid_response()), encoding="utf-8")
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = conformance.main(
                    ["--request", str(req_path), "--response", str(resp_path)]
                )
            self.assertEqual(rc, 0, err.getvalue())

            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text('{"schema":"wellmanifest.llm-request/v1"}', encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                bad_rc = conformance.main(["--request", str(bad_path)])
            self.assertEqual(bad_rc, 1)

    def test_profile_validator_rejects_non_dict_sections_and_bool_limits(self) -> None:
        raw = json.loads((ROOT / "models" / "subactor-first.v1.json").read_text("utf-8"))
        raw["authority"] = "not-an-object"
        raw["limits"]["maxKnowledgeItems"] = True
        raw["extraTop"] = 123
        with tempfile.TemporaryDirectory() as tmp:
            prof_path = Path(tmp) / "profile.json"
            prof_path.write_text(json.dumps(raw), encoding="utf-8")
            errors: list[str] = []
            conformance.check_profile(prof_path, errors)
        self.assertTrue(any("unknown property 'extraTop'" in e for e in errors), errors)
        self.assertTrue(any("authority boundary mismatch" in e for e in errors), errors)
        self.assertTrue(
            any("profile.limits.maxKnowledgeItems" in e for e in errors), errors
        )


class TransactionalInstallerTests(unittest.TestCase):
    def test_dry_run_creates_nothing_and_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            out = io.StringIO()
            with redirect_stdout(out):
                rc = install.main(["--host", "codex", "--target", str(target)])
            self.assertEqual(rc, 0)
            self.assertFalse((target / ".wellmanifest").exists())
            self.assertFalse((target / "AGENTS.md").exists())

            apply_out = io.StringIO()
            with redirect_stdout(apply_out):
                rc_apply = install.main(
                    ["--host", "codex", "--target", str(target), "--apply"]
                )
            self.assertEqual(rc_apply, 0)
            self.assertTrue((target / ".wellmanifest" / "llm.json").is_file())
            self.assertTrue((target / "AGENTS.md").is_file())

            rerun_out = io.StringIO()
            with redirect_stdout(rerun_out):
                rc_rerun = install.main(
                    ["--host", "codex", "--target", str(target), "--apply"]
                )
            self.assertEqual(rc_rerun, 0)
            self.assertIn("UNCHANGED codex", rerun_out.getvalue())

    def test_transactional_plan_prevents_partial_writes_on_later_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            agents.write_text(
                f"# Host\n\n{install.START}\ncustom differing block\n{install.END}\n",
                encoding="utf-8",
            )
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = install.main(["--host", "codex", "--target", str(target), "--apply"])
            self.assertEqual(rc, 1)
            self.assertIn("REFUSED", err.getvalue())
            self.assertFalse(
                (target / ".wellmanifest" / "llm.json").exists(),
                "No document may be written when adapter validation fails",
            )

    def test_installer_appends_marker_span_cleanly_to_existing_host_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            agents = target / "AGENTS.md"
            agents.write_text("# Existing project instructions\n\nKeep me.\n\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                rc = install.main(["--host", "codex", "--target", str(target), "--apply"])
            self.assertEqual(rc, 0)
            merged = agents.read_text(encoding="utf-8")
            self.assertTrue(merged.startswith("# Existing project instructions\n\nKeep me.\n\n"))
            self.assertNotIn("\n\n\n", merged)
            block, err = schema_validators.extract_marked_block(merged)
            self.assertIsNone(err)
            self.assertIsNotNone(block)

    def test_installer_rejects_symlink_target_and_symlink_intermediate_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside"
            outside.mkdir()
            sym_root = Path(tmp) / "sym-root"
            sym_root.symlink_to(outside)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = install.main(["--host", "codex", "--target", str(sym_root), "--apply"])
            self.assertEqual(rc, 1)
            self.assertIn("symlink", err.getvalue())

            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".wellmanifest").symlink_to(outside)
            err2 = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err2):
                rc2 = install.main(["--host", "codex", "--target", str(repo), "--apply"])
            self.assertEqual(rc2, 1)
            self.assertFalse((outside / "llm.json").exists())


if __name__ == "__main__":
    unittest.main()
