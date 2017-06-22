
export NVM_DIR="$HOME/.nvm"
if [[ -d $NVM_DIR ]]; then
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm
fi

# Load .NET version manager
DNX_DIR="$HOME/.dnx"
if [[ -d "$DNX_DIR" ]]; then
  DNX_SCRIPT="$DNX_DIR/dnvm/dnvm.sh"
[ -s "$DNX_SCRIPT" ] && . "$DNX_SCRIPT" # Load dnvm
fi

# Load virtualenvwrapper
GLOBAL_BIN="/usr/local/bin"
USER_BIN="$HOME/.local/bin"
VENV_WRAP_SH="virtualenvwrapper.sh"

if [[ -d $USER_BIN ]]; then
  VENV_WRAP_SCRIPT="$USER_BIN/$VENV_WRAP_SH"
else
  VENV_WRAP_SCRIPT="$GLOBAL_BIN/$VENV_WRAP_SH"
fi

if [[ -f "$VENV_WRAP_SCRIPT" ]]; then
	if [[ $WORKIVA == true ]]; then
		export PROJECT_HOME=$HOME/Workiva
	else
		export PROJECT_HOME=$HOME/Programming/Python
	fi
  mkdir -p "$PROJECT_HOME"
	export WORKON_HOME=$HOME/.virtualenvs
	source $VENV_WRAP_SCRIPT
fi

if [[ -s "$HOME/.rvm/scripts/rvm" ]]; then
	# Add RVM to PATH for scripting
	export PATH="$PATH:$HOME/.rvm/bin" 
	source "$HOME/.rvm/scripts/rvm"
fi
