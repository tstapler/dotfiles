REPO_NAME=dotfiles
CLONE_DIR="$HOME/$REPO_NAME"
DOTFILES_REPO="tstapler/$REPO_NAME"


if [[ ! -d $HOME/dotfiles ]]; then
  echo "Cloning dotfiles"
  git clone "ssh://git@github.com/$DOTFILES_REPO" "$CLONE_DIR" || git clone "https://github.com/$DOTFILES_REPO" "$CLONE_DIR"
  cd "$CLONE_DIR" && git submodule init && git update --init --recursive
  "$CLONE_DIR"/staplerlinker/staplerlinker/cli.py
else
  echo "Could not setup dotfiles, $CLONE_DIR already exists"
fi
