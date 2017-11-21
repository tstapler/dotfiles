
# Theme
export TERM="xterm-256color"
zplug "bhilburn/powerlevel9k", as:theme

# Plugins
zplug "zsh-users/zsh-completions"
zplug "Tarrasch/zsh-autoenv"
zplug "b4b4r07/enhancd", use:"init.sh"
# zplug "zsh-users/zaw"
# zplug "clvv/fasd", as:command

zplug "aswitalski/oh-my-zsh-sensei-git-plugin"

# Suggestions
# zplug "tarruda/zsh-autosuggestions"
zplug "djui/alias-tips"

# zplug "zsh-users/zsh-history-substring-search"

# Set the priority when loading
# e.g., zsh-syntax-highlighting must be loaded
# after executing compinit command and sourcing other plugins
# (If the defer tag is given 2 or above, run after compinit command)
# zplug "zsh-users/zsh-syntax-highlighting", defer:2

# Let zplug manage itself
zplug "zplug/zplug", hook-build:'zplug --self-manage'

