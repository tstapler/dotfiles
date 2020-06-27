# Skaardb tools
export VENV=local

export GOPRIVATE="github.com/Workiva/*"

alias ddev='pub run dart_dev'

OS="$(uname)"
case $OS in
	'Darwin')
	# Setup Groovy
  export GROOVY_HOME='/usr/local/opt/groovy/libexec'
  ;;
esac

export SBT_CREDENTIALS=$HOME/.sbt/.credentials

alias erasereset="workon sky; python tools/erase_reset_data.py --admin=tyler.stapler@workiva.com --password=a"

PATH="$PATH:$HOME/Workiva/onboarding-tools/bin"
PATH="$PATH:$HOME/Workiva/pss/scripts"

eval "$(docker run --rm drydock.workiva.net/workiva/skynet-cli:latest shell)"

EKS_CONFIG=$HOME/Workiva/EKS/kubeconfigs.yaml
if [ -f $EKS_CONFIG ] && [[ $KUBECONFIG != *$EKS_CONFIG* ]]; then
  echo $KUBECONFIG
  export KUBECONFIG="${KUBECONFIG:=$HOME/.kube/config}:$HOME/Workiva/EKS/kubeconfigs.yaml"
fi

