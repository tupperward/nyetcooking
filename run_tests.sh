#!/bin/bash
# Test runner script for Nyetcooking
# This script runs the test suite with appropriate options for CI/CD

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}  Nyetcooking Test Suite${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Check if pytest is installed (check python module, not command)
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Run: pip3 install -r requirements.txt"
    exit 1
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --test|-t)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage    Run with coverage reporting"
            echo "  -v, --verbose     Run with extra verbose output"
            echo "  -t, --test PATH   Run specific test (e.g., tests/test_app.py::TestRecipeSlug)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests"
            echo "  $0 --coverage                         # Run with coverage"
            echo "  $0 --test tests/test_app.py          # Run specific test file"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="python3 -m pytest"

# Add test path if specified
if [ -n "$SPECIFIC_TEST" ]; then
    PYTEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}Running tests with coverage...${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=web --cov-report=term-missing --cov-report=xml --cov-report=html"
else
    echo -e "${YELLOW}Running tests...${NC}"
fi

# Add verbose if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
echo ""

# Run the tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}==================================${NC}"
    echo -e "${GREEN}  All tests passed! ✓${NC}"
    echo -e "${GREEN}==================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage reports generated:${NC}"
        echo "  - Terminal output (above)"
        echo "  - XML: coverage.xml"
        echo "  - HTML: htmlcov/index.html"
        echo ""
        echo -e "${BLUE}To view HTML coverage:${NC}"
        echo "  open htmlcov/index.html  # macOS"
        echo "  xdg-open htmlcov/index.html  # Linux"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}==================================${NC}"
    echo -e "${RED}  Tests failed! ✗${NC}"
    echo -e "${RED}==================================${NC}"
    exit 1
fi
