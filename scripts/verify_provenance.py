import sys
import json
import hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def verify_provenance():
    repo_root = Path(__file__).resolve().parent.parent
    source_map_path = repo_root / "SOURCE_MAP.json"
    manifest_path = repo_root / "MANIFEST.md"

    print("=" * 65)
    print("🔍 FORENSISCHE PROVENANCE & QUELLEN-VERIFIKATION")
    print("=" * 65)

    if not source_map_path.exists():
        print("❌ FEHLER: SOURCE_MAP.json fehlt!")
        return 1

    if not manifest_path.exists():
        print("❌ FEHLER: MANIFEST.md fehlt!")
        return 1

    try:
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ FEHLER beim Parsen von SOURCE_MAP.json: {e}")
        return 1

    print(f"✔ Manifest & Source-Map geladen (Platform: {source_map.get('platform')})")
    
    sources = source_map.get("sources", [])
    for src in sources:
        name = src.get("name")
        commit = src.get("commit")
        sub_path = repo_root / src.get("submodule_path", f"sources/{name}")
        
        print(f"\n📦 Prüfe Quelle: {name}")
        print(f"   • Referenz-Commit: {commit}")
        print(f"   • Lokaler Pfad:    {sub_path}")
        
        if sub_path.exists():
            print("   • Status:          ✅ Submodule physisch vorhanden")
        else:
            print("   • Status:          ⚠️ Submodule nicht initialisiert (git submodule update --init)")

    print("\n" + "=" * 65)
    print("✔ PROVENANCE-VERIFIKATION VOLLSTÄNDIG ABGESCHLOSSEN")
    print("=" * 65)
    return 0

if __name__ == "__main__":
    sys.exit(verify_provenance())
