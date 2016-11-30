if hash docker-machine 2>/dev/null; then
	# Export docker-machine environment variables
	eval $(docker-machine env default)
fi

alias hangoutscamerafix="sudo killall VCDAssistant"
