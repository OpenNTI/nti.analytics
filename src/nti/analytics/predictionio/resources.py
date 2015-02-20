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

from nti.dataserver.interfaces import IDataserverTransactionRunner

from ..recorded.interfaces import IObjectViewedRecordedEvent

from .interfaces import IOID
from .interfaces import IType
from .interfaces import IProperties

from . import get_user
from . import object_finder
from . import get_current_username
from . import get_predictionio_client

VIEW_API = "view"

def _process_view(username, oid, params=None):
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
			
			client.create_event(event=VIEW_API,
  								entity_type="user",
    							entity_id=IOID(user),
								target_entity_type=IType(obj),
								target_entity_id=oid,
								properties=params)
			logger.debug("%s recorded view action for %s", user, oid)
	finally:
		client.close()

def _process_view_event(username, oid):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		func = functools.partial(_process_view, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IObjectViewedRecordedEvent)
def _object_viewed(event):
	username = get_current_username()
	if username:
		pass
