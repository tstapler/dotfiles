#!/bin/bash

#Set Fish as the default script for future runs if available
if [ -a /usr/bin/fish ] && [ "$SHELL" != "/usr/bin/fish" ]; then
    echo "Setting Fish as Default Shell"
    chsh -s /usr/bin/fish $USER
fi

