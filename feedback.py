from collections import namedtuple

from flask import Flask, render_template
from jinja2 import StrictUndefined
import click

app = Flask(__name__)

Category = namedtuple('Category', 'slug icon color question')

CATEGORIES = (
    Category('like', 'heart', '#D9534F', 'Jak se ti lekce líbila?'),
    Category('topic', 'star', '#F0AD4E', 'Jak přínosné bylo téma?'),
    Category('learn', 'rocket', '#0275D8', 'Kolik nového ses naučil/a?'),
    #Category('mat', 'thumbs-o-up', '#5CB85C', 'Jak dobré byly materiály?'),
)

Lesson = namedtuple('Lesson', 'slug title')

LESSONS = (
    Lesson('flask-click', 'Flask & Click'),
    Lesson('requests', 'Requests'),
    Lesson('moduly', 'Moduly & PyPI'),
    Lesson('testovani', 'Testování'),
    Lesson('dokumentace', 'Dokumentace'),
    Lesson('pandas', 'Pandas'),
    Lesson('numpy', 'NumPy'),
    Lesson('cython', 'Cython'),
    Lesson('pyqt', 'PyQt'),
    Lesson('async', 'Asyncio'),
    Lesson('magie', 'Magie'),
    Lesson('micropython', 'MicroPython'),
    Lesson('semestralka', 'Semestrálka'),
)

def rating_selectors(r):
    return [r * i for i in range(10)]

@app.route('/')
def index():
    return render_template(
        'index.html',
        categories=CATEGORIES,
        lessons=LESSONS,
        rating_selectors=rating_selectors,
    )

@click.group()
def cli():
    pass

@cli.command()
@click.option('--port', type=int, help='Port to listen on.')
@click.option('--debug/--no-debug', default=True,
              help='Run in insecure debug mode.')
def serve(port, debug):
    app.run(port=port, debug=debug)


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.undefined = StrictUndefined
    cli()
