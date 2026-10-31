# MA Intel Platform

Public showcase of the forensic diligence, provenance, and M&A intelligence platform.
The code here classifies paths before they leave the machine, checks provenance and file hashes, and builds a daily popularity report from demo fixtures.

Deal-room records, client files, and confidential model artifacts stay in the private operating environment. Files under `data/internal/` and `reports/` are invented demo fixtures.

## What the platform does

Work is split across four data zones. The full definitions live in [docs/DATA_CLASSIFICATION_POLICY.md](docs/DATA_CLASSIFICATION_POLICY.md).

| Zone | Meaning | In this repository |
| --- | --- | --- |
| Restricted | Deal-room data, client records, raw evidence, secrets | Blocked by preflight. Kept private. |
| Confidential | Unredacted reports and confidential model artifacts | Blocked by preflight. Kept private. |
| Internal | Framework logic and dev configuration | Shareable scripts, tests, and config in this tree. |
| Public | Generic tools and documentation | This repository. |

Three checks run on every change:

1. **Classification preflight** rejects restricted and confidential paths.
2. **Provenance verification** reads `SOURCE_MAP.json` and `MANIFEST.md`. Internal source repositories are omitted from this public copy.
3. **Hash validation** certifies a SHA-256 for every file in the tree.

A demo pipeline scores invented catalog items and writes `reports/DEMO_popular_today.md` and `reports/DEMO_popular_today.json`. `.github/workflows/popularity-daily.yml` rebuilds that report on a daily schedule.

## What is in this repository

| Path | Contents |
| --- | --- |
| `scripts/preflight_classification.py` | Path classification guard |
| `scripts/verify_provenance.py` | Provenance check |
| `scripts/compute_popularity.py` | Demo popularity scorer |
| `verification/hash_validator.py` | SHA-256 certification |
| `tests/` | Unit tests for popularity scoring and classification matching |
| `config/popularity_weights.yaml` | Published weight reference for the demo score |
| `policy/flow_rules.yaml` | Data-flow rules between zones |
| `docs/DATA_CLASSIFICATION_POLICY.md` | Four-zone policy |
| `data/internal/` | Demo popularity input |
| `reports/` | Demo popularity output |
| `evidence/chain_of_custody.log` | Custody log for this public repo |
| `SOURCE_MAP.json` | Provenance record |
| `.github/workflows/policy-guard.yml` | CI guard on push and pull request to `main` |
| `.github/workflows/popularity-daily.yml` | Scheduled demo report |

The folder map, including private paths that are not shipped, is in [MANIFEST.md](MANIFEST.md).

## What stays private

These paths belong to the full platform and are absent from this checkout. Preflight fails if they appear in a commit or in the working tree.

- Restricted: `data/restricted/`, `evidence/raw/`, `deal_room/`, `mandanten/`, `.env`, `memory.db`
- Confidential: `models-local/confidential/`, `reports/unredacted/`
- Private components kept off this tree: `ingest/`, `pipeline/`, `models-local/`

## Run locally

From the repository root, with Python 3.11 or newer:

```bash
# Staged files only. This is the local commit-hook check.
python scripts/preflight_classification.py

# Tracked files and the rest of the working tree, including ignored
# paths such as .env and memory.db. This is what CI runs.
python scripts/preflight_classification.py --scan-tree

python scripts/verify_provenance.py
python verification/hash_validator.py
python -m unittest discover -s tests -v
```

`PREFLIGHT_SCAN_TREE=1` selects the working-tree scan. `--staged` forces the index check, including when that variable is set.

## Operations

The operator runbook (classify, verify, release) is [README_OPERATIONS.md](README_OPERATIONS.md).

## Continuous integration

On every push and pull request to `main`, `.github/workflows/policy-guard.yml` runs:

1. `python scripts/verify_provenance.py`
2. `python verification/hash_validator.py`
3. `python scripts/preflight_classification.py --scan-tree`
4. `python -m unittest discover -s tests -v`
