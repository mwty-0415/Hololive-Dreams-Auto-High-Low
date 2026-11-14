import ctypes

# Configure DPI before Tk or any capture/input library creates a window. This
# keeps template coordinates aligned on scaled and multi-monitor desktops.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import sys
import os
import json
import time
import re
import cv2
from PIL import Image, ImageTk
import keyboard

import adb_target
import auto_bot
import window_target

# 🚀 必须在窗口创建前执行：通知 Windows 这是一个独立应用，强制任务栏绑定自身图标
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("hololive.dreams.autobot.v1")
except Exception:
    pass

# ================= 多语言翻译字典 =================
TRANSLATIONS = {
    "zh": {
        "title": "Hololive Dreams 自动猜高低",
        "lang_label": "界面语言",
        "hotkey_label": "停止快捷键",
        "target_label": "目标窗口",
        "target_auto": "自动匹配 (hololive-Dreams)",
        "btn_refresh": "刷新",
        "btn_region": "框选",
        "btn_region_active": "区域*",
        "btn_adb": "ADB 连接",
        "btn_diag": "识别测试",
        "btn_calib": "校准账本",
        "minimized": "最小化",
        "status_idle": "状态：等待启动",
        "status_running": "状态：运行中...",
        "status_stopping": "状态：正在停止...",
        "status_crashed": "状态：崩溃异常",
        "coins_prefix": "金币：{coins} / 20000",
        "btn_exit": "退出",
        "btn_start": "启动挂机",
        "btn_stop": "停止挂机",
        "btn_bg": "切换背景",
        "btn_running": "运行中...",
        "no_target_title": "未找到目标",
        "no_target_msg": "请先打开游戏/模拟器窗口，或通过「ADB 连接」连接设备后再试。",
        "region_title": "预览与框选游戏区域",
        "region_hint": "当前渲染区: {w}x{h} ({ratio}) | 可拖动框选实际 16:9 游戏画面（无工具栏/黑边时可直接关闭或点重置）",
        "region_lock_16_9": "锁定 16:9 比例",
        "region_apply": "确认区域",
        "region_reset": "重置为自动",
        "region_cancel": "取消",
        "adb_title": "ADB 后台静默连接",
        "adb_exe_label": "ADB 路径：",
        "adb_browse": "浏览...",
        "adb_addr_label": "连接地址：",
        "adb_probe": "自动扫描端口",
        "adb_connect": "连接并设为目标",
        "adb_close": "关闭",
        "diag_title": "识别诊断（当前画面测试）",
        "diag_refresh": "重新抓取并检测",
        "calib_title": "校准今日账本（03:00 ~ 次日 02:59）",
        "calib_date": "当前游戏日：{date}（每日凌晨 03:00 自动重置）",
        "calib_coins": "当前金币：",
        "calib_fails": "累计失败次数：",
        "calib_stage": "三阶段进度 (0-3)：",
        "calib_save": "保存校准",
        "calib_reset": "清零今日",
    },
    "tw": {
        "title": "Hololive Dreams 自動猜高低",
        "lang_label": "介面語言",
        "hotkey_label": "停止快捷鍵",
        "target_label": "目標視窗",
        "target_auto": "自動匹配 (hololive-Dreams)",
        "btn_refresh": "刷新",
        "btn_region": "框選",
        "btn_region_active": "區域*",
        "btn_adb": "ADB 連線",
        "btn_diag": "識別測試",
        "btn_calib": "校準帳本",
        "minimized": "最小化",
        "status_idle": "狀態：等待啟動",
        "status_running": "狀態：運行中...",
        "status_stopping": "狀態：正在停止...",
        "status_crashed": "狀態：崩潰異常",
        "coins_prefix": "金幣：{coins} / 20000",
        "btn_exit": "退出",
        "btn_start": "啟動掛機",
        "btn_stop": "停止掛機",
        "btn_bg": "切換背景",
        "btn_running": "運行中...",
        "no_target_title": "找不到目標",
        "no_target_msg": "請先開啟遊戲/模擬器視窗，或透過「ADB 連線」連接裝置後再試。",
        "region_title": "預覽與框選遊戲區域",
        "region_hint": "目前渲染區: {w}x{h} ({ratio}) | 可拖曳框選實際 16:9 遊戲畫面（無工具列/黑邊時可直接關閉或點重置）",
        "region_lock_16_9": "鎖定 16:9 比例",
        "region_apply": "確認區域",
        "region_reset": "重設為自動",
        "region_cancel": "取消",
        "adb_title": "ADB 後台靜默連線",
        "adb_exe_label": "ADB 路徑：",
        "adb_browse": "瀏覽...",
        "adb_addr_label": "連線位址：",
        "adb_probe": "自動掃描連接埠",
        "adb_connect": "連線並設為目標",
        "adb_close": "關閉",
        "diag_title": "識別診斷（目前畫面測試）",
        "diag_refresh": "重新擷取並檢測",
        "calib_title": "校準今日帳本（03:00 ~ 次日 02:59）",
        "calib_date": "目前遊戲日：{date}（每日凌晨 03:00 自動重置）",
        "calib_coins": "目前金幣：",
        "calib_fails": "累計失敗次數：",
        "calib_stage": "三階段進度 (0-3)：",
        "calib_save": "儲存校準",
        "calib_reset": "歸零今日",
    },
    "en": {
        "title": "Hololive Dreams Auto Bot",
        "lang_label": "Language",
        "hotkey_label": "Stop Hotkey",
        "target_label": "Target",
        "target_auto": "Auto (hololive-Dreams)",
        "btn_refresh": "Sync",
        "btn_region": "Crop",
        "btn_region_active": "Crop*",
        "btn_adb": "ADB",
        "btn_diag": "Diagnose",
        "btn_calib": "Calibrate",
        "minimized": "Minimized",
        "status_idle": "Status: Waiting",
        "status_running": "Status: Running...",
        "status_stopping": "Status: Stopping...",
        "status_crashed": "Status: Error",
        "coins_prefix": "Coins: {coins} / 20000",
        "btn_exit": "Exit",
        "btn_start": "Start Bot",
        "btn_stop": "Stop Bot",
        "btn_bg": "Toggle BG",
        "btn_running": "Running...",
        "no_target_title": "Target Not Found",
        "no_target_msg": "Please open the game/emulator window or connect via ADB first.",
        "region_title": "Preview & Crop Game Area",
        "region_hint": "Viewport: {w}x{h} ({ratio}) | Drag to select the 16:9 game area if toolbars or black bars are visible.",
        "region_lock_16_9": "Lock 16:9 Aspect",
        "region_apply": "Apply Crop",
        "region_reset": "Reset Auto",
        "region_cancel": "Cancel",
        "adb_title": "ADB Background Connection",
        "adb_exe_label": "ADB Path:",
        "adb_browse": "Browse...",
        "adb_addr_label": "Endpoint:",
        "adb_probe": "Scan Common Ports",
        "adb_connect": "Connect & Select",
        "adb_close": "Close",
        "diag_title": "Recognition Diagnostics",
        "diag_refresh": "Recapture & Test",
        "calib_title": "Calibrate Ledger (03:00 ~ 02:59)",
        "calib_date": "Game Day: {date} (Resets daily at 03:00)",
        "calib_coins": "Current Coins:",
        "calib_fails": "Fail Count:",
        "calib_stage": "Phased Stage (0-3):",
        "calib_save": "Save",
        "calib_reset": "Reset Today",
    },
    "ja": {
        "title": "Hololive Dreams 自動Bot",
        "lang_label": "言語",
        "hotkey_label": "停止ショートカット",
        "target_label": "対象窓",
        "target_auto": "自動検出 (hololive-Dreams)",
        "btn_refresh": "更新",
        "btn_region": "範囲",
        "btn_region_active": "範囲*",
        "btn_adb": "ADB接続",
        "btn_diag": "認識テスト",
        "btn_calib": "収支調整",
        "minimized": "最小化",
        "status_idle": "ステータス: 待機中",
        "status_running": "ステータス: 実行中...",
        "status_stopping": "ステータス: 停止中...",
        "status_crashed": "ステータス: エラー",
        "coins_prefix": "コイン: {coins} / 20000",
        "btn_exit": "終了",
        "btn_start": "起動",
        "btn_stop": "停止",
        "btn_bg": "背景切替",
        "btn_running": "実行中...",
        "no_target_title": "対象が見つかりません",
        "no_target_msg": "先にゲーム／エミュレータを開くか、ADB接続を行ってください。",
        "region_title": "ゲーム画面のプレビューと範囲選択",
        "region_hint": "検出サイズ: {w}x{h} ({ratio}) | ツールバーや黒帯がある場合は 16:9 のゲーム画面をドラッグで囲ってください。",
        "region_lock_16_9": "16:9 比率を固定",
        "region_apply": "確定",
        "region_reset": "自動に戻す",
        "region_cancel": "キャンセル",
        "adb_title": "ADB バックグラウンド接続",
        "adb_exe_label": "ADB パス:",
        "adb_browse": "参照...",
        "adb_addr_label": "接続先:",
        "adb_probe": "ポート自動スキャン",
        "adb_connect": "接続して選択",
        "adb_close": "閉じる",
        "diag_title": "認識診断テスト",
        "diag_refresh": "再取得してテスト",
        "calib_title": "本日データ調整 (03:00 ~ 翌02:59)",
        "calib_date": "ゲーム日: {date}（毎日 03:00 リセット）",
        "calib_coins": "累計コイン:",
        "calib_fails": "失敗回数:",
        "calib_stage": "3段階進捗 (0-3):",
        "calib_save": "保存",
        "calib_reset": "本日リセット",
    }
}

