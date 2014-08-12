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
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import ICourseCatalogViewEvent

from .common import get_entity
from .common import process_event

from nti.analytics.database import resource_views as db_resource_tags
from nti.analytics.database import resource_views as db_resource_views
from nti.analytics.database import enrollments as db_enrollments
from nti.analytics.database import boards as db_boards
from nti.analytics.database import blogs as db_blogs

def _get_object( ntiid ):
	return ntiids.find_object_with_ntiid( ntiid )

def _get_course( event ):
	return _get_object( event.course )

def _validate_analytics_event( event ):
	""" Validate our events, sanitizing as we go. """
	# I think nti.externalization handles encoding.
	user = get_entity( event.user )
	if user is None:
		raise ValueError( 'Event received with non-existent user (user=%s) (event=%s)' %
							( event.user, event ) )

	time_length = getattr( event, time_length, 0 )
	if time_length < 0:
		raise ValueError( """Event received with negative time_length
							(user=%s) (time_length=%s) (event=%s)""" %
							( event.user, time_length, event ) )

	event.time_length = int( time_length )

def _validate_course_event( event ):
	""" Validate our events, sanitizing as we go. """
	_validate_analytics_event( event )

	course = _get_course( event )
	if course is None:
		raise ValueError( """Event received with non-existent course
							(user=%s) (course=%s) (event=%s)""" %
							( event.user, event.course, event ) )


def _validate_resource_event( event ):
	""" Validate our events, sanitizing as we go. """
	_validate_course_event( event )

	if not ntiids.is_valid_ntiid_string( event.resource_id ):
		raise ValueError( """Event received for invalid resource id
							(user=%s) (resource=%s) (event=%s)""" %
							( event.user, event.resource_id, event ) )


def _validate_video_event( event ):
	""" Validate our events, sanitizing as we go. """
	# Validate our parent fields
	_validate_resource_event( event )

	start = event.video_start_time
	end = event.video_end_time
	if 		start < 0 	\
		or 	end < 0:
		raise ValueError( 'Video event has invalid time values (start=%s) (end=%s) (event=%s)' %
						( start, end, event.event_type ) )

	event.video_start_time = int( start )
	event.video_end_time = int( end )

def _add_note_event( event, nti_session=None ):
	_validate_course_event( event )

	user = get_entity( event.user )
	course = _get_course( event )
	note = _get_object( event.note_id )

	db_resource_tags.create_note_view(
								user,
								nti_session,
								event.timestamp,
								course,
								note )
	logger.debug( 	"Course note view event (user=%s) (course=%s)",
					user, course )

def _add_topic_event( event, nti_session=None ):
	_validate_course_event( event )

	user = get_entity( event.user )
	course = _get_course( event )
	topic = _get_object( event.topic_id )

	db_boards.create_topic_view(user,
								nti_session,
								event.timestamp,
								course,
								topic,
								event.time_length )
	logger.debug( 	"Course topic view event (user=%s) (course=%s) (topic=%s) (time_length=%s)",
					user, course, topic, time_length )

def _add_blog_event( event, nti_session=None ):
	_validate_analytics_event( event )

	user = get_entity( event.user )
	blog = _get_object( event.blog_id )

	db_blogs.create_blog_view(	user,
								nti_session,
								event.timestamp,
								blog,
								event.time_length )
	logger.debug( 	"Blog view event (user=%s) (blog=%s) (time_length=%s)",
					user, blog, time_length )

def _add_catalog_event( event, nti_session=None ):
	_validate_course_event( event )

	user = get_entity( event.user )
	course = _get_course( event )

	db_enrollments.create_course_catalog_view( user,
								nti_session,
								event.timestamp,
								course,
								event.time_length )
	logger.debug( 	"Course catalog view event (user=%s) (course=%s) (time_length=%s)",
					user, course, event.time_length )

def _add_resource_event( event, nti_session=None ):
	_validate_resource_event( event )

	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( event )

	db_resource_views.create_course_resource_view( user,
								nti_session,
								event.timestamp,
								course,
								event.context_path,
								resource_id,
								event.time_length )
	logger.debug( 	"Resource view event (user=%s) (course=%s) (resource=%s) (time_length=%s)",
					user, course, resource_id, event.time_length )


def _add_video_event( event, nti_session=None ):
	_validate_video_event( event )

	user = get_entity( event.user )
	resource_id = event.resource_id
	course = _get_course( event )

	db_resource_views.create_video_event( user,
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
	# We could try to grab one if the event is not too old...
	for event in batch_events:
		if INoteViewEvent( event ):
			process_event( _add_note_event, event=event )
		elif IBlogViewEvent.providedBy( event ):
			process_event( _add_blog_event, event=event )
		elif ITopicViewEvent.providedBy( event ):
			process_event( _add_topic_event, event=event )
		elif IVideoEvent.providedBy( event ):
			process_event( _add_video_event, event=event )
		elif IResourceEvent.providedBy( event ):
			process_event( _add_resource_event, event=event )
		elif ICourseCatalogViewEvent.providedBy( event ):
			process_event( _add_catalog_event, event=event )
	# If we validated early, we could return something meaningful.
	# But we'd have to handle all validation exceptions as to not lose the valid
	# events. The nti.async.processor does this and at least drops the bad
	# events in a failed queue.
	return len( batch_events )
