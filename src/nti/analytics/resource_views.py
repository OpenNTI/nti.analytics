#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from datetime import datetime

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from nti.intid import interfaces as intid_interfaces

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IResourceEvent

from .common import get_entity
from .common import get_nti_session_id
from .common import process_event
from .common import get_course_by_ntiid
from .common import IDLookup
id_lookup = IDLookup()

def _get_course( resource_id ):
	# Try to look up via ntiid
	return get_course_by_ntiid( resource_id )

def _validate_resource_view( event ):
	# TODO implement
	pass

def _validate_video( event ):
	pass

def _add_resource_event( db, event, nti_session=None ):
	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( resource_id )
	db.create_course_resource_view( user,
								nti_session,
								event.timestamp,
								course,
								event.context_path,
								resource_id,
								event.time_length )
	logger.debug( 	"Resource view event (user=%s) (course=%s) (resource=%s)",
					user, course, resource_id )


def _add_video_event( db, event, nti_session=None ):
	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( resource_id )
	db.create_video_event( user,
						nti_session,
						event.timestamp,
						course,
						event.context_path,
						resource_id,
						event.time_length,
						event.event_type,
						event.video_start_time,
						event.video_end_time,
						event.with_transcript )
	logger.debug( 	"Video event (user=%s) (course=%s) (type=%s) (start=%s) (end=%s)",
					user, course, event.event_type, event.video_start_time, event.video_end_time )


def handle_events( batch_events ):
	# TODO We likely don't have valid sessions to pass along.
	for event in batch_events.events:
		if IVideoEvent.providedBy( event ):
			process_event( _add_video_event, event=event )
		elif IResourceEvent.providedBy( event ):
			process_event( _add_resource_event, event=event )
	# If we validate early, we could return something meaningful.
	return len( batch_events.events )
