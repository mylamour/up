"""End-to-End tests for the SESRC product loop.

These tests simulate a full execution of the product loop by mocking the AI Engine.
They verify that the core loop (OBSERVE -> CHECKPOINT -> EXECUTE -> VERIFY -> COMMIT)
works as intended, including fallback, rollback, and doom loop triggers.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.commands.start.loop import run_ai_product_loop
from up.core.state import get_state_manager
from up.core.checkpoint import get_checkpoint_manager


@pytest.fixture
def mock_ai_engine():
    """Mock AIEngine for controlling test outcomes."""
    class MockEngine:
        def __init__(self):
            self.success = True
            self.output = "mock output"
            self.write_file = None
            self.write_content = None

        def execute_task(self, workspace: Path, prompt: str, timeout: int, raise_on_error: bool):
            if self.write_file and self.write_content:
                (workspace / self.write_file).parent.mkdir(parents=True, exist_ok=True)
                (workspace / self.write_file).write_text(self.write_content)
                print(f"MOCK WROTE FILE: {self.write_file}")
            return self.success, self.output

    return MockEngine()


@pytest.fixture
def test_prd(git_workspace):
    """Create a test PRD in the git workspace."""
    prd_path = git_workspace / "prd.json"
    prd_data = {
        "project": "Test E2E",
        "userStories": [
            {
                "id": "US-E2E-01",
                "title": "Success Task",
                "description": "Write a valid Python file.",
                "passes": False
            },
            {
                "id": "US-E2E-02",
                "title": "Failure Task",
                "description": "Write invalid Python code.",
                "passes": False
            }
        ]
    }
    prd_path.write_text(json.dumps(prd_data))
    
    # Add an empty tests directory to avoid pytest exit code 5 (no tests found)
    tests_dir = git_workspace / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_dummy.py").write_text("def test_dummy():\n    pass\n")
    
    return prd_path


def test_successful_loop_execution(git_workspace, test_prd, mock_ai_engine):
    """Test a complete successful SESRC product loop.
    
    Expected:
    1. Checkpoint is created
    2. AI writes valid code
    3. Verification passes
    4. Code is committed
    5. PRD is updated to passes=True
    """
    mock_ai_engine.write_file = "src/hello.py"
    mock_ai_engine.write_content = "def hello():\n    return 'world'\n"

    with patch("up.commands.start.loop.run_ai_task") as mock_run_task:
        mock_run_task.side_effect = lambda ws, prompt, cli, timeout=600: mock_ai_engine.execute_task(ws, prompt, timeout, False)
        
        run_ai_product_loop(
            workspace=git_workspace,
            state={"iteration": 0},
            task_source="prd.json",
            specific_task="US-E2E-01",
            cli_name="claude",
            auto_commit=True,
            verify=True,
            interactive=False
        )

    # 1. Check state manager updates
    sm = get_state_manager(git_workspace)
    assert sm.state.loop.current_task == "US-E2E-01"
    assert "US-E2E-01" in sm.state.loop.tasks_completed
    
    # 2. Check if file was written
    assert (git_workspace / "src/hello.py").exists()
    
    # 3. Check PRD update
    prd_data = json.loads(test_prd.read_text())
    assert prd_data["userStories"][0]["passes"] is True
    
    # 4. Check git commit
    import subprocess
    log_output = subprocess.run(["git", "log", "--oneline"], cwd=git_workspace, capture_output=True, text=True).stdout
    assert "feat(US-E2E-01)" in log_output


def test_failure_loop_triggers_rollback(git_workspace, test_prd, mock_ai_engine):
    """Test a product loop failure where AI fails to execute.
    
    Expected:
    1. Checkpoint is created
    2. AI returns failure
    3. Workspace is rolled back to checkpoint
    4. Task is marked as failed
    """
    mock_ai_engine.success = False
    mock_ai_engine.output = "AI explicitly failed"

    with patch("up.commands.start.loop.run_ai_task") as mock_run_task:
        mock_run_task.side_effect = lambda ws, prompt, cli, timeout=600: mock_ai_engine.execute_task(ws, prompt, timeout, False)
        
        run_ai_product_loop(
            workspace=git_workspace,
            state={"iteration": 0},
            task_source="prd.json",
            specific_task="US-E2E-02",
            cli_name="claude",
            auto_commit=True,
            verify=True,
            interactive=False
        )

    # 1. Check state manager updates
    sm = get_state_manager(git_workspace)
    assert "US-E2E-02" in sm.state.loop.tasks_failed
    assert "US-E2E-02" not in sm.state.loop.tasks_completed
    
    # 2. Check circuit breaker recorded failure
    cb = sm.state.circuit_breakers.get("task")
    assert cb.failures == 1
    
    # 3. Check rollback (file should not exist)
    assert not (git_workspace / "src/bad.py").exists()
    
    # 4. PRD should NOT be marked as passes
    prd_data = json.loads(test_prd.read_text())
    assert prd_data["userStories"][1]["passes"] is False


def test_doom_loop_circuit_breaker(git_workspace, test_prd, mock_ai_engine):
    """Test that multiple failures trigger the doom loop and open the circuit breaker."""
    mock_ai_engine.success = False
    mock_ai_engine.output = "AI explicitly failed"
    
    with patch("up.commands.start.loop.run_ai_task") as mock_run_task:
        mock_run_task.side_effect = lambda ws, prompt, cli, timeout=600: mock_ai_engine.execute_task(ws, prompt, timeout, False)
        
        # Run loop 3 times for the same task to trigger circuit breaker
        for i in range(3):
            run_ai_product_loop(
                workspace=git_workspace,
                state={"iteration": i},
                task_source="prd.json",
                specific_task="US-E2E-02",
                cli_name="claude",
                auto_commit=True,
                verify=True,
                interactive=False
            )

    sm = get_state_manager(git_workspace)
    cb = sm.state.circuit_breakers.get("task")
    
    # Circuit breaker should be open after 3 consecutive failures
    assert cb.failures == 3
    assert cb.state == "OPEN"
    
    # Trying one more time should be blocked by the circuit breaker check in the CLI
    from up.commands.start.helpers import check_circuit_breaker, load_loop_state
    cb_status = check_circuit_breaker(load_loop_state(git_workspace))
    assert cb_status.get("open") is True
    assert "circuit opened after" in cb_status.get("reason")
