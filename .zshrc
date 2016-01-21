#
#|_   _|   _| | ___ _ __( )___     _______| |__  _ __ ___ 
#  | || | | | |/ _ \ '__|// __|   |_  / __| '_ \| '__/ __|
#  | || |_| | |  __/ |    \__ \  _ / /\__ \ | | | | | (__ 
#  |_| \__, |_|\___|_|    |___/ (_)___|___/_| |_|_|  \___|
#      |___/                                              
#

# Load zgen, clone if not found
if [[ ! -d ~/.zplug ]];then
	git clone https://github.com/b4b4r07/zplug.git ~/.zplug
	source ~/.zplug/zplug
	zplug update --self
fi

source ~/.zplug/zplug

#Let zplug manage itself
zplug "b4b4r07/zplug"
zplug "robbyrussell/oh-my-zsh", of:oh-my-zsh.sh, nice:-10
zplug "themes/robbyrussell", from:oh-my-zsh
zplug "zsh-users/zsh-completions"
zplug "b4b4r07/enhancd", of:enhancd.sh
zplug "zsh-users/zaw"

#The fzf file searching command
zplug "zsh-users/zsh-syntax-highlighting"
zplug "tarruda/zsh-autosuggestions"

zplug "junegunn/fzf-bin", \
	as:command, \
	from:gh-r, \
	file:fzf, \
	of:"*linux*64*"

# Install plugins if there are plugins that have not been installed
if ! zplug check --verbose; then
	printf "Install? [y/N]: "
	if read -q; then
		echo; zplug install
	fi
fi

# Then, source plugins and add commands to $PATH
zplug load --verbose

# Enable autosuggestions automatically.
 zle-line-init() {
     zle autosuggest-start
     }
     zle -N zle-line-init
# bind UP and DOWN arrow keys
 zmodload zsh/terminfo
 bindkey "$terminfo[kcuu1]" history-substring-search-up
 bindkey "$terminfo[kcud1]" history-substring-search-down

#Add predict
autoload predict-on
predict-toggle() {
  ((predict_on=1-predict_on)) && predict-on || predict-off
}
zle -N predict-toggle
bindkey '^Z'   predict-toggle
zstyle ':predict' toggle true
zstyle ':predict' verbose true

# User configuration
export PATH="/home/tstapler/stapler-config/env/bin:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
	export EDITOR='vim'
else
	export EDITOR='mvim'
fi

#Aliases
alias zshconfig="$EDITOR ~/.zshrc"
alias ohmyzsh="$EDITOR ~/.oh-my-zsh"
alias vimrc="$EDITOR ~/.vimrc"

#Set environment varibles
export ENHANCD_FILTER=fzf
#Setup RVM
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting
