
# Fixes git + gpg error inside of tmux
export GPG_TTY=$(tty)

# Add Dart pub files to PATH
export PATH=$PATH:"$HOME/.pub-cache/bin"

# Add personal executables to path
export PATH=$PATH:"$HOME/bin/bin"

# Add personal scripts to path
export PATH=$PATH:"$HOME/bin/scripts"

# Add user python executables to path
OS="$(uname)"
case $OS in
  'Linux') 
    export PATH=$PATH:"$HOME/.local/bin"
    ;;
  'FreeBSD')
    ;;
  'WindowsNT')
    ;;
  'Darwin') 
    export PATH=$PATH:"$HOME/Library/Python/2.7/bin"
    ;;
  'SunOS') ;;
  'AIX') ;;
  *) ;;
esac

# Add Android Home to Path
if [[ -d /opt/android-sdk ]]; then
	export ANDROID_HOME="/opt/android-sdk"
elif [[ -d /opt/android-sdk-linux ]]; then
	export ANDROID_HOME="/opt/android-sdk-linux"
fi

# Create Go Path
export GOPATH="$HOME/.local/lib/go"

# Add GO executables to PATH
export PATH=$PATH:"$GOPATH/bin"

# Add Cabal to PATH
export PATH=$PATH:"$HOME/.cabal/bin"

# Add LaTex files to PATH
export TEXMFHOME="$HOME/texmf"

# Set environment varibles for Enhancd
export ENHANCD_FILTER=fzf:peco:gawk

# Enable colorized command output
export CLICOLOR=1

# Set time style to MM/DD/YYYY
export TIME_STYLE=long-iso

# Editor Variable
if hash nvim 2>/dev/null; then
	# Use Neovim if it exists
	export EDITOR='nvim'

elif hash vim 2>/dev/null; then
	# Use Vim if no Neovim
	export EDITOR='vim'

else
	# Settle for vi if all else fails
	export EDITOR='vi'
	alias vim='vi'
fi

export GIT_EDITOR=$EDITOR

if [ -f "$HOME/.gpg-agent-info" ]; then
	. "$HOME/.gpg-agent-info"
	export GPG_AGENT_INFO
	export SSH_AUTH_SOCK
	export SSH_AGENT_PID
fi

# Completions for NativeScript
if [ -f "$HOME/.tnsrc" ]; then 
    source "$HOME/.tnsrc" 
fi

if hash gr 2>/dev/null; then
  . <(gr completion)
fi
