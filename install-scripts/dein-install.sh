curl https://raw.githubusercontent.com/Shougo/dein.vim/master/bin/installer.sh > installer.sh
sh ./installer.sh ~/.vim/bundle
rm installer.sh
cd ~/.config/nvim
ln -s ~/.vimrc init.vim

