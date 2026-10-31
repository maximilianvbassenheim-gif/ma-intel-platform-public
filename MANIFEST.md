# MA Intel Platform – Manifest

## Prinzip
**Dokumentieren → Sichern → Verifizieren → Optimieren**

## Purpose
Public, reviewable slice of the platform: classification preflight, provenance, hash certification, and a demo popularity report. Deal-room and client material stay in the private environment.

## Shipped in this repository

- `.github/workflows/` — Policy & Provenance Guard, and the daily demo popularity report
- `config/` — popularity weight reference (`popularity_weights.yaml`)
- `data/internal/` — invented demo input for the popularity scorer
- `docs/` — data classification policy
- `evidence/` — `chain_of_custody.log` only. Raw evidence is not in this tree
- `policy/` — zone flow rules (`flow_rules.yaml`)
- `reports/` — invented demo popularity report
- `scripts/` — preflight, provenance verification, demo popularity scorer
- `tests/` — unit tests for popularity scoring and classification matching
- `verification/` — forensic SHA-256 validator (`hash_validator.py`)
- `SOURCE_MAP.json` — provenance record. Internal source repositories are not included in this public copy
- `README.md`, `README_OPERATIONS.md` — overview and operator runbook

## Private-only (not shipped here)

These paths belong to the full operating environment and are absent from this checkout. The preflight guard blocks the restricted and confidential entries if they show up in the index or the working tree.

- `ingest/` — validated multi-format connectors (private component)
- `pipeline/` — ETL and analysis pipelines (private component)
- `models-local/` — local and remote inference adapters (private component)
- `data/restricted/` — restricted data
- `evidence/raw/` — raw evidence
- `deal_room/` — deal-room material
- `mandanten/` — client material
- `memory.db` — local restricted index
- `.env` — secrets
- `models-local/confidential/` — confidential model artifacts
- `reports/unredacted/` — confidential reports
