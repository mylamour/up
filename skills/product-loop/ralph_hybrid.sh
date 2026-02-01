#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# Ralph Hybrid Orchestrator
#
# Combines structured task management with production-grade safety features.
# Based on Ralph Hybrid Design v1.0
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ─────────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

# Configurable via environment or .ralphrc
MAX_ITERATIONS="${MAX_ITERATIONS:-100}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-5}"
MAX_CALLS_PER_HOUR="${MAX_CALLS_PER_HOUR:-100}"
CLAUDE_TIMEOUT_MINUTES="${CLAUDE_TIMEOUT_MINUTES:-15}"
SESSION_EXPIRY_HOURS="${SESSION_EXPIRY_HOURS:-24}"
AUTO_COMMIT="${AUTO_COMMIT:-true}"
COMMIT_AUTHOR="${COMMIT_AUTHOR:-Ralph Hybrid <ralph@ai-auditor.local>}"

# State files
STATE_DIR="${WORKSPACE}/.ralph"
LOG_FILE="${STATE_DIR}/ralph_hybrid.log"
OUTPUT_FILE="${STATE_DIR}/last_output.txt"
SESSION_FILE="${STATE_DIR}/.claude_session_id"
CHECKPOINT_FILE="${STATE_DIR}/.checkpoint"
STOP_FILE="${STATE_DIR}/.stop_signal"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─────────────────────────────────────────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────────────────────────────────────────

