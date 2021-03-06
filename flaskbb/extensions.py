# -*- coding: utf-8 -*-
"""
    flaskbb.extensions
    ~~~~~~~~~~~~~~~~~~~~

    The extensions that are used by FlaskBB.

    :copyright: (c) 2013 by the FlaskBB Team.
    :license: BSD, see LICENSE for more details.
"""
from redis import Redis
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.mail import Mail
from flask.ext.cache import Cache
#from flask.ext.debugtoolbar import DebugToolbarExtension

# Database
db = SQLAlchemy()

# Login
login_manager = LoginManager()

# Mail
mail = Mail()

# Caching
cache = Cache()

# Redis
redis = Redis()

# Debugtoolbar
#toolbar = DebugToolbarExtension()
