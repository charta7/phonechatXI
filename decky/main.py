import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import time

import decky

BASE = os.path.join(decky.DECKY_USER_HOME, "phonechat")
BRIDGE_DIR = os.path.join(BASE, "bridge")
BRIDGE = os.path.join(BRIDGE_DIR, "bridge.py")
STATUS = os.path.join(BASE, "status.json")
FRESH_SECONDS = 10
SETTINGS = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "settings.json")
BRIDGE_LOG = os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "bridge.log")
BUNDLED = os.path.join(decky.DECKY_PLUGIN_DIR, "bridge")
BRIDGE_FILES = ("bridge.py", "index.html", "commands.json", "qrcode.js", "start.sh", "README.md")


def _version_of(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            m = re.search(r'^VERSION = "([^"]+)"', f.read(), re.M)
            return m.group(1) if m else ""
    except OSError:
        return ""


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def _install_bridge():
    """Copy the bridge bundled with this plugin into ~/phonechat/bridge when it is newer.
    Keeps config.json (token, port, tell-saving setting) and the saved tells."""
    have = _version_of(BRIDGE)
    ship = _version_of(os.path.join(BUNDLED, "bridge.py"))
    if not ship or (have and _vtuple(have) >= _vtuple(ship)):
        return ""
    os.makedirs(BRIDGE_DIR, exist_ok=True)
    for name in BRIDGE_FILES:
        src = os.path.join(BUNDLED, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(BRIDGE_DIR, name))
    try:
        os.chmod(os.path.join(BRIDGE_DIR, "start.sh"), 0o755)
    except OSError:
        pass
    decky.logger.info("bridge %s installed (was %s)", ship, have or "none")
    return ship


def _clean_env():
    """Decky runs inside a bundled Python; give the bridge a normal system environment."""
    env = dict(os.environ)
    for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH"):
        orig = env.pop(key + "_ORIG", None)
        if orig is not None:
            env[key] = orig
        else:
            env.pop(key, None)
    return env


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _find_pids():
    """PIDs of running phonechat bridges (looks for bridge.py in the process command line)."""
    pids = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return pids
    for name in entries:
        if not name.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % name, "rb") as f:
                cmd = f.read().split(b"\0")
        except OSError:
            continue
        if any(part.endswith(b"bridge.py") for part in cmd) and any(b"python" in part for part in cmd[:2]):
            pids.append(int(name))
    return pids


def _status():
    pids = _find_pids()
    data = _read_json(STATUS, {})
    fresh = bool(data.get("running")) and abs(time.time() - data.get("ts", 0)) <= FRESH_SECONDS
    return {
        "installed": os.path.exists(BRIDGE),
        "bridge_version": _version_of(BRIDGE),
        "notice": NOTICE.get("text", ""),
        "running": bool(pids) and fresh,
        "starting": bool(pids) and not fresh,
        "url": data.get("url", "") if (pids and fresh) else "",
        "version": data.get("version", ""),
        "error": "",
    }


NOTICE = {"text": ""}


class Plugin:
    async def get_status(self):
        return _status()

    async def start_bridge(self):
        st = _status()
        if st["running"] or st["starting"]:
            return st
        if not os.path.exists(BRIDGE):
            st["error"] = "Bridge not found at " + BRIDGE
            return st
        try:
            os.makedirs(decky.DECKY_PLUGIN_LOG_DIR, exist_ok=True)
            log = open(BRIDGE_LOG, "ab")
            subprocess.Popen(
                ["/usr/bin/python3", BRIDGE],
                cwd=BRIDGE_DIR,
                env=_clean_env(),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,   # keeps running if the Decky loader restarts
            )
        except Exception as exc:
            decky.logger.error("start failed: %s", exc)
            st["error"] = "Could not start: %s" % exc
            return st

        for _ in range(20):               # wait up to ~5 s for the first heartbeat
            await asyncio.sleep(0.25)
            st = _status()
            if st["running"]:
                return st
            if not _find_pids():
                break
        st = _status()
        if not st["running"]:
            tail = ""
            try:
                with open(BRIDGE_LOG, "rb") as f:
                    f.seek(0, 2)
                    f.seek(max(0, f.tell() - 600))
                    tail = f.read().decode("utf-8", "replace").strip().splitlines()[-1]
            except (OSError, IndexError):
                pass
            st["error"] = "Bridge did not start. " + tail
        return st

    async def stop_bridge(self):
        for pid in _find_pids():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        for _ in range(16):
            await asyncio.sleep(0.25)
            if not _find_pids():
                break
        for pid in _find_pids():
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        # A killed bridge can leave its heartbeat file behind, which would show the in-game line as ON.
        if not _find_pids():
            try:
                os.remove(STATUS)
            except OSError:
                pass
        return _status()

    async def get_autostart(self):
        return bool(_read_json(SETTINGS, {}).get("autostart", False))

    async def set_autostart(self, enabled: bool):
        try:
            os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
            with open(SETTINGS, "w", encoding="utf-8") as f:
                json.dump({"autostart": bool(enabled)}, f)
        except OSError as exc:
            decky.logger.error("settings save failed: %s", exc)
        return bool(enabled)

    async def _main(self):
        decky.logger.info("phonechat plugin loaded")
        try:
            was_running = bool(_find_pids())
            new = _install_bridge()
            if new:
                NOTICE["text"] = "Bridge updated to " + new
                if was_running:            # restart so the new version is the one running
                    await self.stop_bridge()
                    await asyncio.sleep(0.5)
                    await self.start_bridge()
        except Exception as exc:
            decky.logger.error("bridge install failed: %s", exc)
            NOTICE["text"] = "Could not install the bridge: %s" % exc
        if _read_json(SETTINGS, {}).get("autostart") and not _find_pids():
            await asyncio.sleep(2)
            await self.start_bridge()

    async def _unload(self):
        # Leave the bridge running; it is meant to outlive the panel.
        decky.logger.info("phonechat plugin unloaded")

    async def _uninstall(self):
        await self.stop_bridge()
