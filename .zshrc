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

# Prompt Config
source ~/.shell/powerlevel9k.sh

# Export Environment Variables
source ~/.shell/exports.sh

#Aliases
source ~/.shell/aliases.sh



# Load .NET version manager
[ -s "/home/tstapler/.dnx/dnvm/dnvm.sh" ] && . "/home/tstapler/.dnx/dnvm/dnvm.sh" # Load dnvm
