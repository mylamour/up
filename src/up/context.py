"""Context window management for AI sessions.

Tracks estimated token usage and provides warnings when approaching limits.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# Token estimation constants (rough estimates)
CHARS_PER_TOKEN = 4  # Average characters per token
CODE_MULTIPLIER = 1.3  # Code typically uses more tokens
DEFAULT_BUDGET = 100_000  # Default context budget in tokens


@dataclass
class ContextEntry:
    """A single context entry (file read, message, etc.)."""
    
    timestamp: str
    entry_type: str  # 'file', 'message', 'tool_output'
    source: str  # File path or description
    estimated_tokens: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContextBudget:
    """Tracks context window usage."""
    
    budget: int = DEFAULT_BUDGET
    warning_threshold: float = 0.8  # Warn at 80%
    critical_threshold: float = 0.9  # Critical at 90%
    entries: list[ContextEntry] = field(default_factory=list)
    total_tokens: int = 0
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def usage_percent(self) -> float:
        """Get usage as percentage."""
        return (self.total_tokens / self.budget) * 100 if self.budget > 0 else 0
    
    @property
    def remaining_tokens(self) -> int:
        """Get remaining token budget."""
        return max(0, self.budget - self.total_tokens)
    
    @property
    def status(self) -> str:
        """Get status: OK, WARNING, or CRITICAL."""
        ratio = self.total_tokens / self.budget if self.budget > 0 else 0
        if ratio >= self.critical_threshold:
            return "CRITICAL"
        elif ratio >= self.warning_threshold:
            return "WARNING"
        return "OK"
    
    def to_dict(self) -> dict:
        return {
            "budget": self.budget,
            "total_tokens": self.total_tokens,
            "remaining_tokens": self.remaining_tokens,
            "usage_percent": round(self.usage_percent, 1),
            "status": self.status,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "session_start": self.session_start,
            "entry_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries[-20:]],  # Last 20 entries
        }


def estimate_tokens(text: str, is_code: bool = False) -> int:
    """Estimate token count for text.
    
    Args:
        text: The text to estimate
        is_code: Whether the text is code (uses higher multiplier)
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Basic character-based estimation
    base_tokens = len(text) / CHARS_PER_TOKEN
    
    # Apply code multiplier if needed
    if is_code:
        base_tokens *= CODE_MULTIPLIER
    
    return int(base_tokens)


def estimate_file_tokens(path: Path) -> int:
    """Estimate tokens for a file.
    
    Args:
        path: Path to the file
        
    Returns:
        Estimated token count
    """
    if not path.exists():
        return 0
    
    try:
        content = path.read_text()
    except (UnicodeDecodeError, PermissionError):
        return 0
    
    # Detect if it's code
    code_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java',
        '.c', '.cpp', '.h', '.hpp', '.rb', '.sh', '.bash', '.zsh'
    }
    is_code = path.suffix.lower() in code_extensions
    
    return estimate_tokens(content, is_code)


