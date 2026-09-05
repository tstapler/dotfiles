#Pyenv init script
#Set GOPATH
set GOPATH=$HOME/Programming/go

#Add GO to PATH
set PATH=$PATH:$GOPATH/bin

set PYENV_ROOT $HOME/.pyenv
set -x PATH $PYENV_ROOT/shims $PYENV_ROOT/bin $PATH
pyenv rehash
status --is-interactive; and . (pyenv init - | psub)