init() {
    # Create state directory
    mkdir -p "$STATE_DIR"

    # Load .ralphrc if exists
    if [ -f "${WORKSPACE}/.ralphrc" ]; then
        source "${WORKSPACE}/.ralphrc"
    fi

    # Initialize log
    echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ralph Hybrid Started" >> "$LOG_FILE"
    echo "Workspace: $WORKSPACE" >> "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────────

log() {
    local level="${2:-INFO}"
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $msg" >> "$LOG_FILE"
}

log_info() { log "$1" "INFO"; }
log_warn() { log "$1" "WARN"; }
log_error() { log "$1" "ERROR"; }

# ─────────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗    ██╗  ██╗██╗   ██╗██████╗       ║
║   ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║    ██║  ██║╚██╗ ██╔╝██╔══██╗      ║
║   ██████╔╝███████║██║     ██████╔╝███████║    ███████║ ╚████╔╝ ██████╔╝      ║
║   ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║    ██╔══██║  ╚██╔╝  ██╔══██╗      ║
║   ██║  ██║██║  ██║███████╗██║     ██║  ██║    ██║  ██║   ██║   ██████╔╝      ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝    ╚═╝  ╚═╝   ╚═╝   ╚═════╝       ║
║                                                                               ║
║   Structured Tasks + Safety Systems = Reliable Autonomous Development         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Safety Systems (Python Integration)
# ─────────────────────────────────────────────────────────────────────────────────

check_circuit_breaker() {
    local result
    result=$(python3 "$SCRIPT_DIR/ralph_circuit_breaker.py" status 2>/dev/null || echo '{"can_proceed": true}')
    echo "$result"
}

record_circuit_metrics() {
    local files_modified="$1"
    local errors="$2"
    local output_length="$3"
    local tasks_completed="$4"

    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from ralph_circuit_breaker import record_iteration
import json

result = record_iteration(
    files_modified=$files_modified,
    errors=$errors,
    output_length=$output_length,
    tasks_completed=$tasks_completed,
    state_dir='$STATE_DIR'
)
print(json.dumps(result))
" 2>/dev/null || echo '{"state": "CLOSED", "can_proceed": true}'
}

check_rate_limit() {
    python3 "$SCRIPT_DIR/ralph_rate_limiter.py" 2>/dev/null || echo '{"can_proceed": true}'
}

record_api_call() {
    python3 "$SCRIPT_DIR/ralph_rate_limiter.py" record 2>/dev/null || echo '{"allowed": true}'
}

analyze_response() {
    local output_file="$1"
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from ralph_response_analyzer import analyze_output
from pathlib import Path
import json

output = Path('$output_file').read_text()
result = analyze_output(output, '$STATE_DIR')
print(json.dumps(result))
" 2>/dev/null || echo '{"should_exit": false, "exit_signal": false}'
}

# ─────────────────────────────────────────────────────────────────────────────────
# Session Management
# ─────────────────────────────────────────────────────────────────────────────────

get_session_id() {
    if [ -f "$SESSION_FILE" ]; then
        local data
        data=$(cat "$SESSION_FILE")
        local created
        created=$(echo "$data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('created',''))" 2>/dev/null || echo "")

        if [ -n "$created" ]; then
            # Check if session expired - use Python for cross-platform date parsing
            local age_hours
            age_hours=$(python3 -c "
from datetime import datetime
try:
    created = '$created'.split('+')[0].split('.')[0]  # Strip timezone and microseconds
    created_dt = datetime.fromisoformat(created)
    now = datetime.now()
    age_seconds = (now - created_dt).total_seconds()
    print(int(age_seconds / 3600))
except:
    print(999)  # Force session renewal on parse error
" 2>/dev/null || echo "999")

            if [ "$age_hours" -lt "$SESSION_EXPIRY_HOURS" ]; then
                echo "$data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null
                return
            fi
        fi
    fi

    # Create new session
    local new_id
    new_id=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "session-$(date +%s)")
    echo "{\"session_id\": \"$new_id\", \"created\": \"$(date -Iseconds)\"}" > "$SESSION_FILE"
    echo "$new_id"
}

reset_session() {
    rm -f "$SESSION_FILE"
    log_info "Session reset"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Checkpoint Management
# ─────────────────────────────────────────────────────────────────────────────────

save_checkpoint() {
    local iteration="$1"
    local phase="${2:-implementation}"
    local current_story="${3:-}"

    python3 -c "
import json
from datetime import datetime

checkpoint = {
    'iteration': $iteration,
    'phase': '$phase',
    'current_story': '$current_story',
    'timestamp': datetime.now().isoformat(),
    'workspace': '$WORKSPACE'
}

with open('$CHECKPOINT_FILE', 'w') as f:
    json.dump(checkpoint, f, indent=2)
" 2>/dev/null

    log_info "Checkpoint saved: iteration=$iteration, phase=$phase"
}

load_checkpoint() {
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        echo '{"iteration": 1, "phase": "implementation", "current_story": ""}'
        return
    fi

    cat "$CHECKPOINT_FILE"
}

get_checkpoint_iteration() {
    local checkpoint
    checkpoint=$(load_checkpoint)
    echo "$checkpoint" | python3 -c "import sys,json; print(json.load(sys.stdin).get('iteration', 1))" 2>/dev/null || echo "1"
}

clear_checkpoint() {
    rm -f "$CHECKPOINT_FILE"
    log_info "Checkpoint cleared"
}

display_checkpoint() {
    if [ ! -f "$CHECKPOINT_FILE" ]; then
        echo -e "${YELLOW}No checkpoint found${NC}"
        return
    fi

    echo -e "${CYAN}Checkpoint:${NC}"
    cat "$CHECKPOINT_FILE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Iteration:     {d.get('iteration', 'N/A')}\")
print(f\"  Phase:         {d.get('phase', 'N/A')}\")
print(f\"  Current Story: {d.get('current_story', 'N/A')}\")
print(f\"  Saved At:      {d.get('timestamp', 'N/A')}\")
" 2>/dev/null || echo "  Unable to read checkpoint"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Stop Signal Management
# ─────────────────────────────────────────────────────────────────────────────────

request_stop() {
    echo "{\"requested\": \"$(date -Iseconds)\", \"reason\": \"${1:-user_request}\"}" > "$STOP_FILE"
    log_info "Stop requested: ${1:-user_request}"
    echo -e "${YELLOW}Stop signal sent. Loop will stop after current iteration.${NC}"
}

check_stop_signal() {
    if [ -f "$STOP_FILE" ]; then
        return 0  # Stop requested
    fi
    return 1  # Continue
}

clear_stop_signal() {
    rm -f "$STOP_FILE"
    log_info "Stop signal cleared"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Auto-Commit Functions
# ─────────────────────────────────────────────────────────────────────────────────

has_uncommitted_changes() {
    cd "$WORKSPACE" || return 1
    # Check for staged or unstaged changes (excluding untracked)
    if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        return 0  # Has changes
    fi
    return 1  # No changes
}

get_changed_files() {
    cd "$WORKSPACE" || return
    git diff --name-only HEAD 2>/dev/null
    git diff --cached --name-only 2>/dev/null
}

generate_commit_message() {
    local phase="${1:-implementation}"
    local iteration="${2:-0}"
    local story_id="${3:-}"
    local summary="${4:-}"
    local tasks_completed="${5:-}"

    cd "$WORKSPACE" || return

    # Get list of changed files
    local changed_files
    changed_files=$(get_changed_files | sort -u)
    local file_count
    file_count=$(echo "$changed_files" | grep -c . || echo "0")

    # Categorize changes - use tr to strip newlines and ensure clean integers
    local src_changes
    src_changes=$(echo "$changed_files" | grep -c "^src/" 2>/dev/null || echo "0")
    src_changes=$(echo "$src_changes" | tr -d '[:space:]')
    [ -z "$src_changes" ] && src_changes=0
    
    local test_changes
    test_changes=$(echo "$changed_files" | grep -c "test" 2>/dev/null || echo "0")
    test_changes=$(echo "$test_changes" | tr -d '[:space:]')
    [ -z "$test_changes" ] && test_changes=0
    
    local doc_changes
    doc_changes=$(echo "$changed_files" | grep -c -E "\.md$|docs/" 2>/dev/null || echo "0")
    doc_changes=$(echo "$doc_changes" | tr -d '[:space:]')
    [ -z "$doc_changes" ] && doc_changes=0
    
    local config_changes
    config_changes=$(echo "$changed_files" | grep -c -E "\.json$|\.yaml$|\.toml$" 2>/dev/null || echo "0")
    config_changes=$(echo "$config_changes" | tr -d '[:space:]')
    [ -z "$config_changes" ] && config_changes=0

    # Determine commit type based on work type and changes
    local commit_type="feat"
    local work_type=""
    work_type=$(get_last_work_type)
    
    case "$work_type" in
        testing)
            commit_type="test"
            ;;
        documentation)
            commit_type="docs"
            ;;
        refactoring)
            commit_type="refactor"
            ;;
        *)
            # Infer from file changes
            if [ "$test_changes" -gt 0 ] && [ "$src_changes" -eq 0 ]; then
                commit_type="test"
            elif [ "$doc_changes" -gt 0 ] && [ "$src_changes" -eq 0 ]; then
                commit_type="docs"
            elif echo "$changed_files" | grep -qi "fix\|bug\|patch"; then
                commit_type="fix"
            elif [ "$config_changes" -gt 0 ] && [ "$src_changes" -eq 0 ]; then
                commit_type="chore"
            fi
            ;;
    esac

    # Get primary module/scope from changed files
    local scope=""
    scope=$(echo "$changed_files" | grep "^src/" | head -1 | sed 's|^src/code_auditor/||' | sed 's|/.*||')
    [ -z "$scope" ] && scope=$(echo "$changed_files" | head -1 | sed 's|/.*||')

    # Build commit message title from summary
    local message=""
    local body=""

    case "$phase" in
        research)
            message="$commit_type(learn): add research findings"
            [ -n "$summary" ] && message="$commit_type(learn): $summary"
            body="Research phase completed.

Changes:
- Analyzed external sources and best practices
- Created research documentation"
            ;;
        analyze)
            message="$commit_type(learn): extract patterns from research"
            [ -n "$summary" ] && message="$commit_type(learn): $summary"
            body="Analysis phase completed.

Changes:
- Extracted design patterns from research
- Identified reusable components and approaches"
            ;;
        compare)
            message="$commit_type(learn): complete gap analysis"
            [ -n "$summary" ] && message="$commit_type(learn): $summary"
            body="Comparison phase completed.

Changes:
- Compared current implementation with best practices
- Identified gaps and improvement opportunities"
            ;;
        plan)
            message="$commit_type(learn): generate improvement PRD"
            [ -n "$summary" ] && message="$commit_type(learn): $summary"
            body="Planning phase completed.

Changes:
- Generated product requirements document
- Prioritized improvements by impact/effort"
            ;;
        implementation)
            # Use summary from RALPH_STATUS as commit message
            if [ -n "$summary" ]; then
                # Clean summary: lowercase first char, remove trailing period
                local clean_summary
                clean_summary=$(echo "$summary" | sed 's/\.$//' | sed 's/^\(.\)/\L\1/')
                if [ -n "$scope" ]; then
                    message="$commit_type($scope): $clean_summary"
                else
                    message="$commit_type: $clean_summary"
                fi
            elif [ -n "$story_id" ]; then
                message="$commit_type($scope): implement $story_id"
            else
                # Fallback: generate from changed files
                local main_file
                main_file=$(echo "$changed_files" | grep "^src/" | head -1 | xargs basename 2>/dev/null | sed 's/\.py$//')
                if [ -n "$main_file" ]; then
                    message="$commit_type($scope): update $main_file"
                else
                    message="$commit_type: iteration $iteration changes"
                fi
            fi

            # Build detailed body from actual work done
            if [ -n "$tasks_completed" ] && [ "$tasks_completed" != "[]" ]; then
                body="Tasks completed: $tasks_completed"
            else
                body="Implementation changes"
            fi

            [ -n "$summary" ] && body="$body

