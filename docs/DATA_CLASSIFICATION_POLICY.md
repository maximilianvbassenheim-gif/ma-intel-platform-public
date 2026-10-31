# Data Classification Policy (MA Intel Platform)

## Prinzip
**Dokumentieren → Sichern → Verifizieren → Optimieren**

Die Datenverarbeitung innerhalb der **MA Intel Platform** unterliegt einer strikten 4-Zonen-Klassifikation zur Wahrung von Mandantengeheimnissen, forensischer Evidenz und Zero-Trust-Sicherheit.

---

## 4-Zonen-Matrix

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔴 RESTRICTED (Zero-Cloud / Local-Only)                                     │
│ • Definition: Deal-Room-Daten, Mandantendaten, Verträge, Rohevidenzen.      │
│ • Speicherort: Lokale SQLite FTS5 (memory.db), lokale verschlüsselte SSD.   │
│ • Transferregel: NIEMALS Cloud, NIEMALS Codespaces, NIEMALS externe APIs.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟡 CONFIDENTIAL (Hybrid / Self-Hosted Inferenz)                             │
│ • Definition: Bereinigte Synthesen, M&A-Intelligence-Modelle, Audit-Notizen.│
│ • Speicherort: Lokaler Workspace, dedizierte verschlüsselte Inferenz.       │
│ • Transferregel: Nur Air-Gapped Local LLMs oder isolierte Inferenz-Knoten.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔵 INTERNAL (Cloud-Dev / GitHub Codespaces)                                 │
│ • Definition: Quellcode-Logik, ETL-Pipelines, Test-Suiten, Orchestrierung.  │
│ • Speicherort: GitHub Pro Repositories, Codespaces Cloud VMs.               │
│ • Transferregel: Cloud-Entwicklung erlaubt, KEINE Klientendaten gestattet.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟢 PUBLIC (Open-Source / Generic Tools)                                     │
│ • Definition: Open-Source Hilfsskripte, generische Validatoren, Docs.       │
│ • Speicherort: Öffentliche Repositories, Packages.                          │
│ • Transferregel: Vollständiger Secret- & Provenance-Scan Pflicht vor Push.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Durchsetzungsregeln (Enforcement)
1. **Default Deny**: Jede unklassifizierte Datei wird automatisch als `🔴 RESTRICTED` eingestuft.
2. **Gatekeeper-Prüfung**: `scripts/preflight_classification.py` blockiert gestagte sensible Pfade vor dem Commit. In CI scannt derselbe Guard mit `--scan-tree` (oder `PREFLIGHT_SCAN_TREE=1`) den gesamten Arbeitsbaum, ohne dass Dateien gestagt sein müssen.
3. **Chain-of-Custody**: Jeder Datenimport erfordert einen Eintrag in `evidence/chain_of_custody.log`.
