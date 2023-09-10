export SCRIPT_PATH=/tmp/dont-leave-your-computer-unlocked.sh

cat << EOF > $SCRIPT_PATH
#!/usr/bin/env bash

# Sleep for a random duration
sleep \$((RANDOM % 400 ))

# Fetch a funny quote
QUOTE=\$(curl -s "http://quotes.rest/qod.json?category=funny" | python3 -c 'import json,sys;quote=json.load(sys.stdin)["contents"]["quotes"][0]["quote"];print(quote)')

# Get OS
OS=\$(uname)

# MacOS specific
if [[ "\$OS" == "Darwin" ]]; then
    VOLUME=\$(osascript -e 'output volume of (get volume settings)')
    osascript -e "set volume output volume 100"
    say "\$QUOTE"
    say "And by the way, don't leave your computer unlocked."
    osascript -e "set volume output volume \$VOLUME"

# Linux specific (using amixer for volume and spd-say for speech)
elif [[ "\$OS" == "Linux" ]]; then
    VOLUME=\$(amixer get Master | grep -oP '\[\d+%\]' | head -1 | tr -d '[]%')
    amixer set Master 100%
    spd-say "\$QUOTE"
    spd-say "And by the way, don't leave your computer unlocked."
    amixer set Master \$VOLUME%
fi
EOF

chmod +x /tmp/dont-leave-your-computer-unlocked.sh

# Append to crontab if not present
if ! crontab -l | grep -q "$SCRIPT_PATH"; then
    (EDITOR=tee && crontab -l ; echo "29 * * * * $SCRIPT_PATH") 2>&1 | sed "s/crontab: no crontab for $(whoami)//"  | sort | uniq | crontab -
fi

# Inform the user about the prank
echo "Prank set. To disable:"
echo "touch empty && crontab empty"
echo "rm /tmp/dont*.sh"