Summary: $summary"
            ;;
        *)
            message="$commit_type: automated changes ($phase)"
            [ -n "$summary" ] && message="$commit_type: $summary"
            body="Automated changes from $phase phase."
            ;;
    esac

    # Add file statistics to body
    body="$body

Files modified: $file_count
- Source files: $src_changes
- Test files: $test_changes
- Documentation: $doc_changes
- Config files: $config_changes

Changed files:
$(echo "$changed_files" | head -10 | sed 's/^/- /')"

    [ "$file_count" -gt 10 ] && body="$body
... and $((file_count - 10)) more"

    echo "$message"
    echo "---BODY---"
    echo "$body"
}

get_last_work_type() {
    # Extract work type from last response analysis
    if [ -f "$STATE_DIR/.response_analysis" ]; then
        python3 -c "
import json
with open('$STATE_DIR/.response_analysis') as f:
    d = json.load(f)
print(d.get('status', {}).get('work_type', ''))
" 2>/dev/null || echo ""
    fi
}

get_last_summary() {
    # Extract summary from last response analysis
    if [ -f "$STATE_DIR/.response_analysis" ]; then
        python3 -c "
import json
with open('$STATE_DIR/.response_analysis') as f:
    d = json.load(f)
print(d.get('status', {}).get('summary', ''))
" 2>/dev/null || echo ""
    fi
}

get_last_tasks_completed() {
    # Extract tasks completed from last response analysis
    if [ -f "$STATE_DIR/.response_analysis" ]; then
        python3 -c "
import json
with open('$STATE_DIR/.response_analysis') as f:
    d = json.load(f)
tasks = d.get('status', {}).get('tasks_completed', [])
print(', '.join(tasks) if tasks else '')
" 2>/dev/null || echo ""
    fi
}

auto_commit() {
    local phase="${1:-implementation}"
    local iteration="${2:-0}"
    local story_id="${3:-}"

    # Check if auto-commit is enabled
    if [ "$AUTO_COMMIT" != "true" ]; then
        return 0
    fi

    # Check if there are changes to commit
    if ! has_uncommitted_changes; then
        log_info "No changes to commit"
        return 0
    fi

    cd "$WORKSPACE" || return 1

    # Get summary and tasks from RALPH_STATUS (stored by response analyzer)
    local summary
    summary=$(get_last_summary)
    local tasks_completed
    tasks_completed=$(get_last_tasks_completed)

    # Generate commit message with actual summary
    local full_message
    full_message=$(generate_commit_message "$phase" "$iteration" "$story_id" "$summary" "$tasks_completed")
    local title
    title=$(echo "$full_message" | sed -n '1p')
    local body
    body=$(echo "$full_message" | sed -n '/---BODY---/,$p' | tail -n +2)

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ Auto-Commit                                                     │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────┘${NC}"

    # Show what will be committed
    local changed_files
    changed_files=$(get_changed_files | sort -u | head -10)
    local file_count
    file_count=$(get_changed_files | sort -u | wc -l | tr -d ' ')

    echo -e "  Files changed: ${GREEN}$file_count${NC}"
    echo "$changed_files" | while read -r f; do
        [ -n "$f" ] && echo -e "    - $f"
    done
    if [ "$file_count" -gt 10 ]; then
        echo -e "    ... and $((file_count - 10)) more"
    fi

    # Stage all changes
    git add -A 2>/dev/null

    # Commit with detailed message
    local commit_output
    local full_commit_msg="$title

$body

---
Auto-committed by Ralph Hybrid
Phase: $phase | Iteration: $iteration"

    if commit_output=$(git commit -m "$full_commit_msg" 2>&1); then
        local commit_hash
        commit_hash=$(git rev-parse --short HEAD 2>/dev/null)
        echo ""
        echo -e "  ${GREEN}✓ Committed: $commit_hash${NC}"
        echo -e "  Title: ${CYAN}$title${NC}"
        echo -e "  Body preview:"
        echo "$body" | head -5 | while read -r line; do
            echo -e "    $line"
        done
        log_info "Auto-commit: $commit_hash - $title"
        echo ""
        
        # Update CHANGELOG.md with the change
        update_changelog "$title" "$summary" "$tasks_completed"
        
        return 0
    else
        echo -e "  ${YELLOW}⚠ Commit failed: $commit_output${NC}"
        log_warn "Auto-commit failed: $commit_output"
        echo ""
        return 1
    fi
}

