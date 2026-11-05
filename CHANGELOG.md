# Changelog

Versioning: a patch (like 1.1.1) is fixes and looks only, listed here. A minor version (like 1.2.0) changes what phonechatXI reads, sends or does, and goes to staff for review first. Until staff sign off, a release stays marked as a pre-release.

## 1.1.0 (not reviewed yet)

Includes 1.0.1, which was never released on its own. It reads new kinds of lines and the addon can start the bridge, so it needs staff review before it's used in game.

### Sends

Same list as 1.0.0: `/l`, `/l2`, `/p`, `/t`, `/s`, `/sh`, stock emotes and the CatsEye `!` commands. One tap sends one line, one line per second at most, no automation. A line is at most 130 bytes including the `/l ` or `/t Name ` part (about 127 letters on a linkshell).

Stricter, in both the bridge and the addon:
- Blocked: a `;` followed by a command (`hi ; /wave`), target tokens like `<st>` (`<t>`, `<me>` and `<call>` still work), and full-width lookalikes of `/`, `!`, `;` and `<st>`.
- Blocked: text the game's chat box can't type, like raw auto-translate bytes.
- The addon checks `!` commands against the same list as the bridge, and refuses a message starting with a space.
- A lone `/` (a wave) and `!`, `!!` or `!?` (reactions) are allowed. Anything else starting with `/` or `!` still isn't. Say lines like these from others now show on the phone too (only `!` followed by a letter is treated as a server command).
- A line that shows up twice is typed once.
- Sending pauses while two of your characters are logged in, so a line can't come from the wrong one.

Send status on the phone:
- "Failed" only when the game says so (an offline tell, a party line with no party). If you'd sent tells to two people, it says one of them failed instead of guessing which.
- "Didn't confirm" has no Retry button, so nothing gets sent twice by accident.

### Reads

New:
- "X examines you" (mode 208) and other players' emotes (mode 15), shown with emotes.
- Your own shouts (mode 2), so a shout sent from the phone shows as sent.
- Replies to a `!` command sent from the phone: the non-chat lines in mode 9 for 10 seconds after it's typed. Shown only in the Server tab.
- Party Finder ads, as their own channel.
- Bazaar visits ("X begins to browse your bazaar"). Shown only if you turn it on.
- The linkshell message of the day, pinned above that linkshell's chat.

No longer read: lines mentioning "venture" in the plain system modes. Server messages about ventures now show as ordinary server notices; the Ventures card only shows Populox's VNM alert.

### Addon and setup

- One zip for everyone, installed with the launcher's Add New Addon. The addon copies the bridge into place and starts it (`/pchat start`, `/pchat stop`, or Start with the game). Updates keep your phone link.
- Tested on Steam Deck, and on Windows 11 with Ashita and VanaCore's beta.
- `/pchat` opens a window with the bridge's status, the QR code, New phone link and settings. `/pchat help` lists the commands. `/phonechat` works too.
- The bridge window says what it is (a local relay over your home Wi-Fi), shows your link, and notes when the game or a phone connects.
- The bridge closes itself about 100 seconds after the game is gone (it says so first, and cancels if the game comes back). The addon touches a small local file every 2 seconds for this.
- `/pchat debug` also logs lines other addons print (never sent to the phone). The debug log tops out at 2 MB and never holds your phone link; neither does the Deck's `bridge.log`.
- The bridge only answers requests addressed to this computer, which stops a web page from reaching it through a borrowed address.
- Desktop Mode launcher on the Deck. Test tools and a zip builder in `tools/` (not in the addon zip). GitHub issue templates.
- The Decky plugin is retired; the in-game window replaces it.

### Phone page

Chat
- Scrolling up from the newest line no longer shakes or snaps back, and the view no longer jumps when new lines arrive or you send.
- Your own lines have a faint tint.
- The colored bar on the left of each line always matches its channel. Calls, mentions and your own lines no longer change it.
- Party Finder lines in compact view no longer start with a stray `:`.
- An emoticon button next to the chat box opens a row of text emoticons (`^^`, `:D`, `;)`, `=)`, `<_<`, `T_T` and more). Tapping one adds it to the box. It doesn't send.
- Emoji turn into text emoticons as you type (👀 becomes `<_<`, 😀 becomes `:D`). Emoji were already stripped before sending, so this only changes what's left to send.
- Mentions save as you type. Before, leaving the box with Back on iPhone lost them.
- Mentions are for your name: up to 3 words, letters only, 2 to 15 characters each. Yell (trade spam) and emotes aren't checked, so "X waves to you" doesn't count as a mention. Your name is still highlighted in those lines.
- The keyboard no longer capitalizes the first letter or autocorrects, so game words like Jeuno or Windurst aren't changed. Both can be turned back on in Settings, Typing. The command box never autocorrects (before, it could).
- Only real items (`{{Item}}`) are linked. Auto-translate phrases are styled but not linked. Web addresses in chat are plain text, not links, so the only outside page the phone opens is a BG-Wiki item search.
- Party Finder ads are styled like the game's: the poster's name stands out and the ad is in italics.
- 12-hour (default) or 24-hour clock.
- New lines fade in, unless Reduce Motion is on.
- Removed the "Group call bursts" option. `<call>` badges stay.
- The Home Screen app fills the screen, with no dark band under the tab bar.
- The chat box stays above the iPhone keyboard.

Alerts
- Tabs are Chat, Tells, Emotes, Server (CatsEye `!` commands) and Alerts (VNM, mentions, bazaar, notices). Emotes and the `!` commands each have their own tab instead of sharing one called Commands.
- The Server tab opens on the full `!` command list: one line each, a search box, a star to keep one at the bottom, and CONFIRM on the ones that change something. Tapping a command asks before it sends, from the list or from your starred row. Commands that need more after them, like `!box`, go in the box instead so you can finish typing. Replies show in a small area under the list.
- Game modes: a command that only works in some of ACE, CW or WEW shows those modes' icons, and a filter (All, ACE, CW, WEW) under the search box shows only what works for your mode. The filter is remembered. It only tidies the list: favorites always show, and any command can still be typed and sent. The mode list lives in `commands.json` ("as of October 2026") and only labels and filters; it doesn't change what can be sent.
- Emotes use a `/bow` tag as their icon everywhere (tab, chat lines, picker) instead of a smiley, so it's clear that's where the slash emotes are and it doesn't look like the `:)` emoticon button.
- Ventures shows only Populox's VNM alert: VNM · Active with a 10 minute countdown, then VNM · Expired on one line. Only the latest VNM is shown.
- If Populox's line is worded differently than expected, it still shows in Alerts as plain text instead of disappearing.
- The VNM card and notices can be cleared with ×. Notices also have Clear all. Clearing only hides them on the phone, and it's remembered.

Look and settings
- Text buttons (Save them, Got it, Show QR, Export, Import, Reset, Clear all) have an outline so they read as buttons.
- The Tells banner about saving tells can be dismissed.
- A settings gear on every tab. Tapping the current tab jumps to the newest line.
- Scrollback: the bridge keeps 500, 1,000 or 2,000 lines.
- Phone settings are also saved on the bridge, so a new Home Screen shortcut or a second phone picks them up. Export and Import back them up to a file. Your mention names, tell history and last tell target stay on the phone: they're never sent to the bridge or exported, and the bridge removes them from an older settings file when it starts.
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
