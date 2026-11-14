from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import random
import threading
import time

import cv2
import mss
import numpy as np
import pydirectinput

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

_user32 = ctypes.WinDLL("user32")
_gdi32 = ctypes.WinDLL("gdi32")
_kernel32 = ctypes.WinDLL("kernel32")
_advapi32 = ctypes.WinDLL("advapi32")
try:
    _dwmapi = ctypes.WinDLL("dwmapi")
except Exception:
    _dwmapi = None

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

_user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
_user32.EnumChildWindows.restype = wintypes.BOOL
_user32.IsWindow.argtypes = [wintypes.HWND]
_user32.IsWindow.restype = wintypes.BOOL
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.IsIconic.argtypes = [wintypes.HWND]
_user32.IsIconic.restype = wintypes.BOOL
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetClientRect.restype = wintypes.BOOL
_user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
_user32.ClientToScreen.restype = wintypes.BOOL
_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = ctypes.c_long
_user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetAncestor.restype = wintypes.HWND
_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetDC.argtypes = [wintypes.HWND]
_user32.GetDC.restype = wintypes.HDC
_user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
_user32.ReleaseDC.restype = ctypes.c_int
_user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
_user32.PrintWindow.restype = wintypes.BOOL
_user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindowAsync.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.BringWindowToTop.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.restype = wintypes.BOOL
_user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
_user32.SetWindowPos.restype = wintypes.BOOL
_user32.GetSystemMetrics.argtypes = [ctypes.c_int]
_user32.GetSystemMetrics.restype = ctypes.c_int
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_user32.SetCursorPos.restype = wintypes.BOOL

_gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
_gdi32.CreateCompatibleDC.restype = wintypes.HDC
_gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
_gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
_gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
_gdi32.SelectObject.restype = wintypes.HGDIOBJ
_gdi32.GetBitmapBits.argtypes = [wintypes.HBITMAP, wintypes.LONG, wintypes.LPVOID]
_gdi32.GetBitmapBits.restype = wintypes.LONG
_gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
_gdi32.DeleteObject.restype = wintypes.BOOL
_gdi32.DeleteDC.argtypes = [wintypes.HDC]
_gdi32.DeleteDC.restype = wintypes.BOOL

if _dwmapi is not None:
    _dwmapi.DwmGetWindowAttribute.argtypes = [
        wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    ]
    _dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.GetCurrentProcess.argtypes = []
_kernel32.GetCurrentProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

_advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
_advapi32.OpenProcessToken.restype = wintypes.BOOL
_advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
]
_advapi32.GetTokenInformation.restype = wintypes.BOOL

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
GA_ROOT = 2
DWMWA_CLOAKED = 14
PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_ELEVATION = 20

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

TARGET_ASPECT = 16.0 / 9.0
_IGNORED_TITLES = {
    "program manager",
    "windows input experience",
    "microsoft text input application",
    "settings",
    "nvidia geforce overlay",
}
_EMULATOR_KEYWORDS = (
    "mumu", "雷电", "ldplayer", "bluestacks", "nox", "夜神",
    "memu", "逍遥", "scrcpy", "android", "emulator", "模拟器",
)
_RENDER_CLASS_HINTS = (
    "render", "nemu", "subwin", "android", "sdl", "opengl",
    "d3d", "canvas", "player", "screenboard",
)

_capture_method_cache: dict[int, str] = {}
_elevation_warned_hwnds: set[int] = set()
_thread_local = threading.local()


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    width: int
    height: int
    class_name: str = ""
    minimized: bool = False
    pid: int = 0


def _get_mss():
    sct = getattr(_thread_local, "mss_instance", None)
    if sct is None:
        sct = mss.MSS()
        _thread_local.mss_instance = sct
    return sct


def _reset_mss():
    sct = getattr(_thread_local, "mss_instance", None)
    if sct is not None:
        try:
            sct.close()
        except Exception:
            pass
        _thread_local.mss_instance = None


