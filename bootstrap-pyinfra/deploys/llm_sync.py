"""
Port of bootstrap/roles/llm-sync/tasks/main.yml — syncs Claude agents/
skills/commands and MCP config out to Gemini, OpenCode, Antigravity, and Pi,
then renders tiered Pi settings via the in-repo llm-sync tool
(stapler-scripts/llm-sync). The tool itself is hash-based and idempotent;
this just invokes it and prints its summary.
"""

import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError

from common import brew_prefix, dev_tools_path_env, shell_capture

LLM_SYNC_DIR = os.path.expanduser("~/dotfiles/stapler-scripts/llm-sync")
LLM_SYNC_MAIN = os.path.join(LLM_SYNC_DIR, "main.py")
# PluginSource._find_global() looks for a `plugins/` dir relative to the
# process's cwd, which is LLM_SYNC_DIR here, not the dotfiles repo root — so
# without this flag the dotfiles-bundled plugins (kibitzer, ponytail,
# core-hooks, dotfiles-hooks) are silently never found or installed.
DOTFILES_PLUGINS_DIR = os.path.expanduser("~/dotfiles/plugins")


@deploy("llm-sync")
def llm_sync() -> None:
    if not os.path.isfile(LLM_SYNC_MAIN):
        return

    code, output = shell_capture(
        f'cd {LLM_SYNC_DIR} && PATH="{dev_tools_path_env()}" {brew_prefix()}/bin/uv run main.py'
        f' --plugins-global-dir "{DOTFILES_PLUGINS_DIR}"'
    )
    if code != 0:
        raise DeployError(f"llm-sync failed: {output}")

    print(output)
