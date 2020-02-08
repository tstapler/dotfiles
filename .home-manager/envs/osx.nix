{ pkgs, ... }: 
let hmpkgs =  import <hmpkgs>;
in {


  imports = [
    ./base.nix
  ];

  home.packages = [
  ];
}
