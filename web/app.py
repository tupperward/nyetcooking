from flask import Flask, request, render_template, redirect, url_for
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

recipe_cache = {}


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_recipe():
    recipe_url = request.form.get('recipe_url')
    if not recipe_url:
        return redirect(url_for('index'))

    try:
        recipe_json = get_recipe(recipe_url)
        recipe_slug = get_recipe_slug(recipe_json)
        recipe_cache[recipe_slug] = recipe_json
        return redirect(url_for('recipe_card', recipe_name=recipe_slug))
    except Exception as e:
        return f"Error processing recipe: {str(e)}", 400

@app.route('/<recipe_name>')
def recipe_card(recipe_name):
    recipe_json = recipe_cache.get(recipe_name)
    if not recipe_json:
        return "Recipe not found", 404
    return render_template('recipe_card.html', recipe=recipe_json)

if __name__ == '__main__':
    app.run(debug=True)
