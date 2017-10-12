# Load N (Node.js the version manager)
export N_PREFIX="$HOME/n"; 

if [ ! -d  "$N_PREFIX" ]; then
  echo "Installing n (The Node.js version manager)"

  # Remove old NVM install if present
  NVM_DIR="$HOME/.nvm" 
  if [[ -d "$NVM_DIR" ]]; then
      rm -rf "$NVM_DIR"
  fi
  curl -L https://git.io/n-install | bash -s -- -y -n
else
  [[ :$PATH: == *":$N_PREFIX/bin:"*  ]] || PATH+=":$N_PREFIX/bin" 
fi

# Load .NET version manager
DNX_DIR="$HOME/.dnx"
if [[ -d "$DNX_DIR" ]]; then
  DNX_SCRIPT="$DNX_DIR/dnvm/dnvm.sh"
[ -s "$DNX_SCRIPT" ] && . "$DNX_SCRIPT" # Load dnvm
fi

# Load virtualenvwrapper
VENV_WRAP_SH="virtualenvwrapper.sh"

if command -v $VENV_WRAP_SH >/dev/null 2>&1; then
	if [[ $WORKIVA == true ]]; then
		export PROJECT_HOME=$HOME/Workiva
	else
		export PROJECT_HOME=$HOME/Programming/Python
	fi
  mkdir -p "$PROJECT_HOME"
	export WORKON_HOME=$HOME/.virtualenvs
  source "$(which $VENV_WRAP_SH)"
fi

# Load gvm
GVM_DIR="$HOME/.gvm"
GVM_SCRIPT="$GVM_DIR/scripts/gvm"

if [[ ! -d "$GVM_DIR" ]]; then
  curl -s -S -L "https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer" | zsh
fi

if [[ -x "$GVM_SCRIPT" ]]; then
 . "$GVM_SCRIPT" 
 fi

# Load rbenv

if hash rbenv 2>/dev/null; then
  eval "$(rbenv init -)"
  IFS=:
    for GEM_PATH in $(gem env gempath); do
      PATH="$PATH:$GEM_PATH/bin"
    done
  IFS=" "
fi
