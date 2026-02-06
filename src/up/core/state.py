"""Unified state management for up-cli.

This module provides a single source of truth for all up-cli state,
consolidating previously fragmented state files:
- .loop_state.json → state.loop
- .claude/context_budget.json → state.context
- .parallel_state.json → state.parallel
- .worktrees/*/.agent_state.json → state.agents

All state is now stored in .up/state.json
Configuration is stored in .up/config.json
"""

import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

from filelock import FileLock

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Data Class
# =============================================================================

@dataclass
class UpConfig:
    """Configuration for up-cli (stored in .up/config.json).
    
    All hardcoded values are now configurable here.
    """
    # Doom loop detection
    doom_loop_threshold: int = 3  # Consecutive failures before doom loop
    
    # Circuit breaker
    circuit_breaker_cooldown_minutes: int = 5  # Minutes before HALF_OPEN
    circuit_breaker_failure_threshold: int = 3  # Failures before OPEN
    
    # Checkpoints
    checkpoint_retention_count: int = 50  # Max checkpoints to keep
    
    # Context budget
    context_budget_tokens: int = 100_000
    context_warning_threshold: float = 0.8  # 80%
    context_critical_threshold: float = 0.9  # 90%
    
    # AI execution
    default_ai_timeout_seconds: int = 600  # 10 minutes
    
    # Parallel execution
    default_parallel_workers: int = 3
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UpConfig":
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


# =============================================================================
# State Data Classes
# =============================================================================

@dataclass
class CircuitBreakerState:
    """Circuit breaker state for a specific operation."""
    failures: int = 0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    last_failure: Optional[str] = None
    opened_at: Optional[str] = None
    # Configurable thresholds (set from UpConfig)
    failure_threshold: int = 3
    cooldown_minutes: int = 5
    
    def record_failure(self):
        """Record a failure."""
        self.failures += 1
        self.last_failure = datetime.now().isoformat()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = datetime.now().isoformat()
    
    def record_success(self):
        """Record a success."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures = 0
        elif self.state == "CLOSED":
            self.failures = max(0, self.failures - 1)
    
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "OPEN"
    
    def try_reset(self) -> bool:
        """Try to reset from OPEN to HALF_OPEN after cooldown.
        
        Should be called before attempting an operation to check
        if we can try again after the cooldown period.
        
        Returns:
            True if transitioned to HALF_OPEN, False otherwise
        """
        if self.state != "OPEN" or not self.opened_at:
            return False
        
        opened = datetime.fromisoformat(self.opened_at)
        if (datetime.now() - opened).total_seconds() > self.cooldown_minutes * 60:
            self.state = "HALF_OPEN"
            return True
        return False
    
    def can_execute(self) -> bool:
        """Check if we can execute an operation.
        
        Returns True if circuit is CLOSED or HALF_OPEN (allowing a test).
        Automatically tries to reset if currently OPEN and cooldown expired.
        """
        if self.state == "CLOSED":
            return True
        if self.state == "HALF_OPEN":
            return True
        # Try to reset from OPEN
        self.try_reset()
        return self.state != "OPEN"


@dataclass
class LoopState:
    """Product loop execution state."""
    iteration: int = 0
    phase: str = "IDLE"  # IDLE, OBSERVE, CHECKPOINT, EXECUTE, VERIFY, COMMIT
    current_task: Optional[str] = None
    tasks_completed: List[str] = field(default_factory=list)
    tasks_failed: List[str] = field(default_factory=list)
    last_checkpoint: Optional[str] = None
    started_at: Optional[str] = None
    interrupted_at: Optional[str] = None
    
    # Doom loop detection (threshold set from UpConfig)
    consecutive_failures: int = 0
    doom_loop_threshold: int = 3  # Default, overridden by config


@dataclass
class ContextState:
    """Context window budget tracking."""
    budget: int = 100_000
    total_tokens: int = 0
    warning_threshold: float = 0.8
    critical_threshold: float = 0.9
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    entries: List[Dict[str, Any]] = field(default_factory=list)
    
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


@dataclass
class AgentState:
    """State of a single agent worktree."""
    task_id: str
    task_title: str = ""
    branch: str = ""
    worktree_path: str = ""
    status: str = "created"  # created, executing, verifying, passed, failed, merged
    phase: str = "INIT"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    commits: int = 0
    error: Optional[str] = None


@dataclass
class ParallelState:
    """Parallel execution state."""
    active: bool = False
    max_workers: int = 3
    current_batch: int = 0
    agents: List[str] = field(default_factory=list)  # List of agent task_ids


@dataclass
class MetricsState:
    """Performance metrics."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_time_seconds: float = 0
    total_rollbacks: int = 0
    total_checkpoints: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.completed_tasks + self.failed_tasks
        return self.completed_tasks / total if total > 0 else 0


