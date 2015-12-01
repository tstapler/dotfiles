#Pyenv init script
set PYENV_ROOT $HOME/.pyenv
set -x PATH $PYENV_ROOT/shims $PYENV_ROOT/bin $PATH
pyenv rehash
status --is-interactive; and . (pyenv init - | psub)
