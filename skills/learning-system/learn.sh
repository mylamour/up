#!/bin/bash

# Learning System Orchestrator
# Runs research, analysis, and planning phases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   RALPH HYBRID LEARNING SYSTEM                                ║"
    echo "║   Research → Analyze → Compare → Plan → Implement             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    echo "Usage: learn.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  research [topic]  Research a specific topic"
    echo "  analyze           Analyze all research findings"
    echo "  compare           Compare with current codebase"
    echo "  plan              Generate improvement PRD"
    echo "  full              Run complete pipeline"
    echo "  status            Show learning system status"
}

show_status() {
    echo -e "${CYAN}Learning System Status${NC}"
    echo ""

    # Count research files
    research_count=$(ls -1 "$SCRIPT_DIR/research/"*.md 2>/dev/null | wc -l || echo "0")
    echo "Research files: $research_count"

    # Check insights
    if [ -f "$SCRIPT_DIR/insights/patterns.md" ]; then
        echo "Patterns: ✅ Generated"
    else
        echo "Patterns: ⏳ Not yet generated"
    fi

    if [ -f "$SCRIPT_DIR/insights/gap-analysis.md" ]; then
        echo "Gap Analysis: ✅ Generated"
    else
        echo "Gap Analysis: ⏳ Not yet generated"
    fi

    # Check PRD
    if [ -f "$WORKSPACE/prd.json" ]; then
        echo "PRD: ✅ Generated"
    else
        echo "PRD: ⏳ Not yet generated"
    fi
}

main() {
    print_banner

    case "${1:-help}" in
        research|analyze|compare|plan|full)
            echo -e "${YELLOW}Use Claude to run: /learn $1${NC}"
            echo "The learning system requires Claude's web search and analysis capabilities."
            ;;
        status)
            show_status
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
