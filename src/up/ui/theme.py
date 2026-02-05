"""Cybersecurity/AI Theme for UP-CLI.

A dark, neon-accented theme inspired by cyberpunk aesthetics
and AI terminal interfaces.
"""

from dataclasses import dataclass
from rich.style import Style
from rich.theme import Theme


@dataclass
class CyberTheme:
    """Cybersecurity/AI color palette."""
    
    # Primary colors
    PRIMARY = "#00FFFF"      # Cyan - main accent
    SECONDARY = "#00FF41"    # Matrix green
    ACCENT = "#FF00FF"       # Neon magenta
    
    # Status colors
    SUCCESS = "#00FF41"      # Bright green
    WARNING = "#FFB000"      # Amber
    ERROR = "#FF0040"        # Neon red
    INFO = "#00BFFF"         # Deep sky blue
    
    # UI colors
    BORDER = "#00FFFF"       # Cyan borders
    BORDER_DIM = "#006666"   # Dimmed cyan
    TEXT = "#FFFFFF"         # Bright white
    TEXT_DIM = "#666666"     # Gray
    TEXT_MUTED = "#404040"   # Dark gray
    
    # Background accents (for contrast)
    BG_HIGHLIGHT = "#001a1a" # Very dark cyan tint
    
    # Progress bar colors
    PROGRESS_COMPLETE = "#00FF41"
    PROGRESS_REMAINING = "#333333"
    PROGRESS_PULSE = "#00FFFF"
    
    # Status indicators
    STATUS_RUNNING = "#00FF41"
    STATUS_PAUSED = "#00BFFF"
    STATUS_FAILED = "#FF0040"
    STATUS_COMPLETE = "#00FF41"
    STATUS_VERIFYING = "#FFB000"
    
    # Task status
    TASK_COMPLETE = "#00FF41"
    TASK_IN_PROGRESS = "#00FFFF"
    TASK_PENDING = "#666666"
    TASK_FAILED = "#FF0040"
    TASK_SKIPPED = "#FFB000"


# Rich theme for console styling
THEME = Theme({
    # Status styles
    "status.running": Style(color=CyberTheme.STATUS_RUNNING, bold=True),
    "status.paused": Style(color=CyberTheme.STATUS_PAUSED, bold=True),
    "status.failed": Style(color=CyberTheme.STATUS_FAILED, bold=True),
    "status.complete": Style(color=CyberTheme.STATUS_COMPLETE, bold=True),
    "status.verifying": Style(color=CyberTheme.STATUS_VERIFYING, bold=True),
    
    # UI elements
    "title": Style(color=CyberTheme.PRIMARY, bold=True),
    "subtitle": Style(color=CyberTheme.SECONDARY),
    "border": Style(color=CyberTheme.BORDER),
    "border.dim": Style(color=CyberTheme.BORDER_DIM),
    
    # Text styles
    "text": Style(color=CyberTheme.TEXT),
    "text.dim": Style(color=CyberTheme.TEXT_DIM),
    "text.muted": Style(color=CyberTheme.TEXT_MUTED),
    
    # Task styles
    "task.complete": Style(color=CyberTheme.TASK_COMPLETE),
    "task.progress": Style(color=CyberTheme.TASK_IN_PROGRESS, bold=True),
    "task.pending": Style(color=CyberTheme.TASK_PENDING),
    "task.failed": Style(color=CyberTheme.TASK_FAILED),
    "task.skipped": Style(color=CyberTheme.TASK_SKIPPED),
    
    # Progress
    "progress.complete": Style(color=CyberTheme.PROGRESS_COMPLETE),
    "progress.remaining": Style(color=CyberTheme.PROGRESS_REMAINING),
    
    # Accents
    "accent": Style(color=CyberTheme.ACCENT),
    "primary": Style(color=CyberTheme.PRIMARY),
    "secondary": Style(color=CyberTheme.SECONDARY),
    
    # Standard Rich overrides
    "bar.complete": Style(color=CyberTheme.PROGRESS_COMPLETE),
    "bar.finished": Style(color=CyberTheme.PROGRESS_COMPLETE),
    "bar.pulse": Style(color=CyberTheme.PROGRESS_PULSE),
    "progress.percentage": Style(color=CyberTheme.PRIMARY, bold=True),
    "progress.description": Style(color=CyberTheme.TEXT),
    "progress.elapsed": Style(color=CyberTheme.TEXT_DIM),
    "progress.remaining": Style(color=CyberTheme.TEXT_DIM),
})


# Unicode symbols for status indicators
class Symbols:
    """Terminal symbols for status display."""
    
    # Status bullets
    COMPLETE = "✓"
    IN_PROGRESS = "→"
    PENDING = "○"
    FAILED = "✗"
    SKIPPED = "⊘"
    ROLLBACK = "↩"
    
    # Animated spinner frames
    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    # Progress bar characters
    BAR_FULL = "█"
    BAR_EMPTY = "░"
    BAR_PARTIAL = ["▏", "▎", "▍", "▌", "▋", "▊", "▉"]
    
    # Decorative
    ARROW_RIGHT = "▸"
    ARROW_DOWN = "▾"
    DOT = "●"
    CIRCUIT = "◈"
    PULSE = "◉"
    
    # Box drawing
    CORNER_TL = "╭"
    CORNER_TR = "╮"
    CORNER_BL = "╰"
    CORNER_BR = "╯"
    HORIZONTAL = "─"
    VERTICAL = "│"
