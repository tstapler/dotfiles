# _____     _           ___ _             _         _        ____   _
#|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___   |_  /__| |_  _ _ __
#  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  _ / /(_-< ' \| '_/ _|
#  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)___/__/_||_|_| \__|
#      |__/                         |_|

# Load zplug, clone if not found
if [[ ! -d ~/.zplug ]];then
	curl -sL zplug.sh/installer | zsh
fi

source ~/.zplug/init.zsh

# Let zplug manage itself
zplug "zplug/zplug"

zplug "willghatch/zsh-hooks"

# Theme
export TERM="xterm-256color"
zplug "bhilburn/powerlevel9k", use:powerlevel9k.zsh-theme

# Plugins
zplug "Vifon/deer"
zplug "zsh-users/zsh-completions"
zplug "Tarrasch/zsh-autoenv"
zplug "b4b4r07/enhancd", use:"init.sh"
zplug "zsh-users/zaw"

# The file searchers

if [[ `uname` == 'Linux' ]]; then
zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*linux*64*"
zplug "peco/peco", as:command, from:gh-r, rename-to:peco, use:"*linux*64*"
fi

if [[ `uname` == 'Darwin' ]]; then
zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*darwin*64*"
zplug "peco/peco", as:command, from:gh-r, rename-to:peco, use:"*darwin*64*"
fi


# Suggestions
zplug "tarruda/zsh-autosuggestions"
zplug "zsh-users/zsh-syntax-highlighting"
zplug "zsh-users/zsh-history-substring-search"

# Install plugins if there are plugins that have not been installed
if ! zplug check --verbose; then
	printf "Install? [y/N]: "
	if read -q; then
		echo; zplug install
	fi
fi

# Then, source plugins and add commands to $PATH
zplug load --verbose

# Load the zshell mv module
autoload zmv

# Vim Mode
bindkey -v

# Emacs like keybindings in insert mode
bindkey -M viins '^P' history-substring-search-up
bindkey -M viins '^N' history-substring-search-down
bindkey -M viins '^?' backward-delete-char
bindkey -M viins '^h' backward-delete-char
bindkey -M viins '^w' backward-kill-word
bindkey -M viins '^r' zaw-history
bindkey -M viins '^a' beginning-of-line
bindkey -M viins '^e' end-of-line
bindkey -M viins '^x^e' edit-command-line

# History subzmodload zsh/terminfo
bindkey "$terminfo[kcuu1]" history-substring-search-up
bindkey "$terminfo[kcud1]" history-substring-search-downstring plugin bindings
bindkey -M vicmd 'k' history-substring-search-up
bindkey -M vicmd 'j' history-substring-search-down


# Prompt Config
source $HOME/.shell/powerlevel9k.sh

# Export Environment Variables
source $HOME/.shell/exports.sh

# Aliases
source $HOME/.shell/aliases.sh

# Utility Functions
source $HOME/.shell/functions.sh

# By operating system
OS="`uname`"
case $OS in
	'Darwin')
	source ~/.shell/osx.sh
	;;
esac

# Machine Specific
if [[ -f $HOME/.shell/local.sh ]]; then
	source $HOME/.shell/local.sh
fi

# Workiva specific stuff
if [[ "$WORKIVA" == true ]] ; then
	source $HOME/.shell/workiva.sh
fi

# Language managers (RVM, NVM, PYENV, ...)
source $HOME/.shell/languages.sh