WINDOW_CONFIG_FILE = auto_bot.APP_DIR / "window_config.json"


STRATEGY_LABELS = {
    'zh': ('1.0.1 原版', '三阶段：最大 → 计次 → 最大'),
    'tw': ('1.0.1 原版', '三階段：最大 → 計次 → 最大'),
    'en': ('1.0.1 Legacy', '3 stages: Max → Win count → Max'),
    'ja': ('1.0.1 従来モード', '3段階：最大 → 成功回数 → 最大'),
}


def get_local_data():
    today = auto_bot.get_game_date_str()
    if auto_bot.DATA_FILE.exists():
        try:
            with auto_bot.DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == today:
                    c = data.get("coins", 0)
                    fl = data.get("fails", 0)
                    return c, fl, c - (fl * 50)
        except Exception:
            pass
    return 0, 0, 0


# ================= 拦截底层输出，虚拟滚动核心引擎 =================
class RedirectText:
    def __init__(self, ui):
        self.ui = ui
        self.raw_text = ""

    def write(self, string):
        self.ui.after(0, self._write, string)

    def _write(self, string):
        if not string: return
        self.raw_text += string

        if "今日净利润:" in string:
            m_profit = re.search(r"今日净利润:\s*([+-]?\d+)", string)
            m_fails = re.search(r"累计失败:\s*(\d+)", string)
            m_coins = re.search(r"当前总金币:\s*(\d+)", string) or re.search(r"当日累计代币:\s*(\d+)", string)

            coins = int(m_coins.group(1)) if m_coins else self.ui.current_coins
            fails = int(m_fails.group(1)) if m_fails else self.ui.current_fails
            profit = int(m_profit.group(1)) if m_profit else self.ui.current_profit

            self.ui.update_stats_display(coins, fails, profit)

        if len(self.raw_text) > 15000:
            self.raw_text = self.raw_text[-15000:]
            newline_idx = self.raw_text.find('\n')
            if newline_idx != -1:
                self.raw_text = self.raw_text[newline_idx + 1:]

        self.ui.log_lines = self.raw_text.split('\n')
        self.ui.log_view_start = max(0, len(self.ui.log_lines) - self.ui.log_max_lines)
        self.ui.update_log_view()

    def flush(self):
        pass

    def clear(self):
        self.raw_text = ""
        self.ui.log_lines = []
        self.ui.log_view_start = 0
        self.ui.update_log_view()


def load_window_config():
    if WINDOW_CONFIG_FILE.exists():
        try:
            with WINDOW_CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {"last_target_title": None, "crops": {}}


def save_window_config(config):
    try:
        tmp = WINDOW_CONFIG_FILE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WINDOW_CONFIG_FILE)
    except Exception:
        pass


