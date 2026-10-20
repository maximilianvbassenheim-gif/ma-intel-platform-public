#!/usr/bin/env python3
"""
Popularity Filter Engine (v1):
Computes deterministic popularity scores based on activity, stars, forks, and engagement.
Generates reports/DEMO_popular_today.md (items with score >= 70) and reports/DEMO_popular_today.json
from the demo input data/internal/DEMO_items.json (DEMO-Daten: frei erfunden, keine echten Sterne/Forks/Downloads).
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO_ROOT = Path(__file__).resolve().parent.parent

def parse_iso(ts_str: str) -> datetime:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)

def compute_item_score(item: dict, now: datetime = None) -> tuple[float, dict]:
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Stars (0-30 pts)
    stars = item.get("stars", 0)
    stars_norm = min(30.0, float(stars) * 0.6)

    # 2. Forks (0-15 pts)
    forks = item.get("forks", 0)
    forks_norm = min(15.0, float(forks) * 0.75)

    # 3. Recent Activity (0-25 pts, last 14 days)
    last_act = parse_iso(item.get("last_activity_date", ""))
    days_ago = (now - last_act).total_seconds() / 86400.0
    
    if days_ago <= 14:
        recent_activity_norm = max(0.0, 25.0 * (1.0 - (days_ago / 14.0)))
    else:
        recent_activity_norm = 0.0

    # 4. Engagement (0-20 pts)
    views = item.get("views", 0)
    downloads = item.get("downloads", 0)
    engagement_raw = (views * 0.02) + (downloads * 0.1)
    engagement_norm = min(20.0, engagement_raw)

    # Penalty if stale > 90 days
    penalty = 20.0 if days_ago > 90 else 0.0

    total_score = max(0.0, stars_norm + forks_norm + recent_activity_norm + engagement_norm - penalty)

    breakdown = {
        "stars_norm": round(stars_norm, 2),
        "forks_norm": round(forks_norm, 2),
        "recent_activity_norm": round(recent_activity_norm, 2),
        "engagement_norm": round(engagement_norm, 2),
        "stale_penalty": round(penalty, 2),
        "total_score": round(total_score, 2)
    }

    return round(total_score, 2), breakdown

def run_pipeline():
    input_path = REPO_ROOT / "data" / "internal" / "DEMO_items.json"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"⚠️ Eingabedatei nicht gefunden: {input_path}")
        return 1

    try:
        items = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Fehler beim Laden von DEMO_items.json: {e}")
        return 1

    scored_items = []
    now = datetime.now(timezone.utc)

    for it in items:
        score, breakdown = compute_item_score(it, now)
        scored_items.append({
            **it,
            "score": score,
            "breakdown": breakdown
        })

    # Sort by score descending
    scored_items.sort(key=lambda x: x["score"], reverse=True)

    # Filter popularity >= 70
    popular_items = [it for it in scored_items if it["score"] >= 70.0][:25]

    # 1. Output JSON
    out_json = reports_dir / "DEMO_popular_today.json"
    out_json.write_text(json.dumps(scored_items, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. Output Markdown
    out_md = reports_dir / "DEMO_popular_today.md"
    md_lines = [
        "> **DEMO-Daten: frei erfunden, keine echten Sterne/Forks/Downloads**",
        "",
        "# 🌟 Popular Today — Top Inhalte & Artefakte",
        "",
        f"**Erstellt am**: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "**Filter-Kriterium**: `popularity_score >= 70.0`",
        "",
        "| Rang | Titel | Kategorie | Score | Sterne | Forks | Aufrufe | Letzte Aktivität |",
        "| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :--- |"
    ]

    if not popular_items:
        md_lines.append("\n*Heute haben keine Elemente den Schwellenwert von 70 Punkten erreicht.*")
    else:
        for idx, it in enumerate(popular_items, 1):
            md_lines.append(
                f"| **#{idx}** | **{it.get('title')}** | `{it.get('category')}` | **{it.get('score')}** | "
                f"{it.get('stars', 0)} | {it.get('forks', 0)} | {it.get('views', 0)} | {it.get('last_activity_date', 'N/A')[:10]} |"
            )

    md_lines.extend([
        "",
        "---",
        "### 📊 Score-Aufbau (v1)",
        "- **Stars**: max. 30 Pkt",
        "- **Forks**: max. 15 Pkt",
        "- **Aktivität (letzte 14 Tage)**: max. 25 Pkt",
        "- **Engagement (Views & Downloads)**: max. 20 Pkt",
        "- **Stale-Malus**: -20 Pkt wenn > 90 Tage inaktiv"
    ])

    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print("=" * 60)
    print(f"✔ Popularitäts-Filter erfolgreich abgeschlossen!")
    print(f"  • Gescannt: {len(scored_items)} Elemente")
    print(f"  • Qualifiziert (Score >= 70): {len(popular_items)} Elemente")
    print(f"  • Berichte generiert: {out_md.name} & {out_json.name}")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(run_pipeline())
