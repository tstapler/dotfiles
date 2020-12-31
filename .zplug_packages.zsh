# Let zplug manage itself
zplug "zplug/zplug", hook-build:'zplug --self-manage'

zplug "willghatch/zsh-hooks"

# Theme
export TERM="xterm-256color"
zplug "romkatv/powerlevel10k", as:theme, depth:1

# Plugins
zplug "zsh-users/zsh-completions"
zplug "Tarrasch/zsh-autoenv"
zplug "b4b4r07/enhancd", use:"init.sh"

# ZSH completion from various sources
zplug "zsh-users/zaw"

# Command line completion engine
zplug "clvv/fasd", as:command

zplug "lib/completion", from:oh-my-zsh
zplug "plugins/httpie", from:oh-my-zsh
zplug "plugins/kubectl", from:oh-my-zsh
# AWS completion is broken at the moment
# https://github.com/aws/aws-cli/issues/4950
# zplug "plugins/aws", from:oh-my-zsh
zplug "aswitalski/oh-my-zsh-sensei-git-plugin"
zplug "plugins/git", from:oh-my-zsh
zplug "djui/alias-tips"
zplug "plugins/asdf", from:oh-my-zsh

# The file searchers

case $(uname) in
	Darwin) 
		BIN_ARCH=darwin
		zplug "plugins/osx", from:oh-my-zsh
		;;
	*)
		BIN_ARCH=linux
		;;
esac

zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*$BIN_ARCH*_amd64*"


# Suggestions
zplug "tarruda/zsh-autosuggestions"
zplug "zsh-users/zsh-syntax-highlighting"
zplug "zsh-users/zsh-history-substring-search"

