"""Provenance tracking for AI-generated code.

Records the lineage of every AI-generated change:
- Which AI model generated the code
- What prompt was used
- What files were modified
- Hash of input context
- Verification results

Stored in .up/provenance/ with content-addressed storage.
"""

import hashlib
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class ProvenanceEntry:
    """A single provenance record for an AI operation."""
    
    # Unique ID (content hash)
    id: str = ""
    
    # AI Model info
    ai_model: str = "unknown"  # claude, cursor, gpt-4, etc.
    ai_version: str = ""
    
    # Task info
    task_id: str = ""
    task_title: str = ""
    prompt_hash: str = ""  # Hash of the prompt sent
    prompt_preview: str = ""  # First 200 chars
    
    # Context info
    context_files: List[str] = field(default_factory=list)
    context_hash: str = ""  # Hash of all context files
    
    # Result info
    files_modified: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    
    # Git info
    commit_sha: str = ""
    branch: str = ""
    
    # Verification
    tests_passed: Optional[bool] = None
    lint_passed: Optional[bool] = None
    type_check_passed: Optional[bool] = None
    verification_notes: str = ""
    
    # Status
    status: str = "pending"  # pending, accepted, rejected, reverted
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        """Generate ID if not set."""
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate content-addressed ID."""
        content = f"{self.task_id}:{self.prompt_hash}:{self.context_hash}:{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProvenanceEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProvenanceManager:
    """Manages provenance records for AI operations."""
    
    PROVENANCE_DIR = ".up/provenance"
    INDEX_FILE = "index.json"
    
    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self.provenance_dir = self.workspace / self.PROVENANCE_DIR
        self.index_file = self.provenance_dir / self.INDEX_FILE
        self._index: Dict[str, str] = {}  # task_id -> entry_id
        self._load_index()
    
    def _load_index(self) -> None:
        """Load provenance index."""
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text())
            except json.JSONDecodeError:
                self._index = {}
    
    def _save_index(self) -> None:
        """Save provenance index."""
        self.provenance_dir.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(json.dumps(self._index, indent=2))
    
    def start_operation(
        self,
        task_id: str,
        task_title: str,
        prompt: str,
        ai_model: str = "unknown",
        context_files: List[str] = None
    ) -> ProvenanceEntry:
        """Start tracking a new AI operation.
        
        Call this before running AI generation.
        """
        # Hash the prompt
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        # Hash context files
        context_hash = ""
        if context_files:
            context_content = ""
            for f in context_files:
                path = self.workspace / f
                if path.exists():
                    try:
                        context_content += path.read_text()
                    except Exception:
                        pass
            context_hash = hashlib.sha256(context_content.encode()).hexdigest()[:16]
        
        # Get current branch
        branch = self._get_branch()
        
        entry = ProvenanceEntry(
            task_id=task_id,
            task_title=task_title,
            ai_model=ai_model,
            prompt_hash=prompt_hash,
            prompt_preview=prompt[:200] + "..." if len(prompt) > 200 else prompt,
            context_files=context_files or [],
            context_hash=context_hash,
            branch=branch,
            status="pending",
        )
        
        # Save entry
        self._save_entry(entry)
        
        # Update index
        self._index[task_id] = entry.id
        self._save_index()
        
        return entry
    
    def complete_operation(
        self,
        entry_id: str,
        files_modified: List[str] = None,
        lines_added: int = 0,
        lines_removed: int = 0,
        commit_sha: str = "",
        tests_passed: bool = None,
        lint_passed: bool = None,
        type_check_passed: bool = None,
        status: str = "accepted"
    ) -> ProvenanceEntry:
        """Complete tracking an AI operation.
        
        Call this after AI generation and verification.
        """
        entry = self._load_entry(entry_id)
        if not entry:
            raise ValueError(f"Provenance entry not found: {entry_id}")
        
        entry.files_modified = files_modified or []
        entry.lines_added = lines_added
        entry.lines_removed = lines_removed
        entry.commit_sha = commit_sha or self._get_head_sha()
        entry.tests_passed = tests_passed
        entry.lint_passed = lint_passed
        entry.type_check_passed = type_check_passed
        entry.status = status
        entry.completed_at = datetime.now().isoformat()
        
        self._save_entry(entry)
        return entry
    
    def reject_operation(self, entry_id: str, reason: str = "") -> ProvenanceEntry:
        """Mark an operation as rejected (reverted)."""
        entry = self._load_entry(entry_id)
        if not entry:
            raise ValueError(f"Provenance entry not found: {entry_id}")
        
        entry.status = "rejected"
        entry.verification_notes = reason
        entry.completed_at = datetime.now().isoformat()
        
        self._save_entry(entry)
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[ProvenanceEntry]:
        """Get a provenance entry by ID."""
        return self._load_entry(entry_id)
    
    def get_entry_for_task(self, task_id: str) -> Optional[ProvenanceEntry]:
        """Get provenance entry for a task."""
        entry_id = self._index.get(task_id)
        if entry_id:
            return self._load_entry(entry_id)
        return None
    
    def list_entries(self, limit: int = 50, status: str = None) -> List[ProvenanceEntry]:
        """List provenance entries."""
        entries = []
        
        if not self.provenance_dir.exists():
            return entries
        
        for file_path in sorted(self.provenance_dir.glob("*.json"), reverse=True):
            if file_path.name == self.INDEX_FILE:
                continue
            
            entry = self._load_entry_from_file(file_path)
            if entry:
                if status and entry.status != status:
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break
        
        return entries
    
    def get_stats(self) -> dict:
        """Get provenance statistics."""
        entries = self.list_entries(limit=1000)
        
        total = len(entries)
        accepted = sum(1 for e in entries if e.status == "accepted")
        rejected = sum(1 for e in entries if e.status == "rejected")
        pending = sum(1 for e in entries if e.status == "pending")
        
        total_lines_added = sum(e.lines_added for e in entries)
        total_lines_removed = sum(e.lines_removed for e in entries)
        
        tests_run = sum(1 for e in entries if e.tests_passed is not None)
        tests_passed = sum(1 for e in entries if e.tests_passed is True)
        
        models = {}
        for e in entries:
            models[e.ai_model] = models.get(e.ai_model, 0) + 1
        
        return {
            "total_operations": total,
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
            "acceptance_rate": accepted / total if total > 0 else 0,
            "total_lines_added": total_lines_added,
            "total_lines_removed": total_lines_removed,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "test_pass_rate": tests_passed / tests_run if tests_run > 0 else 0,
            "models_used": models,
        }
    
    def _save_entry(self, entry: ProvenanceEntry) -> None:
        """Save entry to file."""
        self.provenance_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.provenance_dir / f"{entry.id}.json"
        file_path.write_text(json.dumps(entry.to_dict(), indent=2))
    
    def _load_entry(self, entry_id: str) -> Optional[ProvenanceEntry]:
        """Load entry from file."""
        file_path = self.provenance_dir / f"{entry_id}.json"
        return self._load_entry_from_file(file_path)
    
    def _load_entry_from_file(self, file_path: Path) -> Optional[ProvenanceEntry]:
        """Load entry from file path."""
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text())
            return ProvenanceEntry.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _get_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.workspace,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""
    
    def _get_head_sha(self) -> str:
        """Get current HEAD commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.workspace,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()[:12] if result.returncode == 0 else ""
        except Exception:
            return ""


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_manager: Optional[ProvenanceManager] = None


def get_provenance_manager(workspace: Optional[Path] = None) -> ProvenanceManager:
    """Get or create the default provenance manager."""
    global _default_manager
    if _default_manager is None or (workspace and _default_manager.workspace != workspace):
        _default_manager = ProvenanceManager(workspace)
    return _default_manager


def track_ai_operation(
    task_id: str,
    task_title: str,
    prompt: str,
    ai_model: str = "unknown",
    context_files: List[str] = None,
    workspace: Optional[Path] = None
) -> ProvenanceEntry:
    """Start tracking an AI operation (convenience function)."""
    return get_provenance_manager(workspace).start_operation(
        task_id=task_id,
        task_title=task_title,
        prompt=prompt,
        ai_model=ai_model,
        context_files=context_files
    )


def complete_ai_operation(
    entry_id: str,
    files_modified: List[str] = None,
    status: str = "accepted",
    workspace: Optional[Path] = None
) -> ProvenanceEntry:
    """Complete tracking an AI operation (convenience function)."""
    return get_provenance_manager(workspace).complete_operation(
        entry_id=entry_id,
        files_modified=files_modified,
        status=status
    )
