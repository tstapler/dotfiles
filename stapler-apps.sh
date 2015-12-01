#!/bin/bash

echo "Installing spf-13 and vim related files"
#Files for Vim Plugins
sudo apt-get install ack-grep silversearcher-ag

#Install spf-13 vim
if [ ! -d ~/.spf13-vim-3/ ];
then
    if [ -z "${VIMRUNTIME+x}" ];
    then 
        sh <(curl https://j.mp/spf13-vim3 -L)
    else
        echo "You need vim installed to install spf-13 vim"
    fi
fi


