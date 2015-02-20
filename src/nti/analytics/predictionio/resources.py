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

from nti.dataserver.users import User
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.ntiids.ntiids import find_object_with_ntiid

from ..recorded.interfaces import IObjectViewedRecordedEvent

from . import get_current_username
from . import get_predictionio_app

from .interfaces import IType
from .interfaces import IProperties

VIEW_API = "view"

def _process_like_pio(app, username, oid, api):
	client = predictionio.Client(app.AppKey, apiurl=app.URL)
	try:
		user = User.get_user(username)
		obj = find_object_with_ntiid(oid)
		if obj is not None and user is not None:
			client.create_user(username, params=IProperties(user))
			client.create_item(oid, IType(obj), IProperties(obj))
			client.identify(username)
			client.record_action_on_item(api, oid)
			logger.debug("%s recorded action '%s' for %s", username, api, oid)
	finally:
		client.close()

def record_view(app, username, oid):
	_process_like_pio(app, username, oid, VIEW_API)

def _process_view_event(app, username, oid, like=True):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		func = functools.partial(record_view, app=app, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IObjectViewedRecordedEvent)
def _object_viewed(event):
	app = get_predictionio_app()
	username = get_current_username()
	if app is not None and username:
		pass
