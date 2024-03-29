#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from six import string_types

from sqlalchemy import func
from sqlalchemy import or_

from nti.analytics_database.resource_views import VideoEvents
from nti.analytics_database.resource_views import ResourceViews
from nti.analytics_database.resource_views import VideoPlaySpeedEvents

from nti.analytics.common import timestamp_type

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_root_context_records

from nti.analytics.database.query_utils import get_filtered_records
from nti.analytics.database.query_utils import get_record_count_by_user

from nti.analytics.database.resources import get_resource_id
from nti.analytics.database.resources import get_resource_record

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import get_ntiid_id

from nti.analytics.interfaces import VIDEO_WATCH

logger = __import__('logging').getLogger(__name__)


def _resource_view_exists( db, table, user_id, resource_id, timestamp ):
	return db.session.query(table).filter(
							table.user_id == user_id,
							table.resource_id == resource_id,
							table.timestamp == timestamp).first()


def _create_view(table, user, nti_session, timestamp, root_context, context_path, resource, time_length):
	"""
	Create a basic view event, if necessary.  Also if necessary, may update existing
	events with appropriate data.
	"""
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	rid = get_ntiid_id( resource )
	resource_record = get_resource_record(db, rid, create=True)
	timestamp = timestamp_type( timestamp )

	existing_record = _resource_view_exists(db, table, user_record.user_id,
											resource_record.resource_id, timestamp)
	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
			return
		else:
			logger.warn('%s view already exists (user=%s) (resource_id=%s) (timestamp=%s) (time_length=%s)',
						table.__tablename__, user, rid, timestamp, time_length)
			return
	context_path = get_context_path( context_path )
	root_context, entity_root_context = get_root_context_records(root_context)

	new_object = table(session_id=sid,
					   timestamp=timestamp,
					   context_path=context_path,
					   time_length=time_length)
	new_object._resource = resource_record
	new_object._user_record = user_record
	new_object._root_context_record = root_context
	new_object._entity_root_context_record = entity_root_context
	db.session.add(new_object)


def create_resource_view(user, nti_session, timestamp, root_context,
						 context_path, resource, time_length):
	return _create_view(ResourceViews, user, nti_session, timestamp,
						root_context, context_path, resource, time_length)
create_course_resource_view = create_resource_view


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


def create_play_speed_event(user, nti_session, timestamp, root_context, resource_id,
							video_time, old_play_speed, new_play_speed):
	db = get_analytics_db()
	user = get_or_create_user( user )
	sid = nti_session
	vid = get_ntiid_id( resource_id )
	resource_record = get_resource_record(db, vid, create=True)

	timestamp = timestamp_type( timestamp )

	existing_record = _video_play_speed_exists(db, user.user_id,
											   resource_record.resource_id,
											   timestamp, video_time)

	if existing_record is not None:
		# Should only have one record for timestamp, video_time, user, video.
		# Ok, duplicate event received, apparently.
		logger.warn('Video play_speed already exists (user=%s) (video_time=%s) (timestamp=%s)',
					user, video_time, timestamp)
		return

	root_context, entity_root_context = get_root_context_records(root_context)
	video_record = _video_view_exists(db, user.user_id,
									  resource_record.resource_id,
									  timestamp, 'WATCH')
	video_view_id = video_record.video_view_id if video_record else None

	new_object = VideoPlaySpeedEvents(session_id=sid,
									  timestamp=timestamp,
									  video_view_id=video_view_id,
									  video_time=video_time,
									  old_play_speed=old_play_speed,
									  new_play_speed=new_play_speed)
	new_object._resource = resource_record
	new_object._user_record = user
	new_object._root_context_record = root_context
	new_object._entity_root_context_record = entity_root_context
	db.session.add(new_object)


