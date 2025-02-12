#!/bin/bash

# Update Termux packages
pkg update && pkg upgrade -y

# Install GitHub CLI
pkg install gh -y

# Configure Git with your name and email
git config --global user.name "Tyler Stapler"
git config --global user.email "tystapler@gmail.com"

# Setup SSH keys in the termux private storage
ssh-keygen -t rsa -b 4096 -C "tystapler@gmail.com" -f ~/.ssh/id_rsa -N ""

# Start the ssh-agent and add your SSH key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa

# Authenticate with GitHub CLI
gh auth login

# Clone your personal wiki repository into shared storage using GitHub CLI
gh repo clone tstapler/personal-wiki /storage/emulated/0/personal-wiki

