{ pkgs, ... }:{

  imports = [
    ../nixstaples
  ];

  home.packages = [
    pkgs.ag
    pkgs.aspell
    pkgs.aspellDicts.en
    pkgs.automake
    pkgs.coreutils
    pkgs.crystal
    pkgs.ctags
    pkgs.diffutils
    pkgs.figlet
    pkgs.fontconfig
    pkgs.fzf
    pkgs.fzy
    pkgs.gdb
    pkgs.gettext
    pkgs.git
    pkgs.gitAndTools.hub
    pkgs.gnupg1
    pkgs.gnused
    pkgs.kubernetes-helm
    pkgs.htop
    pkgs.httpie
    pkgs.hunspell
    pkgs.hunspellDicts.en-us
    pkgs.jq
    pkgs.keybase
    pkgs.keychain
    pkgs.languagetool
    pkgs.lnav
    pkgs.ncat
    pkgs.neovim
    pkgs.nmap
    pkgs.opensc
    pkgs.pandoc
    pkgs.patchutils
    pkgs.peco
    pkgs.powerline-fonts
    pkgs.powerline-fonts
    pkgs.proselint
    pkgs.pypi2nix
    pkgs.python27Packages.flake8
    pkgs.python27Packages.grip
    pkgs.python27Packages.isort
    pkgs.python27Packages.neovim
    pkgs.python27Packages.pandocfilters
    pkgs.python36Packages.neovim
    pkgs.python36Packages.powerline
    pkgs.ranger
    pkgs.rclone
    pkgs.ripgrep
    pkgs.shellcheck
    pkgs.tmux
    pkgs.toilet
    pkgs.tree
    pkgs.valgrind
    pkgs.vim-vint
    pkgs.watch
    pkgs.watchman
  ];

  fonts.fontconfig.enableProfileFonts = true;
}
