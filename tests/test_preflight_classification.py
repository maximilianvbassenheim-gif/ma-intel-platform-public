import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.preflight_classification import (  # noqa: E402
    CONFIDENTIAL_PATTERNS,
    RESTRICTED_PATTERNS,
    collect_staged_paths,
    collect_tree_paths,
    collect_tree_paths_from_filesystem,
    collect_violations,
    main,
    match_classification,
    resolve_scan_tree,
    run_guard,
)

RESTRICTED_EXAMPLES = {
    "data/restricted/": "data/restricted/deal.pdf",
    "evidence/raw/": "evidence/raw/tape.bin",
    "deal_room/": "deal_room/teaser.pdf",
    "mandanten/": "mandanten/acme/notes.txt",
    ".env": "config/.env",
    "memory.db": "local/memory.db",
}

CONFIDENTIAL_EXAMPLES = {
    "models-local/confidential/": "models-local/confidential/weights.bin",
    "reports/unredacted/": "reports/unredacted/summary.md",
}

SAFE_PATHS = [
    "data/restricted",
    "data/restricted_export.csv",
    "evidence/raw",
    "evidence/raw-index.txt",
    "evidence/chain_of_custody.log",
    "deal_room",
    "deal_room_archive.zip",
    "mandanten",
    "mandantenliste.csv",
    "env",
    "environment.yml",
    "memory",
    "memory.database",
    "models-local/confidential",
    "models-local/public/adapter.py",
    "reports/unredacted",
    "reports/DEMO_popular_today.md",
    "data/internal/DEMO_items.json",
    "scripts/preflight_classification.py",
    "docs/DATA_CLASSIFICATION_POLICY.md",
    "README.md",
    "tests/test_popularity.py",
]


class TestClassificationMatching(unittest.TestCase):
    def test_patterns_are_lowercase_substrings(self):
        for pattern in (*RESTRICTED_PATTERNS, *CONFIDENTIAL_PATTERNS):
            with self.subTest(pattern=pattern):
                self.assertEqual(pattern, pattern.lower())
                self.assertTrue(pattern)

    def test_each_restricted_pattern_matches_its_example(self):
        for pattern, example in RESTRICTED_EXAMPLES.items():
            with self.subTest(pattern=pattern):
                hits = match_classification(example)
                self.assertIn(("restricted", pattern), hits)
                self.assertTrue(all(level == "restricted" for level, _ in hits))

    def test_each_confidential_pattern_matches_its_example(self):
        for pattern, example in CONFIDENTIAL_EXAMPLES.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    match_classification(example),
                    [("confidential", pattern)],
                )

    def test_safe_and_near_miss_paths_have_no_hits(self):
        for path in SAFE_PATHS:
            with self.subTest(path=path):
                self.assertEqual(match_classification(path), [])

    def test_case_and_backslashes_still_match(self):
        hits = match_classification("Evidence\\Raw\\Tape.BIN")
        self.assertEqual(hits, [("restricted", "evidence/raw/")])

        hits = match_classification("MODELS-LOCAL/CONFIDENTIAL/Weights.BIN")
        self.assertEqual(hits, [("confidential", "models-local/confidential/")])

    def test_violation_text_keeps_the_original_path(self):
        path = "Evidence\\Raw\\tape.bin"
        self.assertEqual(
            collect_violations([path]),
            ["🔴 RESTRICTED DATA BLOCK: 'Evidence\\Raw\\tape.bin' (match: evidence/raw/)"],
        )

    def test_multiple_patterns_keep_declaration_order(self):
        self.assertEqual(
            match_classification("data/restricted/memory.db"),
            [("restricted", "data/restricted/"), ("restricted", "memory.db")],
        )
        self.assertEqual(
            [level for level, _ in match_classification(
                "deal_room/models-local/confidential/weights.bin"
            )],
            ["restricted", "confidential"],
        )

    def test_dot_env_match_is_a_substring(self):
        self.assertEqual(match_classification(".environment"), [("restricted", ".env")])
        self.assertEqual(
            match_classification("var/memory.db-journal"),
            [("restricted", "memory.db")],
        )

    def test_file_order_is_preserved(self):
        violations = collect_violations([
            "README.md",
            "data/restricted/a",
            "reports/unredacted/b.md",
        ])
        self.assertEqual(
            violations,
            [
                "🔴 RESTRICTED DATA BLOCK: 'data/restricted/a' (match: data/restricted/)",
                "🟡 CONFIDENTIAL DATA BLOCK: 'reports/unredacted/b.md' (match: reports/unredacted/)",
            ],
        )

    def test_empty_path_and_empty_list(self):
        self.assertEqual(match_classification(""), [])
        self.assertEqual(collect_violations([]), [])


