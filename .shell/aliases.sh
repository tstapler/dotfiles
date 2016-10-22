# Make some possibly destructive commands more interactive.
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
 
# Add some easy shortcuts for formatted directory listings and add a touch of color.
alias ll='ls -lF --color=auto'
alias la='ls -alF --color=auto'
alias ls='ls -F'

if hash hub 2>/dev/null; then
	alias git=hub
fi

function gen_pass {
xkcdpass -c 20 -d "-" -n 3 |
awk -v NUM=$(python -c "import random; print(random.randrange(0,10))") '{printf("%s-%d\n",$1,NUM)}'  |
python -c 'import sys; sys.stdout.write(sys.stdin.read().title())'
}

function ssh-switch {
	ssh-add -D
	ssh-add ~/.ssh/$1
}

function commited_files {
	if [[ $# -eq 0 ]]; then
		commits=1
	else
		commits=$1
	fi
		
	git log --pretty=format: --name-only -n $commits | sort | uniq | tr '\n' ' '
}

alias xkp='gen_pass'

# Encourage the use of NeoVim when possible
if [ "$EDITOR" = "nvim" ]; then
	alias vim='nvim'
fi


if hash gpg2 2>/dev/null; then
	alias gpg=gpg2
fi
