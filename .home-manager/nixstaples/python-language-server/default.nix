{nixpkgs, ...}:
{
  nixpkgs.overlays = [
    (import ./overlay.nix)
  ];
}
