"""Core modules for up-cli.

This package contains the foundational modules used across all commands:
- state: Unified state management
- checkpoint: Git checkpoint operations
"""

from up.core.checkpoint import (
    CheckpointError,
    CheckpointManager,
    CheckpointMetadata,
    CheckpointNotFoundError,
    GitError,
    NotAGitRepoError,
    get_checkpoint_manager,
    get_diff,
    restore_checkpoint,
    save_checkpoint,
)
from up.core.loop import (
    BeginTaskResult,
    CircuitBreakerStatus,
    FailureResult,
    LoopOrchestrator,
    SuccessResult,
    TaskInfo,
    TaskPrompts,
    VerificationCommands,
)
from up.core.prd_schema import (
    PRD,
    PRDValidationError,
    UserStory,
    load_prd,
    save_prd,
)
from up.core.provenance import (
    ProvenanceEntry,
    ProvenanceManager,
    complete_ai_operation,
    get_provenance_manager,
    track_ai_operation,
)
from up.core.state import (
    AgentState,
    CircuitBreakerState,
    ContextState,
    LoopState,
    StateManager,
    UnifiedState,
    get_state,
    get_state_manager,
    save_state,
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
    # Loop Orchestrator
    "LoopOrchestrator",
    "TaskInfo",
    "BeginTaskResult",
    "TaskPrompts",
    "FailureResult",
    "SuccessResult",
    "CircuitBreakerStatus",
    "VerificationCommands",
]
