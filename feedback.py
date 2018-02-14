from collections import namedtuple
import base64
import os
import urllib.parse
import csv
import io
import hashlib

from flask import Flask, render_template, request, abort, redirect, url_for
from flask import Response
from jinja2 import StrictUndefined
from flask_sqlalchemy import SQLAlchemy
import click

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = database = SQLAlchemy(app)

class Category(db.Model):
    order = db.Column(db.Integer)
    slug = db.Column(db.Unicode, primary_key=True)
    icon = db.Column(db.Unicode, unique=True)
    color = db.Column(db.Unicode)
    question = db.Column(db.Unicode)

    __mapper_args__ = {"order_by": order}

class Lesson(db.Model):
    order = db.Column(db.Integer)
    slug = db.Column(db.Unicode, primary_key=True)
    title = db.Column(db.Unicode)

    __mapper_args__ = {"order_by": order}

class LessonFeedback(db.Model):
    token = db.Column(db.Unicode, primary_key=True)
    category_slug = db.Column(db.Unicode, db.ForeignKey(Category.slug), primary_key=True)
    lesson_slug = db.Column(db.Unicode, db.ForeignKey(Lesson.slug), primary_key=True)
    mark = db.Column(db.Unicode, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True),
                          server_default=db.func.now())

    @property
    def slug(self):
        return 'feedback-{}-{}'.format(self.category_slug, self.lesson_slug)

class SimpleFeedback(db.Model):
    token = db.Column(db.Unicode, primary_key=True)
    question_slug = db.Column(db.Unicode, primary_key=True)
    answer = db.Column(db.Unicode, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True),
                          server_default=db.func.now())


SIMPLE_QUESTIONS = 'mark', 'missing', 'future', 'message', 'secret'
PRIVATE_QUESTIONS = ['secret']

assert set(PRIVATE_QUESTIONS) < set(SIMPLE_QUESTIONS)


def add_order(*items):
    for i, item in enumerate(items):
        item.order = i
    return items


def rating_selectors(r):
    """Helper for a CSS trick to highlight icons based on slected radio button
    """
    return [r * i for i in range(10)]


@app.route('/')
@app.route('/form/')
@app.route('/form/<token>/', methods=['GET', 'POST'])
def form(token=None):
    show_thankyou = bool(token)
    if token is None:
        # Generate a random token
        # (in Python 3.6+ this would be `secrets.token_urlsafe`)
        bencoded = base64.urlsafe_b64encode(os.urandom(8))
        token = bencoded.rstrip(b'=').decode('ascii')
    if not (5 < len(token) < 20):
        abort(404)

    categories = list(db.session.query(Category))
    lessons = list(db.session.query(Lesson))

    if request.method == 'POST':
        print(request.form)
        _prefetch = (list(db.session.query(LessonFeedback).filter_by(token=token)),
                     list(db.session.query(SimpleFeedback).filter_by(token=token)))
        for cat in categories:
            for lesson in lessons:
                feedback = LessonFeedback(
                    token=token,
                    category_slug=cat.slug,
                    lesson_slug=lesson.slug,
                )
                mark = request.form.get(feedback.slug)
                if mark == 'None':
                    mark = None
                feedback.mark = mark
                db.session.merge(feedback)
        for question in SIMPLE_QUESTIONS:
            answer = request.form.get(question)
            db.session.merge(SimpleFeedback(
                token=token,
                question_slug=question,
                answer=answer,
            ))
        db.session.commit()
        return redirect(url_for('form', token=token))

    lesson_feedback = {
        f.slug: f.mark
        for f in db.session.query(LessonFeedback).filter_by(token=token)}
    simple_feedback = {
        f.question_slug: f.answer
        for f in db.session.query(SimpleFeedback).filter_by(token=token)}

    simple_feedback.setdefault('mark', '?')

    return render_template(
        'index.html',
        categories=categories,
        lessons=lessons,
        lesson_feedback=lesson_feedback,
        simple_feedback=simple_feedback,
        rating_selectors=rating_selectors,
        token=token,
        show_thankyou=show_thankyou,
    )

@app.route('/results.csv')
def results():
    result_file = io.StringIO()
    with result_file as f:
        writer = csv.DictWriter(f, ['user_hash', 'lesson', 'category', 'answer'])
        writer.writeheader()
        for feedback in LessonFeedback.query.order_by(db.func.random()):
            writer.writerow({
                'user_hash': hashlib.sha256(feedback.token.encode('utf-8')).hexdigest(),
                'category': feedback.category_slug,
                'lesson': feedback.lesson_slug,
                'answer': feedback.mark,
            })
        for feedback in SimpleFeedback.query.order_by(db.func.random()):
            if feedback.question_slug not in PRIVATE_QUESTIONS:
                writer.writerow({
                    'user_hash': hashlib.sha256(feedback.token.encode('utf-8')).hexdigest(),
                    'category': feedback.question_slug,
                    'answer': feedback.answer,
                })
        return Response(response=result_file.getvalue(),
                        headers={"Content-Disposition": 'inline; filename="results.csv"'},
                        mimetype='text/csv')


INITIAL_CATEGORIES = add_order(
    Category(slug='like', icon='heart', color='#D9534F', question='Jak se ti lekce líbila?'),
    Category(slug='topic', icon='star', color='#F0AD4E', question='Jak přínosné bylo téma?'),
    Category(slug='learn', icon='rocket', color='#0275D8', question='Kolik nového ses naučil/a?'),
    #Category(slug='mat', 'thumbs-o-up', '#5CB85C', 'Jak dobré byly materiály?'),
)

INITIAL_LESSONS = add_order(
    Lesson(slug='requests-click', title='Requests & Click'),
    Lesson(slug='flask', title='Flask'),
    Lesson(slug='pandas', title='Pandas'),
    Lesson(slug='distribution', title='Moduly & PyPI'),
    Lesson(slug='numpy', title='NumPy'),
    Lesson(slug='testing', title='Testování'),
    Lesson(slug='cython', title='Cython'),
    Lesson(slug='docs', title='Dokumentace & Sphinx'),
    Lesson(slug='pyqt', title='PyQt'),
    Lesson(slug='micropython', title='MicroPython'),
    Lesson(slug='geopython', title='GeoPython'),
    Lesson(slug='async', title='AsyncIO'),
    Lesson(slug='magic', title='Magie'),
    Lesson(slug='semestralka', title='Semestrálka'),
)


@click.group()
def cli():
    pass

@cli.command()
@click.option('--port', type=int, help='Port to listen on.')
@click.option('--debug/--no-debug', default=True,
              help='Run in insecure debug mode.')
@click.option('--db', default='form.db',
              help='Database to use. May be a file (created & filled with '
                   'initial data if not present), or a SQLAlchemy URL.')
def serve(port, debug, db):
    if debug:
        app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.undefined = StrictUndefined

    url = urllib.parse.urlparse(db)
    print(url)
    if url.scheme in ('', 'file'):
        if url.scheme == 'file':
            db = url.path
        filename = os.path.abspath(db)
        @app.before_first_request
        def setup_db():
            if not os.path.exists(filename):
                print('Filling initial data in', filename)
                database.create_all()
                for item in INITIAL_CATEGORIES + INITIAL_LESSONS:
                    database.session.add(item)
                database.session.commit()
        db = 'sqlite:///' + filename
    app.config['SQLALCHEMY_DATABASE_URI'] = db
    app.config['SQLALCHEMY_ECHO'] = True

    app.run(port=port, debug=debug)


if __name__ == '__main__':
    cli()
