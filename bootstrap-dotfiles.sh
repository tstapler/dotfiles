#!/usr/bin/env sh
REPO_NAME=dotfiles
CLONE_DIR="$HOME/$REPO_NAME"
DOTFILES_REPO="tstapler/$REPO_NAME"


# Install python
if ! [ -d "$HOME/.pyenv/" ]; then
  curl https://pyenv.run | bash
fi

PYTHON_VERSION=3.9.12
export PYENV_VERSION=$PYTHON_VERSION
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
if ! [ -d "$HOME/.pyenv/versions/$PYTHON_VERSION/" ]; then
  pyenv install 3.9.12
fi

pyenv exec python -m pip install pipx
pyenv exec pipx ensurepath
pyenv exec pipx install ansible

if [ ! -d "$HOME/dotfiles" ]; then
  echo "Cloning dotfiles"
  GIT_CONFIG_NOSYSTEM=1 git clone "https://github.com/$DOTFILES_REPO" "$CLONE_DIR"
else
  echo "Skipping directory creation, $CLONE_DIR already exists."
fi

echo "Checking out and updating submodules"
cd "$CLONE_DIR" && git submodule update --init --recursive


echo "Installing cfgcaddy dependencies."

pyenv exec pipx install cfgcaddy
pyenv exec cfgcaddy init "$CLONE_DIR" "$HOME"

echo "Linking Dotfiles"
pyenv exec cfgcaddy link

cd "$HOME/dotfiles/stapler-scripts/" || exit

pyenv exec ansible-galaxy install -r requirements.yml
pyenv exec ansible-playbook -vvv -K bootstrap.yaml
