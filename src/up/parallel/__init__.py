"""Parallel task execution package.

Consolidates basic parallel execution and advanced dependency-aware
scheduling into a single package with one import path.

Usage:
    from up.parallel import run_enhanced_parallel_loop
    from up.parallel import get_pending_tasks, TaskResult
"""

from up.parallel.analyze import (
    ExploreAnalyzer,
    ExploreComparison,
    ExploreResultSummary,
)
from up.parallel.executor import (
    ParallelExecutionManager,
    TaskResult,
    execute_task_in_worktree,
    get_pending_tasks,
    mark_task_complete_in_prd,
    verify_worktree,
)
from up.parallel.explore import (
    ExploreExecutor,
    ExploreResult,
    ExploreStrategy,
    cleanup_explorations,
    get_default_strategies,
    get_strategies,
    load_custom_strategies,
    merge_exploration,
)
from up.parallel.scheduler import (
    AgentProgress,
    ParallelDashboard,
    SharedKnowledge,
    TaskFileMap,
    build_dependency_graph,
    get_execution_waves,
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
    # Explore (Phase 2)
    "ExploreStrategy",
    "ExploreResult",
    "ExploreExecutor",
    "ExploreAnalyzer",
    "ExploreComparison",
    "ExploreResultSummary",
    "get_default_strategies",
    "get_strategies",
    "load_custom_strategies",
    "merge_exploration",
    "cleanup_explorations",
]
