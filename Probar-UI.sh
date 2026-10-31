#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export DECK_LIBRARY_UI_PREVIEW=1
exec sh "$base/launch.sh" "$@"
