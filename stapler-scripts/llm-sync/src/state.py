import json
from pathlib import Path
from typing import Dict, Optional, Any

class SyncStateManager:
    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or Path.home() / ".config" / "llm-sync" / "state.json"
        self.state: Dict[str, Dict[str, str]] = self._load()

    def _load(self) -> Dict[str, Dict[str, str]]:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def save(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, sort_keys=True)

    def get_hash(self, direction: str, target_name: str, item_type: str, item_name: str) -> Optional[str]:
        """
        direction: 'to-target' or 'from-target'
        target_name: 'GeminiTarget', 'OpenCodeTarget', etc.
        item_type: 'agents', 'skills', 'commands'
        """
        key = f"{direction}:{target_name}:{item_type}"
        return self.state.get(key, {}).get(item_name)

    def set_hash(self, direction: str, target_name: str, item_type: str, item_name: str, hash_val: str):
        key = f"{direction}:{target_name}:{item_type}"
        if key not in self.state:
            self.state[key] = {}
        self.state[key][item_name] = hash_val