@dataclass
class UnifiedState:
    """Unified state for all up-cli operations.
    
    This is the single source of truth, stored in .up/state.json
    """
    version: str = "2.0"
    
    # Core states
    loop: LoopState = field(default_factory=LoopState)
    context: ContextState = field(default_factory=ContextState)
    parallel: ParallelState = field(default_factory=ParallelState)
    metrics: MetricsState = field(default_factory=MetricsState)
    
    # Circuit breakers (keyed by operation name)
    circuit_breakers: Dict[str, CircuitBreakerState] = field(default_factory=dict)
    
    # Agent states (keyed by task_id)
    agents: Dict[str, AgentState] = field(default_factory=dict)
    
    # Checkpoints (list of checkpoint IDs)
    checkpoints: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_circuit_breaker(self, name: str, config: Optional["UpConfig"] = None) -> CircuitBreakerState:
        """Get or create a circuit breaker by name.
        
        Args:
            name: Circuit breaker identifier
            config: Optional config to apply thresholds (used by StateManager)
        """
        if name not in self.circuit_breakers:
            cb = CircuitBreakerState()
            if config:
                cb.failure_threshold = config.circuit_breaker_failure_threshold
                cb.cooldown_minutes = config.circuit_breaker_cooldown_minutes
            self.circuit_breakers[name] = cb
        return self.circuit_breakers[name]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "loop": asdict(self.loop),
            "context": asdict(self.context),
            "parallel": asdict(self.parallel),
            "metrics": asdict(self.metrics),
            "circuit_breakers": {
                k: asdict(v) for k, v in self.circuit_breakers.items()
            },
            "agents": {
                k: asdict(v) for k, v in self.agents.items()
            },
            "checkpoints": self.checkpoints,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UnifiedState":
        """Create from dictionary."""
        state = cls()
        state.version = data.get("version", "2.0")
        
        # Load loop state
        if "loop" in data:
            loop_data = data["loop"]
            state.loop = LoopState(**{
                k: v for k, v in loop_data.items()
                if k in LoopState.__dataclass_fields__
            })
        
        # Load context state
        if "context" in data:
            ctx_data = data["context"]
            state.context = ContextState(**{
                k: v for k, v in ctx_data.items()
                if k in ContextState.__dataclass_fields__
            })
        
        # Load parallel state
        if "parallel" in data:
            par_data = data["parallel"]
            state.parallel = ParallelState(**{
                k: v for k, v in par_data.items()
                if k in ParallelState.__dataclass_fields__
            })
        
        # Load metrics state
        if "metrics" in data:
            met_data = data["metrics"]
            state.metrics = MetricsState(**{
                k: v for k, v in met_data.items()
                if k in MetricsState.__dataclass_fields__
            })
        
        # Load circuit breakers
        if "circuit_breakers" in data:
            for name, cb_data in data["circuit_breakers"].items():
                state.circuit_breakers[name] = CircuitBreakerState(**cb_data)
        
        # Load agents
        if "agents" in data:
            for task_id, agent_data in data["agents"].items():
                state.agents[task_id] = AgentState(**{
                    k: v for k, v in agent_data.items()
                    if k in AgentState.__dataclass_fields__
                })
        
        state.checkpoints = data.get("checkpoints", [])
        state.created_at = data.get("created_at", datetime.now().isoformat())
        state.updated_at = data.get("updated_at", datetime.now().isoformat())
        
        return state


# =============================================================================
# State Manager
# =============================================================================

