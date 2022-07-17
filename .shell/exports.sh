# Add Dart pub files to PATH
pathadd "$HOME/.pub-cache/bin"

# Add personal executables to path
pathadd "$HOME/bin/bin"

# Add personal scripts to path
pathadd "$HOME/bin/scripts"

LOCAL_BIN="$HOME/.local/bin"
pathadd "$LOCAL_BIN"

# Add Android Home to Path
if [[ -d /opt/android-sdk ]]; then
	export ANDROID_HOME="/opt/android-sdk"
elif [[ -d /opt/android-sdk-linux ]]; then
	export ANDROID_HOME="/opt/android-sdk-linux"
fi

# Create Go Path
export GOPATH="$HOME/.local/lib/go"
export GOBIN="$LOCAL_BIN"

# Create Workiva Gopath
export WGOPATH="$GOPATH/src/github.com/Workiva"

# Enable go modules
export GO111MODULES=auto

# Add GO executables to PATH
pathadd "$GOPATH/bin"

# Add Cabal to PATH
pathadd "$HOME/.cabal/bin"

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

# Fixes git + gpg error inside of tmux
export GPG_TTY=$(tty)

# Enable GPG SSH auth
if hash gpgconf 2>/dev/null; then
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)
fi


# Completions for NativeScript
if [ -f "$HOME/.tnsrc" ]; then 
    source "$HOME/.tnsrc" 
fi

if hash hunspell 2>/dev/null; then
  export DICTIONARY=en_US
  export DICTPATH=$HOME/.nix-profile/share/hunspell/$DICTIONARY
fi

if hash gr 2>/dev/null; then
  unalias gr 2>/dev/null
  . <(gr completion)
fi

if hash kubectl 2>/dev/null; then
  source <(kubectl completion zsh)
fi

# Add krew the kubectl plugin manager to path
pathadd "${KREW_ROOT:-$HOME/.krew}/bin"

if hash helm 2>/dev/null; then
  source <(helm completion zsh)
fi

pathadd "$HOME/.yarn/bin"
pathadd "$HOME/.config/yarn/global/node_modules/.bin"
pathadd "$HOME/.poetry/bin"
