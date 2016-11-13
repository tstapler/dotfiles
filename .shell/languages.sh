
export NVM_DIR="$HOME/.nvm"
if [[ -d $NVM_DIR ]]; then
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm
fi

# Load .NET version manager
if [[ -d "~/.dnx" ]]; then
[ -s "/home/tstapler/.dnx/dnvm/dnvm.sh" ] && . "/home/tstapler/.dnx/dnvm/dnvm.sh" # Load dnvm
fi

# Load virtualenvwrapper
if [[ -f "/usr/local/bin/virtualenvwrapper.sh" ]]; then
	if [[ $WORKIVA == true ]]; then
		export PROJECT_HOME=$HOME/Workiva
	else
		export PROJECT_HOME=$HOME/Programming/Python
	fi
	export WORKON_HOME=$HOME/.virtualenvs
	source /usr/local/bin/virtualenvwrapper.sh
fi

if [[ -s "$HOME/.rvm/scripts/rvm" ]]; then
	# Add RVM to PATH for scripting
	export PATH="$PATH:$HOME/.rvm/bin" 
	source "$HOME/.rvm/scripts/rvm"
fi
