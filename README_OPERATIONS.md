# 📖 Runbook: MA Intel Platform (Operations)

## Prinzip
**Dokumentieren → Sichern → Verifizieren → Optimieren**

> **Öffentlicher Checkout:** Die hier mitgelieferten Ordner stehen in [MANIFEST.md](MANIFEST.md). `ingest/`, `pipeline/`, `models-local/` sowie die 🔴- und 🟡-Datenpfade gehören zum privaten Betriebsmodell und sind in diesem Repository nicht enthalten.

---

## 🚀 Der 3-Schritte-Standard-Ablauf

```text
① KLASSIFIZIEREN       ② VERIFIZIEREN         ③ FREIGEBEN / RUN
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Datenzone       │──▶│  Hash-Chain &    │──▶│  Air-Gapped /    │
│  bestimmen       │   │  Preflight-Check │   │  Cloud-Dev Run   │
│  (🔴/🟡/🔵/🟢)  │   │  ausführen       │   │  starten         │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

### Schritt 1: Klassifizieren
Vor jeder Datenverarbeitung den Pfad der richtigen Zone zuweisen:
* **Deal-Room / Mandanten-Raw-Daten** ➔ In `evidence/raw/` ablegen (`🔴 RESTRICTED` – bleibt lokal).
* **M&A-Intelligence-Modelle / Prompts** ➔ In `models-local/` ablegen (`🟡 CONFIDENTIAL` – isolierte Inferenz).
* **Code / Pipelines / Tests** ➔ In `pipeline/` & `scripts/` ablegen (`🔵 INTERNAL` – GitHub/Codespaces erlaubt). Im öffentlichen Checkout liegen Tests und Skripte unter `tests/` und `scripts/`. `pipeline/` ist hier nicht enthalten.

---

### Schritt 2: Verifizieren
Vor jedem Commit oder Audit die Integrität prüfen:
```bash
# 1a. Preflight vor dem Commit (nur gestagte Dateien, lokaler Hook):
python scripts/preflight_classification.py

# 1b. Preflight über den Arbeitsbaum (CI-Modus, ohne Staging):
python scripts/preflight_classification.py --scan-tree

# 2. Provenance & Submodule-Integrität prüfen:
python scripts/verify_provenance.py

# 3. Forensische SHA-256 Hashes zertifizieren:
python verification/hash_validator.py

# 4. Unit-Tests:
python -m unittest discover -s tests -v
```

`PREFLIGHT_SCAN_TREE=1` wählt denselben Arbeitsbaum-Scan wie `--scan-tree`. `--staged` erzwingt die Index-Prüfung.

---

### Schritt 3: Freigeben / Betrieb
* **Lokaler Audit-Lauf (Zero-Cloud)**:
  Alle Berechnungen laufen auf lokalen Cores oder Air-Gapped GPUs.
* **Dev & Cloud CI/CD**:
  `.github/workflows/policy-guard.yml` prüft bei jedem Push und Pull Request auf `main` Provenance, Hashes, den Arbeitsbaum-Preflight (`--scan-tree`) und `python -m unittest discover -s tests -v`.
