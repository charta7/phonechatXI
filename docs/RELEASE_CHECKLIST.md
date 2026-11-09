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
- Lock/unlock, Wi-Fi loss/recovery, bridge restart: history recovers and no message is resent automatically.
- VNM/HVNM first announcement, warning, concurrent events, POP!, and expiry.

## Install and upgrade
- Ask a new tester to follow the README without assistance; record unclear steps.
- Upgrade an existing install, preserving custom colors/settings and opt-in tell history.
- Confirm the new build identifier appears after restarting the addon/bridge and reloading the phone page.
- Retain the previous known-good ZIP and back up local settings privately before testing rollback; verify the previous version starts and preferences remain usable.
- Share only the generated release ZIP. Do not include phone links, QR codes, configuration, or real chat logs in reports.

Release only after recording device results; automated checks do not replace them.
