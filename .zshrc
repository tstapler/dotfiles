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

#Theme
export TERM="xterm-256color"
zplug "bhilburn/powerlevel9k"
POWERLEVEL9k_MODE='awesome-fontconfig'

zplug "zsh-users/zsh-completions"
zplug "b4b4r07/enhancd", of:enhancd.sh
zplug "zsh-users/zaw"

zplug "zsh-users/zsh-syntax-highlighting"
zplug "tarruda/zsh-autosuggestions"

#The file searchers 
zplug "junegunn/fzf-bin", as:command, from:gh-r, file:fzf, of:"*linux*64*"
zplug "peco/peco", as:command, from:gh-r, file:peco, of:"*linux_amd64*"

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
# Toggle Auto Suggest
bindkey '^T' autosuggest-toggle

#Add predict
autoload predict-on
predict-toggle() {
  ((predict_on=1-predict_on)) && predict-on || predict-off
}
zle -N predict-toggle
bindkey '^Z'   predict-toggle
zstyle ':predict' toggle true
zstyle ':predict' verbose true

#Powerlevel 9k config
POWERLEVEL9K_PROMPT_ON_NEWLINE=true
POWERLEVEL9K_MULTILINE_FIRST_PROMPT_PREFIX="↱"
POWERLEVEL9K_MULTILINE_SECOND_PROMPT_PREFIX="↳ "
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(context dir rbenv vcs)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status history time)
POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
POWERLEVEL9K_SHORTEN_DELIMITER=""
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_from_right"
# User configuration
export PATH=$PATH:"/home/tstapler/stapler-config/env/bin:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

#Set GOPATH
export GOPATH=$HOME/Programming/go

#Add GO to PATH
export PATH=$PATH:$GOPATH/bin

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
