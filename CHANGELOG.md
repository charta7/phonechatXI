# Changelog

Versioning: a patch (like 1.1.1) is fixes and looks only, listed here. A minor version (like 1.2.0) changes what phonechatXI reads, sends or does, and goes to staff for review first; it isn't released until they sign off.

## 1.1.1 (November 2026)

- Chat, channel, and tell composers use a full-width draft above compact target/emoticon/send controls. Chat header is slimmer and saved view tabs fit their labels.

- Unsent drafts stay in the open page across navigation, composer rebuilds, and reconnects, separated by composer/channel/tell recipient. Reloading or closing the page clears them; they are never sent automatically or included in settings backups.
- Build ID is visible in Settings. Keyboard focus indicators, composer labels, reduced-motion support, and readable optional channel text colors improve accessibility without enlarging view/channel controls.
- Neutral message text is again the default for new settings; explicit existing preferences remain unchanged.

- Link replacement now explains re-scanning and rebuilding Home Screen shortcuts on the Deck, phone, and local setup page. Authentication and capture scope are unchanged.

- Quick filter row visibility is now a saved option inside Edit view, removing the separate Filters button. Channel-colored message text defaults on for new settings; existing choices are preserved. LS2 defaults to #06ED00. Shortened Yell and saved-tell descriptions.

- HVNM cards recognize the existing Populox announcements, with the same countdown and warning rules as VNM. VNM and HVNM timers stay separate. This only interprets text already delivered to the phone; no additional game data is captured.
- Native channel color pickers survive live updates. Default LS2 is a deeper green; existing custom colors are preserved. Optional channel-colored message text is available in Settings.
- Channel filters collapse behind a Filters button. Jump to latest sits below the feed instead of covering messages. Device safe-area padding is retained.
- MOTDs survive intervening server notices, and changing the end of a dismissed MOTD makes it visible again.
- A successful chat send preserves a draft edited while the request was pending.

Fixes only. It reads the same lines as 1.1.0, except one that it now reads less of (the first fix below), and how LS1's message of the day is sorted changed.

