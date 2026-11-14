import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import adb_target
import auto_bot as bot


class AdbAndLedgerTests(unittest.TestCase):
    def setUp(self):
        bot.set_target_window()

    def tearDown(self):
        bot.set_target_window()

    def test_game_day_boundary_is_0300_to_next_0259(self):
        self.assertEqual(bot.get_game_date_str(datetime(2026, 11, 13, 0, 0, 0)), "2026-11-12")
        self.assertEqual(bot.get_game_date_str(datetime(2026, 11, 13, 2, 59, 59)), "2026-11-12")
        self.assertEqual(bot.get_game_date_str(datetime(2026, 11, 13, 3, 0, 0)), "2026-11-13")
        self.assertEqual(bot.get_game_date_str(datetime(2026, 11, 13, 23, 59, 59)), "2026-11-13")

    def test_shared_ledger_uses_0300_game_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily_coins.json"
            with patch.object(bot, "DATA_FILE", path):
                with patch.object(bot, "get_game_date_str", return_value="2026-11-12"):
                    bot.save_daily_data(6400, 2, 1)
                    self.assertEqual(bot.load_daily_data(), (6400, 2))
                    self.assertEqual(bot.load_daily_stage(), 1)
                # After 03:00 rollover, old date resets to 0.
                with patch.object(bot, "get_game_date_str", return_value="2026-11-13"):
                    self.assertEqual(bot.load_daily_data(), (0, 0))
                    self.assertEqual(bot.load_daily_stage(), 0)

    def test_parse_adb_devices(self):
        sample = (
            "List of devices attached\n"
            "127.0.0.1:16384\tdevice product:cancro model:MuMu_12 device:cancro\n"
            "emulator-5554\toffline\n"
        )
        devices = adb_target.parse_adb_devices(sample)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0], adb_target.AdbDevice("127.0.0.1:16384", "device", "MuMu_12"))
        self.assertTrue(devices[0].ready)
        self.assertFalse(devices[1].ready)

    def test_adb_capture_and_tap_mapping_with_crop(self):
        raw_img = np.random.default_rng(11).integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".png", raw_img)
        self.assertTrue(ok)
        png_bytes = encoded.tobytes()

        bot.set_adb_target("127.0.0.1:16384", adb_path="adb.exe", crop_rect=(0.25, 0.25, 0.5, 0.5))

        class _FakeProc:
            returncode = 0
            stdout = png_bytes
            stderr = b""

        with patch.object(adb_target, "find_adb_executable", return_value="adb.exe"), \
             patch.object(adb_target.subprocess, "run", return_value=_FakeProc()), \
             contextlib.redirect_stdout(io.StringIO()):
            norm, left, top = bot.capture_game_window()

        self.assertEqual(norm.shape, (1080, 1920, 3))
        self.assertEqual((left, top), (320, 180))

        taps = []
        with patch.object(bot, "adb_tap", side_effect=lambda s, x, y, adb_path=None: taps.append((s, x, y)) or True):
            clicked = bot.safe_click(960, 540, left, top)

        self.assertTrue(clicked)
        serial, tx, ty = taps[0]
        self.assertEqual(serial, "127.0.0.1:16384")
        # Center of (320, 180, 640, 360) is (640, 360), +/- 4px offset
        self.assertTrue(636 <= tx <= 644, f"tx={tx}")
        self.assertTrue(356 <= ty <= 364, f"ty={ty}")

    def test_diagnose_frame_on_fixtures(self):
        fixtures = Path(__file__).parent / "fixtures"
        challenge_img = cv2.imread(str(fixtures / "challenge-12800.png"))
        result_img = cv2.imread(str(fixtures / "result-12800.png"))
        self.assertIsNotNone(challenge_img)
        self.assertIsNotNone(result_img)

        annotated_c, rep_c = bot.diagnose_frame(challenge_img)
        self.assertEqual(annotated_c.shape, (1080, 1920, 3))
        self.assertEqual(rep_c["state"], "ASK_CHALLENGE")
        self.assertEqual(rep_c["challenge_ocr"], 12800)

        annotated_r, rep_r = bot.diagnose_frame(result_img)
        self.assertEqual(annotated_r.shape, (1080, 1920, 3))
        self.assertEqual(rep_r["state"], "RESULT")
        self.assertEqual(rep_r["result_ocr"], 12800)


if __name__ == "__main__":
    unittest.main()
