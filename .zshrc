# _____     _           ___ _             _         _        ____   _
#|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___   |_  /__| |_  _ _ __
#  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  _ / /(_-< ' \| '_/ _|
#  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)___/__/_||_|_| \__|
#      |__/                         |_|


# A prior Claude Code session (or vim, etc.) can exit without disabling
# terminal focus-reporting (DECSET 1004) or mouse-reporting (1000/1002/1003/
# 1006), leaving the terminal stuck streaming escape sequences into whatever
# reads the tty next. Reset them on every new shell so a fresh tab/pane never
# inherits a dirty state. https://github.com/anthropics/claude-code/issues/10375
printf '\e[?1004l\e[?1000l\e[?1002l\e[?1003l\e[?1006l'

# Plugins are sourced straight from the zplug checkout (~/.zplug/repos) in a
# fixed order instead of running `zplug check`/`zplug load` on every shell,
# which cost ~1s of forks and flock. Anything missing falls back to the full
# zplug flow below; `zplug` (install/update/...) is loaded on first use.
export ZPLUG_LOADFILE=$HOME/.zplug_packages.zsh
_zp=$HOME/.zplug/repos
_zp_plugins=(
  $_zp/willghatch/zsh-hooks/zsh-hooks.plugin.zsh
  $_zp/zsh-users/zsh-completions/zsh-completions.plugin.zsh
  $_zp/Tarrasch/zsh-autoenv/autoenv.plugin.zsh
  $_zp/zsh-users/zaw/zaw.plugin.zsh
  $_zp/robbyrussell/oh-my-zsh/lib/completion.zsh
  $_zp/robbyrussell/oh-my-zsh/plugins/kubectl/kubectl.plugin.zsh
  $_zp/robbyrussell/oh-my-zsh/lib/functions.zsh
  $_zp/robbyrussell/oh-my-zsh/plugins/aws/aws.plugin.zsh
  $_zp/aswitalski/oh-my-zsh-sensei-git-plugin/sensei-git.plugin.zsh
  $_zp/robbyrussell/oh-my-zsh/lib/git.zsh
  $_zp/robbyrussell/oh-my-zsh/plugins/git/git.plugin.zsh
  $_zp/djui/alias-tips/alias-tips.plugin.zsh
  $_zp/robbyrussell/oh-my-zsh/plugins/asdf/asdf.plugin.zsh
  $_zp/tarruda/zsh-autosuggestions/zsh-autosuggestions.plugin.zsh
  $_zp/zsh-users/zsh-syntax-highlighting/zsh-syntax-highlighting.plugin.zsh
  $_zp/zsh-users/zsh-history-substring-search/zsh-history-substring-search.plugin.zsh
  $_zp/romkatv/powerlevel10k/powerlevel10k.zsh-theme
  $_zp/romkatv/powerlevel10k/powerlevel9k.zsh-theme
)

_zp_ok=1
for _zp_file in $_zp_plugins; do [[ -r $_zp_file ]] || { _zp_ok=0; break; }; done

