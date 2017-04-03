# Skaardb tools
export VENV=local

run_local_skaardb () {
if ! pgrep skaardb > /dev/null; then
	if ! pgrep gnatsd > /dev/null; then
		echo "Starting gnatsd in background!"
		gnatsd& > /dev/null
	fi

	if ! pgrep messaging-frontend > /dev/null; then
		echo "Starting messaging-frontend in background!"
		messaging-frontend& > /dev/null
	fi

	if [ -f ./skaardb ]; then
		echo "Starting local skaardb!"
		./skaardb
	else
		echo "Starting global skaardb!"
		skaardb
	fi
else
	echo "skaardb already running!"
fi
}

alias ddev='pub run dart_dev'


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
OS="$(uname)"
case $OS in
	'Darwin')
	# Setup Groovy
	export GROOVY_HOME=/usr/local/opt/groovy/libexec
	if [[ -f  '/opt/homebrew-cask/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc' ]]; then
		source '/opt/homebrew-cask/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc'
		source '/opt/homebrew-cask/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc'
	fi
	;;
esac

alias erasereset="workon sky; python tools/erase_reset_data.py --admin=tyler.stapler@workiva.com --password=a"
