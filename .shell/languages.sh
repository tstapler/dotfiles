ASDF_PLUGIN_DIR="$ASDF_DIR/plugins"

ASDF_SETUP="$HOME/.asdf/asdf.sh" 
if [ -f "$ASDF_SETUP" ]; then
  . $ASDF_SETUP
fi
if ! hash asdf 2>/dev/null; then
  git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.8.0
fi

if hash asdf 2>/dev/null; then
# Add ASDF plugins if they don't exist
  for plug in nodejs python java
  do
    if [ ! -d "$ASDF_PLUGIN_DIR/$plug" ]; then
      asdf plugin add $plug
    fi
  done
fi


SET_JAVA_HOME="$HOME/.asdf/plugins/java/set-java-home.zsh"
if [ -f "$SET_JAVA_HOME" ]; then
  . "$SET_JAVA_HOME"
fi
# Load N (Node.js the version manager)
# export N_PREFIX="$HOME/n"; 

# if [ ! -d  "$N_PREFIX" ]; then
#   echo "Installing n (The Node.js version manager)"

#   # Remove old NVM install if present
#   NVM_DIR="$HOME/.nvm" 
#   if [[ -d "$NVM_DIR" ]]; then
#       rm -rf "$NVM_DIR"
#   fi
#   curl -L https://git.io/n-install | bash -s -- -y -n
# fi

# if [ -d "$N_PREFIX" ]; then
#     [[ :$PATH: == *":$N_PREFIX/bin:"*  ]] || PATH+=":$N_PREFIX/bin" 
#     if hash npm 2>/dev/null; then
#       NPM_CONFIG_PREFIX="$HOME/.npm-global"
#       npm config set prefix "$NPM_CONFIG_PREFIX"
#       [[ :$PATH: == *":$NPM_CONFIG_PREFIX/bin:"*  ]] \
#         || PATH+=":$NPM_CONFIG_PREFIX/bin" 
#     fi
# fi


# # Load .NET version manager
# DNX_DIR="$HOME/.dnx"
# if [[ -d "$DNX_DIR" ]]; then
#   DNX_SCRIPT="$DNX_DIR/dnvm/dnvm.sh"
# [ -s "$DNX_SCRIPT" ] && . "$DNX_SCRIPT" # Load dnvm
# fi

# Load virtualenvwrapper
VENV_WRAP_SH="virtualenvwrapper.sh"

if hash $VENV_WRAP_SH >/dev/null 2>&1; then
	if [[ $WORKIVA == true ]]; then
		export PROJECT_HOME=$HOME/Workiva
	else
		export PROJECT_HOME=$HOME/Programming/Python
	fi
  mkdir -p "$PROJECT_HOME"
	export WORKON_HOME=$HOME/.virtualenvs
  source "$(which $VENV_WRAP_SH)"
fi

# Install tmux plugin manager
if [[ ! -d  "$HOME/.tmux/plugins/tpm" ]]; then
  mkdir -p "$HOME/.tmux/plugins"
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
fi

if ! hash poetry 2>/dev/null; then
  if python --version | grep -v 2.7 ; then
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
  fi
fi
