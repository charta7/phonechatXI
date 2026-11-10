"""Retake the README screenshots from made-up chat, so no real player's words end up in an image.

    python3 tools/screenshots.py            writes docs/screenshots/*.png

Starts the bridge on 127.0.0.1 with a throwaway folder, writes fake lines into its feed,
then runs tools/screenshots.js (Node + Playwright) to capture each page at iPhone size.
Nothing touches your real phonechat folder, link or settings.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
PORT = 8877
CHAR = "Charta"

FIRST = "Hmm... Something is interrupting ventures in these zones..."
WARN = "Hmm... Whatever's stirring in these venture zones is about to reveal itself..."


def feed_lines(now):
    # (seconds ago, channel, direction, name, body)
    return [
        (900, "zone", "in", "", "Lower Jeuno"),
        (890, "motd", "in", "ls1", "Dynamis Saturday 9pm, bring meds"),
        (880, "ls1", "in", "Marlow", "anyone up for a Dynamis run tonight?"),
        (860, "ls2", "in", "Quenby", "what lvl cap are we doing"),
        (840, "party", "in", "Mara", "pulling in 10"),
        (820, "say", "in", "Brigid", "anyone selling crystals?"),
        (800, "tell", "in", "Wren", "got a sec?"),
        (790, "tell", "out", "Wren", "sure, what's up"),
        (780, "tell", "in", "Wren", "can you help with my AF quest later"),
        (760, "finder", "in", "", "Seul is looking for members: Venture (Lv57) - Melee Venture need lv18-20 Join to PF"),
        (740, "shout", "in", "Tolliver", "WTS Shadow cuishes PST"),
        (720, "emote", "in", "", "Sundayninja waves to Charta."),
        (700, "ls1", "in", "Arkonik", "Charta you wanna do anything?"),
        (690, "ls1", "out", CHAR, "on my way ^^"),
        (620, "venture", "in", "Populox", FIRST),
        (620, "venture", "in", "Populox", "Meriphataud Mountains (H-11) / Valkurm Dunes (E-8)"),
        (250, "venture", "in", "Populox", FIRST),
        (250, "venture", "in", "Populox", "Yhoator Jungle (G-7) / Sea Serpent Grotto (K-7)"),
        (120, "bazaar", "in", "", "Mara begins to browse the merchandise in your bazaar."),
        (60, "ls2", "in", "Quenby", "gg all"),
    ]


def main():
    if not shutil.which("node"):
        sys.exit("Needs Node and Playwright (npm i playwright; npx playwright install chromium).")
    work = tempfile.mkdtemp(prefix="pcxi-shots-")
    hb = os.path.join(work, "game.heartbeat")
    stop = threading.Event()

    def beats():
        while not stop.is_set():
            with open(hb, "w") as f:
                f.write("%d %s" % (int(time.time()), CHAR))
            stop.wait(2)

    threading.Thread(target=beats, daemon=True).start()
    bridge = subprocess.Popen([sys.executable, os.path.join(ROOT, "bridge", "bridge.py"), "--dir", work,
                               "--port", str(PORT), "--host", "127.0.0.1"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if os.path.exists(os.path.join(work, "status.json")):
                break
            time.sleep(0.2)
        now = int(time.time())
        with open(os.path.join(work, "feed-%s.log" % CHAR), "ab") as f:
            for ago, ch, d, name, body in feed_lines(now):
                f.write(("%d\t%s\t%s\t%s\t%s\n" % (now - ago, ch, d, name, body)).encode("cp932"))
        time.sleep(4)   # past the bridge's 3 s Populox hold
        url = json.load(open(os.path.join(work, "status.json")))["url"]
        host = url.split("://", 1)[1].split("/", 1)[0]
        url = url.replace(host, "127.0.0.1:%d" % PORT, 1)
        os.makedirs(OUT, exist_ok=True)
        print("writing to", OUT)
        r = subprocess.run(["node", os.path.join(ROOT, "tools", "screenshots.js"), url, OUT])
        if r.returncode:
            sys.exit(r.returncode)
    finally:
        stop.set()
        bridge.terminate()
        bridge.wait(5)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
