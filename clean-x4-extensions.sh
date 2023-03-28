#!/usr/bin/env zsh

X4_EXTENSIONS_PATH="$HOME/.steam/steamapps/common/X4 Foundations/extensions"
find "$X4_EXTENSIONS_PATH" -type d -name '*bak' -exec rm --recursive --verbose {} +
