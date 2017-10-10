# Make some possibly destructive commands more interactive.
alias rm="rm -i"
alias mv="mv -i"
alias cp="cp -i"
 
# Add some easy shortcuts for formatted directory listings
alias ll="ls -lF"
alias la="ls -alF"
alias ls="ls -F"

# Add zmv aliases
alias zmv="noglob zmv"
alias zcp="noglob zmv -C"
alias zln="noglob zmv -L"
alias zsy="noglob zmv -Ls"

# Add npm-exec to execute from local node_modules
alias npm-exec='PATH=$(npm bin):$PATH'

# Use hub which gives git github integration
if hash hub 2>/dev/null; then
	alias git=hub
fi

alias gcv="git commit --verbose"

alias xkp="gen_pass"

if hash ag 2>/dev/null; then
	alias ag='ag --path-to-ignore $HOME/.agignore'
fi

# Encourage the use of NeoVim when possible
if [ "$EDITOR" = "nvim" ]; then
	alias vim="nvim"
fi


if hash gpg2 2>/dev/null; then
	alias gpg="gpg2"
fi

if [[ -x /usr/bin/vendor_perl/rename ]]; then
  alias rename="/usr/bin/vendor_perl/rename"
fi

if hash mosh 2>/dev/null; then
  alias mosh_leviathan="mosh --ssh='ssh -p 222' --port=60001 tstapler@Leviathan"
  alias mosh_absis="mosh --ssh='ssh -p 2222' --port=60000 tstapler@Absis"
fi
