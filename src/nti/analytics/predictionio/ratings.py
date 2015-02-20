#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import transaction
from functools import partial

from zope import component

from contentratings.interfaces import IObjectRatedEvent

from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.interfaces import IRatable
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.dataserver.rating import IObjectUnratedEvent

from .interfaces import IOID

from .utils import create_user_event

from . import get_current_username

LIKE_API = "like"
DISLIKE_API = "dislike"
LIKE_CAT_NAME = "likes"
RATE_CATE_NAME = 'rating'

def _process_like_pio(username, oid, api, params=None):
	return create_user_event(event=api, 
				  		 	 user=username,
				  		 	 obj=oid,
				  			 params=params)

def record_like(username, oid):
	_process_like_pio(username, oid, LIKE_API)

def record_unlike(username, oid):
	_process_like_pio(username, oid, DISLIKE_API)

def _process_like_event(username, oid, like=True):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		if like:
			func = partial(record_like, username=username, oid=oid)
		else:
			func = partial(record_unlike, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

def record_rating(username, oid, rating, params=None):
	params = params or {}
	params['pio_rate'] = int(rating)
	return create_user_event(event="rate", 
			  		 	 	 user=username,
			  		 	 	 obj=oid,
			  			 	 params=params)

def _process_rating_event(username, oid, rating):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		func = partial(record_rating, username=username, rating=rating, oid=oid)
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