def clear_capture_cache(hwnd: int | None = None):
    if hwnd is None:
        _capture_method_cache.clear()
        _elevation_warned_hwnds.clear()
    else:
        _capture_method_cache.pop(hwnd, None)
        _elevation_warned_hwnds.discard(hwnd)


def get_window_title(hwnd: int) -> str:
    length = _user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def get_process_image_path(pid: int) -> str | None:
    if not pid:
        return None
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        _kernel32.CloseHandle(handle)


def get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    length = _user32.GetClassNameW(hwnd, buf, 256)
    return buf.value[:length] if length > 0 else ""


def _is_window_cloaked(hwnd: int) -> bool:
    if _dwmapi is None:
        return False
    cloaked = wintypes.DWORD(0)
    hr = _dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    return hr == 0 and cloaked.value != 0


def get_client_geometry(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError()
    if not _user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise ctypes.WinError()
    return int(origin.x), int(origin.y), int(rect.right - rect.left), int(rect.bottom - rect.top)


def get_root_hwnd(hwnd: int) -> int:
    if not hwnd or not _user32.IsWindow(hwnd):
        return 0
    root = _user32.GetAncestor(hwnd, GA_ROOT)
    return int(root) if root else int(hwnd)


def _window_sort_key(win: WindowInfo, default_title: str) -> tuple[int, int, str]:
    lowered = win.title.casefold()
    if lowered == default_title.casefold():
        priority = 0
    elif default_title.casefold() in lowered:
        priority = 1
    elif any(kw in lowered for kw in _EMULATOR_KEYWORDS):
        priority = 2
    else:
        priority = 3
    return (priority, -(win.width * win.height), lowered)


def list_candidate_windows(
    default_title: str = "hololive-Dreams",
    exclude_pids: set[int] | None = None,
    exclude_hwnds: set[int] | None = None,
) -> list[WindowInfo]:
    exclude_pids = exclude_pids or set()
    exclude_hwnds = exclude_hwnds or set()
    windows: list[WindowInfo] = []

    def _callback(hwnd, _lparam):
        hwnd_int = int(hwnd)
        if hwnd_int in exclude_hwnds:
            return True
        if not _user32.IsWindowVisible(hwnd):
            return True
        if _is_window_cloaked(hwnd):
            return True

        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in exclude_pids:
            return True

        title = get_window_title(hwnd)
        if not title or title.casefold() in _IGNORED_TITLES:
            return True

        minimized = bool(_user32.IsIconic(hwnd))
        rect = wintypes.RECT()
        if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)

        ex_style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if (ex_style & WS_EX_TOOLWINDOW) and (minimized or width < 320 or height < 180):
            return True

        if not minimized and (width < 200 or height < 150):
            return True

        windows.append(
            WindowInfo(
                hwnd=hwnd_int,
                title=title,
                width=max(0, width),
                height=max(0, height),
                class_name=get_class_name(hwnd),
                minimized=minimized,
                pid=int(pid.value),
            )
        )
        return True

    proc = WNDENUMPROC(_callback)
    _user32.EnumWindows(proc, 0)
    windows.sort(key=lambda w: _window_sort_key(w, default_title))
    return windows


