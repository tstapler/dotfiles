# Make some possibly destructive commands more interactive.
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
 
# Add some easy shortcuts for formatted directory listings and add a touch of color.
alias ll='ls -lF --color=auto'
alias la='ls -alF --color=auto'
alias ls='ls -F'

# Use hub which gives git github integration
if hash hub 2>/dev/null; then
	alias git=hub
fi

alias xkp='gen_pass'

# Encourage the use of NeoVim when possible
if [ "$EDITOR" = "nvim" ]; then
	alias vim='nvim'
fi


if hash gpg2 2>/dev/null; then
	alias gpg=gpg2
fi
