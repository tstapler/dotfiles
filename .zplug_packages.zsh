# Let zplug manage itself
zplug "zplug/zplug", hook-build:'zplug --self-manage'

zplug "willghatch/zsh-hooks"

# Theme
export TERM="xterm-256color"
zplug "bhilburn/powerlevel9k", as:theme

# Plugins
zplug "zsh-users/zsh-completions"
zplug "Tarrasch/zsh-autoenv"
zplug "b4b4r07/enhancd", use:"init.sh"
zplug "zsh-users/zaw"

zplug "Schnouki/git-annex-zsh-completion"
zplug "greymd/docker-zsh-completion"
zplug "lib/completion", from:oh-my-zsh
zplug "plugins/httpie", from:oh-my-zsh
zplug "aswitalski/oh-my-zsh-sensei-git-plugin"
zplug "djui/alias-tips"

# The file searchers

case $(uname) in
	Darwin) 
		BIN_ARCH=darwin
		;;
	*)
		BIN_ARCH=linux
		;;
esac

zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*$BIN_ARCH*_amd64*"

zplug "peco/peco", as:command, from:gh-r, rename-to:peco, use:"*$BIN_ARCH*64*"
zplug "clvv/fasd", as:command 
zplug "stedolan/jq", \
    from:gh-r, \
    as:command, \
    rename-to:jq

# Suggestions
zplug "tarruda/zsh-autosuggestions"
zplug "zsh-users/zsh-syntax-highlighting"
zplug "zsh-users/zsh-history-substring-search"