class RegionCropDialog(tk.Toplevel):
    """Preview the captured target window and optionally drag-select the 16:9 game area."""

    def __init__(self, parent, frame_bgr, current_crop, texts):
        super().__init__(parent)
        self.result = None
        self.confirmed = False
        self.texts = texts
        self.title(texts["region_title"])
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        fh, fw = frame_bgr.shape[:2]
        ratio = f"{fw / max(1, fh):.2f}:1"
        if abs((fw / max(1, fh)) - (16.0 / 9.0)) < 0.03:
            ratio = "16:9"

        max_w, max_h = 880, 500
        scale = min(max_w / fw, max_h / fh, 1.0)
        self.disp_w = max(1, round(fw * scale))
        self.disp_h = max(1, round(fh * scale))

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb).resize((self.disp_w, self.disp_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(pil_img)

        header = ttk.Label(
            self,
            text=texts["region_hint"].format(w=fw, h=fh, ratio=ratio),
            padding=(10, 8),
        )
        header.pack(fill="x")

        self.preview_canvas = tk.Canvas(
            self, width=self.disp_w, height=self.disp_h, cursor="crosshair", highlightthickness=1
        )
        self.preview_canvas.pack(padx=10, pady=(0, 8))
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self._photo)

        self.rect_id = None
        self.start_x = 0
        self.start_y = 0
        self.sel_box = None
        if current_crop:
            rx, ry, rw, rh = current_crop
            self.sel_box = (
                round(rx * self.disp_w),
                round(ry * self.disp_h),
                round((rx + rw) * self.disp_w),
                round((ry + rh) * self.disp_h),
            )
            self.rect_id = self.preview_canvas.create_rectangle(
                *self.sel_box, outline="#00FF66", width=2
            )

        self.preview_canvas.bind("<ButtonPress-1>", self._on_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_release)

        controls = ttk.Frame(self, padding=(10, 0, 10, 10))
        controls.pack(fill="x")

        self.lock_aspect = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls, text=texts["region_lock_16_9"], variable=self.lock_aspect
        ).pack(side="left")

        ttk.Button(controls, text=texts["region_cancel"], command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(controls, text=texts["region_reset"], command=self._reset_crop).pack(side="right", padx=(6, 0))
        ttk.Button(controls, text=texts["region_apply"], command=self._apply_crop).pack(side="right")

        self.lift()
        self.focus_force()

    def _clamp_box(self, x1, y1, x2, y2):
        if self.lock_aspect.get():
            dx = x2 - x1
            dy = y2 - y1
            sign_x = 1 if dx >= 0 else -1
            sign_y = 1 if dy >= 0 else -1
            w = abs(dx)
            h = round(w * 9.0 / 16.0)
            if abs(dy) > h:
                h = abs(dy)
                w = round(h * 16.0 / 9.0)
            x2 = x1 + sign_x * w
            y2 = y1 + sign_y * h

        left = max(0, min(x1, x2))
        right = min(self.disp_w, max(x1, x2))
        top = max(0, min(y1, y2))
        bottom = min(self.disp_h, max(y1, y2))
        return left, top, right, bottom

    def _on_press(self, event):
        self.start_x = max(0, min(self.disp_w, event.x))
        self.start_y = max(0, min(self.disp_h, event.y))

    def _on_drag(self, event):
        cur_x = max(0, min(self.disp_w, event.x))
        cur_y = max(0, min(self.disp_h, event.y))
        self.sel_box = self._clamp_box(self.start_x, self.start_y, cur_x, cur_y)
        if self.rect_id is None:
            self.rect_id = self.preview_canvas.create_rectangle(
                *self.sel_box, outline="#00FF66", width=2
            )
        else:
            self.preview_canvas.coords(self.rect_id, *self.sel_box)

    def _on_release(self, event):
        self._on_drag(event)

    def _apply_crop(self):
        if self.sel_box is not None:
            x1, y1, x2, y2 = self.sel_box
            if (x2 - x1) >= 40 and (y2 - y1) >= 24:
                self.result = (
                    x1 / self.disp_w,
                    y1 / self.disp_h,
                    (x2 - x1) / self.disp_w,
                    (y2 - y1) / self.disp_h,
                )
        self.confirmed = True
        self.destroy()

    def _reset_crop(self):
        self.result = None
        self.confirmed = True
        self.destroy()


class AdbConnectDialog(tk.Toplevel):
    """Configure adb.exe path and connect/probe emulator ADB endpoints."""

    def __init__(self, parent, adb_path, last_endpoint, texts, on_connected):
        super().__init__(parent)
        self.texts = texts
        self.on_connected = on_connected
        self.title(texts["adb_title"])
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=texts["adb_exe_label"]).grid(row=0, column=0, sticky="w", pady=4)
        detected = adb_target.find_adb_executable(adb_path) or ""
        self.var_adb_path = tk.StringVar(value=adb_path or detected)
        ttk.Entry(frame, textvariable=self.var_adb_path, width=38).grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        ttk.Button(frame, text=texts["adb_browse"], command=self._browse_adb).grid(row=0, column=2, pady=4)

        ttk.Label(frame, text=texts["adb_addr_label"]).grid(row=1, column=0, sticky="w", pady=4)
        self.var_addr = tk.StringVar(value=last_endpoint or "127.0.0.1:16384")
        ttk.Entry(frame, textvariable=self.var_addr, width=38).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Button(frame, text=texts["adb_connect"], command=self._connect).grid(row=1, column=2, pady=4)

        presets = ttk.Frame(frame)
        presets.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 4))
        for label, addr in [
            ("MuMu12 (16384)", "127.0.0.1:16384"),
            ("MuMu6 (7555)", "127.0.0.1:7555"),
            ("雷电/BS (5555)", "127.0.0.1:5555"),
            ("夜神 (62001)", "127.0.0.1:62001"),
            ("逍遥 (21503)", "127.0.0.1:21503"),
        ]:
            ttk.Button(presets, text=label, command=lambda a=addr: self.var_addr.set(a)).pack(side="left", padx=2)

        self.var_status = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.var_status, foreground="#2255AA", wraplength=480).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=6
        )

        btns = ttk.Frame(frame)
        btns.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        ttk.Button(btns, text=texts["adb_probe"], command=self._probe).pack(side="left")
        ttk.Button(btns, text=texts["adb_close"], command=self.destroy).pack(side="right")

        self.lift()
        self.focus_force()

    def _browse_adb(self):
        path = filedialog.askopenfilename(
            parent=self,
            title=self.texts["adb_title"],
            filetypes=[("ADB Executable", "adb*.exe;nox_adb.exe;HD-Adb.exe"), ("All Files", "*.*")],
        )
        if path:
            self.var_adb_path.set(path)

    def _current_adb_path(self):
        val = self.var_adb_path.get().strip()
        return val or None

    def _connect(self):
        addr = self.var_addr.get().strip()
        adb_path = self._current_adb_path()
        try:
            ok, msg = adb_target.connect_adb_endpoint(addr, adb_path=adb_path)
            self.var_status.set(msg)
            if ok:
                self.on_connected(adb_path, addr, addr)
        except Exception as exc:
            self.var_status.set(str(exc))

    def _probe(self):
        adb_path = self._current_adb_path()
        try:
            devices, logs = adb_target.auto_probe_common_ports(adb_path=adb_path)
            ready = [d for d in devices if d.ready]
            if ready:
                self.var_status.set("已发现可用设备: " + ", ".join(d.serial for d in ready))
                self.on_connected(adb_path, self.var_addr.get().strip(), ready[0].serial)
            elif logs:
                self.var_status.set("\n".join(logs))
            else:
                self.var_status.set("未检测到常见本地模拟器 ADB 端口，请确认模拟器已启动并开启 ADB 调试。")
        except Exception as exc:
            self.var_status.set(str(exc))


