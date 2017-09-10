# Skaardb tools
export VENV=local

alias ddev='pub run dart_dev'

if hash pub 2>/dev/null; then
  # Use dart_dev completions
  if [ -n "$ZSH_VERSION" ]; then
    autoload -U compinit
    compinit
    autoload -U bashcompinit
    bashcompinit
    eval "$(pub global run dart_dev bash-completion)"
  elif [ -n "$BASH_VERSION" ]; then
    eval "$(pub global run dart_dev bash-completion)"
  fi
fi

OS="$(uname)"
case $OS in
	'Darwin')
	# Setup Groovy
  export GROOVY_HOME='/usr/local/opt/groovy/libexec'
  ;;
esac

alias erasereset="workon sky; python tools/erase_reset_data.py --admin=tyler.stapler@workiva.com --password=a"

PATH="$PATH:$HOME/Workiva/pss/scripts"
