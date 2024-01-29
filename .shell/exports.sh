# Add Dart pub files to PATH
pathadd "$HOME/.pub-cache/bin"

# Add personal executables to path
pathadd "$HOME/bin/bin"

# Add personal scripts to path
pathadd "$HOME/bin/scripts"

LOCAL_BIN="$HOME/.local/bin"
pathadd "$LOCAL_BIN"

HOMEBREW_PATH="/opt/homebrew/bin/"
if [[ -d "$HOMEBREW_PATH" ]]; then
  pathadd "$HOMEBREW_PATH"
fi

# Add Android Home to Path
if [[ -d /opt/android-sdk ]]; then
	export ANDROID_HOME="/opt/android-sdk"
elif [[ -d /opt/android-sdk-linux ]]; then
	export ANDROID_HOME="/opt/android-sdk-linux"
fi

if [[ -d "$HOME/Android" ]]; then
	android_root="$HOME/Android"
elif [[ -d  "$HOME/Library/Android" ]]; then
	android_root="$HOME/Library/Android"
fi

android_sdk_path="$android_root/Sdk"
if [[ -d "$android_sdk_path" ]]; then
	export ANDROID_HOME="$android_sdk_path"
	export ANDROID_SDK_ROOT="$ANDROID_HOME"
fi

adv_home="$HOME/.android/avd"
if [[ -d "$adv_home" ]]; then
	export ANDROID_AVD_HOME="$adv_home"
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


# Completions for NativeScript
if [ -f "$HOME/.tnsrc" ]; then 
    source "$HOME/.tnsrc" 
fi

if hash hunspell 2>/dev/null; then
  export DICTIONARY=en_US
  export DICTPATH=$HOME/.nix-profile/share/hunspell/$DICTIONARY
fi

if hash helm 2>/dev/null; then
	source <(helm completion zsh)
fi

if hash aws_completer 2>/dev/null; then
	complete -C aws_completer aws
fi

if hash aws-vault 2>/dev/null; then 
	eval "$(aws-vault --completion-script-zsh)"
fi

if hash gr 2>/dev/null; then
  unalias gr 2>/dev/null
  source <(gr completion)
fi


if hash flux 2>/dev/null; then
  source <(flux completion zsh)
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

# Export the path that we have updated via pathadd
export PATH="$PATH"
