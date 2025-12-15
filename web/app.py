from flask import Flask, request, render_template, redirect
import json
import requests
from bs4 import BeautifulSoup
import re
import logging
import sys
import traceback
import os
import time
from urllib.parse import quote, unquote

# URL normalization helpers
def normalize_url_for_path(url):
    """Convert full URL to clean path format (remove protocol and www)"""
    # Remove protocol
    clean = re.sub(r'^https?://', '', url)
    # Remove www.
    clean = re.sub(r'^www\.', '', clean)
    return clean

def denormalize_path_to_url(path):
    """Convert clean path back to full URL (add https://)"""
    # Try with https:// first
    url = f"https://{path}"
    return url

def denormalize_path_to_url_with_www(path):
    """Convert clean path to full URL with www. prefix"""
    # Some sites require www.
    if not path.startswith('www.'):
        return f"https://www.{path}"
    return f"https://{path}"

# Configure logging for k8s
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis setup with fallback to in-memory cache
def connect_to_redis_with_retry(max_retries=5, initial_delay=1):
    """
    Attempt to connect to Redis with exponential backoff.
    Returns tuple: (redis_client, success_bool)
    """
    try:
        import redis
    except ImportError:
        logger.warning("Redis module not available")
        return None, False

    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting to connect to Redis at {redis_host}:{redis_port} (attempt {attempt}/{max_retries})")
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            client.ping()
            logger.info(f"Redis connected successfully at {redis_host}:{redis_port}")
            return client, True
        except Exception as e:
            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(f"Redis connection attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.warning(f"Redis connection failed after {max_retries} attempts: {e}")
                logger.info("Falling back to in-memory cache")
                return None, False

redis_client, USE_REDIS = connect_to_redis_with_retry()

# Log startup information immediately
logger.info("=== Nyetcooking Flask App Initializing ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask app name: {app.name}")
logger.info(f"Cache backend: {'Redis' if USE_REDIS else 'In-memory'}")
logger.info("Available routes will be logged after app creation")

@app.before_request
def log_request():
    logger.info(f"Request: {request.method} {request.url}")
    if request.form:
        logger.info(f"Form data: {dict(request.form)}")

@app.after_request
def log_response(response):
    logger.info(f"Response: {response.status_code} for {request.url}")
    return response

# Cache helper functions
def cache_recipe(slug, recipe_data, original_url):
    """Store recipe in cache (Redis or in-memory)"""
    cache_data = {
        'recipe': recipe_data,
        'original_url': original_url
    }

    if USE_REDIS:
        try:
            redis_client.setex(f"recipe:{slug}", 2592000, json.dumps(cache_data))  # 30 day TTL (1 month)
            logger.info(f"Cached recipe '{slug}' in Redis")
        except Exception as e:
            logger.error(f"Redis cache failed, falling back to memory: {e}")
            recipe_cache[slug] = cache_data
    else:
        recipe_cache[slug] = cache_data
        logger.info(f"Cached recipe '{slug}' in memory")

def get_cached_recipe(slug):
    """Retrieve recipe from cache (Redis or in-memory)"""
    if USE_REDIS:
        try:
            cached = redis_client.get(f"recipe:{slug}")
            if cached:
                logger.info(f"Retrieved recipe '{slug}' from Redis")
                return json.loads(cached)
            else:
                logger.info(f"Recipe '{slug}' not found in Redis")
                return None
        except Exception as e:
            logger.error(f"Redis get failed, falling back to memory: {e}")
            return recipe_cache.get(slug)
    else:
        cached = recipe_cache.get(slug)
        if cached:
            logger.info(f"Retrieved recipe '{slug}' from memory")
        else:
            logger.info(f"Recipe '{slug}' not found in memory")
        return cached

def get_cache_keys():
    """Get all cache keys for debugging"""
    if USE_REDIS:
        try:
            keys = redis_client.keys("recipe:*")
            # Strip the "recipe:" prefix for consistency
            return [key.replace("recipe:", "") for key in keys]
        except Exception as e:
            logger.error(f"Redis keys failed: {e}")
            return list(recipe_cache.keys())
    else:
        return list(recipe_cache.keys())

def get_recipe_with_retry(url, max_retries=3, retry_delay=2):
    """Fetch recipe with retry logic"""
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching recipe (attempt {attempt}/{max_retries})")
            return get_recipe(url)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")

    # If we get here, all retries failed
    raise last_error

def get_recipe(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    logger.info(f"Fetching URL: {url}")
    try:
        res = requests.get(url, headers=headers, timeout=30)
        logger.info(f"Response status: {res.status_code}")

        if res.status_code != 200:
            logger.error(f"HTTP error {res.status_code} when fetching {url}")
            raise ValueError(f"HTTP {res.status_code}: Failed to fetch recipe page")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout when fetching {url}")
        raise ValueError("Request timed out when fetching recipe page")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error when fetching {url}: {e}")
        raise ValueError("Connection error when fetching recipe page")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error when fetching {url}: {e}")
        raise ValueError(f"Request error: {e}")

    soup = BeautifulSoup(res.content, "html.parser")
    script_tags = soup.find_all("script", attrs={"type": "application/ld+json"})

    logger.info(f"Found {len(script_tags)} JSON-LD script tags")

    if not script_tags:
        raise ValueError("Could not find any JSON-LD scripts on page.")

    recipe_json = None
    for i, script_tag in enumerate(script_tags):
        try:
            if not script_tag.string:
                logger.warning(f"Script tag {i} has no content")
                continue

            data = json.loads(script_tag.string.strip())
            logger.info(f"Script tag {i} parsed successfully, type: {type(data)}")

            # Handle @graph format (used by some sites like Minimalist Baker, Yoast SEO)
            if isinstance(data, dict) and '@graph' in data:
                logger.info(f"Found @graph with {len(data['@graph'])} items")
                items = data['@graph']
            # Handle both single objects and arrays
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            for j, item in enumerate(items):
                logger.info(f"Item {j} in script {i}: @type = {item.get('@type', 'unknown')}")

                # Look for Recipe type (case insensitive)
                item_type = item.get('@type', '')
                if isinstance(item_type, str) and item_type.lower() in ['recipe']:
                    recipe_json = item
                    logger.info(f"Found Recipe in script {i}, item {j}")
                    logger.info(f"Recipe name: {recipe_json.get('name', 'unnamed')}")
                    break
                elif isinstance(item_type, list) and any('recipe' in t.lower() for t in item_type):
                    recipe_json = item
                    logger.info(f"Found Recipe in script {i}, item {j} (list type)")
                    logger.info(f"Recipe name: {recipe_json.get('name', 'unnamed')}")
                    break

            if recipe_json:
                break

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse script tag {i}: {e}")
            continue

    if not recipe_json:
        raise ValueError("Could not find a Recipe object in any JSON-LD scripts.")

    # Validate that we have essential recipe data
    if not recipe_json.get('name'):
        logger.warning("Recipe has no name")
    if not recipe_json.get('recipeIngredient'):
        logger.warning("Recipe has no ingredients")
    if not recipe_json.get('recipeInstructions'):
        logger.warning("Recipe has no instructions")

    logger.info(f"Successfully extracted recipe: {recipe_json.get('name', 'unnamed')}")

    # Try to extract additional data from __NEXT_DATA__ (for NYT Cooking)
    try:
        next_data_script = soup.find("script", attrs={"id": "__NEXT_DATA__"})
        if next_data_script and next_data_script.string:
            next_data = json.loads(next_data_script.string.strip())
            logger.info("Found __NEXT_DATA__ block")

            # Navigate to recipe data in Next.js structure
            # Typical path: props.pageProps.recipe
            recipe_data = (
                next_data.get('props', {})
                .get('pageProps', {})
                .get('recipe', {})
            )

            if recipe_data:
                # Extract tips if available
                tips = recipe_data.get('tip_data') or recipe_data.get('tips')
                if tips:
                    recipe_json['tips'] = tips
                    logger.info(f"Extracted {len(tips)} tips from __NEXT_DATA__")

                # You can extract other fields here as needed
                # Example: notes, variations, etc.
                if recipe_data.get('notes'):
                    recipe_json['notes'] = recipe_data['notes']
                    logger.info("Extracted notes from __NEXT_DATA__")
            else:
                logger.info("No recipe data found in __NEXT_DATA__")
        else:
            logger.info("No __NEXT_DATA__ script found on page")
    except Exception as e:
        logger.warning(f"Failed to extract __NEXT_DATA__: {e}")
        # Don't fail the whole request if __NEXT_DATA__ extraction fails

    return recipe_json

def extract_nyt_recipe_id(url):
    """Extract recipe ID from NYT Cooking URLs"""
    # Pattern: https://cooking.nytimes.com/recipes/1234567890-recipe-name
    match = re.search(r'cooking\.nytimes\.com/recipes/(\d+)', url)
    return match.group(1) if match else None

def get_recipe_slug(recipe_json, original_url=None):
    """Generate slug from recipe name, optionally including NYT recipe ID"""
    name = recipe_json.get('name', 'recipe')
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = slug.lower()

    # If this is a NYT recipe, prepend the recipe ID for direct access
    if original_url:
        nyt_id = extract_nyt_recipe_id(original_url)
        if nyt_id:
            slug = f"{nyt_id}-{slug}"

    return slug

def recipe_to_markdown(recipe_json):
    md = f"# {recipe_json.get('name', 'Recipe')}\n\n"

    if recipe_json.get('author') and recipe_json['author'].get('name'):
        md += f"*By {recipe_json['author']['name']}*\n\n"

    if recipe_json.get('description'):
        md += f"{recipe_json['description']}\n\n"

    # Recipe meta information
    meta_items = []
    if recipe_json.get('totalTime'):
        meta_items.append(f"**Total Time:** {recipe_json['totalTime']}")
    if recipe_json.get('prepTime'):
        meta_items.append(f"**Prep Time:** {recipe_json['prepTime']}")
    if recipe_json.get('cookTime'):
        meta_items.append(f"**Cook Time:** {recipe_json['cookTime']}")
    if recipe_json.get('recipeYield'):
        meta_items.append(f"**Serves:** {recipe_json['recipeYield']}")

    if meta_items:
        md += " | ".join(meta_items) + "\n\n"

    # Ingredients
    md += "## Ingredients\n\n"
    for ingredient in recipe_json.get('recipeIngredient', []):
        md += f"- {ingredient}\n"
    md += "\n"

    # Instructions
    md += "## Instructions\n\n"
    for i, step in enumerate(recipe_json.get('recipeInstructions', []), 1):
        instruction = step.get('text', step) if isinstance(step, dict) else step
        md += f"{i}. {instruction}\n"
    md += "\n"

    # Tips
    if recipe_json.get('tips'):
        md += "## Tips\n\n"
        for tip in recipe_json['tips']:
            md += f"- {tip}\n"
        md += "\n"

    # Notes
    if recipe_json.get('notes'):
        md += "## Notes\n\n"
        md += f"{recipe_json['notes']}\n\n"

    # Rating
    if recipe_json.get('aggregateRating') and recipe_json['aggregateRating'].get('ratingValue'):
        rating = recipe_json['aggregateRating']['ratingValue']
        review_count = recipe_json['aggregateRating'].get('reviewCount', '')
        review_text = f" (based on {review_count} reviews)" if review_count else ""
        md += f"**Rating:** {rating}/5 stars{review_text}\n"

    return md

recipe_cache = {}


@app.route('/health')
def health():
    """Health check endpoint for k8s"""
    try:
        # Simple health check - verify we can import required modules
        import json, requests, bs4
        import datetime

        health_status = {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "cache_backend": "redis" if USE_REDIS else "in-memory"
        }

        # Check Redis connectivity if enabled
        if USE_REDIS and redis_client:
            try:
                redis_client.ping()
                health_status["redis"] = "connected"
            except Exception as redis_error:
                logger.warning(f"Redis health check failed: {redis_error}")
                health_status["redis"] = "disconnected"
                health_status["redis_error"] = str(redis_error)
                # Still return 200 since app falls back to in-memory cache

        return health_status, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_recipe():
    recipe_url = request.form.get('recipe_url')
    if not recipe_url:
        return redirect('/')

    try:
        logger.info(f"=== Processing recipe URL: {recipe_url} ===")

        # Normalize URL for clean path
        clean_path = normalize_url_for_path(recipe_url)
        logger.info(f"Normalized path: {clean_path}")

        # Fetch recipe (will be cached automatically in the route handler)
        recipe_json = get_recipe_with_retry(recipe_url)

        if not recipe_json:
            logger.error("get_recipe returned None or empty data")
            return "Error: Recipe data is empty. Check server logs for details.", 400

        logger.info(f"Recipe data keys: {list(recipe_json.keys()) if recipe_json else 'None'}")

        # Cache using clean path as key
        cache_recipe(clean_path, recipe_json, recipe_url)
        logger.info(f"Cached recipe at path: {clean_path}")

        # Redirect to new URL-based path
        logger.info(f"Redirecting to /{clean_path}")
        return redirect(f"/{clean_path}")
    except Exception as e:
        logger.error(f"ERROR in process_recipe: {str(e)}")
        logger.error(f"ERROR type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Error processing recipe: {str(e)}", 400

@app.route('/<int:recipe_id>')
@app.route('/recipes/<int:recipe_id>')
@app.route('/recipes/<int:recipe_id>-<recipe_name>')
def nyt_recipe_auto_fetch(recipe_id, recipe_name=None):
    """Auto-fetch NYT recipes by ID if not cached"""
    # Try to find the recipe in cache first - check both formats
    slug_with_id = f"{recipe_id}-{recipe_name}" if recipe_name else None
    cached_data = None

    if slug_with_id:
        cached_data = get_cached_recipe(slug_with_id)

    if not cached_data:
        # Try to find any cached recipe with this ID
        cache_keys = get_cache_keys()
        for key in cache_keys:
            if key.startswith(f"{recipe_id}-"):
                cached_data = get_cached_recipe(key)
                if cached_data:
                    logger.info(f"Found cached recipe with ID {recipe_id} under key: {key}")
                    break

    if not cached_data:
        # Auto-fetch from NYT
        nyt_url = f"https://cooking.nytimes.com/recipes/{recipe_id}"
        logger.info(f"Auto-fetching NYT recipe {recipe_id} from: {nyt_url}")

        try:
            recipe_json = get_recipe_with_retry(nyt_url)
            if recipe_json:
                # Generate proper slug and cache
                recipe_slug = get_recipe_slug(recipe_json, nyt_url)
                cache_recipe(recipe_slug, recipe_json, nyt_url)
                logger.info(f"Auto-fetched and cached recipe as: {recipe_slug}")

                # Redirect to the proper slug URL
                return redirect(f"/{recipe_slug}")
            else:
                logger.error(f"Failed to fetch recipe {recipe_id}")
                return "Recipe not found at NYT Cooking", 404
        except Exception as e:
            logger.error(f"Error auto-fetching recipe {recipe_id}: {e}")
            return f"Error fetching recipe: {e}", 400
    else:
        # Recipe found in cache - extract and render
        if isinstance(cached_data, dict) and 'recipe' in cached_data:
            recipe_json = cached_data['recipe']
        else:
            recipe_json = cached_data

        logger.info(f"Rendering auto-fetched recipe {recipe_id}")
        return render_template('recipe_card.html', recipe=recipe_json)

@app.route('/<path:recipe_path>')
def recipe_card(recipe_path):
    logger.info(f"=== Recipe card requested for path: {recipe_path} ===")

    # Check if it's the markdown export endpoint
    if recipe_path.endswith('/markdown'):
        # Strip /markdown and handle separately
        actual_path = recipe_path[:-9]  # Remove '/markdown'
        return recipe_markdown(actual_path)

    # Try cache first using the clean path
    cached_data = get_cached_recipe(recipe_path)

    if cached_data and isinstance(cached_data, dict) and 'recipe' in cached_data:
        # Found in cache
        recipe_json = cached_data['recipe']
        original_url = cached_data['original_url']
        logger.info(f"Recipe found in cache with URL: {original_url}")
    elif cached_data:
        # Old format (just recipe data)
        recipe_json = cached_data
        logger.info(f"Recipe found in cache (old format)")
    else:
        # Not in cache - try to fetch from URL in path
        logger.warning(f"Recipe '{recipe_path}' not found in cache")

        # Try to reconstruct URL from path
        urls_to_try = [
            denormalize_path_to_url(recipe_path),  # Try https://
            denormalize_path_to_url_with_www(recipe_path),  # Try https://www.
        ]

        recipe_json = None
        successful_url = None

        for attempt, url in enumerate(urls_to_try, 1):
            logger.info(f"Attempt {attempt}/{len(urls_to_try)}: Trying to fetch from {url}")
            try:
                recipe_json = get_recipe_with_retry(url, max_retries=2)
                if recipe_json:
                    logger.info(f"Successfully fetched from {url}")
                    successful_url = url
                    # Cache it using the clean path
                    cache_recipe(recipe_path, recipe_json, url)
                    break
            except Exception as e:
                logger.warning(f"Failed to fetch from {url}: {e}")
                continue

        if not recipe_json:
            logger.error(f"Failed to fetch recipe from any URL variant of {recipe_path}")
            return render_template('404.html', recipe_name=recipe_path), 404

    logger.info(f"Recipe ready for rendering: {recipe_json.get('name', 'NO NAME')}")

    try:
        return render_template('recipe_card.html', recipe=recipe_json)
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Template rendering error: {e}", 500

def recipe_markdown(recipe_path):
    """Handle markdown export - called from recipe_card route"""
    cached_data = get_cached_recipe(recipe_path)

    if cached_data and isinstance(cached_data, dict) and 'recipe' in cached_data:
        # Found in cache
        recipe_json = cached_data['recipe']
    elif cached_data:
        # Old format
        recipe_json = cached_data
    else:
        # Not in cache - try to fetch
        logger.warning(f"Recipe '{recipe_path}' not found in cache for markdown export")

        urls_to_try = [
            denormalize_path_to_url(recipe_path),
            denormalize_path_to_url_with_www(recipe_path),
        ]

        recipe_json = None
        for url in urls_to_try:
            try:
                logger.info(f"Markdown export: Trying to fetch from {url}")
                recipe_json = get_recipe_with_retry(url, max_retries=2)
                if recipe_json:
                    cache_recipe(recipe_path, recipe_json, url)
                    break
            except Exception as e:
                logger.warning(f"Markdown export fetch failed: {e}")
                continue

        if not recipe_json:
            return "Recipe not found", 404

    return recipe_to_markdown(recipe_json), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    try:
        logger.info("Starting Flask development server...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
else:
    # This runs when imported by Gunicorn
    logger.info("Flask app imported by WSGI server (Gunicorn)")
    logger.info(f"App routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