class ContextManager:
    """Manages context window budget for AI sessions.
    
    Now uses the unified StateManager for storage while maintaining
    backwards compatibility with the existing API.
    """
    
    def __init__(
        self,
        workspace: Optional[Path] = None,
        budget: int = DEFAULT_BUDGET
    ):
        self.workspace = workspace or Path.cwd()
        # Old location for migration
        self._old_state_file = self.workspace / ".claude" / "context_budget.json"
        # New unified state
        self._use_unified_state = True
        self.budget = ContextBudget(budget=budget)
        self._load_state()
    
    def _load_state(self) -> None:
        """Load state from unified state manager or migrate from old file."""
        try:
            from up.core.state import get_state_manager
            manager = get_state_manager(self.workspace)
            ctx = manager.state.context
            
            # Sync from unified state
            self.budget.budget = ctx.budget
            self.budget.total_tokens = ctx.total_tokens
            self.budget.warning_threshold = ctx.warning_threshold
            self.budget.critical_threshold = ctx.critical_threshold
            self.budget.session_start = ctx.session_start
            
            # Convert entries
            self.budget.entries = [
                ContextEntry(**e) if isinstance(e, dict) else e
                for e in ctx.entries
            ]
            
        except ImportError:
            # Fallback to old file-based storage
            self._use_unified_state = False
            self._load_state_legacy()
    
    def _load_state_legacy(self) -> None:
        """Load state from old file location (for backwards compatibility)."""
        if self._old_state_file.exists():
            try:
                data = json.loads(self._old_state_file.read_text())
                self.budget.budget = data.get("budget", DEFAULT_BUDGET)
                self.budget.total_tokens = data.get("total_tokens", 0)
                self.budget.session_start = data.get("session_start", datetime.now().isoformat())
                entries_data = data.get("entries", [])
                self.budget.entries = [
                    ContextEntry(**e) for e in entries_data
                ]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
    
    def _save_state(self) -> None:
        """Save state to unified state manager."""
        if self._use_unified_state:
            try:
                from up.core.state import get_state_manager
                manager = get_state_manager(self.workspace)
                
                # Sync to unified state
                manager.state.context.budget = self.budget.budget
                manager.state.context.total_tokens = self.budget.total_tokens
                manager.state.context.warning_threshold = self.budget.warning_threshold
                manager.state.context.critical_threshold = self.budget.critical_threshold
                manager.state.context.session_start = self.budget.session_start
                manager.state.context.entries = [
                    e.to_dict() if hasattr(e, 'to_dict') else e
                    for e in self.budget.entries[-50:]  # Keep last 50
                ]
                
                manager.save()
                return
            except ImportError:
                pass
        
        # Fallback to old file-based storage
        self._old_state_file.parent.mkdir(parents=True, exist_ok=True)
        self._old_state_file.write_text(json.dumps(self.budget.to_dict(), indent=2))
    
    def record_file_read(self, path: Path) -> ContextEntry:
        """Record a file being read into context.
        
        Args:
            path: Path to the file read
            
        Returns:
            The context entry created
        """
        tokens = estimate_file_tokens(path)
        entry = ContextEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="file",
            source=str(path),
            estimated_tokens=tokens
        )
        self.budget.entries.append(entry)
        self.budget.total_tokens += tokens
        self._save_state()
        return entry
    
    def record_message(self, message: str, role: str = "user") -> ContextEntry:
        """Record a message in context.
        
        Args:
            message: The message content
            role: 'user' or 'assistant'
            
        Returns:
            The context entry created
        """
        tokens = estimate_tokens(message)
        entry = ContextEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="message",
            source=f"{role} message",
            estimated_tokens=tokens
        )
        self.budget.entries.append(entry)
        self.budget.total_tokens += tokens
        self._save_state()
        return entry
    
    def record_tool_output(self, tool: str, output_size: int) -> ContextEntry:
        """Record tool output in context.
        
        Args:
            tool: Name of the tool
            output_size: Size of output in characters
            
        Returns:
            The context entry created
        """
        tokens = estimate_tokens("x" * output_size)  # Rough estimate
        entry = ContextEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="tool_output",
            source=f"tool:{tool}",
            estimated_tokens=tokens
        )
        self.budget.entries.append(entry)
        self.budget.total_tokens += tokens
        self._save_state()
        return entry
    
    def get_status(self) -> dict:
        """Get current context budget status.
        
        Returns:
            Status dictionary with usage info
        """
        return self.budget.to_dict()
    
    def check_budget(self) -> tuple[str, str]:
        """Check budget and return status with message.
        
        Returns:
            Tuple of (status, message)
        """
        status = self.budget.status
        usage = self.budget.usage_percent
        remaining = self.budget.remaining_tokens
        
        if status == "CRITICAL":
            msg = (
                f"⚠️ CRITICAL: Context at {usage:.1f}% ({remaining:,} tokens remaining). "
                "Consider summarizing and creating a checkpoint."
            )
        elif status == "WARNING":
            msg = (
                f"⚡ WARNING: Context at {usage:.1f}% ({remaining:,} tokens remaining). "
                "Start planning for handoff."
            )
        else:
            msg = f"✅ OK: Context at {usage:.1f}% ({remaining:,} tokens remaining)."
        
        return status, msg
    
    def reset(self) -> None:
        """Reset context budget for new session."""
        self.budget = ContextBudget(budget=self.budget.budget)
        self._save_state()
    
    def estimate_file_impact(self, path: Path) -> dict:
        """Estimate impact of reading a file on budget.
        
        Args:
            path: Path to the file
            
        Returns:
            Impact analysis dictionary
        """
        tokens = estimate_file_tokens(path)
        new_total = self.budget.total_tokens + tokens
        new_percent = (new_total / self.budget.budget) * 100 if self.budget.budget > 0 else 0
        
        return {
            "file": str(path),
            "estimated_tokens": tokens,
            "current_total": self.budget.total_tokens,
            "new_total": new_total,
            "current_percent": round(self.budget.usage_percent, 1),
            "new_percent": round(new_percent, 1),
            "will_exceed_warning": new_percent >= self.budget.warning_threshold * 100,
            "will_exceed_critical": new_percent >= self.budget.critical_threshold * 100,
        }
    
    def suggest_files_to_drop(self, target_reduction: int) -> list[str]:
        """Suggest files that could be dropped to reduce context.
        
        Args:
            target_reduction: Target token reduction
            
        Returns:
            List of file paths to consider dropping
        """
        # Get file entries sorted by tokens (largest first)
        file_entries = [
            e for e in self.budget.entries
            if e.entry_type == "file"
        ]
        file_entries.sort(key=lambda e: e.estimated_tokens, reverse=True)
        
        suggestions = []
        reduction = 0
        
        for entry in file_entries:
            if reduction >= target_reduction:
                break
            suggestions.append(entry.source)
            reduction += entry.estimated_tokens
        
        return suggestions


def create_context_budget_file(target_dir: Path, budget: int = DEFAULT_BUDGET) -> Path:
    """Create initial context budget file for a project.
    
    Args:
        target_dir: Project directory
        budget: Token budget
        
    Returns:
        Path to created file
    """
    manager = ContextManager(workspace=target_dir, budget=budget)
    manager.reset()
    # Return the unified state file path
    return target_dir / ".up" / "state.json"


# CLI integration
if __name__ == "__main__":
    import sys
    
    manager = ContextManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "status":
            status, msg = manager.check_budget()
            print(msg)
            print(json.dumps(manager.get_status(), indent=2))
            
        elif cmd == "reset":
            manager.reset()
            print("Context budget reset for new session.")
            
        elif cmd == "estimate" and len(sys.argv) > 2:
            path = Path(sys.argv[2])
            impact = manager.estimate_file_impact(path)
            print(json.dumps(impact, indent=2))
            
        elif cmd == "record" and len(sys.argv) > 2:
            path = Path(sys.argv[2])
            entry = manager.record_file_read(path)
            print(f"Recorded: {entry.source} ({entry.estimated_tokens} tokens)")
            status, msg = manager.check_budget()
            print(msg)
            
        else:
            print("Usage: python context.py [status|reset|estimate <file>|record <file>]")
    else:
        status, msg = manager.check_budget()
        print(msg)