update_changelog() {
    local title="$1"
    local summary="$2"
    local tasks="$3"
    
    local changelog="${WORKSPACE}/CHANGELOG.md"
    local changelog_dir="${WORKSPACE}/docs/changelog"
    
    # Determine the category based on commit type
    local category="Changed"
    if echo "$title" | grep -q "^feat"; then
        category="Added"
    elif echo "$title" | grep -q "^fix"; then
        category="Fixed"
    elif echo "$title" | grep -q "^docs"; then
        category="Documentation"
    elif echo "$title" | grep -q "^test"; then
        category="Testing"
    elif echo "$title" | grep -q "^refactor"; then
        category="Changed"
    elif echo "$title" | grep -q "^security"; then
        category="Security"
    fi
    
    # Extract the description from title (after the colon)
    local description
    description=$(echo "$title" | sed 's/^[^:]*: //')
    
    # 1. Update main CHANGELOG.md if exists
    if [ -f "$changelog" ] && grep -q "^\## \[Unreleased\]" "$changelog"; then
        python3 -c "
import re
from pathlib import Path
from datetime import datetime

changelog = Path('$changelog')
content = changelog.read_text()

# Find [Unreleased] section
unreleased_match = re.search(r'^## \[Unreleased\].*$', content, re.MULTILINE)
if not unreleased_match:
    exit(0)

insert_pos = unreleased_match.end()

category = '$category'
description = '$description'
tasks = '$tasks'

# Build the entry
entry = f'- {description}'
if tasks:
    entry += f' ({tasks})'

# Look for existing category section
category_pattern = rf'^### {category}\s*$'
category_match = re.search(category_pattern, content[insert_pos:insert_pos+500], re.MULTILINE)

if category_match:
    cat_pos = insert_pos + category_match.end()
    new_content = content[:cat_pos] + '\n' + entry + content[cat_pos:]
else:
    new_section = f'\n\n### {category}\n{entry}'
    new_content = content[:insert_pos] + new_section + content[insert_pos:]

changelog.write_text(new_content)
" 2>/dev/null || true
        log_info "CHANGELOG.md updated: $category - $description"
    fi
    
    # 2. Create detailed changelog entry in docs/changelog/ (following best practices)
    if [ -d "$changelog_dir" ] || mkdir -p "$changelog_dir" 2>/dev/null; then
        local date_str
        date_str=$(date '+%Y-%m-%d')
        local slug
        slug=$(echo "$description" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-50)
        local entry_file="${changelog_dir}/${date_str}-${slug}.md"
        
        # Only create if doesn't exist (avoid duplicates)
        if [ ! -f "$entry_file" ]; then
            local changed_files
            changed_files=$(get_changed_files | sort -u | head -20)
            
            python3 -c "
from pathlib import Path
from datetime import datetime

entry = '''# $description

**Created**: $(date '+%Y-%m-%d')  
**Status**: ✅ Complete  
**Priority**: 🟢 Low

---

## Summary

$summary

## Changes Made

### $category
- $description

## Tasks Completed

$tasks

## Files Modified

| File | Type | Changes |
|------|------|---------|
$(echo "$changed_files" | while read f; do
    [ -n "$f" ] && echo "| \`$f\` | Update | Implementation changes |"
done)

## Impact

Changes to the codebase as described above.

---

**Auto-generated by Ralph Hybrid**
'''

Path('$entry_file').write_text(entry)
" 2>/dev/null || true
            
            log_info "Created changelog entry: $entry_file"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────────
# Status Display
# ─────────────────────────────────────────────────────────────────────────────────

display_status() {
    local iteration="$1"
    local cb_status="$2"
    local rl_status="$3"

    local cb_state
    cb_state=$(echo "$cb_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','CLOSED'))" 2>/dev/null || echo "CLOSED")
    local rl_remaining
    rl_remaining=$(echo "$rl_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('remaining',100))" 2>/dev/null || echo "100")

    echo ""
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD} Iteration $iteration / $MAX_ITERATIONS ${NC}"
    echo -e "${PURPLE}───────────────────────────────────────────────────────────────${NC}"
    echo -e " Time:           $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e " Circuit:        ${cb_state}"
    echo -e " Rate Limit:     ${rl_remaining} calls remaining"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
}

