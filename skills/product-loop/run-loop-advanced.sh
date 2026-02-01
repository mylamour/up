#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# Product Build Loop - Advanced Runner
# Multi-mode infinite development loop with smart scheduling
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
MAX_ITERATIONS=${MAX_ITERATIONS:-100}
SLEEP_BETWEEN=${SLEEP_BETWEEN:-3}
MODE=${MODE:-"full"}              # full, features, quality, docs
FOCUS=${FOCUS:-""}                # Optional focus area
LOG_FILE="product-loop.log"
STATE_FILE=".product-loop-state"
METRICS_FILE=".product-loop-metrics"

# ─────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ████████╗██████╗  ██████╗ ██████╗ ██╗   ██╗ ██████╗████████╗║
    ║   ██╔═══██║██╔══██╗██╔═══██╗██╔══██╗██║   ██║██╔════╝╚══██╔══╝║
    ║   ████████║██████╔╝██║   ██║██║  ██║██║   ██║██║        ██║   ║
    ║   ██╔═════╝██╔══██╗██║   ██║██║  ██║██║   ██║██║        ██║   ║
    ║   ██║      ██║  ██║╚██████╔╝██████╔╝╚██████╔╝╚██████╗   ██║   ║
    ║   ╚═╝      ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝   ╚═╝   ║
    ║                                                               ║
    ║              BUILD LOOP - Infinite Development                ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$MODE] $1" >> "$LOG_FILE"
}

save_state() {
    cat > "$STATE_FILE" << EOF
iteration=$1
phase=$2
mode=$MODE
focus=$FOCUS
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
EOF
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        echo -e "${YELLOW}📂 Resuming: iteration=$iteration, mode=$mode${NC}"
        MODE=$mode
        return 0
    fi
    return 1
}

update_metrics() {
    local key=$1
    local value=$2
    
    if [ ! -f "$METRICS_FILE" ]; then
        echo "{}" > "$METRICS_FILE"
    fi
    
    # Simple metrics tracking
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$key,$value" >> "${METRICS_FILE}.csv"
}

# ─────────────────────────────────────────────────────────────────
# Mode-Specific Prompts
# ─────────────────────────────────────────────────────────────────

get_mode_prompt() {
    local mode=$1
    local focus=$2
    
    case $mode in
        "full")
            echo "/product-loop"
            ;;
        "features")
            echo "/product-loop Focus only on Phase 2 (BUILD). Implement features from TODO.md. Skip design analysis and enhancement discovery. Just build what's defined."
            ;;
        "quality")
            echo "/product-loop Focus on Phase 3 (TEST) and Phase 5 (ANALYZE). Run all quality checks, fix issues, discover improvements. Don't implement new features."
            ;;
        "docs")
            echo "/product-loop Focus on Phase 4 (SHIP). Update all documentation, README, CHANGELOG, API docs. Don't implement new features."
            ;;
        "custom")
            echo "/product-loop Focus specifically on: $focus"
            ;;
        *)
            echo "/product-loop"
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────
# Progress Display
# ─────────────────────────────────────────────────────────────────

display_progress() {
    local iteration=$1
    local phase=$2
    
    # Progress bar
    local progress=$((iteration * 100 / MAX_ITERATIONS))
    local filled=$((progress / 5))
    local empty=$((20 - filled))
    
    echo -e "${BLUE}"
    printf "Progress: ["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %d%%\n" $progress
    echo -e "${NC}"
}

# ─────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────

run_health_check() {
    echo -e "${CYAN}Running pre-loop health check...${NC}"
    
    local errors=0
    
    # Check for required files
    if [ ! -f "TODO.md" ]; then
        echo -e "${YELLOW}  ⚠ TODO.md not found (will create)${NC}"
    else
        echo -e "${GREEN}  ✓ TODO.md found${NC}"
    fi
    
    if [ ! -f "CLAUDE.md" ]; then
        echo -e "${RED}  ✗ CLAUDE.md not found (required)${NC}"
        errors=$((errors + 1))
    else
        echo -e "${GREEN}  ✓ CLAUDE.md found${NC}"
    fi
    
    # Check for Python environment
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}  ✓ Python3 available${NC}"
    else
        echo -e "${RED}  ✗ Python3 not found${NC}"
        errors=$((errors + 1))
    fi
    
    # Check for Claude CLI
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}  ✓ Claude CLI available${NC}"
    else
        echo -e "${RED}  ✗ Claude CLI not found${NC}"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        echo -e "${RED}Health check failed with $errors errors${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Health check passed!${NC}"
    return 0
}

# ─────────────────────────────────────────────────────────────────
# Main Loop
# ─────────────────────────────────────────────────────────────────