class TestScanModeSelection(unittest.TestCase):
    def test_resolve_scan_tree_precedence(self):
        cases = [
            (False, False, {}, False),
            (True, False, {}, True),
            (False, True, {"PREFLIGHT_SCAN_TREE": "1"}, False),
            (False, False, {"PREFLIGHT_SCAN_TREE": "1"}, True),
            (False, False, {"PREFLIGHT_SCAN_TREE": "true"}, True),
            (False, False, {"PREFLIGHT_SCAN_TREE": "YES"}, True),
            (False, False, {"PREFLIGHT_SCAN_TREE": "on"}, True),
            (False, False, {"PREFLIGHT_SCAN_TREE": "0"}, False),
            (False, False, {"PREFLIGHT_SCAN_TREE": "false"}, False),
            (False, False, {"PREFLIGHT_SCAN_TREE": "  "}, False),
            (True, False, {"PREFLIGHT_SCAN_TREE": "0"}, True),
        ]
        for scan_flag, staged_flag, env, expected in cases:
            with self.subTest(scan_flag=scan_flag, staged_flag=staged_flag, env=env):
                self.assertEqual(
                    resolve_scan_tree(
                        scan_tree_flag=scan_flag,
                        staged_flag=staged_flag,
                        env=env,
                    ),
                    expected,
                )


class TestWorkingTreeScan(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_filesystem_walk_reports_relative_posix_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "reports" / "unredacted"
            nested.mkdir(parents=True)
            (nested / "note.md").write_text("x", encoding="utf-8")
            paths = collect_tree_paths_from_filesystem(root)
            self.assertEqual(paths, ["reports/unredacted/note.md"])
            self.assertEqual(
                collect_violations(paths),
                [
                    "🟡 CONFIDENTIAL DATA BLOCK: 'reports/unredacted/note.md' "
                    "(match: reports/unredacted/)"
                ],
            )

    def test_scan_tree_outside_git_blocks_restricted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = root / "evidence" / "raw"
            secret.mkdir(parents=True)
            (secret / "tape.bin").write_text("x", encoding="utf-8")
            (root / "README.md").write_text("ok", encoding="utf-8")

            blocked = io.StringIO()
            with redirect_stdout(blocked):
                blocked_code = run_guard(root, scan_tree=True)
            self.assertEqual(blocked_code, 1)
            self.assertIn("ARBEITSBAUM BLOCKIERT", blocked.getvalue())
            self.assertIn("evidence/raw/tape.bin", blocked.getvalue())

            staged = io.StringIO()
            with redirect_stdout(staged):
                staged_code = run_guard(root, scan_tree=False)
            self.assertEqual(staged_code, 0)
            self.assertIn("Git-Prüfung fehlgeschlagen", staged.getvalue())
            self.assertNotIn("gestagten Dateien", staged.getvalue())

    def test_tree_scan_sees_untracked_and_ignored_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git(root, "init", "-b", "main")
            (root / ".gitignore").write_text("*.db\n.env\n", encoding="utf-8")
            (root / "README.md").write_text("public\n", encoding="utf-8")
            self._git(root, "add", ".gitignore", "README.md")
            (root / "deal_room").mkdir()
            (root / "deal_room" / "teaser.pdf").write_text("x", encoding="utf-8")
            (root / ".env").write_text("TOKEN=demo\n", encoding="utf-8")
            (root / "memory.db").write_bytes(b"db")

            violations = "\n".join(collect_violations(collect_tree_paths(root)))
            self.assertIn("deal_room/teaser.pdf", violations)
            self.assertIn(".env", violations)
            self.assertIn("memory.db", violations)
            self.assertEqual(collect_violations(collect_staged_paths(root)), [])

            blocked = io.StringIO()
            with redirect_stdout(blocked):
                self.assertEqual(run_guard(root, scan_tree=True), 1)
            self.assertIn("ARBEITSBAUM BLOCKIERT", blocked.getvalue())

            clean = io.StringIO()
            with redirect_stdout(clean):
                self.assertEqual(run_guard(root, scan_tree=False), 0)
            self.assertNotIn("COMMIT ABGEBROCHEN", clean.getvalue())
            self.assertIn("gestagten Dateien", clean.getvalue())

            self._git(root, "add", "deal_room/teaser.pdf")
            hooked = io.StringIO()
            with redirect_stdout(hooked):
                self.assertEqual(run_guard(root, scan_tree=False), 1)
            self.assertIn("COMMIT ABGEBROCHEN", hooked.getvalue())
            self.assertIn("deal_room/teaser.pdf", hooked.getvalue())

    def test_main_scan_tree_and_env_do_not_require_staged_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("ok", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--scan-tree"], repo_root=root), 0)
            (root / ".env").write_text("x", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--scan-tree"], repo_root=root), 1)
                self.assertEqual(main(["--staged"], repo_root=root), 0)
            with mock.patch.dict(os.environ, {"PREFLIGHT_SCAN_TREE": "1"}):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main([], repo_root=root), 1)
                    self.assertEqual(main(["--staged"], repo_root=root), 0)

    def test_public_checkout_has_no_classification_hits(self):
        violations = collect_violations(collect_tree_paths(REPO_ROOT))
        self.assertEqual(violations, [])

    def test_policy_guard_workflow_runs_tree_scan_and_unittest(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "policy-guard.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python scripts/verify_provenance.py", workflow)
        self.assertIn("python verification/hash_validator.py", workflow)
        self.assertIn("python scripts/preflight_classification.py --scan-tree", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)


if __name__ == "__main__":
    unittest.main()
