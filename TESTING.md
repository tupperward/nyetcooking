# Testing Guide

This document describes how to run the test suite for the Nyetcooking recipe card generator.

## Overview

The test suite is built with pytest and includes:
- 36 comprehensive unit and integration tests
- Code coverage reporting with pytest-cov
- CI/CD integration via GitHub Actions
- Tests for Flask routes, recipe processing, caching, and Redis integration

## Prerequisites

Install the required testing dependencies:

```bash
pip3 install -r requirements.txt
```

This installs:
- `pytest>=7.0.0` - Test framework
- `pytest-mock>=3.10.0` - Mocking utilities
- `pytest-cov>=4.0.0` - Coverage reporting

## Running Tests

### Basic Test Run

Run all tests with verbose output:

```bash
pytest
```

Or explicitly:

```bash
python3 -m pytest
```

### Run Specific Tests

Run a specific test file:

```bash
pytest tests/test_app.py
```

Run a specific test class:

```bash
pytest tests/test_app.py::TestRecipeSlug
```

Run a specific test:

```bash
pytest tests/test_app.py::TestRecipeSlug::test_basic_slug
```

### Coverage Reports

Run tests with coverage reporting:

```bash
pytest --cov=web --cov-report=term-missing
```

Generate multiple coverage report formats:

```bash
pytest --cov=web --cov-report=term-missing --cov-report=html --cov-report=xml
```

This creates:
- Terminal output with line-by-line coverage
- `htmlcov/` directory with browsable HTML report
- `coverage.xml` for CI/CD integration

View HTML coverage report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Configuration

Test configuration is managed in `pytest.ini`:

- **Test discovery**: Automatically finds `test_*.py` files in `tests/` directory
- **Output format**: Verbose with short tracebacks for readability
- **Coverage settings**: Configured to track `web/` and `modules/` directories
- **Markers**: Tests can be marked as `slow`, `unit`, or `integration`

## CI/CD Integration

### GitHub Actions

The test suite runs automatically on:
- Push to `main`, `flask-rewrite`, or `flask-rewrite-redis` branches
- Pull requests to `main`

The CI workflow (`.github/workflows/test.yml`) runs tests on:
- Python 3.9, 3.10, and 3.11
- Generates coverage reports
- Uploads coverage to Codecov (optional)

### Running Tests Locally (CI-style)

To run tests exactly as CI does:

```bash
pytest --cov=web --cov-report=term-missing --cov-report=xml
```

## Test Structure

The test suite (`tests/test_app.py`) is organized into classes:

- **TestRecipeSlug** - URL slug generation
- **TestNYTRecipeID** - NYT recipe ID extraction
- **TestMarkdownConversion** - Recipe to markdown conversion
- **TestCaching** - Recipe caching with Redis/in-memory
- **TestHealthEndpoint** - Health check endpoint
- **TestIndexRoute** - Main index page
- **TestRecipeProcessing** - Recipe URL processing
- **TestRetryLogic** - Retry mechanisms for fetching
- **TestImageFormats** - Different image format handling
- **TestMarkdownExport** - Markdown export endpoint
- **TestPathBasedRouting** - Path-based URL routing
- **TestProcessEndpoint** - Recipe processing endpoint
- **TestRedisRetry** - Redis connection retry logic

## Current Test Coverage

As of the last run:
- **Total Statements**: 403
- **Covered**: 234 (58%)
- **Missing**: 169

Most uncovered code is in:
- Recipe scraping functions (live HTTP requests)
- Error handling edge cases
- Template rendering paths

## Writing New Tests

### Test File Location

Place tests in the `tests/` directory with the naming pattern `test_*.py`.

### Using Fixtures

Common fixtures are defined in `tests/test_app.py`:

```python
def test_my_feature(client, sample_recipe):
    # client: Flask test client
    # sample_recipe: Mock recipe data
    response = client.get('/some/route')
    assert response.status_code == 200
```

Available fixtures:
- `client` - Flask test client
- `sample_recipe` - Sample recipe JSON data
- `sample_recipe_with_image_object` - Recipe with ImageObject format

### Mocking External Calls

Use `pytest-mock` or `unittest.mock` for mocking:

```python
from unittest.mock import patch

@patch('web.app.get_recipe_with_retry')
def test_something(mock_get_recipe, client):
    mock_get_recipe.return_value = {'name': 'Test Recipe'}
    # Test code here
```

## Troubleshooting

### Tests Fail with Import Errors

Ensure you're running from the project root and the virtual environment is activated:

```bash
cd /path/to/nyetcooking
python3 -m pytest
```

### Redis Connection Errors

Tests mock Redis connections, but if you see connection errors, ensure Redis isn't required for test runs or is properly mocked.

### Coverage Not Showing

Make sure `pytest-cov` is installed:

```bash
pip3 install pytest-cov
```

## Output for CI/CD

The test suite outputs to stdout with:
- Color-coded pass/fail indicators
- Detailed failure messages with tracebacks
- Coverage statistics
- XML coverage report for CI tools

Exit codes:
- `0` - All tests passed
- `1` - One or more tests failed

## Quick Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=web --cov-report=term-missing

# Run specific test
pytest tests/test_app.py::TestRecipeSlug::test_basic_slug

# Run and show print statements
pytest -s

# Run in parallel (if pytest-xdist installed)
pytest -n auto

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l
```
