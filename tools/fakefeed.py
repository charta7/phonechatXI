#!/usr/bin/env python3
"""
phonechatXI fake feed: a test tool, not part of the addon or the release.

It writes made-up chat lines into the bridge's feed file so you can test the
phone page with no game running. The lines are already parsed, in the format the
addon writes. To test the addon's parsing with real lines, use replay.py. Nothing here touches the game. With the addon
unloaded, nothing you send from the phone reaches the game either.

Use:
  1. Close the game. Start the bridge by itself (the phonechatXI Bridge launcher, or start.sh).
  2. Run this:   python3 fakefeed.py            (plays one short session)
                 python3 fakefeed.py --loop     (repeats a venture alert every few minutes)
                 python3 fakefeed.py --fast     (5x speed, for a quick look)
  3. Open the phone page as usual.

If the bridge's folder isn't ~/phonechat, pass it:  --dir "Z:\\home\\deck\\phonechat"
Python 3.7 or newer, no extra packages.
"""
import argparse, os, sys, time, random

# (seconds to wait first, channel, direction, name, body)
SESSION = [
    (0,  "zone",    "in", "", "Lower Jeuno"),
    (1,  "ls1",     "in", "Marlow", "anyone up for a Dynamis run tonight?"),
    (4,  "ls2",     "in", "Quenby", "what lvl cap are we doing"),
    (5,  "party",   "in", "Mara", "pulling in 10"),
    (6,  "ls1",     "in", "Arkonik", "Charta you wanna do anything?"),
    (4,  "ls1",     "in", "Arkonik", "char are you around"),
    (5,  "emote",   "in", "", "Sundayninja examines you."),
    (6,  "tell",    "in", "Wren", "got a sec?"),
    (5,  "shout",   "in", "Brigid", "SAM68 anylvl ventures PST"),
    (4,  "finder",  "in", "", "Seul is looking for members: Venture (Lv57) - Melee Venture need lv18-20 Join to PF"),
    (4,  "ls1",     "in", "Tolliver", "{I can understand a little.} guide https://www.bg-wiki.com/ffxi/CatsEyeXI_Commands"),
    (5,  "server",  "in", "", "This command may only be used in cities."),
    (6,  "ls1",     "in", "Quenby", "selling {{Suppanomimi}} for {Looking for party}"),
    (8,  "ls1",     "in", "Marlow", "<call 1>"),
    (1,  "venture", "in", "Populox", "Hmm... Whatever's stirring in these venture zones is about to reveal itself..."),
    (1,  "venture", "in", "Populox", "Meriphataud Mountains (H-11) / Valkurm Dunes (E-8)"),
    (6,  "ls1",     "in", "Tolliver", "nice, VNM time"),
    (5,  "bazaar",  "in", "", "Mara begins to browse the merchandise in your bazaar."),
    (4,  "unity",   "in", "Apururu", "Looks like our forces-warses are gathering!"),
    (6,  "unity",   "in", "Apururu", "Kumhau could appear anytime in the next 5 minutes"),
]

CHATTER = [
    ("ls1", "Marlow", "brb 5"), ("ls1", "Tolliver", "who has a spare Charta tell me"),
    ("ls2", "Quenby", "lol"), ("party", "Mara", "ready when you are"),
    ("say", "Brigid", "anyone selling crystals?"), ("ls1", "Arkonik", "char check your tells"),
    ("shout", "Seller", "WTS rare stuff cheap"), ("ls1", "Marlow", "gg"),
]
ZONES = [
    "Meriphataud Mountains (H-11) / Valkurm Dunes (E-8)",
    "Fort Karugo-Narugo [S] (G-5) / Grauberg [S] (J-9)",
    "Qufim Island (F-7) / Yuhtunga Jungle (G-6)",
]


def default_dir():
    d = os.path.join(os.path.expanduser("~"), "phonechat")
    return d


def emit(path, ch, direction, name, body):
    line = "%d\t%s\t%s\t%s\t%s\n" % (int(time.time()), ch, direction, name, body)
    with open(path, "ab") as f:
        f.write(line.encode("cp932", "replace"))
    print("%s  %-7s %s%s" % (time.strftime("%H:%M:%S"), ch, (name + ": ") if name else "", body))


def main():
    ap = argparse.ArgumentParser(description="Play fake chat lines into the phonechatXI bridge.")
    ap.add_argument("--dir", default=default_dir(), help="the bridge's shared folder (default: ~/phonechat)")
    ap.add_argument("--char", default="Charta", help="character name the feed file is for")
    ap.add_argument("--loop", action="store_true", help="keep going: a venture alert every ~3 minutes plus chatter")
    ap.add_argument("--fast", action="store_true", help="5x speed")
    a = ap.parse_args()
    if not os.path.isdir(a.dir):
        sys.exit("Can't find %s. Start the bridge once so it makes that folder, or pass --dir." % a.dir)
    path = os.path.join(a.dir, "feed-%s.log" % a.char)
    speed = 5.0 if a.fast else 1.0
    print("Writing to", path, "(Ctrl+C to stop)")
    try:
        for wait, ch, d, name, body in SESSION:
            time.sleep(wait / speed)
            emit(path, ch, d, name, body)
        n = 0
        while a.loop:
            n += 1
            for _ in range(random.randint(3, 5)):
                time.sleep(random.uniform(8, 25) / speed)
                ch, name, body = random.choice(CHATTER)
                emit(path, ch, "in", name, body)
            z = ZONES[n % len(ZONES)]
            time.sleep(10 / speed)
            time.sleep(1 / speed)
            emit(path, "venture", "in", "Populox", "Hmm... Whatever's stirring in these venture zones is about to reveal itself...")
            time.sleep(1 / speed)
            emit(path, "venture", "in", "Populox", z)
            time.sleep(150 / speed)
    except KeyboardInterrupt:
        print("\nStopped.")
    print("Done.")


if __name__ == "__main__":
    main()
