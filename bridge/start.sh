#!/bin/sh
# Start the phonechat bridge. Ctrl+C to stop.
cd "$(dirname "$0")" || exit 1
exec python3 bridge.py "$@"
