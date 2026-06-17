# asdf (Go version, 0.16+) — installed as a binary via Homebrew. No git clone
# and no asdf.sh sourcing; just put the shims on PATH. Plugins and tool
# versions are managed by the asdf Ansible role / .tool-versions.
export ASDF_DATA_DIR="$HOME/.asdf"
if hash asdf 2>/dev/null; then
  export PATH="$ASDF_DATA_DIR/shims:$PATH"
fi

# Dev headers so python builds under asdf produce a shared libpython
export PYTHON_CONFIGURE_OPTS="--enable-shared"

SET_JAVA_HOME="$ASDF_DATA_DIR/plugins/java/set-java-home.zsh"
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
