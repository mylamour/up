#!/usr/bin/env python3
"""
State Manager for Product Loop

Manages loop state, checkpoints, and progress tracking.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class LoopState:
    """Current state of the product loop."""
    version: str = "1.0"
    iteration: int = 0
    phase: str = "INIT"
    current_task: Optional[str] = None
    tasks_completed: list[str] = field(default_factory=list)
    tasks_remaining: list[str] = field(default_factory=list)
    checkpoints: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=lambda: {
        "total_edits": 0,
        "total_rollbacks": 0,
        "success_rate": 1.0,
    })
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class StateManager:
    """Manages product loop state."""
    
    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self.state_file = self.workspace / ".loop_state.json"
        self.state = self._load()
    
    def _load(self) -> LoopState:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return LoopState(
                    version=data.get("version", "1.0"),
                    iteration=data.get("iteration", 0),
                    phase=data.get("phase", "INIT"),
                    current_task=data.get("current_task"),
                    tasks_completed=data.get("tasks_completed", []),
                    tasks_remaining=data.get("tasks_remaining", []),
                    checkpoints=data.get("checkpoints", []),
                    metrics=data.get("metrics", {}),
                    last_updated=data.get("last_updated", datetime.now().isoformat()),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return LoopState()
    
    def save(self) -> None:
        self.state.last_updated = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(asdict(self.state), indent=2))
    
    def start_iteration(self) -> None:
        self.state.iteration += 1
        self.state.phase = "OBSERVE"
        self.save()
    
    def set_phase(self, phase: str) -> None:
        self.state.phase = phase
        self.save()
    
    def set_current_task(self, task_id: str) -> None:
        self.state.current_task = task_id
        self.save()
    
    def complete_task(self, task_id: str) -> None:
        if task_id not in self.state.tasks_completed:
            self.state.tasks_completed.append(task_id)
        if task_id in self.state.tasks_remaining:
            self.state.tasks_remaining.remove(task_id)
        if self.state.current_task == task_id:
            self.state.current_task = None
        self.save()
    
    def add_checkpoint(self, description: str, files: list[str]) -> str:
        checkpoint_id = f"cp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.state.checkpoints.append({
            "id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "files": files,
        })
        # Keep only last 10 checkpoints
        self.state.checkpoints = self.state.checkpoints[-10:]
        self.save()
        return checkpoint_id
    
    def record_edit(self) -> None:
        self.state.metrics["total_edits"] = self.state.metrics.get("total_edits", 0) + 1
        self._update_success_rate()
        self.save()
    
    def record_rollback(self) -> None:
        self.state.metrics["total_rollbacks"] = self.state.metrics.get("total_rollbacks", 0) + 1
        self._update_success_rate()
        self.save()
    
    def _update_success_rate(self) -> None:
        edits = self.state.metrics.get("total_edits", 0)
        rollbacks = self.state.metrics.get("total_rollbacks", 0)
        if edits > 0:
            self.state.metrics["success_rate"] = round((edits - rollbacks) / edits, 2)
    
    def get_summary(self) -> dict:
        return {
            "iteration": self.state.iteration,
            "phase": self.state.phase,
            "current_task": self.state.current_task,
            "completed": len(self.state.tasks_completed),
            "remaining": len(self.state.tasks_remaining),
            "success_rate": self.state.metrics.get("success_rate", 1.0),
            "checkpoints": len(self.state.checkpoints),
        }
    
    def reset(self) -> None:
        self.state = LoopState()
        self.save()


if __name__ == "__main__":
    import sys
    
    manager = StateManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "summary":
            print(json.dumps(manager.get_summary(), indent=2))
        elif cmd == "reset":
            manager.reset()
            print("State reset")
        elif cmd == "full":
            print(json.dumps(asdict(manager.state), indent=2))
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(manager.get_summary(), indent=2))
