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

function gpg_agent_fix {
	if ! test -v GPG_AGENT_INFO; then
		if gpg-agent 2>/dev/null; then
			if test -e /tmp/.gpg-agent-$USER/env; then
				. /tmp/.gpg-agent-$USER/env
			elif test -e ~/.gpg-agent-info; then
				. ~/.gpg-agent-info
			else
				echo 'A gpg agent is running, but we cannot find its socket info because'
				echo 'the GPG_AGENT_INFO env var is not set and gpg agent info has not been'
				echo 'written to any expected location. Cannot continue. Please report this'
				echo 'issue for investigation.'
				exit 5
			fi
		else
			mkdir /tmp/.gpg-agent-$USER
			chmod 700 /tmp/.gpg-agent-$USER
			gpg-agent --daemon --write-env-file /tmp/.gpg-agent-$USER/env
			. /tmp/.gpg-agent-$USER/env
		fi
		# The env file doesn't include an export statement
		export GPG_AGENT_INFO
	else
		if ! gpg-agent 2>/dev/null; then
			echo 'GPG_AGENT_INFO is set, but cannot connect to the agent.'
			echo 'Unsure how to proceed, so aborting execution. Please report this'
			echo 'issue for investigation.'
			exit 5
		fi
	fi
}

function arch_fix_audio_quality {
	pacmd set-card-profile 2 a2dp_sink
}
