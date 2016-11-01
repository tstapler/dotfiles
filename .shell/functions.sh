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
		
	git log --pretty=format: --name-only -n $commits | sort | uniq | tr '\n' ' '; echo ''
}
