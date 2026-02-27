"""Diverge-Then-Converge exploration engine.

Spawns multiple AI agents with different strategies to tackle the same
problem in isolated worktrees, then compares results for user selection.

Phase 2 of the UP Platform PRD.
"""

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# US-001: ExploreStrategy dataclass and default strategies
# ---------------------------------------------------------------------------

@dataclass
class ExploreStrategy:
    """A strategy that guides an AI agent toward a specific approach."""

    name: str
    description: str
    prompt_template: str
    constraints: list[str] = field(default_factory=list)


def get_default_strategies() -> list[ExploreStrategy]:
    """Return the 3 built-in exploration strategies."""
    return [
        ExploreStrategy(
            name="minimal",
            description="Fewest changes, lowest risk",
            prompt_template=(
                "You are solving the following problem with a MINIMAL approach.\n"
                "Goal: Make the fewest possible changes to fix/implement this.\n"
                "Prioritize: small diffs, low risk, no refactoring.\n\n"
                "Problem:\n{problem}\n\n"
                "Codebase context:\n{codebase_context}\n\n"
                "{constraints}"
            ),
            constraints=[
                "Change as few files as possible",
                "Avoid refactoring existing code",
                "Prefer the simplest solution that works",
            ],
        ),
        ExploreStrategy(
            name="clean",
            description="Best architecture, may refactor",
            prompt_template=(
                "You are solving the following problem with a CLEAN ARCHITECTURE approach.\n"
                "Goal: Produce the best possible design, even if it means refactoring.\n"
                "Prioritize: clean abstractions, testability, maintainability.\n\n"
                "Problem:\n{problem}\n\n"
                "Codebase context:\n{codebase_context}\n\n"
                "{constraints}"
            ),
            constraints=[
                "Refactor freely if it improves the design",
                "Add proper abstractions and interfaces",
                "Ensure high test coverage for new code",
            ],
        ),
        ExploreStrategy(
            name="pragmatic",
            description="Balance of speed and quality",
            prompt_template=(
                "You are solving the following problem with a PRAGMATIC approach.\n"
                "Goal: Balance speed of implementation with code quality.\n"
                "Prioritize: working solution, reasonable quality, moderate effort.\n\n"
                "Problem:\n{problem}\n\n"
                "Codebase context:\n{codebase_context}\n\n"
                "{constraints}"
            ),
            constraints=[
                "Balance between minimal changes and clean design",
                "Refactor only when clearly beneficial",
                "Add tests for critical paths",
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# US-002: ExploreExecutor — parallel agent spawning with strategies
# ---------------------------------------------------------------------------

@dataclass
class ExploreResult:
    """Result from a single exploration agent."""

    strategy_name: str
    branch: str
    worktree_path: Path
    success: bool
    output: str
    files_changed: list[str] = field(default_factory=list)
    error: str | None = None


class ExploreExecutor:
    """Spawns one agent per strategy in isolated worktrees."""

    def __init__(
        self,
        workspace: Path,
        engine=None,
        timeout: int = 300,
    ):
        self.workspace = workspace
        self.engine = engine  # AIEngine instance
        self.timeout = timeout

    def _build_prompt(
        self, strategy: ExploreStrategy, problem: str, context: str = ""
    ) -> str:
        """Render a strategy's prompt template."""
        constraints_text = ""
        if strategy.constraints:
            constraints_text = "Constraints:\n" + "\n".join(
                f"- {c}" for c in strategy.constraints
            )
        return strategy.prompt_template.format(
            problem=problem,
            codebase_context=context or "(no additional context)",
            constraints=constraints_text,
        )

    def _run_agent(
        self, strategy: ExploreStrategy, problem: str, context: str
    ) -> ExploreResult:
        """Run a single agent in its own worktree."""
        from up.git.worktree import create_worktree

        task_id = f"explore-{strategy.name}"
        branch = ""
        wt_path = Path(".")

        try:
            wt_path, _state = create_worktree(
                task_id=task_id,
                task_title=f"Explore: {strategy.name}",
                base_branch="main",
            )
            branch = f"up/{task_id}"

            prompt = self._build_prompt(strategy, problem, context)

            if self.engine is None:
                return ExploreResult(
                    strategy_name=strategy.name,
                    branch=branch,
                    worktree_path=wt_path,
                    success=False,
                    output="",
                    error="No AI engine configured",
                )

            success, output = self.engine.execute_task(
                workspace=wt_path,
                prompt=prompt,
                timeout=self.timeout,
            )

            # Collect changed files
            files_changed = self._get_changed_files(wt_path)

            return ExploreResult(
                strategy_name=strategy.name,
                branch=branch,
                worktree_path=wt_path,
                success=success,
                output=output,
                files_changed=files_changed,
            )

        except Exception as e:
            logger.exception("Agent %s failed", strategy.name)
            return ExploreResult(
                strategy_name=strategy.name,
                branch=branch,
                worktree_path=wt_path,
                success=False,
                output="",
                error=str(e),
            )

    def _get_changed_files(self, worktree: Path) -> list[str]:
        """List files changed in the worktree relative to its base."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=worktree,
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            pass
        return []

    def execute(
        self,
        problem: str,
        strategies: list[ExploreStrategy],
        context: str = "",
    ) -> list[ExploreResult]:
        """Run all strategies in parallel and return results."""
        results: list[ExploreResult] = []

        with ThreadPoolExecutor(max_workers=len(strategies)) as pool:
            futures = {
                pool.submit(self._run_agent, s, problem, context): s
                for s in strategies
            }
            for future in as_completed(futures):
                strategy = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(
                        ExploreResult(
                            strategy_name=strategy.name,
                            branch="",
                            worktree_path=Path("."),
                            success=False,
                            output="",
                            error=str(e),
                        )
                    )

        # Sort by strategy order (match input order)
        name_order = {s.name: i for i, s in enumerate(strategies)}
        results.sort(key=lambda r: name_order.get(r.strategy_name, 99))
        return results


# ---------------------------------------------------------------------------
# US-005: Merge selected exploration result
# ---------------------------------------------------------------------------

def merge_exploration(
    choice,
    results: list[ExploreResult],
    workspace: Path,
    target_branch: str = "main",
) -> bool:
    """Merge the chosen exploration result back to the target branch.

    Args:
        choice: ExploreChoice from the UI.
        results: List of ExploreResult from ExploreExecutor.
        workspace: Root workspace path.
        target_branch: Branch to merge into.

    Returns:
        True if merge succeeded.
    """
    from up.git.worktree import merge_worktree
    from up.ui.explore_display import ExploreChoice

    if choice == ExploreChoice.NONE:
        cleanup_explorations(results)
        return False

    if choice == ExploreChoice.COMBINE:
        return _combine_explorations(results, workspace, target_branch)

    # Single strategy selection
    idx = int(choice.value) - 1
    if idx < 0 or idx >= len(results):
        logger.error("Invalid choice index %d", idx)
        cleanup_explorations(results)
        return False

    selected = results[idx]
    task_id = f"explore-{selected.strategy_name}"

    try:
        ok = merge_worktree(
            task_id=task_id,
            target_branch=target_branch,
            squash=True,
            message=f"explore({selected.strategy_name}): merge selected approach",
        )
        return ok
    except Exception:
        logger.exception("Merge failed for %s", selected.strategy_name)
        return False
    finally:
        cleanup_explorations(results)


def _combine_explorations(
    results: list[ExploreResult],
    workspace: Path,
    target_branch: str,
) -> bool:
    """Best-effort cherry-pick of non-conflicting changes from multiple worktrees."""
    from up.git.worktree import merge_worktree

    merged_any = False
    for r in results:
        if not r.success:
            continue
        task_id = f"explore-{r.strategy_name}"
        try:
            ok = merge_worktree(
                task_id=task_id,
                target_branch=target_branch,
                squash=True,
                message=f"explore({r.strategy_name}): combined merge",
            )
            if ok:
                merged_any = True
        except Exception:
            logger.warning("Could not merge %s during combine", r.strategy_name)
    return merged_any


def cleanup_explorations(results: list[ExploreResult]) -> None:
    """Remove all exploration worktrees."""
    from up.git.worktree import remove_worktree

    for r in results:
        task_id = f"explore-{r.strategy_name}"
        try:
            remove_worktree(task_id, force=True)
        except Exception:
            logger.debug("Could not remove worktree for %s", r.strategy_name)


# ---------------------------------------------------------------------------
# US-007: Custom strategy definitions via Markdown
# ---------------------------------------------------------------------------

def load_custom_strategies(workspace: Path) -> list[ExploreStrategy]:
    """Load custom strategies from .up/plugins/*/strategies/ directories.

    Strategy files are Markdown with YAML frontmatter:
        ---
        name: my-strategy
        description: A custom approach
        constraints:
          - Do X
          - Avoid Y
        ---
        Prompt template body with {problem}, {codebase_context}, {constraints}.
    """
    strategies: list[ExploreStrategy] = []
    plugins_dir = workspace / ".up" / "plugins"

    if not plugins_dir.is_dir():
        return strategies

    for strategies_dir in plugins_dir.glob("*/*/strategies"):
        for md_file in sorted(strategies_dir.glob("*.md")):
            s = _parse_strategy_file(md_file)
            if s:
                strategies.append(s)

    return strategies


def _parse_strategy_file(path: Path) -> ExploreStrategy | None:
    """Parse a Markdown strategy file with YAML frontmatter."""
    try:
        text = path.read_text()
    except Exception:
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML parsing
    meta: dict = {}
    current_key = None
    current_list: list[str] = []

    for line in frontmatter.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip())
            continue
        if current_key and current_list:
            meta[current_key] = current_list
            current_list = []
            current_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                meta[key] = val
            else:
                current_key = key

    if current_key and current_list:
        meta[current_key] = current_list

    name = meta.get("name", "")
    if not name:
        return None

    constraints = meta.get("constraints", [])
    if isinstance(constraints, str):
        constraints = [constraints]

    return ExploreStrategy(
        name=name,
        description=meta.get("description", ""),
        prompt_template=body,
        constraints=constraints,
    )


def get_strategies(
    workspace: Path,
    names: list[str] | None = None,
) -> list[ExploreStrategy]:
    """Get strategies by name, merging defaults with custom ones.

    Custom strategies override defaults when names collide.
    If *names* is provided, only return strategies matching those names.
    """
    defaults = {s.name: s for s in get_default_strategies()}
    custom = {s.name: s for s in load_custom_strategies(workspace)}

    merged = {**defaults, **custom}

    if names:
        return [merged[n] for n in names if n in merged]
    return list(merged.values())
