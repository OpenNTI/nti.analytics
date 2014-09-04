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

from sqlalchemy.schema import Sequence
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings

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

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import CommentsMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin
from nti.analytics.database.meta_mixins import RatingsMixin

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.courses import get_course_id

class ForumMixin(CourseMixin):
	@declared_attr
	def forum_id(cls):
		return Column('forum_id', Integer, ForeignKey("ForumsCreated.forum_id"), nullable=False, index=True )

class TopicMixin(ForumMixin):
	@declared_attr
	def topic_id(cls):
		return Column('topic_id', Integer, ForeignKey("TopicsCreated.topic_id"), nullable=False, index=True )


class ForumsCreated(Base,BaseTableMixin,CourseMixin,DeletedMixin):
	__tablename__ = 'ForumsCreated'
	forum_ds_id = Column('forum_ds_id', INTID_COLUMN_TYPE, nullable=True, index=True, autoincrement=False)
	forum_id = Column('forum_id', Integer, Sequence( 'forum_seq' ), index=True, nullable=False, primary_key=True )


class TopicsCreated(Base,BaseTableMixin,ForumMixin,DeletedMixin,RatingsMixin):
	__tablename__ = 'TopicsCreated'
	topic_ds_id = Column('topic_ds_id', INTID_COLUMN_TYPE, nullable=True, autoincrement=False, index=True )
	topic_id = Column('topic_id', Integer, Sequence( 'topic_seq' ), index=True, nullable=False, primary_key=True )

class ForumCommentsCreated(Base,CommentsMixin,TopicMixin,RatingsMixin):
	__tablename__ = 'ForumCommentsCreated'

	__table_args__ = (
        PrimaryKeyConstraint('comment_id'),
    )

class TopicsViewed(Base,BaseViewMixin,TopicMixin,TimeLengthMixin):
	__tablename__ = 'TopicsViewed'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'topic_id', 'timestamp'),
    )

def _get_forum( db, forum_ds_id ):
	forum = db.session.query(ForumsCreated).filter( ForumsCreated.forum_ds_id == forum_ds_id ).first()
	return forum

def _get_forum_id( db, forum_ds_id ):
	forum = _get_forum( db, forum_ds_id )
	return forum.forum_id

def _get_forum_id_from_forum( db, forum ):
	forum_ds_id = _forumid.get_id( forum )
	return _get_forum_id( db, forum_ds_id )

def _get_topic( db, topic_ds_id ):
	topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).first()
	return topic

def _get_topic_id( db, topic_ds_id ):
	topic = _get_topic( db, topic_ds_id )
	return topic.topic_id

def _get_topic_id_from_topic( db, topic ):
	topic_ds_id = _topicid.get_id( topic )
	return _get_topic_id( db, topic_ds_id )

def create_forum(user, nti_session, course, forum):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	forum_ds_id = _forumid.get_id( forum )
	course_id = get_course_id( db, course )

	timestamp = get_created_timestamp( forum )

	new_object = ForumsCreated( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								forum_ds_id=forum_ds_id )
	db.session.add( new_object )

def delete_forum(timestamp, forum_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_forum = db.session.query(ForumsCreated).filter( ForumsCreated.forum_ds_id==forum_ds_id ).one()
	db_forum.deleted=timestamp
	db_forum.forum_ds_id = None
	forum_id = db_forum.forum_id

	# Get our topics and comments
	db.session.query( TopicsCreated ).filter(
						TopicsCreated.forum_id == forum_id ).update(
							{ TopicsCreated.deleted : timestamp,
							 TopicsCreated.topic_ds_id : None } )
	db.session.query( ForumCommentsCreated ).filter(
						ForumCommentsCreated.forum_id == forum_id ).update(
							{ ForumCommentsCreated.deleted : timestamp } )
	db.session.flush()

def create_topic(user, nti_session, course, topic):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	__traceback_info__ = topic, topic.__parent__
	fid = _get_forum_id_from_forum( db, topic.__parent__ )
	topic_ds_id = _topicid.get_id( topic )
	course_id = get_course_id( db, course )

	timestamp = get_created_timestamp( topic )
	like_count, favorite_count, is_flagged = get_ratings( topic )

	new_object = TopicsCreated( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									forum_id=fid,
									topic_ds_id=topic_ds_id,
									like_count=like_count,
									favorite_count=favorite_count,
									is_flagged=is_flagged )
	db.session.add( new_object )

def delete_topic(timestamp, topic_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).one()
	db_topic.deleted = timestamp
	db_topic.topic_ds_id = None
	topic_id = db_topic.topic_id

	db.session.query( ForumCommentsCreated ).filter(
						ForumCommentsCreated.topic_id == topic_id ).update(
											{ ForumCommentsCreated.deleted : timestamp } )
	db.session.flush()

def like_topic( topic, delta ):
	db = get_analytics_db()
	topic_ds_id = _topicid.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).one()
	db_topic.like_count += delta
	db.session.flush()

