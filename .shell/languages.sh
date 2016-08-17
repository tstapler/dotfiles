
export NVM_DIR="/home/tstapler/.nvm"
if [[ -d $NVM_DIR ]]; then
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm
fi

# Load .NET version manager
if [[ -d "~/.dnx" ]]; then
[ -s "/home/tstapler/.dnx/dnvm/dnvm.sh" ] && . "/home/tstapler/.dnx/dnvm/dnvm.sh" # Load dnvm
fi
