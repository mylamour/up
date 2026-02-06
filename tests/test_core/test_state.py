"""Tests for up.core.state module."""

import json
import threading
from pathlib import Path

import pytest

from up.core.state import (
    StateManager,
    UnifiedState,
    UpConfig,
    LoopState,
    CircuitBreakerState,
    ContextState,
    AgentState,
)


class TestUnifiedState:
    """Tests for UnifiedState dataclass."""

    def test_default_state(self):
        state = UnifiedState()
        assert state.version == "2.0"
        assert state.loop.iteration == 0
        assert state.loop.phase == "IDLE"
        assert state.metrics.success_rate == 0

    def test_to_dict_roundtrip(self):
        state = UnifiedState()
        state.loop.iteration = 5
        state.loop.current_task = "US-001"
        state.checkpoints = ["cp-1", "cp-2"]

        data = state.to_dict()
        restored = UnifiedState.from_dict(data)

        assert restored.loop.iteration == 5
        assert restored.loop.current_task == "US-001"
        assert restored.checkpoints == ["cp-1", "cp-2"]

    def test_circuit_breaker_get_or_create(self):
        state = UnifiedState()
        cb = state.get_circuit_breaker("test")
        assert cb.state == "CLOSED"
        assert cb.failures == 0

        # Same name returns same instance
        cb2 = state.get_circuit_breaker("test")
        assert cb is cb2

    def test_circuit_breaker_with_config(self):
        state = UnifiedState()
        config = UpConfig(circuit_breaker_failure_threshold=5, circuit_breaker_cooldown_minutes=10)
        cb = state.get_circuit_breaker("custom", config)
        assert cb.failure_threshold == 5
        assert cb.cooldown_minutes == 10


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState."""

    def test_record_failure_opens_circuit(self):
        cb = CircuitBreakerState(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED"
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.failures == 3

    def test_record_success_resets_from_half_open(self):
        cb = CircuitBreakerState(state="HALF_OPEN", failures=2)
        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failures == 0

    def test_can_execute(self):
        cb = CircuitBreakerState()
        assert cb.can_execute() is True
        cb.state = "OPEN"
        cb.opened_at = None
        assert cb.can_execute() is False

    def test_is_open(self):
        cb = CircuitBreakerState()
        assert cb.is_open() is False
        cb.state = "OPEN"
        assert cb.is_open() is True


class TestContextState:
    """Tests for ContextState."""

    def test_usage_percent(self):
        ctx = ContextState(budget=100_000, total_tokens=80_000)
        assert ctx.usage_percent == 80.0

    def test_remaining_tokens(self):
        ctx = ContextState(budget=100_000, total_tokens=60_000)
        assert ctx.remaining_tokens == 40_000

    def test_status_levels(self):
        ctx = ContextState(budget=100_000, total_tokens=50_000)
        assert ctx.status == "OK"
        ctx.total_tokens = 85_000
        assert ctx.status == "WARNING"
        ctx.total_tokens = 95_000
        assert ctx.status == "CRITICAL"


class TestStateManager:
    """Tests for StateManager."""

    def test_load_creates_fresh_state(self, workspace):
        sm = StateManager(workspace)
        state = sm.load()
        assert isinstance(state, UnifiedState)
        assert state.loop.iteration == 0

    def test_save_and_load(self, workspace):
        sm = StateManager(workspace)
        state = sm.load()
        state.loop.iteration = 42
        state.loop.current_task = "BF-001"
        sm.save()

        sm2 = StateManager(workspace)
        loaded = sm2.load()
        assert loaded.loop.iteration == 42
        assert loaded.loop.current_task == "BF-001"

    def test_save_creates_backup(self, workspace):
        sm = StateManager(workspace)
        sm.load()
        sm.save()  # First save, no backup source
        sm.save()  # Second save creates backup

        bak = workspace / ".up" / "state.json.bak"
        assert bak.exists()

    def test_load_recovers_from_corrupt_state(self, workspace):
        sm = StateManager(workspace)
        state = sm.load()
        state.loop.iteration = 77
        sm.save()
        # Save again to create backup of iteration=77
        state.loop.iteration = 88
        sm.save()

        # Corrupt main file
        state_file = workspace / ".up" / "state.json"
        state_file.write_text("{corrupted!")

        sm2 = StateManager(workspace)
        recovered = sm2.load()
        assert recovered.loop.iteration == 77  # Recovered from backup

    def test_state_property_lazy_loads(self, workspace):
        sm = StateManager(workspace)
        assert sm._state is None
        _ = sm.state
        assert sm._state is not None

    def test_reset(self, state_manager_with_state):
        sm = state_manager_with_state
        assert sm.state.loop.iteration == 5
        sm.reset()
        assert sm.state.loop.iteration == 0

    def test_update_loop(self, state_manager):
        sm = state_manager
        sm.load()
        sm.update_loop(iteration=10, phase="VERIFY")
        assert sm.state.loop.iteration == 10
        assert sm.state.loop.phase == "VERIFY"

    def test_record_task_complete(self, state_manager):
        sm = state_manager
        sm.load()
        sm.record_task_complete("US-001")
        assert "US-001" in sm.state.loop.tasks_completed
        assert sm.state.metrics.completed_tasks == 1
        assert sm.state.loop.consecutive_failures == 0

    def test_record_task_failed(self, state_manager):
        sm = state_manager
        sm.load()
        sm.record_task_failed("US-002")
        assert "US-002" in sm.state.loop.tasks_failed
        assert sm.state.metrics.failed_tasks == 1
        assert sm.state.loop.consecutive_failures == 1

    def test_doom_loop_detection(self, state_manager):
        sm = state_manager
        sm.load()

        # Not in doom loop yet
        is_doom, msg = sm.check_doom_loop()
        assert is_doom is False

        # Trigger 3 failures
        sm.record_task_failed("t1")
        sm.record_task_failed("t2")
        sm.record_task_failed("t3")
        is_doom, msg = sm.check_doom_loop()
        assert is_doom is True
        assert "DOOM LOOP" in msg

    def test_add_and_remove_agent(self, state_manager):
        sm = state_manager
        sm.load()
        agent = AgentState(task_id="agent-1", task_title="Test Agent")
        sm.add_agent(agent)
        assert "agent-1" in sm.state.agents
        assert "agent-1" in sm.state.parallel.agents

        sm.remove_agent("agent-1")
        assert "agent-1" not in sm.state.agents
        assert "agent-1" not in sm.state.parallel.agents

    def test_add_checkpoint(self, state_manager):
        sm = state_manager
        sm.load()
        sm.add_checkpoint("cp-001")
        assert "cp-001" in sm.state.checkpoints
        assert sm.state.loop.last_checkpoint == "cp-001"
        assert sm.state.metrics.total_checkpoints == 1

    def test_checkpoint_retention(self, workspace):
        sm = StateManager(workspace)
        sm.load()
        sm.update_config(checkpoint_retention_count=3)

        for i in range(5):
            sm.add_checkpoint(f"cp-{i}")

        assert len(sm.state.checkpoints) == 3
        assert sm.state.checkpoints == ["cp-2", "cp-3", "cp-4"]

    def test_atomic_update(self, workspace):
        sm = StateManager(workspace)
        sm.load()
        sm.save()

        sm.atomic_update(lambda s: setattr(s.loop, "iteration", 99))

        sm2 = StateManager(workspace)
        assert sm2.load().loop.iteration == 99

    def test_update_config(self, workspace):
        sm = StateManager(workspace)
        sm.load()
        sm.update_config(doom_loop_threshold=5)
        assert sm.config.doom_loop_threshold == 5

        # Config persists
        sm2 = StateManager(workspace)
        assert sm2.config.doom_loop_threshold == 5

    def test_migrate_old_loop_state(self, workspace):
        old_file = workspace / ".loop_state.json"
        old_file.write_text(json.dumps({
            "iteration": 10,
            "phase": "EXECUTE",
            "current_task": "US-003",
        }))

        sm = StateManager(workspace)
        state = sm.load()
        assert state.loop.iteration == 10
        assert state.loop.current_task == "US-003"

    def test_lock_file_created(self, workspace):
        sm = StateManager(workspace)
        sm.load()
        sm.save()
        lock_file = workspace / ".up" / "state.json.lock"
        assert lock_file.exists()

    def test_concurrent_saves(self, workspace):
        """Verify concurrent saves don't corrupt state."""
        sm = StateManager(workspace)
        sm.load()
        sm.save()

        errors = []

        def do_update(iteration_value):
            try:
                mgr = StateManager(workspace)
                mgr.atomic_update(
                    lambda s: setattr(s.loop, "iteration", iteration_value)
                )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=do_update, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent errors: {errors}"

        # State should be valid JSON
        final = StateManager(workspace).load()
        assert isinstance(final.loop.iteration, int)