display_analysis() {
    local analysis="$1"

    local status
    status=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    local exit_signal
    exit_signal=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('exit_signal',False))" 2>/dev/null || echo "False")
    local should_exit
    should_exit=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('should_exit',False))" 2>/dev/null || echo "False")
    local tasks_remaining
    tasks_remaining=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tasks_remaining',-1))" 2>/dev/null || echo "-1")
    local summary
    summary=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('summary','')[:60])" 2>/dev/null || echo "")

    echo ""
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ Response Analysis                                               │${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC} Status:         $status"
    echo -e "${CYAN}│${NC} EXIT_SIGNAL:    $exit_signal"
    echo -e "${CYAN}│${NC} Should Exit:    $should_exit"
    echo -e "${CYAN}│${NC} Tasks Left:     $tasks_remaining"
    echo -e "${CYAN}│${NC} Summary:        $summary"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────┘${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Main Loop
# ─────────────────────────────────────────────────────────────────────────────────

run_loop() {
    local resume="${1:-false}"
    local iteration=1

    print_banner

    # Check for checkpoint and resume if requested
    if [ "$resume" = "true" ] && [ -f "$CHECKPOINT_FILE" ]; then
        iteration=$(get_checkpoint_iteration)
        echo -e "${GREEN}Resuming from checkpoint at iteration $iteration${NC}"
        log_info "Resuming from checkpoint: iteration=$iteration"
        display_checkpoint
        echo ""
    elif [ -f "$CHECKPOINT_FILE" ]; then
        local saved_iter=$(get_checkpoint_iteration)
        echo -e "${YELLOW}Found checkpoint at iteration $saved_iter${NC}"
        echo -e "${YELLOW}Use 'resume' command to continue, or 'start' to restart from 1${NC}"
        echo ""
    fi

    echo -e "${BOLD}Configuration:${NC}"
    echo -e "  Workspace:       ${CYAN}$WORKSPACE${NC}"
    echo -e "  Max Iterations:  ${CYAN}$MAX_ITERATIONS${NC}"
    echo -e "  Rate Limit:      ${CYAN}$MAX_CALLS_PER_HOUR/hour${NC}"
    echo -e "  Timeout:         ${CYAN}${CLAUDE_TIMEOUT_MINUTES}min${NC}"
    echo ""

    log_info "Loop started at iteration $iteration"

    # Clear any previous stop signal when starting fresh
    if [ "$resume" != "true" ]; then
        clear_stop_signal
    fi

    while [ "$iteration" -le "$MAX_ITERATIONS" ]; do
        # 0. Check for stop signal
        if check_stop_signal; then
            echo ""
            echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║  STOP SIGNAL RECEIVED                                         ║${NC}"
            echo -e "${YELLOW}║  Loop stopped gracefully at iteration $iteration                    ║${NC}"
            echo -e "${YELLOW}║  Run: ralph_hybrid.sh resume  to continue                     ║${NC}"
            echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
            log_info "Loop stopped by stop signal at iteration $iteration"
            clear_stop_signal
            exit 0
        fi

        # 1. Check circuit breaker
        local cb_status
        cb_status=$(check_circuit_breaker)
        local can_proceed_cb
        can_proceed_cb=$(echo "$cb_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('can_proceed',True))" 2>/dev/null || echo "True")

        if [ "$can_proceed_cb" = "False" ]; then
            echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║  CIRCUIT BREAKER OPEN - Loop halted                           ║${NC}"
            echo -e "${RED}║  Run: ralph_hybrid.sh reset-circuit to reset                  ║${NC}"
            echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
            log_error "Circuit breaker OPEN - halting"
            exit 1
        fi

        # 2. Check rate limit
        local rl_status
        rl_status=$(check_rate_limit)
        local can_proceed_rl
        can_proceed_rl=$(echo "$rl_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('can_proceed',True))" 2>/dev/null || echo "True")

        if [ "$can_proceed_rl" = "False" ]; then
            local wait_seconds
            wait_seconds=$(echo "$rl_status" | python3 -c "import sys,json; print(json.load(sys.stdin).get('wait_seconds',300))" 2>/dev/null || echo "300")
            echo -e "${YELLOW}Rate limit reached. Waiting ${wait_seconds}s...${NC}"
            log_warn "Rate limit - waiting ${wait_seconds}s"
            sleep "$wait_seconds"
            continue
        fi

        # Display status
        display_status "$iteration" "$cb_status" "$rl_status"

        # 3. Record API call
        record_api_call > /dev/null

        # 4. Execute Claude
        log_info "Iteration $iteration: Executing Claude"
        local timeout_seconds=$((CLAUDE_TIMEOUT_MINUTES * 60))

        # Clear previous output
        > "$OUTPUT_FILE"

        # Capture output using script command (works reliably on macOS)
        # script -q creates a typescript without header/footer
        local claude_exit=0

        # Use script for reliable output capture
        # Syntax differs between macOS and Linux
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS: script -q file command
            script -q "$OUTPUT_FILE" bash -c "timeout $timeout_seconds claude -p '/product-loop' 2>&1" || claude_exit=$?
        else
            # Linux: script -q -c "command" file
            script -q -c "timeout $timeout_seconds claude -p '/product-loop' 2>&1" "$OUTPUT_FILE" || claude_exit=$?
        fi

        # Clean up script control characters if any
        if [ -f "$OUTPUT_FILE" ]; then
            # Remove carriage returns and control chars (use sed without -i '' on Linux)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' 's/\r//g' "$OUTPUT_FILE" 2>/dev/null || true
            else
                sed -i 's/\r//g' "$OUTPUT_FILE" 2>/dev/null || true
            fi
        fi

        if [ "$claude_exit" -eq 0 ]; then
            log_info "Iteration $iteration: Claude completed"
        elif [ "$claude_exit" -eq 124 ]; then
            log_warn "Iteration $iteration: Claude timed out"
            echo -e "${YELLOW}Claude timed out after ${CLAUDE_TIMEOUT_MINUTES} minutes${NC}"
        else
            log_error "Iteration $iteration: Claude failed with code $claude_exit"
        fi

        echo "" # Newline after output

        # 5. Analyze response
        local analysis
        analysis=$(analyze_response "$OUTPUT_FILE")
        display_analysis "$analysis"

        # Extract metrics for circuit breaker
        local files_modified
        files_modified=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('files_modified',[]))" 2>/dev/null || echo "[]")
        local errors
        errors=$(echo "$analysis" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error') or '[]')" 2>/dev/null || echo "[]")
        local output_length
        output_length=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')

        # 6. Update circuit breaker
        record_circuit_metrics "$files_modified" "[$errors]" "$output_length" "[]" > /dev/null

        # 7. Check exit conditions (dual-condition)
        local should_exit
        should_exit=$(echo "$analysis" | python3 -c "import sys,json; print(json.load(sys.stdin).get('should_exit',False))" 2>/dev/null || echo "False")

        if [ "$should_exit" = "True" ]; then
            echo ""
            echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║   🎉 PROJECT COMPLETE 🎉                                      ║${NC}"
            echo -e "${GREEN}║   Dual-condition exit: EXIT_SIGNAL + indicators met           ║${NC}"
            echo -e "${GREEN}║   Total iterations: $iteration                                     ║${NC}"
            echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
            log_info "Project complete after $iteration iterations"
            clear_checkpoint  # Clear checkpoint on successful completion
            exit 0
        fi

        # 8. Save checkpoint after each iteration
        save_checkpoint "$iteration" "implementation"

        # 9. Auto-commit changes if enabled
        auto_commit "implementation" "$iteration"

        # 10. Next iteration
        iteration=$((iteration + 1))

        if [ "$iteration" -le "$MAX_ITERATIONS" ]; then
            echo -e "${CYAN}⏳ Next iteration in ${SLEEP_BETWEEN}s...${NC}"
            sleep "$SLEEP_BETWEEN"
        fi
    done

    echo -e "${YELLOW}Maximum iterations ($MAX_ITERATIONS) reached${NC}"
    log_warn "Max iterations reached"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────────
# Learning System Integration
# ─────────────────────────────────────────────────────────────────────────────────

LEARNING_DIR="${SCRIPT_DIR}/../learning-system"

run_auto_learn() {
    local skip_implement="${1:-false}"

    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║   AUTO-LEARN MODE                                                             ║
║   Analyze Project → Research → Analyze → Compare → Plan → Implement          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    log_info "Auto-learn mode started"

    # Phase 0: Analyze Project
    echo -e "${BOLD}Phase 0: PROJECT ANALYSIS${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    echo -e "Scanning codebase to identify improvement areas..."

    local profile
    profile=$(python3 "$LEARNING_DIR/project_analyzer.py" 2>/dev/null)

    if [ -z "$profile" ]; then
        echo -e "${YELLOW}Could not analyze project. Falling back to general research.${NC}"
        run_learn "" "$skip_implement"
        return
    fi

    echo -e "${GREEN}$profile${NC}"
    echo ""

    # Get topics from analyzer
    local topics
    topics=$(python3 -c "
import sys
sys.path.insert(0, '$LEARNING_DIR')
from project_analyzer import ProjectAnalyzer
analyzer = ProjectAnalyzer()
profile = analyzer.analyze()
print('\\n'.join(profile.research_topics))
" 2>/dev/null)

    if [ -z "$topics" ]; then
        echo -e "${YELLOW}No topics identified. Using default research.${NC}"
        run_learn "" "$skip_implement"
        return
    fi

    # Research each topic
    echo -e "${BOLD}Phase 1: RESEARCH (Auto-detected topics)${NC}"
    echo -e "───────────────────────────────────────────────────────────────"

    while IFS= read -r topic; do
        if [ -n "$topic" ]; then
            echo -e "Researching: ${CYAN}$topic${NC}"
            run_claude_learn "research $topic"
        fi
    done <<< "$topics"

    # Continue with remaining phases
    run_learn_phases "$skip_implement"
}

run_learn() {
    local topic="${1:-}"
    local skip_implement="${2:-false}"

    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║   LEARNING MODE                                                               ║
║   Research → Analyze → Compare → Plan → Implement                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    log_info "Learning mode started"

    # Phase 1: Research
    echo -e "${BOLD}Phase 1: RESEARCH${NC}"
    echo -e "───────────────────────────────────────────────────────────────"

    if [ -n "$topic" ]; then
        echo -e "Researching topic: ${CYAN}$topic${NC}"
        log_info "Research topic: $topic"
        run_claude_learn "research $topic"
    else
        echo -e "Running general research from sources.json"
        log_info "Research: general"
        run_claude_learn "research"
    fi

    # Phase 2: Analyze
    echo ""
    echo -e "${BOLD}Phase 2: ANALYZE${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    echo -e "Extracting patterns from research..."
    run_claude_learn "analyze"

    # Phase 3: Compare
    echo ""
    echo -e "${BOLD}Phase 3: COMPARE${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    echo -e "Comparing with current implementation..."
    run_claude_learn "compare"

    # Phase 4: Plan
    echo ""
    echo -e "${BOLD}Phase 4: PLAN${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    echo -e "Generating improvement PRD..."
    run_claude_learn "plan"

    # Check if PRD was generated
    if [ ! -f "${WORKSPACE}/prd.json" ]; then
        echo -e "${YELLOW}No prd.json generated. Learning complete without implementation.${NC}"
        log_warn "No PRD generated"
        return 0
    fi

    # Phase 5: Implement (unless skipped)
    if [ "$skip_implement" = "true" ]; then
        echo ""
        echo -e "${GREEN}Learning phases complete. PRD generated at: ${WORKSPACE}/prd.json${NC}"
        echo -e "Run ${CYAN}ralph_hybrid.sh start${NC} to implement."
        return 0
    fi

    echo ""
    echo -e "${BOLD}Phase 5: IMPLEMENT${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    echo -e "Starting Ralph Hybrid implementation loop..."
    echo ""

    # Start the main loop
    run_loop
}

run_claude_learn() {
    local phase="$1"
    local timeout_seconds=$((CLAUDE_TIMEOUT_MINUTES * 60))
    local output_file="${STATE_DIR}/learn_${phase// /_}.txt"
    local phase_name="${phase%% *}"  # Get first word (research, analyze, compare, plan)

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ Running: /learn $phase${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────┘${NC}"

    # Record API call
    record_api_call > /dev/null

    # Clear previous output
    > "$output_file"

    # Show spinner while running
    echo -ne "${YELLOW}⏳ Processing...${NC}"

    # Use script for reliable output capture
    local claude_exit=0
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: script -q file command
        script -q "$output_file" bash -c "timeout $timeout_seconds claude -p '/learn $phase' 2>&1" || claude_exit=$?
    else
        # Linux: script -q -c "command" file
        script -q -c "timeout $timeout_seconds claude -p '/learn $phase' 2>&1" "$output_file" || claude_exit=$?
    fi

    # Clean up control characters
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' 's/\r//g' "$output_file" 2>/dev/null || true
    else
        sed -i 's/\r//g' "$output_file" 2>/dev/null || true
    fi

    # Clear spinner line
    echo -ne "\r\033[K"

    if [ "$claude_exit" -eq 124 ]; then
        echo -e "${YELLOW}⚠ Phase timed out after ${CLAUDE_TIMEOUT_MINUTES} minutes${NC}"
        log_warn "Learn phase '$phase' timed out"
    elif [ "$claude_exit" -ne 0 ]; then
        echo -e "${YELLOW}⚠ Phase completed with warnings (exit: $claude_exit)${NC}"
    else
        echo -e "${GREEN}✓ Phase completed successfully${NC}"
    fi

    # Show phase-specific summary
    show_phase_summary "$phase_name" "$output_file"

    # Auto-commit changes from this phase
    auto_commit "$phase_name" "0"

    log_info "Learn phase '$phase' completed"
}

show_phase_summary() {
    local phase="$1"
    local output_file="$2"

    echo ""
    case "$phase" in
        research)
            # Show research findings summary
            echo -e "${CYAN}Research Summary:${NC}"
            local research_dir="${WORKSPACE}/.claude/skills/learning-system/research"
            if [ -d "$research_dir" ]; then
                local count=$(find "$research_dir" -name "*.md" -mmin -30 2>/dev/null | wc -l | tr -d ' ')
                echo -e "  New research files: ${GREEN}$count${NC}"
                # Show recent files
                find "$research_dir" -name "*.md" -mmin -30 2>/dev/null | head -3 | while read f; do
                    echo -e "    - $(basename "$f")"
                done
            else
                echo -e "  ${YELLOW}No research directory found${NC}"
            fi
            ;;
        analyze)
            # Show patterns found
            echo -e "${CYAN}Analysis Summary:${NC}"
            local patterns_file="${WORKSPACE}/.claude/skills/learning-system/insights/patterns.md"
            if [ -f "$patterns_file" ]; then
                local pattern_count=$(grep -c "^## Pattern:" "$patterns_file" 2>/dev/null || echo "0")
                echo -e "  Patterns extracted: ${GREEN}$pattern_count${NC}"
            else
                echo -e "  ${YELLOW}No patterns file generated yet${NC}"
            fi
            ;;
        compare)
            # Show gaps found
            echo -e "${CYAN}Comparison Summary:${NC}"
            local gaps_file="${WORKSPACE}/.claude/skills/learning-system/insights/gap-analysis.md"
            if [ -f "$gaps_file" ]; then
                local gap_count=$(grep -c "^## Gap:" "$gaps_file" 2>/dev/null || echo "0")
                echo -e "  Gaps identified: ${GREEN}$gap_count${NC}"
            else
                echo -e "  ${YELLOW}No gap analysis file generated yet${NC}"
            fi
            ;;
        plan)
            # Show PRD status
            echo -e "${CYAN}Plan Summary:${NC}"
            if [ -f "${WORKSPACE}/prd.json" ]; then
                python3 -c "
import json
with open('${WORKSPACE}/prd.json') as f:
    d = json.load(f)
stories = d.get('userStories', [])
print(f'  Project: {d.get(\"project\", \"Unknown\")}')
print(f'  User Stories: {len(stories)}')
for s in stories[:5]:
    print(f'    - {s.get(\"id\", \"?\")}: {s.get(\"title\", \"Untitled\")[:50]}')
if len(stories) > 5:
    print(f'    ... and {len(stories) - 5} more')
" 2>/dev/null || echo -e "  ${YELLOW}Unable to parse prd.json${NC}"
            else
                echo -e "  ${YELLOW}No prd.json generated${NC}"
            fi
            ;;
    esac
    echo ""
}

