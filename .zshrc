# _____     _           ___ _             _         _        ____   _
#|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___   |_  /__| |_  _ _ __
#  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  _ / /(_-< ' \| '_/ _|
#  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)___/__/_||_|_| \__|
#      |__/                         |_|


# Check if zplug is installed
if [[ ! -d ~/.zplug ]]; then
  # Ignore the system .gitconfig in case it tries to force SSH
  GIT_CONFIG_NOSYSTEM=1 git clone https://github.com/zplug/zplug $HOME/.zplug
fi


export ZPLUG_LOADFILE=$HOME/.zplug_packages.zsh
source $HOME/.zplug/init.zsh

# Install packages that have not been installed yet
if ! zplug check --verbose; then
    printf "Install? [y/N]: "
    if read -q; then
        echo; zplug install
    else
        echo
    fi
fi

# Then, source plugins and add commands to $PATH
zplug load

# Load the zshell mv module
autoload -U zmv

# Add line editing
autoload -Uz edit-command-line
zle -N edit-command-line

# Add Completions
autoload -U bashcompinit && bashcompinit

export HISTFILE=$HOME/.zsh_history

# Appends every command to the history file once it is executed
setopt inc_append_history
export HISTTIMEFORMAT="[%F %T] "
# How many lines to keep in memory
export HISTSIZE=10000
# How many lines to keep in the history file
export SAVEHIST=100000

# Add the time of the history command
setopt inc_append_history_time
# Reloads the history whenever you use it
setopt share_history

# Dont search for dupes when using Ctrl+R
setopt HIST_FIND_NO_DUPS

# Only save unique commands
setopt HIST_IGNORE_ALL_DUPS

setopt extendedglob

# Allow comments in interactive shells to mimic ksh, sh, bash behavior
setopt interactivecomments

# Vim Mode
bindkey -v

# Emacs like keybindings in insert mode
bindkey -M viins '^P' history-substring-search-up
bindkey -M viins '^N' history-substring-search-down
bindkey -M viins '^?' backward-delete-char
bindkey -M viins '^h' backward-delete-char
bindkey -M viins '^w' backward-kill-word
bindkey -M viins '^a' beginning-of-line
bindkey -M viins '^e' end-of-line
bindkey -M viins '^x^e' edit-command-line
bindkey -M vicmd '^x^e' edit-command-line

# History subzmodload zsh/terminfo
bindkey "$terminfo[kcuu1]" history-substring-search-up
bindkey "$terminfo[kcud1]" history-substring-search-down
bindkey -M vicmd 'k' history-substring-search-up
bindkey -M vicmd 'j' history-substring-search-down

bindkey '^R' zaw-history


export ZPLUG_FILTER=fzy:fzf-tmux:fzf:peco:percol:zaw

# Add a helper function to append to path
export -f pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH="${PATH:+"$PATH:"}$1"
    fi
}

# Language managers (RVM, NVM, PYENV, ...)
source $HOME/.shell/languages.sh

if hash keychain 2>/dev/null; then
	eval `keychain --agents gpg,ssh --quick --quiet --noask --inherit any`
fi

# Setup Fasd
if hash fasd 2>/dev/null; then
	eval "$(fasd --init auto)"
fi

# Prompt Config
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Export Environment Variables
source $HOME/.shell/exports.sh

# Aliases
source $HOME/.shell/aliases.sh

# Utility Functions
source $HOME/.shell/functions.sh

# Machine Specific Configuration
if [[ -f $HOME/.shell/local.sh ]]; then
	source $HOME/.shell/local.sh
fi

# Workiva specific stuff
if [[ "$WORKIVA" == true ]] ; then
	source $HOME/.shell/workiva.sh
fi

# By operating system
OS=$(uname -a)
case $OS in
	*Darwin*)
		source ~/.shell/osx.sh
	;;
esac
