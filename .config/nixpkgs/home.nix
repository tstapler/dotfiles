{ pkgs, ... }:

{
  home.packages = [
    # pkgs.gitAndTools.git-annex
    # pkgs.gitAndTools.git-annex-remote-rclone
    # pkgs.pdfgrep
    pkgs.ag
    pkgs.automake
    pkgs.ccid
    pkgs.crystal
    pkgs.ctags
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
    pkgs.jq
    pkgs.keybase
    pkgs.keychain
    pkgs.lnav
    pkgs.ncat
    pkgs.neovim
    pkgs.nmap
    pkgs.opensc
    pkgs.pandoc
    pkgs.patchutils
    pkgs.pcsctools
    pkgs.peco
    pkgs.python27Packages.flake8
    pkgs.python27Packages.grip
    pkgs.python27Packages.htmltreediff
    pkgs.python27Packages.isort
    pkgs.python27Packages.neovim
    pkgs.python27Packages.pandocfilters
    pkgs.python36Packages.neovim
    pkgs.ranger
    pkgs.rclone
    pkgs.ripgrep
    pkgs.shellcheck
    pkgs.tmux
    pkgs.toilet
    pkgs.tree
    pkgs.valgrind
  ];

 programs.home-manager = {
    enable = true;
    path = "https://github.com/rycee/home-manager/archive/master.tar.gz";
  };
}
