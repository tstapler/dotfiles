# Make some possibly destructive commands more interactive.
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
 
# Add some easy shortcuts for formatted directory listings and add a touch of color.
alias ll='ls -lF --color=auto'
alias la='ls -alF --color=auto'
alias ls='ls -F'

# Add zmv aliases
alias zmv='noglob zmv'
alias zcp='noglob zmv -C'
alias zln='noglob zmv -L'
alias zsy='noglob zmv -Ls'

# Add npm-exec to execute from local node_modules
alias npm-exec='PATH=$(npm bin):$PATH'

# Use hub which gives git github integration
if hash hub 2>/dev/null; then
	alias git=hub
fi

alias gcv='git commit --verbose'

alias xkp='gen_pass'

if hash ag 2>/dev/null; then
	alias ag='ag --path-to-agignore ~/.agignore'
fi

# Encourage the use of NeoVim when possible
if [ "$EDITOR" = "nvim" ]; then
	alias vim='nvim'
fi


if hash gpg2 2>/dev/null; then
	alias gpg=gpg2
fi
