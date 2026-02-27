"""Git utilities for up-cli."""

from up.git.utils import (
    BRANCH_PREFIX,
    LEGACY_BRANCH_PREFIX,
    count_commits_since,
    get_current_branch,
    is_git_repo,
    make_branch_name,
    migrate_legacy_branch,
    preview_merge,
    run_git,
)
from up.git.worktree import (
    WorktreeState,
    create_worktree,
    list_worktrees,
    merge_worktree,
    remove_worktree,
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
    "preview_merge",
    "BRANCH_PREFIX",
    "LEGACY_BRANCH_PREFIX",
]