- Game messages that aren't chat no longer show up as a line in your chat. The auction house's "You can only place a single item or a set of 12 such items on auction." was one. Only the two failure lines the phone uses (a tell that wasn't received, and "There are no party members.") come through now.
- The VNM countdown starts at Populox's first message ("Something is interrupting ventures in these zones...") and runs 10 minutes. The 5 minute warning ("Whatever's stirring... is about to reveal itself...") no longer restarts it. When it reaches zero the card shows POP! for a minute, then it's over. Each VNM gets its own card, so two or three running at once all show. If only the warning is seen (say you were zoning), the countdown counts back from it, about 4:50 left.
- The LS1 message of the day now shows in full. LS1's comes in as a server message, and 1.1.0 pinned its first line ("LS name: set by") instead, with the message itself under server notices.
- The pinned message of the day has an × to hide it. A linkshell with no message of the day prints nothing when you switch to it, so the old one stayed up. A hidden one stays hidden until it changes.
- When a linkshell's message of the day comes in, its old one is cleared first.
- The name field in Settings shows a made-up example (faded, in italics) instead of a real name, so it no longer looks already filled in.
- The Party Finder filter is now "PF", with a "looking for members" icon instead of a magnifying glass.
- About in Settings is shorter and up to date.
- The QR code in Settings stays black on white even if your browser has a night mode, so it can be scanned.
- The message box grows as you type, up to 4 lines, then scrolls inside itself, so a long line is readable while you write it. Return still sends. A line break you paste in becomes a space.
- The hint in the message box ("Message LS2") is in faded italics, so it doesn't look like typed text.
- The :) emoticons are yours to set in Settings ("Your emoticons", separated by commas, up to 20). The field starts with the defaults (^^, ^_^, :), ;), :D, :P, XD and <3), so you can add to them, and "Reset to defaults" brings them back. They open as a grid that grows to fit, with a red × to close.
- An emoji with no text swap gets a hint above the box ("🤔" not valid, won't appear in game), instead of quietly disappearing from the line.
- The `/pchat debug` log keeps the previous 2 MB as `debug-<Name>.old.log` when it fills up, instead of starting over, so the lines just before a problem aren't lost.
- A settings change made just before closing the page is no longer lost. The phone's newer copy now wins over an older one on the bridge.
- A failed tell or party line no longer shows the game's error twice. It's on the failed line only, not repeated as its own chat line.

## 1.1.0 (November 2026)

Reviewed and approved by CatsEyeXI staff. Includes 1.0.1, which was never released on its own.

### Sends

Same list as 1.0.0: `/l`, `/l2`, `/p`, `/t`, `/s`, `/sh`, stock emotes and the CatsEye `!` commands. One tap sends one line, one line per second at most, no automation. A line is at most 130 bytes including the `/l ` or `/t Name ` part (about 127 letters on a linkshell).

Stricter, in both the bridge and the addon:
- Blocked: a `;` followed by a command (`hi ; /wave`), target tokens like `<st>` (`<t>`, `<me>` and calls like `<call14>` still work), and full-width lookalikes are checked like the plain characters, so `！points` is blocked like `!points`.
- Blocked: text the game's chat box can't type, like raw auto-translate bytes.
- The addon checks `!` commands against the same list as the bridge, and refuses a message starting with a space.
- A lone `/` (a wave) and `!`, `!!` or `!?` (reactions) are allowed. Anything else starting with `/` or `!` still isn't.
- A line that shows up twice is typed once.
- Sending pauses while two of your characters are logged in, so a line can't come from the wrong one.

Send status on the phone:
- "Failed" only when the game says so (an offline tell, a party line with no party). If you'd sent tells to two people, it says one of them failed instead of guessing which.
- "Didn't confirm" has no Retry button, so nothing gets sent twice by accident.

### Reads

New:
- "X examines you" (mode 208) and other players' emotes (mode 15), shown with emotes.
- Your own shouts (mode 2, the retail mode; not yet confirmed on CatsEye), so a shout sent from the phone shows as sent. If CatsEye uses another mode, the shout just shows "didn't confirm".
- Replies to a `!` command sent from the phone: the non-chat lines in mode 9 for 10 seconds after it's typed. Shown only in the Server tab.
- Party Finder ads, as their own channel.
- Bazaar visits ("X begins to browse your bazaar"). Shown only if you turn it on.
- The linkshell message of the day, pinned above that linkshell's chat.
- Say lines that are just `!`, `!!` or `!?`. 1.0.0 hid every say line starting with `!` as a server command; now only `!` followed by a letter is hidden.

Ventures: 1.0.0 sent any line mentioning "venture" in mode 9 or the plain system modes to Ventures. 1.1.0 doesn't read those lines. Server messages about ventures show as ordinary server notices, and the Ventures card only shows Populox's VNM alert.

### Addon and setup

- One zip for everyone, installed with the launcher's Add New Addon. The addon copies the bridge into place and starts it (`/pchat start`, `/pchat stop`, or Start with the game). Updates keep your phone link.
- 1.0.0 runs in game on the Steam Deck and on Windows 11 (Ashita, and VanaCore's beta). 1.1.0 was tested offline before review.
- `/pchat` opens a window with the bridge's status, the QR code, New phone link and settings. `/pchat help` lists the commands. `/phonechat` works too.
- The bridge window says what it is (a local relay over your home Wi-Fi), shows your link, and notes when the game or a phone connects.
- The bridge closes itself about 100 seconds after the game is gone. It says so first, in its window and on the phone, and cancels if the game comes back. The addon writes a small local file every 2 seconds for this.
- `/pchat debug` also logs lines other addons print (never sent to the phone). The debug log tops out at 2 MB and never holds your phone link; neither does the Deck's `bridge.log`.
- The bridge ignores requests sent to it under any other web address, so a website you visit can't use your browser to reach it.
- Settings files are checked before use. The addon only puts a folder path made of plain path characters into the command that starts the bridge, and ignores a `dir.txt` that has anything else. The phone checks every value in a saved or imported settings file and falls back to the default for anything unexpected.
- Desktop Mode launcher on the Deck. Test tools and a zip builder in `tools/` (not in the addon zip). GitHub issue templates.
- The Decky plugin is retired; the in-game window replaces it.

### Phone page

- Tabs: Chat, Tells, Emotes, Server and Alerts. Emotes and the `!` commands each get their own tab (they used to share one called Commands).
- Server tab: the full `!` command list with search and stars. Tapping a command asks before it sends, from the list or your starred row. Commands that need more after them, like `!box`, go in the box so you can finish typing. Replies show under the list. The star next to the command box and the separate All commands screen are gone.
- Game modes: icons show which of ACE, CW or WEW a command works in, and an All/ACE/CW/WEW filter tidies the list. It only filters: favorites always show, and any command can still be typed and sent. The mode list lives in `commands.json` and doesn't change what can be sent.
- Ventures shows only Populox's VNM alert (Active with a 10 minute countdown, then Expired). If his line is worded differently, it still shows as plain text. The VNM card and notices can be cleared with ×, which only hides them on the phone.
- Chat scrolling no longer jumps or snaps back. The colored bar always matches the channel, and your own lines have a faint tint.
- Mentions are for your name (up to 3 words) and skip yell and emotes. They save as you type.
- An emoticon row next to the chat box, and emoji turn into text emoticons as you type. Neither sends anything by itself.
- The keyboard no longer capitalizes or autocorrects (both can be turned back on in Settings, Typing). The command box never autocorrects.
- Only real items link out (to a BG-Wiki search). Web addresses in chat are plain text.
- Party Finder ads styled like the game's. 12 or 24-hour clock. Scrollback of 500, 1,000 or 2,000 lines. "Group call bursts" removed.
- Phone settings are also saved on the bridge, with Export and Import. Your mention names, which tells you've read, your last tell target and the notices you cleared stay on the phone: never sent to the bridge or exported, and the bridge removes them from an older settings file when it starts.
- Copy debug info in Settings for bug reports, without the phone link, watch words or any chat.
- Smaller fixes: iPhone keyboard and Home Screen layout, outlined text buttons, a settings gear on every tab, a dismissable Tells banner, a gold cursor in the Classic skin, plainer wording throughout.

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
