import argparse
import json
import jinja2
import requests
import os
from bs4 import BeautifulSoup

def get_recipe(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    script_tag = soup.find("script", attrs={"type": "application/ld+json"})
    if script_tag is None:
        raise ValueError("Could not find recipe on page.")
    recipe_json = json.loads(script_tag.string)
    return recipe_json

def render_recipe_card(recipe_json, output_path):
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("recipe_card.html")
    html_output = template.render(recipe=recipe_json)

    with open(output_path, "w") as f:
        f.write(html_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help='URL of the webpage to parse.')
    parser.add_argument('--path', type=str, help='Path to output the recipe to.')
    args = parser.parse_args()

    # Get the filename from the recipe title
    res = requests.get(args.url)
    soup = BeautifulSoup(res.content, "html.parser")
    title = soup.find("title").text.strip().replace(" ", "-").replace("---","-").lower()
    filename = title

    recipe_json = get_recipe(args.url)
    path = args.path
    os.makedirs(args.path, exist_ok=True)
    output = os.path.join(args.path, f"{filename}-recipe-card.html")
    render_recipe_card(recipe_json, output)
    
    