# Load N (Node.js the version manager)
export N_PREFIX="$HOME/n"; 

if [ ! -d  "$N_PREFIX" ]; then
  echo "Installing n (The Node.js version manager)"

  # Remove old NVM install if present
  NVM_DIR="$HOME/.nvm" 
  if [[ -d "$NVM_DIR" ]]; then
      rm -rf "$NVM_DIR"
  fi
  curl -L https://git.io/n-install | bash -s -- -y -n
fi

if [ -d "$N_PREFIX" ]; then
    [[ :$PATH: == *":$N_PREFIX/bin:"*  ]] || PATH+=":$N_PREFIX/bin" 
    if hash npm 2>/dev/null; then
      NPM_CONFIG_PREFIX="$HOME/.npm-global"
      npm config set prefix "$NPM_CONFIG_PREFIX"
      [[ :$PATH: == *":$NPM_CONFIG_PREFIX/bin:"*  ]] \
        || PATH+=":$NPM_CONFIG_PREFIX/bin" 
    fi
fi


# Load .NET version manager
DNX_DIR="$HOME/.dnx"
if [[ -d "$DNX_DIR" ]]; then
  DNX_SCRIPT="$DNX_DIR/dnvm/dnvm.sh"
[ -s "$DNX_SCRIPT" ] && . "$DNX_SCRIPT" # Load dnvm
fi

# Load virtualenvwrapper
VENV_WRAP_SH="virtualenvwrapper.sh"

if command -v $VENV_WRAP_SH >/dev/null 2>&1; then
	if [[ $WORKIVA == true ]]; then
		export PROJECT_HOME=$HOME/Workiva
	else
		export PROJECT_HOME=$HOME/Programming/Python
	fi
  mkdir -p "$PROJECT_HOME"
	export WORKON_HOME=$HOME/.virtualenvs
  source "$(which $VENV_WRAP_SH)"
fi

# Load gvm
GVM_DIR="$HOME/.gvm"
GVM_SCRIPT="$GVM_DIR/scripts/gvm"

if [[ ! -d "$GVM_DIR" ]]; then
  curl -s -S -L "https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer" | zsh
fi

if [[ -x "$GVM_SCRIPT" ]]; then
 . "$GVM_SCRIPT" 
 fi

# Load rbenv

if hash rbenv 2>/dev/null; then
  eval "$(rbenv init -)"
  IFS=:
    for GEM_PATH in $(gem env gempath); do
      PATH="$PATH:$GEM_PATH/bin"
    done
  IFS=" "
fi



NIX_SCRIPT="$HOME/.nix-profile/etc/profile.d/nix.sh"

if [[ ! -f "$NIX_SCRIPT" ]]; then
  echo "Installing Nix using install script"
  curl https://nixos.org/nix/install | sh
  echo "Setting proper permissions"
  mkdir -m 0755 -p /nix/var/nix/{profiles,gcroots}/per-user/$USER
fi

if [[ -f "$NIX_SCRIPT" ]]; then
  source "$NIX_SCRIPT"
  if ! hash home-manager 2>/dev/null; then
# Export nix homemanager config for use in bootstrap
    export HM_PATH=https://github.com/rycee/home-manager/archive/master.tar.gz
    cfgcaddy link
    nix-shell $HM_PATH -A install --run 'home-manager switch'
  fi
fi
