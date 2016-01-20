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

    # syntax highlighting
    zgen load zsh-users/zsh-syntax-highlighting

    # suggestions
    zgen load tarruda/zsh-autosuggestions

    # theme
    zgen oh-my-zsh themes/arrow


    # save all to init script
    zgen save
fi

zle-line-init() {
zle autosuggest-start
}
zle -N zle-line-init

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
#Setup RVM
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting
