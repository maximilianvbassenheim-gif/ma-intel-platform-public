import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.compute_popularity import compute_item_score

class TestPopularityEngine(unittest.TestCase):

    def test_popular_item_qualifies(self):
        now = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)
        item = {
            "id": "test-top",
            "title": "Top Project",
            "stars": 50,      # 30 pts max
            "forks": 20,      # 15 pts max
            "views": 500,     # 10 pts
            "downloads": 100, # 10 pts -> total engagement 20 pts
            "last_activity_date": (now - timedelta(hours=2)).isoformat() # ~24.7 pts
        }
        score, breakdown = compute_item_score(item, now)
        self.assertGreaterEqual(score, 70.0)
        self.assertEqual(breakdown["stars_norm"], 30.0)
        self.assertEqual(breakdown["forks_norm"], 15.0)
        self.assertEqual(breakdown["stale_penalty"], 0.0)

    def test_stale_item_receives_penalty(self):
        now = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)
        item = {
            "id": "test-stale",
            "title": "Old Archive",
            "stars": 5,
            "forks": 0,
            "views": 20,
            "downloads": 0,
            "last_activity_date": (now - timedelta(days=120)).isoformat()
        }
        score, breakdown = compute_item_score(item, now)
        self.assertEqual(breakdown["stale_penalty"], 20.0)
        self.assertLess(score, 70.0)

    def test_missing_fields_graceful_fallback(self):
        now = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)
        item = {
            "id": "empty-item"
        }
        score, breakdown = compute_item_score(item, now)
        self.assertGreaterEqual(score, 0.0)
        self.assertEqual(breakdown["stars_norm"], 0.0)
        self.assertEqual(breakdown["forks_norm"], 0.0)
        self.assertEqual(breakdown["stale_penalty"], 0.0)

if __name__ == "__main__":
    unittest.main()
