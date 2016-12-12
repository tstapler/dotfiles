if hash keychain 2>/dev/null; then
	eval `keychain --agents ssh --eval id_rsa`
fi

# Language managers (RVM, NVM, PYENV, ...)
source $HOME/.shell/languages.sh
