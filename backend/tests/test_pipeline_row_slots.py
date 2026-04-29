from __future__ import annotations

import unittest
from pathlib import Path


class PipelineRowSlotTests(unittest.TestCase):
    def test_pipeline_limits_per_account_stages_without_global_shared_slots(self) -> None:
        source = Path("backend/pipeline/runner.py").read_text(encoding="utf-8")
        self.assertIn("_ACCOUNT_LIMITS", source)
        self.assertIn('"row": threading.Semaphore(3)', source)
        self.assertIn('"download": threading.Semaphore(3)', source)
        self.assertIn('"ffmpeg": threading.Semaphore(3)', source)
        self.assertIn('"upload": threading.Semaphore(3)', source)
        self.assertIn('with limits["row"]:', source)
        self.assertIn("with limits[\"download\"]:", source)
        self.assertIn("with limits[\"ffmpeg\"]:", source)
        self.assertIn("with limits[\"upload\"]:", source)
        self.assertNotIn("_GLOBAL_DOWNLOAD_SLOTS", source)
        self.assertNotIn("_GLOBAL_FFMPEG_SLOTS", source)
        self.assertNotIn("_GLOBAL_UPLOAD_SLOTS", source)
        self.assertIn("account_slot_key", source)


if __name__ == "__main__":
    unittest.main()
