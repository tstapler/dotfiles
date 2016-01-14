#!/bin/bash

echo "Installing Tyler's Config \n"

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Switch to the install directory

cd $DIR

#Create links to the files in the user's home directory
echo "Linking the following files to the home directory"
shopt -s extglob dotglob
echo $DIR/!(*stapler*|.git|.|..|.config) 
echo ""
cp --symbolic-link $DIR/!(*stapler*|.git|.|..|.config) ~/
cp -rs $DIR/.config/ ~/
shopt -u extglob dotglob