run_learn_phases() {
    # Shared phases for both learn and auto-learn
    local skip_implement="${1:-false}"

    # Phase 2: Analyze
    echo ""
    echo -e "${BOLD}Phase 2: ANALYZE${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    run_claude_learn "analyze"

    # Phase 3: Compare
    echo ""
    echo -e "${BOLD}Phase 3: COMPARE${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    run_claude_learn "compare"

    # Phase 4: Plan
    echo ""
    echo -e "${BOLD}Phase 4: PLAN${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    run_claude_learn "plan"

    # Verify and validate PRD
    verify_prd

    # Check PRD and implement
    if [ ! -f "${WORKSPACE}/prd.json" ]; then
        echo -e "${YELLOW}No prd.json generated.${NC}"
        return 0
    fi

    if [ "$skip_implement" = "true" ]; then
        echo -e "${GREEN}PRD generated: ${WORKSPACE}/prd.json${NC}"
        return 0
    fi

    echo ""
    echo -e "${BOLD}Phase 5: IMPLEMENT${NC}"
    echo -e "───────────────────────────────────────────────────────────────"
    run_loop
}

verify_prd() {
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ PRD Verification                                                │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────┘${NC}"

    local prd_file="${WORKSPACE}/prd.json"

    if [ ! -f "$prd_file" ]; then
        echo -e "${YELLOW}⚠ No prd.json found at: $prd_file${NC}"
        echo ""
        echo -e "Would you like to create a template PRD? (y/n)"
        read -r create_template
        if [ "$create_template" = "y" ] || [ "$create_template" = "Y" ]; then
            create_prd_template
        fi
        return 1
    fi

    # Validate PRD structure
    local validation
    validation=$(python3 -c "
import json
import sys

try:
    with open('$prd_file') as f:
        prd = json.load(f)

    errors = []
    warnings = []

    # Required fields
    if 'project' not in prd:
        errors.append('Missing required field: project')
    if 'userStories' not in prd:
        errors.append('Missing required field: userStories')
    elif not isinstance(prd['userStories'], list):
        errors.append('userStories must be a list')
    elif len(prd['userStories']) == 0:
        warnings.append('userStories is empty')
    else:
        # Validate each story
        for i, story in enumerate(prd['userStories']):
            if 'id' not in story:
                errors.append(f'Story {i+1}: missing id')
            if 'title' not in story:
                errors.append(f'Story {i+1}: missing title')

    # Optional but recommended
    if 'branchName' not in prd:
        warnings.append('Missing recommended field: branchName')
    if 'description' not in prd:
        warnings.append('Missing recommended field: description')

    result = {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'story_count': len(prd.get('userStories', [])),
        'project': prd.get('project', 'Unknown')
    }
    print(json.dumps(result))
except json.JSONDecodeError as e:
    print(json.dumps({'valid': False, 'errors': [f'Invalid JSON: {e}'], 'warnings': []}))
except Exception as e:
    print(json.dumps({'valid': False, 'errors': [str(e)], 'warnings': []}))
" 2>/dev/null)

    if [ -z "$validation" ]; then
        echo -e "${RED}✗ Failed to validate PRD${NC}"
        return 1
    fi

    local is_valid
    is_valid=$(echo "$validation" | python3 -c "import sys,json; print(json.load(sys.stdin).get('valid',False))" 2>/dev/null)
    local story_count
    story_count=$(echo "$validation" | python3 -c "import sys,json; print(json.load(sys.stdin).get('story_count',0))" 2>/dev/null)
    local project_name
    project_name=$(echo "$validation" | python3 -c "import sys,json; print(json.load(sys.stdin).get('project','Unknown'))" 2>/dev/null)

    if [ "$is_valid" = "True" ]; then
        echo -e "${GREEN}✓ PRD is valid${NC}"
        echo -e "  Project: ${CYAN}$project_name${NC}"
        echo -e "  Stories: ${CYAN}$story_count${NC}"

        # Show warnings if any
        echo "$validation" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for w in d.get('warnings', []):
    print(f'  ⚠ Warning: {w}')
" 2>/dev/null
    else
        echo -e "${RED}✗ PRD validation failed${NC}"
        echo "$validation" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for e in d.get('errors', []):
    print(f'  ✗ Error: {e}')
for w in d.get('warnings', []):
    print(f'  ⚠ Warning: {w}')
" 2>/dev/null
        return 1
    fi

    echo ""
    return 0
}

create_prd_template() {
    local prd_file="${WORKSPACE}/prd.json"
    local gaps_file="${WORKSPACE}/.claude/skills/learning-system/insights/gap-analysis.md"

    echo -e "${CYAN}Creating PRD template...${NC}"

    # Try to extract gaps from gap-analysis.md if it exists
    local stories="[]"
    if [ -f "$gaps_file" ]; then
        stories=$(python3 -c "
import re
import json

with open('$gaps_file') as f:
    content = f.read()

# Extract gaps
gaps = re.findall(r'## Gap: (.+?)\\n', content)
stories = []
for i, gap in enumerate(gaps[:10], 1):  # Limit to 10 stories
    stories.append({
        'id': f'LEARN-{i:03d}',
        'title': gap.strip(),
        'description': f'Implement improvement based on gap analysis: {gap.strip()}',
        'acceptanceCriteria': [
            'Implementation matches best practice',
            'Tests pass',
            'Documentation updated'
        ],
        'passes': False
    })

print(json.dumps(stories))
" 2>/dev/null || echo "[]")
    fi

    # Create the PRD
    python3 -c "
import json
from datetime import datetime

stories = $stories
if not stories:
    stories = [
        {
            'id': 'LEARN-001',
            'title': 'Placeholder - Add your improvements here',
            'description': 'Replace this with actual improvements from research',
            'acceptanceCriteria': ['Define acceptance criteria'],
            'passes': False
        }
    ]

prd = {
    'project': 'Learning-Driven Improvements',
    'branchName': 'feature/learning-improvements',
    'description': 'Improvements based on research and gap analysis',
    'created': datetime.now().isoformat(),
    'userStories': stories
}

with open('$prd_file', 'w') as f:
    json.dump(prd, f, indent=2)

print(f'Created PRD with {len(stories)} stories')
" 2>/dev/null

    if [ -f "$prd_file" ]; then
        echo -e "${GREEN}✓ PRD template created at: $prd_file${NC}"
        echo -e "  Edit this file to customize your improvement plan."
    else
        echo -e "${RED}✗ Failed to create PRD template${NC}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────────
# CLI Commands
# ─────────────────────────────────────────────────────────────────────────────────

show_help() {
    echo -e "${BOLD}Ralph Hybrid Orchestrator${NC}"
    echo ""
    echo "Usage: ralph_hybrid.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start              Start the autonomous loop (default)"
    echo "  stop               Stop a running loop gracefully"
    echo "  resume             Resume from last checkpoint"
    echo "  status             Show current status"
    echo "  learn [topic]      Run learning pipeline then implement"
    echo "  learn-only [topic] Run learning pipeline without implementing"
    echo "  learn-auto         Auto-detect improvements and implement"
    echo "  learn-auto-only    Auto-detect improvements without implementing"
    echo "  reset              Reset all state"
    echo "  reset-circuit      Reset circuit breaker only"
    echo "  reset-rate         Reset rate limiter only"
    echo "  reset-checkpoint   Clear checkpoint only"
    echo ""
    echo "Stop Command:"
    echo "  The 'stop' command sends a graceful stop signal."
    echo "  The loop will finish its current iteration and exit."
    echo "  Use 'resume' to continue from where it stopped."
    echo ""
    echo "Checkpoint:"
    echo "  Checkpoints are saved after each iteration automatically."
    echo "  Use 'resume' to continue from where you left off."
    echo "  Use 'reset-checkpoint' to start fresh."
    echo ""
    echo "Learning Mode:"
    echo "  learn [topic]      Research specific topic"
    echo "  learn-auto         Analyze project, detect improvements, research & implement"
    echo ""
    echo "Examples:"
    echo "  ralph_hybrid.sh start"
    echo "  ralph_hybrid.sh resume"
    echo "  ralph_hybrid.sh learn taint-analysis"
    echo "  ralph_hybrid.sh learn-auto"
    echo ""
    echo "Environment Variables:"
    echo "  MAX_ITERATIONS          Max loop iterations (default: 100)"
    echo "  MAX_CALLS_PER_HOUR      Rate limit (default: 100)"
    echo "  CLAUDE_TIMEOUT_MINUTES  Timeout per iteration (default: 15)"
    echo "  SLEEP_BETWEEN           Seconds between iterations (default: 5)"
    echo "  AUTO_COMMIT             Auto-commit changes (default: true)"
    echo ""
    echo "Auto-Commit:"
    echo "  Changes are automatically committed after each iteration/phase."
    echo "  Set AUTO_COMMIT=false to disable."
    echo "  Commit messages are generated based on the phase and changes."
}

show_status() {
    echo -e "${BOLD}Ralph Hybrid Status${NC}"
    echo ""

    # PRD Progress (if exists)
    if [ -f "${WORKSPACE}/prd.json" ]; then
        echo -e "${CYAN}PRD Progress:${NC}"
        python3 -c "
import json
with open('${WORKSPACE}/prd.json') as f:
    d = json.load(f)
stories = d.get('userStories', [])
done = sum(1 for s in stories if s.get('passes'))
total = len(stories)
print(f'  Project: {d.get(\"project\", \"Unknown\")}')
print(f'  Progress: {done}/{total} tasks complete')
for s in stories:
    status = '✅' if s.get('passes') else '⏳'
    print(f'    {status} {s[\"id\"]}: {s[\"title\"]}')
" 2>/dev/null || echo "  Unable to read prd.json"
        echo ""
    fi

    # Circuit breaker
    echo -e "${CYAN}Circuit Breaker:${NC}"
    check_circuit_breaker | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  State: {d.get('state', 'UNKNOWN')}\")
print(f\"  Can Proceed: {d.get('can_proceed', True)}\")
print(f\"  No Progress Count: {d.get('no_progress_count', 0)}\")
" 2>/dev/null || echo "  Unable to read state"

    echo ""

    # Rate limiter
    echo -e "${CYAN}Rate Limiter:${NC}"
    check_rate_limit | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Calls This Hour: {d.get('calls_this_hour', 0)}\")
print(f\"  Remaining: {d.get('remaining', 100)}\")
print(f\"  Can Proceed: {d.get('can_proceed', True)}\")
" 2>/dev/null || echo "  Unable to read state"

    echo ""

    # Last analysis
    if [ -f "$STATE_DIR/.response_analysis" ]; then
        echo -e "${CYAN}Last Response Analysis:${NC}"
        cat "$STATE_DIR/.response_analysis" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d.get('status', {})
i = d.get('indicators', {})
print(f\"  Status: {s.get('status', 'UNKNOWN')}\")
print(f\"  EXIT_SIGNAL: {s.get('exit_signal', False)}\")
print(f\"  Should Exit: {i.get('should_exit', False)}\")
print(f\"  Indicator Count: {i.get('count', 0)}\")
" 2>/dev/null || echo "  Unable to read analysis"
    fi

    echo ""

    # Checkpoint
    display_checkpoint
}

reset_all() {
    echo -e "${YELLOW}Resetting all Ralph Hybrid state...${NC}"
    rm -rf "$STATE_DIR"
    mkdir -p "$STATE_DIR"
    echo -e "${GREEN}✓ All state reset${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────────
# Signal Handlers
# ─────────────────────────────────────────────────────────────────────────────────

trap_handler() {
    echo ""
    echo -e "${YELLOW}╭─────────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${YELLOW}│ ⏸️  Loop paused by user (Ctrl+C)                                │${NC}"
    echo -e "${YELLOW}│ Run: ralph_hybrid.sh start  to resume                          │${NC}"
    echo -e "${YELLOW}╰─────────────────────────────────────────────────────────────────╯${NC}"
    log_info "Loop paused by user"
    exit 0
}

trap trap_handler INT TERM

# ─────────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────────

main() {
    init

    case "${1:-start}" in
        start)
            run_loop "false"
            ;;
        stop)
            # Send stop signal to running loop
            init
            request_stop "user_command"
            ;;
        resume)
            # Resume from last checkpoint
            run_loop "true"
            ;;
        learn)
            # Learn and implement: research → analyze → compare → plan → implement
            run_learn "${2:-}" "false"
            ;;
        learn-only)
            # Learn without implementing: research → analyze → compare → plan
            run_learn "${2:-}" "true"
            ;;
        learn-auto)
            # Auto-learn: analyze project → research → analyze → compare → plan → implement
            run_auto_learn "false"
            ;;
        learn-auto-only)
            # Auto-learn without implementing
            run_auto_learn "true"
            ;;
        status)
            show_status
            ;;
        reset)
            reset_all
            ;;
        reset-circuit)
            python3 "$SCRIPT_DIR/ralph_circuit_breaker.py" reset
            echo -e "${GREEN}✓ Circuit breaker reset${NC}"
            ;;
        reset-rate)
            python3 "$SCRIPT_DIR/ralph_rate_limiter.py" reset
            echo -e "${GREEN}✓ Rate limiter reset${NC}"
            ;;
        reset-checkpoint)
            clear_checkpoint
            echo -e "${GREEN}✓ Checkpoint cleared${NC}"
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
