from flask_bootstrap import Bootstrap
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bikers.sqlite3'

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)

from shop import models, routes