def _get_video_play_speed( db, user_id, resource_id, timestamp ):
	return db.session.query(VideoPlaySpeedEvents).filter(
							VideoPlaySpeedEvents.user_id == user_id,
							VideoPlaySpeedEvents.resource_id == resource_id,
							VideoPlaySpeedEvents.timestamp == timestamp).first()


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
						play_speed,
						player_configuration ):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	vid = get_ntiid_id(video_resource)
	resource_record = get_resource_record(db, vid, create=True,
										  max_time_length=max_time_length)

	timestamp = timestamp_type(timestamp)

	existing_record = _video_view_exists(db, user_record.user_id,
										 resource_record.resource_id,
										 timestamp, video_event_type)

	if 		time_length is None \
		and video_start_time is not None \
		and video_end_time is not None \
		and video_start_time < video_end_time:
		# The client may not provide this
		time_length = video_end_time - video_start_time

	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
			existing_record.video_start_time = video_start_time
			existing_record.video_end_time = video_end_time
			return
		else:
			# Ok, duplicate event received, apparently.
			# XXX: Really shouldn't happen anymore
			logger.warn('Video view already exists (user=%s) (resource_id=%s) (timestamp=%s) (time_length=%s)',
						user, vid, timestamp, time_length)
			return

	context_path = get_context_path( context_path )
	root_context, entity_root_context = get_root_context_records(root_context)

	new_object = VideoEvents(session_id=sid,
							 timestamp=timestamp,
							 context_path=context_path,
							 time_length=time_length,
							 video_event_type=video_event_type,
							 video_start_time=video_start_time,
							 video_end_time=video_end_time,
							 with_transcript=with_transcript,
							 play_speed=play_speed,
							 player_configuration=player_configuration)
	new_object._resource = resource_record
	new_object._user_record = user_record
	new_object._root_context_record = root_context
	new_object._entity_root_context_record = entity_root_context
	db.session.add(new_object)

	# Update our referenced field, if necessary.
	video_play_speed = _get_video_play_speed(db, user_record.user_id,
											 resource_record.resource_id,
											 timestamp)
	if video_play_speed:
		video_play_speed.video_view_id = new_object.video_view_id


def _resolve_resource_view(record, root_context=None, user=None):
	if root_context is not None:
		record.RootContext = root_context
	if user is not None:
		record.user = user
	return record


def _resolve_video_view(record, course=None, user=None, max_time_length=None):
	if course is not None:
		record.RootContext = course
	if user is not None:
		record.user = user
	if max_time_length is not None:
		record.MaxDuration = max_time_length
	return record


def get_resource_views_for_ntiid(resource_ntiid, user=None,
								 root_context=None, **kwargs):
	results = ()
	db = get_analytics_db()
	resource_id = get_resource_id(db, resource_ntiid)
	if resource_id is not None:
		filters = ( ResourceViews.resource_id == resource_id, )
		view_records = get_filtered_records(user,
											ResourceViews,
											root_context=root_context,
											filters=filters,
											**kwargs )
		results = resolve_objects(_resolve_resource_view, view_records,
								 user=user, root_context=root_context)
	return results


def get_user_resource_views_for_ntiid(user, resource_ntiid):
	return get_resource_views_for_ntiid(resource_ntiid, user=user)


def get_video_views_for_ntiid( resource_ntiid, user=None, course=None, **kwargs ):
	results = ()
	db = get_analytics_db()
	resource_record = resource_ntiid
	if isinstance(resource_ntiid, string_types):
		resource_record = get_resource_record( db, resource_ntiid )
	if resource_record is not None:
		resource_id = resource_record.resource_id
		max_time_length = resource_record.max_time_length
		filters = ( VideoEvents.video_event_type == VIDEO_WATCH,
					VideoEvents.resource_id == resource_id )
		video_records = get_filtered_records(user,
											VideoEvents,
											course=course,
											filters=filters,
											**kwargs )
		results = resolve_objects(_resolve_video_view, video_records,
								  user=user, course=course,
								  max_time_length=max_time_length)
	return results


def _segment_query_factory(session, table):
	# When a user starts watching a video we get an initial watch
	# event with a video_start_time, but no duration, and no video_end_time.
	# if they close the window or we don't get any updates for that event.
	# In that case our segment is (start, start). When we start getting heartbeats
	# we then have a duration (time_length) that is the delta between the current
	# playhead location and the start time. In this case in active segment is
	# (start, start + time_length). We deal with all that in this query, which is
	# nastier than it would ideally be. We'd need to change how we send these events
	# and clean data to simplify this. One such approach would be to make sure
	# we always have a video_end_time
	return session.query(VideoEvents.video_start_time.label('start'),
						 func.coalesce(func.nullif(VideoEvents.video_end_time, 0),
									   VideoEvents.video_start_time \
									   + func.coalesce(VideoEvents.time_length, 0)).label('end'),
						 func.count('*'))

