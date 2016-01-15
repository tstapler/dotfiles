if [ ! -d ~/.vim/bundle/neobundle.vim ]; then
    echo "Installing neobundle, and related vim files"
    if [ -z "${VIMRUNTIME+x}" ];
    then 
        #Install Neobundle
        if [ ! -d ~/.vim/bundle ]; then
        mkdir -p ~/.vim/bundle
        fi
        git clone https://github.com/Shougo/neobundle.vim ~/.vim/bundle/neobundle.vim
    else
        echo "You need vim installed to install vim"
    fi
fi
