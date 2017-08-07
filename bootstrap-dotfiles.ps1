$REPO_NAME="dotfiles"
$CLONE_DIR="$HOME/$REPO_NAME"
$DOTFILES_REPO="tstapler/$REPO_NAME"

if(!(Get-Command git)) {
    Write-Verbose "This script requires Git! Please install"
    return
}

if(!(Test-Path -Path "$HOME/dotfiles")){
  Write-Verbose "Cloning dotfiles"
  git clone "ssh://git@github.com/$DOTFILES_REPO" "$CLONE_DIR" || git clone "https://github.com/$DOTFILES_REPO" "$CLONE_DIR"
} else {
  Write-Verbose "Skipping directory creation, $CLONE_DIR already exists."
}

Write-Verbose "Checking out and updating submodules"
cd "$CLONE_DIR" && git submodule update --init --recursive

$CFG_CADDY_DIR="$CLONE_DIR"/cfgcaddy

if ((Test-Path -Path "$CFG_CADDY_DIR"))
{
  Write-Verbose "Installing cfgcaddy dependencies."
  if ( ! (Get-Command pip)) {
    install_package python-pip
  }
  pip install --user --editable "$CFG_CADDY_DIR"

  Write-Verbose "Linking Dotfiles"
  
  cfgcaddy link
  
 } else {
 
 Write-Verbose "cfgcaddy repo is not present, cannot link dotfiles"
 
}
