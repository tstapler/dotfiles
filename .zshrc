# _____     _           ___ _             _         _        ____   _
#|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___   |_  /__| |_  _ _ __
#  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  _ / /(_-< ' \| '_/ _|
#  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)___/__/_||_|_| \__|
#      |__/                         |_|

# Load zplug, clone if not found
if [[ ! -d ~/.zplug ]];then
	git clone https://github.com/b4b4r07/zplug.git ~/.zplug
	source ~/.zplug/zplug
	zplug update --self
fi

source ~/.zplug/zplug

#Let zplug manage itself
zplug "b4b4r07/zplug"

#oh-my-zsh pack
zplug "robbyrussell/oh-my-zsh", of:oh-my-zsh.sh, nice:-10
zplug "willghatch/zsh-hooks"

#Theme
export TERM="xterm-256color"
zplug "bhilburn/powerlevel9k"

zplug "zsh-users/zsh-completions"
zplug "b4b4r07/enhancd", of:enhancd.sh
zplug "zsh-users/zaw"

#The file searchers
zplug "junegunn/fzf-bin", as:command, from:gh-r, file:fzf, of:"*linux*64*"
zplug "peco/peco", as:command, from:gh-r, file:peco, of:"*linux_amd64*"

zplug "tarruda/zsh-autosuggestions"
zplug "zsh-users/zsh-syntax-highlighting"


# Install plugins if there are plugins that have not been installed
if ! zplug check --verbose; then
	printf "Install? [y/N]: "
	if read -q; then
		echo; zplug install
	fi
fi

# Then, source plugins and add commands to $PATH
zplug load --verbose

# Toggle Auto Suggest
bindkey '^T' autosuggest-toggle

#Powerlevel 9k config
POWERLEVEL9k_MODE='awesome-fontconfig'
POWERLEVEL9K_PROMPT_ON_NEWLINE=true
POWERLEVEL9K_MULTILINE_FIRST_PROMPT_PREFIX="%{%F{249}%}\u250f"
POWERLEVEL9K_MULTILINE_SECOND_PROMPT_PREFIX="%{%F{249}%}\u2517%{%F{default}%}%{%F{249}%}\u27A4% %{%F{red}%}$%  "
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(context dir virtualenv vcs vi_mode)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status history time)
POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
POWERLEVEL9K_SHORTEN_DELIMITER=""
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_from_right"
POWERLEVEL9K_DIR_DEFAULT_BACKGROUND="240"
POWERLEVEL9K_DIR_DEFAULT_FOREGROUND="208"
POWERLEVEL9K_DIR_HOME_BACKGROUND="208"
POWERLEVEL9K_DIR_HOME_FOREGROUND="240"
POWERLEVEL9K_DIR_HOME_SUBFOLDER_BACKGROUND="240"
POWERLEVEL9K_DIR_HOME_SUBFOLDER_FOREGROUND="208"

# User configuration
export PATH=$PATH:"/home/tstapler/stapler-config/env/bin:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

#Add Dart pub files to PATH
export PATH=$PATH:"/home/tstapler/.pub-cache/bin"

#Create Go Path
export GOPATH=/usr/local/go

#Add LaTex files to PATH
export TEXMFHOME=~/texmf

#Add GO to PATH
export PATH="$PATH":"$GOPATH/bin"

#Add Cabal to PATH
export PATH="$HOME/.cabal/bin:"$PATH

#Set environment varibles
export ENHANCD_FILTER=fzf

#Setup RVM
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting

if hash nvim 2>/dev/null; then
	# Use Neovim if it exists
	export EDITOR='nvim'
	alias vim='nvim'

elif hash vim 2>/dev/null; then
	# Use Vim if no Neovim
	export EDITOR='vim'

else
	# Settle for vi if all else fails
	export EDITOR='vi'
	alias vim='vi'
fi

#Aliases
alias zshconfig="$EDITOR ~/.zshrc"
alias ohmyzsh="$EDITOR ~/.oh-my-zsh"
alias vimrc="$EDITOR ~/.vimrc"



[ -s "/home/tstapler/.dnx/dnvm/dnvm.sh" ] && . "/home/tstapler/.dnx/dnvm/dnvm.sh" # Load dnvm
