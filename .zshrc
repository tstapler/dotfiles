# _____     _           ___ _             _         _        ____   _
#|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___   |_  /__| |_  _ _ __
#  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  _ / /(_-< ' \| '_/ _|
#  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)___/__/_||_|_| \__|
#      |__/                         |_|


# Language managers (RVM, NVM, PYENV, ...)
source $HOME/.shell/languages.sh

# Check if zplug is installed
if [[ ! -d ~/.zplug ]]; then
  git clone https://github.com/zplug/zplug $HOME/.zplug
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

echo "Loading zplug"

# Then, source plugins and add commands to $PATH
zplug load --verbose

echo "Loading finished"

# Load the zshell mv module
autoload -U zmv

# Add line editing
autoload -Uz edit-command-line
zle -N edit-command-line

# Add Completions
# autoload -U bashcompinit && bashcompinit

setopt extendedglob

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
bindkey "$terminfo[kcud1]" history-substring-search-downstring plugin bindings
bindkey -M vicmd 'k' history-substring-search-up
bindkey -M vicmd 'j' history-substring-search-down

bindkey '^R' zaw-history


export ZPLUG_FILTER=fzy:fzf-tmux:fzf:peco:percol:zaw

_comp_options+=(NO_err_return)

# Setup Fasd
if hash fasd 2>/dev/null; then
	eval "$(fasd --init auto)"
else
	echo "Fasd not installed!"
fi

# Prompt Config
source $HOME/.shell/powerlevel9k.sh

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
	*\#1-Microsoft*)

	;;
esac
