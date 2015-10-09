#!/bin/bash
echo "Installing Tyler's Config"

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Install spf-13 vim
if [ -z "${VIMRUNTIME+x}" ]
then 
    sh <(curl https://j.mp/spf13-vim3 -L)
else
    echo "You need vim installed to install spf-13 vim"


#Switch to the install directory
cd $DIR

#Create links to the files in the user's home directory
shopt -s extglob
ln -s ./!(setup.sh|.git) ~/
shopt -u extglob

