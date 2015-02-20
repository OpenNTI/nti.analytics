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

from zope import component

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from nti.dataserver.interfaces import ICreated
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from .interfaces import IOID

from . import get_predictionio_client

def _remove_generated(oid):
	client = get_predictionio_client()
	if client is not None:
		try:
			client.delete_item(oid)
		finally:
			client.close()
		logger.debug("item '%s' was removed", oid)

def _process_removal(obj):
	oid = IOID(obj)
	def _process_event():
		_remove_generated(oid=oid)
	transaction.get().addAfterCommitHook(
					lambda success: success and gevent.spawn(_process_event))

@component.adapter(ICreated, IObjectRemovedEvent)
def _created_removed(modeled, event):
	_process_removal(modeled)

@component.adapter(ITopic, IObjectRemovedEvent)
def _topic_removed(topic, event):
	_process_removal(topic)
