#!/usr/bin/env python3
"""
Preflight Classification Guard:
Blocks accidental commits or exports of RESTRICTED (🔴) and CONFIDENTIAL (🟡) files.
"""

import sys
import subprocess
from pathlib import Path

RESTRICTED_PATTERNS = [
    "data/restricted/",
    "evidence/raw/",
    "deal_room/",
    "mandanten/",
    ".env",
    "memory.db"
]

CONFIDENTIAL_PATTERNS = [
    "models-local/confidential/",
    "reports/unredacted/"
]

def check_staged_files():
    repo_root = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        staged = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception as e:
        print(f"⚠️ Git-Prüfung fehlgeschlagen: {e}")
        return 0

    violations = []
    for f in staged:
        f_norm = f.replace("\\", "/").lower()
        for p in RESTRICTED_PATTERNS:
            if p in f_norm:
                violations.append(f"🔴 RESTRICTED DATA BLOCK: '{f}' (match: {p})")
        for p in CONFIDENTIAL_PATTERNS:
            if p in f_norm:
                violations.append(f"🟡 CONFIDENTIAL DATA BLOCK: '{f}' (match: {p})")

    if violations:
        print("❌ PREFLIGHT CLASSIFICATION GUARD - COMMIT ABGEBROCHEN!")
        print("=" * 60)
        for v in violations:
            print(f"  {v}")
        print("=" * 60)
        print("Sensible Daten dürfen niemals in Git/Cloud gepusht werden.")
        return 1

    print("✔ PREFLIGHT GUARD: Alle gestagten Dateien entsprechen der Policy (🔵/🟢).")
    return 0

if __name__ == "__main__":
    sys.exit(check_staged_files())
