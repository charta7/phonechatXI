<p align="center"><img src="docs/header.png" alt="phonechatXI" width="640"></p>

> [!NOTE]
> **v1.0.0 was reviewed by CatsEyeXI staff: T1, Sanctioned** (October 2026).
> From the review: *"If the addon gets any major changes (new features, automation, or anything that changes what it sends or reads), please resubmit it for review before using the updated version."*
>
> **v1.1.0 is waiting on staff review.** It reads a few new kinds of lines and the addon can start the bridge itself. What it sends hasn't changed. Don't use it in game until it's marked as a full release. See the [changelog](CHANGELOG.md).

# phonechatXI

**Your phone as a second chat window for FFXI on CatsEyeXI.**

FFXI's chat is hard to read and type in with a controller, especially on a Steam Deck. phonechatXI puts your chat on your phone, so you can read LS, party, tells and the rest, and reply with a real keyboard, while you keep playing on the main screen. It's meant to be used alongside the game, on the same Wi-Fi network.

**The pieces:**
- **Addon** (`phonechat`): runs inside the game through Ashita. Reads chat, types the lines you send, and starts the bridge.
- **Bridge:** a small program on the same computer as the game. It serves the phone page on your Wi-Fi. It ships inside the addon zip.
- **Phone page:** what you open on your phone. Add it to your Home Screen and it works like an app.

<p>
  <img src="docs/screenshots/chat.png" width="220" alt="Chat feed with linkshell, party, tells, say and shout">
  <img src="docs/screenshots/tell-thread.png" width="220" alt="A tell thread">
  <img src="docs/screenshots/emotes.png" width="220" alt="Emote picker">
</p>

## What it does

- **One feed for all your chat:** LS1, LS2, party, tells, say, shout, unity, yell, emotes and Party Finder, color-coded like the game. Linkshells get linkpearl icons.
- **Your own views,** like the game's chat windows. "All", "Linkshells" and "Party & tells" come built in, and you can make your own.
- **Tells get their own tab,** with a thread per person.
- **Tap to reply.** Tap a name to start a tell. Tap a line to reply in that channel. Tap the channel icon to open just that channel. Nothing sends until you hit send.
- **Item links.** Items you link in game (`{{Suppanomimi}}`) open a BG-Wiki search on your phone.
- **Mentions.** Pick words to watch, like your name. Matches are marked in chat and listed in Alerts.
- **LS message of the day** pinned at the top of chat.
- **Commands tab:** every stock emote grouped by mood, plus dances, chair poses and job emotes, and CatsEye server commands like `!points` and `!dailies`. Commands that change something ask first.
- **Alerts tab:** the VNM card from Populox (Active with a 10 minute countdown, then Expired), the ventures addon's progress lines, active venture seals, mentions, bazaar visits (off by default) and server notices. Tap × to clear any of them. Party Finder ads stay in the chat filters, not here.
- **Looks:** Midnight, Classic (the blue game-window look) or Onyx skins, Readable or Classic font, comfortable or compact, text size, 12 or 24-hour clock, and a color per channel.
- **Settings follow you.** They're saved on the bridge too, and you can export them to a file.

<p>
  <img src="docs/screenshots/skin-midnight.png" width="180" alt="Midnight skin">
  <img src="docs/screenshots/skin-classic.png" width="180" alt="Classic skin">
  <img src="docs/screenshots/skin-onyx.png" width="180" alt="Onyx skin">
</p>

<p>
  <img src="docs/screenshots/chat-compact.png" width="180" alt="Compact layout">
  <img src="docs/screenshots/send-to.png" width="180" alt="Choosing where to send">
  <img src="docs/screenshots/emote-action.png" width="180" alt="Emotes view showing only emote lines">
  <img src="docs/screenshots/ventures.png" width="180" alt="VNM alert with countdown, ventures addon and seals">
</p>

## What it will never do

- **No automation.** Every message, emote or command is one tap from you. No auto replies, nothing that reacts to chat, no timers, repeats or macros. Mentions only mark lines on your phone; they never send anything.
- **No game actions.** `/ma`, `/ja`, `/ws`, `/item`, `/attack`, `/follow`, targeting and movement are all blocked.
- **No yell.**
- **No flooding.** One tap sends one line, and each line has to fit the normal 130 character chat limit. Messages are never split into several sends. At most one line per second.
- **No combat log.** Battle messages are never captured.
- **Not a ventures replacement.** It shows the ventures addon's one progress line. Use the ventures addon for everything else.
- **Nothing leaves your home network.** No cloud, no outside server. Fonts and icons are served by the bridge. The only outside page is BG-Wiki, and only when you tap an item link.

