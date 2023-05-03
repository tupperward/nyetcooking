from flask import Flask

app = Flask(__name__)

@app.route('/')
async def index():
    """Index Page - Takes a URL to generate a page 
    
    Keyword arguments:
    argument -- description
    Return: Renders the index page
    """
    