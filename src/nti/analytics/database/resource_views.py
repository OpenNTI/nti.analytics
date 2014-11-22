#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import OrderedDict

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import Enum

from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import ResourceId

from nti.analytics.model import ResourceEvent
from nti.analytics.model import WatchVideoEvent
from nti.analytics.model import SkipVideoEvent

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import ResourceViewMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database import resolve_objects
from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user_db_id
from nti.analytics.database.courses import get_course_id
from nti.analytics.database.resources import get_resource_id
from nti.analytics.database.resources import get_resource_val

# For meta-views into synthetic course info, we can special type the resource_id:
#	(about|instructors|tech_support)
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
	video_end_time = Column('video_end_time', Integer, nullable=False )
	with_transcript = Column('with_transcript', Boolean, nullable=False )
	max_time_length = Column( 'max_time_length', Integer, nullable=True )

	video_view_id = Column('video_view_id', Integer, Sequence( 'video_view_id_seq' ), primary_key=True )

def _get_context_path( context_path ):
	# Note: we could also sub these resource_ids for the actual
	# ids off of the Resources table.  That would be a bit tricky, because
	# we sometimes have courses and client specific strings (e.g. 'overview')
	# in this collection.

	result = ''
	if context_path:
		# This will remove all duplicate elements. Hopefully we do
		# not have scattered duplicates, which would be an error condition.
		context_path = list( OrderedDict.fromkeys( context_path ) )
		# '/' is illegal in ntiid strings
		result = '/'.join( context_path )

	return result

def _expand_context_path( context_path ):
	return context_path.split( '/' )

def _resource_view_exists( db, user_id, resource_id, timestamp ):
	# TODO Need to clean up these dupe events
	# We probably do not need a timestamp index here since we have an index on
	# the user and resource columns.
	return db.session.query( CourseResourceViews ).filter(
							CourseResourceViews.user_id == user_id,
							CourseResourceViews.resource_id == resource_id,
							CourseResourceViews.timestamp == timestamp ).count()

def create_course_resource_view(user, nti_session, timestamp, course, context_path, resource, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( resource )
	rid = get_resource_id( db, rid, create=True )

	course_id = get_course_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	if _resource_view_exists( db, uid, rid, timestamp ):
		logger.warn( 'Resource view already exists (user=%s) (resource_id=%s) (timestamp=%s)',
					user, rid, timestamp )
		return


	context_path = _get_context_path( context_path )

	new_object = CourseResourceViews( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										context_path=context_path,
										resource_id=rid,
										time_length=time_length )
	db.session.add( new_object )

def _video_view_exists( db, user_id, resource_id, timestamp, event_type ):
	return db.session.query( VideoEvents ).filter(
							VideoEvents.user_id == user_id,
							VideoEvents.resource_id == resource_id,
							VideoEvents.timestamp == timestamp,
							VideoEvents.video_event_type == event_type ).count()

def create_video_event(	user,
						nti_session, timestamp,
						course, context_path,
						video_resource,
						time_length,
						max_time_length,
						video_event_type,
						video_start_time,
						video_end_time,
						with_transcript ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	vid = ResourceId.get_id( video_resource )
	vid = get_resource_id( db, vid, create=True )

	course_id = get_course_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	if _video_view_exists( db, uid, vid, timestamp, video_event_type ):
		logger.warn( 'Video view already exists (user=%s) (resource_id=%s) (timestamp=%s)',
					user, vid, timestamp )
		return

	context_path = _get_context_path( context_path )

	new_object = VideoEvents(	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								context_path=context_path,
								resource_id=vid,
								time_length=time_length,
								max_time_length=max_time_length,
								video_event_type=video_event_type,
								video_start_time=video_start_time,
								video_end_time=video_end_time,
								with_transcript=with_transcript )
	db.session.add( new_object )

def _resolve_resource_view( record, course=None, user=None ):
	time_length = record.time_length

	if time_length < 1:
		# Ignore inconsequential events
		return None

	timestamp = record.timestamp
	context_path = record.context_path
	context_path = _expand_context_path( context_path )

	resource_id = record.resource_id
	resource_ntiid = get_resource_val( resource_id )

	resource_event = ResourceEvent(user=user,
					timestamp=timestamp,
					RootContextID=course,
					context_path=context_path,
					resource_id=resource_ntiid,
					Duration=time_length)

	return resource_event

def _resolve_video_view( record, course=None, user=None ):
	time_length = record.time_length
	max_time_length = record.max_time_length

	if time_length < 1:
		# Ignore inconsequential events
		return None

	timestamp = record.timestamp
	context_path = record.context_path
	context_path = _expand_context_path( context_path )

	resource_id = record.resource_id
	resource_ntiid = get_resource_val( resource_id )
	video_start_time = record.video_start_time
	video_end_time = record.video_end_time
	with_transcript = record.with_transcript

	if record.video_event_type == SkipVideoEvent.event_type:
		video_type = SkipVideoEvent
	else:
		video_type = WatchVideoEvent

	video_event = video_type(user=user,
				timestamp=timestamp,
				RootContextID=course,
				context_path=context_path,
				resource_id=resource_ntiid,
				Duration=time_length,
				MaxDuration=max_time_length,
				video_start_time=video_start_time,
				video_end_time=video_end_time,
				with_transcript=with_transcript)
	return video_event

def get_user_resource_views_for_ntiid( user, resource_ntiid ):
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	resource_id = get_resource_id( db, resource_ntiid )
	results = db.session.query( CourseResourceViews ).filter( CourseResourceViews.user_id == user_id,
															CourseResourceViews.resource_id == resource_id ).all()
	return resolve_objects( _resolve_resource_view, results, user=user )

def get_user_video_views_for_ntiid( user, resource_ntiid ):
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	resource_id = get_resource_id( db, resource_ntiid )
	results = db.session.query( VideoEvents ).filter( VideoEvents.user_id == user_id,
													VideoEvents.resource_id == resource_id ).all()
	return resolve_objects( _resolve_video_view, results, user=user )

def get_user_resource_views( user, course ):
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	course_id = get_course_id( db, course )
	results = db.session.query( CourseResourceViews ).filter( CourseResourceViews.user_id == user_id,
															CourseResourceViews.course_id == course_id ).all()
	return resolve_objects( _resolve_resource_view, results, user=user, course=course )

def get_user_video_events( user, course ):
	db = get_analytics_db()
	user_id = get_user_db_id( user )
	course_id = get_course_id( db, course )
	results = db.session.query( VideoEvents ).filter( VideoEvents.user_id == user_id,
													VideoEvents.course_id == course_id ).all()
	return resolve_objects( _resolve_video_view, results, user=user, course=course )

