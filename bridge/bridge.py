#!/usr/bin/env python3
"""
phonechatXI bridge v1.1.0

Tails feed-<Character>.log files written by the phonechat addon, keeps recent
history in memory, serves the phone page on your home network, and passes
replies and server commands from the phone back to the addon.

    python3 bridge.py [--dir /home/deck/phonechat] [--port 8765] [--host 0.0.0.0] [--open]

The addon copies this folder into its shared folder (<shared>/bridge) and starts it from
there, so the shared folder is normally just the folder above this one.
Needs Python 3.7 or newer (Steam's game container ships 3.7).

Rules this file enforces (see the spec):
  * Nothing is sent unless the phone asked for that one message. The bridge never
    makes up a message on its own: no auto replies, triggers, timers or repeats.
  * Chat goes only to LS1, LS2, party, tells, say and shout. Commands are the
    CatsEye ! server commands and the stock emotes listed in commands.json.
    Everything else is refused.
  * Only tells can be saved to disk, and only when saving is turned on.

Needs only the Python standard library.
"""

import argparse
import atexit
import glob
import ipaddress
import json
import os
import re
import secrets
import shutil
import signal
import socket
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "1.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))

# Max messages kept in memory per channel, so shout/yell spam can't push out LS or tells.
CAPS = {
    "ls1": 500, "ls2": 500, "party": 500, "tell": 600,
    "unity": 300, "say": 300, "shout": 300, "yell": 300, "emote": 200,
    "venture": 200, "server": 100, "system": 150, "zone": 100, "echo": 50,
    "_ack": 300, "finder": 300, "bazaar": 100, "motd": 10,
}
SCROLLBACK = (1, 2, 4)          # Settings > Scrollback multiplies the chat caps above
DEFAULT_CAP = 200

FEED_ROTATE_BYTES = 5 * 1024 * 1024
POLL_SECONDS = 0.5
STATUS_SECONDS = 3
TEASER_HOLD_SECONDS = 3.0

SEND_GAP_SECONDS = 1.0          # one line into the game per second at most
SEND_QUEUE_MAX = 8              # lines waiting; more than this is refused
CONFIRM_SECONDS = 8.0          # no echo from the game after this = "unconfirmed"
FAIL_LINK_SECONDS = 5.0        # a mode 123 line this soon after a send = that send failed
LINE_BYTES = 130                # FFXI's chat line limit; counted on the whole typed line, prefix included
MAX_PARTS = 4
TELLS_KEEP = 50                 # saved lines per person

TARGETS = {"ls1": "/l", "ls2": "/l2", "party": "/p", "tell": "/t", "say": "/s", "shout": "/sh"}
NAME_RE = re.compile(r"^[A-Za-z]{3,15}$")
ARGS_RE = re.compile(r"^[A-Za-z0-9 _\-]{0,40}$")
CALL_RE = re.compile(r"<\s*call\s*(\d{1,2})\s*>", re.I)
ZONE_RE = re.compile(r"^\s*(.+?)\s*\(([A-Z]-\d+)\)\s*$")
YELL_RE = re.compile(r"^(.+?)\[(.*)\]$")
ALERT_RE = re.compile(r"^(?:Pool ([AB]) )?(.+?) is now ([\d.]+)% complete(?: at \(([A-Z]-\d+)\))?")

CURLY = {"‘": "'", "’": "'", "“": '"', "”": '"', "…": "...",
         "–": "-", "—": "-", " ": " "}


def parse_zones(body):
    """'Fort Karugo-Narugo [S] (G-5) / Grauberg [S] (J-9)' -> [{zone, grid}, ...] or None."""
    parts = [p for p in body.split(" / ") if p.strip()]
    zones = []
    for p in parts:
        m = ZONE_RE.match(p)
        if not m:
            return None
        zones.append({"zone": m.group(1), "grid": m.group(2)})
    return zones or None


def norm(s):
    return " ".join((s or "").split()).lower()


# --------------------------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------------------------