def favorite_topic( topic, delta ):
	db = get_analytics_db()
	topic_ds_id = _topicid.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).one()
	db_topic.favorite_count += delta
	db.session.flush()

def flag_topic( topic, state ):
	db = get_analytics_db()
	topic_ds_id = _topicid.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).one()
	db_topic.is_flagged = state
	db.session.flush()

def create_topic_view(user, nti_session, timestamp, course, topic, time_length):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	__traceback_info__ = topic, topic.__parent__
	fid = _get_forum_id_from_forum( db, topic.__parent__ )
	did = _get_topic_id_from_topic( db, topic )
	course_id = get_course_id( db, course )
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
	fid = _get_forum_id_from_forum( db, forum )
	topic_id = _get_topic_id_from_topic( db, topic )
	cid = _commentid.get_id(comment)
	course_id = get_course_id( db, course )
	pid = None
	timestamp = get_created_timestamp( comment )
	like_count, favorite_count, is_flagged = get_ratings( comment )

	comment_length = sum( len( x ) for x in comment.body )

	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = _commentid.get_id( parent_comment )

	new_object = ForumCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										topic_id=topic_id,
										parent_id=pid,
										comment_length=comment_length,
										comment_id=cid,
										like_count=like_count,
										favorite_count=favorite_count,
										is_flagged=is_flagged )
	db.session.add( new_object )

def delete_forum_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==comment_id ).one()
	comment.deleted=timestamp
	db.session.flush()

def like_comment( comment, delta ):
	db = get_analytics_db()
	comment_id = _commentid.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id == comment_id ).one()
	db_comment.like_count += delta
	db.session.flush()

def favorite_comment( comment, delta ):
	db = get_analytics_db()
	comment_id = _commentid.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id == comment_id ).one()
	db_comment.favorite_count += delta
	db.session.flush()

def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = _commentid.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id == comment_id ).one()
	db_comment.is_flagged = state
	db.session.flush()

# StudentParticipationReport
def get_forum_comments_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = get_course_id( db, course )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.user_id == uid,
															ForumCommentsCreated.course_id == course_id,
															ForumCommentsCreated.deleted == None ).all()

	for fcc in results:
		comment = _commentid.get_object( fcc.comment_id )
		setattr( fcc, 'comment', comment )

	return results

def get_topics_created_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = get_course_id( db, course )
	results = db.session.query(TopicsCreated).filter( TopicsCreated.user_id == uid,
														TopicsCreated.course_id == course_id,
														TopicsCreated.deleted == None  ).all()

	for tc in results:
		topic = _topicid.get_object( tc.topic_id )
		setattr( tc, 'topic', topic )
	return results

#TopicReport
def get_comments_for_topic(topic ):
	db = get_analytics_db()
	topic_id = _get_topic_id_from_topic( topic )
	#FIXME null safety
	results = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.topic_id == topic_id ).all()
	return results


#ForumReport
def get_forum_comments(forum):
	db = get_analytics_db()
	forum_id = _get_forum_id_from_forum( db, forum )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.forum_id == forum_id,
																ForumCommentsCreated.deleted == None  ).all()
	return results

def get_topics_created_for_forum(forum):
	db = get_analytics_db()
	forum_id = _get_forum_id_from_forum( db, forum )
	results = db.session.query(TopicsCreated).filter( TopicsCreated.forum_id == forum_id,
													TopicsCreated.deleted == None  ).all()
	return results


#CourseReport
def get_forum_comments_for_course(course):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query(ForumCommentsCreated).filter( 	ForumCommentsCreated.course_id == course_id,
																ForumCommentsCreated.deleted == None  ).all()
	return results

def get_topics_created_for_course(course):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query(TopicsCreated).filter( 	TopicsCreated.course_id == course_id,
																TopicsCreated.deleted == None  ).all()
	return results

