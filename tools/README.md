# Test tools

These are for testing phonechatXI without the game. They aren't part of the addon zip, and they never touch the game.

Close the game first, then start the bridge by itself (the phonechatXI Bridge launcher in `~/phonechat/`, or `start.sh`). Open the phone page as usual and run one of these.

## fakefeed.py

Plays a short made-up session into the bridge: linkshell chat, tells, emotes, a Party Finder ad, a Populox VNM alert with the ventures addon's lines, seals, Apururu and a bazaar visit. The lines are already in the format the addon writes, so this tests the bridge and the phone page.

```
python3 fakefeed.py            one session
python3 fakefeed.py --loop     keeps going, with a VNM alert every few minutes
python3 fakefeed.py --fast     5x speed
```

## replay.py

Plays a `/pchat debug` log back through the real addon code, with a fake Ashita around it. The lines go through the same parsing as in game, so this tests the addon too, using real CatsEye text. The fake Ashita can't type, start programs or reach the network.

```
pip install lupa
python3 replay.py ~/phonechat/debug-Charta.log
python3 replay.py sample-debug-Charta.log --instant
```

`--fast` plays at 5x, and `--instant` doesn't wait between lines. Without the game, auto-translate isn't expanded, so items show as `[item]`.

To get a log, turn on `/pchat debug` on an approved version, play normally, then turn it off. Debug logs hold other players' chat, so don't share them publicly. `sample-debug-Charta.log` is a made-up one in the same format.

Both tools need Python 3.7 or newer. Pass `--dir` if the bridge's folder isn't `~/phonechat`.
