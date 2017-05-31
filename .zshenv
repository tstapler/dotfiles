OS=`uname -a`

case $OS in
  '\1#-Microsoft')
    unsetopt BG_NICE
    ;;
esac
