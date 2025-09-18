from flask import Flask, request, render_template, redirect
import json
import requests
from bs4 import BeautifulSoup
import re
import logging
import sys
import traceback

# Configure logging for k8s
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Log startup information immediately
logger.info("=== NYet Cooking Flask App Initializing ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Flask app name: {app.name}")
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

            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]

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
    return recipe_json

def get_recipe_slug(recipe_json):
    name = recipe_json.get('name', 'recipe')
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = slug.lower()
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
        return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}, 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 500

@app.route('/nyetcooking')
@app.route('/nyetcooking/')
def index():
    return render_template('index.html')

@app.route('/nyetcooking/process', methods=['POST'])
def process_recipe():
    recipe_url = request.form.get('recipe_url')
    if not recipe_url:
        return redirect('/nyetcooking')

    try:
        logger.info(f"=== Processing recipe URL: {recipe_url} ===")
        recipe_json = get_recipe(recipe_url)

        if not recipe_json:
            logger.error("get_recipe returned None or empty data")
            return "Error: Recipe data is empty. Check server logs for details.", 400

        logger.info(f"Recipe data keys: {list(recipe_json.keys()) if recipe_json else 'None'}")

        recipe_slug = get_recipe_slug(recipe_json)
        logger.info(f"Generated slug: {recipe_slug}")

        # Store both recipe data AND original URL for fallback
        recipe_cache[recipe_slug] = {
            'recipe': recipe_json,
            'original_url': recipe_url
        }
        logger.info(f"Cached recipe with slug: {recipe_slug}")
        logger.info(f"Cache now contains: {list(recipe_cache.keys())}")

        # Verify the recipe was actually cached
        cached_recipe = recipe_cache.get(recipe_slug)
        if cached_recipe:
            logger.info(f"Cache verification successful for '{recipe_slug}'")
        else:
            logger.error(f"Cache verification FAILED for '{recipe_slug}'!")

        logger.info(f"Redirecting to /nyetcooking/{recipe_slug}")
        return redirect(f"/nyetcooking/{recipe_slug}")
    except Exception as e:
        logger.error(f"ERROR in process_recipe: {str(e)}")
        logger.error(f"ERROR type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Error processing recipe: {str(e)}", 400

@app.route('/nyetcooking/<recipe_name>')
def recipe_card(recipe_name):
    logger.info(f"=== Recipe card requested for: {recipe_name} ===")
    logger.info(f"Current cache keys: {list(recipe_cache.keys())}")
    logger.info(f"Cache size: {len(recipe_cache)}")

    cached_data = recipe_cache.get(recipe_name)

    if cached_data and isinstance(cached_data, dict) and 'recipe' in cached_data:
        # New format with URL stored
        recipe_json = cached_data['recipe']
        original_url = cached_data['original_url']
        logger.info(f"Recipe '{recipe_name}' found in cache with URL: {original_url}")
    elif cached_data:
        # Old format (just recipe data) - still works
        recipe_json = cached_data
        original_url = None
        logger.info(f"Recipe '{recipe_name}' found in cache (old format)")
    else:
        # Not in cache - no fallback possible without stored URL
        logger.warning(f"Recipe '{recipe_name}' not found in cache (likely multi-worker issue)")
        logger.info(f"Available recipes: {list(recipe_cache.keys())}")

        # Add some debug info about similar keys
        similar_keys = [k for k in recipe_cache.keys() if recipe_name in k or k in recipe_name]
        if similar_keys:
            logger.info(f"Similar keys found: {similar_keys}")
            # Try to get URL from similar key
            for similar_key in similar_keys:
                similar_data = recipe_cache.get(similar_key)
                if isinstance(similar_data, dict) and 'original_url' in similar_data:
                    original_url = similar_data['original_url']
                    logger.info(f"Found original URL from similar key '{similar_key}': {original_url}")

                    try:
                        logger.info(f"Attempting fallback re-fetch from: {original_url}")
                        recipe_json = get_recipe(original_url)
                        if recipe_json:
                            # Cache it for this worker (new format)
                            recipe_cache[recipe_name] = {
                                'recipe': recipe_json,
                                'original_url': original_url
                            }
                            logger.info(f"Fallback successful! Re-cached {recipe_name}")
                            break
                        else:
                            logger.error("Fallback failed - no recipe data")
                    except Exception as e:
                        logger.error(f"Fallback failed with error: {e}")
            else:
                # No successful fallback found
                logger.error("No fallback possible - recipe not found")
                return "Recipe not found", 404
        else:
            logger.error("Recipe not found and no fallback available")
            return "Recipe not found", 404

    logger.info(f"Recipe '{recipe_name}' ready for rendering")
    logger.info(f"Recipe has name: {recipe_json.get('name', 'NO NAME')}")

    try:
        return render_template('recipe_card.html', recipe=recipe_json)
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Template rendering error: {e}", 500

@app.route('/nyetcooking/<recipe_name>/markdown')
def recipe_markdown(recipe_name):
    cached_data = recipe_cache.get(recipe_name)

    if cached_data and isinstance(cached_data, dict) and 'recipe' in cached_data:
        # New format with URL stored
        recipe_json = cached_data['recipe']
    elif cached_data:
        # Old format (just recipe data) - still works
        recipe_json = cached_data
    else:
        logger.warning(f"Recipe '{recipe_name}' not found in cache for markdown export")

        # Try to find it in another worker's cache and use its URL
        similar_keys = [k for k in recipe_cache.keys() if recipe_name in k or k in recipe_name]
        if similar_keys:
            for similar_key in similar_keys:
                similar_data = recipe_cache.get(similar_key)
                if isinstance(similar_data, dict) and 'original_url' in similar_data:
                    original_url = similar_data['original_url']
                    try:
                        logger.info(f"Markdown fallback re-fetch from: {original_url}")
                        recipe_json = get_recipe(original_url)
                        if recipe_json:
                            # Cache it for this worker (new format)
                            recipe_cache[recipe_name] = {
                                'recipe': recipe_json,
                                'original_url': original_url
                            }
                            logger.info(f"Markdown fallback successful for {recipe_name}")
                            break
                    except Exception as e:
                        logger.error(f"Markdown fallback failed: {e}")
            else:
                return "Recipe not found", 404
        else:
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
