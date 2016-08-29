# Fixes git + gpg error inside of tmux
export GPG_TTY=$(tty)

# Add Dart pub files to PATH
export PATH="$PATH":"$HOME/.pub-cache/bin"

# Add personal executables to path
export PATH=$PATH:"$HOME/bin/bin"

# Add personal scripts to path
export PATH=$PATH:"$HOME/bin/scripts"

# Create Go Path
export GOPATH="$HOME/.local/lib/go"

# Add LaTex files to PATH
export TEXMFHOME=~/texmf

# Add GO executables to PATH
export PATH="$PATH":"$GOPATH/bin"

# Add Cabal to PATH
export PATH="$HOME/.cabal/bin:"$PATH

# Set environment varibles for Enhancd
export ENHANCD_FILTER=fzf

# Setup RVM Path
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting

# Set Gem Path
if which ruby >/dev/null && which gem >/dev/null; then
    PATH="$(ruby -rubygems -e 'puts Gem.user_dir')/bin:$PATH"
fi

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
