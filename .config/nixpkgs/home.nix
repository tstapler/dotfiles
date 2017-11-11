{ pkgs, ... }:

{
  home.packages = [
    pkgs.crystal
    pkgs.fasd
    pkgs.fzf
    pkgs.fzy
    pkgs.htop
    pkgs.jq
    pkgs.lnav
    pkgs.neovim
    pkgs.peco
    pkgs.httpie
  ];

  services.gpg-agent = {
    enable = true;
    defaultCacheTtl = 1800;
    enableSshSupport = true;
  };

 programs.home-manager = {
    enable = true;
    path = "https://github.com/rycee/home-manager/archive/master.tar.gz";
  };
}
