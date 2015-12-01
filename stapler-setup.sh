#!/bin/bash
echo "Installing Tyler's Config"

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

if [ ! -d ~/.spf13-vim-3/ ];
then
    #Install spf-13 vim
    if [ -z "${VIMRUNTIME+x}" ];
    then 
        sh <(curl https://j.mp/spf13-vim3 -L)
    else
        echo "You need vim installed to install spf-13 vim"
    fi
fi


#Switch to the install directory
cd $DIR

#Create links to the files in the user's home directory
echo "Linking the following files to the home directory"
bash -O extglob -c 'echo !(*-setup.sh*|.git|.|..)'
bash -O extglob -c 'ln -s !(*-setup.sh*|.git|.|..) ~/'