def get_watched_segments_for_ntiid( resource_ntiid, user=None, course=None, **kwargs ):
	"""
	Returns an iterable of triples indentifying the distinct segments of the video
	that have been watched.

	The return value is a list of tuples of the form (video_start_time, video_end_time, count)
	"""
	db = get_analytics_db()
	resource_record = resource_ntiid
	if isinstance(resource_ntiid, string_types):
		resource_record = get_resource_record( db, resource_ntiid )
	results = ()
	if resource_record is not None:
		resource_id = resource_record.resource_id
		filters = ( VideoEvents.video_event_type == VIDEO_WATCH,
					VideoEvents.resource_id == resource_id,
					# We have video watch events where the start > end, which seems nonsensical.
					# The starts are large and look like at one point we might be sending start
					# times in ms instead of seconds??? As a watched segment these don't make sense
					# and cause problems upstream so strip them here. We have to be careful that
					# we don't filter out the events where there is no end time. We want those
					# TODO Should we migrate and actually remove them?
					or_(func.nullif(VideoEvents.video_end_time, 0) == None,
						VideoEvents.video_start_time <= VideoEvents.video_end_time)
				   )
		query = get_filtered_records(user,
									 VideoEvents,
									 course=course,
									 filters=filters,
									 query_factory=_segment_query_factory,
									 yield_per=None, #give us the query so we can group_by
									 **kwargs )
		query = query.group_by('start', 'end')
		results = query.all()
		
	return results

def get_user_video_views_for_ntiid(user, resource_ntiid):
	return get_video_views_for_ntiid(resource_ntiid, user=user)


def get_user_resource_views(user=None, root_context=None, **kwargs):
	results = get_filtered_records(user, ResourceViews,
								   root_context=root_context, **kwargs)
	if user is not None or root_context is not None:
		results = resolve_objects(_resolve_resource_view, results,
						   		 user=user, root_context=root_context)
	return results
get_resource_views = get_user_resource_views


def get_resource_views_by_user(root_context=None, **kwargs):
	return get_record_count_by_user(ResourceViews,
									root_context=root_context,
									**kwargs)


def get_user_video_views( user=None, course=None, **kwargs  ):
	filters = ( VideoEvents.video_event_type == VIDEO_WATCH,
				VideoEvents.time_length > 1 )
	results = get_filtered_records( user, VideoEvents,
								course=course, filters=filters, **kwargs )
	if user is not None or course is not None:
		results = resolve_objects( _resolve_video_view, results, user=user, course=course )
	return results
get_video_views = get_user_video_views


def get_video_views_by_user(root_context=None, **kwargs):
	filters = (VideoEvents.video_event_type == VIDEO_WATCH,
			   VideoEvents.time_length > 1)

	return get_record_count_by_user(VideoEvents,
									root_context=root_context,
									filters=filters,
									**kwargs)


def remove_video_data(user, video):
	"""
	Remove the video data for a user and video. Useful for QA.
	"""
	db = get_analytics_db()
	# Testing
	resource_ds_id = getattr(video, 'ntiid', video)
	resource_record = get_resource_record(db, resource_ds_id)
	if resource_record is not None:
		resource_id = resource_record.resource_id
		user_record = get_or_create_user(user)
		if user_record is not None:
			user_id = user_record.user_id
			db.session.query(VideoEvents).filter(
							 VideoEvents.user_id == user_id,
							 VideoEvents.resource_id == resource_id).delete()


def remove_resource_data(user, resource):
	"""
	Remove the resource data for a user and reading. Useful for QA.
	"""
	db = get_analytics_db()
	# Testing
	resource_ds_id = getattr(resource, 'ntiid', resource)
	resource_record = get_resource_record(db, resource_ds_id)
	if resource_record is not None:
		resource_id = resource_record.resource_id
		user_record = get_or_create_user(user)
		if user_record is not None:
			user_id = user_record.user_id
			db.session.query(ResourceViews).filter(
							 ResourceViews.user_id == user_id,
							 ResourceViews.resource_id == resource_id).delete()

