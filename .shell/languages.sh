ASDF_DIR="$HOME/.asdf"

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
ASDF_PLUGIN_DIR="$ASDF_DIR/plugins"
# Add ASDF plugins if they don't exist
  for plug in nodejs python java golang clojure
  do
    if [ ! -d "$ASDF_PLUGIN_DIR/$plug" ]; then
      asdf plugin add $plug
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

if ! hash poetry 2>/dev/null; then
  if hash python3 2>/dev/null; then
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
  fi
fi