Everything it's allowed to send is on a fixed list, checked twice: once by the bridge and again by the addon right before it types the line. If you want to check the list yourself, it's `allowed()` in [`addon/phonechat/phonechat.lua`](addon/phonechat/phonechat.lua) and [`bridge/commands.json`](bridge/commands.json).

<p>
  <img src="docs/screenshots/settings.png" width="220" alt="Settings showing fixed commands and no automation">
  <img src="docs/screenshots/command-confirm.png" width="220" alt="Confirm step before an action command">
</p>

## Scope

What staff reviewed in v1.0.0, and what v1.1.0 adds. Anything past this needs a new review first.

- **Reads (1.0.0):** LS1, LS2, party, tells, say, shout, unity, yell, emotes, venture alerts, server notices and failed-tell messages. Never combat.
- **Reads (new in 1.1.0, under review):** "X examines you", the ventures addon's progress line, Party Finder ads, the Active Venture Seals line, bazaar visits (off by default), and the LS message of the day.
- **Sends (unchanged):** `/l`, `/l2`, `/p`, `/t`, `/s`, `/sh`, the stock emotes, and the CatsEye `!` server commands in `bridge/commands.json`. One tap, one line, 130 characters max, one line per second.
- **Does (new in 1.1.0, under review):** the addon starts and stops the bridge program when you ask, and shows the QR code in an in-game window.
- **Never:** automation of any kind, game actions, `/yell`, or splitting a message into several sends.

## How it works

```
game  ->  addon  ->  feed file  ->  bridge  ->  your phone
phone ->  bridge ->  outbox file ->  addon  ->  chat  (one line per tap)
```

- **Addon** ([`addon/phonechat`](addon/phonechat), Ashita v4): reads chat and writes it to a file. When you send from your phone, it types that one line through Ashita's normal command queue, same as typing it yourself. No packet injection. It also starts the bridge when you ask (`/pchat start` or "Start with the game").
- **Bridge** ([`bridge/`](bridge), Python 3.7+, no extra packages): serves the phone page on your home Wi-Fi.

