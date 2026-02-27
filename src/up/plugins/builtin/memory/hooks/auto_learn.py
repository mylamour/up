#!/usr/bin/env python3
"""Auto-learn hook: escalate novel repeated errors to the learning system.

Triggers on TASK_FAILED events. When auto_recall found no matching memory
AND the same error pattern has occurred multiple times, this hook triggers
the learning system to research the error topic.

Exit codes:
  0 = allow (no escalation needed)
  1 = warn (learning triggered)
"""

import json
import sys
import os
import hashlib
from pathlib import Path


def _load_config(workspace):
    """Load auto_learn config from .up/config.json."""
    config_path = os.path.join(workspace, ".up", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            learn_cfg = cfg.get("automation", {}).get("learning", {})
            return {
                "enabled": learn_cfg.get("auto_learn", True),
                "escalation_threshold": learn_cfg.get("escalation_threshold", 3),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return {"enabled": True, "escalation_threshold": 3}


def _error_signature(error_text):
    """Generate a signature from error text for dedup."""
    try:
        from up.memory.patterns import ErrorPatternExtractor
        extractor = ErrorPatternExtractor()
        keywords = extractor.extract(error_text)
        sig_input = " ".join(keywords) if keywords else error_text[:200]
    except Exception:
        sig_input = error_text[:200]
    return hashlib.md5(sig_input.encode()).hexdigest()


def _get_escalation_tracker(workspace):
    """Load the escalation tracker (tracks novel errors without memory matches)."""
    tracker_path = os.path.join(workspace, ".up", "learn_escalation.json")
    if os.path.exists(tracker_path):
        try:
            with open(tracker_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"novel_errors": {}, "researched": []}


def _save_escalation_tracker(workspace, tracker):
    """Save the escalation tracker."""
    tracker_path = os.path.join(workspace, ".up", "learn_escalation.json")
    os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)


def _trigger_learning(workspace, keywords, error_text):
    """Trigger the learning system to research the error topic."""
    try:
        from up.learn.utils import find_skill_dir, record_to_memory

        topic = " ".join(keywords[:5]) if keywords else error_text[:60]

        # Record the escalation to memory
        record_to_memory(
            workspace,
            f"Auto-learn escalation: researching '{topic}' after repeated novel errors",
        )

        # Save a research request file for the learning system
        skill_dir = find_skill_dir(workspace, "learning-system")
        research_dir = skill_dir / "research"
        research_dir.mkdir(parents=True, exist_ok=True)

        sig = hashlib.md5(topic.encode()).hexdigest()[:8]
        request_file = research_dir / f"auto_learn_{sig}.md"
        request_file.write_text(
            f"# Auto-Learn Research Request\n\n"
            f"**Topic**: {topic}\n"
            f"**Source**: Repeated novel error (no memory match)\n\n"
            f"## Error Context\n\n"
            f"```\n{error_text[:500]}\n```\n\n"
            f"## Research Needed\n\n"
            f"- Root cause analysis for this error pattern\n"
            f"- Common solutions and workarounds\n"
            f"- Prevention strategies\n"
        )
        return True
    except Exception as e:
        print(f"auto_learn trigger error: {e}", file=sys.stderr)
        return False


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    config = _load_config(workspace)
    if not config["enabled"]:
        sys.exit(0)

    error_output = event_data.get("error", "") or event_data.get("output", "")
    if not error_output:
        sys.exit(0)

    # Check if auto_recall already found a match (hint was provided)
    if event_data.get("memory_hint"):
        sys.exit(0)

    try:
        from up.memory.patterns import ErrorPatternExtractor

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract(error_output)
        if not keywords:
            sys.exit(0)

        signature = _error_signature(error_output)
        tracker = _get_escalation_tracker(workspace)

        # Skip if already researched
        if signature in tracker.get("researched", []):
            sys.exit(0)

        # Increment novel error count
        novel = tracker.setdefault("novel_errors", {})
        novel[signature] = novel.get(signature, 0) + 1

        threshold = config["escalation_threshold"]

        if novel[signature] >= threshold:
            # Escalate to learning system
            success = _trigger_learning(workspace, keywords, error_output)
            if success:
                # Mark as researched so we don't re-trigger
                tracker.setdefault("researched", []).append(signature)
                del novel[signature]
                _save_escalation_tracker(workspace, tracker)

                hint = {
                    "escalated": True,
                    "topic": " ".join(keywords[:5]),
                }
                print(json.dumps(hint))
                print(
                    f"Auto-learn: escalated novel error to learning system "
                    f"('{' '.join(keywords[:3])}')",
                    file=sys.stderr,
                )
                sys.exit(1)

        _save_escalation_tracker(workspace, tracker)

    except Exception as e:
        print(f"auto_learn error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
