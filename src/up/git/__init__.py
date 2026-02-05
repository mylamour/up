"""Git utilities for up-cli."""

from up.git.worktree import (
    create_worktree,
    remove_worktree,
    list_worktrees,
    merge_worktree,
    WorktreeState,
)
from up.git.utils import (
    is_git_repo,
    get_current_branch,
    count_commits_since,
    make_branch_name,
    run_git,
    migrate_legacy_branch,
    BRANCH_PREFIX,
    LEGACY_BRANCH_PREFIX,
)

__all__ = [
    "create_worktree",
    "remove_worktree",
    "list_worktrees",
    "merge_worktree",
    "WorktreeState",
    "is_git_repo",
    "get_current_branch",
    "count_commits_since",
    "make_branch_name",
    "run_git",
    "migrate_legacy_branch",
    "BRANCH_PREFIX",
    "LEGACY_BRANCH_PREFIX",
]
