#Install pyenv
if [ ! -d ~/.pyenv ]; then
    echo "Installing pyenv"
    installer_script=$(mktemp)
    if curl -fsSL https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer -o "$installer_script"; then
        bash "$installer_script"
        rm "$installer_script"
    else
        echo "Failed to download pyenv installer"
        rm "$installer_script"
        exit 1
    fi
fi