run_loop() {
    local iteration=1
    local phase="INIT"
    local consecutive_failures=0
    local max_consecutive_failures=3
    
    # Check for resume
    if load_state; then
        iteration=$((iteration + 1))
    fi
    
    print_banner
    
    echo -e "${BOLD}Configuration:${NC}"
    echo -e "  Mode: ${CYAN}$MODE${NC}"
    echo -e "  Max Iterations: ${CYAN}$MAX_ITERATIONS${NC}"
    echo -e "  Sleep Between: ${CYAN}${SLEEP_BETWEEN}s${NC}"
    if [ -n "$FOCUS" ]; then
        echo -e "  Focus: ${CYAN}$FOCUS${NC}"
    fi
    echo ""
    
    # Health check
    if ! run_health_check; then
        echo -e "${RED}Fix health check errors before continuing.${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}Starting Product Build Loop...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to pause${NC}"
    echo ""
    
    log "Loop started with mode=$MODE"
    
    while [ $iteration -le $MAX_ITERATIONS ]; do
        # Display iteration header
        echo ""
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD} Iteration $iteration / $MAX_ITERATIONS ${NC}"
        echo -e "${PURPLE}───────────────────────────────────────────────────────────────${NC}"
        echo -e " $(date '+%Y-%m-%d %H:%M:%S')"
        display_progress $iteration "RUNNING"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        
        save_state $iteration $phase
        
        # Get the appropriate prompt for the mode
        local PROMPT=$(get_mode_prompt "$MODE" "$FOCUS")
        
        log "Iteration $iteration: Running with prompt: $PROMPT"
        
        # Run Claude
        local start_time=$(date +%s)
        OUTPUT=$(claude -p "$PROMPT" 2>&1 || true)
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo "$OUTPUT"
        
        # Log
        echo "=== Iteration $iteration (${duration}s) ===" >> "$LOG_FILE"
        echo "$OUTPUT" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        update_metrics "iteration_duration" $duration
        
        # Check for completion
        if echo "$OUTPUT" | grep -q "PRODUCT BUILD COMPLETE"; then
            echo ""
            echo -e "${GREEN}"
            cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🎉🎉🎉  PRODUCT BUILD COMPLETE!  🎉🎉🎉                     ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
EOF
            echo -e "${NC}"
            echo -e "  Total iterations: ${CYAN}$iteration${NC}"
            echo -e "  Log file: ${CYAN}$LOG_FILE${NC}"
            
            log "COMPLETE after $iteration iterations"
            rm -f "$STATE_FILE"
            exit 0
        fi
        
        # Check for errors
        if echo "$OUTPUT" | grep -qE "(CRITICAL ERROR|FATAL|Traceback)"; then
            consecutive_failures=$((consecutive_failures + 1))
            log "Error detected (failure $consecutive_failures/$max_consecutive_failures)"
            
            if [ $consecutive_failures -ge $max_consecutive_failures ]; then
                echo -e "${RED}Too many consecutive failures. Stopping.${NC}"
                log "Stopped due to consecutive failures"
                exit 1
            fi
            
            echo -e "${YELLOW}Error detected. Retrying... ($consecutive_failures/$max_consecutive_failures)${NC}"
        else
            consecutive_failures=0
        fi
        
        # Next iteration
        iteration=$((iteration + 1))
        
        if [ $iteration -le $MAX_ITERATIONS ]; then
            echo ""
            echo -e "${CYAN}⏳ Next iteration in ${SLEEP_BETWEEN}s...${NC}"
            sleep $SLEEP_BETWEEN
        fi
    done
    
    echo -e "${YELLOW}Maximum iterations reached.${NC}"
    log "Max iterations reached"
    exit 1
}

# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

show_help() {
    echo -e "${BOLD}Product Build Loop - Advanced Runner${NC}"
    echo ""
    echo "Usage: ./run-loop-advanced.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start         Start the loop (default)"
    echo "  status        Show current loop status"
    echo "  reset         Reset state and start fresh"
    echo "  metrics       Show loop metrics"
    echo ""
    echo "Options:"
    echo "  --mode MODE   Set loop mode (full|features|quality|docs|custom)"
    echo "  --focus TEXT  Focus area for custom mode"
    echo "  --max N       Maximum iterations (default: 100)"
    echo "  --sleep N     Seconds between iterations (default: 3)"
    echo ""
    echo "Modes:"
    echo "  full      Complete SDLC loop (default)"
    echo "  features  Focus on implementing features"
    echo "  quality   Focus on tests, types, linting"
    echo "  docs      Focus on documentation"
    echo "  custom    Custom focus (use --focus)"
    echo ""
    echo "Examples:"
    echo "  ./run-loop-advanced.sh"
    echo "  ./run-loop-advanced.sh --mode features --max 50"
    echo "  ./run-loop-advanced.sh --mode custom --focus 'RCE Hunter module'"
}

show_status() {
    echo -e "${BOLD}Product Build Loop Status${NC}"
    echo ""
    
    if [ -f "$STATE_FILE" ]; then
        echo -e "${CYAN}Current State:${NC}"
        cat "$STATE_FILE" | while read line; do
            echo "  $line"
        done
    else
        echo "No saved state. Loop will start fresh."
    fi
    
    echo ""
    
    if [ -f "$LOG_FILE" ]; then
        local lines=$(wc -l < "$LOG_FILE")
        local iterations=$(grep -c "^=== Iteration" "$LOG_FILE" || echo "0")
        echo -e "${CYAN}Log Statistics:${NC}"
        echo "  Log file: $LOG_FILE"
        echo "  Total lines: $lines"
        echo "  Iterations logged: $iterations"
    fi
}

show_metrics() {
    echo -e "${BOLD}Product Build Loop Metrics${NC}"
    echo ""
    
    if [ -f "${METRICS_FILE}.csv" ]; then
        echo -e "${CYAN}Recent Metrics:${NC}"
        tail -20 "${METRICS_FILE}.csv" | while read line; do
            echo "  $line"
        done
    else
        echo "No metrics recorded yet."
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        start)
            shift
            ;;
        status)
            show_status
            exit 0
            ;;
        reset)
            rm -f "$STATE_FILE" "$METRICS_FILE" "${METRICS_FILE}.csv"
            echo -e "${GREEN}✓ State reset${NC}"
            exit 0
            ;;
        metrics)
            show_metrics
            exit 0
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --focus)
            FOCUS="$2"
            MODE="custom"
            shift 2
            ;;
        --max)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        --sleep)
            SLEEP_BETWEEN="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Trap Ctrl+C
trap 'echo ""; echo -e "${YELLOW}Paused. Run again to resume.${NC}"; log "Paused by user"; exit 0' INT TERM

# Run the loop
run_loop
