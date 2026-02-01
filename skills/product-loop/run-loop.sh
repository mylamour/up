#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# Product Build Loop Runner
# Infinite autonomous development loop for building your product
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
MAX_ITERATIONS=${MAX_ITERATIONS:-100}     # Safety limit
SLEEP_BETWEEN=${SLEEP_BETWEEN:-3}         # Seconds between iterations
LOG_FILE="product-loop.log"
STATE_FILE=".product-loop-state"

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   🔄 PRODUCT BUILD LOOP                                       ║"
    echo "║                                                               ║"
    echo "║   Infinite autonomous development cycle:                      ║"
    echo "║   DESIGN → BUILD → TEST → SHIP → ANALYZE → repeat            ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print phase
print_phase() {
    local phase=$1
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📍 Phase: ${phase}${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print iteration header
print_iteration() {
    local iteration=$1
    echo ""
    echo -e "${BLUE}╭─────────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${BLUE}│ 🔁 Iteration ${iteration}/${MAX_ITERATIONS}                                           │${NC}"
    echo -e "${BLUE}│ $(date '+%Y-%m-%d %H:%M:%S')                                      │${NC}"
    echo -e "${BLUE}╰─────────────────────────────────────────────────────────────────╯${NC}"
}

# Log message
log() {
    local msg=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" >> "$LOG_FILE"
}

# Save state
save_state() {
    local iteration=$1
    local phase=$2
    echo "iteration=$iteration" > "$STATE_FILE"
    echo "phase=$phase" >> "$STATE_FILE"
    echo "timestamp=$(date '+%Y-%m-%d %H:%M:%S')" >> "$STATE_FILE"
}

# Load state (for resume)
load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        echo -e "${YELLOW}📂 Resuming from iteration $iteration, phase: $phase${NC}"
        return 0
    fi
    return 1
}

# Check for completion
check_complete() {
    local output=$1
    if echo "$output" | grep -q "PRODUCT BUILD COMPLETE"; then
        return 0
    fi
    return 1
}

# Run the product loop
run_product_loop() {
    local iteration=1
    local phase="DESIGN"
    
    # Check for resume
    if load_state; then
        iteration=$((iteration + 1))
    fi
    
    print_banner
    log "Starting Product Build Loop"
    
    echo -e "${GREEN}Starting infinite development loop...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop at any time.${NC}"
    echo ""
    
    while [ $iteration -le $MAX_ITERATIONS ]; do
        print_iteration $iteration
        save_state $iteration $phase
        
        # Run Claude with the product-loop skill
        log "Iteration $iteration starting"
        
        OUTPUT=$(claude -p "/product-loop" 2>&1 || true)
        
        echo "$OUTPUT"
        echo ""
        
        # Log output
        echo "=== Iteration $iteration ===" >> "$LOG_FILE"
        echo "$OUTPUT" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        # Check for completion
        if check_complete "$OUTPUT"; then
            echo ""
            echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║   🎉 PRODUCT BUILD COMPLETE! 🎉                               ║${NC}"
            echo -e "${GREEN}║                                                               ║${NC}"
            echo -e "${GREEN}║   Total iterations: $iteration                                     ║${NC}"
            echo -e "${GREEN}║   Log file: $LOG_FILE                                  ║${NC}"
            echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
            
            log "Product Build Complete after $iteration iterations"
            rm -f "$STATE_FILE"
            exit 0
        fi
        
        # Check for critical errors
        if echo "$OUTPUT" | grep -q "CRITICAL ERROR"; then
            echo -e "${RED}❌ Critical error detected. Stopping loop.${NC}"
            log "Critical error at iteration $iteration"
            exit 1
        fi
        
        # Safety limit check
        if [ $iteration -eq $MAX_ITERATIONS ]; then
            echo ""
            echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║   ⚠️  Maximum iterations reached ($MAX_ITERATIONS)                        ║${NC}"
            echo -e "${YELLOW}║                                                               ║${NC}"
            echo -e "${YELLOW}║   The loop has run $MAX_ITERATIONS times without completing.          ║${NC}"
            echo -e "${YELLOW}║   Review $LOG_FILE for progress.                       ║${NC}"
            echo -e "${YELLOW}║                                                               ║${NC}"
            echo -e "${YELLOW}║   To continue: MAX_ITERATIONS=200 ./run-loop.sh               ║${NC}"
            echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
            
            log "Max iterations reached"
            exit 1
        fi
        
        iteration=$((iteration + 1))
        
        echo -e "${CYAN}⏳ Sleeping ${SLEEP_BETWEEN}s before next iteration...${NC}"
        sleep $SLEEP_BETWEEN
    done
}

# Handle Ctrl+C gracefully
trap_handler() {
    echo ""
    echo -e "${YELLOW}╭─────────────────────────────────────────────────────────────────╮${NC}"
    echo -e "${YELLOW}│ ⏸️  Loop paused by user (Ctrl+C)                                │${NC}"
    echo -e "${YELLOW}│                                                                 │${NC}"
    echo -e "${YELLOW}│ To resume: ./run-loop.sh                                        │${NC}"
    echo -e "${YELLOW}│ To restart: rm .product-loop-state && ./run-loop.sh             │${NC}"
    echo -e "${YELLOW}╰─────────────────────────────────────────────────────────────────╯${NC}"
    log "Loop paused by user"
    exit 0
}

trap trap_handler INT TERM

# Main
main() {
    case "${1:-}" in
        --help|-h)
            echo "Usage: ./run-loop.sh [options]"
            echo ""
            echo "Options:"
            echo "  --help, -h     Show this help message"
            echo "  --reset        Reset state and start fresh"
            echo "  --status       Show current loop status"
            echo ""
            echo "Environment variables:"
            echo "  MAX_ITERATIONS  Maximum iterations (default: 100)"
            echo "  SLEEP_BETWEEN   Seconds between iterations (default: 3)"
            exit 0
            ;;
        --reset)
            rm -f "$STATE_FILE"
            echo -e "${GREEN}✓ State reset. Loop will start fresh.${NC}"
            exit 0
            ;;
        --status)
            if [ -f "$STATE_FILE" ]; then
                echo -e "${CYAN}Current state:${NC}"
                cat "$STATE_FILE"
            else
                echo "No saved state. Loop will start from beginning."
            fi
            exit 0
            ;;
        *)
            run_product_loop
            ;;
    esac
}

main "$@"
