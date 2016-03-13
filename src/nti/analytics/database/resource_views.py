#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics_database.resource_views import VideoEvents
from nti.analytics_database.resource_views import CourseResourceViews
from nti.analytics_database.resource_views import VideoPlaySpeedEvents
from nti.analytics_database.resource_views import UserFileUploadViewEvents

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import get_ds_id
from nti.analytics.identifier import get_ntiid_id

from nti.analytics.interfaces import VIDEO_WATCH

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_root_context_ids
from nti.analytics.database._utils import get_filtered_records

from nti.analytics.database.mime_types import get_mime_type_id

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database.resources import get_resource_id
from nti.analytics.database.resources import get_resource_record

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.dataserver.users import User

def _resource_view_exists( db, table, user_id, resource_id, timestamp ):
	return db.session.query( table ).filter(
							table.user_id == user_id,
							table.resource_id == resource_id,
							table.timestamp == timestamp ).first()

def _create_view( table, user, nti_session, timestamp, root_context, context_path, resource, time_length ):
	"""
	Create a basic view event, if necessary.  Also if necessary, may update existing
	events with appropriate data.
	"""
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	rid = get_ntiid_id( resource )
	rid = get_resource_id( db, rid, create=True )
	timestamp = timestamp_type( timestamp )

	existing_record = _resource_view_exists( db, table, uid, rid, timestamp )
	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			return
		else:
			logger.warn( '%s view already exists (user=%s) (resource_id=%s) (timestamp=%s)',
						table.__tablename__, user, rid, timestamp )
			return
	context_path = get_context_path( context_path )
	course_id, entity_root_context_id = get_root_context_ids( root_context )

	new_object = table( user_id=uid,
						session_id=sid,
						timestamp=timestamp,
						course_id=course_id,
						entity_root_context_id=entity_root_context_id,
						context_path=context_path,
						resource_id=rid,
						time_length=time_length )
	db.session.add( new_object )

def create_course_resource_view( user, nti_session, timestamp, course, context_path, resource, time_length):
	return _create_view(CourseResourceViews, user, nti_session, timestamp,
						course, context_path, resource, time_length)

def _video_view_exists( db, user_id, resource_id, timestamp, event_type ):
	return db.session.query( VideoEvents ).filter(
							VideoEvents.user_id == user_id,
							VideoEvents.resource_id == resource_id,
							VideoEvents.timestamp == timestamp,
							VideoEvents.video_event_type == event_type ).first()

def _video_play_speed_exists( db, user_id, resource_id, timestamp, video_time ):
	return db.session.query( VideoPlaySpeedEvents ).filter(
							VideoPlaySpeedEvents.user_id == user_id,
							VideoPlaySpeedEvents.resource_id == resource_id,
							VideoPlaySpeedEvents.timestamp == timestamp,
							VideoPlaySpeedEvents.video_time == video_time ).first()

