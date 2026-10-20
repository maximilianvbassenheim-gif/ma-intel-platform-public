# 📖 Runbook: MA Intel Platform (Operations)

## Prinzip
**Dokumentieren → Sichern → Verifizieren → Optimieren**

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
* **Code / Pipelines / Tests** ➔ In `pipeline/` & `scripts/` ablegen (`🔵 INTERNAL` – GitHub/Codespaces erlaubt).

---

### Schritt 2: Verifizieren
Vor jedem Commit oder Audit die Integrität prüfen:
```bash
# 1. Preflight-Check (blockt sensible Leaks vor dem Commit):
python scripts/preflight_classification.py

# 2. Provenance & Submodule-Integrität prüfen:
python scripts/verify_provenance.py

# 3. Forensische SHA-256 Hashes zertifizieren:
python verification/hash_validator.py
```

---

### Schritt 3: Freigeben / Betrieb
* **Lokaler Audit-Lauf (Zero-Cloud)**:
  Alle Berechnungen laufen auf lokalen Cores oder Air-Gapped GPUs.
* **Dev & Cloud CI/CD**:
  GitHub Actions prüft automatisch alle Pull Requests und Commits im Meta-Repo.
