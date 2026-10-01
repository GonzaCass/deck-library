#!/bin/sh
# Double-click in Desktop Mode and choose Run.
set -eu
cd -- "$(dirname -- "$0")"
python3 install.py --desktop
exec "$HOME/Applications/DeckLibrary/launch.sh"
