#!/usr/bin/env python3
"""
phonechatXI replay: a test tool, not part of the addon or the release.

Plays a /pchat debug log back through the real addon code (addon/phonechat/phonechat.lua)
with a fake Ashita around it, so the lines go through the same parsing as in game and
end up in the bridge's feed file. Use it to test CatsEye's real chat text without
the game running.

Nothing here touches the game. The fake Ashita can't type, start programs or reach
the network: sending is logged to this window instead, and program starts are refused.

Use:
  1. Close the game. Start the bridge by itself (the phonechatXI Bridge launcher, or start.sh).
  2. pip install lupa      (once; the Lua runtime this uses)
  3. python3 replay.py ~/phonechat/debug-Charta.log
        --fast       5x speed          --instant   no waiting between lines
        --dir DIR    the bridge's folder (default ~/phonechat)
        --char NAME  character name for the feed file (default: from the log's file name)
  4. Open the phone page as usual.

Heads-up: like the addon, this starts that character's feed file over when it begins.

Debug logs come from /pchat debug on an approved version, played normally. They hold
raw chat lines, including other players' chat, so don't share them publicly.
"""
import argparse, os, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(HERE, "..", "addon", "phonechat", "phonechat.lua")

FAKE_ASHITA = r'''
FAKE_CLOCK = 0
os.clock = function() return FAKE_CLOCK end
os.execute = function(c) SAY("refused to run a program: " .. tostring(c)) return false end
io.popen = nil
addon = { path = ADDON_DIR }
package.preload['common'] = function()
  function string:args() local t = {} for w in self:gmatch('%S+') do t[#t+1] = w end return t end
  return {}
end
package.preload['chat'] = function()
  local m = {}
  function m.header(n) return { append = function(_, x) return '[' .. n .. '] ' .. x end } end
  function m.message(t) return t end
  function m.success(t) return t end
  function m.error(t) return t end
  return m
end
print = function(s) SAY('addon: ' .. tostring(s)) end
EVENTS = {}
AshitaCore = {
  GetChatManager = function() return {
    -- No game here, so auto-translate stays unexpanded and shows as [item] / [auto-translate].
    ParseAutoTranslate = function(self, s, b) return s end,
    QueueCommand = function(self, mode, cmd) SAY('would type (not sent): ' .. tostring(cmd)) end } end,
  GetInstallPath = function() return '' end,
  GetMemoryManager = function() return { GetParty = function() return {
    GetMemberName = function(self, i) return CHAR_NAME end } end } end,
}
ashita = { events = { register = function(n, id, fn) EVENTS[n] = fn end },
           fs = { create_dir = function(p) MKDIR(p) end, exists = function(p) return EXISTS(p) end } }
local real_open = io.open
io.open = function(p, m) return real_open((p:gsub('\\', '/')), m) end
'''

LINE_RE = re.compile(rb"^(\d\d):(\d\d):(\d\d)\t(\d+)\t(\d+)\t(.*)$")


def unescape(b):
    """The debug log writes control bytes as \\xNN. Turn them back into bytes."""
    return re.sub(rb"\\x([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), b)


def main():
    ap = argparse.ArgumentParser(description="Replay a /pchat debug log through the addon, into the bridge's feed.")
    ap.add_argument("log", help="a debug-<Char>.log file from /pchat debug")
    ap.add_argument("--dir", default=os.path.join(os.path.expanduser("~"), "phonechat"), help="the bridge's folder")
    ap.add_argument("--char", help="character name (default: from the log's file name)")
    ap.add_argument("--fast", action="store_true", help="5x speed")
    ap.add_argument("--instant", action="store_true", help="no waiting between lines")
    a = ap.parse_args()
    # Ashita runs addons on LuaJIT, so use the same Lua here (newer Lua versions differ).
    LuaRuntime = None
    for mod in ("luajit21", "luajit20", "lua51"):
        try:
            LuaRuntime = __import__("lupa." + mod, fromlist=["LuaRuntime"]).LuaRuntime
            break
        except ImportError:
            pass
    if LuaRuntime is None:
        sys.exit("This needs the lupa package (pip install lupa) with LuaJIT or Lua 5.1.")
    if not os.path.isdir(a.dir):
        sys.exit("Can't find %s. Start the bridge once so it makes that folder, or pass --dir." % a.dir)
    m = re.search(r"debug-(\w+)\.log$", os.path.basename(a.log))
    char = a.char or (m.group(1) if m else None)
    if not char:
        sys.exit("Couldn't tell the character from the file name. Pass --char NAME.")

    # The addon reads dir.txt next to itself to find the shared folder. Run it from a temp copy
    # so nothing is written into the repo.
    tmp = tempfile.mkdtemp(prefix="pcxi-replay-")
    shutil.copy(ADDON, tmp)
    shutil.copy(os.path.join(os.path.dirname(ADDON), "qrencode.lua"), tmp)
    with open(os.path.join(tmp, "dir.txt"), "w") as f:
        f.write(os.path.join(os.path.abspath(a.dir), ""))

    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    g.SAY = lambda s: print("  " + str(s))
    g.MKDIR = lambda p: os.makedirs(p.replace("\\", "/"), exist_ok=True)
    g.EXISTS = lambda p: os.path.exists(p.replace("\\", "/"))
    g.ADDON_DIR = os.path.join(tmp, "")
    g.CHAR_NAME = char
    lua.execute(FAKE_ASHITA)
    with open(os.path.join(tmp, "phonechat.lua"), "rb") as f:
        lua.execute(f.read())          # as bytes: the addon's patterns work on raw Shift-JIS bytes
    ev = g.EVENTS
    ev["load"]()

    speed = 1 if not a.fast else 5
    prev = None
    n = 0
    print("Replaying %s as %s into %s (Ctrl+C to stop)" % (a.log, char, a.dir))
    try:
        with open(a.log, "rb") as f:
            for raw in f:
                m = LINE_RE.match(raw.rstrip(b"\r\n"))
                if not m:
                    continue
                t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                if prev is not None and not a.instant:
                    time.sleep(min(max(t - prev, 0), 10) / speed)   # long gaps are cut to 10 seconds
                prev = t
                msg = m.group(6)
                injected = msg.startswith(b"[addon] ")
                if injected:
                    msg = msg[len(b"[addon] "):]
                e = lua.table_from({"mode": int(m.group(4)), "message": unescape(msg), "injected": injected, "blocked": False})
                ev["text_in"](e)
                n += 1
                g.FAKE_CLOCK = g.FAKE_CLOCK + 1
                ev["d3d_present"]()
    except KeyboardInterrupt:
        print("\nStopped.")
    shutil.rmtree(tmp, ignore_errors=True)
    print("Done: %d lines replayed." % n)


if __name__ == "__main__":
    main()
