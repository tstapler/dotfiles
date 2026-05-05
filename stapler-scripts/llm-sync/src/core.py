import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

@dataclass(kw_only=True)
class SyncItem(ABC):
    """Base class for items that can be synced."""
    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[str] = None

    def get_hash(self) -> str:
        """Calculate a stable hash of the item's content and key metadata."""
        # Base components for the hash
        data = {
            "name": self.name,
            "description": self.description,
            "metadata": {k: v for k, v in self.metadata.items() if k != 'source_file'},
            "content": getattr(self, 'content', ''),
            "tools": getattr(self, 'tools', {})
        }
        # Serialize to stable JSON string
        json_data = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_data.encode('utf-8')).hexdigest()

# Files to ignore during discovery
IGNORED_NAMES = {'README', 'CLAUDE', 'LICENSE', 'CONTRIBUTING', '.DS_Store', 'package', 'pyproject', 'uv.lock'}

@dataclass(kw_only=True)
class Agent(SyncItem):
    """Universal representation of an LLM agent/subagent."""
    content: str  # The system prompt / instructions
    tools: Dict[str, bool] = field(default_factory=dict)

@dataclass(kw_only=True)
class Skill(SyncItem):
    """Legacy/directory-based LLM skill."""
    content: str
    tools: Dict[str, bool] = field(default_factory=dict)

@dataclass(kw_only=True)
class Command(SyncItem):
    """Universal representation of a CLI command."""
    content: str  # The command prompt/template

@dataclass
class MCPServer:
    """An MCP server configuration entry."""
    name: str
    # stdio transport
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    # http transport
    type: Optional[str] = None
    url: Optional[str] = None
    disabled: bool = False


@dataclass
class Plugin:
    """A Claude Code plugin loaded from a plugins/ directory."""
    name: str
    description: str
    version: str
    commands: List["Command"] = field(default_factory=list)
    skills: List["Skill"] = field(default_factory=list)
    # hooks: event_type -> list of hook entries (each entry has optional matcher + hooks list)
    hooks: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    source_dir: Optional[str] = None

class SyncSource(ABC):
    def load_agents(self) -> List[Agent]:
        """Load agents from the source."""
        return []
    
    def load_skills(self) -> List[Skill]:
        """Load skills from the source."""
        return []
    
    def load_commands(self) -> List[Command]:
        """Load commands from the source."""
        return []

class SyncTarget(ABC):
    def save_agents(self, agents: List[Agent], dry_run: bool = False, force: bool = False) -> int:
        """Save agents to the target."""
        return 0

    def save_skills(self, skills: List[Skill], dry_run: bool = False, force: bool = False) -> int:
        """Save skills to the target."""
        return 0
    
    def save_commands(self, commands: List[Command], dry_run: bool = False, force: bool = False) -> int:
        """Save commands to the target."""
        return 0
