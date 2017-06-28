#!/usr/bin/env sh
REPO_NAME=dotfiles
CLONE_DIR="$HOME/$REPO_NAME"
DOTFILES_REPO="tstapler/$REPO_NAME"

haveProg() {
  [ -x "$(which "$1")" ]
}

install_package() {
if haveProg apt-get ; then sudo apt-get update && sudo apt-get install -y "$@"
elif haveProg yum ; then sudo yum install "$@"
elif haveProg pacman ; then sudo pacman -S "$@"
else
  echo 'Current package manager not supported!'
  echo "Please install $@ manually"
  exit 2
fi
}


if [ ! -d $HOME/dotfiles ]; then
  echo "Cloning dotfiles"
  git clone "ssh://git@github.com/$DOTFILES_REPO" "$CLONE_DIR" || git clone "https://github.com/$DOTFILES_REPO" "$CLONE_DIR"
else
  echo "Skipping directory creation, $CLONE_DIR already exists."
fi

echo "Checking out and updating submodules"
cd "$CLONE_DIR" && git submodule update --init --recursive

CFG_CADDY_DIR="$CLONE_DIR"/cfgcaddy

if [[ -d "$CFG_CADDY_DIR" ]]; then
  echo "Installing cfgcaddy dependencies."
  if ! haveProg pip; then
    install_package python-pip
  fi
  pip install --user -r "$CFG_CADDY_DIR"/requirements.txt

  echo "Linking Dotfiles"
  "$CLONE_DIR"/bin/scripts/cfgcaddy link
else 
  echo "cfgcaddy repo is not present, cannot link dotfiles"
fi
