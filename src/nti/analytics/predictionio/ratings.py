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

from zope import component

from contentratings.interfaces import IObjectRatedEvent

from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.interfaces import IRatable
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.dataserver.rating import IObjectUnratedEvent

from .interfaces import IOID
from .interfaces import IType
from .interfaces import IProperties

from . import get_user
from . import object_finder
from . import get_current_username
from . import get_predictionio_client

LIKE_API = "like"
DISLIKE_API = "dislike"
LIKE_CAT_NAME = "likes"
RATE_CATE_NAME = 'rating'

def _process_like_pio(username, oid, api, params=None):
	client = get_predictionio_client()
	if client is None:
		return
	try:
		params = params or {}
		obj = object_finder(oid)
		user = get_user(username)
		if obj is not None and user is not None:
			client.create_event(event="$set",
  								entity_type="user",
  								entity_id=IOID(user),
  								properties=IProperties(user))
			
			client.create_event(event="$set",
  								entity_type=IType(obj),
    							entity_id=oid,
    							properties=IProperties(obj))
			
			client.create_event(event=api,
  								entity_type="user",
    							entity_id=IOID(user),
								target_entity_type=IType(obj),
								target_entity_id=oid,
								properties=params)
			logger.debug("%s recorded action '%s' for %s", username, api, oid)
	finally:
		client.close()

def record_like(app, username, oid):
	_process_like_pio(app, username, oid, LIKE_API)

def record_unlike(username, oid):
	_process_like_pio(username, oid, DISLIKE_API)

def _process_like_event(username, oid, like=True):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		if like:
			func = functools.partial(record_like, username=username, oid=oid)
		else:
			func = functools.partial(record_unlike, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

def record_rating(username, oid, rating, params=None):
	client = get_predictionio_client()
	if client is None:
		return
	try:
		params = params or {}
		obj = object_finder(oid)
		user = get_user(username)
		if obj is not None and user is not None:
			client.create_event(event="$set",
  								entity_type="user",
  								entity_id=IOID(user),
  								properties=IProperties(user))
			
			client.create_event(event="$set",
								entity_id=oid,
  								entity_type=IType(obj),
    							properties=IProperties(obj))
			
			params['pio_rate'] = int(rating)
			client.create_event(event="rate",
  								entity_type="user",
    							entity_id=IOID(user),
								target_entity_type=IType(obj),
								target_entity_id=oid,
								properties=params)

			logger.debug("%s recorded rate action for %s", username, oid)
	finally:
		client.close()

def _process_rating_event(username, oid, rating):

	def _process_event():
		transaction_runner = \
				component.getUtility(IDataserverTransactionRunner)
		func = functools.partial(record_rating, username=username,
								 rating=rating, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IRatable, IObjectRatedEvent)
def _object_rated(modeled, event):
	username = get_current_username()
	if username:
		oid = IOID(modeled)
		if event.category == LIKE_CAT_NAME:
			like = event.rating != 0
			_process_like_event(username, oid, like)
		elif event.category == RATE_CATE_NAME and \
			 not IObjectUnratedEvent.providedBy(event):
			rating = getattr(event, 'rating', None)
			_process_rating_event(username, oid, rating)

@component.adapter(ITopic, IObjectRatedEvent)
def _topic_rated(topic, event):
	_object_rated(topic, event)
