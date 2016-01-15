#Install pyenv
if [ ! -d ~/.pyenv ]; then
    echo "Installing pyenv"
    curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
fi
