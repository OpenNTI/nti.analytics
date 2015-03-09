#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from ..recorded.interfaces import IObjectViewedRecordedEvent

from .utils import create_user_event

from .interfaces import IOID

from . import VIEW_API
from . import primitives as _primitives

def _process_view_event(username, oid, params=None, event_time=None, safe=True):
	__traceback_info__ = username, oid, params, event_time
	try:
		## CS: 20150309. Don't process events in a greenlet
		## since view events are batched queue events
		return create_user_event(event=VIEW_API, 
				  		 	 	 user=username,
				  		 	 	 obj=oid,
				  			 	 params=params,
				  			 	 event_time=event_time)
	except Exception:
		if not safe:
			raise
		else:
			logger.exception("Cannot process user view event")

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
		
	# event time
	event_time = getattr(event, 'timestamp', None)
	
	## add event properties
	for name in ('duration', 'context_path', 'video_end_time',
			  	 'with_transcript', 'video_start_time'):
		value = getattr(event, name, None)
		if value is not None:
			params[name] = str(value)

	_process_view_event(username=user.username, oid=oid,
						params=params, event_time=event_time)