class Store:
    """In-memory history with per-channel caps and a condition variable for live streaming."""

    def __init__(self):
        self.cond = threading.Condition()
        self.next_id = 1
        self.by_ch = {}
        self.boot = int(time.time() * 1000)
        self.mult = 1

    def add(self, msg):
        with self.cond:
            msg["id"] = self.next_id
            self.next_id += 1
            dq = self.by_ch.setdefault(msg["ch"], deque())
            dq.append(msg)
            cap = CAPS.get(msg["ch"], DEFAULT_CAP) * self.mult
            while len(dq) > cap:
                dq.popleft()
            self.cond.notify_all()
        return msg

    def _since(self, last_id):
        items = [m for dq in self.by_ch.values() for m in dq if m["id"] > last_id]
        items.sort(key=lambda m: m["id"])
        return items

    def reset(self, keep=None):
        """Forget history (optionally keep some messages) and tell clients to start over."""
        with self.cond:
            for ch, dq in self.by_ch.items():
                self.by_ch[ch] = deque(m for m in dq if keep and keep(m))
            self.boot = int(time.time() * 1000)
            self.cond.notify_all()


store = Store()


# --------------------------------------------------------------------------------------------
# Saved tells (opt-in)
# --------------------------------------------------------------------------------------------

class Tells:
    def __init__(self, folder, cfg, save_cfg):
        self.root = os.path.join(folder, "tells")
        self.cfg = cfg
        self.save_cfg = save_cfg
        self.lock = threading.Lock()

    @property
    def enabled(self):
        return bool(self.cfg.get("save_tells", False))

    def set_enabled(self, on):
        self.cfg["save_tells"] = bool(on)
        self.save_cfg()

    def _path(self, char, peer):
        return os.path.join(self.root, char, peer + ".jsonl")

    def record(self, msg):
        if not self.enabled or msg.get("ch") != "tell" or msg.get("saved"):
            return
        peer = msg.get("name") or ""
        char = msg.get("char") or ""
        if not NAME_RE.match(peer) or not re.match(r"^[\w\-]+$", char):
            return
        row = {k: msg[k] for k in ("ts", "dir", "name", "body")}
        path = self._path(char, peer)
        with self.lock:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                lines = []
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.read().splitlines()
                lines.append(json.dumps(row, ensure_ascii=False))
                lines = lines[-TELLS_KEEP:]
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                os.replace(tmp, path)
            except OSError as exc:
                print("could not save tell:", exc, file=sys.stderr)

    def load(self, only_char=None):
        """Put saved tells back into memory (marked saved) so the Tells tab has history."""
        if not os.path.isdir(self.root):
            return
        rows = []
        for path in glob.glob(os.path.join(self.root, "*", "*.jsonl")):
            char = os.path.basename(os.path.dirname(path))
            if only_char and char != only_char:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except ValueError:
                            continue
                        rows.append({"ts": int(r.get("ts", 0)), "char": char, "ch": "tell",
                                     "dir": r.get("dir", "in"), "name": r.get("name", ""),
                                     "body": r.get("body", ""), "saved": True})
            except OSError:
                pass
        rows.sort(key=lambda m: m["ts"])
        for r in rows:
            store.add(r)

    def clear(self):
        with self.lock:
            shutil.rmtree(self.root, ignore_errors=True)
        store.reset(keep=lambda m: not m.get("saved"))


# --------------------------------------------------------------------------------------------
# Sending (phone -> outbox -> addon)
# --------------------------------------------------------------------------------------------

class SendError(Exception):
    pass


def clean_text(text):
    text = "".join(CURLY.get(c, c) for c in (text or ""))
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)          # control characters and newlines
    out = []
    for c in text:
        try:
            c.encode("cp932")
        except UnicodeEncodeError:
            continue                                        # emoji and anything the game can't show
        out.append(c)
    return " ".join("".join(out).split())