def find_window_by_title(title: str, exact: bool = True) -> int | None:
    expected = title.casefold().strip()
    if not expected:
        return None
    matches: list[tuple[int, int]] = []

    def _callback(hwnd, _lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True
        win_title = get_window_title(hwnd)
        normalized = win_title.casefold().strip()
        if (normalized == expected) if exact else (expected in normalized):
            rect = wintypes.RECT()
            if _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                matches.append((area, int(hwnd)))
        return True

    _user32.EnumWindows(WNDENUMPROC(_callback), 0)
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def _score_child_candidate(
    child_rect: tuple[int, int, int, int],
    child_class: str,
    root_rect: tuple[int, int, int, int],
    depth_order: int,
) -> tuple[float, int, int] | None:
    cl, ct, cw, ch = child_rect
    rl, rt, rw, rh = root_rect
    if cw < 320 or ch < 180:
        return None
    if cl < rl - 4 or ct < rt - 4 or cl + cw > rl + rw + 4 or ct + ch > rt + rh + 4:
        return None
    root_area = max(1, rw * rh)
    child_area = cw * ch
    if child_area < 0.40 * root_area:
        return None

    root_aspect = rw / max(1, rh)
    child_aspect = cw / max(1, ch)
    root_diff = abs(root_aspect - TARGET_ASPECT)
    child_diff = abs(child_aspect - TARGET_ASPECT)

    # Ignore children that merely mirror the root bounds unless root isn't 16:9.
    same_size = abs(cw - rw) <= 4 and abs(ch - rh) <= 4
    if same_size and root_diff < 0.03:
        return None

    # A valid emulator render child excludes titlebar/sidebar so it is smaller than
    # root while maintaining (or improving) proximity to 16:9.
    improves_aspect = child_diff + 0.01 < root_diff
    clean_inner_box = (cw < rw - 4 or ch < rh - 4) and child_diff <= max(0.15, root_diff + 0.02)
    if not (improves_aspect or clean_inner_box):
        return None

    class_lower = child_class.casefold()
    hint_bonus = 1 if any(k in class_lower for k in _RENDER_CLASS_HINTS) else 0
    # Lower aspect difference is better; then prefer known render class, then larger area / deeper child.
    return (-round(child_diff, 4), hint_bonus, child_area + depth_order)


def select_best_render_child(
    root_rect: tuple[int, int, int, int],
    children: list[tuple[int, tuple[int, int, int, int], str]],
) -> tuple[int | None, tuple[int, int, int, int]]:
    """Pure helper to choose the best inner render viewport among child windows."""
    best_score = None
    best_hwnd = None
    best_rect = root_rect
    for order, (child_hwnd, child_rect, child_class) in enumerate(children):
        score = _score_child_candidate(child_rect, child_class, root_rect, order)
        if score is not None and (best_score is None or score > best_score):
            best_score = score
            best_hwnd = child_hwnd
            best_rect = child_rect
    return best_hwnd, best_rect


def resolve_render_viewport(root_hwnd: int, auto_detect_child: bool = True) -> tuple[int, int, tuple[int, int, int, int]]:
    """Return (root_hwnd, render_hwnd, (left, top, width, height))."""
    root_hwnd = get_root_hwnd(root_hwnd)
    if not root_hwnd:
        raise RuntimeError("目标窗口句柄无效")

    if _user32.IsIconic(root_hwnd):
        _user32.ShowWindowAsync(root_hwnd, 9)  # SW_RESTORE
        time.sleep(0.4)

    root_rect = get_client_geometry(root_hwnd)
    if root_rect[2] < 320 or root_rect[3] < 180:
        raise RuntimeError(f"窗口客户区尺寸异常: {root_rect[2]}x{root_rect[3]}")

    if not auto_detect_child:
        return root_hwnd, root_hwnd, root_rect

    children: list[tuple[int, tuple[int, int, int, int], str]] = []

    def _child_cb(hwnd, _lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True
        try:
            crect = get_client_geometry(hwnd)
        except Exception:
            return True
        children.append((int(hwnd), crect, get_class_name(hwnd)))
        return True

    _user32.EnumChildWindows(root_hwnd, WNDENUMPROC(_child_cb), 0)
    child_hwnd, best_rect = select_best_render_child(root_rect, children)
    if child_hwnd is not None:
        return root_hwnd, child_hwnd, best_rect
    return root_hwnd, root_hwnd, root_rect


def apply_crop_rect(
    rect: tuple[int, int, int, int],
    crop_rect: tuple[float, float, float, float] | None,
) -> tuple[int, int, int, int]:
    left, top, width, height = rect
    if not crop_rect:
        return left, top, width, height
    rx, ry, rw, rh = crop_rect
    rx = max(0.0, min(0.95, float(rx)))
    ry = max(0.0, min(0.95, float(ry)))
    rw = max(0.05, min(1.0 - rx, float(rw)))
    rh = max(0.05, min(1.0 - ry, float(rh)))
    cx = left + round(rx * width)
    cy = top + round(ry * height)
    cw = max(1, round(rw * width))
    ch = max(1, round(rh * height))
    return cx, cy, cw, ch


def _is_frame_valid(frame: np.ndarray | None) -> bool:
    if frame is None or frame.size == 0:
        return False
    return float(frame.mean()) >= 1.0 and float(frame.std()) >= 1.0


def _capture_client_with_printwindow(hwnd: int, width: int, height: int) -> np.ndarray:
    window_dc = _user32.GetDC(hwnd)
    memory_dc = bitmap = old_bitmap = None
    try:
        if not window_dc:
            raise ctypes.WinError()
        memory_dc = _gdi32.CreateCompatibleDC(window_dc)
        bitmap = _gdi32.CreateCompatibleBitmap(window_dc, width, height)
        if not memory_dc or not bitmap:
            raise ctypes.WinError()
        old_bitmap = _gdi32.SelectObject(memory_dc, bitmap)

        if not _user32.PrintWindow(hwnd, memory_dc, PW_CLIENTONLY | PW_RENDERFULLCONTENT):
            raise RuntimeError("PrintWindow failed")

        byte_count = width * height * 4
        buffer = ctypes.create_string_buffer(byte_count)
        if _gdi32.GetBitmapBits(bitmap, byte_count, buffer) != byte_count:
            raise RuntimeError("GetBitmapBits returned an incomplete frame")
        frame = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width, 4)
        return frame[:, :, :3].copy()
    finally:
        if old_bitmap and memory_dc:
            _gdi32.SelectObject(memory_dc, old_bitmap)
        if bitmap:
            _gdi32.DeleteObject(bitmap)
        if memory_dc:
            _gdi32.DeleteDC(memory_dc)
        if window_dc:
            _user32.ReleaseDC(hwnd, window_dc)


def _grab_mss_region(left: int, top: int, width: int, height: int) -> np.ndarray:
    monitor = {"top": int(top), "left": int(left), "width": int(width), "height": int(height)}
    try:
        sct = _get_mss()
        raw = np.array(sct.grab(monitor))
    except Exception:
        _reset_mss()
        sct = _get_mss()
        raw = np.array(sct.grab(monitor))
    return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)


