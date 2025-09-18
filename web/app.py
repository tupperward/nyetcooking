from flask import Flask, request, render_template, redirect
import json
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
def get_recipe(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    script_tag = soup.find("script", attrs={"type": "application/ld+json"})
    if script_tag is None:
        raise ValueError("Could not find recipe on page.")
    recipe_json = json.loads(script_tag.string)
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
        recipe_json = get_recipe(recipe_url)
        recipe_slug = get_recipe_slug(recipe_json)
        recipe_cache[recipe_slug] = recipe_json
        return redirect(f"/nyetcooking/{recipe_slug}")
    except Exception as e:
        return f"Error processing recipe: {str(e)}", 400

@app.route('/nyetcooking/<recipe_name>')
def recipe_card(recipe_name):
    recipe_json = recipe_cache.get(recipe_name)
    if not recipe_json:
        return "Recipe not found", 404
    return render_template('recipe_card.html', recipe=recipe_json)

@app.route('/nyetcooking/<recipe_name>/markdown')
def recipe_markdown(recipe_name):
    recipe_json = recipe_cache.get(recipe_name)
    if not recipe_json:
        return "Recipe not found", 404
    return recipe_to_markdown(recipe_json), 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == '__main__':
    app.run(debug=True)
