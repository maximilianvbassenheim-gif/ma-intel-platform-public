#!/usr/bin/env python3
"""Preflight classification guard.

Blocks accidental commits or exports of RESTRICTED and CONFIDENTIAL paths.

Local commit hooks keep the default: only the index is inspected.

    python scripts/preflight_classification.py
    python scripts/preflight_classification.py --staged

CI scans tracked files and the rest of the working tree, including
untracked and ignored paths, so a clean index is not required.

    python scripts/preflight_classification.py --scan-tree

PREFLIGHT_SCAN_TREE=1 selects that same working-tree scan.
--staged still forces the index check when the variable is set.
"""

import argparse
import os
import sys
import subprocess
from collections.abc import Mapping
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RESTRICTED_PATTERNS = [
    "data/restricted/",
    "evidence/raw/",
    "deal_room/",
    "mandanten/",
    ".env",
    "memory.db",
]

CONFIDENTIAL_PATTERNS = [
    "models-local/confidential/",
    "reports/unredacted/",
]

_SCAN_TREE_ENV = "PREFLIGHT_SCAN_TREE"
_SCAN_TREE_TRUTHY = {"1", "true", "yes", "on"}

_LEVEL_LABEL = {
    "restricted": "🔴 RESTRICTED DATA BLOCK",
    "confidential": "🟡 CONFIDENTIAL DATA BLOCK",
}


class PathCollectionError(Exception):
    """Raised when git cannot list the paths a scan needs."""


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower()


def match_classification(path: str) -> list[tuple[str, str]]:
    """Return (level, pattern) hits for a repo-relative path.

    Restricted patterns are reported first, then confidential patterns,
    each in declaration order. Matching is a case-insensitive substring
    check on the slash-normalized path.
    """
    normalized = normalize_path(path)
    hits: list[tuple[str, str]] = []
    for pattern in RESTRICTED_PATTERNS:
        if pattern in normalized:
            hits.append(("restricted", pattern))
    for pattern in CONFIDENTIAL_PATTERNS:
        if pattern in normalized:
            hits.append(("confidential", pattern))
    return hits


def format_violation(path: str, level: str, pattern: str) -> str:
    label = _LEVEL_LABEL[level]
    return f"{label}: '{path}' (match: {pattern})"


def collect_violations(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        for level, pattern in match_classification(path):
            violations.append(format_violation(path, level, pattern))
    return violations


def resolve_scan_tree(
    *,
    scan_tree_flag: bool,
    staged_flag: bool,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Choose the working-tree scan.

    --staged wins, then --scan-tree, then PREFLIGHT_SCAN_TREE.
    """
    if staged_flag:
        return False
    if scan_tree_flag:
        return True
    source = os.environ if env is None else env
    raw = source.get(_SCAN_TREE_ENV, "")
    return raw.strip().lower() in _SCAN_TREE_TRUTHY


def _git_paths(repo_root: Path, args: list[str]) -> list[str]:
    try:
        out = subprocess.run(
            ["git", *args, "-z"],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            stderr = exc.stderr.decode("utf-8", errors="replace").strip()
            detail = stderr.splitlines()[0] if stderr else ""
        message = str(exc)
        if detail:
            message = f"{message}: {detail}"
        raise PathCollectionError(message) from exc
    text = out.stdout.decode("utf-8", errors="surrogateescape")
    return [line for line in text.split("\0") if line]


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def collect_staged_paths(repo_root: Path) -> list[str]:
    return _git_paths(repo_root, ["diff", "--cached", "--name-only"])


def collect_tree_paths(repo_root: Path) -> list[str]:
    """Tracked paths plus other working-tree paths, ignored files included."""
    tracked = _git_paths(repo_root, ["ls-files"])
    untracked = _git_paths(repo_root, ["ls-files", "--others", "--exclude-standard"])
    ignored = _git_paths(
        repo_root,
        ["ls-files", "--others", "--ignored", "--exclude-standard"],
    )
    return _dedupe(tracked + untracked + ignored)


def collect_tree_paths_from_filesystem(repo_root: Path) -> list[str]:
    """List working-tree files when git cannot. Skips the .git directory."""
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for filename in filenames:
            full = Path(dirpath) / filename
            paths.append(full.relative_to(repo_root).as_posix())
    paths.sort()
    return paths


def run_guard(repo_root: Path, *, scan_tree: bool) -> int:
    try:
        if scan_tree:
            paths = collect_tree_paths(repo_root)
        else:
            paths = collect_staged_paths(repo_root)
    except PathCollectionError as exc:
        if not scan_tree:
            print(f"⚠️ Git-Prüfung fehlgeschlagen: {exc}")
            return 0
        print(f"⚠️ Git-Prüfung fehlgeschlagen, verwende Dateisystem-Scan: {exc}")
        try:
            paths = collect_tree_paths_from_filesystem(repo_root)
        except OSError as fs_exc:
            print(f"❌ PREFLIGHT: Pfade konnten nicht gelesen werden: {fs_exc}")
            return 1

    violations = collect_violations(paths)
    if violations:
        if scan_tree:
            print("❌ PREFLIGHT CLASSIFICATION GUARD - ARBEITSBAUM BLOCKIERT!")
        else:
            print("❌ PREFLIGHT CLASSIFICATION GUARD - COMMIT ABGEBROCHEN!")
        print("=" * 60)
        for violation in violations:
            print(f"  {violation}")
        print("=" * 60)
        print("Sensible Daten dürfen niemals in Git/Cloud gepusht werden.")
        return 1

    if scan_tree:
        print(
            f"✔ PREFLIGHT GUARD: Alle {len(paths)} Dateien im Arbeitsbaum "
            "entsprechen der Policy (🔵/🟢)."
        )
    else:
        print("✔ PREFLIGHT GUARD: Alle gestagten Dateien entsprechen der Policy (🔵/🟢).")
    return 0


def check_staged_files() -> int:
    """Hook entry point. Always the index check, ignoring PREFLIGHT_SCAN_TREE."""
    repo_root = Path(__file__).resolve().parent.parent
    return run_guard(repo_root, scan_tree=False)


def main(argv: list[str] | None = None, repo_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Block RESTRICTED and CONFIDENTIAL paths before commit or export."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scan-tree",
        action="store_true",
        help="Scan tracked and working-tree paths. Does not require staged files.",
    )
    mode.add_argument(
        "--staged",
        action="store_true",
        help="Scan only the index (local commit hooks). This is the default.",
    )
    args = parser.parse_args(argv)
    scan_tree = resolve_scan_tree(
        scan_tree_flag=args.scan_tree,
        staged_flag=args.staged,
    )
    root = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent
    return run_guard(root, scan_tree=scan_tree)


if __name__ == "__main__":
    sys.exit(main())
