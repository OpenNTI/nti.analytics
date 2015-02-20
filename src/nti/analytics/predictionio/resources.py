#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import gevent
import numbers
import transaction
from functools import partial

from zope import component

from nti.dataserver.interfaces import IDataserverTransactionRunner

from ..recorded.interfaces import IObjectViewedRecordedEvent

from .utils import create_user_event

from .interfaces import IOID

from . import VIEW_API

_primitives = six.string_types + (numbers.Number, bool)

def _process_view(username, oid, params=None):
	return create_user_event(event=VIEW_API, 
			  		 	 	 user=username,
			  		 	 	 obj=oid,
			  			 	 params=params)

def _process_view_event(username, oid, params=None):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		func = partial(_process_view, username=username, oid=oid, params=params)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IObjectViewedRecordedEvent)
def _object_viewed(event):
	params = {}
	user = event.user
	oid = IOID(event.object, None)
	
	## handle context
	context = getattr(event, 'context', None)
	if not isinstance(context, _primitives):
		context = IOID(context, None)
	if context is not None:
		params['context'] = str(context)
		
	## add event properties
	for name in ('duration', 'context_path', 'video_end_time',
			  	 'with_transcript', 'video_start_time', 'timestamp'):
		value = getattr(event, name, None)
		if value is not None:
			params[name] = str(value)
	_process_view_event(username=user.username, oid=oid, params=params)
