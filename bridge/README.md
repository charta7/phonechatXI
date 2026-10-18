# phonechatXI bridge

This folder is the bridge: a small Python program (3.7 or newer, no extra packages) that serves the phone page on your home Wi-Fi.

You don't need to touch it. The phonechat addon copies it here and starts it for you: `/pchat` in game, then **Start**.

- `start.sh`: starts the bridge on Steam Deck or Linux. Its log goes to `../bridge.log`.
- `start-bridge.bat`: starts the bridge on Windows.
- `config.json`: your phone link and settings. Keep it. Delete it only if you want a brand new link and port.
- `commands.json`: the fixed list of CatsEye `!` commands the phone can send.

Running it by hand: `./start.sh --open` (or `python3 bridge.py --open`) starts it and opens the setup page with the QR. Add `--port 8780` if 8765 is taken.

Full instructions: the README in the phonechatXI repo.
