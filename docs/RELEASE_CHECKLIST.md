# Release verification

Record the ZIP build identifier from Settings → Copy debug info with each result.

## Capture boundary
- Review any diff touching addon chat modes, injected-line handling, packet handlers, command allowlists, or bridge input handling explicitly before release.
- Run `node tools/test_qc.js`, `python tools/test_qc.py`, `python tools/build_zip.py`, and `python tools/check_zip.py`.
- Passing fixtures guard known exclusions; they do not prove every possible game line is excluded. No broader capture should be added as a debugging shortcut.

## Device trial
Record device, OS, browser, browser/Home Screen mode, build, and pass/fail.
- iPhone Safari and Home Screen; Android Chrome; narrow screen and landscape.
- Keyboard opens/closes; composer and navigation remain accessible; safe-area padding is retained.
- Color picker remains open while messages arrive and while choosing multiple colors.
- Filters, jump-to-latest, channel text colors, long drafts, and MOTD dismissal work.
- Search: opens with the keyboard up and results stay above the keys; tapping a result closes the keyboard and lands on the right line; "Back to live" returns to the newest chat; back returns to the results.
- Long-press a line: the menu opens and stays open when you lift your finger; Copy text pastes into Notes; Find in chat opens Search with the name. A line with an item: "Search BG-Wiki for" opens BG-Wiki, and a plain tap on the item replies instead of opening BG-Wiki. A line with a web address: a tap replies; long-press shows "Open <site>"; Open asks first with the site in bold; Cancel opens nothing; Open opens it in Safari; Copy (on the confirm screen) copies it without closing. A short tap still replies. Page scrolling isn't caught as a long-press.
- New line: leave LS1's page, let lines come in, open it again: "New" sits above them. Lock the phone for a minute and come back: Chat shows "New".
- Alerts: tapping a mention lands on that line; back says Alerts.
- Keyboard up in Chat: the title row, view tabs, chips and MOTD hide and come back when the keyboard closes; the newest line stays in view.
- Lock/unlock, Wi-Fi loss/recovery, bridge restart: history recovers and no message is resent automatically.
- VNM/HVNM first announcement, warning, concurrent events, POP!, and expiry.

## Settings must survive an update
Three rules for every change, so nobody loses their setup:
1. Never rename a stored setting or one of its saved values. Change the label on screen only (the Font option "Plain" is still saved as `classic`).
2. Every new option has a default, so settings saved by an older version load without it.
3. Never move the phonechat folder or change what `config.json` holds.

`node tools/test_qc.js` loads a 1.1.0-era settings file into the current page and checks nothing is lost. Add to that file's sample when a release adds an option.

## Install and upgrade
- Ask a new tester to follow the README without assistance; record unclear steps.
- Upgrade an existing install, preserving custom colors/settings and opt-in tell history. The phone shows "Updated to <version>. Your settings were kept." once; Settings > Backup offers "Before the last update" and the restore brings the old settings back.
- Confirm the new build identifier appears after restarting the addon/bridge and reloading the phone page.
- Retain the previous known-good ZIP and back up local settings privately before testing rollback; verify the previous version starts and preferences remain usable.
- Share only the generated release ZIP. Do not include phone links, QR codes, configuration, or real chat logs in reports.

Release only after recording device results; automated checks do not replace them.
