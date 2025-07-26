#!/bin/bash
# Quick Start Script for Local Mutation Testing
# 
# This script provides a one-command way to run mutation tests locally
# with automatic setup, progress indicators, and report generation.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
TARGET_FILES=""
OPEN_REPORT=true
BASELINE_CHECK=false
QUICK_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET_FILES="$2"
            shift 2
            ;;
        --no-open)
            OPEN_REPORT=false
            shift
            ;;
        --baseline)
            BASELINE_CHECK=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --help|-h)
            echo "🦠 Local Mutation Testing Quick Start"
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --target FILE     Target specific file for mutation testing"
            echo "  --no-open         Don't automatically open the HTML report"
            echo "  --baseline        Run with baseline checking and tracking"
            echo "  --quick           Quick mode - target models.py only for fast feedback"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Full mutation test with HTML report"
            echo "  $0 --quick                   # Quick test on models.py only"
            echo "  $0 --target src/database.py  # Test specific file"
            echo "  $0 --baseline                # Run with baseline tracking"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${BLUE}🦠 Local Mutation Testing Quick Start${NC}"
echo "======================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/leaderboard" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
    echo "   Expected to find: pyproject.toml and src/leaderboard/"
    exit 1
fi

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
    if [ -d "test_venv" ]; then
        echo "   Activating test_venv..."
        source test_venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    elif [ -d ".venv" ]; then
        echo "   Activating .venv..."
        source .venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    else
        echo -e "${YELLOW}   Consider creating a virtual environment: python3 -m venv .venv${NC}"
        echo "   Continuing with system Python..."
    fi
fi

# Verify dependencies
echo -e "${BLUE}🔍 Checking dependencies...${NC}"
if ! python3 -c "import mutmut" 2>/dev/null; then
    echo -e "${RED}❌ mutmut not found. Installing dependencies...${NC}"
    pip install -r requirements-dev.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies OK${NC}"
fi

# Clean previous artifacts
echo -e "${BLUE}🧹 Cleaning previous artifacts...${NC}"
rm -rf .mutmut-cache/ html/ mutmut.log 2>/dev/null || true
echo -e "${GREEN}✅ Cleaned${NC}"

# Determine what to test
if [ "$QUICK_MODE" = true ]; then
    TARGET_FILES="src/leaderboard/models.py"
    echo -e "${YELLOW}⚡ Quick mode: testing models.py only${NC}"
elif [ -n "$TARGET_FILES" ]; then
    echo -e "${YELLOW}🎯 Targeting: $TARGET_FILES${NC}"
else
    echo -e "${BLUE}🎯 Testing all source files${NC}"
fi

# Run mutation tests
echo ""
echo -e "${BLUE}🦠 Running mutation tests...${NC}"
if [ "$BASELINE_CHECK" = true ]; then
    echo "   Using baseline tracking script..."
    python3 scripts/mutation-baseline.py
else
    echo "   Running mutmut directly..."
    START_TIME=$(date +%s)
    
    if [ -n "$TARGET_FILES" ]; then
        python3 -m mutmut run --paths-to-mutate "$TARGET_FILES"
    else
        python3 -m mutmut run
    fi
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo -e "${GREEN}✅ Mutation tests completed in ${DURATION}s${NC}"
fi

# Generate reports
echo ""
echo -e "${BLUE}📊 Generating reports...${NC}"

# Generate HTML report
python3 -m mutmut html
echo -e "${GREEN}✅ HTML report generated: html/index.html${NC}"

# Show text summary
echo ""
echo -e "${BLUE}📋 Results Summary:${NC}"
python3 -m mutmut results

# Calculate mutation score for display
RESULTS_OUTPUT=$(python3 -m mutmut results)
KILLED=$(echo "$RESULTS_OUTPUT" | grep -o '🎉 [0-9]*' | grep -o '[0-9]*' || echo "0")
SURVIVED=$(echo "$RESULTS_OUTPUT" | grep -o '🙁 [0-9]*' | grep -o '[0-9]*' || echo "0")

if [ "$KILLED" -gt 0 ] || [ "$SURVIVED" -gt 0 ]; then
    TOTAL=$((KILLED + SURVIVED))
    if [ "$TOTAL" -gt 0 ]; then
        SCORE=$(python3 -c "print(f'{($KILLED / $TOTAL) * 100:.1f}')")
        echo ""
        echo -e "${GREEN}🎯 Mutation Score: ${SCORE}%${NC}"
        
        if (( $(echo "$SCORE >= 90" | bc -l) )); then
            echo -e "${GREEN}   Excellent! Your tests are very robust.${NC}"
        elif (( $(echo "$SCORE >= 80" | bc -l) )); then
            echo -e "${YELLOW}   Very good! Consider improving tests for surviving mutants.${NC}"
        elif (( $(echo "$SCORE >= 70" | bc -l) )); then
            echo -e "${YELLOW}   Good! There's room for test improvements.${NC}"
        else
            echo -e "${RED}   Tests could be improved. Focus on surviving mutants.${NC}"
        fi
    fi
fi

# Open HTML report if requested
if [ "$OPEN_REPORT" = true ] && [ -f "html/index.html" ]; then
    echo ""
    echo -e "${BLUE}🌐 Opening HTML report...${NC}"
    
    # Try to open the report with the default browser
    if command -v xdg-open > /dev/null; then
        xdg-open html/index.html
    elif command -v open > /dev/null; then
        open html/index.html
    elif command -v start > /dev/null; then
        start html/index.html
    else
        echo -e "${YELLOW}   Could not auto-open browser. Please open: html/index.html${NC}"
    fi
fi

# Next steps
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "   📊 View detailed report: open html/index.html"
echo "   🔍 Interactive analysis: make mutate-browse"
echo "   🎯 Focus on specific files: $0 --target src/leaderboard/handler.py"
echo "   🧹 Clean up: make mutate-clean"
echo ""
echo -e "${GREEN}✅ Mutation testing completed successfully!${NC}"