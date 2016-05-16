curl https://raw.githubusercontent.com/Shougo/dein.vim/master/bin/installer.sh > installer.sh
sh ./installer.sh ~/.vim/bundle
rm installer.sh
if [! -d "~/.config" ]; then
	mkdir ~/.config/nvim
fi
cd ~/.config/nvim
ln -s ~/.vimrc init.vim