def bring_window_to_front(hwnd: int) -> bool:
    root_hwnd = get_root_hwnd(hwnd)
    if not root_hwnd:
        return False

    changed = False
    if _user32.IsIconic(root_hwnd):
        _user32.ShowWindowAsync(root_hwnd, 9)  # SW_RESTORE
        time.sleep(0.25)
        changed = True

    if _user32.GetForegroundWindow() != root_hwnd:
        _user32.BringWindowToTop(root_hwnd)
        _user32.SetForegroundWindow(root_hwnd)
        if _user32.GetForegroundWindow() != root_hwnd:
            flags = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW
            _user32.SetWindowPos(root_hwnd, wintypes.HWND(-1), 0, 0, 0, 0, flags)
            _user32.SetWindowPos(root_hwnd, wintypes.HWND(-2), 0, 0, 0, 0, flags)
        changed = True

    if changed:
        time.sleep(0.05)
    return True


def _is_process_elevated(handle) -> bool | None:
    token = wintypes.HANDLE()
    if not _advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
        return None
    try:
        elevation = wintypes.DWORD(0)
        ret_len = wintypes.DWORD(0)
        ok = _advapi32.GetTokenInformation(
            token, TOKEN_ELEVATION, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(ret_len)
        )
        return bool(elevation.value) if ok else None
    finally:
        _kernel32.CloseHandle(token)


def warn_if_target_elevated(hwnd: int):
    root_hwnd = get_root_hwnd(hwnd)
    if not root_hwnd or root_hwnd in _elevation_warned_hwnds:
        return
    _elevation_warned_hwnds.add(root_hwnd)

    self_elevated = _is_process_elevated(_kernel32.GetCurrentProcess())
    if self_elevated:
        return

    pid = wintypes.DWORD(0)
    _user32.GetWindowThreadProcessId(root_hwnd, ctypes.byref(pid))
    if not pid.value:
        return

    proc_handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not proc_handle:
        print("[提示] 无法查询目标窗口权限（可能为管理员权限运行）。若无法点击，请以管理员身份运行本程序。")
        return
    try:
        if _is_process_elevated(proc_handle):
            print("[警告] 检测到目标窗口以管理员权限运行！如果无法自动点击，请右键「以管理员身份运行」本程序。")
    finally:
        _kernel32.CloseHandle(proc_handle)


