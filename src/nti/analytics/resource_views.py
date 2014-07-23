#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.ntiids import ntiids

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IResourceEvent

from .common import get_entity
from .common import process_event
from .common import get_course_by_ntiid
from .common import IDLookup
id_lookup = IDLookup()

def _get_course( event ):
	# TODO We also have event.course, not sure what the app would pass us (ntiid?).
	# Try to look up via resource ntiid (don't think this will work).
	#return get_course_by_ntiid( event.resource_id )
	return ntiids.find_object_with_ntiid( event.course )

def _validate_resource_event( event ):
	""" Validate our events, sanitizing as we go. """
	# I think nti.externalization handles encoding.
	user = get_entity( event.user )
	if user is None:
		raise ValueError( 'Event received with non-existent user (user=%s) (event=%s)' %
							( event.user, event ) )

	course = _get_course( event )
	if course is None:
		raise ValueError( """Event received with non-existent course
							(user=%s) (course=%s) (event=%s)""" %
							( event.user, event.course, event ) )

	time_length = event.time_length
	if time_length < 0:
		raise ValueError( """Event received with negative time_length
							(user=%s) (time_length=%s) (event=%s)""" %
							( event.user, time_length, event ) )

	event.time_length = int( time_length )

	if not ntiids.is_valid_ntiid_string( event.resource_id ):
		raise ValueError( """Event received for invalid resource id
							(user=%s) (resource=%s) (event=%s)""" %
							( event.user, event.resource_id, event) )


def _validate_video_event( event ):
	""" Validate our events, sanitizing as we go. """
	# Validate our parent fields
	_validate_resource_event( event )

	start = event.video_start_time
	end = event.video_end_time
	if 		start < 0 	\
		or 	end < 0 	\
		or 	end < start:
		raise ValueError( 'Video event has invalid time values (start=%s) (end=%s) (event=%s)' %
						( start, end, event.event_type ) )

	event.video_start_time = int( start )
	event.video_end_time = int( end )


def _add_resource_event( db, event, nti_session=None ):
	_validate_resource_event( event )

	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( event )
	db.create_course_resource_view( user,
								nti_session,
								event.timestamp,
								course,
								event.context_path,
								resource_id,
								event.time_length )
	logger.debug( 	"Resource view event (user=%s) (course=%s) (resource=%s) (time_length=%s)",
					user, course, resource_id, event.time_length )


def _add_video_event( db, event, nti_session=None ):
	_validate_video_event( event )

	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( event )
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
	logger.debug( 	"Video event (user=%s) (course=%s) (resource=%s) (type=%s) (start=%s) (end=%s) (time_length=%s)",
					user, course, resource_id,
					event.event_type, event.video_start_time,
					event.video_end_time, event.time_length )


def handle_events( batch_events ):
	# TODO We likely don't have valid sessions to pass along.
	for event in batch_events:
		if IVideoEvent.providedBy( event ):
			process_event( _add_video_event, event=event )
		elif IResourceEvent.providedBy( event ):
			process_event( _add_resource_event, event=event )
	# If we validated early, we could return something meaningful.
	# But we'd have to handle all validation exceptions as to not lose the valid
	# events. The nti.async.processor does this and at least drops the bad
	# events in a failed queue.
	return len( batch_events )
