"""Internal hook runtime for git hook invocations.

This module provides the sync execution paths that git hooks call.
It is NOT a public CLI command — hooks invoke it via:
    python -m up._hook_runtime memory
    python -m up._hook_runtime context

This replaces the removed ``up memory sync`` and ``up sync`` commands
that hooks previously (incorrectly) referenced.
"""

import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def sync_memory(workspace: Path) -> dict[str, Any]:
    """Sync memory: index recent commits and file changes.

    Called by the post-commit hook.
    """
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    warnings.filterwarnings("ignore")
    logging.getLogger("chromadb").setLevel(logging.ERROR)

    old_stderr = sys.stderr
    try:
        sys.stderr = open(os.devnull, "w")
        from up.memory import MemoryManager

        # Always use JSON backend in hooks — loading ChromaDB/sentence-transformers
        # triggers BLAS (gemm_thread_n) which segfaults on macOS due to thread
        # stack size limits. Hooks only index commit messages; keyword search suffices.
        manager = MemoryManager(workspace, use_vectors=False)
        results = manager.sync()
        return {
            "commits": results.get("commits_indexed", 0),
            "files": results.get("files_indexed", 0),
            "backend": manager._backend,
        }
    except Exception as exc:
        logger.debug("Memory sync failed: %s", exc)
        return {"error": str(exc)}
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr


def sync_context(workspace: Path) -> dict[str, Any]:
    """Refresh context docs (update dates, etc.).

    Called by the post-checkout hook.
    """
    import re
    from datetime import date

    updated = 0
    context_file = workspace / "docs" / "CONTEXT.md"
    if context_file.exists():
        content = context_file.read_text()
        today = date.today().isoformat()
        new_content = re.sub(
            r"\*\*Updated\*\*:\s*[\d-]+",
            f"**Updated**: {today}",
            content,
        )
        if new_content != content:
            context_file.write_text(new_content)
            updated += 1

    return {"updated": updated}


def main() -> None:
    """Entry point for ``python -m up._hook_runtime``."""
    workspace = Path.cwd()
    if len(sys.argv) < 2:
        sys.exit(0)

    action = sys.argv[1]
    if action == "memory":
        sync_memory(workspace)
    elif action == "context":
        sync_context(workspace)


if __name__ == "__main__":
    main()
