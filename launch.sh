#!/bin/sh
set -eu
if [ -n "${DISPLAY:-}" ]; then
    export GDK_BACKEND="${GDK_BACKEND:-x11}"
fi
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 "$base/app.py" "$@"