class DiagnoseDialog(tk.Toplevel):
    """Capture one frame and overlay state/card/OCR diagnostics."""

    def __init__(self, parent, capture_fn, texts):
        super().__init__(parent)
        self.capture_fn = capture_fn
        self.texts = texts
        self.title(texts["diag_title"])
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.var_info = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.var_info, padding=(10, 8), justify="left").pack(fill="x")

        self.img_label = ttk.Label(self)
        self.img_label.pack(padx=10, pady=(0, 8))

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill="x")
        ttk.Button(btns, text=texts["diag_refresh"], command=self.run_diagnose).pack(side="left")
        ttk.Button(btns, text=texts["adb_close"], command=self.destroy).pack(side="right")

        self._photo = None
        self.run_diagnose()
        self.lift()
        self.focus_force()

    def run_diagnose(self):
        res = self.capture_fn()
        if res is None:
            self.destroy()
            return
        frame_norm, raw_shape = res
        annotated, report = auto_bot.diagnose_frame(frame_norm)
        disp = cv2.resize(annotated, (880, 495), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.img_label.configure(image=self._photo)

        cards = ", ".join(report["cards"]) if report["cards"] else "-"
        self.var_info.set(
            f"原始画面: {raw_shape[1]}x{raw_shape[0]} | 识别状态: {report['state']} "
            f"(最高模板: {report['best_template']} = {report['best_score']:.2f})\n"
            f"识别牌面: {cards} | 挑战金额 OCR: {report['challenge_ocr']} | 结算金额 OCR: {report['result_ocr']}"
        )


class CalibrateLedgerDialog(tk.Toplevel):
    """View or manually adjust today's shared ledger (03:00 ~ next day 02:59)."""

    def __init__(self, parent, texts, on_saved):
        super().__init__(parent)
        self.texts = texts
        self.on_saved = on_saved
        self.title(texts["calib_title"])
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        coins, fails = auto_bot.load_daily_data()
        try:
            stage = auto_bot.load_daily_stage()
        except Exception:
            stage = 0

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=texts["calib_date"].format(date=auto_bot.get_game_date_str()),
            foreground="#2255AA",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(frame, text=texts["calib_coins"]).grid(row=1, column=0, sticky="w", pady=4)
        self.var_coins = tk.StringVar(value=str(coins))
        ttk.Entry(frame, textvariable=self.var_coins, width=18).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frame, text=texts["calib_fails"]).grid(row=2, column=0, sticky="w", pady=4)
        self.var_fails = tk.StringVar(value=str(fails))
        ttk.Entry(frame, textvariable=self.var_fails, width=18).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frame, text=texts["calib_stage"]).grid(row=3, column=0, sticky="w", pady=4)
        self.var_stage = tk.StringVar(value=str(stage))
        ttk.Combobox(frame, textvariable=self.var_stage, values=["0", "1", "2", "3"], state="readonly", width=15).grid(
            row=3, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        btns = ttk.Frame(frame)
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(btns, text=texts["calib_reset"], command=self._reset_today).pack(side="left")
        ttk.Button(btns, text=texts["region_cancel"], command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text=texts["calib_save"], command=self._save).pack(side="right")

        self.lift()
        self.focus_force()

    def _save(self):
        try:
            coins = max(0, int(self.var_coins.get().strip()))
            fails = max(0, int(self.var_fails.get().strip()))
            stage = int(self.var_stage.get().strip())
            if not 0 <= stage <= 3:
                raise ValueError
        except ValueError:
            messagebox.showwarning(self.texts["calib_title"], "请输入有效的非负整数（阶段为 0~3）。", parent=self)
            return
        auto_bot.save_daily_data(coins, fails, stage)
        self.on_saved(coins, fails)
        self.destroy()

    def _reset_today(self):
        auto_bot.save_daily_data(0, 0, 0)
        self.on_saved(0, 0)
        self.destroy()


class HololiveBotUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.bot_thread = None
        self.is_running = False
        self.current_lang = "zh"
        self.show_bg = True

        self.window_config = load_window_config()
        saved_lang = self.window_config.get("lang", "zh")
        if saved_lang in ["zh", "tw", "en", "ja"]:
            self.current_lang = saved_lang

        self.current_coins, self.current_fails, self.current_profit = get_local_data()

        self.title(TRANSLATIONS[self.current_lang]["title"])
        # 🚀 替换这里的两行：优先加载 PNG 图标，任务栏永不退化为白纸
        try:
            transparent_icon = auto_bot.RESOURCE_DIR / "icon_transparent.png"
            png_icon = auto_bot.RESOURCE_DIR / "icon.png"
            ico_icon = auto_bot.RESOURCE_DIR / "icon.ico"
            if transparent_icon.exists():
                self._app_icon = ImageTk.PhotoImage(file=str(transparent_icon))
                self.iconphoto(True, self._app_icon)
            elif png_icon.exists():
                self._app_icon = ImageTk.PhotoImage(file=str(png_icon))
                self.iconphoto(True, self._app_icon)
            elif ico_icon.exists():
                self.iconbitmap(str(ico_icon))
        except Exception as e:
            print(f"[警告] 图标加载失败: {e}")

        self.geometry("450x800")
        self.minsize(360, 640)

        self.last_w = 450
        self.last_h = 800

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_image_path = auto_bot.RESOURCE_DIR / "background.png"
        if self.bg_image_path.exists():
            self.original_bg = Image.open(self.bg_image_path)
        else:
            self.original_bg = Image.new('RGB', (450, 800), color='#F0F0F0')
            self.show_bg = False

        self.bg_id = self.canvas.create_image(0, 0, anchor="nw")

        font_title = ("Microsoft YaHei", 16, "bold")
        font_normal = ("Microsoft YaHei", 12, "bold")
        font_log = ("Microsoft YaHei", 12, "bold")

        self.title_id = self.canvas.create_text(0, 0, font=font_title, fill="#111111")

        self.lang_label_id = self.canvas.create_text(0, 0, font=font_normal, fill="#111111", anchor="w")
        self.lang_keys = ["zh", "tw", "en", "ja"]
        self.combo_lang = ttk.Combobox(self, values=["简体中文", "繁體中文", "English", "日本語"], state="readonly")
        self.combo_lang.current(self.lang_keys.index(self.current_lang))
        self.combo_lang.bind("<<ComboboxSelected>>", self.change_language)
        self.combo_window = self.canvas.create_window(0, 0, window=self.combo_lang, anchor="e")

        self.hotkey_label_id = self.canvas.create_text(0, 0, font=font_normal, fill="#111111", anchor="w")
        self.current_hotkey = str(self.window_config.get("hotkey") or "INSERT")
        self.is_listening = False

        self.btn_hotkey = ttk.Button(self, text=self.current_hotkey, command=self.start_listen_hotkey)
        self.hotkey_window = self.canvas.create_window(0, 0, window=self.btn_hotkey, anchor="e")

        try:
            keyboard.add_hotkey(self.current_hotkey, lambda: self.after(0, self.stop_bot))
        except Exception:
            self.current_hotkey = "INSERT"
            self.btn_hotkey.configure(text=self.current_hotkey)
            keyboard.add_hotkey(self.current_hotkey, lambda: self.after(0, self.stop_bot))

        self.target_options = []
        self.selected_target_mode = self.window_config.get("last_target_mode", "auto")
        self.selected_target_hwnd = None
        self.selected_target_title = self.window_config.get("last_target_title")
        self.selected_adb_serial = self.window_config.get("last_adb_serial")
        self.adb_path = self.window_config.get("adb_path")
        self.target_label_id = self.canvas.create_text(0, 0, font=font_normal, fill="#111111", anchor="w")
        self.combo_target = ttk.Combobox(self, state="readonly", postcommand=self.refresh_target_windows)
        self.combo_target.bind("<<ComboboxSelected>>", self.on_target_selected)
        self.target_window = self.canvas.create_window(0, 0, window=self.combo_target, anchor="w")
        self.btn_refresh = ttk.Button(self, command=self.refresh_target_windows)
        self.btn_refresh_win = self.canvas.create_window(0, 0, window=self.btn_refresh)
        self.btn_region = ttk.Button(self, command=self.open_region_selector)
        self.btn_region_win = self.canvas.create_window(0, 0, window=self.btn_region)

        self.btn_adb = ttk.Button(self, command=self.open_adb_dialog)
        self.btn_adb_win = self.canvas.create_window(0, 0, window=self.btn_adb)
        self.btn_diag = ttk.Button(self, command=self.open_diagnose_dialog)
        self.btn_diag_win = self.canvas.create_window(0, 0, window=self.btn_diag)
        self.btn_calib = ttk.Button(self, command=self.open_calibrate_dialog)
        self.btn_calib_win = self.canvas.create_window(0, 0, window=self.btn_calib)

        self.status_id = self.canvas.create_text(0, 0, font=font_normal, fill="#111111", anchor="w")
        self.coins_id = self.canvas.create_text(0, 0, font=font_normal, fill="#111111", anchor="w")

        self.log_text_id = self.canvas.create_text(0, 0, font=font_log, fill="#000000", anchor="nw", justify="left")
        self.log_lines = []
        self.log_max_lines = 11
        self.log_view_start = 0

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.scroll_log)
        self.scrollbar_win = self.canvas.create_window(0, 0, window=self.scrollbar, anchor="ne")
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.btn_next = ttk.Button(self, command=self.start_bot)
        self.btn_stop = ttk.Button(self, command=self.stop_bot, state="disabled")
        self.btn_bg = ttk.Button(self, command=self.toggle_bg)
        self.btn_exit = ttk.Button(self, command=self.destroy)

        self.btn_next_win = self.canvas.create_window(0, 0, window=self.btn_next)
        self.btn_stop_win = self.canvas.create_window(0, 0, window=self.btn_stop)
        self.btn_bg_win = self.canvas.create_window(0, 0, window=self.btn_bg)
        self.btn_exit_win = self.canvas.create_window(0, 0, window=self.btn_exit)

        self.combo_strategy = ttk.Combobox(self, state='readonly',
                                           values=STRATEGY_LABELS[self.current_lang])
        saved_strategy = int(self.window_config.get("strategy", 0))
        self.combo_strategy.current(1 if saved_strategy == 1 else 0)
        self.combo_strategy.bind("<<ComboboxSelected>>", self.on_strategy_selected)
        self.strategy_window = self.canvas.create_window(0, 0, window=self.combo_strategy, anchor='nw')
        self.active_mode = 'phased' if saved_strategy == 1 else 'legacy'

        self.sys_redirector = RedirectText(self)
        self.original_stdout = sys.stdout
        sys.stdout = self.sys_redirector

        self.canvas.bind("<Configure>", self.on_resize)
        self.resize_after_id = None

        self.refresh_target_windows(initial=True)
        self.refresh_texts()

    def start_listen_hotkey(self):
        if self.is_listening or self.is_running:
            return

        self.is_listening = True
        self.btn_hotkey.configure(text="[按键...]")
        print("\n[系统] 请点击键盘上想要切换的键...")

        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self):
        time.sleep(0.1)
        while True:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name.upper()
                break

        self.after(0, self._apply_new_hotkey, key)

    def _apply_new_hotkey(self, new_key):
        self.is_listening = False
        try:
            keyboard.remove_hotkey(self.current_hotkey)
        except:
            pass

        self.current_hotkey = new_key
        try:
            keyboard.add_hotkey(self.current_hotkey, lambda: self.after(0, self.stop_bot))
            self.btn_hotkey.configure(text=self.current_hotkey)
            print(f"[系统] 停止快捷键已成功更换为: {self.current_hotkey}\n")
        except Exception as e:
            print(f"[系统] 无法绑定按键 '{new_key}'，已自动恢复默认 F11\n")
            self.current_hotkey = "F11"
            keyboard.add_hotkey(self.current_hotkey, lambda: self.after(0, self.stop_bot))
            self.btn_hotkey.configure(text=self.current_hotkey)
        self.window_config["hotkey"] = self.current_hotkey
        save_window_config(self.window_config)

    def on_mouse_wheel(self, event):
        direction = -1 if event.delta > 0 else 1
        self.scroll_log('scroll', direction * 3)

    def scroll_log(self, *args):
        if not self.log_lines: return

        if args[0] == 'moveto':
            fraction = float(args[1])
            self.log_view_start = int(fraction * len(self.log_lines))
        elif args[0] == 'scroll':
            self.log_view_start += int(args[1])

        max_start = max(0, len(self.log_lines) - self.log_max_lines)
        self.log_view_start = max(0, min(self.log_view_start, max_start))
        self.update_log_view()

    def update_log_view(self):
        max_start = max(0, len(self.log_lines) - self.log_max_lines)
        if len(self.log_lines) == 0:
            self.scrollbar.set(0.0, 1.0)
            visible = []
        else:
            fraction = self.log_view_start / max(1, len(self.log_lines))
            fraction_end = (self.log_view_start + self.log_max_lines) / max(1, len(self.log_lines))
            self.scrollbar.set(fraction, fraction_end)
            visible = self.log_lines[self.log_view_start: self.log_view_start + self.log_max_lines]

        self.canvas.itemconfig(self.log_text_id, text='\n'.join(visible))

    def on_resize(self, event):
        if event.widget != self.canvas: return
        w, h = event.width, event.height
        if w <= 10 or h <= 10: return

        target_h = int(w * 16 / 9)
        target_w = int(h * 9 / 16)

        if abs(h - target_h) <= 2:
            self.last_w, self.last_h = w, h
            self.draw_ui(w, h)
            return

        delta_w = abs(w - self.last_w)
        delta_h = abs(h - self.last_h)

        if delta_w > delta_h / (16 / 9):
            new_w = w
            new_h = target_h
        else:
            new_w = target_w
            new_h = h

        if self.resize_after_id:
            self.after_cancel(self.resize_after_id)
        self.resize_after_id = self.after(20, lambda: self.geometry(f"{new_w}x{new_h}"))

    def draw_ui(self, w, h):
        if self.show_bg:
            img = self.original_bg.resize((w, h), Image.Resampling.LANCZOS)
        else:
            img = Image.new('RGB', (w, h), color='#FFFFFF')

        self.bg_photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self.bg_id, image=self.bg_photo)

        self.canvas.coords(self.title_id, w / 2, h * 0.040)

        self.canvas.coords(self.lang_label_id, w * 0.08, h * 0.088)
        self.canvas.coords(self.combo_window, w * 0.92, h * 0.088)
        self.canvas.itemconfig(self.combo_window, width=w * 0.30)

        self.canvas.coords(self.hotkey_label_id, w * 0.08, h * 0.130)
        self.canvas.coords(self.hotkey_window, w * 0.92, h * 0.130)
        self.canvas.itemconfig(self.hotkey_window, width=w * 0.30)

        self.canvas.coords(self.target_label_id, w * 0.08, h * 0.172)
        self.canvas.coords(self.target_window, w * 0.31, h * 0.172)
        self.canvas.itemconfig(self.target_window, width=w * 0.37)
        self.canvas.coords(self.btn_refresh_win, w * 0.745, h * 0.172)
        self.canvas.itemconfig(self.btn_refresh_win, width=w * 0.11, height=h * 0.034)
        self.canvas.coords(self.btn_region_win, w * 0.865, h * 0.172)
        self.canvas.itemconfig(self.btn_region_win, width=w * 0.11, height=h * 0.034)

        tool_w = w * 0.265
        tool_h = h * 0.034
        self.canvas.coords(self.btn_adb_win, w * 0.215, h * 0.214)
        self.canvas.itemconfig(self.btn_adb_win, width=tool_w, height=tool_h)
        self.canvas.coords(self.btn_diag_win, w * 0.500, h * 0.214)
        self.canvas.itemconfig(self.btn_diag_win, width=tool_w, height=tool_h)
        self.canvas.coords(self.btn_calib_win, w * 0.785, h * 0.214)
        self.canvas.itemconfig(self.btn_calib_win, width=tool_w, height=tool_h)

        self.canvas.coords(self.status_id, w * 0.08, h * 0.262)
        self.canvas.coords(self.coins_id, w * 0.08, h * 0.312)

        btn_w = w * 0.38
        btn_h = h * 0.044

        self.canvas.coords(self.btn_next_win, w * 0.28, h * 0.375)
        self.canvas.itemconfig(self.btn_next_win, width=btn_w, height=btn_h)
        self.canvas.coords(self.btn_stop_win, w * 0.72, h * 0.375)
        self.canvas.itemconfig(self.btn_stop_win, width=btn_w, height=btn_h)

        self.canvas.coords(self.btn_bg_win, w * 0.28, h * 0.428)
        self.canvas.itemconfig(self.btn_bg_win, width=btn_w, height=btn_h)
        self.canvas.coords(self.btn_exit_win, w * 0.72, h * 0.428)
        self.canvas.itemconfig(self.btn_exit_win, width=btn_w, height=btn_h)

        log_x = w * 0.06
        self.canvas.coords(self.strategy_window, w * .06, h * .470)
        self.canvas.itemconfig(self.strategy_window, width=w * .88)
        log_y = h * 0.518
        self.canvas.coords(self.log_text_id, log_x, log_y)

        # 🚀 修改 2：给日志文字设定最大物理宽度。当碰到距离右侧 15% 的边界时，强行折行！
        self.canvas.itemconfig(self.log_text_id, width=w * 0.85)

        self.canvas.coords(self.scrollbar_win, w * 0.98, log_y)
        self.canvas.itemconfig(self.scrollbar_win, height=h * 0.44)

    def _current_crop_key(self):
        if self.selected_target_mode == "adb" and self.selected_adb_serial:
            return f"adb:{self.selected_adb_serial}"
        return self.selected_target_title or "__auto__"

    def _current_crop_rect(self):
        crops = self.window_config.get("crops", {})
        rect = crops.get(self._current_crop_key())
        if isinstance(rect, (list, tuple)) and len(rect) == 4:
            return tuple(float(v) for v in rect)
        return None

    def _sync_bot_target(self):
        if self.selected_target_mode == "adb" and self.selected_adb_serial:
            auto_bot.set_adb_target(
                serial=self.selected_adb_serial,
                adb_path=self.adb_path,
                crop_rect=self._current_crop_rect(),
            )
        else:
            auto_bot.set_target_window(
                hwnd=self.selected_target_hwnd,
                title=self.selected_target_title,
                crop_rect=self._current_crop_rect(),
                auto_detect_child=True,
            )

    def refresh_target_windows(self, initial=False):
        t = TRANSLATIONS[self.current_lang]
        try:
            candidates = window_target.list_candidate_windows(
                default_title=auto_bot.GAME_TITLE,
                exclude_pids={os.getpid()},
            )
        except Exception:
            candidates = []

        try:
            adb_devices = [d for d in adb_target.list_adb_devices(self.adb_path) if d.ready]
        except Exception:
            adb_devices = []

        title_counts = {}
        for win in candidates:
            title_counts[win.title] = title_counts.get(win.title, 0) + 1

        options = [{
            "label": t["target_auto"],
            "mode": "auto",
            "hwnd": None,
            "title": None,
            "serial": None,
        }]
        for dev in adb_devices:
            model_tag = f" ({dev.model})" if dev.model else ""
            options.append({
                "label": f"[ADB] {dev.serial}{model_tag}",
                "mode": "adb",
                "hwnd": None,
                "title": None,
                "serial": dev.serial,
            })
        for win in candidates:
            size_tag = f"{win.width}x{win.height}" if not win.minimized else t["minimized"]
            if title_counts.get(win.title, 0) > 1:
                label = f"{win.title} ({size_tag}) [0x{win.hwnd:X}]"
            else:
                label = f"{win.title} ({size_tag})"
            options.append({
                "label": label,
                "mode": "window",
                "hwnd": win.hwnd,
                "title": win.title,
                "serial": None,
            })

        self.target_options = options
        self.combo_target.configure(values=[opt["label"] for opt in options])

        selected_idx = 0
        if self.selected_target_mode == "adb" and self.selected_adb_serial:
            for idx, opt in enumerate(options[1:], start=1):
                if opt["mode"] == "adb" and opt["serial"] == self.selected_adb_serial:
                    selected_idx = idx
                    break
        elif self.selected_target_mode == "window":
            if self.selected_target_hwnd is not None:
                for idx, opt in enumerate(options[1:], start=1):
                    if opt["mode"] == "window" and opt["hwnd"] == self.selected_target_hwnd:
                        selected_idx = idx
                        break
            if selected_idx == 0 and self.selected_target_title:
                for idx, opt in enumerate(options[1:], start=1):
                    if opt["mode"] == "window" and opt["title"] == self.selected_target_title:
                        selected_idx = idx
                        break

        if selected_idx == 0 and initial:
            self.selected_target_mode = "auto"
            self.selected_target_hwnd = None
            self.selected_target_title = None
            self.selected_adb_serial = None

        self.combo_target.current(selected_idx)
        chosen = options[selected_idx]
        self.selected_target_mode = chosen["mode"]
        self.selected_target_hwnd = chosen["hwnd"]
        self.selected_target_title = chosen["title"]
        self.selected_adb_serial = chosen["serial"]
        self._sync_bot_target()
        if not initial:
            self._update_region_button_text()

    def on_target_selected(self, event=None):
        idx = self.combo_target.current()
        if idx < 0 or idx >= len(self.target_options):
            return
        chosen = self.target_options[idx]
        self.selected_target_mode = chosen["mode"]
        self.selected_target_hwnd = chosen["hwnd"]
        self.selected_target_title = chosen["title"]
        self.selected_adb_serial = chosen["serial"]
        self.window_config["last_target_mode"] = self.selected_target_mode
        self.window_config["last_target_title"] = self.selected_target_title
        self.window_config["last_adb_serial"] = self.selected_adb_serial
        save_window_config(self.window_config)
        self._sync_bot_target()
        self._update_region_button_text()
        print(f"[目标] 当前已选择: {chosen['label']}")

    def _update_region_button_text(self):
        t = TRANSLATIONS[self.current_lang]
        has_crop = self._current_crop_rect() is not None
        self.btn_region.configure(text=t["btn_region_active"] if has_crop else t["btn_region"])

    def _capture_preview_frame(self, apply_crop=False):
        t = TRANSLATIONS[self.current_lang]
        self._sync_bot_target()
        crop = self._current_crop_rect() if apply_crop else None
        if self.selected_target_mode == "adb":
            if not self.selected_adb_serial:
                messagebox.showwarning(t["no_target_title"], t["no_target_msg"], parent=self)
                return None
            try:
                frame, _ = adb_target.adb_capture_frame(
                    self.selected_adb_serial, adb_path=self.adb_path, crop_rect=crop
                )
                return frame
            except Exception as exc:
                messagebox.showwarning(t["no_target_title"], f"{t['no_target_msg']}\n({exc})", parent=self)
                return None

        hwnd = auto_bot.resolve_target_hwnd()
        if not hwnd:
            messagebox.showwarning(t["no_target_title"], t["no_target_msg"], parent=self)
            return None
        try:
            frame, _ = window_target.capture_window_frame(hwnd, crop_rect=crop, auto_detect_child=True)
            return frame
        except Exception as exc:
            messagebox.showwarning(t["no_target_title"], f"{t['no_target_msg']}\n({exc})", parent=self)
            return None

    def open_region_selector(self):
        if self.is_running:
            return
        t = TRANSLATIONS[self.current_lang]
        frame = self._capture_preview_frame(apply_crop=False)
        if frame is None:
            return

        dialog = RegionCropDialog(self, frame, self._current_crop_rect(), t)
        self.wait_window(dialog)
        if dialog.confirmed:
            crops = self.window_config.setdefault("crops", {})
            key = self._current_crop_key()
            if dialog.result is None:
                crops.pop(key, None)
                print("[窗口] 已重置游戏区域为自动识别。")
            else:
                crops[key] = [round(v, 4) for v in dialog.result]
                print("[窗口] 已保存自定义游戏区域。")
            save_window_config(self.window_config)
            self._sync_bot_target()
            self._update_region_button_text()

    def open_adb_dialog(self):
        if self.is_running:
            return
        t = TRANSLATIONS[self.current_lang]

        def _on_connected(adb_path, endpoint, serial):
            self.adb_path = adb_path
            self.selected_target_mode = "adb"
            self.selected_adb_serial = serial
            self.selected_target_hwnd = None
            self.selected_target_title = None
            self.window_config["adb_path"] = adb_path
            self.window_config["last_adb_endpoint"] = endpoint
            self.window_config["last_target_mode"] = "adb"
            self.window_config["last_adb_serial"] = serial
            save_window_config(self.window_config)
            self.refresh_target_windows()
            print(f"[ADB] 已切换至后台设备: {serial}")

        AdbConnectDialog(
            self,
            self.adb_path,
            self.window_config.get("last_adb_endpoint"),
            t,
            _on_connected,
        )

    def open_diagnose_dialog(self):
        if self.is_running:
            return
        t = TRANSLATIONS[self.current_lang]

        def _capture_for_diag():
            raw = self._capture_preview_frame(apply_crop=True)
            if raw is None:
                return None
            norm = cv2.resize(raw, (auto_bot.REFERENCE_WIDTH, auto_bot.REFERENCE_HEIGHT), interpolation=cv2.INTER_CUBIC)
            return norm, raw.shape

        DiagnoseDialog(self, _capture_for_diag, t)

    def open_calibrate_dialog(self):
        if self.is_running:
            return
        t = TRANSLATIONS[self.current_lang]

        def _on_saved(coins, fails):
            self.update_stats_display(coins, fails, coins - fails * 50)
            print(f"[账本] 已手动校准今日数据: 金币 {coins}, 失败 {fails} 次。")

        CalibrateLedgerDialog(self, t, _on_saved)

    def toggle_bg(self):
        self.show_bg = not self.show_bg
        self.draw_ui(self.winfo_width(), self.winfo_height())

    def update_stats_display(self, coins=None, fails=None, profit=None):
        if coins is not None: self.current_coins = coins
        if fails is not None: self.current_fails = fails
        if profit is not None: self.current_profit = profit

        t = TRANSLATIONS[self.current_lang]
        base_text = t["coins_prefix"].replace("{coins}", str(self.current_coins))
        display_str = f"{base_text}\n净利: {self.current_profit:+d} | 失败: {self.current_fails}"
        self.canvas.itemconfig(self.coins_id, text=display_str)

    def refresh_texts(self):
        t = TRANSLATIONS[self.current_lang]
        selected_strategy = self.combo_strategy.current()
        self.combo_strategy.configure(values=STRATEGY_LABELS[self.current_lang],
                                      state='disabled' if self.is_running else 'readonly')
        self.combo_strategy.current(max(0, selected_strategy))
        self.title(t["title"])
        self.canvas.itemconfig(self.title_id, text=t["title"])
        self.canvas.itemconfig(self.lang_label_id, text=t["lang_label"])
        self.canvas.itemconfig(self.hotkey_label_id, text=t["hotkey_label"])
        self.canvas.itemconfig(self.target_label_id, text=t["target_label"])

        if self.target_options:
            selected_target = self.combo_target.current()
            self.target_options[0]["label"] = t["target_auto"]
            self.combo_target.configure(values=[opt["label"] for opt in self.target_options])
            self.combo_target.current(max(0, selected_target))

        self.btn_refresh.configure(text=t["btn_refresh"])
        self._update_region_button_text()
        self.btn_adb.configure(text=t["btn_adb"])
        self.btn_diag.configure(text=t["btn_diag"])
        self.btn_calib.configure(text=t["btn_calib"])
        self.btn_bg.configure(text=t["btn_bg"])
        self.btn_exit.configure(text=t["btn_exit"])

        self.update_stats_display()

        if not self.is_running:
            self.canvas.itemconfig(self.status_id, text=t["status_idle"], fill="#111111")
            self.btn_next.configure(text=t["btn_start"], state="normal")
            self.btn_stop.configure(text=t["btn_stop"], state="disabled")
            self.btn_hotkey.configure(state="normal")
            self.combo_target.configure(state="readonly")
            self.btn_refresh.configure(state="normal")
            self.btn_region.configure(state="normal")
            self.btn_adb.configure(state="normal")
            self.btn_diag.configure(state="normal")
            self.btn_calib.configure(state="normal")
        else:
            self.btn_next.configure(text=t["btn_running"], state="disabled")
            self.btn_stop.configure(text=t["btn_stop"], state="normal")
            self.btn_hotkey.configure(state="disabled")
            self.combo_target.configure(state="disabled")
            self.btn_refresh.configure(state="disabled")
            self.btn_region.configure(state="disabled")
            self.btn_adb.configure(state="disabled")
            self.btn_diag.configure(state="disabled")
            self.btn_calib.configure(state="disabled")

    def on_strategy_selected(self, event=None):
        self.window_config["strategy"] = max(0, self.combo_strategy.current())
        save_window_config(self.window_config)

    def change_language(self, event=None):
        idx = self.combo_lang.current()
        self.current_lang = self.lang_keys[idx]
        self.window_config["lang"] = self.current_lang
        save_window_config(self.window_config)
        self.refresh_texts()

    def start_bot(self):
        self.active_mode = 'phased' if self.combo_strategy.current() == 1 else 'legacy'
        self._sync_bot_target()
        self.is_running = True
        self.refresh_texts()
        self.canvas.itemconfig(self.status_id,
                               text=TRANSLATIONS[self.current_lang]["status_running"],
                               fill="green")

        self.sys_redirector.clear()

        auto_bot.bot_running = True
        self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        if not self.is_running: return

        print(f"\n[系统] 收到停止指令 (或按下了快捷键)，正在等待当前动作完成并安全退出...")
        auto_bot.bot_running = False
        self.btn_stop.configure(state="disabled")
        self.canvas.itemconfig(self.status_id,
                               text=TRANSLATIONS[self.current_lang]["status_stopping"],
                               fill="orange")

    def run_bot(self):
        crashed = False
        try:
            auto_bot.auto_play_loop(self.active_mode)
        except Exception as e:
            crashed = True
            print(f"崩溃异常: {e}")
        finally:
            def _finish():
                self.is_running = False
                auto_bot.bot_running = False
                self.refresh_texts()
                if crashed:
                    self.canvas.itemconfig(
                        self.status_id,
                        text=TRANSLATIONS[self.current_lang]["status_crashed"],
                        fill="red",
                    )
                print("\n[系统] 挂机已完全停止。")

            self.after(0, _finish)

    def destroy(self):
        sys.stdout = self.original_stdout
        keyboard.unhook_all()
        super().destroy()


if __name__ == "__main__":
    app = HololiveBotUI()
    app.mainloop()
