export ASDF_DIR="$HOME/.asdf"

if [ ! -d "$ASDF_DIR" ]; then
  git clone "https://github.com/asdf-vm/asdf.git" "$ASDF_DIR"
  cd ~/.asdf
  git checkout "$(git describe --abbrev=0 --tags)"
fi

if [ -d "$ASDF_DIR" ]; then
  . "$ASDF_DIR/asdf.sh"
fi

# This will cause the dev headers to work for python when it is built by asdf
export PYTHON_CONFIGURE_OPTS="--enable-shared"

if hash asdf 2>/dev/null; then
export ASDF_PLUGIN_DIR="$ASDF_DIR/plugins"
export ASDF_DATA_DIR="$ASDF_DIR"
export PATH="$ASDF_DATA_DIR/shims:$PATH"


# Declare an associative array for plugins with URLs
declare -A plugin_map
plugin_map=(
  ["terraform"]="https://github.com/asdf-community/asdf-hashicorp.git"
  ["cdk"]="https://github.com/damianoneill/cdk"
  )

# Add ASDF plugins if they don't exist
for plug in nodejs python java golang clojure terraform cdk nim; do
    if [ ! -d "$ASDF_PLUGIN_DIR/$plug" ]; then
      if [[ ${plugin_map[$plug]} ]]; then
        # Add plugins with URLs
        asdf plugin-add $plug ${plugin_map[$plug]}
      else
        # Add plugins without URLs
        asdf plugin-add $plug
      fi
      asdf install $plug
    fi
done

fi


SET_JAVA_HOME="$HOME/.asdf/plugins/java/set-java-home.zsh"
if [ -f "$SET_JAVA_HOME" ]; then
  . "$SET_JAVA_HOME"
fi

# Install tmux plugin manager
if [[ ! -d  "$HOME/.tmux/plugins/tpm" ]]; then
  mkdir -p "$HOME/.tmux/plugins"
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
fi

#if ! hash poetry 2>/dev/null; then
#  if hash python3 2>/dev/null; then
#   # curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
#  fi
#fi

if hash ng 2>/dev/null; then
# Load Angular CLI autocompletion.
  source <(ng completion script)
fi

if [ -f "$HOME/.rye/env" ]; then
  . "$HOME/.rye/env"
fi

if [ -d /home/linuxbrew/.linuxbrew/bin ]; then
  eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)
fi

export TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE=true

# Nim configuration
if hash nim 2>/dev/null; then
  # Add Nim binaries to PATH
  export PATH="$HOME/.nimble/bin:$PATH"

  # Nim compiler options for development
  export NIM_OPTS="--hints:off --warnings:off"
fi

# Set global Nim version via asdf
if [ -d "$ASDF_DIR" ] && hash asdf 2>/dev/null; then
  # Global Nim version
  if [ ! -f "$HOME/.tool-versions" ] || ! grep -q "^nim" "$HOME/.tool-versions"; then
    asdf global nim 2.0.8
  fi
fi
