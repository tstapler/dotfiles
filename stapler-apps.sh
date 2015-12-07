#!/bin/bash

#Set Fish as the default script for future runs if available
if [ -a /usr/bin/fish ] && [ "$SHELL" != "/usr/bin/fish" ]; then
    echo "Setting Fish as Default Shell"
    chsh -s /usr/bin/fish $USER
fi

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Install Applications
sudo apt-get install eclipse vim-gtk


#Install Development Tools
sudo apt-get install nodejs

#Install Node Packages
sudo npm install -g js-beautify

#Install Ruby Gems
sudo gem install ruby-beautify

#Install Libraries and Build Utilities
sudo apt-get install automake gcc cmake openjdk-7-jdk exuberant-ctags pylint

#Install Neobundle and vim plugins
if [ ! -d ~/.vim/bundle/neobundle.vim ]; then
    echo "Installing neobundle, and related vim files"
    if [ -z "${VIMRUNTIME+x}" ];
    then 
        #Install Neobundle
        if [ ! -d ~/.vim/bundle ]; then
        mkdir -p ~/.vim/bundle
        fi
        git clone https://github.com/Shougo/neobundle.vim ~/.vim/bundle/neobundle.vim

        #TODO:Install Eclim Support
        #TODO:Install Eclipse 4.5 (Mars)

    else
        echo "You need vim installed to install spf-13 vim"
    fi
    sudo apt-get install astyle clang-format ack-grep silversearcher-ag python-autopep8 tidy 
fi



if [ ! -d /usr/local/share/wemux ]; then
    echo "Installing tmux/wemux"
    sudo git clone git://github.com/zolrath/wemux.git /usr/local/share/wemux
    sudo ln -sv /usr/local/share/wemux/wemux /usr/local/bin/wemux
    sudo cp -rvs $DIR/wemux.conf /usr/local/etc/wemux.conf

    echo "Installing wemux-pair"
    gem install wemux-pair
fi

#Install pyenv
if [ ! -d ~/.pyenv ]; then
    echo "Installing pyenv"
    curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
fi
