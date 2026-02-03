"""Conversation summarizer for Claude and Cursor chat history.

Extracts patterns, learnings, and actionable insights from AI conversation history.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import Counter


@dataclass
class ConversationPattern:
    """A pattern extracted from conversations."""
    name: str
    description: str
    frequency: int
    examples: list[str] = field(default_factory=list)
    category: str = "general"


@dataclass 
class ConversationInsight:
    """An insight or learning from conversations."""
    title: str
    description: str
    source_count: int
    confidence: str  # high, medium, low
    actionable: bool = False
    action: str = ""


@dataclass
class SummaryReport:
    """Summary report from conversation analysis."""
    total_conversations: int
    total_messages: int
    date_range: tuple[str, str]
    top_topics: list[tuple[str, int]]
    patterns: list[ConversationPattern]
    insights: list[ConversationInsight]
    code_snippets: list[dict]
    errors_encountered: list[str]


class ConversationSummarizer:
    """Analyzes and summarizes AI conversation history."""
    
    # Common coding topics to detect
    TOPIC_PATTERNS = {
        "testing": r"\b(test|pytest|jest|unit test|integration test|coverage)\b",
        "debugging": r"\b(debug|error|exception|traceback|fix|bug)\b",
        "refactoring": r"\b(refactor|clean up|improve|optimize|restructure)\b",
        "documentation": r"\b(document|readme|docstring|comment|explain)\b",
        "api": r"\b(api|endpoint|route|http|rest|graphql)\b",
        "database": r"\b(database|sql|query|migration|schema|model)\b",
        "authentication": r"\b(auth|login|jwt|session|permission|role)\b",
        "deployment": r"\b(deploy|docker|kubernetes|ci/cd|pipeline)\b",
        "performance": r"\b(performance|optimize|cache|slow|fast|memory)\b",
        "security": r"\b(security|vulnerability|sanitize|escape|inject)\b",
    }
    
    # Error patterns
    ERROR_PATTERNS = [
        r"error:\s*(.+?)(?:\n|$)",
        r"exception:\s*(.+?)(?:\n|$)",
        r"failed:\s*(.+?)(?:\n|$)",
        r"TypeError:\s*(.+?)(?:\n|$)",
        r"ValueError:\s*(.+?)(?:\n|$)",
        r"ImportError:\s*(.+?)(?:\n|$)",
    ]
    
    def __init__(self, conversations: list[dict]):
        """Initialize with conversation data.
        
        Args:
            conversations: List of conversation dicts with messages
        """
        self.conversations = conversations
        self.all_messages = []
        self._extract_messages()
    
    def _extract_messages(self) -> None:
        """Extract all messages from conversations."""
        for conv in self.conversations:
            for msg in conv.get("messages", []):
                self.all_messages.append({
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp"),
                    "conversation_id": conv.get("id"),
                    "project": conv.get("project"),
                })
    
    def analyze(self) -> SummaryReport:
        """Analyze conversations and generate summary report."""
        # Basic stats
        total_convs = len(self.conversations)
        total_msgs = len(self.all_messages)
        
        # Date range
        timestamps = [
            m["timestamp"] for m in self.all_messages 
            if m.get("timestamp")
        ]
        if timestamps:
            date_range = (
                self._format_timestamp(min(timestamps)),
                self._format_timestamp(max(timestamps)),
            )
        else:
            date_range = ("Unknown", "Unknown")
        
        # Analyze topics
        top_topics = self._analyze_topics()
        
        # Extract patterns
        patterns = self._extract_patterns()
        
        # Generate insights
        insights = self._generate_insights(top_topics, patterns)
        
        # Extract code snippets
        code_snippets = self._extract_code_snippets()
        
        # Extract errors
        errors = self._extract_errors()
        
        return SummaryReport(
            total_conversations=total_convs,
            total_messages=total_msgs,
            date_range=date_range,
            top_topics=top_topics[:10],
            patterns=patterns[:10],
            insights=insights[:10],
            code_snippets=code_snippets[:20],
            errors_encountered=errors[:20],
        )
    
    def _format_timestamp(self, ts: int) -> str:
        """Format timestamp to readable string."""
        try:
            dt = datetime.fromtimestamp(ts / 1000)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return "Unknown"
    
    def _analyze_topics(self) -> list[tuple[str, int]]:
        """Analyze topic frequency in conversations."""
        topic_counts = Counter()
        
        for msg in self.all_messages:
            content = msg.get("content", "").lower()
            for topic, pattern in self.TOPIC_PATTERNS.items():
                if re.search(pattern, content, re.IGNORECASE):
                    topic_counts[topic] += 1
        
        return topic_counts.most_common()
    
    def _extract_patterns(self) -> list[ConversationPattern]:
        """Extract common patterns from conversations."""
        patterns = []
        
        # Pattern: Common user request types
        request_patterns = {
            "implementation": r"(implement|create|add|build)\s+(\w+)",
            "fix": r"(fix|resolve|solve)\s+(\w+)",
            "explain": r"(explain|what is|how does)\s+(\w+)",
            "refactor": r"(refactor|improve|clean)\s+(\w+)",
        }
        
        request_counts = Counter()
        request_examples = {}
        
        for msg in self.all_messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            
            for pattern_name, pattern in request_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    request_counts[pattern_name] += len(matches)
                    if pattern_name not in request_examples:
                        request_examples[pattern_name] = []
                    if len(request_examples[pattern_name]) < 3:
                        request_examples[pattern_name].append(content[:100])
        
        for name, count in request_counts.most_common(10):
            patterns.append(ConversationPattern(
                name=f"Request: {name}",
                description=f"User frequently requests {name} actions",
                frequency=count,
                examples=request_examples.get(name, []),
                category="request_type",
            ))
        
        return patterns
    
    def _generate_insights(
        self, 
        topics: list[tuple[str, int]], 
        patterns: list[ConversationPattern]
    ) -> list[ConversationInsight]:
        """Generate actionable insights from analysis."""
        insights = []
        
        # Insight from top topics
        if topics:
            top_topic = topics[0][0]
            insights.append(ConversationInsight(
                title=f"Primary Focus: {top_topic.title()}",
                description=f"Most conversations involve {top_topic} ({topics[0][1]} mentions)",
                source_count=topics[0][1],
                confidence="high",
                actionable=True,
                action=f"Consider creating documentation or templates for {top_topic}",
            ))
        
        # Insight from error patterns
        error_count = sum(1 for m in self.all_messages if "error" in m.get("content", "").lower())
        if error_count > 10:
            insights.append(ConversationInsight(
                title="Frequent Debugging Sessions",
                description=f"{error_count} messages contain error-related content",
                source_count=error_count,
                confidence="high",
                actionable=True,
                action="Consider improving error handling or adding better logging",
            ))
        
        # Insight from conversation length
        avg_msgs = len(self.all_messages) / max(len(self.conversations), 1)
        if avg_msgs > 20:
            insights.append(ConversationInsight(
                title="Long Conversation Sessions",
                description=f"Average {avg_msgs:.0f} messages per conversation",
                source_count=len(self.conversations),
                confidence="medium",
                actionable=True,
                action="Consider breaking complex tasks into smaller sessions",
            ))
        
        return insights
    
    def _extract_code_snippets(self) -> list[dict]:
        """Extract code snippets from conversations."""
        snippets = []
        code_pattern = r"```(\w+)?\n(.*?)```"
        
        for msg in self.all_messages:
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            
            matches = re.findall(code_pattern, content, re.DOTALL)
            for lang, code in matches:
                if len(code.strip()) > 20:  # Skip trivial snippets
                    snippets.append({
                        "language": lang or "unknown",
                        "code": code.strip()[:500],  # Limit size
                        "project": msg.get("project"),
                    })
        
        return snippets
    
    def _extract_errors(self) -> list[str]:
        """Extract unique errors from conversations."""
        errors = set()
        
        for msg in self.all_messages:
            content = msg.get("content", "")
            for pattern in self.ERROR_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    error_text = match.strip()[:100]
                    if len(error_text) > 10:
                        errors.add(error_text)
        
        return sorted(errors)
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        report = self.analyze()
        
        lines = [
            "# Conversation Analysis Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Period**: {report.date_range[0]} to {report.date_range[1]}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- **Total Conversations**: {report.total_conversations}",
            f"- **Total Messages**: {report.total_messages}",
            "",
            "## Top Topics",
            "",
        ]
        
        for topic, count in report.top_topics:
            lines.append(f"- {topic.title()}: {count} mentions")
        
        lines.extend([
            "",
            "## Key Insights",
            "",
        ])
        
        for insight in report.insights:
            lines.append(f"### {insight.title}")
            lines.append(f"")
            lines.append(f"{insight.description}")
            if insight.actionable:
                lines.append(f"")
                lines.append(f"**Action**: {insight.action}")
            lines.append("")
        
        if report.errors_encountered:
            lines.extend([
                "## Common Errors",
                "",
            ])
            for error in report.errors_encountered[:10]:
                lines.append(f"- `{error}`")
        
        lines.extend([
            "",
            "---",
            "",
            "*Generated by up-cli conversation summarizer*",
        ])
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Generate JSON report."""
        report = self.analyze()
        
        return json.dumps({
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_conversations": report.total_conversations,
                "total_messages": report.total_messages,
                "date_range": report.date_range,
            },
            "top_topics": [
                {"topic": t, "count": c} for t, c in report.top_topics
            ],
            "insights": [
                {
                    "title": i.title,
                    "description": i.description,
                    "actionable": i.actionable,
                    "action": i.action if i.actionable else None,
                }
                for i in report.insights
            ],
            "errors": report.errors_encountered,
        }, indent=2)


def summarize_cursor_history(output_format: str = "markdown") -> str:
    """Summarize Cursor chat history.
    
    Args:
        output_format: 'markdown' or 'json'
        
    Returns:
        Formatted summary report
    """
    # Import the export script
    try:
        from scripts.export_cursor_history import load_all_data
    except ImportError:
        # Try relative import
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from export_cursor_history import load_all_data
    
    conversations = load_all_data()
    summarizer = ConversationSummarizer(conversations)
    
    if output_format == "json":
        return summarizer.to_json()
    return summarizer.to_markdown()


# CLI
if __name__ == "__main__":
    import sys
    
    output_format = "markdown"
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        output_format = "json"
    
    try:
        result = summarize_cursor_history(output_format)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
