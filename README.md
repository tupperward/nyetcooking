# NYetcooking

A Flask web application that scrapes recipe data from web pages using structured JSON-LD data and generates printable recipe cards. Extract recipe information from URLs and display it in a clean, print-optimized format with markdown export capabilities.

## Features

- Scrape recipes from any website with JSON-LD structured data
- Clean, print-optimized recipe card display
- Export recipes to markdown format
- Redis caching for improved performance
- In-memory fallback when Redis is unavailable

## Quick Start

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python web/app.py

# Visit http://localhost:5000/nyetcooking
```

### Production (Docker)

```bash
# Build the image
docker build -t tupperward/nyetcooking .

# Run the container
docker run -p 5000:5000 tupperward/nyetcooking

# Visit http://localhost:5000/nyetcooking
```

### Production (Kubernetes)

```bash
# Deploy Redis and the application
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/deployment.yaml
```

## Testing

### Run Tests

```bash
# Basic test run
pytest

# With coverage report
pytest --cov=web --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=web --cov-report=html
open htmlcov/index.html
```

### Test Configuration

Test configuration is in `tests/pytest.ini`:
- 36 comprehensive unit and integration tests
- Tests for Flask routes, recipe processing, caching, and Redis integration
- Coverage reporting with pytest-cov

### Run Specific Tests

```bash
# Run a specific test file
pytest tests/test_app.py

# Run a specific test class
pytest tests/test_app.py::TestRecipeSlug

# Run a specific test
pytest tests/test_app.py::TestRecipeSlug::test_basic_slug
```

## Architecture

### Core Structure

- **`web/app.py`** - Main Flask application with routes and business logic
- **`web/templates/`** - Jinja2 HTML templates
  - `index.html` - Landing page with URL input form
  - `recipe_card.html` - Recipe display page with print styling
- **`requirements.txt`** - Python dependencies
- **`Dockerfile`** - Container configuration
- **`k8s/`** - Kubernetes deployment manifests

### Application Flow

1. User submits recipe URL via form at `/nyetcooking`
2. `/nyetcooking/process` endpoint scrapes URL for JSON-LD structured data
3. Recipe data is cached (Redis or in-memory) with slug-based keys
4. User redirected to `/nyetcooking/<recipe-slug>` for formatted display
5. Optional markdown export at `/nyetcooking/<recipe-slug>/markdown`

### Key Functions

- `get_recipe(url)` - Scrapes and parses JSON-LD recipe data from URLs
- `get_recipe_slug(recipe_json)` - Generates URL-safe slugs from recipe names
- `recipe_to_markdown(recipe_json)` - Converts recipe data to markdown format

### Data Persistence

- Redis caching (when available) via `REDIS_HOST` and `REDIS_PORT` env vars
- In-memory fallback dictionary when Redis is unavailable
- Recipe data follows JSON-LD Recipe schema format

## Environment Variables

```bash
REDIS_HOST=redis-service  # Redis hostname (optional)
REDIS_PORT=6379          # Redis port (optional)
```

## Deployment

### Using the Build Script

```bash
# Build, push, and deploy to Kubernetes
./rebuild.sh
```

The script performs:
1. Docker build with tag `tupperward/nyetcooking`
2. Push to Docker registry
3. Kubernetes rollout restart in namespace `blog`

## Development Notes

- The app expects recipe pages to contain valid JSON-LD structured data
- All routes are prefixed with `/nyetcooking` for subdirectory deployment
- Recipe images support multiple JSON-LD formats (string, array, object with url/contentUrl)
- Print-optimized styles with `@media print` rules
- External CSS framework from worstwizard.online

## Project Structure

```
nyetcooking/
├── web/
│   ├── app.py           # Main Flask application
│   └── templates/       # Jinja2 templates
├── tests/
│   ├── test_app.py      # Test suite
│   └── pytest.ini       # Test configuration
├── k8s/                 # Kubernetes manifests
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container definition
├── rebuild.sh          # Build and deploy script
└── CLAUDE.md           # AI assistant guidance
```

## License

This project is for educational and personal use.
