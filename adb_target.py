from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import socket
import subprocess

import cv2
import numpy as np

from window_target import apply_crop_rect, get_process_image_path, list_candidate_windows

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_ADB_NAMES = ("adb.exe", "adb_server.exe", "nox_adb.exe", "HD-Adb.exe", "adb")

COMMON_ADB_PORTS = (
    ("127.0.0.1", 16384, "MuMu 12"),
    ("127.0.0.1", 7555, "MuMu 6"),
    ("127.0.0.1", 5555, "LDPlayer / BlueStacks"),
    ("127.0.0.1", 5557, "LDPlayer / BlueStacks #2"),
    ("127.0.0.1", 62001, "Nox"),
    ("127.0.0.1", 21503, "MEmu"),
)


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    model: str = ""

    @property
    def ready(self) -> bool:
        return self.state == "device"


def _candidate_adb_paths_from_dirs(dirs: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for base in dirs:
        for folder in (base, base.parent, base / "shell", base.parent / "shell", base / "bin"):
            for name in _ADB_NAMES:
                cand = folder / name
                if cand not in seen:
                    seen.add(cand)
                    found.append(cand)
    return found


def find_adb_executable(preferred_path: str | None = None) -> str | None:
    if preferred_path:
        p = Path(preferred_path)
        if p.is_file():
            return str(p)

    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb

    search_dirs: list[Path] = []
    try:
        for win in list_candidate_windows(exclude_pids={os.getpid()}):
            exe = get_process_image_path(win.pid)
            if exe:
                search_dirs.append(Path(exe).parent)
    except Exception:
        pass

    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
    ]
    if str(local_app):
        search_dirs.append(local_app / "Android" / "Sdk" / "platform-tools")
    for drive in ("C:/", "D:/", "E:/"):
        dp = Path(drive)
        search_dirs.extend([
            dp / "leidian" / "LDPlayer9",
            dp / "leidian" / "LDPlayer4",
            dp / "LDPlayer" / "LDPlayer9",
            dp / "Program Files" / "Netease" / "MuMuPlayer-12.0" / "shell",
            dp / "Program Files" / "Netease" / "MuMuPlayerGlobal-12.0" / "shell",
            dp / "Program Files" / "Netease" / "MuMu" / "emulator" / "nemu" / "vmonitor" / "bin",
            dp / "Program Files" / "BlueStacks_nxt",
            dp / "Program Files" / "Nox" / "bin",
            dp / "Program Files" / "Microvirt" / "MEmu",
        ])
    for pf in program_files:
        search_dirs.extend([
            pf / "Netease" / "MuMuPlayer-12.0" / "shell",
            pf / "Netease" / "MuMuPlayerGlobal-12.0" / "shell",
            pf / "BlueStacks_nxt",
            pf / "BlueStacks",
            pf / "Nox" / "bin",
            pf / "Microvirt" / "MEmu",
        ])

    for cand in _candidate_adb_paths_from_dirs(search_dirs):
        try:
            if cand.is_file():
                return str(cand)
        except OSError:
            continue
    return None


def _run_adb(args: list[str], adb_path: str | None = None, timeout: float = 5.0) -> subprocess.CompletedProcess:
    exe = find_adb_executable(adb_path)
    if not exe:
        raise FileNotFoundError("未找到 adb.exe，请在 ADB 设置中手动指定路径或安装/开启模拟器自带 ADB。")
    return subprocess.run(
        [exe, *args],
        capture_output=True,
        timeout=timeout,
        creationflags=_CREATE_NO_WINDOW,
    )


def parse_adb_devices(output: str) -> list[AdbDevice]:
    devices: list[AdbDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        model = ""
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token.split(":", 1)[1]
                break
        devices.append(AdbDevice(serial=serial, state=state, model=model))
    return devices


def list_adb_devices(adb_path: str | None = None) -> list[AdbDevice]:
    res = _run_adb(["devices", "-l"], adb_path=adb_path, timeout=4.0)
    text = res.stdout.decode("utf-8", errors="replace")
    return parse_adb_devices(text)


def connect_adb_endpoint(address: str, adb_path: str | None = None) -> tuple[bool, str]:
    endpoint = address.strip()
    if not endpoint:
        return False, "ADB 地址不能为空"
    res = _run_adb(["connect", endpoint], adb_path=adb_path, timeout=5.0)
    out = (res.stdout + res.stderr).decode("utf-8", errors="replace").strip()
    ok = res.returncode == 0 and ("connected" in out.lower() or "already connected" in out.lower())
    return ok, out or ("连接成功" if ok else "连接失败")


def _is_port_open(host: str, port: int, timeout: float = 0.12) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def auto_probe_common_ports(adb_path: str | None = None) -> tuple[list[AdbDevice], list[str]]:
    logs: list[str] = []
    for host, port, label in COMMON_ADB_PORTS:
        if _is_port_open(host, port):
            addr = f"{host}:{port}"
            ok, msg = connect_adb_endpoint(addr, adb_path=adb_path)
            logs.append(f"{label} ({addr}): {msg}")
    return list_adb_devices(adb_path=adb_path), logs


def adb_capture_frame(
    serial: str,
    adb_path: str | None = None,
    crop_rect: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, dict]:
    if not serial:
        raise RuntimeError("未指定 ADB 设备序列号")
    exe = find_adb_executable(adb_path)
    if not exe:
        raise RuntimeError("未找到 adb.exe")

    res = subprocess.run(
        [exe, "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=6.0,
        creationflags=_CREATE_NO_WINDOW,
    )
    if res.returncode != 0 or not res.stdout:
        err = res.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ADB 截图失败: {err or f'exit {res.returncode}'}")

    raw = res.stdout
    img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None and b"\r\n" in raw:
        # Some legacy adb builds perform CRLF translation on stdout.
        img = cv2.imdecode(np.frombuffer(raw.replace(b"\r\n", b"\n"), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        raise RuntimeError("ADB 返回的截图无法解码")

    dh, dw = img.shape[:2]
    cx, cy, cw, ch = apply_crop_rect((0, 0, dw, dh), crop_rect)
    cropped = img[cy : cy + ch, cx : cx + cw].copy()
    context = {
        "mode": "adb",
        "serial": serial,
        "adb_path": exe,
        "left": cx,
        "top": cy,
        "width": cw,
        "height": ch,
        "device_width": dw,
        "device_height": dh,
        "crop_rect": crop_rect,
    }
    return cropped, context


def adb_tap(serial: str, x: int, y: int, adb_path: str | None = None) -> bool:
    if not serial:
        return False
    res = _run_adb(
        ["-s", serial, "shell", "input", "tap", str(int(x)), str(int(y))],
        adb_path=adb_path,
        timeout=4.0,
    )
    return res.returncode == 0
