# -*- coding: utf-8 -*-
"""
    flaskbb.utils
    ~~~~~~~~~~~~~~~~~~~~

    A few utils that are used by flaskbb

    :copyright: (c) 2013 by the FlaskBB Team.
    :license: BSD, see LICENSE for more details.
"""
import random
import time
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import types
from sqlalchemy.ext.mutable import Mutable
from wtforms.widgets.core import Select, HTMLString, html_params
from postmarkup import render_bbcode

from flaskbb.extensions import redis


def mark_online(user_id, guest=False):
    """
    Source: http://flask.pocoo.org/snippets/71/
    """
    now = int(time.time())
    expires = now + (current_app.config['ONLINE_LAST_MINUTES'] * 60) + 10
    if guest:
        all_users_key = 'online-guests/%d' % (now // 60)
        user_key = 'guest-activity/%s' % user_id
    else:
        all_users_key = 'online-users/%d' % (now // 60)
        user_key = 'user-activity/%s' % user_id
    p = redis.pipeline()
    p.sadd(all_users_key, user_id)
    p.set(user_key, now)
    p.expireat(all_users_key, expires)
    p.expireat(user_key, expires)
    p.execute()


def get_last_user_activity(user_id, guest=False):
    if guest:
        last_active = redis.get('guest-activity/%s' % user_id)
    else:
        last_active = redis.get('user-activity/%s' % user_id)

    if last_active is None:
        return None
    return datetime.utcfromtimestamp(int(last_active))


def get_online_users(guest=False):
    current = int(time.time()) // 60
    minutes = xrange(current_app.config['ONLINE_LAST_MINUTES'])
    if guest:
        return redis.sunion(['online-guests/%d' % (current - x)
                             for x in minutes])
    return redis.sunion(['online-users/%d' % (current - x)
                         for x in minutes])


def check_perm(user, perm, forum, post_user_id=None):
    """
    Checks if the `user` has a specified `perm` in the `forum`
    If post_user_id is provided, it will also check if the user
    has created the post
    """
    if can_moderate(user, forum):
        return True
    if post_user_id and user.is_authenticated():
        return user.permissions[perm] and user.id == post_user_id
    return user.permissions[perm]


def can_moderate(user, forum):
    """
    Checks if a user can moderate a forum
    He needs to be super moderator or a moderator of the
    specified `forum`
    """
    if user.permissions['mod'] and user.id in forum.moderators:
        return True
    return user.permissions['super_mod'] or user.permissions['admin']


def perm_edit_post(user, post_user_id, forum):
    """
    Check if the post can be edited by the user
    """
    return check_perm(user=user, perm='editpost', forum=forum,
                      post_user_id=post_user_id)


def perm_delete_post(user, post_user_id, forum):
    """
    Check if the post can be deleted by the user
    """
    return check_perm(user=user, perm='deletepost', forum=forum,
                      post_user_id=post_user_id)


def perm_delete_topic(user, post_user_id, forum):
    """
    Check if the topic can be deleted by the user
    """
    return check_perm(user=user, perm='deletetopic', forum=forum,
                      post_user_id=post_user_id)


def perm_post_reply(user, forum):
    """
    Check if the user is allowed to post in the forum
    """
    return check_perm(user=user, perm='postreply', forum=forum)


def perm_post_topic(user, forum):
    """
    Check if the user is allowed to create a new topic in the forum
    """
    return check_perm(user=user, perm='posttopic', forum=forum)


def crop_title(title):
    """
    Crops the title to a specified length
    """
    length = current_app.config['TITLE_LENGTH']
    if len(title) > length:
        return title[:length] + "..."
    return title


def render_markup(text):
    return render_bbcode(text)


def is_online(user):
    return user.lastseen >= time_diff()


def time_diff():
    now = datetime.utcnow()
    diff = now - timedelta(minutes=current_app.config['ONLINE_LAST_MINUTES'])
    return diff


def format_date(value, format='%Y-%m-%d'):
    """
    Returns a formatted time string
    """
    return value.strftime(format)


def time_since(value):
    return time_delta_format(value)


def time_delta_format(dt, default=None):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    Ref: https://bitbucket.org/danjac/newsmeme/src/a281babb9ca3/newsmeme/
    """

    if default is None:
        default = 'just now'

    now = datetime.utcnow()
    diff = now - dt

    periods = (
        (diff.days / 365, 'year', 'years'),
        (diff.days / 30, 'month', 'months'),
        (diff.days / 7, 'week', 'weeks'),
        (diff.days, 'day', 'days'),
        (diff.seconds / 3600, 'hour', 'hours'),
        (diff.seconds / 60, 'minute', 'minutes'),
        (diff.seconds, 'second', 'seconds'),
    )

    for period, singular, plural in periods:

        if not period:
            continue

        if period == 1:
            return u'%d %s ago' % (period, singular)
        else:
            return u'%d %s ago' % (period, plural)

    return default


class DenormalizedText(Mutable, types.TypeDecorator):
    """
    Stores denormalized primary keys that can be
    accessed as a set.

    :param coerce: coercion function that ensures correct
                   type is returned

    :param separator: separator character

    Source: https://github.com/imwilsonxu/fbone/blob/master/fbone/user/models.py#L13-L45
    """

    impl = types.Text

    def __init__(self, coerce=int, separator=" ", **kwargs):

        self.coerce = coerce
        self.separator = separator

        super(DenormalizedText, self).__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            items = [str(item).strip() for item in value]
            value = self.separator.join(item for item in items if item)
        return value

    def process_result_value(self, value, dialect):
        if not value:
            return set()
        return set(self.coerce(item) for item in value.split(self.separator))

    def copy_value(self, value):
        return set(value)


class SelectDateWidget(object):
    """
    Renders a DateTime field with 3 selects.
    For more information see: http://stackoverflow.com/a/14664504
    """
    FORMAT_CHOICES = {
        '%d': [(x, str(x)) for x in range(1, 32)],
        '%m': [(x, str(x)) for x in range(1, 13)]
    }

    FORMAT_CLASSES = {
        '%d': 'select_date_day',
        '%m': 'select_date_month',
        '%Y': 'select_date_year'
    }

    def __init__(self, years=range(1930, datetime.utcnow().year+1)):
        super(SelectDateWidget, self).__init__()
        self.FORMAT_CHOICES['%Y'] = [(x, str(x)) for x in years]

    def __call__(self, field, **kwargs):
        field_id = kwargs.pop('id', field.id)
        html = []
        allowed_format = ['%d', '%m', '%Y']

        for format in field.format.split():
            if (format in allowed_format):
                choices = self.FORMAT_CHOICES[format]
                id_suffix = format.replace('%', '-')
                id_current = field_id + id_suffix

                kwargs['class'] = self.FORMAT_CLASSES[format]
                try:
                    del kwargs['placeholder']
                except:
                    pass

                html.append('<select %s>' % html_params(name=field.name,
                                                        id=id_current,
                                                        **kwargs))

                if field.data:
                    current_value = int(field.data.strftime(format))
                else:
                    current_value = None

                for value, label in choices:
                    selected = (value == current_value)
                    html.append(Select.render_option(value, label, selected))
                html.append('</select>')
            else:
                html.append(format)
                html.append(
                    """<input type="hidden" value="{}" {}></input>""".format(
                        html_params(name=field.name, id=id_current, **kwargs)))

            html.append(' ')

        return HTMLString(''.join(html))
