# Research: Hardening Patterns for CLI Tools

**Created**: 2026-02-06
**Status**: Reference
**Source**: filelock docs, Click testing docs, pytest-subprocess, CAS literature

---

## Topic 1: Thread-Safe State Management

### Key Findings

1. The `filelock` library is the gold standard for Python file locking (cross-platform)
2. Atomic writes require: temp file + fsync + os.replace() (not Path.rename())
3. Read-modify-write must hold the lock for the entire cycle
4. Rolling backups (.bak) provide crash recovery

### Pattern: Safe State Save

```python
from filelock import FileLock
import json, tempfile, os

class SafeStateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._lock = FileLock(str(state_file) + ".lock")
    
    def atomic_update(self, updater_fn):
        """Thread-safe read-modify-write."""
        with self._lock:
            # Read current
            data = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
            
            # Modify
            data = updater_fn(data)
            
            # Atomic write
            fd, tmp = tempfile.mkstemp(dir=str(self.state_file.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, str(self.state_file))
            except:
                os.unlink(tmp)
                raise
    
    def save(self, data):
        """Thread-safe atomic save."""
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=str(self.state_file.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, str(self.state_file))
            except:
                os.unlink(tmp)
                raise
```

### Key Takeaways

- Use `filelock.FileLock` (not fcntl directly) for cross-platform
- Use `os.replace()` not `Path.rename()` for atomic semantics
- Always fsync before replace to prevent data loss on crash
- Use `tempfile.mkstemp()` in same directory for same-filesystem guarantee
- Lock file should be separate (`.lock` suffix) from data file

---

## Topic 2: Click CLI Testing

### Key Findings

1. Click's `CliRunner` with `isolated_filesystem()` provides full file isolation
2. `pytest-subprocess` (fp fixture) mocks all subprocess calls
3. Combined pattern: isolated_filesystem + fake_process = no side effects
4. CliRunner is NOT thread-safe (fine for tests, but don't use in production)

### Pattern: CLI Test Factory

```python
import pytest
from click.testing import CliRunner
from pathlib import Path

@pytest.fixture
def cli_runner():
    """Isolated CLI runner with temp workspace."""
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        workspace = Path(td)
        # Set up minimal .up/ structure
        (workspace / ".up").mkdir()
        (workspace / ".git").mkdir()
        yield runner, workspace

@pytest.fixture
def mock_git(fp):
    """Mock git subprocess calls."""
    fp.register(["git", "rev-parse", "--git-dir"], stdout=".git")
    fp.register(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout="main")
    fp.register(["git", fp.any()], stdout="")
    return fp

def test_save_command(cli_runner, mock_git):
    runner, workspace = cli_runner
    result = runner.invoke(save_cmd, ["--message", "test"])
    assert result.exit_code == 0
    assert "Checkpoint created" in result.output
```

### Key Takeaways

- Use `isolated_filesystem()` for every test that touches files
- Use `pytest-subprocess` to mock git/AI CLI calls
- Test exit codes, output text, and file side effects
- Create fixtures for common setups (git repo, .up/ directory)
- Test error paths (missing git, corrupted state, etc.)

---

## Topic 3: Content-Addressed Storage

### Key Findings

1. True CAS hashes ONLY content, never metadata (timestamps, paths, etc.)
2. Git's model: hash = sha256(type + size + content)
3. Metadata that changes (timestamps) must be OUTSIDE the hash
4. Deduplication: check for existing hash before creating new entry
5. Merkle chains: include parent hash in child for chain integrity

### Pattern: Proper Content-Addressed Provenance

```python
import hashlib
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ProvenanceEntry:
    # Content fields (hashed)
    task_id: str
    prompt_hash: str
    context_hash: str
    model: str
    files_touched: list[str]
    
    # Metadata fields (NOT hashed)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"
    parent_id: str = ""  # For chain integrity
    
    # Derived
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = self._content_hash()
    
    def _content_hash(self) -> str:
        """Hash ONLY content fields, not metadata."""
        content = "|".join([
            self.task_id,
            self.prompt_hash,
            self.context_hash,
            self.model,
            ",".join(sorted(self.files_touched)),
            self.parent_id,  # Chain integrity
        ])
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def exists(self, storage_dir: Path) -> bool:
        """Check if this exact content already exists."""
        return (storage_dir / f"{self.id}.json").exists()
```

### Key Takeaways

- Never include timestamps in content hash
- Include parent hash for Merkle chain integrity
- Sort list fields before hashing for determinism
- Use 16+ chars of hash to avoid collisions
- Check for existing entries before creating (dedup)
- Store metadata alongside but separate from content hash

---

## Applicable to up-cli

### Immediate Fixes
1. Add `filelock` dependency, wrap StateManager.save() with lock
2. Use `os.replace()` + fsync instead of `Path.rename()`
3. Remove `created_at` from ProvenanceEntry hash
4. Add `pytest-subprocess` to dev deps, create test fixtures

### Architecture Improvements
1. `StateManager.atomic_update(fn)` pattern for read-modify-write
2. Test factory fixtures for isolated CLI testing
3. Proper deduplication in provenance storage
4. Merkle chain with parent_id in provenance entries
