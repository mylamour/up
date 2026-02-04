"""Core modules for up-cli.

This package contains the foundational modules used across all commands:
- state: Unified state management
- checkpoint: Git checkpoint operations
"""

from up.core.state import (
    UnifiedState,
    LoopState,
    ContextState,
    AgentState,
    CircuitBreakerState,
    StateManager,
    get_state_manager,
    get_state,
    save_state,
)

from up.core.checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
    CheckpointError,
    GitError,
    NotAGitRepoError,
    CheckpointNotFoundError,
    get_checkpoint_manager,
    save_checkpoint,
    restore_checkpoint,
    get_diff,
)

from up.core.provenance import (
    ProvenanceEntry,
    ProvenanceManager,
    get_provenance_manager,
    track_ai_operation,
    complete_ai_operation,
)

__all__ = [
    # State
    "UnifiedState",
    "LoopState",
    "ContextState",
    "AgentState",
    "CircuitBreakerState",
    "StateManager",
    "get_state_manager",
    "get_state",
    "save_state",
    # Checkpoint
    "CheckpointManager",
    "CheckpointMetadata",
    "CheckpointError",
    "GitError",
    "NotAGitRepoError",
    "CheckpointNotFoundError",
    "get_checkpoint_manager",
    "save_checkpoint",
    "restore_checkpoint",
    "get_diff",
    # Provenance
    "ProvenanceEntry",
    "ProvenanceManager",
    "get_provenance_manager",
    "track_ai_operation",
    "complete_ai_operation",
]
