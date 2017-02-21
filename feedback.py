from flask import Flask, render_template
import click

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


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
    cli()
