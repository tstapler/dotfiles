if [ ! -d /usr/local/share/wemux ]; then
    echo "Installing tmux/wemux"
    sudo git clone git://github.com/zolrath/wemux.git /usr/local/share/wemux
    sudo ln -sv /usr/local/share/wemux/wemux /usr/local/bin/wemux
    sudo cp -rvs $DIR/wemux.conf /usr/local/etc/wemux.conf
fi
