# Fixes git + gpg error inside of tmux
export GPG_TTY=$(tty)

# User path configuration
export PATH=$PATH:"/home/tstapler/stapler-config/env/bin:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/shims:/home/tstapler/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"

#Add Dart pub files to PATH
export PATH=$PATH:"/home/tstapler/.pub-cache/bin"

#Create Go Path
export GOPATH="$HOME/.local/lib/go"

#Add LaTex files to PATH
export TEXMFHOME=~/texmf

#Add GO executables to PATH
export PATH="$PATH":"$GOPATH/bin"

#Add Cabal to PATH
export PATH="$HOME/.cabal/bin:"$PATH

#Set environment varibles
export ENHANCD_FILTER=fzf

#Setup RVM
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting

# Editor Variable
if hash nvim 2>/dev/null; then
	# Use Neovim if it exists
	export EDITOR='nvim'
	export GIT_EDITOR='nvim'

elif hash vim 2>/dev/null; then
	# Use Vim if no Neovim
	export EDITOR='vim'
	export GIT_EDITOR='vim'

else
	# Settle for vi if all else fails
	export EDITOR='vi'
	alias vim='vi'
fi
