#!/usr/bin/env zsh

set -o nounset                              # Treat unset variables as an error

# Remove the usual suspects to support a fresh zplug install
rm -rf $HOME/.zplug
rm -rf $HOME/.cache/zplug
rm -f $HOME/.zcompdump
