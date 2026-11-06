#!/bin/sh
# Start the phonechatXI bridge. The addon runs this through Proton (/pchat start); you can also
# run it yourself. In a terminal it prints to the screen; otherwise it logs to ../bridge.log.
cd "$(dirname "$0")" || exit 1
if [ -t 1 ]; then
    exec python3 -u bridge.py "$@"
fi
LOG=../bridge.log
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1000000 ]; then : > "$LOG"; fi
echo "== $(date) start" >> "$LOG"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not found. phonechatXI needs python3." >> "$LOG"
    exit 1
fi
exec python3 -u bridge.py "$@" >> "$LOG" 2>&1
