# PATH is managed centrally in ~/.shell/exports.sh (sourced from ~/.zshrc).
# ~/.local/bin and ~/.poetry/bin are added there via pathadd, so no per-login
# PATH exports are needed here.


# Added by Antigravity CLI installer
[[ "$(uname)" == Linux ]] && export PATH="/home/tstapler/.local/bin:$PATH"  # macOS /home is autofs: every PATH lookup spawns od_user_homes
