#!/usr/bin/env python3
"""
phonechatXI: build the addon zip from the repo. A build tool, not part of the addon.

    python3 tools/build_zip.py            writes dist/phonechatXI-v<version>.zip

The zip holds one folder, phonechat/, as the CatsEye launcher's Add New Addon installs it:
    phonechat/phonechat.lua, qrencode.lua, qrencode-LICENSE.md, LICENSE
    phonechat/bridge/  every file listed in bridge/manifest.txt, plus manifest.txt

Only files on that list go in, so nothing from a working folder can slip in (config.json, tells,
logs, settings). It refuses to build if the addon and bridge versions differ, if a listed file is
missing, or if any name on the list looks like a per-install or private file.
"""
import hashlib, os, re, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ADDON = os.path.join(ROOT, "addon", "phonechat")
BRIDGE = os.path.join(ROOT, "bridge")
NEVER = re.compile(r"(^|/)(config\.json|phone-settings\.json|status\.json|stop\.request|newlink\.request|"
                   r"game\.heartbeat|addon-settings\.txt|dir\.txt|tells/.*|.*\.log|.*\.exe|.*\.dll|.*\.pyc|"
                   r".*staff.*)$", re.I)


def fail(msg):
    sys.exit("build_zip: " + msg)


def version_of(path, pattern):
    with open(path, encoding="latin-1") as f:
        m = re.search(pattern, f.read(), re.M)
    return m.group(1) if m else None


def main():
    av = version_of(os.path.join(ADDON, "phonechat.lua"), r"^addon\.version\s*=\s*'([^']+)'")
    bv = version_of(os.path.join(BRIDGE, "bridge.py"), r'^VERSION = "([^"]+)"')
    if not av or av != bv:
        fail("addon version %r and bridge version %r must match" % (av, bv))
    files = [(os.path.join(ADDON, n), "phonechat/" + n) for n in ("phonechat.lua", "qrencode.lua", "qrencode-LICENSE.md")]
    files.append((os.path.join(ROOT, "LICENSE"), "phonechat/LICENSE"))
    with open(os.path.join(BRIDGE, "manifest.txt"), encoding="utf-8") as f:
        listed = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    for rel in listed + ["manifest.txt"]:
        if ".." in rel or rel.startswith("/") or "\\" in rel:
            fail("bad path in manifest.txt: " + rel)
        files.append((os.path.join(BRIDGE, rel), "phonechat/bridge/" + rel))
    for src, name in files:
        if NEVER.search(name):
            fail("refusing to ship " + name)
        if not os.path.isfile(src):
            fail("missing " + src)
    build = hashlib.sha256()
    for src, name in sorted(files, key=lambda x: x[1]):
        build.update(name.encode("utf-8") + b"\0")
        with open(src, "rb") as f:
            build.update(f.read())
    build_id = build.hexdigest()[:16]
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", "phonechatXI-v%s.zip" % av)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in sorted(files, key=lambda x: x[1]):
            if name == "phonechat/bridge/manifest.txt":
                z.writestr(name, "# build " + build_id + "\n" + "\n".join(listed) + "\n")
            else:
                z.write(src, name)
    with open(out, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print("wrote %s (%d files, %d bytes)" % (out, len(files), os.path.getsize(out)))
    print("build %s" % build_id)
    print("sha256 %s" % digest)
    for _, name in sorted(files, key=lambda x: x[1]):
        print("  " + name)


if __name__ == "__main__":
    main()
