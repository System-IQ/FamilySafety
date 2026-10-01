"""Real system metrics collector for Android/Termux + Linux.

Battery is queried in a background thread with a 15-second cache so
/metrics returns instantly (termux-battery-status is slow inside runit).
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
from typing import Any, Optional

_PROCESS_START = time.time()
_REQUEST_COUNTER = {"total": 0, "errors": 0}

# ────────────────────────────────────────────────────────────
# Request counter API
# ────────────────────────────────────────────────────────────
def record_request(status_code: int) -> None:
    _REQUEST_COUNTER["total"] += 1
    if status_code >= 400:
        _REQUEST_COUNTER["errors"] += 1


# ────────────────────────────────────────────────────────────
# Battery — cached, refreshed in background
# ────────────────────────────────────────────────────────────
_BATTERY_CACHE: dict[str, Any] = {
    "percent": None, "charging": None, "temperature_c": None,
    "last_update": 0.0,
}
_BATTERY_LOCK = threading.Lock()
_BATTERY_REFRESH_INTERVAL = 15.0  # seconds
_BATTERY_THREAD_STARTED = False


def _battery_query_blocking() -> dict[str, Any]:
    """Actually call termux-battery-status — slow (2-5s), so only from a thread."""
    out: dict[str, Any] = {"percent": None, "charging": None, "temperature_c": None}

    # 1) Try sysfs (fast, often blocked on Android 14)
    for pth in (
        "/sys/class/power_supply/battery/capacity",
        "/sys/class/power_supply/Battery/capacity",
        "/sys/class/power_supply/bms/capacity",
    ):
        try:
            with open(pth) as f:
                out["percent"] = int(f.read().strip())
            break
        except Exception:
            pass

    for pth in (
        "/sys/class/power_supply/battery/status",
        "/sys/class/power_supply/Battery/status",
    ):
        try:
            with open(pth) as f:
                st = f.read().strip().lower()
            out["charging"] = st in ("charging", "full")
            break
        except Exception:
            pass

    if out["percent"] is not None:
        return out  # sysfs worked, no need for termux-api

    # 2) termux-battery-status (slow)
    termux_bin = os.path.join(
        os.environ.get("PREFIX", "/data/data/com.termux/files/usr"),
        "bin", "termux-battery-status",
    )
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(termux_bin) + ":" + env.get("PATH", "")
    try:
        res = subprocess.run(
            [termux_bin],
            capture_output=True, text=True, timeout=10, env=env,
        )
        if res.returncode == 0 and res.stdout.strip():
            import json as _json
            data = _json.loads(res.stdout)
            pct = data.get("percentage")
            if isinstance(pct, (int, float)):
                out["percent"] = int(pct)
            status = (data.get("status") or "").upper()
            if status in ("CHARGING", "FULL"):
                out["charging"] = True
            elif status in ("DISCHARGING", "NOT_CHARGING", "UNKNOWN"):
                out["charging"] = False
            temp = data.get("temperature")
            if isinstance(temp, (int, float)) and temp > 0:
                out["temperature_c"] = round(float(temp), 1)
    except Exception:
        pass

    return out


def _battery_refresh_loop() -> None:
    """Background: refresh battery cache every 15s."""
    while True:
        try:
            data = _battery_query_blocking()
            with _BATTERY_LOCK:
                _BATTERY_CACHE.update(data)
                _BATTERY_CACHE["last_update"] = time.time()
        except Exception:
            pass
        time.sleep(_BATTERY_REFRESH_INTERVAL)


def _ensure_battery_thread() -> None:
    global _BATTERY_THREAD_STARTED
    if _BATTERY_THREAD_STARTED:
        return
    with _BATTERY_LOCK:
        if _BATTERY_THREAD_STARTED:
            return
        t = threading.Thread(target=_battery_refresh_loop, daemon=True, name="battery-monitor")
        t.start()
        _BATTERY_THREAD_STARTED = True


def _battery_info() -> dict[str, Any]:
    """Return cached battery info. Never blocks."""
    _ensure_battery_thread()
    with _BATTERY_LOCK:
        return {
            "percent": _BATTERY_CACHE["percent"],
            "charging": _BATTERY_CACHE["charging"],
            "temperature_c": _BATTERY_CACHE["temperature_c"],
            "age_seconds": round(time.time() - _BATTERY_CACHE["last_update"], 1)
                             if _BATTERY_CACHE["last_update"] > 0 else None,
        }


# ────────────────────────────────────────────────────────────
# CPU
# ────────────────────────────────────────────────────────────
def _cpu_info() -> dict[str, Any]:
    out: dict[str, Any] = {
        "load_1m": 0.0, "load_5m": 0.0, "load_15m": 0.0,
        "cores": os.cpu_count() or 1,
        "percent": 0.0,
    }
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            out["load_1m"] = float(parts[0])
            out["load_5m"] = float(parts[1])
            out["load_15m"] = float(parts[2])
    except Exception:
        pass
    cores = out["cores"]
    if cores > 0:
        out["percent"] = round(min((out["load_1m"] / cores) * 100.0, 100.0), 1)
    return out


# ────────────────────────────────────────────────────────────
# Memory
# ────────────────────────────────────────────────────────────
def _read_meminfo() -> dict[str, int]:
    info: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                v = v.strip().split()[0]
                try:
                    info[k] = int(v)
                except ValueError:
                    pass
    except Exception:
        pass
    return info


def _memory_info() -> dict[str, Any]:
    mi = _read_meminfo()
    total_kb = mi.get("MemTotal", 0)
    avail_kb = mi.get("MemAvailable", mi.get("MemFree", 0))
    used_kb = max(0, total_kb - avail_kb)
    to_mb = lambda kb: round(kb / 1024.0, 1)
    pct = round((used_kb / total_kb * 100.0), 1) if total_kb > 0 else 0.0
    return {
        "total_mb": to_mb(total_kb),
        "used_mb": to_mb(used_kb),
        "free_mb": to_mb(avail_kb),
        "percent": pct,
    }


# ────────────────────────────────────────────────────────────
# Storage
# ────────────────────────────────────────────────────────────
def _storage_info(path: str = "/data/data/com.termux/files/home") -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        total_mb = round(usage.total / (1024 * 1024), 1)
        free_mb = round(usage.free / (1024 * 1024), 1)
        used_mb = round((usage.total - usage.free) / (1024 * 1024), 1)
        pct = round((used_mb / total_mb * 100.0), 1) if total_mb > 0 else 0.0
        return {"total_mb": total_mb, "used_mb": used_mb, "free_mb": free_mb,
                "percent": pct, "path": path}
    except Exception:
        return {"total_mb": 0.0, "used_mb": 0.0, "free_mb": 0.0, "percent": 0.0, "path": path}


# ────────────────────────────────────────────────────────────
# Process
# ────────────────────────────────────────────────────────────
def _process_info() -> dict[str, Any]:
    pid = os.getpid()
    rss_mb = 0.0
    threads = 0
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_mb = round(int(line.split()[1]) / 1024.0, 1)
                elif line.startswith("Threads:"):
                    threads = int(line.split()[1])
    except Exception:
        pass
    return {
        "pid": pid, "rss_mb": rss_mb, "threads": threads,
        "uptime_seconds": round(time.time() - _PROCESS_START, 1),
    }


# ────────────────────────────────────────────────────────────
# Network (rates via /proc/self/net/dev — often blocked on Android)
# ────────────────────────────────────────────────────────────
_NET_LAST: dict[str, Any] = {"ts": 0.0, "rx": 0, "tx": 0}


def _read_netdev() -> tuple[int, int]:
    for path in ("/proc/self/net/dev", "/proc/net/dev"):
        try:
            rx_total = 0
            tx_total = 0
            with open(path) as f:
                for line in f.readlines()[2:]:
                    if ":" not in line:
                        continue
                    iface, rest = line.split(":", 1)
                    if iface.strip() == "lo":
                        continue
                    fields = rest.split()
                    if len(fields) < 16:
                        continue
                    rx_total += int(fields[0])
                    tx_total += int(fields[8])
            return rx_total, tx_total
        except Exception:
            continue
    return 0, 0


def _network_info() -> dict[str, Any]:
    now = time.time()
    rx, tx = _read_netdev()
    rx_rate = 0.0
    tx_rate = 0.0
    if _NET_LAST["ts"] > 0 and (rx > 0 or tx > 0):
        dt = now - _NET_LAST["ts"]
        if dt > 0:
            rx_rate = max(0.0, (rx - _NET_LAST["rx"]) / dt)
            tx_rate = max(0.0, (tx - _NET_LAST["tx"]) / dt)
    _NET_LAST.update({"ts": now, "rx": rx, "tx": tx})
    return {
        "rx_rate_bps": round(rx_rate, 1),
        "tx_rate_bps": round(tx_rate, 1),
        "rx_total_mb": round(rx / (1024 * 1024), 1),
        "tx_total_mb": round(tx / (1024 * 1024), 1),
        "hostname": socket.gethostname(),
        "unavailable": rx == 0 and tx == 0,
    }


# ────────────────────────────────────────────────────────────
# Database
# ────────────────────────────────────────────────────────────
def _database_info(db_path: str) -> dict[str, Any]:
    size_mb = 0.0
    try:
        if db_path and os.path.exists(db_path):
            size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    except Exception:
        pass
    return {"size_mb": size_mb, "path": db_path}


# ────────────────────────────────────────────────────────────
# Requests
# ────────────────────────────────────────────────────────────
def _requests_info() -> dict[str, Any]:
    return {
        "total": _REQUEST_COUNTER["total"],
        "errors": _REQUEST_COUNTER["errors"],
    }


# ────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────
def collect(db_path: Optional[str] = None) -> dict[str, Any]:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cpu": _cpu_info(),
        "memory": _memory_info(),
        "battery": _battery_info(),
        "storage": _storage_info(),
        "process": _process_info(),
        "network": _network_info(),
        "database": _database_info(db_path or ""),
        "requests": _requests_info(),
    }