if (( _zp_ok )); then
  # Same ZSH/ZSH_CACHE_DIR zplug exports before loading oh-my-zsh files
  export ZSH=$_zp/robbyrussell/oh-my-zsh ZSH_CACHE_DIR=$_zp/robbyrussell/oh-my-zsh/cache/
  path=($HOME/.zplug/bin $path)
  fpath=($_zp/zsh-users/zsh-completions/src $ZSH/plugins/httpie $HOME/.zplug/misc/completions $fpath)

  # zplug exports these from .zplug_packages.zsh on every load
  case $CPUTYPE in x86_64) ARCHITECTURE_NAME=amd64 ;; *) ARCHITECTURE_NAME=$CPUTYPE ;; esac
  export ARCHITECTURE_NAME PLATFORM_ARCHITECTURE_GLOB="*${OSTYPE%%[-0-9.]*}*$ARCHITECTURE_NAME*"

  # One compinit: trust the dump (-C) and rebuild it at most once a day
  autoload -Uz compinit
  _zp_dump=( $HOME/.zplug/zcompdump(N.mh-24) )
  if (( $#_zp_dump )); then compinit -C -d $HOME/.zplug/zcompdump; else compinit -d $HOME/.zplug/zcompdump; fi
  unset _zp_dump

  # git.plugin.zsh forks `git version` on every shell (~0.26s under endpoint-security
  # exec scans); answer it from a cache keyed on the git binary instead.
  () {
    local exe=${commands[git]} dir=${XDG_CACHE_HOME:-$HOME/.cache}/shell-eval; local -A st
    [[ -n $exe ]] && zmodload -F zsh/stat b:zstat && zstat -H st -- $exe || return
    local f=$dir/git-version.${st[mtime]}-${st[size]}
    [[ -s $f ]] || { mkdir -p $dir && command git version >| $f 2>/dev/null || return; }
    _zp_git_version=$(<$f)
    git() { if [[ $1 == version ]]; then print -r -- $_zp_git_version; else command git "$@"; fi }
  }

  # zplug sent plugin stderr to its own log; keep shells quiet the same way
  for _zp_file in $_zp_plugins; do source $_zp_file 2>/dev/null; done
  (( $+functions[git] )) && unfunction git
  unset _zp_git_version
  setopt prompt_subst  # zplug does this when loading a theme

  zplug() {
    unfunction zplug
    source $HOME/.zplug/init.zsh && zplug "$@"
  }
else
  # Check if zplug is installed
  if [[ ! -d ~/.zplug ]]; then
    # Ignore the system .gitconfig in case it tries to force SSH
    GIT_CONFIG_NOSYSTEM=1 git clone https://github.com/tstapler/zplug $HOME/.zplug
  fi

  source $HOME/.zplug/init.zsh

  # Install packages that have not been installed yet
  if ! zplug check --verbose; then
      printf "Install? [y/N]: "
      if read -q; then
          echo; zplug install
      else
          echo
      fi
  fi

  # Then, source plugins and add commands to $PATH
  zplug load
fi
unset _zp _zp_plugins _zp_ok _zp_file

# Load the zshell mv module
autoload -U zmv

# Add line editing
autoload -Uz edit-command-line
zle -N edit-command-line

# Add Completions
autoload -U bashcompinit && bashcompinit

export HISTFILE=$HOME/.zsh_history

# Appends every command to the history file once it is executed
setopt inc_append_history
export HISTTIMEFORMAT="[%F %T] "
# How many lines to keep in memory
export HISTSIZE=10000
# How many lines to keep in the history file
export SAVEHIST=100000

# Add the time of the history command
setopt inc_append_history_time
# Reloads the history whenever you use it
setopt share_history

# Dont search for dupes when using Ctrl+R
setopt HIST_FIND_NO_DUPS

# Only save unique commands
setopt HIST_IGNORE_ALL_DUPS

setopt extendedglob

# Allow comments in interactive shells to mimic ksh, sh, bash behavior
setopt interactivecomments

# Vim Mode
bindkey -v

# Emacs like keybindings in insert mode
bindkey -M viins '^P' history-substring-search-up
bindkey -M viins '^N' history-substring-search-down
bindkey -M viins '^?' backward-delete-char
bindkey -M viins '^h' backward-delete-char
bindkey -M viins '^w' backward-kill-word
bindkey -M viins '^a' beginning-of-line
bindkey -M viins '^e' end-of-line
bindkey -M viins '^x^e' edit-command-line
bindkey -M vicmd '^x^e' edit-command-line

# History subzmodload zsh/terminfo
bindkey "$terminfo[kcuu1]" history-substring-search-up
bindkey "$terminfo[kcud1]" history-substring-search-down
bindkey -M vicmd 'k' history-substring-search-up
bindkey -M vicmd 'j' history-substring-search-down

bindkey '^R' zaw-history


export ZPLUG_FILTER=fzy:fzf-tmux:fzf:peco:percol:zaw

# pathadd is defined in ~/.shell/exports.sh (sourced below).

if [[ $OSTYPE == linux* && -x "/home/linuxbrew/.linuxbrew/bin/brew" ]]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Language managers (RVM, NVM, PYENV, ...)
source $HOME/.shell/languages.sh

if hash keychain 2>/dev/null; then
	# Without --eval keychain prints nothing, so only its side effects matter
	# (agent running, ~/.keychain/* refreshed): run it off the startup path.
	keychain --quick --quiet --noask >/dev/null 2>&1 &!
fi

# Prompt Config
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Export Environment Variables
source $HOME/.shell/exports.sh

# Aliases
source $HOME/.shell/aliases.sh

# Utility Functions
source $HOME/.shell/functions.sh

# Machine Specific Configuration
if [[ -f $HOME/.shell/local.sh ]]; then
	source $HOME/.shell/local.sh
fi

# Workiva specific stuff
if [[ "$WORKIVA" == true ]] ; then
	source $HOME/.shell/workiva.sh
fi

# By operating system
: ${OS:=$(uname -a)}  # normally already set by .zshenv
case $OS in
	*Darwin*)
		source ~/.shell/osx.sh
	;;
esac

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
[[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && export PATH="$HOME/.local/bin:${PATH}"  # concur CLI
[[ ":$PATH:" != *":$HOME/.nopctl/bin:"* ]] && export PATH="$HOME/.nopctl/bin:${PATH}"
[[ ":$PATH:" != *":$HOME/.nopctl/bin:"* ]] && export PATH="$HOME/.nopctl/bin:${PATH}"
[[ ":$PATH:" != *":$HOME/.nopctl/bin:"* ]] && export PATH="$HOME/.nopctl/bin:${PATH}"
[[ ":$PATH:" != *":$HOME/.nopctl/bin:"* ]] && export PATH="$HOME/.nopctl/bin:${PATH}"


# Added by Antigravity CLI installer
[[ $OSTYPE == linux* ]] && export PATH="$HOME/.local/bin:$PATH"  # Linux-only: on macOS this path lives under /Users