def capture_window_frame(
    root_hwnd: int,
    crop_rect: tuple[float, float, float, float] | None = None,
    auto_detect_child: bool = True,
) -> tuple[np.ndarray, dict]:
    """Capture the game area from root_hwnd, returning (bgr_image, context_dict)."""
    root_hwnd, render_hwnd, render_rect = resolve_render_viewport(
        root_hwnd, auto_detect_child=auto_detect_child
    )
    rl, rt, rw, rh = render_rect
    crop_left, crop_top, crop_w, crop_h = apply_crop_rect(render_rect, crop_rect)

    method = _capture_method_cache.get(root_hwnd)
    frame: np.ndarray | None = None

    if method in (None, "printwindow_render"):
        try:
            candidate = _capture_client_with_printwindow(render_hwnd, rw, rh)
            sub = candidate[
                crop_top - rt : crop_top - rt + crop_h,
                crop_left - rl : crop_left - rl + crop_w,
            ]
            if _is_frame_valid(sub):
                frame = sub.copy()
                _capture_method_cache[root_hwnd] = "printwindow_render"
        except Exception:
            frame = None

    if frame is None and render_hwnd != root_hwnd and method in (None, "printwindow_root"):
        try:
            root_l, root_t, root_w, root_h = get_client_geometry(root_hwnd)
            root_img = _capture_client_with_printwindow(root_hwnd, root_w, root_h)
            dx = crop_left - root_l
            dy = crop_top - root_t
            if dx >= 0 and dy >= 0 and dx + crop_w <= root_w and dy + crop_h <= root_h:
                sub = root_img[dy : dy + crop_h, dx : dx + crop_w]
                if _is_frame_valid(sub):
                    frame = sub.copy()
                    _capture_method_cache[root_hwnd] = "printwindow_root"
        except Exception:
            frame = None

    if frame is None:
        if method != "mss":
            print("[提示] 当前窗口后台截图受限，已自动切换为高速前台截图模式（请勿遮挡游戏画面）。")
            _capture_method_cache[root_hwnd] = "mss"
        bring_window_to_front(root_hwnd)
        # Re-read coordinates after potential restore/foreground move.
        _, render_hwnd, render_rect = resolve_render_viewport(
            root_hwnd, auto_detect_child=auto_detect_child
        )
        crop_left, crop_top, crop_w, crop_h = apply_crop_rect(render_rect, crop_rect)
        frame = _grab_mss_region(crop_left, crop_top, crop_w, crop_h)

    context = {
        "hwnd": root_hwnd,
        "root_hwnd": root_hwnd,
        "render_hwnd": render_hwnd,
        "left": crop_left,
        "top": crop_top,
        "width": crop_w,
        "height": crop_h,
        "render_width": render_rect[2],
        "render_height": render_rect[3],
        "crop_rect": crop_rect,
        "auto_detect_child": auto_detect_child,
        "capture_method": _capture_method_cache.get(root_hwnd, "mss"),
    }
    return frame, context


def move_cursor_to(target_x: int, target_y: int):
    primary_w = _user32.GetSystemMetrics(SM_CXSCREEN)
    primary_h = _user32.GetSystemMetrics(SM_CYSCREEN)
    if 0 <= target_x < primary_w and 0 <= target_y < primary_h:
        pydirectinput.moveTo(int(target_x), int(target_y))
    else:
        _user32.SetCursorPos(int(target_x), int(target_y))


def click_at_screen(target_x: int, target_y: int):
    move_cursor_to(target_x, target_y)
    time.sleep(random.uniform(0.02, 0.05))
    pydirectinput.mouseDown()
    time.sleep(random.uniform(0.05, 0.08))
    pydirectinput.mouseUp()
    time.sleep(random.uniform(0.05, 0.1))
