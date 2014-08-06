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
from sqlalchemy import ForeignKey

from sqlalchemy.ext.declarative import declared_attr

import zope.intid

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CourseId
from nti.analytics.identifier import CommentId
from nti.analytics.identifier import ForumId
from nti.analytics.identifier import TopicId
_sessionid = SessionId()
_courseid = CourseId()
_commentid = CommentId()
_forumid = ForumId()
_topicid = TopicId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import CommentsMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_or_create_user

class ForumMixin(CourseMixin):
	@declared_attr
	def forum_id(cls):
		return Column('forum_id', Integer, ForeignKey("ForumsCreated.forum_id"), nullable=False, index=True, primary_key=True)

class TopicMixin(ForumMixin):
	@declared_attr
	def topic_id(cls):
		return Column('topic_id', Integer, ForeignKey("TopicsCreated.topic_id"), nullable=False, index=True, primary_key=True)


class ForumsCreated(Base,BaseTableMixin,CourseMixin,DeletedMixin):
	__tablename__ = 'ForumsCreated'
	forum_id = Column('forum_id', Integer, primary_key=True, index=True)

class TopicsCreated(Base,BaseTableMixin,ForumMixin,DeletedMixin):
	__tablename__ = 'TopicsCreated'
	topic_id = Column('topic_id', Integer, primary_key=True )

class ForumCommentsCreated(Base,CommentsMixin,TopicMixin):
	__tablename__ = 'ForumCommentsCreated'

class TopicsViewed(Base,BaseViewMixin,TopicMixin,TimeLengthMixin):
	__tablename__ = 'TopicsViewed'

def create_forum(user, nti_session, course, forum):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	fid = _forumid.get_id( forum )
	course_id = _courseid.get_id( course )

	timestamp = get_created_timestamp( forum )

	new_object = ForumsCreated( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								forum_id=fid )
	db.session.add( new_object )

def delete_forum(timestamp, forum_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_forum = db.session.query(ForumsCreated).filter( ForumsCreated.forum_id==forum_id ).one()
	db_forum.deleted=timestamp

	# Get our topics and comments
	db.session.query( TopicsCreated ).filter(
						TopicsCreated.forum_id == forum_id ).update( { TopicsCreated.deleted : timestamp } )
	db.session.query( ForumCommentsCreated ).filter(
						ForumCommentsCreated.forum_id == forum_id ).update(
							{ ForumCommentsCreated.deleted : timestamp } )
	db.session.flush()

def create_topic(user, nti_session, course, topic):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	fid = _forumid.get_id( topic.__parent__ )
	did = _topicid.get_id( topic )
	course_id = _courseid.get_id( course )

	timestamp = get_created_timestamp( topic )

	new_object = TopicsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										topic_id=did )
	db.session.add( new_object )

def delete_topic(timestamp, topic_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_id == topic_id ).one()
	db_topic.deleted = timestamp

	db.session.query( ForumCommentsCreated ).filter(
						ForumCommentsCreated.topic_id == topic_id ).update(
											{ ForumCommentsCreated.deleted : timestamp } )
	db.session.flush()

def create_topic_view(user, nti_session, timestamp, course, topic, time_length):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	fid = _forumid.get_id( topic.__parent__ )
	did = _topicid.get_id( topic )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = TopicsViewed( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid,
									topic_id=did,
									time_length=time_length )
	db.session.add( new_object )

def create_forum_comment(user, nti_session, course, topic, comment):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	forum = topic.__parent__
	fid = _forumid.get_id(forum)
	did = _topicid.get_id(topic)
	cid = _commentid.get_id(comment)
	course_id = _courseid.get_id( course )
	pid = None
	timestamp = get_created_timestamp( comment )

	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = _commentid.get_id( parent_comment )

	new_object = ForumCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										topic_id=did,
										parent_id=pid,
										comment_id=cid )
	db.session.add( new_object )

def delete_forum_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==comment_id ).one()
	comment.deleted=timestamp
	db.session.flush()


# StudentParticipationReport
def get_forum_comments_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = _courseid.get_id( course )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == uid,
															ForumCommentsCreated.course_id == course_id,
															ForumCommentsCreated.deleted == None ).all()
	return results

def get_topics_created_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = _courseid.get_id( course )
	results = db.session.query(TopicsCreated).filter( TopicsCreated.user_id == uid,
														TopicsCreated.course_id == course_id,
														TopicsCreated.deleted == None  ).all()
	return results

#TopicReport
def get_comments_for_topic(topic ):
	db = get_analytics_db()
	topic_id = _topicid.get_id( topic )
	results = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.topic_id == topic_id ).all()
	return results


#ForumReport
def get_forum_comments(forum):
	db = get_analytics_db()
	forum_id = _forumid.get_id( forum )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id == forum_id,
																ForumCommentsCreated.deleted == None  ).all()
	return results

def get_topics_created_for_forum(forum):
	db = get_analytics_db()
	forum_id = _forumid.get_id( forum )
	results = db.session.query(TopicsCreated).filter( TopicsCreated.forum_id == forum_id,
															TopicsCreated.deleted == None  ).all()
	return results


#CourseReport
def get_forum_comments_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id == course_id,
																ForumCommentsCreated.deleted == None  ).all()
	return results

def get_topics_created_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(TopicsCreated).filter( 	TopicsCreated.course_id == course_id,
																TopicsCreated.deleted == None  ).all()
	return results

