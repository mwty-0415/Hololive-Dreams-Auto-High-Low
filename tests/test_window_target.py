import contextlib
import io
import unittest
from unittest.mock import patch

import numpy as np

import auto_bot as bot
import window_target as wt


class WindowTargetTests(unittest.TestCase):
    def setUp(self):
        wt.clear_capture_cache()
        bot.set_target_window()

    def tearDown(self):
        wt.clear_capture_cache()
        bot.set_target_window()

    def test_select_best_render_child_ignores_chrome_and_toolbar(self):
        # Simulated emulator window: 1280x720 Android viewport + 36px titlebar + 48px right toolbar
        root_rect = (100, 100, 1328, 756)
        children = [
            (201, (100, 100, 1328, 36), "Qt5QWindowIcon"),       # Top bar (too short)
            (202, (1380, 136, 48, 720), "ToolbarWindow"),       # Right sidebar (too narrow)
            (203, (100, 136, 1280, 720), "nemuwin"),            # Actual 16:9 Android render canvas
        ]
        child_hwnd, rect = wt.select_best_render_child(root_rect, children)
        self.assertEqual(child_hwnd, 203)
        self.assertEqual(rect, (100, 136, 1280, 720))

    def test_select_best_render_child_keeps_root_for_16_9_pc_window(self):
        root_rect = (0, 0, 1920, 1080)
        children = [
            (301, (0, 0, 1920, 1080), "Chrome_RenderWidgetHostHWND"),
        ]
        child_hwnd, rect = wt.select_best_render_child(root_rect, children)
        self.assertIsNone(child_hwnd)
        self.assertEqual(rect, root_rect)

    def test_apply_crop_rect_computes_and_clamps_subregion(self):
        self.assertEqual(wt.apply_crop_rect((100, 200, 1280, 720), None), (100, 200, 1280, 720))
        cropped = wt.apply_crop_rect((100, 200, 1000, 800), (0.1, 0.25, 0.5, 0.5))
        self.assertEqual(cropped, (200, 400, 500, 400))

    def test_window_sort_prioritizes_game_then_emulators(self):
        wins = [
            wt.WindowInfo(1, "Notepad", 800, 600),
            wt.WindowInfo(2, "MuMu模拟器12", 1280, 720),
            wt.WindowInfo(3, "hololive-Dreams", 1920, 1080),
            wt.WindowInfo(4, "雷电模拟器", 1280, 720),
        ]
        ordered = sorted(wins, key=lambda w: wt._window_sort_key(w, "hololive-Dreams"))
        self.assertEqual([w.title for w in ordered], [
            "hololive-Dreams", "MuMu模拟器12", "雷电模拟器", "Notepad"
        ])

    def test_capture_falls_back_to_root_crop_then_mss_with_caching(self):
        blank = np.zeros((720, 1280, 3), dtype=np.uint8)
        solid_gray = np.full((756, 1328, 3), 40, dtype=np.uint8)
        root_with_game = np.full((756, 1328, 3), 30, dtype=np.uint8)
        root_with_game[36:756, 0:1280, :] = (np.arange(1280) % 250).astype(np.uint8)[None, :, None]

        # 1) Child PrintWindow blank -> Root PrintWindow succeeds & crops child
        with patch.object(wt, "resolve_render_viewport", return_value=(1000, 1001, (100, 136, 1280, 720))), \
             patch.object(wt, "get_client_geometry", return_value=(100, 100, 1328, 756)), \
             patch.object(wt, "_capture_client_with_printwindow", side_effect=[blank, root_with_game]):
            frame, ctx = wt.capture_window_frame(1000)
        self.assertEqual(frame.shape, (720, 1280, 3))
        self.assertEqual(ctx["capture_method"], "printwindow_root")

        wt.clear_capture_cache()

        # 2) Both PrintWindow calls solid/blank -> switches to mss and caches 'mss' mode
        live_frame = np.random.default_rng(42).integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)
        pw_calls = []

        def fake_pw(hwnd, w, h):
            pw_calls.append(hwnd)
            return blank if hwnd == 1001 else solid_gray

        with patch.object(wt, "resolve_render_viewport", return_value=(1000, 1001, (100, 136, 1280, 720))), \
             patch.object(wt, "get_client_geometry", return_value=(100, 100, 1328, 756)), \
             patch.object(wt, "_capture_client_with_printwindow", side_effect=fake_pw), \
             patch.object(wt, "bring_window_to_front", return_value=True), \
             patch.object(wt, "_grab_mss_region", return_value=live_frame) as mock_mss, \
             contextlib.redirect_stdout(io.StringIO()):
            frame1, ctx1 = wt.capture_window_frame(1000)
            self.assertEqual(ctx1["capture_method"], "mss")
            self.assertEqual(len(pw_calls), 2)

            # Second capture should go straight to mss without retrying PrintWindow
            frame2, ctx2 = wt.capture_window_frame(1000)
            self.assertEqual(ctx2["capture_method"], "mss")
            self.assertEqual(len(pw_calls), 2)
            self.assertEqual(mock_mss.call_count, 2)
            np.testing.assert_array_equal(frame1, live_frame)
            np.testing.assert_array_equal(frame2, live_frame)

    def test_safe_click_maps_normalized_coords_to_emulator_viewport_and_crop(self):
        fake_frame = np.random.default_rng(7).integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)
        bot.set_target_window(hwnd=5000, title="MuMu模拟器12", crop_rect=(0.25, 0.25, 0.5, 0.5))

        with patch.object(bot._user32, "IsWindow", return_value=1), \
             patch.object(bot, "get_root_hwnd", return_value=5000), \
             patch.object(bot, "get_window_title", return_value="MuMu模拟器12"), \
             patch.object(bot, "warn_if_target_elevated"), \
             patch.object(wt, "resolve_render_viewport", return_value=(5000, 5001, (200, 150, 1280, 720))), \
             patch.object(wt, "_capture_client_with_printwindow", return_value=fake_frame), \
             contextlib.redirect_stdout(io.StringIO()):
            norm, left, top = bot.capture_game_window()

        self.assertEqual(norm.shape, (1080, 1920, 3))
        # Crop of (200, 150, 1280, 720) with (0.25, 0.25, 0.5, 0.5) => (520, 330, 640, 360)
        self.assertEqual((left, top), (520, 330))

        clicks = []
        with patch.object(bot, "_bring_game_to_front", return_value=True) as mock_front, \
             patch.object(bot, "resolve_render_viewport", return_value=(5000, 5001, (200, 150, 1280, 720))), \
             patch.object(bot, "click_at_screen", side_effect=lambda x, y: clicks.append((x, y))):
            ok = bot.safe_click(960, 540, left, top)

        self.assertTrue(ok)
        mock_front.assert_called_once_with(5000)
        cx, cy = clicks[0]
        # Center of (520, 330, 640, 360) is (840, 510), +/- 4px random offset
        self.assertTrue(836 <= cx <= 844, f"cx={cx} out of expected range")
        self.assertTrue(506 <= cy <= 514, f"cy={cy} out of expected range")

    def test_resolve_target_hwnd_refinds_by_title_when_hwnd_closes(self):
        bot.set_target_window(hwnd=999999, title="雷电模拟器")
        with patch.object(bot._user32, "IsWindow", return_value=0), \
             patch.object(bot, "find_window_by_title", return_value=7777), \
             patch.object(bot, "get_root_hwnd", return_value=7777):
            self.assertEqual(bot.resolve_target_hwnd(), 7777)


if __name__ == "__main__":
    unittest.main()
