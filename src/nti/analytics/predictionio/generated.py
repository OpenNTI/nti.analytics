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
import predictionio

from zope import component
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.dataserver.interfaces import ICreated
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.externalization.externalization import to_external_ntiid_oid

from . import get_predictionio_app

def _remove_generated(app, oid):
	client = predictionio.Client(app.AppKey, apiurl=app.URL)
	try:
		client.delete_item(oid)
	finally:
		client.close()
	logger.debug("item '%s' was removed", oid)

def _process_removal(app, obj):
	oid = to_external_ntiid_oid(obj)
	def _process_event():
		_remove_generated(app=app, oid=oid)
	transaction.get().addAfterCommitHook(
					lambda success: success and gevent.spawn(_process_event))

@component.adapter(ICreated, IObjectRemovedEvent)
def _created_removed(modeled, event):
	app = get_predictionio_app()
	if app is not None:
		_process_removal(app, modeled)

@component.adapter(ITopic, IObjectRemovedEvent)
def _topic_removed(topic, event):
	app = get_predictionio_app()
	if app is not None:
		_process_removal(app, topic)
