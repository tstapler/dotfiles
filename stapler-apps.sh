#!/bin/bash
#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Files for Vim Plugins
sudo apt-get install ack-grep silversearcher-ag dnf automake gcc gcc-c++ kernel-devel cmake python-devel

#Install spf-13 vim
if [ ! -d ~/.spf13-vim-3/ ];
echo "Installing spf-13 and vim related files"
then
    if [ -z "${VIMRUNTIME+x}" ];
    then 
        sh <(curl https://j.mp/spf13-vim3 -L)
        echo "Compiling YouCompleteMe"
        cd ~/.vim/bundle/YouCompleteMe
        ./install.py --clang-completer
    else
        echo "You need vim installed to install spf-13 vim"
    fi
fi

echo "Installing tmux/wemux \n"

if [ ! -d /usr/local/share/wemux ]; then
   sudo git clone git://github.com/zolrath/wemux.git /usr/local/share/wemux
   sudo ln -s /usr/local/share/wemux/wemux /usr/local/bin/wemux
   sudo cp -rs $DIR/wemux.conf /usr/local/etc/wemux.conf

   echo "Installing wemux-pair"
   gem install wemux-pair
fi

