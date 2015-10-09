#!/bin/bash
echo "Installing Tyler's Config"

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Store the user's current directory
CURR = pwd
echo $CURR

#Switch to the install directory
cd $DIR

#Create links to the files in the user's home directory
shopt -s extglob
ln -s ./!(setup.sh|.git) ~/
shopt -u extglob

#Return to the directory where the script was called from
cd $CURR
