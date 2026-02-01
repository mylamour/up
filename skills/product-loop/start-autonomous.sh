#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# Start Autonomous AI Agent
# Uses YOUR EXISTING Claude CLI - NO API keys needed
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_FILE="$WORKSPACE/agent.log"
PID_FILE="$WORKSPACE/.agent.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     AUTONOMOUS AI AGENT - Using Claude CLI                    ║"
    echo "║     No API keys needed - uses your existing 'claude' command  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_claude_cli() {
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}✓ Claude CLI found: $(which claude)${NC}"
        return 0
    else
        echo -e "${RED}✗ Claude CLI not found!${NC}"
        echo ""
        echo "The 'claude' command is not in your PATH."
        echo "Make sure Claude CLI is installed and accessible."
        return 1
    fi
}

start_agent() {
    echo "Starting autonomous agent..."
    echo "Log file: $LOG_FILE"
    echo ""
    
    # Start in background
    cd "$WORKSPACE"
    nohup python3 "$SCRIPT_DIR/autonomous_agent.py" >> "$LOG_FILE" 2>&1 &
    
    # Save PID
    echo $! > "$PID_FILE"
    
    echo -e "${GREEN}✓ Agent started with PID $(cat $PID_FILE)${NC}"
    echo ""
    echo "The agent will:"
    echo "  1. Read TODO.md and V1_RELEASE_CHECKLIST.md"
    echo "  2. Find the next uncompleted [ ] task"
    echo "  3. Call 'claude -p /product-loop' to implement it"
    echo "  4. Repeat until all tasks are [x] complete"
    echo ""
    echo -e "${YELLOW}Each iteration takes ~10-15 minutes${NC}"
    echo ""
    echo "Commands:"
    echo "  Monitor:  tail -f $LOG_FILE"
    echo "  Status:   $0 status"
    echo "  Stop:     $0 stop"
}

stop_agent() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            rm "$PID_FILE"
            echo -e "${GREEN}✓ Agent stopped${NC}"
        else
            rm "$PID_FILE"
            echo -e "${YELLOW}Agent was not running${NC}"
        fi
    else
        echo -e "${YELLOW}No PID file found${NC}"
    fi
}

status_agent() {
    echo ""
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Agent is running (PID: $PID)${NC}"
            echo ""
            
            # Show task progress
            echo "Task Progress:"
            if [ -f "$WORKSPACE/docs/todo/V1_RELEASE_CHECKLIST.md" ]; then
                DONE=$(grep -c '\[x\]' "$WORKSPACE/docs/todo/V1_RELEASE_CHECKLIST.md" 2>/dev/null || echo "0")
                TODO=$(grep -c '\[ \]' "$WORKSPACE/docs/todo/V1_RELEASE_CHECKLIST.md" 2>/dev/null || echo "0")
                echo "  Checklist: $DONE done, $TODO remaining"
            fi
            echo ""
            
            echo "Recent log (last 15 lines):"
            echo "─────────────────────────────────────"
            tail -15 "$LOG_FILE" 2>/dev/null || echo "(no log yet)"
            echo "─────────────────────────────────────"
        else
            echo -e "${YELLOW}Agent is not running (stale PID file)${NC}"
            rm "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}Agent is not running${NC}"
    fi
}

show_help() {
    print_banner
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    Start the autonomous agent in background"
    echo "  stop     Stop the running agent"
    echo "  status   Check agent status and progress"
    echo "  logs     Show live log output (Ctrl+C to exit)"
    echo "  help     Show this help"
    echo ""
    echo "How it works:"
    echo "  1. Reads your TODO.md and V1_RELEASE_CHECKLIST.md"
    echo "  2. Finds the next [ ] uncompleted item"
    echo "  3. Calls 'claude -p /product-loop' to implement it"
    echo "  4. Checks if task was marked [x] complete"
    echo "  5. Repeats until ALL tasks are done"
    echo ""
    echo "Requirements:"
    echo "  - Claude CLI ('claude' command) must be installed"
    echo "  - No API keys needed - uses your existing Claude setup"
}

# Main
case "${1:-}" in
    start)
        print_banner
        if check_claude_cli; then
            start_agent
        else
            exit 1
        fi
        ;;
    stop)
        stop_agent
        ;;
    status)
        status_agent
        ;;
    logs)
        echo "Showing live log (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
