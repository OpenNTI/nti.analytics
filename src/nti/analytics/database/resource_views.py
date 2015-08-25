#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import Enum
from sqlalchemy import String

from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import ResourceId

from nti.analytics.interfaces import VIDEO_WATCH

from nti.analytics.read_models import AnalyticsResourceView
from nti.analytics.read_models import AnalyticsVideoSkip
from nti.analytics.read_models import AnalyticsVideoView

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import resolve_objects
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_filtered_records

from nti.analytics.database.meta_mixins import ResourceMixin
from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import ResourceViewMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_user
from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user_db_id

from nti.analytics.database.resources import get_resource_id
from nti.analytics.database.resources import get_resource_val
from nti.analytics.database.resources import get_resource_record
from nti.analytics.database.resources import get_resource_record_from_id

from nti.analytics.database._utils import expand_context_path
from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_root_context_ids
from nti.analytics.database._utils import get_root_context_obj

class CourseResourceViews(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'CourseResourceViews'

	# Need to have a seq primary key that we will not use to work around primary key limits
	# in mysql, or we could put our resource_ids into another table to conserve space (we did).
	# We'll probably just pull all of these events by indexed course; so, to avoid a join,
	# let's try this.
	resource_view_id = Column('resource_view_id', Integer, Sequence( 'resource_view_id_seq' ), primary_key=True )

class VideoEvents(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'VideoEvents'
	video_event_type = Column('video_event_type', Enum( 'WATCH', 'SKIP' ), nullable=False )
	# seconds from beginning of video (time 0s)
	video_start_time = Column('video_start_time', Integer, nullable=False )
	video_end_time = Column('video_end_time', Integer, nullable=True )
	with_transcript = Column('with_transcript', Boolean, nullable=False )
	video_view_id = Column('video_view_id', Integer, Sequence( 'video_view_id_seq' ), primary_key=True )
	play_speed = Column( 'play_speed', String( 16 ), nullable=True )

class VideoPlaySpeedEvents(Base,BaseTableMixin,ResourceMixin):
	__tablename__ = 'VideoPlaySpeedEvents'

	video_play_speed_id = Column('video_play_speed_id', Integer,
								Sequence( 'video_play_speed_id_seq' ), primary_key=True )
	old_play_speed = Column( 'old_play_speed', String( 16 ), nullable=False )
	new_play_speed = Column( 'new_play_speed', String( 16 ), nullable=False )
	video_time = Column('video_time', Integer, nullable=False )

	# Optionally link to an actual video event, if possible.
	video_view_id = Column('video_view_id', Integer, nullable=True, index=True )

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
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( resource )
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
	return _create_view( CourseResourceViews, user, nti_session, timestamp,
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
	sid = SessionId.get_id( nti_session )
	vid = ResourceId.get_id( resource_id )
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
	user = get_or_create_user( user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	vid = ResourceId.get_id( video_resource )
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

def _resolve_resource_view( record, course=None, user=None ):
	time_length = record.time_length

	# We could filter out time_length = 0 events, but they
	# may be useful to determine if 'some' progress has possibly made.
	# We also store 0s events at event start time.

	timestamp = record.timestamp
	context_path = record.context_path
	context_path = expand_context_path( context_path )
	root_context = get_root_context_obj( record ) if course is None else course
	user = get_user( record.user_id ) if user is None else user

	resource_id = record.resource_id
	resource_ntiid = get_resource_val( resource_id )

	resource_event = AnalyticsResourceView(user=user,
					timestamp=timestamp,
					RootContext=root_context,
					context_path=context_path,
					ResourceId=resource_ntiid,
					Duration=time_length)

	return resource_event

def _resolve_video_view( record, course=None, user=None, max_time_length=None ):
	time_length = record.time_length

	# We could filter out time_length = 0 events, but they
	# may be useful to determine if 'some' progress has possibly made.
	# We also store 0s events at event start time.

	timestamp = record.timestamp
	context_path = record.context_path
	context_path = expand_context_path( context_path )
	root_context = get_root_context_obj( record ) if course is None else course
	user = get_user( record.user_id ) if user is None else user
	resource_record = get_resource_record_from_id( record.resource_id )

	if max_time_length is None:
		max_time_length = resource_record.max_time_length

	resource_ntiid = resource_record.resource_ds_id
	video_start_time = record.video_start_time
	video_end_time = record.video_end_time
	with_transcript = record.with_transcript


	if record.video_event_type == 'WATCH':
		video_type = AnalyticsVideoView
	else:
		video_type = AnalyticsVideoSkip

	video_event = video_type(user=user,
				SessionID=record.session_id,
				timestamp=timestamp,
				RootContext=root_context,
				context_path=context_path,
				ResourceId=resource_ntiid,
				Duration=time_length,
				MaxDuration=max_time_length,
				VideoStartTime=video_start_time,
				VideoEndTime=video_end_time,
				WithTranscript=with_transcript)
	return video_event

def get_user_resource_views_for_ntiid( user, resource_ntiid ):
	results = ()
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	resource_id = get_resource_id( db, resource_ntiid )
	if resource_id is not None:
		view_records = db.session.query( CourseResourceViews ).filter(
										CourseResourceViews.user_id == user_id,
										CourseResourceViews.resource_id == resource_id ).all()
		results = resolve_objects( _resolve_resource_view, view_records, user=user )
	return results

def get_user_video_views_for_ntiid( user, resource_ntiid ):
	results = ()
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	resource_record = get_resource_record( db, resource_ntiid )
	if resource_record is not None:
		resource_id = resource_record.resource_id
		max_time_length = resource_record.max_time_length
		video_records = db.session.query( VideoEvents ).filter(
										VideoEvents.user_id == user_id,
										VideoEvents.resource_id == resource_id,
										VideoEvents.video_event_type == VIDEO_WATCH ).all()
		results = resolve_objects( _resolve_video_view, video_records, user=user, max_time_length=max_time_length )
	return results

def get_user_resource_views( user, course=None, **kwargs ):
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
