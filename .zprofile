# PATH is managed centrally in ~/.shell/exports.sh (sourced from ~/.zshrc).
# ~/.local/bin and ~/.poetry/bin are added there via pathadd, so no per-login
# PATH exports are needed here.


# Added by Antigravity CLI installer
[[ $OSTYPE == linux* ]] && export PATH="$HOME/.local/bin:$PATH"  # Linux-only: on macOS this path lives under /Users
