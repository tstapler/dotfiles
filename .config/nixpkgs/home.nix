{ pkgs, ... }:

{
  home.packages = [
    pkgs.crystal
    pkgs.fzf
    pkgs.fzy
    pkgs.gettext
    pkgs.htop
    pkgs.jq
    pkgs.lnav
    pkgs.neovim
    pkgs.peco
    pkgs.httpie
    pkgs.rclone
  ];

 programs.home-manager = {
    enable = true;
    path = "https://github.com/rycee/home-manager/archive/master.tar.gz";
  };
}
