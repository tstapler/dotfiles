# .zshenv runs for every zsh (scripts included): skip the uname fork on macOS
case $OSTYPE in darwin*) OS=Darwin ;; *) OS=`uname -a` ;; esac

case $OS in
  '\1#-Microsoft')
    unsetopt BG_NICE
    ;;
esac
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