class Commands:
    def __init__(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.info = dict(data.get("info", {}))
        self.action = dict(data.get("action", {}))
        self.emotes = set(data.get("emotes", []))
        self.jobs = set(j.upper() for j in data.get("jobs", []))

    def public(self):
        return {"info": self.info, "action": self.action,
                "emotes": sorted(self.emotes), "jobs": sorted(self.jobs)}

    def emote(self, text):
        """'/wave', '/wave motion', '/wave text', '/sitchair 2', '/jobemote war' -> line, or None."""
        m = re.match(r"^/([a-z][a-z0-9]*)(?:\s+([a-z0-9]+))?$", text.lower())
        if not m:
            return None
        name, opt = m.group(1), m.group(2) or ""
        if name == "jobemote":
            return "/jobemote " + opt if opt.upper() in self.jobs else None
        if name not in self.emotes:
            return None
        if opt in ("", "motion", "text") or (name == "sitchair" and opt in ("1", "2", "3", "4")):
            return "/" + name + ((" " + opt) if opt else "")
        return None

    def check(self, text, confirmed):
        """Return the game command for an allowed command, or raise SendError."""
        text = clean_text(text)
        if not text:
            raise SendError("Empty command.")
        line = self.emote(text)
        if line:
            return line, False
        m = re.match(r"^!([A-Za-z]+)(?:\s+(.*))?$", text)
        if not m:
            raise SendError("Blocked: not an allowed command.")
        name, args = m.group(1).lower(), (m.group(2) or "").strip()
        if name not in self.info and name not in self.action:
            raise SendError("Blocked: not an allowed command.")
        if not ARGS_RE.match(args):
            raise SendError("Blocked: arguments can only use letters, numbers, spaces, _ and -.")
        if name in self.action and not confirmed:
            raise SendError("needs_confirm")
        return "/say !" + name + ((" " + args) if args else ""), name in self.action


class Sender(threading.Thread):
    def __init__(self, folder):
        super().__init__(daemon=True)
        self.folder = folder
        self.lock = threading.Lock()
        self.queue = deque()           # lines waiting to go into the outbox
        self.pending = {}              # pid -> info, for chat lines waiting on the game's echo
        self.last_cmd = 0.0            # when the last command went out (for showing replies)
        self.char = None               # character the outbox belongs to

    def outbox(self):
        if not self.char:
            raise SendError("The game is not connected yet (no character seen).")
        return os.path.join(self.folder, "outbox-%s.log" % self.char)

    def enqueue(self, items):
        with self.lock:
            if len(self.queue) + len(items) > SEND_QUEUE_MAX:
                raise SendError("Too many messages waiting. Try again in a few seconds.")
            self.outbox()
            for it in items:
                self.queue.append(it)

    def chat(self, target, peer, text):
        if target not in TARGETS:
            raise SendError("That channel can't be sent to.")
        raw = (text or "").strip()
        if raw.startswith("/") or raw.startswith("!"):
            raise SendError("Commands go through Game command, not chat.")
        text = clean_text(raw)
        if not text:
            raise SendError("Nothing to send after cleaning the text.")
        prefix = TARGETS[target]
        if target == "tell":
            if not NAME_RE.match(peer or ""):
                raise SendError("Tell needs a character name (letters only).")
            prefix = "/t " + peer
        room = LINE_BYTES - len((prefix + " ").encode("cp932"))
        size = len(text.encode("cp932"))
        if size > room:
            # One tap = one line. Never split a message into several sends.
            raise SendError("Too long for one chat line: %d over the %d limit." % (size - room, room))
        parts = [text]
        sid = secrets.token_hex(4)
        items = []
        for i, p in enumerate(parts):
            pid = "%s-%d" % (sid, i)
            items.append({"pid": pid, "kind": "chat", "ch": target, "peer": peer if target == "tell" else "",
                          "text": p, "line": prefix + " " + p})
        self.enqueue(items)
        return [{"pid": it["pid"], "text": it["text"]} for it in items]

    def command(self, line):
        pid = "c" + secrets.token_hex(4)
        self.enqueue([{"pid": pid, "kind": "cmd", "ch": "cmd", "peer": "", "text": line, "line": line}])
        return pid

    # ----- matching what comes back from the game -----

    def match_echo(self, ch, name, body):
        """An outgoing line showed up in the feed. Return the pid it confirms, if any."""
        now = time.time()
        with self.lock:
            best = None
            for pid, p in self.pending.items():
                if p["state"] != "sending" or p["ch"] != ch:
                    continue
                if ch == "tell" and p["peer"].lower() != (name or "").lower():
                    continue
                if norm(p["text"]) == norm(body):
                    best = pid
                    break
                if best is None and norm(body)[:12] == norm(p["text"])[:12] and now - p["at"] < CONFIRM_SECONDS:
                    best = pid
            if best:
                self.pending[best]["state"] = "sent"
        if best:
            ack(best, "sent")
        return best

    def match_failure(self, body):
        now = time.time()
        with self.lock:
            hit = None
            for pid, p in sorted(self.pending.items(), key=lambda kv: -kv[1]["at"]):
                if p["state"] == "sending" and now - p["at"] <= FAIL_LINK_SECONDS and p["ch"] in ("tell", "party"):
                    hit = pid
                    break
            hits = []
            if hit:
                sid = hit.split("-")[0]
                for pid, p in self.pending.items():          # every part of a split message
                    if pid.split("-")[0] == sid and p["state"] in ("sending", "unconfirmed"):
                        p["state"] = "failed"
                        hits.append(pid)
        for pid in hits:
            ack(pid, "failed", body)

    def run(self):
        while True:
            item = None
            with self.lock:
                if self.queue:
                    item = self.queue.popleft()
            if item:
                self.write(item)
                time.sleep(SEND_GAP_SECONDS)
            else:
                time.sleep(0.2)
            self.expire()

    def write(self, item):
        try:
            line = "%s\t%d\t%s\n" % (item["pid"], int(time.time()), item["line"])
            with open(self.outbox(), "ab") as f:
                f.write(line.encode("cp932", errors="ignore"))
        except (OSError, SendError) as exc:
            ack(item["pid"], "failed", "Could not write to the game: %s" % exc)
            return
        if item["kind"] == "cmd":
            self.last_cmd = time.time()
            ack(item["pid"], "sent")
        else:
            with self.lock:
                self.pending[item["pid"]] = {"ch": item["ch"], "peer": item["peer"], "text": item["text"],
                                             "at": time.time(), "state": "sending"}

    def expire(self):
        now = time.time()
        late = []
        with self.lock:
            for pid, p in list(self.pending.items()):
                if p["state"] == "sending" and now - p["at"] > CONFIRM_SECONDS:
                    p["state"] = "unconfirmed"
                    late.append(pid)
                if now - p["at"] > 120:
                    del self.pending[pid]
        for pid in late:
            ack(pid, "unconfirmed")


def ack(pid, state, reason=""):
    store.add({"ts": int(time.time()), "char": "", "ch": "_ack", "dir": "", "name": "", "body": "",
               "pid": pid, "state": state, "reason": reason})


# --------------------------------------------------------------------------------------------
# Feed tailing (addon -> bridge)
# --------------------------------------------------------------------------------------------

class Tailer(threading.Thread):
    def __init__(self, folder, sender, tells):
        super().__init__(daemon=True)
        self.folder = folder
        self.sender = sender
        self.tells = tells
        self.files = {}
        self.pending = {}
        self.plock = threading.Lock()

    def handle_line(self, char, raw):
        text = raw.decode("cp932", errors="replace").rstrip("\r")
        parts = text.split("\t", 4)
        if len(parts) != 5:
            return
        ts, ch, direction, name, body = parts
        try:
            ts = int(ts)
        except ValueError:
            return
        body = body.replace("\x0b", "\n")
        msg = {"ts": ts, "char": char, "ch": ch, "dir": direction, "name": name, "body": body}

        if ch == "yell":
            m = YELL_RE.match(name)
            if m:
                msg["name"], msg["zone"] = m.group(1), m.group(2)
        calls = [int(n) for n in CALL_RE.findall(body) if 1 <= int(n) <= 25]
        if calls:
            msg["calls"] = calls
            msg["callonly"] = CALL_RE.sub("", body).strip() == ""

        if direction == "out" and ch in TARGETS:
            pid = self.sender.match_echo(ch, msg["name"], body)
            if pid:
                msg["pid"] = pid
        if ch == "system":
            self.sender.match_failure(body)

        if ch == "venture":
            self.handle_venture(char, msg)
            return
        if ch == "echo" and time.time() - self.sender.last_cmd > 10:
            return                               # only show /echo output right after a phone command
        store.add(msg)
        if ch == "tell":
            self.tells.record(msg)

    def handle_venture(self, char, msg):
        if msg["name"] == "Seals":                   # "A (F-7) / B (G-6), C (D-9) / D (H-9)"
            pairs = [parse_zones(p) for p in msg["body"].split(", ")]
            if all(pairs):
                msg["zones"] = [z for pair in pairs for z in pair]
            store.add(msg)
            return
        if msg["name"] == "ventures":                # alert line from the ventures addon
            m = ALERT_RE.match(msg["body"])
            if m:
                msg["pool"], msg["area"] = m.group(1) or "", m.group(2)
                msg["pct"] = float(m.group(3))
                if m.group(4):
                    msg["grid"] = m.group(4)
            store.add(msg)
            return
        zones = parse_zones(msg["body"])
        with self.plock:
            held = self.pending.pop(char, None)
            if held:
                held[1].cancel()
            if zones:
                msg["zones"] = zones
                if held:
                    msg["teaser"] = held[0]["body"]
                    msg["ts"] = held[0]["ts"]
                store.add(msg)
                return
            if held:
                store.add(held[0])
            if msg["name"] == "Populox":
                timer = threading.Timer(TEASER_HOLD_SECONDS, self.flush_teaser, args=(char, msg))
                timer.daemon = True
                self.pending[char] = (msg, timer)
                timer.start()
            else:
                store.add(msg)

    def flush_teaser(self, char, msg):
        with self.plock:
            held = self.pending.get(char)
            if held and held[0] is msg:
                del self.pending[char]
                store.add(msg)

    def poll_file(self, path):
        char = os.path.basename(path)[len("feed-"):-len(".log")]
        try:
            size = os.path.getsize(path)
        except OSError:
            return
        st = self.files.get(path)
        if st is None:
            st = {"off": 0, "buf": b""}
            self.files[path] = st
        elif size < st["off"]:
            # Addon reloaded and emptied the file: start over for this character.
            store.reset(keep=lambda m: m.get("char") != char)
            self.tells.load(only_char=char)
            st["off"], st["buf"] = 0, b""
        self.sender.char = char          # replies go to the character whose feed is live

        if size > st["off"]:
            try:
                with open(path, "rb") as f:
                    f.seek(st["off"])
                    data = f.read(size - st["off"])
            except OSError:
                return
            st["off"] += len(data)
            data = st["buf"] + data
            lines = data.split(b"\n")
            st["buf"] = lines.pop()
            for line in lines:
                if line:
                    self.handle_line(char, line)

        if st["off"] > FEED_ROTATE_BYTES:
            # Move the file aside, read anything the addon appended in the meantime, then drop
            # it. The addon opens the feed for each line, so its next line starts a new file.
            old = path + ".old"
            try:
                os.replace(path, old)
                with open(old, "rb") as f:
                    f.seek(st["off"])
                    rest = f.read()
                os.remove(old)
            except OSError:
                rest = b""
            data = st["buf"] + rest
            st["off"], st["buf"] = 0, b""
            for line in data.split(b"\n"):
                if line:
                    self.handle_line(char, line)

    def run(self):
        while True:
            try:
                paths = glob.glob(os.path.join(self.folder, "feed-*.log"))
                paths.sort(key=lambda p: os.path.getmtime(p))     # newest last = current character
                for gone in set(self.files) - set(paths):
                    del self.files[gone]
                for p in paths:
                    self.poll_file(p)
            except Exception as exc:  # keep the bridge alive no matter what
                print("tailer error:", exc, file=sys.stderr)
            time.sleep(POLL_SECONDS)


# --------------------------------------------------------------------------------------------
# Config, address, status
# --------------------------------------------------------------------------------------------

CFG_PATH = os.path.join(HERE, "config.json")


def load_config():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        tmp = CFG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1)
        os.replace(tmp, CFG_PATH)
    except OSError as exc:
        print("could not save config:", exc, file=sys.stderr)


