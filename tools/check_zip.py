"""Validate release layout and generated build metadata without running the game."""
import pathlib, re, zipfile
root = pathlib.Path(__file__).resolve().parents[1]
archives = list((root / "dist").glob("*.zip"))
assert archives, "No release archive"
for archive in archives:
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        manifest = z.read("phonechat/bridge/manifest.txt").decode()
        assert re.fullmatch(r"# build [0-9a-f]{16}", manifest.splitlines()[0])
        listed = [x for x in manifest.splitlines() if x and not x.startswith("#")]
        expected = {"phonechat/" + x for x in ("phonechat.lua", "qrencode.lua", "qrencode-LICENSE.md", "LICENSE")}
        expected |= {"phonechat/bridge/" + x for x in listed + ["manifest.txt"]}
        assert set(z.namelist()) == expected
        for name in listed:
            assert z.read("phonechat/bridge/" + name) == (root / "bridge" / name).read_bytes()
        assert z.read("phonechat/phonechat.lua") == (root / "addon/phonechat/phonechat.lua").read_bytes()
    print("PASS:", archive.name, "integrity, exact manifest contents, source matches, build ID")
