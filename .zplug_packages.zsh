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

zplug "lib/completion", from:oh-my-zsh
zplug "plugins/httpie", from:oh-my-zsh
zplug "plugins/kubectl", from:oh-my-zsh
zplug "plugins/aws", from:oh-my-zsh
zplug "aswitalski/oh-my-zsh-sensei-git-plugin"
zplug "plugins/git", from:oh-my-zsh
zplug "djui/alias-tips"
zplug "plugins/asdf", from:oh-my-zsh

# The file searchers

case $(uname) in
	Darwin) 
		PLATFORM_NAME=darwin
		zplug "plugins/osx", from:oh-my-zsh
		;;
	*)
		PLATFORM_NAME=linux
		;;
esac

# some machines do not have the arch command
architecture=$(arch 2>/dev/null || echo "x86_64")
case $architecture in
	x86_64)
		ARCHITECTURE_NAME=amd64
		PLATFORM_ARCHITECTURE_GLOB="*$PLATFORM_NAME*$ARCHITECTURE_NAME*"
		zplug "MichaelMure/git-bug", as:command, from:gh-r,  rename-to:git-bug, use:"$PLATFORM_ARCHITECTURE_GLOB"
		RG_GLOB="*$architecture*$PLATFORM_NAME*"
		;;
	*)
		ARCHITECTURE_NAME=$(arch)
		PLATFORM_ARCHITECTURE_GLOB="*$PLATFORM_NAME*$ARCHITECTURE_NAME*"
		RG_GLOB="*$ARCHITECTURE_NAME*$PLATFORM_NAME*"
		;;
esac
export ARCHITECTURE_NAME
export PLATFORM_ARCHITECTURE_GLOB

# Command line completion engine
zplug "clvv/fasd", as:command

# Fuzzy finder
zplug "junegunn/fzf", as:command, from:gh-r, rename-to:fzf, use:"$PLATFORM_ARCHITECTURE_GLOB"


# Suggestions
zplug "tarruda/zsh-autosuggestions"
zplug "zsh-users/zsh-syntax-highlighting"
zplug "zsh-users/zsh-history-substring-search"