The bridge lives in a folder outside the addon (`~/phonechat/` on the Deck, `<Ashita>\config\addons\phonechat\` on Windows). On the Deck it runs as a Linux program, so it can't run from inside the game's folders. And keeping it outside means addon updates never wipe your phone link.

## Install

Grab `phonechatXI-v1.1.0.zip` from [Releases](../../releases). A full release has been reviewed by CatsEye staff (or they were told about it, for small fixes). A pre-release is waiting on that, so hold off using it in game.

### Steam Deck

1. **Add the addon:** in the CatsEye launcher, use **Add New Addon** and pick the zip. Turn it on in the launcher's addon list.
2. **Start the game.** The phonechatXI window opens the first time. Click **Start**, and tick **Start with the game** if you want it every time.
3. **Scan the QR** with your phone's camera and open the link. In Safari, tap Share, then **Add to Home Screen**.

That's it. When you start the bridge, the addon copies it to `/home/deck/phonechat/` first.

**Had the Decky plugin?** Uninstall it in Decky. That also stops its bridge. Keep the `~/phonechat` folder; it holds your link.

**Desktop Mode:** after the first run there's a **phonechatXI Bridge** launcher in `/home/deck/phonechat/`. Double-click it to start the bridge and open the QR page.

### Windows (not tested, not supported yet)

phonechatXI is built and tested for Steam Deck. Windows is untested and isn't part of this build yet. The steps below were written but never run, so treat them as a rough guide.

1. Install Python 3 from [python.org](https://www.python.org/downloads/). Tick **Add python.exe to PATH**.
2. Add the addon zip with the CatsEye launcher's **Add New Addon**, and turn it on.
3. In game, `/pchat config` and click **Start**. A small bridge window opens; leave it open. If Windows asks about the firewall, allow **Private networks**.
4. Scan the QR in the phonechatXI window.

The bridge goes in `<Ashita>\config\addons\phonechat\bridge\`.

### Updating

- Add the new zip with the launcher the same way.
- If the bridge is already running, the addon tells you an update is ready. `/pchat stop`, then `/pchat start` (or Stop and Start in the window). Your phone link is kept.
- The phone page updates by itself. Your settings stay.
- To get a new Home Screen icon, delete the old shortcut and add it again.

### Uninstall

1. `/pchat stop`, then remove the addon in the CatsEye launcher.
2. Delete `/home/deck/phonechat/` on the Deck, or `<Ashita>\config\addons\phonechat\` on Windows.
3. Delete the shortcut from your phone's Home Screen.

## In game

| Command | What it does |
|---|---|
| `/pchat` | Bridge status, your phone link, and the list of options |
| `/pchat config` | The phonechatXI window: start/stop, QR code, new phone link, settings |
| `/pchat start` / `stop` | Start or stop the bridge |
| `/pchat url` | Print the phone link |
| `/pchat newlink` | Make a new phone link. The old one stops working. |
| `/pchat debug` | Log every chat line with its mode number, for troubleshooting |

`/pcxi` and `/phonechat` work too.

## Good to know

- **No notifications.** iPhone won't buzz for tells. Web pages on your home network can't send push notifications.
- **It pauses in the background.** When the phone locks or you switch apps, Safari pauses the page. It catches up when you come back, as long as the bridge kept running.
- **The screen will sleep.** Turn up Auto-Lock in iPhone Settings if you want it to stay on.
- **Address changes.** Your router can give the Deck a new address, which breaks the saved link. Scan the QR again, or set a fixed address for the Deck in your router (often called a DHCP reservation).
- **Home Wi-Fi only.** Don't run the bridge on public or hotel Wi-Fi. Anyone there with your link could read and send.

## Troubleshooting

| Problem | Try this |
|---|---|
| Phone can't connect | Same Wi-Fi as the Deck/PC? Is the bridge on (`/pchat`)? The address may have changed: scan the QR again. On Windows, allow Python through the firewall on private networks. |
| Bridge won't start (Deck) | Check `/home/deck/phonechat/bridge.log`. The error also shows in the phonechatXI window. |
| Bridge won't start (Windows) | The bridge window says why. Usually Python isn't installed or wasn't added to PATH. |
| "Port in use" | Another bridge is running, often an old Decky one. Uninstall the Decky plugin, or `/pchat stop` and start again. |
| Bridge is on but no chat shows | Make sure the addon is on in the launcher. `/pchat debug` logs every line it sees. |
| A message says "unconfirmed" | The game didn't echo it back within a few seconds. Check the game before sending again. |
| A message says "failed" | The game rejected it, usually a tell to someone offline. |
| Someone else saw your link or QR | **New phone link** in the phonechatXI window (or `/pchat newlink`). The old link stops working right away. Scan the new QR. |
| Page says "This link was replaced" | A new link was made. Scan the new QR and delete the old shortcut. |

## Privacy

- Chat lives in the bridge's memory and is gone when it stops. The chat file it reads from is cleared every time the bridge starts and every time the addon loads.
- Only tells can be saved, and only if you turn on "Remember tells". That keeps the last 50 lines per person, and "Clear saved tells" deletes them. Linkshell and party chat are never saved.
- Your phone settings (views, colors, watch words) are saved on the bridge in `phone-settings.json`. No chat is in that file.
- Anyone on your Wi-Fi with your link can read and send, so keep your link to yourself. If it gets out, make a new one (see Troubleshooting).

## Credits

- Built with help from Claude.
- `bridge/qrcode.js` is [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase (MIT).
- The in-game QR code uses [luaqrcode](https://github.com/speedata/luaqrcode) by speedata (BSD-3), in `addon/phonechat/qrencode.lua`.
- The retired Decky plugin (`decky/`) started from the Decky plugin template (BSD-3).
- Fonts: Cinzel, Atkinson Hyperlegible, JetBrains Mono and Cormorant SC (logo), all SIL Open Font License. License files are in `bridge/fonts/`.
- Server command list from the [CatsEyeXI Commands](https://www.bg-wiki.com/ffxi/CatsEyeXI_Commands) page on BG-Wiki.
