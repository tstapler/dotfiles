#
#|_   _|   _| | ___ _ __( )___     _______| |__  _ __ ___ 
#  | || | | | |/ _ \ '__|// __|   |_  / __| '_ \| '__/ __|
#  | || |_| | |  __/ |    \__ \  _ / /\__ \ | | | | | (__ 
#  |_| \__, |_|\___|_|    |___/ (_)___|___/_| |_|_|  \___|
#      |___/                                              
#

# load zgen
source "${HOME}/.zgen/zgen.zsh"

# check if there's no init script
if ! zgen saved; then
    echo "Creating a zgen save"

    zgen oh-my-zsh

    # plugins
    zgen oh-my-zsh plugins/git
    zgen oh-my-zsh plugins/sudo
    zgen oh-my-zsh plugins/tmux
    zgen oh-my-zsh plugins/command-not-found

    # completions
    zgen load zsh-users/zsh-completions src


    zgen load chrissicool/zsh-256color

    #File browser
    zgen load Vifon/deer


    # syntax highlighting
    zgen load zsh-users/zsh-syntax-highlighting
    
    # fish like history search
    zgen load zsh-users/zsh-history-substring-search

    #Bind Keys for zsh-history-substring-search
    ###########################################

    # bind UP and DOWN arrow keys
    zmodload zsh/terminfo
    bindkey "$terminfo[kcuu1]" history-substring-search-up
    bindkey "$terminfo[kcud1]" history-substring-search-down

    # bind k and j for VI mode
    bindkey -M vicmd 'k' history-substring-search-up
    bindkey -M vicmd 'j' history-substring-search-down

    ############################################

    # suggestions
    zgen load tarruda/zsh-autosuggestions

    # Enable autosuggestions automatically
    zle-line-init() {
	    zle autosuggest-start
    }
    zle -N zle-line-init


    # theme
    zgen load halfo/lambda-mod-zsh-theme lambda-mod

    # save all to init script
    zgen save
fi




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

#Setup RVM
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting
