# Append a directory to PATH if it exists and isn't already present.
# Defined here so this file is self-contained for both zsh and bash
# (.bashrc and .zshrc both source it).
pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH="${PATH:+"$PATH:"}$1"
    fi
}

# Print-and-cache for slow `<tool> completion zsh` style generators: sets REPLY to a
# cache file keyed on the binary's mtime+size, so the tool only runs after an upgrade.
# zsh only (returns 1 elsewhere). Usage: _cache_output kubectl completion zsh && source "$REPLY"
_cache_output() {
    [ -n "$ZSH_VERSION" ] || return 1
    local exe=${commands[$1]} dir=${XDG_CACHE_HOME:-$HOME/.cache}/shell-eval name=${(j:_:)@}
    [[ -n $exe ]] || return 1
    local -A st
    zmodload -F zsh/stat b:zstat && zstat -H st -- $exe || return 1
    REPLY=$dir/$name.${st[mtime]}-${st[size]}
    [[ -s $REPLY ]] && return 0
    local -a stale
    mkdir -p $dir && "$@" >| $REPLY.$$ 2>/dev/null && [[ -s $REPLY.$$ ]] && mv -f $REPLY.$$ $REPLY || { rm -f $REPLY.$$; return 1; }
    stale=( $dir/$name.*(N) ); stale=( ${stale:#$REPLY} )
    (( $#stale )) && rm -f -- $stale
    return 0
}

# Add Rust/cargo-installed binaries (e.g. stapler-mcp, self-built rtk fork) to PATH
pathadd "$HOME/.cargo/bin"

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

# Self-built/self-managed binaries in ~/.local/bin should shadow Homebrew
# equivalents (e.g. a self-built rtk instead of the upstream bottle).
PATH="$LOCAL_BIN:$PATH"

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
	pathadd "$ANDROID_HOME/platform-tools"
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
export GPG_TTY=${TTY:-$(tty)}


# Completions for NativeScript
if [ -f "$HOME/.tnsrc" ]; then 
    source "$HOME/.tnsrc" 
fi

if hash hunspell 2>/dev/null; then
  export DICTIONARY=en_US
  export DICTPATH=$HOME/.nix-profile/share/hunspell/$DICTIONARY
fi

if hash helm 2>/dev/null; then
	_cache_output helm completion zsh && source "$REPLY"
fi

if hash aws_completer 2>/dev/null; then
	complete -C aws_completer aws
fi

if hash aws-vault 2>/dev/null; then 
	_cache_output aws-vault --completion-script-zsh && source "$REPLY"
	export AWS_VAULT_BIOMETRICS=true
fi

if hash gr 2>/dev/null; then
  unalias gr 2>/dev/null
  _cache_output gr completion && source "$REPLY"
fi


if hash flux 2>/dev/null; then
  _cache_output flux completion zsh && source "$REPLY"
fi

if hash kubectl 2>/dev/null; then
  _cache_output kubectl completion zsh && source "$REPLY"
fi

# Add krew the kubectl plugin manager to path
pathadd "${KREW_ROOT:-$HOME/.krew}/bin"

pathadd "$HOME/.yarn/bin"
pathadd "$HOME/.config/yarn/global/node_modules/.bin"
pathadd "$HOME/.poetry/bin"

# Personal wiki / Logseq graph root (used by knowledge synthesis commands).
# The graph moved from ~/Documents/personal-wiki/logseq to ~/Documents/notes.
# LOGSEQ_PATH is the path-agnostic lookup honored by logseq_path() and skills.
export LOGSEQ_PATH="$HOME/Documents/notes"
export PERSONAL_WIKI="$LOGSEQ_PATH"

# Export the path that we have updated via pathadd
export PATH="$PATH"

# SSH agent priority: 1Password → GPG → ~/.ssh/agent/* fallback.
# environment.d/ssh-agent.conf handles the systemd user instance (Claude Code, services).
if [ -z "$SSH_AUTH_SOCK" ] || [ ! -S "$SSH_AUTH_SOCK" ]; then
  _gpg_sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/gnupg/S.gpg-agent.ssh"
  _op_sock="$HOME/.1password/agent.sock"
  _fb_sock=$(ls -t "$HOME/.ssh/agent"/s.*.agent.* 2>/dev/null | head -1)
  if [ -S "$_op_sock" ]; then
    export SSH_AUTH_SOCK="$_op_sock"
  elif [ -S "$_gpg_sock" ]; then
    export SSH_AUTH_SOCK="$_gpg_sock"
  elif [ -n "$_fb_sock" ] && [ -S "$_fb_sock" ]; then
    export SSH_AUTH_SOCK="$_fb_sock"
  fi
  unset _gpg_sock _op_sock _fb_sock
fi
