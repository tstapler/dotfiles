rm -rf ~/.vim/bundle

if [ -d ~/dotfiles ]; then
	TARGET="dotfiles"
else
	TARGET="stapler-config"
fi
~/$TARGET/stapler-scripts/install-scripts/dein-install.sh
python ~/$TARGET/stapler-linker/stapler_linker/linker.py
