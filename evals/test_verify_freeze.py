#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("verify_freeze.py")
spec = importlib.util.spec_from_file_location("verify_freeze", SCRIPT)
assert spec is not None
verify_freeze = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verify_freeze)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VerifyFreezeTests(unittest.TestCase):
    def test_committed_freezes_verify(self) -> None:
        for freeze in verify_freeze.freeze_files():
            errors, _, _ = verify_freeze.verify(freeze)
            self.assertEqual(errors, [], freeze.name)

    def test_tampered_dataset_reports_expected_and_actual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "evals" / "datasets" / "d.json"
            dataset.parent.mkdir(parents=True)
            dataset.write_bytes(b"original\n")
            expected = sha256(dataset.read_bytes())
            freeze = self.write_freeze(
                root,
                dataset_sha256=expected,
                artifacts={"dataset_sha256": "evals/datasets/d.json"},
            )

            dataset.write_bytes(b"tampered\n")
            actual = sha256(dataset.read_bytes())
            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("dataset_sha256 mismatch", errors[0])
            self.assertIn(f"expected {expected}", errors[0])
            self.assertIn(f"actual {actual}", errors[0])

    def test_hash_without_a_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(root, dataset_sha256=sha256(b"x"))

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("has no artifact path", errors[0])

    def test_external_hash_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                candidate_sha256=sha256(b"binary"),
                external_artifacts={"candidate_sha256": "binary built during the run"},
            )

            errors, skips, verified = verify_freeze.verify(freeze, root)

            self.assertEqual(errors, [])
            self.assertEqual(verified, 0)
            self.assertEqual(len(skips), 1)
            self.assertIn("candidate_sha256", skips[0])

    def test_missing_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                dataset_sha256=sha256(b"x"),
                artifacts={"dataset_sha256": "evals/datasets/missing.json"},
            )

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("artifact is missing", errors[0])

    def test_path_outside_the_repository_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            freeze = self.write_freeze(
                root,
                dataset_sha256=sha256(b"x"),
                artifacts={"dataset_sha256": "../outside.json"},
            )

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("outside the repository", errors[0])

    def test_absolute_artifact_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                dataset_sha256=sha256(b"x"),
                artifacts={"dataset_sha256": str(root / "evals" / "datasets" / "d.json")},
            )

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("must be repository-relative", errors[0])

    def test_non_hexadecimal_hash_fails_even_when_external(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                candidate_sha256="z" * 64,
                external_artifacts={"candidate_sha256": "binary built during the run"},
            )

            errors, skips, _ = verify_freeze.verify(freeze, root)

            self.assertEqual(len(errors), 1)
            self.assertIn("not a SHA-256 hex digest", errors[0])
            self.assertEqual(skips, [])

    def test_artifact_without_a_hash_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                dataset_sha256=sha256(b"x"),
                artifacts={
                    "dataset_sha256": "evals/datasets/d.json",
                    "suite_sha256": "evals/suites/s.json",
                },
            )

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertTrue(any("no such hash field" in error for error in errors))

    def test_artifact_and_external_cannot_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze = self.write_freeze(
                root,
                dataset_sha256=sha256(b"x"),
                artifacts={"dataset_sha256": "evals/datasets/d.json"},
                external_artifacts={"dataset_sha256": "declared twice"},
            )

            errors, _, _ = verify_freeze.verify(freeze, root)

            self.assertTrue(any("both a repository artifact and external" in error for error in errors))

    @staticmethod
    def write_freeze(root: Path, **fields: object) -> Path:
        path = root / "evals" / "results" / "freeze.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fields, indent=2) + "\n")
        return path


if __name__ == "__main__":
    unittest.main()
