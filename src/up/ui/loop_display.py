"""Product Loop Display - Cybersecurity/AI themed dashboard.

A real-time, refreshing terminal UI for the UP product loop.
Auto-detects terminal size and adapts layout accordingly.
"""

from __future__ import annotations

import shutil
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    SpinnerColumn,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text

from up.ui.theme import CyberTheme, THEME, Symbols


class TaskStatus(Enum):
    """Status of a task in the queue."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class LoopStatus(Enum):
    """Overall loop status."""
    IDLE = "idle"
    RUNNING = "running"
    VERIFYING = "verifying"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETE = "complete"


@dataclass
class TaskInfo:
    """Information about a task."""
    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    priority: str = "medium"
    effort: str = "medium"
    phase: str = ""
    description: str = ""


@dataclass
class LoopStats:
    """Statistics for the loop."""
    elapsed_seconds: float = 0.0
    failures: int = 0
    rollbacks: int = 0
    completed: int = 0
    total: int = 0
    current_iteration: int = 0


@dataclass
class DisplayState:
    """Current state of the display."""
    status: LoopStatus = LoopStatus.IDLE
    current_task: Optional[TaskInfo] = None
    current_phase: str = "INIT"
    tasks: list[TaskInfo] = field(default_factory=list)
    stats: LoopStats = field(default_factory=LoopStats)
    log_entries: deque = field(default_factory=lambda: deque(maxlen=6))
    start_time: Optional[datetime] = None


class ProductLoopDisplay:
    """Real-time product loop dashboard with cybersecurity/AI theme.
    
    Features:
    - Auto-detects terminal size (compact vs full layout)
    - Real-time refresh using Rich Live
    - Animated progress bars
    - Status indicators with color coding
    - Scrolling activity log
    
    Usage:
        display = ProductLoopDisplay()
        display.start()
        
        display.set_tasks(tasks)
        display.update_task_status("C-001", TaskStatus.IN_PROGRESS)
        display.log("Starting implementation...")
        
        display.stop()
    """
    
    # Layout thresholds
    COMPACT_WIDTH = 80
    COMPACT_HEIGHT = 24
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the display.
        
        Args:
            console: Rich console instance (created if not provided)
        """
        self.console = console or Console(theme=THEME)
        self.state = DisplayState()
        self.live: Optional[Live] = None
        self._running = False
        self._spinner_frame = 0
        self._last_update = time.time()
        
    def start(self) -> None:
        """Start the live display."""
        if self._running:
            return
            
        self.state.start_time = datetime.now()
        self.state.status = LoopStatus.RUNNING
        self._running = True
        
        # Create live display with appropriate refresh rate
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self.live.start()
        
    def stop(self) -> None:
        """Stop the live display."""
        if not self._running:
            return
            
        self._running = False
        if self.live:
            self.live.stop()
            self.live = None
            
    def update(self) -> None:
        """Force update the display."""
        if self.live and self._running:
            self._update_elapsed()
            self._spinner_frame = (self._spinner_frame + 1) % len(Symbols.SPINNER)
            self.live.update(self._render())
            
    def _update_elapsed(self) -> None:
        """Update elapsed time."""
        if self.state.start_time:
            delta = datetime.now() - self.state.start_time
            self.state.stats.elapsed_seconds = delta.total_seconds()
    
    # ─── State Setters ───────────────────────────────────────────────────
    
    def set_status(self, status: LoopStatus) -> None:
        """Set the overall loop status."""
        self.state.status = status
        self.update()
        
    def set_tasks(self, tasks: list[dict]) -> None:
        """Set the task queue from PRD task dicts."""
        self.state.tasks = []
        for t in tasks:
            task_info = TaskInfo(
                id=t.get("id", ""),
                title=t.get("title", ""),
                priority=t.get("priority", "medium"),
                effort=t.get("effort", "medium"),
                phase=t.get("phase", ""),
                description=t.get("description", ""),
                status=TaskStatus.COMPLETE if t.get("passes") else TaskStatus.PENDING,
            )
            self.state.tasks.append(task_info)
            
        self.state.stats.total = len(tasks)
        self.state.stats.completed = sum(1 for t in self.state.tasks if t.status == TaskStatus.COMPLETE)
        self.update()
        
    def set_current_task(self, task_id: str, phase: str = "EXECUTE") -> None:
        """Set the current task being processed."""
        self.state.current_phase = phase
        
        for task in self.state.tasks:
            if task.id == task_id:
                task.status = TaskStatus.IN_PROGRESS
                self.state.current_task = task
                break
                
        self.update()
        
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update a task's status."""
        for task in self.state.tasks:
            if task.id == task_id:
                task.status = status
                
                if status == TaskStatus.COMPLETE:
                    self.state.stats.completed += 1
                elif status == TaskStatus.FAILED:
                    self.state.stats.failures += 1
                elif status == TaskStatus.ROLLED_BACK:
                    self.state.stats.rollbacks += 1
                break
                
        # Clear current task if it's the one being updated
        if self.state.current_task and self.state.current_task.id == task_id:
            if status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.ROLLED_BACK):
                self.state.current_task = None
                
        self.update()
        
    def set_phase(self, phase: str) -> None:
        """Set the current phase."""
        self.state.current_phase = phase
        if phase == "VERIFY":
            self.state.status = LoopStatus.VERIFYING
        elif phase == "EXECUTE":
            self.state.status = LoopStatus.RUNNING
        self.update()
        
    def increment_iteration(self) -> None:
        """Increment the iteration counter."""
        self.state.stats.current_iteration += 1
        self.update()
        
    def log(self, message: str, style: str = "") -> None:
        """Add a log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = (timestamp, message, style)
        self.state.log_entries.append(entry)
        self.update()
        
    def log_success(self, message: str) -> None:
        """Add a success log entry."""
        self.log(f"{Symbols.COMPLETE} {message}", "task.complete")
        
    def log_error(self, message: str) -> None:
        """Add an error log entry."""
        self.log(f"{Symbols.FAILED} {message}", "task.failed")
        
    def log_warning(self, message: str) -> None:
        """Add a warning log entry."""
        self.log(f"⚠ {message}", "task.skipped")
    
    # ─── Rendering ───────────────────────────────────────────────────────
    
    def _get_terminal_size(self) -> tuple[int, int]:
        """Get terminal dimensions."""
        size = shutil.get_terminal_size((80, 24))
        return size.columns, size.lines
        
    def _is_compact(self) -> bool:
        """Check if we should use compact layout."""
        width, height = self._get_terminal_size()
        return width < self.COMPACT_WIDTH or height < self.COMPACT_HEIGHT
        
    def _render(self) -> RenderableType:
        """Render the dashboard."""
        if self._is_compact():
            return self._render_compact()
        return self._render_full()
        
    def _render_full(self) -> Panel:
        """Render full layout dashboard."""
        layout = Layout()
        
        # Main structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=3),
            Layout(name="main", ratio=1),
            Layout(name="log", size=10),
            Layout(name="stats", size=3),
            Layout(name="footer", size=1),
        )
        
        # Split main into current task and queue
        layout["main"].split_row(
            Layout(name="current", ratio=1),
            Layout(name="queue", ratio=1),
        )
        
        # Render components
        layout["header"].update(self._render_header())
        layout["progress"].update(self._render_progress_bar())
        layout["current"].update(self._render_current_task())
        layout["queue"].update(self._render_task_queue())
        layout["log"].update(self._render_log())
        layout["stats"].update(self._render_stats())
        layout["footer"].update(self._render_footer())
        
        return Panel(
            layout,
            border_style=Style(color=CyberTheme.BORDER),
            padding=0,
        )
        
    def _render_compact(self) -> Panel:
        """Render compact layout for small terminals."""
        parts = []
        
        # Header with status
        parts.append(self._render_compact_header())
        parts.append("")
        
        # Progress
        parts.append(self._render_compact_progress())
        parts.append("")
        
        # Current task (one line)
        if self.state.current_task:
            task = self.state.current_task
            parts.append(Text(f"  Current: {task.id} {task.title[:30]}...", style="task.progress"))
            parts.append(Text(f"  Phase:   {self.state.current_phase}", style="text.dim"))
        else:
            parts.append(Text("  Current: None", style="text.dim"))
            
        parts.append("")
        
        # Compact task list
        parts.append(self._render_compact_tasks())
        parts.append("")
        
        # Stats line
        stats = self.state.stats
        elapsed = self._format_duration(stats.elapsed_seconds)
        parts.append(Text(
            f"  ⏱ {elapsed}  {Symbols.FAILED} {stats.failures} fails  {Symbols.ROLLBACK} {stats.rollbacks} rollbacks",
            style="text.dim"
        ))
        
        return Panel(
            Group(*parts),
            title=f"[title]UP LOOP[/]",
            subtitle="[text.dim]Ctrl+C to pause[/]",
            border_style=Style(color=CyberTheme.BORDER),
        )
        
    def _render_header(self) -> Panel:
        """Render the header with status badge."""
        status = self.state.status
        spinner = Symbols.SPINNER[self._spinner_frame] if status == LoopStatus.RUNNING else ""
        
        status_styles = {
            LoopStatus.RUNNING: ("status.running", f"{spinner} RUNNING"),
            LoopStatus.VERIFYING: ("status.verifying", "◉ VERIFYING"),
            LoopStatus.PAUSED: ("status.paused", "◉ PAUSED"),
            LoopStatus.FAILED: ("status.failed", "◉ FAILED"),
            LoopStatus.COMPLETE: ("status.complete", "◉ COMPLETE"),
            LoopStatus.IDLE: ("text.dim", "◉ IDLE"),
        }
        
        style, label = status_styles.get(status, ("text.dim", "◉ UNKNOWN"))
        
        title_text = Text()
        title_text.append("  UP ", style="title")
        title_text.append("PRODUCT LOOP", style="secondary")
        title_text.append(" " * 30)
        title_text.append(label, style=style)
        title_text.append("  ")
        
        return Panel(
            Align.center(title_text),
            border_style=Style(color=CyberTheme.BORDER_DIM),
            padding=0,
        )
        
    def _render_compact_header(self) -> Text:
        """Render compact header."""
        status = self.state.status
        spinner = Symbols.SPINNER[self._spinner_frame] if status == LoopStatus.RUNNING else "●"
        
        status_colors = {
            LoopStatus.RUNNING: CyberTheme.STATUS_RUNNING,
            LoopStatus.VERIFYING: CyberTheme.STATUS_VERIFYING,
            LoopStatus.PAUSED: CyberTheme.STATUS_PAUSED,
            LoopStatus.FAILED: CyberTheme.STATUS_FAILED,
            LoopStatus.COMPLETE: CyberTheme.STATUS_COMPLETE,
        }
        
        color = status_colors.get(status, CyberTheme.TEXT_DIM)
        
        header = Text()
        header.append(f"  {spinner} ", style=Style(color=color))
        header.append("UP LOOP", style="title")
        header.append(f" │ {status.value.upper()}", style=Style(color=color))
        
        return header
        
    def _render_progress_bar(self) -> Panel:
        """Render the animated progress bar."""
        stats = self.state.stats
        total = stats.total or 1
        completed = stats.completed
        percentage = (completed / total) * 100
        
        # Create progress bar
        width = 40
        filled = int(width * completed / total)
        
        bar = Text()
        bar.append("  Progress  ", style="text.dim")
        bar.append(Symbols.BAR_FULL * filled, style="progress.complete")
        bar.append(Symbols.BAR_EMPTY * (width - filled), style="progress.remaining")
        bar.append(f"  {percentage:5.1f}%", style="primary")
        bar.append(f"  ({completed}/{total} tasks)", style="text.dim")
        
        return Panel(
            Align.center(bar),
            border_style=Style(color=CyberTheme.BORDER_DIM),
            padding=0,
        )
        
    def _render_compact_progress(self) -> Text:
        """Render compact progress bar."""
        stats = self.state.stats
        total = stats.total or 1
        completed = stats.completed
        percentage = (completed / total) * 100
        
        width = 25
        filled = int(width * completed / total)
        
        bar = Text()
        bar.append("  ", style="text")
        bar.append(Symbols.BAR_FULL * filled, style="progress.complete")
        bar.append(Symbols.BAR_EMPTY * (width - filled), style="progress.remaining")
        bar.append(f" {percentage:5.1f}% ({completed}/{total})", style="primary")
        
        return bar
        
    def _render_current_task(self) -> Panel:
        """Render current task panel."""
        task = self.state.current_task
        
        if not task:
            content = Text("\n  No task in progress\n", style="text.dim")
            return Panel(
                content,
                title="[title]Current Task[/]",
                border_style=Style(color=CyberTheme.BORDER_DIM),
            )
            
        lines = []
        lines.append("")
        lines.append(Text(f"  {task.id}: {task.title}", style="task.progress"))
        lines.append("")
        lines.append(Text(f"  Priority: {task.priority}  │  Effort: {task.effort}  │  Phase: {task.phase}", style="text.dim"))
        lines.append("")
        
        # Current phase indicator
        phase = self.state.current_phase
        phase_icon = {
            "INIT": "○",
            "CHECKPOINT": "◐",
            "EXECUTE": Symbols.SPINNER[self._spinner_frame],
            "VERIFY": "◑",
            "COMMIT": "◒",
        }.get(phase, "○")
        
        lines.append(Text(f"  Status: {phase_icon} {phase}", style="status.running"))
        lines.append("")
        
        if task.description:
            desc = task.description[:60] + "..." if len(task.description) > 60 else task.description
            lines.append(Text(f"  {desc}", style="text.dim"))
            
        return Panel(
            Group(*lines),
            title="[title]Current Task[/]",
            border_style=Style(color=CyberTheme.PRIMARY),
        )
        
    def _render_task_queue(self) -> Panel:
        """Render task queue panel."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            expand=True,
        )
        
        table.add_column("Status", width=3)
        table.add_column("ID", width=8)
        table.add_column("Title", ratio=1)
        table.add_column("State", width=12, justify="right")
        
        status_symbols = {
            TaskStatus.COMPLETE: (Symbols.COMPLETE, "task.complete"),
            TaskStatus.IN_PROGRESS: (Symbols.IN_PROGRESS, "task.progress"),
            TaskStatus.PENDING: (Symbols.PENDING, "task.pending"),
            TaskStatus.FAILED: (Symbols.FAILED, "task.failed"),
            TaskStatus.SKIPPED: (Symbols.SKIPPED, "task.skipped"),
            TaskStatus.ROLLED_BACK: (Symbols.ROLLBACK, "task.skipped"),
        }
        
        for task in self.state.tasks[:8]:  # Show max 8 tasks
            symbol, style = status_symbols.get(task.status, (Symbols.PENDING, "task.pending"))
            
            title = task.title[:30] + "..." if len(task.title) > 30 else task.title
            state_label = task.status.value.replace("_", " ")
            
            table.add_row(
                Text(symbol, style=style),
                Text(task.id, style=style),
                Text(title, style=style if task.status == TaskStatus.IN_PROGRESS else "text"),
                Text(state_label, style=style),
            )
            
        # Show count if more tasks
        remaining = len(self.state.tasks) - 8
        if remaining > 0:
            table.add_row(
                Text("", style="text.dim"),
                Text("", style="text.dim"),
                Text(f"... +{remaining} more tasks", style="text.dim"),
                Text("", style="text.dim"),
            )
            
        return Panel(
            table,
            title="[title]Task Queue[/]",
            border_style=Style(color=CyberTheme.BORDER_DIM),
        )
        
    def _render_compact_tasks(self) -> Text:
        """Render compact task indicators."""
        status_symbols = {
            TaskStatus.COMPLETE: (Symbols.COMPLETE, CyberTheme.TASK_COMPLETE),
            TaskStatus.IN_PROGRESS: (Symbols.IN_PROGRESS, CyberTheme.TASK_IN_PROGRESS),
            TaskStatus.PENDING: (Symbols.PENDING, CyberTheme.TASK_PENDING),
            TaskStatus.FAILED: (Symbols.FAILED, CyberTheme.TASK_FAILED),
            TaskStatus.SKIPPED: (Symbols.SKIPPED, CyberTheme.TASK_SKIPPED),
            TaskStatus.ROLLED_BACK: (Symbols.ROLLBACK, CyberTheme.TASK_SKIPPED),
        }
        
        text = Text("  ")
        for task in self.state.tasks[:12]:
            symbol, color = status_symbols.get(task.status, (Symbols.PENDING, CyberTheme.TASK_PENDING))
            text.append(f"{symbol} {task.id}  ", style=Style(color=color))
            
        return text
        
    def _render_log(self) -> Panel:
        """Render activity log panel."""
        lines = []
        
        for timestamp, message, style in self.state.log_entries:
            line = Text()
            line.append(f"  {timestamp}  ", style="text.dim")
            line.append(message[:60], style=style or "text")
            lines.append(line)
            
        # Pad with empty lines if needed
        while len(lines) < 6:
            lines.append(Text(""))
            
        return Panel(
            Group(*lines),
            title="[title]Activity Log[/]",
            border_style=Style(color=CyberTheme.BORDER_DIM),
        )
        
    def _render_stats(self) -> Panel:
        """Render stats panel."""
        stats = self.state.stats
        elapsed = self._format_duration(stats.elapsed_seconds)
        
        text = Text()
        text.append("  ⏱  ", style="text.dim")
        text.append(f"Elapsed: {elapsed}", style="primary")
        text.append("    │    ", style="text.dim")
        text.append(f"{Symbols.FAILED} ", style="task.failed")
        text.append(f"Failures: {stats.failures}", style="text")
        text.append("    │    ", style="text.dim")
        text.append(f"{Symbols.ROLLBACK} ", style="task.skipped")
        text.append(f"Rollbacks: {stats.rollbacks}", style="text")
        text.append("    │    ", style="text.dim")
        text.append(f"Iteration: {stats.current_iteration}", style="secondary")
        
        return Panel(
            Align.center(text),
            border_style=Style(color=CyberTheme.BORDER_DIM),
            padding=0,
        )
        
    def _render_footer(self) -> Text:
        """Render footer."""
        return Text("  Press Ctrl+C to pause  │  q to quit", style="text.dim", justify="center")
        
    def _format_duration(self, seconds: float) -> str:
        """Format duration as human readable string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


# ─── Context Manager Support ─────────────────────────────────────────────

class ProductLoopDisplayContext:
    """Context manager for the display."""
    
    def __init__(self, display: ProductLoopDisplay):
        self.display = display
        
    def __enter__(self) -> ProductLoopDisplay:
        self.display.start()
        return self.display
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.display.stop()
        return False


def create_display(console: Optional[Console] = None) -> ProductLoopDisplayContext:
    """Create a display context manager.
    
    Usage:
        with create_display() as display:
            display.set_tasks(tasks)
            display.log("Starting...")
            # ... do work ...
    """
    display = ProductLoopDisplay(console)
    return ProductLoopDisplayContext(display)
