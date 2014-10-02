#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import functools
import transaction
import predictionio

from zope import component

from contentratings.interfaces import IObjectRatedEvent

from nti.dataserver.users import User
from nti.dataserver.interfaces import IRatable
from nti.dataserver.rating import IObjectUnratedEvent
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.externalization.externalization import to_external_ntiid_oid

from nti.ntiids.ntiids import find_object_with_ntiid

from . import get_current_username
from . import get_predictionio_app

from .interfaces import ITypes
from .interfaces import IProperties

LIKE_API = "like"
DISLIKE_API = "dislike"
LIKE_CAT_NAME = "likes"
RATE_CATE_NAME = 'rating'

def _process_like_pio(app, username, oid, api):
	client = predictionio.Client(app.AppKey, apiurl=app.URL)
	try:
		user = User.get_user(username)
		obj = find_object_with_ntiid(oid)
		if obj is not None and user is not None:
			client.create_user(username, params=IProperties(user))
			client.create_item(oid, ITypes(obj), IProperties(obj))
			client.identify(username)
			client.record_action_on_item(api, oid)
			logger.debug("%s recorded action '%s' for %s", username, api, oid)
	finally:
		client.close()

def record_like(app, username, oid):
	_process_like_pio(app, username, oid, LIKE_API)

def record_unlike(app, username, oid):
	_process_like_pio(app, username, oid, DISLIKE_API)

def _process_like_event(app, username, oid, like=True):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		if like:
			func = functools.partial(record_like, app=app, username=username, oid=oid)
		else:
			func = functools.partial(record_unlike, app=app, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

def record_rating(app, username, oid, rating):
	client = predictionio.Client(app.AppKey, apiurl=app.URL)
	try:
		user = User.get_user(username)
		modeled = find_object_with_ntiid(oid)
		if modeled is not None and user is not None:
			client.create_user(username, params=IProperties(user))
			client.create_item(oid, ITypes(modeled), IProperties(modeled))
			client.identify(username)
			client.record_action_on_item("rate", oid, {'pio_rate':int(rating)})
			logger.debug("%s recorded rate action for %s", username, oid)
	finally:
		client.close()

def _process_rating_event(app, username, oid, rating):

	def _process_event():
		transaction_runner = \
				component.getUtility(IDataserverTransactionRunner)
		func = functools.partial(record_rating, app=app, username=username,
								 rating=rating, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IRatable, IObjectRatedEvent)
def _object_rated(modeled, event):
	app = get_predictionio_app()
	username = get_current_username()
	if app is not None and username:
		oid = to_external_ntiid_oid(modeled)
		if event.category == LIKE_CAT_NAME:
			like = event.rating != 0
			_process_like_event(app, username, oid, like)
		elif event.category == RATE_CATE_NAME and \
			 not IObjectUnratedEvent.providedBy(event):
			rating = getattr(event, 'rating', None)
			_process_rating_event(app, username, oid, rating)

@component.adapter(ITopic, IObjectRatedEvent)
def _topic_rated(topic, event):
	_object_rated(topic, event)
