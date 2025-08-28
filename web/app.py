from flask import Flask
import argparse
import json
import requests
import os
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_recipe(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    script_tag = soup.find("script", attrs={"type": "application/ld+json"})
    if script_tag is None:
        raise ValueError("Could not find recipe on page.")
    recipe_json = json.loads(script_tag.string)
    return recipe_jsongr.

@app.route('/')
async def index():
    """Index Page - Takes a URL to generate a page

    Keyword arguments:
    argument -- description
    Return: Renders the index page
    """
