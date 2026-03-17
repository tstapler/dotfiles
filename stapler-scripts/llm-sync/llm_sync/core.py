from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

@dataclass(kw_only=True)
class SyncItem(ABC):
    """Base class for items that can be synced."""
    name: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[str] = None

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
