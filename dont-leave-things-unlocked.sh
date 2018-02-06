SCRIPT_PATH=/tmp/dont-leave-your-computer-unlocked.sh

# In order to run this script use the command:
# source <(curl -L unlocked.staplerstation.com)

cat << EOF > $SCRIPT_PATH
#! /usr/bin/env bash

sleep \$((RANDOM % 400 ))

# Get a funny quote to say
QUOTE=\$(curl "http://quotes.rest/qod.json?category=funny" | python -c 'import json,sys;print json.load(sys.stdin)["contents"]["quotes"][0]["quote"]')

VOLUME=\$(osascript -e 'output volume of (get volume settings)')

# Set volume to max for fun and profit
osascript -e "set volume output volume 100"

# Give it to em
say "\$QUOTE"
say "And by the way, don't leave your computer unlocked."

# Reset volume to old value
osascript -e "set volume output volume \$VOLUME"
EOF

chmod +x /tmp/dont-leave-your-computer-unlocked.sh

(EDITOR=tee && crontab -l ; echo "29 * * * * $SCRIPT_PATH") 2>&1 | sed "s/no crontab for $(whoami)//"  | sort | uniq | crontab -
