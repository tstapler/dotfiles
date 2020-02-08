{ pkgs, ... }: {
  imports = [
    ./base.nix
  ];

  home.packages = [
     pkgs.gitAndTools.git-annex
     pkgs.gitAndTools.git-annex-remote-rclone
     pkgs.pdfgrep
     pkgs.ccid
     pkgs.pcsctools
     pkgs.python27Packages.htmltreediff
  ];
}
