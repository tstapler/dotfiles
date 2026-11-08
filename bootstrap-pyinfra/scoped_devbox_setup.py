"""One-off scoped deploy: tool setup requested for this dev workspace.
Not part of main.py — deliberately skips nix/secrets/sudo-mfa/fbg/claude/
ai_tools/pi/shell/asdf/fonts/github, which were not asked for here.
"""

from deploys.dotfiles import dotfiles
from deploys.homebrew import homebrew
from deploys.llm_sync import llm_sync
from deploys.overlays import overlays

homebrew()
dotfiles()
overlays()
llm_sync()
