# Changelog

Version numbers: **1.0.x** is fixes and looks only, and staff get an FYI. **1.x.0** changes what phonechatXI reads, sends or does, and goes back to staff for review first. Until staff sign off, a release is marked pre-release.

## 1.1.0 (October 2026, not reviewed yet)

1.0.1 was never released on its own, so it's folded in here (listed below). This version reads a few new kinds of lines and the addon can start the bridge itself, so it needs staff review before it's used in game.

**What it sends: unchanged.** Same fixed list as 1.0.0: `/l`, `/l2`, `/p`, `/t`, `/s`, `/sh`, stock emotes and the CatsEye `!` commands. One tap, one line, 130 characters max, one line per second. No automation.

**New things it reads**
- "X examines you" lines, shown with emotes.
- Other players' emotes (already allowed in 1.0.0; now caught on every chat mode they use).
- The ventures addon's progress line (`[ventures] Pool A ... is now 75% complete at (G-5)`). Only that one line. It shows in Alerts. phonechatXI doesn't replace the ventures addon or read its packets.
- Party Finder ads get their own channel (on by default), in the chat filters only. They don't show in Alerts.
- "Active Venture Seals" and "a venture is currently taking place" server lines, on the venture card.
- Bazaar visits ("X begins to browse your bazaar"). Off by default, shown in Alerts.
- The linkshell message of the day, pinned at the top of chat instead of mixed into Notices.

**Install and setup**
- One zip for everyone. Add it with the CatsEye launcher's Add New Addon. The bridge is inside it, and the addon copies it to the right place the first time it loads. Your phone link is kept on updates.
- The addon can start and stop the bridge: `/pchat start`, `/pchat stop`, or "Start with the game". Works on Steam Deck in Game Mode (through Proton) and on Windows.
- In-game window (`/pchat config`): bridge on/off, the QR code to scan, "New phone link", and settings. It opens by itself the first time.
- The Decky plugin is retired. The in-game window does everything it did. If you have it, uninstall it in Decky (that also stops its bridge). Its code stays in the repo under `decky/` as a fallback, but it isn't released.
- Desktop Mode: a "phonechatXI Bridge" launcher appears in your phonechat folder. Double-click it to run the bridge and open the QR page.
- `/phonechat` works as a command too.
- `/pchat debug` also logs lines printed by other addons (flagged), and the debug log starts over past 2 MB.
- Bridge log on Steam Deck: `~/phonechat/bridge.log`.

**Chat**
- Scrolling fixed. Starting to scroll up from the newest line no longer shakes or snaps back, and reading back no longer jumps when new lines arrive or you send.
- Your own lines get a faint background tint.
- Emoticon button next to the chat box opens a row of text emoticons (`^^`, `:D`, `<_<`, `T_T` and so on). Tapping one puts it in the box. You still hit send.
- Emoji turn into the game's text emoticons as you type (for example 👀 becomes `<_<`, 😀 becomes `:D`). You see the swap in the box before you send. Emoji were already dropped before sending, so this only changes what you see and what's left to send.
- Mentions: add words to watch in Settings. They save as you type (leaving the box by tapping Back used to lose them on iPhone). Matching lines are marked in chat and listed in Alerts with a badge.
- Item links only for real items (`{{Item}}` from the game's item auto-translate). Auto-translate phrases are styled but not linked.
- Clock: 12-hour (default) or 24-hour. AM/PM is set smaller so times stay on one line.
- Party Finder ads look like the game's: the poster's name stands out and the ad is in italics.
- New lines fade in (off with Reduce Motion).
- Removed "Group call bursts". `<call>` badges stay.
- Home Screen app fills the screen; no more dark band under the tab bar.
- Keyboard: the chat box now reliably sits above the iPhone keyboard.

**Layout**
- Bottom bar: Chat, Tells, Commands (Emotes and Server commands), Alerts (Ventures, Mentions, Bazaar, Notices).
- Alerts cards all share one layout: icon and bold label on the left, time on the right.
- Notices, venture cards and seals can be dismissed with an x (Notices also have Clear all). This only hides them on the phone, and it's remembered.
- Venture cards are labelled VNM · Active, then VNM · Expired about 10 minutes after the alert. The Active card shows a 10:00 countdown. Expired alerts shrink to one line, and pools at 100% drop off after the same 10 minutes. Pools under 100% stay until you dismiss them. Alerts shows only the latest VNM, a single "In progress" card for pools under 100% (the 100% pool lives on the VNM card, not twice), and the seals as one plain line.
- Text buttons (Save them, Got it, Show QR, Export, Import, Reset, Clear all) have a gold oval outline so they read as buttons.
- The Tells banner about saving tells can be dismissed.
- Settings gear on every tab. Tap the tab you're on to jump to the latest.

**Settings**
- Scrollback: keep 500, 1,000 or 2,000 lines on the bridge.
- Your phone settings are also saved on the bridge, so a new Home Screen shortcut or a second phone picks them up.
- Backup: Export and Import your settings as a file.
- Plainer wording throughout: banners, tips, empty states, Settings and About.
- Classic skin: the tap cursor is gold, so it shows up on light rows.
- Removed the star next to the command box. Star commands from the All commands list instead.

**From 1.0.1 (never released on its own)**
- Skins: Midnight (default), Classic (blue game-window look, rounded frames, gold title bar, a ▶ cursor when you tap) and Onyx (plain black).
- Fonts: Readable or Classic.
- Tap someone's name to start a tell. Tap a line to reply in that channel. Tap the channel icon to open just that channel. Nothing is sent until you hit send.
- Emote screen regrouped into tiles by mood, plus dances, chair poses and job emotes. Same emotes as before.
- New pearl icon and wordmark.
- Fonts and icons are served by the bridge. Nothing loads from Google Fonts.
- New phone link: make a new link and the old one, plus any open phone pages, stop working right away.

## 1.0.0 (October 2026)

First release. Reviewed by CatsEyeXI staff: T1, Sanctioned.
