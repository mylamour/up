"""Parallel task execution package.

Consolidates basic parallel execution and advanced dependency-aware
scheduling into a single package with one import path.

Usage:
    from up.parallel import run_enhanced_parallel_loop
    from up.parallel import get_pending_tasks, TaskResult
"""

from up.parallel.executor import (
    TaskResult,
    ParallelExecutionManager,
    get_pending_tasks,
    execute_task_in_worktree,
    verify_worktree,
    mark_task_complete_in_prd,
)
from up.parallel.scheduler import (
    build_dependency_graph,
    get_execution_waves,
    TaskFileMap,
    SharedKnowledge,
    AgentProgress,
    ParallelDashboard,
    partial_merge,
    run_enhanced_parallel_loop,
)

__all__ = [
    # Core execution
    "TaskResult",
    "ParallelExecutionManager",
    "get_pending_tasks",
    "execute_task_in_worktree",
    "verify_worktree",
    "mark_task_complete_in_prd",
    # Scheduling
    "build_dependency_graph",
    "get_execution_waves",
    "TaskFileMap",
    "SharedKnowledge",
    "AgentProgress",
    "ParallelDashboard",
    "partial_merge",
    "run_enhanced_parallel_loop",
]
