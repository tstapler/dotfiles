#!/usr/bin/env sh
REPO_NAME=dotfiles
CLONE_DIR="$HOME/$REPO_NAME"
DOTFILES_REPO="tstapler/$REPO_NAME"

haveProg() {
  [ -x "$(which "$1")" ]
}

install_package() {
if haveProg apt-get ; then sudo apt-get update && sudo apt-get install -y "$@"
elif haveProg yum ; then sudo yum install -y "$@"
elif haveProg pacman ; then sudo pacman -S --noconfirm "$@"
elif haveProg brew; then brew install "$@"
else
  echo 'Current package manager not supported!'
  echo "Please install $@ manually"
  exit 2
fi
}

PYTHON_EXE=python
PIP_PACKAGE_NAME=python-pip
PIP_EXE_NAME=pip
PIP_ARGS="--user"

OS="$(uname -a)"

case $OS in
	*Debian*)
		;;
	*Ubuntu*)
		;;
  *\#1-Microsoft*)
		;;
	*MANJARO*|*ARCH*)
		;;	
	*Darwin*)
	if ! haveProg brew; then
		/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
		brew install python
	fi
	echo "Detected OSX"
	PYTHON_EXE=python3
	PIP_PACKAGE_NAME=python
	PIP_EXE_NAME=pip3
	BREW_PATH="export PATH="$PATH:$(brew --prefix)/lib/$(python3 --version | awk '{ print $2}')/site-packages
	PROFILE="$HOME/.profile"
	grep -qxF "$BREW_PATH" "$PROFILE" || sudo echo "$BREW_PATH" >> "$PROFILE"
		;;
  *)
    echo "OS Not supported"
esac 

if ! haveProg git; then
  install_package git
fi

if [ ! -d "$HOME/dotfiles" ]; then
  echo "Cloning dotfiles"
  git clone "ssh://git@github.com/$DOTFILES_REPO" "$CLONE_DIR" || git clone "https://github.com/$DOTFILES_REPO" "$CLONE_DIR"
else
  echo "Skipping directory creation, $CLONE_DIR already exists."
fi

echo "Checking out and updating submodules"
cd "$CLONE_DIR" && git submodule update --init --recursive

CFG_CADDY_DIR="$CLONE_DIR"/cfgcaddy

if [ -d "$CFG_CADDY_DIR" ]; then
  echo "Installing cfgcaddy dependencies."

  if ! haveProg $PIP_EXE_NAME; then
    install_package $PIP_PACKAGE_NAME
  fi

  $PIP_EXE_NAME install $PIP_ARGS --editable "$CFG_CADDY_DIR"

  $PYTHON_EXE -m cfgcaddy init "$CLONE_DIR" "$HOME"

  echo "Linking Dotfiles"
  $PYTHON_EXE -m cfgcaddy link
else 
  echo "cfgcaddy repo is not present, cannot link dotfiles"
fi

if ! hash zsh 2>/dev/null; then
  install_package zsh gpg keychain
fi
