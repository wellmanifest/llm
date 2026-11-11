"""Adversarial regression tests for wellmanifest/llm JSON, IO, URI, and type hardening."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import conformance  # noqa: E402
import install  # noqa: E402
import schema_validators  # noqa: E402


def _base_request() -> dict[str, Any]:
    return {
        "schema": "wellmanifest.llm-request/v1",
        "requestId": "req-20261111-0099",
        "operation": "knowledge.resolve",
        "intent": {"topic": "subactor-first"},
        "limits": {"maxItems": 5, "maxBytes": 4096, "timeoutSeconds": 30},
        "authority": "read-only",
        "contextRefs": ["knowledge://subactor/llm/v1"],
    }


def _base_response() -> dict[str, Any]:
    return {
        "schema": "wellmanifest.llm-response/v1",
        "requestId": "req-20261111-0099",
        "operation": "knowledge.resolve",
        "status": "ok",
        "results": [
            {
                "ref": "knowledge://subactor/llm/v1",
                "mediaType": "application/json",
                "digest": "sha256:" + ("b" * 64),
            }
        ],
        "receipt": {
            "redacted": True,
            "transport": "mcp",
            "route": "subactor://knowledge/resolve",
            "model": None,
            "startedAt": "2026-11-11T01:00:00Z",
            "finishedAt": "2026-11-11T01:00:02Z",
        },
    }


class LlmHardeningTests(unittest.TestCase):
    def test_strict_json_rejects_non_finite_float_overflow_and_deep_nesting(self) -> None:
        for payload in (
            '{"x": NaN}',
            '{"x": Infinity}',
            '{"x": -Infinity}',
            '{"x": 1e999}',
            '{"x": -1e999}',
            ("[" * 66) + "1" + ("]" * 66),
            ("[" * 1500) + "1" + ("]" * 1500),
        ):
            with self.subTest(payload=payload[:32]):
                with self.assertRaises(ValueError):
                    schema_validators.loads_strict_json(payload)

    def test_regular_file_reader_and_cli_reject_symlinks_and_oversized_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            real_req = base / "real-req.json"
            real_req.write_text(json.dumps(_base_request()), encoding="utf-8")
            sym_req = base / "sym-req.json"
            sym_req.symlink_to(real_req)

            with self.assertRaises(OSError):
                schema_validators.load_strict_json(sym_req)

            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = conformance.main(["--request", str(sym_req)])
            self.assertEqual(rc, 1)
            self.assertIn("symlink", err.getvalue().lower())

            sym_profile = base / "sym-profile.json"
            sym_profile.symlink_to(ROOT / "models" / "subactor-first.v1.json")
            err_prof = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err_prof):
                rc_prof = conformance.main(["--profile", str(sym_profile)])
            self.assertEqual(rc_prof, 1)
            self.assertIn("symlink", err_prof.getvalue().lower())

            big_file = base / "oversized.json"
            pad = b"x" * (schema_validators.MAX_FILE_BYTES + 16)
            big_file.write_bytes(b'{"a":"' + pad + b'"}')
            with self.assertRaises(ValueError):
                schema_validators.load_strict_json(big_file)

    def test_unhashable_enum_containers_do_not_crash_validators(self) -> None:
        bad_req = _base_request()
        bad_req["operation"] = ["knowledge.resolve"]
        bad_req["authority"] = {"mode": "read-only"}
        req_errors = schema_validators.validate_request_document(bad_req)
        self.assertTrue(any("request.operation" in e for e in req_errors), req_errors)
        self.assertTrue(any("request.authority" in e for e in req_errors), req_errors)

        bad_resp = _base_response()
        bad_resp["operation"] = {"op": 1}
        bad_resp["status"] = ["gap"]
        bad_resp["gap"] = {
            "method": ["live-observation"],
            "query": "q",
            "deduplicateAgainst": [],
        }
        bad_resp["receipt"] = dict(bad_resp["receipt"], transport=["mcp"])
        resp_errors = schema_validators.validate_response_document(bad_resp)
        self.assertTrue(any("response.operation" in e for e in resp_errors), resp_errors)
        self.assertTrue(any("response.status" in e for e in resp_errors), resp_errors)
        self.assertTrue(any("response.gap.method" in e for e in resp_errors), resp_errors)
        self.assertTrue(any("response.receipt.transport" in e for e in resp_errors), resp_errors)

    def test_non_string_dict_keys_and_non_finite_intent_values_are_rejected_cleanly(self) -> None:
        req_non_str: dict[Any, Any] = dict(_base_request())
        req_non_str[1] = "extra"
        req_non_str["intent"] = {2: "bad"}
        req_errors = schema_validators.validate_request_document(req_non_str)
        self.assertTrue(any("request: object keys must be strings" in e for e in req_errors))
        self.assertTrue(any("request.intent: object keys must be strings" in e for e in req_errors))

        nan_intent = _base_request()
        nan_intent["intent"] = {"score": float("nan")}
        nan_errors = schema_validators.validate_request_document(nan_intent)
        self.assertTrue(any("non-finite" in e for e in nan_errors), nan_errors)

        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema"],
            "properties": {"schema": {"type": "string"}},
        }
        schema_errors: list[str] = []
        conformance.check_required_by_schema({1: "x", "extra": "y"}, schema, schema_errors)
        self.assertTrue(any("object keys must be strings" in e for e in schema_errors))
        self.assertTrue(any("unknown property 'extra'" in e for e in schema_errors))

    def test_uri_validators_reject_traversal_empty_segments_and_control_chars(self) -> None:
        bad_grants = (
            "grant://..",
            "grant://subactor/../admin",
            "grant://subactor/./write",
            "grant://subactor//write",
            "grant://subactor/write/",
        )
        for grant_uri in bad_grants:
            with self.subTest(grant=grant_uri):
                req = _base_request()
                req["authority"] = "mutation-with-grant"
                req["grantRef"] = grant_uri
                errs = schema_validators.validate_request_document(req)
                self.assertTrue(any("request.grantRef" in e for e in errs), errs)

        bad_contexts = (
            "knowledge://subactor/../secret/v1",
            "artifact://subactor/./doc/r1",
            "observation://host//cpu",
            "observation://host\\cpu",
            "observation://host/\x1bcpu",
        )
        for ctx_uri in bad_contexts:
            with self.subTest(ctx=ctx_uri):
                req = _base_request()
                req["contextRefs"] = [ctx_uri]
                errs = schema_validators.validate_request_document(req)
                self.assertTrue(any("request.contextRefs" in e for e in errs), errs)

        resp = _base_response()
        resp["status"] = "gap"
        resp["results"] = [
            {
                "ref": "knowledge://subactor/../secret/v1",
                "mediaType": "application/json",
                "digest": "sha256:" + ("c" * 64),
            }
        ]
        resp["gap"] = {
            "method": "live-observation",
            "query": "check",
            "deduplicateAgainst": ["knowledge://subactor/../secret/v1"],
        }
        resp["receipt"] = dict(resp["receipt"], grantRef="grant://subactor/../admin")
        resp_errs = schema_validators.validate_response_document(resp)
        self.assertTrue(any("response.results[0].ref" in e for e in resp_errs), resp_errs)
        self.assertTrue(any("response.gap.deduplicateAgainst" in e for e in resp_errs), resp_errs)
        self.assertTrue(any("response.receipt.grantRef" in e for e in resp_errs), resp_errs)

    def test_installer_refuses_symlink_destination_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            outside = base / "outside.md"
            outside.write_text("do not touch\n", encoding="utf-8")
            repo = base / "repo"
            repo.mkdir()
            (repo / "AGENTS.md").symlink_to(outside)
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                rc = install.main(["--host", "codex", "--target", str(repo), "--apply"])
            self.assertEqual(rc, 1)
            self.assertEqual(outside.read_text(encoding="utf-8"), "do not touch\n")


if __name__ == "__main__":
    unittest.main()
