#!/bin/bash
echo "Installing Tyler's Config"

#Store the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR 

#Switch to the install directory
cd $DIR

#Create links to the files in the user's home directory
echo "Linking the following files to the home directory"
bash -O extglob -c 'echo !(*-setup.sh*|.git|.|..)'
bash -O extglob -c 'ln -s !(*-setup.sh*|.git|.|..) ~/'

