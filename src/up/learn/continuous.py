"""Continuous learning trigger.

Monitors task completions and triggers learning analysis after a
configurable number of tasks. If significant changes are detected,
auto-runs `up sync` to regenerate AI instructions.

Wired into EventBridge via create_learning_handlers().
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default: trigger learning every N task completions
DEFAULT_LEARNING_INTERVAL = 5


def _load_learning_config(workspace: Path) -> dict:
    """Load continuous learning config from .up/config.json."""
    config_path = workspace / ".up" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            learn_cfg = data.get("automation", {}).get("learning", {})
            return {
                "enabled": learn_cfg.get("continuous", True),
                "interval": learn_cfg.get("interval", DEFAULT_LEARNING_INTERVAL),
                "auto_sync": learn_cfg.get("auto_sync", True),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "enabled": True,
        "interval": DEFAULT_LEARNING_INTERVAL,
        "auto_sync": True,
    }


def _get_task_counter(workspace: Path) -> int:
    """Read the task completion counter."""
    counter_file = workspace / ".up" / "learning_counter.json"
    if counter_file.exists():
        try:
            data = json.loads(counter_file.read_text())
            return data.get("tasks_since_last_learn", 0)
        except (json.JSONDecodeError, OSError):
            pass
    return 0


def _set_task_counter(workspace: Path, count: int) -> None:
    """Write the task completion counter."""
    counter_file = workspace / ".up" / "learning_counter.json"
    counter_file.parent.mkdir(parents=True, exist_ok=True)
    counter_file.write_text(json.dumps({
        "tasks_since_last_learn": count,
    }))


def _run_self_improvement(workspace: Path) -> dict:
    """Run learn_self_improvement and return the result."""
    try:
        from up.learn.analyzer import learn_self_improvement
        return learn_self_improvement(workspace, use_ai=False)
    except Exception as e:
        logger.warning("Continuous learning failed: %s", e)
        return


def _run_sync(workspace: Path) -> None:
    """Re-run up sync to regenerate AI instructions."""
    try:
        from up.commands.sync_config import run_sync
        run_sync(workspace)
        logger.info("Auto-sync completed after learning trigger")
    except Exception as e:
        logger.warning("Auto-sync failed: %s", e)


def check_learning_trigger(workspace: Path) -> dict | None:
    """Check if learning should trigger and run it if so.

    Called after each task completion. Returns improvement dict
    if learning was triggered, None otherwise.
    """
    config = _load_learning_config(workspace)
    if not config["enabled"]:
        return None

    count = _get_task_counter(workspace) + 1
    interval = config["interval"]

    if count < interval:
        _set_task_counter(workspace, count)
        return None

    # Threshold reached — trigger learning
    _set_task_counter(workspace, 0)
    logger.info("Continuous learning triggered after %d tasks", count)

    improvements = _run_self_improvement(workspace)

    # Auto-sync if significant changes detected
    if config["auto_sync"] and improvements:
        new_patterns = improvements.get("new_patterns", [])
        addressed = improvements.get("addressed_improvements", [])
        if new_patterns or addressed:
            _run_sync(workspace)

    return improvements