def create_play_speed_event( user, nti_session, timestamp, root_context, resource_id,
							video_time, old_play_speed, new_play_speed ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	sid = nti_session
	vid = get_ntiid_id( resource_id )
	vid = get_resource_id( db, vid, create=True )

	timestamp = timestamp_type( timestamp )

	existing_record = _video_play_speed_exists( db, uid, vid, timestamp, video_time )

	if existing_record is not None:
		# Should only have one record for timestamp, video_time, user, video.
		# Ok, duplicate event received, apparently.
		logger.warn( 'Video play_speed already exists (user=%s) (video_time=%s) (timestamp=%s)',
					user, video_time, timestamp )
		return

	course_id, entity_root_context_id = get_root_context_ids( root_context )
	video_record = _video_view_exists( db, uid, vid, timestamp, 'WATCH' )
	video_view_id = video_record.video_view_id if video_record else None

	new_object = VideoPlaySpeedEvents(	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								entity_root_context_id=entity_root_context_id,
								resource_id=vid,
								video_view_id=video_view_id,
								video_time=video_time,
								old_play_speed=old_play_speed,
								new_play_speed=new_play_speed )
	db.session.add( new_object )

def _get_video_play_speed( db, user_id, resource_id, timestamp ):
	return db.session.query( VideoPlaySpeedEvents ).filter(
							VideoPlaySpeedEvents.user_id == user_id,
							VideoPlaySpeedEvents.resource_id == resource_id,
							VideoPlaySpeedEvents.timestamp == timestamp ).first()

def create_video_event(	user,
						nti_session, timestamp,
						root_context, context_path,
						video_resource,
						time_length,
						max_time_length,
						video_event_type,
						video_start_time,
						video_end_time,
						with_transcript,
						play_speed ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	vid = get_ntiid_id( video_resource )
	vid = get_resource_id( db, vid, create=True, max_time_length=max_time_length )

	timestamp = timestamp_type( timestamp )

	existing_record = _video_view_exists( db, uid, vid, timestamp, video_event_type )

	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			existing_record.video_start_time = video_start_time
			existing_record.video_end_time = video_end_time
			return
		else:
			# Ok, duplicate event received, apparently.
			logger.warn( 'Video view already exists (user=%s) (resource_id=%s) (timestamp=%s)',
						user, vid, timestamp )
			return

	context_path = get_context_path( context_path )
	course_id, entity_root_context_id = get_root_context_ids( root_context )

	new_object = VideoEvents(	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								entity_root_context_id=entity_root_context_id,
								context_path=context_path,
								resource_id=vid,
								time_length=time_length,
								video_event_type=video_event_type,
								video_start_time=video_start_time,
								video_end_time=video_end_time,
								with_transcript=with_transcript,
								play_speed=play_speed )
	db.session.add( new_object )
	db.session.flush()

	# Update our referenced field, if necessary.
	video_play_speed = _get_video_play_speed( db, uid, vid, timestamp )
	if video_play_speed:
		video_play_speed.video_view_id = new_object.video_view_id

def create_file_view( file_obj, session_id, timestamp, user, referrer, creator_username ):
	file_ds_id = get_ds_id( file_obj )

	db = get_analytics_db()
	user_record = get_or_create_user( user )
	user_id = user_record.user_id
	timestamp = timestamp_type( timestamp )

	creator = User.get_user( creator_username )
	creator = get_or_create_user( creator )
	creator_id = creator.user_id
	mime_type = 	getattr( file_obj, 'contentType', None ) \
				or 	getattr( file_obj, 'mime_type', None )
	mime_type_id = get_mime_type_id( db, mime_type )

	file_view = UserFileUploadViewEvents(user_id=user_id,
										session_id=session_id,
										timestamp=timestamp,
										referrer=referrer,
										creator_id=creator_id,
										file_ds_id=file_ds_id,
										file_mime_type_id=mime_type_id )
	db.session.add( file_view )
	logger.info('Created file view event (user=%s) (file=%s)',
				user.username,
				getattr( file_obj, 'filename', getattr( file_obj, '__name__', '' )))
	return file_view

def _resolve_resource_view( record, course=None, user=None ):
	if course is not None:
		record.RootContext = course
	if user is not None:
		record.user = user
	return record

def _resolve_video_view( record, course=None, user=None, max_time_length=None ):
	if course is not None:
		record.RootContext = course
	if user is not None:
		record.user = user
	if max_time_length is not None:
		record.MaxDuration = max_time_length
	return record

def get_resource_views_for_ntiid( resource_ntiid, user=None, course=None, **kwargs ):
	results = ()
	db = get_analytics_db()
	resource_id = get_resource_id( db, resource_ntiid )
	if resource_id is not None:
		filters = ( CourseResourceViews.resource_id == resource_id, )
		view_records = get_filtered_records( user, CourseResourceViews,
											course=course, filters=filters, **kwargs )
		results = resolve_objects( _resolve_resource_view, view_records, user=user, course=course )
	return results

def get_user_resource_views_for_ntiid( user, resource_ntiid ):
	return get_resource_views_for_ntiid( resource_ntiid, user=user )

def get_video_views_for_ntiid( resource_ntiid, user=None, course=None, **kwargs ):
	results = ()
	db = get_analytics_db()
	resource_record = get_resource_record( db, resource_ntiid )
	if resource_record is not None:
		resource_id = resource_record.resource_id
		max_time_length = resource_record.max_time_length
		filters = ( VideoEvents.video_event_type == VIDEO_WATCH,
					VideoEvents.resource_id == resource_id )
		video_records = get_filtered_records( user, VideoEvents,
											course=course, filters=filters, **kwargs )
		results = resolve_objects( _resolve_video_view, video_records, user=user, course=course, max_time_length=max_time_length )
	return results

def get_user_video_views_for_ntiid( user, resource_ntiid ):
	return get_video_views_for_ntiid( resource_ntiid, user=user )

def get_user_resource_views( user=None, course=None, **kwargs ):
	results = get_filtered_records( user, CourseResourceViews,
								course=course, **kwargs )
	return resolve_objects( _resolve_resource_view, results, user=user, course=course )

def get_user_video_views( user=None, course=None, **kwargs  ):
	filters = ( VideoEvents.video_event_type == VIDEO_WATCH,
				VideoEvents.time_length > 1 )
	results = get_filtered_records( user, VideoEvents,
								course=course, filters=filters, **kwargs )
	return resolve_objects( _resolve_video_view, results, user=user, course=course )

get_video_views = get_user_video_views
get_resource_views = get_user_resource_views