class StateManager:
    """Manages unified state for up-cli.
    
    Provides:
    - Load/save to .up/state.json
    - Configuration via .up/config.json
    - Migration from old state files
    - Atomic updates with timestamps
    """
    
    STATE_DIR = ".up"
    STATE_FILE = "state.json"
    CONFIG_FILE = "config.json"
    
    # Old state file locations for migration
    OLD_LOOP_STATE = ".loop_state.json"
    OLD_CONTEXT_STATE = ".claude/context_budget.json"
    OLD_PARALLEL_STATE = ".parallel_state.json"
    
    def __init__(self, workspace: Optional[Path] = None):
        """Initialize state manager.
        
        Args:
            workspace: Project root directory (defaults to cwd)
        """
        self.workspace = workspace or Path.cwd()
        self.state_dir = self.workspace / self.STATE_DIR
        self.state_file = self.state_dir / self.STATE_FILE
        self.config_file = self.state_dir / self.CONFIG_FILE
        self._state: Optional[UnifiedState] = None
        self._config: Optional[UpConfig] = None
        # File lock for thread-safe and cross-process state access
        self._lock = FileLock(str(self.state_file) + ".lock", timeout=30)
    
    @property
    def config(self) -> UpConfig:
        """Get configuration, loading if necessary."""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> UpConfig:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                return UpConfig.from_dict(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return UpConfig()
    
    def save_config(self) -> None:
        """Save configuration to file."""
        if self._config is None:
            return
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(self._config.to_dict(), indent=2))
    
    def update_config(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save_config()
        # Apply new config to state
        self._apply_config_to_state()
    
    @property
    def state(self) -> UnifiedState:
        """Get current state, loading if necessary."""
        if self._state is None:
            self._state = self.load()
        return self._state
    
    def _apply_config_to_state(self) -> None:
        """Apply configuration values to state objects."""
        if self._state is None:
            return
        
        cfg = self.config
        
        # Apply doom loop threshold
        self._state.loop.doom_loop_threshold = cfg.doom_loop_threshold
        
        # Apply context budget config
        self._state.context.budget = cfg.context_budget_tokens
        self._state.context.warning_threshold = cfg.context_warning_threshold
        self._state.context.critical_threshold = cfg.context_critical_threshold
        
        # Apply parallel config
        self._state.parallel.max_workers = cfg.default_parallel_workers
        
        # Apply circuit breaker config to all breakers
        for cb in self._state.circuit_breakers.values():
            cb.failure_threshold = cfg.circuit_breaker_failure_threshold
            cb.cooldown_minutes = cfg.circuit_breaker_cooldown_minutes
    
    def load(self) -> UnifiedState:
        """Load state from file, migrating old files if needed.
        
        If state.json is corrupted, attempts recovery from .bak file
        before falling back to migration.
        """
        # Try loading new unified state
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._state = UnifiedState.from_dict(data)
                # Apply configuration
                self._apply_config_to_state()
                return self._state
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning("State file corrupted: %s. Trying backup.", e)
                # Try recovery from backup
                backup_file = self.state_file.with_suffix(".json.bak")
                if backup_file.exists():
                    try:
                        data = json.loads(backup_file.read_text())
                        self._state = UnifiedState.from_dict(data)
                        self._apply_config_to_state()
                        logger.info("Recovered state from backup file")
                        # Re-save to fix the corrupted main file
                        self.save()
                        return self._state
                    except (json.JSONDecodeError, TypeError, KeyError):
                        logger.warning("Backup file also corrupted")
        
        # No unified state (or both corrupted), try migration
        self._state = self._migrate_old_states()
        # Apply configuration
        self._apply_config_to_state()
        return self._state
    
    def save(self) -> None:
        """Save current state to file (thread-safe, atomic).
        
        Uses filelock for cross-thread/cross-process safety,
        writes to a temp file with fsync, then atomically replaces
        the target file using os.replace().
        """
        if self._state is None:
            return
        
        # Update timestamp
        self._state.updated_at = datetime.now().isoformat()
        
        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        with self._lock:
            # Rolling backup: copy current state to .bak before overwriting
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix(".json.bak")
                try:
                    shutil.copy2(str(self.state_file), str(backup_file))
                except OSError:
                    logger.warning("Could not create state backup")
            
            # Atomic write: temp file + fsync + os.replace()
            fd = None
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(self.state_dir),
                    suffix=".tmp",
                    prefix="state_",
                )
                with os.fdopen(fd, "w") as f:
                    fd = None  # os.fdopen takes ownership of fd
                    json.dump(self._state.to_dict(), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(self.state_file))
                tmp_path = None  # replaced successfully
            except Exception:
                # Clean up temp file on failure
                if fd is not None:
                    os.close(fd)
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
    
    def atomic_update(self, updater: Callable[[UnifiedState], None]) -> None:
        """Thread-safe read-modify-write on the state.
        
        Holds the file lock for the entire read-modify-write cycle
        to prevent lost updates from concurrent access.
        
        Args:
            updater: Function that mutates the state in-place.
        
        Example:
            def bump_iteration(state):
                state.loop.iteration += 1
            manager.atomic_update(bump_iteration)
        """
        with self._lock:
            # Re-read state from disk to get latest
            if self.state_file.exists():
                try:
                    data = json.loads(self.state_file.read_text())
                    self._state = UnifiedState.from_dict(data)
                    self._apply_config_to_state()
                except (json.JSONDecodeError, TypeError, KeyError):
                    if self._state is None:
                        self._state = UnifiedState()
            elif self._state is None:
                self._state = UnifiedState()
            
            # Apply the update
            updater(self._state)
            
            # Save (will re-acquire lock, but FileLock is re-entrant)
            self._state.updated_at = datetime.now().isoformat()
            self.state_dir.mkdir(parents=True, exist_ok=True)
            
            # Rolling backup
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix(".json.bak")
                try:
                    shutil.copy2(str(self.state_file), str(backup_file))
                except OSError:
                    pass
            
            # Atomic write
            fd = None
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(self.state_dir),
                    suffix=".tmp",
                    prefix="state_",
                )
                with os.fdopen(fd, "w") as f:
                    fd = None
                    json.dump(self._state.to_dict(), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(self.state_file))
                tmp_path = None
            except Exception:
                if fd is not None:
                    os.close(fd)
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
    
    def reset(self) -> UnifiedState:
        """Reset to fresh state."""
        self._state = UnifiedState()
        self.save()
        return self._state
    
    def _migrate_old_states(self) -> UnifiedState:
        """Migrate from old fragmented state files."""
        state = UnifiedState()
        migrated = []
        
        # Migrate old loop state
        old_loop = self.workspace / self.OLD_LOOP_STATE
        if old_loop.exists():
            try:
                data = json.loads(old_loop.read_text())
                state.loop = LoopState(
                    iteration=data.get("iteration", 0),
                    phase=data.get("phase", "IDLE"),
                    current_task=data.get("current_task"),
                    tasks_completed=data.get("tasks_completed", []),
                    last_checkpoint=data.get("last_checkpoint"),
                    started_at=data.get("started_at"),
                    interrupted_at=data.get("interrupted_at"),
                )
                # Migrate circuit breakers
                if "circuit_breaker" in data:
                    for name, cb_data in data["circuit_breaker"].items():
                        if isinstance(cb_data, dict):
                            state.circuit_breakers[name] = CircuitBreakerState(
                                failures=cb_data.get("failures", 0),
                                state=cb_data.get("state", "CLOSED"),
                            )
                migrated.append(str(old_loop))
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Migrate old context budget
        old_context = self.workspace / self.OLD_CONTEXT_STATE
        if old_context.exists():
            try:
                data = json.loads(old_context.read_text())
                state.context = ContextState(
                    budget=data.get("budget", 100_000),
                    total_tokens=data.get("total_tokens", 0),
                    warning_threshold=data.get("warning_threshold", 0.8),
                    critical_threshold=data.get("critical_threshold", 0.9),
                    session_start=data.get("session_start", datetime.now().isoformat()),
                    entries=data.get("entries", []),
                )
                migrated.append(str(old_context))
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Migrate old parallel state
        old_parallel = self.workspace / self.OLD_PARALLEL_STATE
        if old_parallel.exists():
            try:
                data = json.loads(old_parallel.read_text())
                state.parallel = ParallelState(
                    active=data.get("mode") == "parallel",
                    max_workers=data.get("parallel_limit", 3),
                    current_batch=data.get("iteration", 0),
                    agents=data.get("active_worktrees", []),
                )
                migrated.append(str(old_parallel))
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Log migration
        if migrated:
            state.version = "2.0"
            # Save migrated state
            self._state = state
            self.save()
            
            # Optionally rename old files (don't delete yet for safety)
            for old_file in migrated:
                old_path = Path(old_file)
                if old_path.exists():
                    backup = old_path.with_suffix(old_path.suffix + ".migrated")
                    try:
                        old_path.rename(backup)
                    except OSError:
                        pass  # Can't rename, leave it
        
        self._state = state
        return state
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def update_loop(self, **kwargs) -> None:
        """Update loop state fields."""
        for key, value in kwargs.items():
            if hasattr(self.state.loop, key):
                setattr(self.state.loop, key, value)
        self.save()
    
    def update_context(self, **kwargs) -> None:
        """Update context state fields."""
        for key, value in kwargs.items():
            if hasattr(self.state.context, key):
                setattr(self.state.context, key, value)
        self.save()
    
    def record_task_complete(self, task_id: str) -> None:
        """Record a task completion."""
        if task_id not in self.state.loop.tasks_completed:
            self.state.loop.tasks_completed.append(task_id)
        self.state.metrics.completed_tasks += 1
        self.state.loop.consecutive_failures = 0  # Reset doom loop counter
        self.save()
    
    def record_task_failed(self, task_id: str) -> None:
        """Record a task failure."""
        if task_id not in self.state.loop.tasks_failed:
            self.state.loop.tasks_failed.append(task_id)
        self.state.metrics.failed_tasks += 1
        self.state.loop.consecutive_failures += 1
        self.save()
    
    def check_doom_loop(self) -> tuple[bool, str]:
        """Check if we're in a doom loop.
        
        Uses configurable threshold from .up/config.json
        
        Returns:
            Tuple of (is_doom_loop, message)
        """
        failures = self.state.loop.consecutive_failures
        threshold = self.config.doom_loop_threshold
        
        if failures >= threshold:
            return True, (
                f"⚠️ DOOM LOOP DETECTED: {failures} consecutive failures. "
                f"Consider running 'up reset' instead of continuing."
            )
        elif failures >= threshold - 1:
            return False, (
                f"⚡ Warning: {failures} consecutive failures. "
                f"One more failure will trigger doom loop detection."
            )
        return False, ""
    
    def get_circuit_breaker(self, name: str) -> CircuitBreakerState:
        """Get or create a circuit breaker with config applied."""
        return self.state.get_circuit_breaker(name, self.config)
    
    def add_agent(self, agent: AgentState) -> None:
        """Add an agent to state."""
        self.state.agents[agent.task_id] = agent
        if agent.task_id not in self.state.parallel.agents:
            self.state.parallel.agents.append(agent.task_id)
        self.save()
    
    def remove_agent(self, task_id: str) -> None:
        """Remove an agent from state."""
        if task_id in self.state.agents:
            del self.state.agents[task_id]
        if task_id in self.state.parallel.agents:
            self.state.parallel.agents.remove(task_id)
        self.save()
    
    def add_checkpoint(self, checkpoint_id: str) -> None:
        """Record a checkpoint."""
        self.state.checkpoints.append(checkpoint_id)
        self.state.loop.last_checkpoint = checkpoint_id
        self.state.metrics.total_checkpoints += 1
        # Keep only configured number of checkpoints
        retention = self.config.checkpoint_retention_count
        if len(self.state.checkpoints) > retention:
            self.state.checkpoints = self.state.checkpoints[-retention:]
        self.save()
    
    def record_rollback(self) -> None:
        """Record a rollback."""
        self.state.metrics.total_rollbacks += 1
        self.save()


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_manager: Optional[StateManager] = None


def get_state_manager(workspace: Optional[Path] = None) -> StateManager:
    """Get or create the default state manager."""
    global _default_manager
    if _default_manager is None or (workspace and _default_manager.workspace != workspace):
        _default_manager = StateManager(workspace)
    return _default_manager


def get_state(workspace: Optional[Path] = None) -> UnifiedState:
    """Get current unified state."""
    return get_state_manager(workspace).state


def save_state(workspace: Optional[Path] = None) -> None:
    """Save current state."""
    get_state_manager(workspace).save()
