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

from sqlalchemy.schema import Sequence

import zope.intid

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CourseId
from nti.analytics.identifier import ResourceId
_sessionid = SessionId()
_courseid = CourseId()
_resourceid = ResourceId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import ResourceViewMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_or_create_user

# For meta-views into synthetic course info, we can special type the resource_id:
#	(about|instructors|tech_support)
class CourseResourceViews(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'CourseResourceViews'

	# Need to have a seq primary key that we will not use to work around primary key limits
	# in mysql, or we could put our resource_ids into another table to conserve space.
	# We'll probably just pull all of these events by indexed course; so, to avoid a join,
	# let's try this.
	resource_view_id = Column('resource_view_id', Integer, Sequence( 'resource_view_id_seq' ), primary_key=True )


# Would we query on these separate event types? Probably not.
# If so, we may break them out into separate tables.
# TODO Rewatch events? (kaltura player doesn't really have this right now; we could infer...)
class VideoEvents(Base,ResourceViewMixin,TimeLengthMixin):
	__tablename__ = 'VideoEvents'
	video_event_type = Column('video_event_type', Enum( 'WATCH', 'SKIP' ), nullable=False )
	# seconds from beginning of video (time 0s)
	video_start_time = Column('video_start_time', Integer, nullable=False )
	video_end_time = Column('video_end_time', Integer, nullable=False )
	with_transcript = Column('with_transcript', Boolean, nullable=False )

	video_view_id = Column('video_view_id', Integer, Sequence( 'video_view_id_seq' ), primary_key=True )

def create_course_resource_view(user, nti_session, timestamp, course, context_path, resource, time_length):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	rid = _resourceid.get_id( resource )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = CourseResourceViews( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										context_path=context_path,
										resource_id=rid,
										time_length=time_length )
	db.session.add( new_object )

def create_video_event(	user,
						nti_session, timestamp,
						course, context_path,
						video_resource,
						time_length,
						video_event_type,
						video_start_time,
						video_end_time,
						with_transcript ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	vid = _resourceid.get_id( video_resource )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = VideoEvents(	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								context_path=context_path,
								resource_id=vid,
								time_length=time_length,
								video_event_type=video_event_type,
								video_start_time=video_start_time,
								video_end_time=video_end_time,
								with_transcript=with_transcript )
	db.session.add( new_object )

