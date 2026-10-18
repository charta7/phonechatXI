# Changelog

Versioning: a patch (like 1.1.1) is fixes and looks only, listed here. A minor version (like 1.2.0) changes what phonechatXI reads, sends or does, and goes to staff for review first. Until staff sign off, a release stays marked as a pre-release.

## 1.1.0 (October 2026, not reviewed yet)

Includes 1.0.1, which was never released on its own. This version reads new kinds of lines and the addon can start the bridge, so it needs staff review before it's used in game.

### Sends

Same fixed list as 1.0.0: `/l`, `/l2`, `/p`, `/t`, `/s`, `/sh`, stock emotes and the CatsEye `!` commands. One tap sends one line, 130 characters at most, one line per second. No automation.

Two checks are stricter:
- A chat line with a `;` followed by a command (like `hi ; /wave`) is blocked by the bridge and the addon.
- The bridge looks for a leading `/` or `!` after cleaning the text, so a hidden character can't get a command past it.

### Reads

- "X examines you" lines, shown with emotes.
- Other players' emotes on every chat mode they use. Emotes were already read in 1.0.0.
- The ventures addon's progress line (`[ventures] Pool A ... is now 75% complete at (G-5)`), and only that line. phonechatXI doesn't read the ventures addon's packets or replace it.
- Party Finder ads, as their own chat channel (on by default). Not shown in Alerts.
- The "Active Venture Seals" and "a venture is currently taking place" server lines.
- Bazaar visits ("X begins to browse your bazaar"). Off by default.
- The linkshell message of the day, pinned above chat instead of listed in Notices.

### Addon and setup

- One zip. Add it with the CatsEye launcher's Add New Addon. The bridge is inside it, and the addon copies it out the first time it starts it. Updates keep your phone link.
- The addon starts and stops the bridge: `/pchat start`, `/pchat stop`, or Start with the game. Tested on Steam Deck in Game Mode. Windows is untested.
- An in-game window (`/pchat`) with bridge on/off, the QR code, New phone link and settings. It opens by itself the first time. `/pchat help` prints the commands in chat.
- `/phonechat` works as a command.
- `/pchat debug` also logs lines printed by other addons, flagged as such. The debug log starts over past 2 MB.
- The bridge logs to `~/phonechat/bridge.log` on the Deck.
- Desktop Mode: a phonechatXI Bridge launcher in the phonechat folder starts the bridge and opens the QR page.
- Test tools in `tools/` (not in the addon zip): `fakefeed.py` plays a made-up session into the bridge, and `replay.py` plays a `/pchat debug` log back through the addon code with a fake Ashita that can't type or start programs.
- GitHub issue templates for bug reports and requests.
- The Decky plugin is retired. The in-game window replaces it. If you have it, uninstall it in Decky, which also stops its bridge. Its code is removed from the repo; it's still in the 1.0.0 history.

### Phone page

Chat
- Scrolling up from the newest line no longer shakes or snaps back, and the view no longer jumps when new lines arrive or you send.
- Your own lines have a faint tint.
- The colored bar on the left of each line always matches its channel. Calls, mentions and your own lines no longer change it.
- Party Finder lines in compact view no longer start with a stray `:`.
- An emoticon button next to the chat box opens a row of text emoticons (`^^`, `:D`, `;)`, `=)`, `<_<`, `T_T` and more). Tapping one adds it to the box. It doesn't send.
- Emoji turn into text emoticons as you type (👀 becomes `<_<`, 😀 becomes `:D`). Emoji were already stripped before sending, so this only changes what's left to send.
- Mentions save as you type. Before, leaving the box with Back on iPhone lost them.
- Mentions are for your name: up to 3 words, letters only, 2 to 15 characters each. Yell (trade spam) isn't checked.
- The keyboard no longer capitalizes the first letter or autocorrects, so game words like Jeuno or Windurst aren't changed. Both can be turned back on in Settings, Typing. The command box never autocorrects (before, it could).
- Only real items (`{{Item}}`) are linked. Auto-translate phrases are styled but not linked.
- Party Finder ads are styled like the game's: the poster's name stands out and the ad is in italics.
- 12-hour (default) or 24-hour clock.
- New lines fade in, unless Reduce Motion is on.
- Removed the "Group call bursts" option. `<call>` badges stay.
- The Home Screen app fills the screen, with no dark band under the tab bar.
- The chat box stays above the iPhone keyboard.

Alerts
- Tabs are Chat, Tells, Emotes, Server (CatsEye `!` commands) and Alerts (ventures, mentions, bazaar, notices). Emotes and the `!` commands each have their own tab instead of sharing one called Commands.
- The Server tab opens on the full `!` command list: one line each, a search box, a star to keep one at the bottom, and CONFIRM on the ones that change something. Tapping a command asks before it sends. Commands that need more after them, like `!box`, go in the box instead so you can finish typing. Replies show in a small area under the list.
- Game modes: a command that only works in some of ACE, CW or WEW shows those modes' icons, and a filter (All, ACE, CW, WEW) under the search box shows only what works for your mode. The filter is remembered. It only tidies the list: favorites always show, and any command can still be typed and sent. The mode list lives in `commands.json` ("as of October 2026") and only labels and filters; it doesn't change what can be sent.
- Emotes use a text `^_^` icon everywhere (tab, chat lines, picker) instead of a smiley.
- The VNM alert shows as VNM · Active with a 10 minute countdown, then VNM · Expired on one line. Only the latest VNM is shown.
- Pools under 100% are listed on one In progress card. A pool at 100% shows on the VNM card instead, and drops off with it after 10 minutes.
- Active seals show as one line.
- If a venture line is worded differently than expected, it still shows in Alerts as plain text instead of disappearing.
- Venture cards, seals and notices can be cleared with ×. Notices also have Clear all. Clearing only hides them on the phone, and it's remembered.

Look and settings
- Text buttons (Save them, Got it, Show QR, Export, Import, Reset, Clear all) have an outline so they read as buttons.
- The Tells banner about saving tells can be dismissed.
- A settings gear on every tab. Tapping the current tab jumps to the newest line.
- Scrollback: the bridge keeps 500, 1,000 or 2,000 lines.
- Phone settings are also saved on the bridge, so a new Home Screen shortcut or a second phone picks them up. Export and Import back them up to a file.
- Plainer wording in banners, tips, empty screens, Settings and About.
- Copy debug info in Settings: versions, connection, settings and recent errors for a bug report. It leaves out the phone link, watch words and all chat.
- Classic skin: the tap cursor is gold so it shows on light rows.
- Removed the star next to the command box and the separate All commands screen. Star commands right in the Server tab's list.

### From 1.0.1

- Skins: Midnight (default), Classic (the blue game-window look, with a gold title bar and a ▶ cursor) and Onyx (plain black).
- Fonts: Readable or Classic.
- Tap a name to start a tell, a line to reply on its channel, or a channel icon to open that channel. Nothing sends until you press send.
- Emotes grouped into tiles by mood, plus dances, chair poses and job emotes. Same emotes as before.
- New pearl icon and wordmark.
- Fonts and icons are served by the bridge. Nothing loads from Google Fonts.
- New phone link: making one stops the old link and any open phone pages right away.

## 1.0.0 (October 2026)

First release. Reviewed by CatsEyeXI staff: T1, Sanctioned.