LINK = {"cfg": None, "port": 0, "folder": ""}


def new_link():
    """Replace the phone link token. Old links stop working right away."""
    cfg = LINK["cfg"]
    cfg["token"] = secrets.token_urlsafe(12)
    save_config(cfg)
    Handler.token = cfg["token"]
    Handler.url = "http://%s:%d/?t=%s" % (lan_ip(), LINK["port"], cfg["token"])
    Handler.gen += 1
    with store.cond:
        store.cond.notify_all()
    write_status(LINK["folder"], Handler.url, True)
    print("new phone link:", Handler.url)


PREFS_MAX = 64 * 1024


def load_prefs(folder):
    try:
        with open(os.path.join(folder, "phone-settings.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def save_prefs(folder, prefs):
    path = os.path.join(folder, "phone-settings.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prefs, f)
    os.replace(tmp, path)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))     # no packet is actually sent
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def write_status(folder, url, running=True):
    path = os.path.join(folder, "status.json")
    tmp = path + ".tmp"
    data = {"ts": int(time.time()), "running": running, "url": url, "version": VERSION}
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        pass


def clear_status(folder):
    try:
        os.remove(os.path.join(folder, "status.json"))
    except OSError:
        pass


def start_fresh(folder):
    """Privacy: empty the feed and outbox files when the bridge starts."""
    for pattern in ("feed-*.log", "outbox-*.log"):
        for p in glob.glob(os.path.join(folder, pattern)):
            try:
                os.truncate(p, 0)
            except OSError:
                pass
    try:
        os.remove(os.path.join(folder, "stop.request"))
    except OSError:
        pass


# --------------------------------------------------------------------------------------------
# Web server
# --------------------------------------------------------------------------------------------

def host_ok(host):
    h = (host or "").strip().lower()
    if h.startswith("["):
        h = h[1:h.find("]")] if "]" in h else h
    else:
        h = h.rsplit(":", 1)[0] if h.count(":") == 1 else h
    if h in ("localhost", socket.gethostname().lower()) or h.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


# Icons are public (iOS fetches the home-screen icon without the token). Nothing private in them.
ICONS = ("apple-touch-icon.png", "icon-512.png", "favicon-32.png", "pearl-48.png", "pearl-96.png", "wordmark.png")
# Fonts ship with the bridge so the phone page never calls out to Google Fonts. Also public.
FONTS = ("cinzel-latin-600-normal.woff2", "cinzel-latin-700-normal.woff2",
         "atkinson-hyperlegible-latin-400-normal.woff2", "atkinson-hyperlegible-latin-700-normal.woff2",
         "atkinson-hyperlegible-latin-400-italic.woff2",
         "jetbrains-mono-latin-400-normal.woff2", "jetbrains-mono-latin-700-normal.woff2")

SETUP_PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>phonechatXI setup</title><script src="/qr.js"></script><link rel="icon" href="/icons/favicon-32.png">
<style>body{margin:0;background:#0b1020;color:#e8ecf6;font:16px system-ui,sans-serif;display:flex;justify-content:center}
main{max-width:420px;padding:32px 20px;text-align:center}h1{color:#d9b45a;font-weight:700;letter-spacing:.5px}
#qr{background:#fff;border-radius:12px;padding:10px;width:240px;margin:20px auto}a{color:#7fb2ff;word-break:break-all}
p{color:#c9d2ec;line-height:1.5}</style></head><body><main><h1><img src="/icons/wordmark.png" alt="phonechatXI" style="width:100%%;max-width:380px"></h1>
<p>Scan with your phone's camera. Your phone has to be on the same Wi-Fi.</p><div id="qr"></div>
<p><a href="%(url)s">%(url)s</a></p><p>Bridge %(version)s is running. Watching %(folder)s</p>
<form method="post" action="/setup/newlink" onsubmit="return confirm('Make a new phone link? The old link stops working and you will need to scan the new QR.')">
<button style="font:inherit;color:#e8ecf6;background:#1d2850;border:1px solid #3a4a80;border-radius:10px;padding:10px 16px">Make a new link</button></form>
<p style="font-size:13px;color:#8e9ac0">Use this if someone else saw your link or QR. Your phone will need to scan again.</p></main>
<script>var q=qrcode(0,"M");q.addData("%(url)s");q.make();document.getElementById("qr").innerHTML=q.createSvgTag({cellSize:5,margin:2,scalable:true});</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "phonechatXI/" + VERSION
    protocol_version = "HTTP/1.1"
    token = ""
    url = ""
    gen = 0          # bumps when the link changes; open streams on the old link close
    folder = ""
    sender = None
    tells = None
    commands = None

    def log_message(self, *args):
        pass

    def send_body(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, code, obj):
        self.send_body(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def authed(self, q):
        given = self.headers.get("X-Token") or (q.get("t") or [""])[0]
        return bool(given) and secrets.compare_digest(given, self.token)

    def static(self, name, ctype):
        try:
            with open(os.path.join(HERE, name), "rb") as f:
                self.send_body(200, f.read(), ctype)
        except OSError:
            self.send_body(404, "missing " + name)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/favicon.ico":
            self.static("icons/favicon-32.png", "image/png")
            return
        if u.path.startswith("/icons/") and u.path[7:] in ICONS:
            self.static("icons/" + u.path[7:], "image/png")
            return
        if u.path.startswith("/fonts/") and u.path[7:] in FONTS:
            self.static("fonts/" + u.path[7:], "font/woff2")
            return
        if u.path == "/qr.js":
            self.static("qrcode.js", "application/javascript; charset=utf-8")
            return
        if u.path == "/setup":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                self.send_body(403, "Open /setup on the computer running the bridge.")
                return
            self.send_body(200, SETUP_PAGE % {"url": self.url, "version": VERSION, "folder": self.folder},
                           "text/html; charset=utf-8")
            return
        if not self.authed(q):
            self.send_body(403, "forbidden")
            return
        if u.path == "/":
            self.static("index.html", "text/html; charset=utf-8")
        elif u.path == "/events":
            self.stream()
        elif u.path == "/api/status":
            self.send_json(200, {"version": VERSION, "url": self.url, "boot": store.boot,
                                 "char": self.sender.char, "save_tells": self.tells.enabled,
                                 "scrollback": store.mult})
        elif u.path == "/api/prefs":
            self.send_json(200, {"prefs": load_prefs(self.folder)})
        elif u.path == "/api/commands":
            self.send_json(200, self.commands.public())
        else:
            self.send_body(404, "not found")

    def do_POST(self):
        u = urlparse(self.path)
        if not host_ok(self.headers.get("Host")):
            self.send_body(403, "bad host")
            return
        if u.path == "/setup/newlink":
            # Only from the computer running the bridge, and only from its own /setup page.
            origin = self.headers.get("Origin") or ""
            local = ("http://localhost:%d" % self.server.server_port, "http://127.0.0.1:%d" % self.server.server_port)
            if self.client_address[0] not in ("127.0.0.1", "::1") or (origin and origin not in local):
                self.send_body(403, "forbidden")
                return
            new_link()
            self.send_response(303)
            self.send_header("Location", "/setup")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if not self.headers.get("X-Token") or not secrets.compare_digest(self.headers.get("X-Token"), self.token):
            self.send_body(403, "forbidden")
            return
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            self.send_body(415, "json only")
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > (PREFS_MAX if u.path == "/api/prefs" else 4096):
                raise ValueError
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            self.send_body(400, "bad request")
            return

        try:
            if u.path == "/api/send":
                parts = self.sender.chat(body.get("target"), body.get("peer") or "", body.get("text") or "")
                self.send_json(200, {"ok": True, "parts": parts})
            elif u.path == "/api/command":
                line, _ = self.commands.check(body.get("text") or "", bool(body.get("confirm")))
                pid = self.sender.command(line)
                self.send_json(200, {"ok": True, "pid": pid, "line": line})
            elif u.path == "/api/settings":
                if "save_tells" in body:
                    self.tells.set_enabled(bool(body["save_tells"]))
                if body.get("scrollback") in SCROLLBACK:
                    store.mult = int(body["scrollback"])
                    self.tells.cfg["scrollback"] = store.mult
                    self.tells.save_cfg()
                self.send_json(200, {"ok": True, "save_tells": self.tells.enabled, "scrollback": store.mult})
            elif u.path == "/api/tells/clear":
                self.tells.clear()
                self.send_json(200, {"ok": True})
            elif u.path == "/api/prefs":
                # Phone page settings (views, colors, favorites...), kept so a new Home Screen
                # shortcut or a second phone picks them up. Never holds the link token.
                prefs = body.get("prefs")
                if not isinstance(prefs, dict):
                    raise SendError("Settings must be an object.")
                save_prefs(self.folder, prefs)
                self.send_json(200, {"ok": True})
            else:
                self.send_body(404, "not found")
        except SendError as exc:
            msg = str(exc)
            if msg == "needs_confirm":
                self.send_json(409, {"ok": False, "needs_confirm": True})
            else:
                self.send_json(400, {"ok": False, "error": msg})

    def stream(self):
        try:
            last = int(self.headers.get("Last-Event-ID") or 0)
        except ValueError:
            last = 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.close_connection = True
        my_boot = None
        my_gen = Handler.gen
        try:
            while True:
                if Handler.gen != my_gen:
                    return                       # the link was replaced
                with store.cond:
                    if my_boot == store.boot:
                        items = store._since(last)
                        if not items:
                            store.cond.wait(15)
                            items = store._since(last) if my_boot == store.boot else []
                    else:
                        items = []
                    boot_now = store.boot
                out = []
                if boot_now != my_boot:
                    if my_boot is not None:
                        last = 0                 # history was reset: send everything again
                    my_boot = boot_now
                    out.append("event: hello\ndata: %s\n\n" % json.dumps({"boot": boot_now}))
                    with store.cond:
                        items = store._since(last)
                for m in items:
                    out.append("id: %d\ndata: %s\n\n" % (m["id"], json.dumps(m, ensure_ascii=False)))
                    last = m["id"]
                if not out:
                    out.append(": ping\n\n")
                self.wfile.write("".join(out).encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


def dir_from_txt(addon_dir):
    """When run from inside the addon folder: use the addon's dir.txt (a Z:\\ path on Linux)."""
    try:
        with open(os.path.join(addon_dir, "dir.txt"), "r", encoding="utf-8-sig") as f:
            txt = f.read().strip()
    except OSError:
        return ""
    if re.match(r"^[Zz]:\\", txt):
        txt = txt[2:].replace("\\", "/")
    return txt.rstrip("/\\") if txt else ""


def main():
    ap = argparse.ArgumentParser(description="phonechatXI bridge")
    ap.add_argument("--dir", default="", help="shared folder with the addon's feed files (remembered)")
    ap.add_argument("--port", type=int, default=0, help="web port (remembered, default 8765)")
    ap.add_argument("--host", default="0.0.0.0", help="address to listen on")
    ap.add_argument("--open", action="store_true", help="open the setup page (QR) in a browser")
    args = ap.parse_args()

    cfg = load_config()
    if args.dir:
        cfg["dir"] = os.path.abspath(os.path.expanduser(args.dir))
    if args.port:
        cfg["port"] = args.port
    if "dir" not in cfg and os.path.exists(os.path.join(os.path.dirname(HERE), "phonechat.lua")):
        guess = dir_from_txt(os.path.dirname(HERE))       # running from the addon folder
        if guess:
            cfg["dir"] = guess
    cfg.setdefault("dir", os.path.dirname(HERE))
    cfg.setdefault("port", 8765)
    cfg.setdefault("save_tells", False)
    if cfg.get("scrollback") in SCROLLBACK:
        store.mult = int(cfg["scrollback"])
    if not cfg.get("token"):
        cfg["token"] = secrets.token_urlsafe(12)
    save_config(cfg)

    folder = cfg["dir"]
    os.makedirs(folder, exist_ok=True)
    newlink_file = os.path.join(folder, "newlink.request")
    if os.path.exists(newlink_file):            # asked for a new link while the bridge was off
        cfg["token"] = secrets.token_urlsafe(12)
        save_config(cfg)
        try:
            os.remove(newlink_file)
        except OSError:
            pass
    start_fresh(folder)
    port = int(cfg["port"])
    url = "http://%s:%d/?t=%s" % (lan_ip(), port, cfg["token"])

    sender = Sender(folder)
    tells = Tells(folder, cfg, lambda: save_config(cfg))
    tells.load()

    Handler.token = cfg["token"]
    Handler.url = url
    LINK.update(cfg=cfg, port=port, folder=folder)
    Handler.folder = folder
    Handler.sender = sender
    Handler.tells = tells
    Handler.commands = Commands(os.path.join(HERE, "commands.json"))

    sender.start()
    Tailer(folder, sender, tells).start()

    def status_loop():
        stop_file = os.path.join(folder, "stop.request")
        while True:
            if os.path.exists(stop_file):          # /pchat stop from inside the game
                try:
                    os.remove(stop_file)
                except OSError:
                    pass
                print("stop requested from the game")
                os.kill(os.getpid(), signal.SIGTERM)
                return
            if os.path.exists(newlink_file):      # "New phone link" from the in-game window
                try:
                    os.remove(newlink_file)
                except OSError:
                    pass
                new_link()
            write_status(folder, Handler.url, True)
            time.sleep(STATUS_SECONDS)

    atexit.register(clear_status, folder)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))

    try:
        httpd = ThreadingHTTPServer((args.host, port), Handler)
    except OSError as exc:
        print("Could not use port %d (%s). Try: start.sh --port 8780" % (port, exc))
        sys.exit(1)
    httpd.daemon_threads = True
    threading.Thread(target=status_loop, daemon=True).start()
    print("phonechatXI bridge %s" % VERSION)
    print("watching:", folder)
    print("open on your phone:", url)
    print("on this computer: http://localhost:%d/setup" % port)
    sys.stdout.flush()
    if args.open:
        def open_setup():
            try:
                import webbrowser
                webbrowser.open("http://localhost:%d/setup" % port)
            except Exception:
                pass
        threading.Timer(1.0, open_setup).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
