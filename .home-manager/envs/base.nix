{ pkgs, ... }:{
  home.packages = [
    pkgs.ag
    pkgs.aspell
    pkgs.aspellDicts.en
    pkgs.automake
    pkgs.crystal
    pkgs.ctags
    pkgs.coreutils
    pkgs.diffutils
    pkgs.figlet
    pkgs.fzf
    pkgs.fzy
    pkgs.gdb
    pkgs.gettext
    pkgs.git
    pkgs.gitAndTools.hub
    pkgs.gnupg1
    pkgs.gnused
    pkgs.htop
    pkgs.httpie
    pkgs.hunspell
    pkgs.hunspellDicts.en-us
    pkgs.jq
    pkgs.keybase
    pkgs.keychain
    pkgs.lnav
    pkgs.ncat
    pkgs.neovim
    pkgs.nmap
    pkgs.opensc
    pkgs.proselint
    pkgs.pandoc
    pkgs.patchutils
    pkgs.peco
    pkgs.python27Packages.flake8
    pkgs.python27Packages.grip
    pkgs.python27Packages.isort
    pkgs.python27Packages.neovim
    pkgs.python27Packages.pandocfilters
    pkgs.python36Packages.neovim
    pkgs.python36Packages.powerline
    pkgs.powerline-fonts
    pkgs.ranger
    pkgs.rclone
    pkgs.ripgrep
    pkgs.shellcheck
    pkgs.tmux
    pkgs.toilet
    pkgs.tree
    pkgs.watch
    pkgs.watchman
    pkgs.valgrind
    pkgs.vim-vint
  ];

  fonts.fontconfig.enableProfileFonts = true;
  manual.manpages.enable = false;

}
