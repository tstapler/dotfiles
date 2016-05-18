# Make some possibly destructive commands more interactive.
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
 
# Add some easy shortcuts for formatted directory listings and add a touch of color.
alias ll='ls -lF --color=auto'
alias la='ls -alF --color=auto'
alias ls='ls -F'

gen_pass () {
xkcdpass -c 5 -d "-" -n 3 |
awk -v NUM=$(echo $RANDOM % 10 | bc) '{printf("%s-%d\n",$1,NUM)}'
}


alias xkp='gen_pass'

# Encourage the use of NeoVim when possible
if [ "$EDITOR" = "nvim" ]; then
	alias vim='nvim'
fi

