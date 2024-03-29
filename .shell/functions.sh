function gen_pass {
  local PYTHON_BIN
  for bin in python python3 python2; do
    if hash $bin 2>/dev/null; then
      PYTHON_BIN=$bin
      break
    fi
  done

  if ! hash xkcdpass 2>/dev/null; then
    echo Please install xkcd pass:
    echo $PYTHON_BIN -m pip install pipx
    echo pipx install xkcdpass
    return
  fi

  GEN_RANDOM_NUMBER="import random; print(random.randrange(0,10))"
  INPUT_TO_TITLE_CASE="import sys; sys.stdout.write(sys.stdin.read().title())"
  xkcdpass -c 20 -d "-" -n 3 |
  awk -v NUM=$($PYTHON_BIN -c "$GEN_RANDOM_NUMBER") '{printf("%s-%d\n",$1,NUM)}'  |
  $PYTHON_BIN -c "$INPUT_TO_TITLE_CASE"
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

function rnsp {
  if hash rename 2>/dev/null; then
    rename 's/ /_/g' "$@"
  else
    echo "Please install the perl-rename utility"
  fi
}

function fix_insecure_compaudit {
  compaudit | xargs chmod g-w
}

get_pip_private_url() {
  grep "@" $HOME/.pip/pip.conf | awk '{ print $3 }'
}

check_multi_arch(){
	ARCH=${ARCH?}
	local image_url=$1
	local image_name=$(echo $1 | sed 's%.*/\(.*$\)%\1%g' | tr ':/.' '_')
	mkdir -p $image_name && \
	
	# Download the contents of the image
	(cd $image_name && \
	(docker rm $image_name >/dev/null 2>&1 || true) && \
	docker create --name $image_name --platform linux/$ARCH $image_url >/dev/null && \
	(docker export $image_name | tar x) && \
	docker rm $image_name >/dev/null 2>&1) || return

	# Read the magix header for all of the files in the docker image and print the
	# architecture field.
	echo "Detected ELF files compiled for the following architectures:"
  find $image_name | xargs -n 300 file | awk -F',' '/ELF/{ print $2 }' | sort -u
}
