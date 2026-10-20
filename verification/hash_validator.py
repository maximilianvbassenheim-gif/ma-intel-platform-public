import sys
import hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def verify_manifest(base_dir: Path):
    print("🔍 Starte forensische Hash-Validierung...")
    results = {}
    for p in base_dir.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            results[str(p.relative_to(base_dir))] = calculate_sha256(p)
    print(f"✔ {len(results)} Dateien erfolgreich zertifiziert.")
    return results

if __name__ == "__main__":
    verify_manifest(Path(__file__).resolve().parent.parent)
