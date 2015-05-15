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

from sqlalchemy.orm.session import make_transient

from sqlalchemy.schema import Sequence
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_creator
from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings

from nti.analytics.read_models import AnalyticsForumComment
from nti.analytics.read_models import AnalyticsTopic
from nti.analytics.read_models import AnalyticsTopicView

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CommentId
from nti.analytics.identifier import ForumId
from nti.analytics.identifier import TopicId

from nti.analytics.database import resolve_objects
from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import CommentsMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin
from nti.analytics.database.meta_mixins import RatingsMixin
from nti.analytics.database.meta_mixins import CreatorMixin

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user
from nti.analytics.database.users import get_user_db_id
from nti.analytics.database.root_context import get_root_context_id
from nti.analytics.database.root_context import get_root_context

from nti.analytics.database._utils import resolve_like
from nti.analytics.database._utils import resolve_favorite
from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_filtered_records
from nti.analytics.database._utils import get_ratings_for_user_objects
from nti.analytics.database._utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database._utils import get_user_replies_to_others as _get_user_replies_to_others

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

class TopicRatingMixin(CreatorMixin, CourseMixin):
	@declared_attr
	def topic_id(cls):
		return Column('topic_id', Integer, ForeignKey("TopicsCreated.topic_id"), nullable=False, index=True )

class TopicFavorites(Base,BaseTableMixin,TopicRatingMixin):
	__tablename__ = 'TopicFavorites'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'topic_id'),
    )

class TopicLikes(Base,BaseTableMixin,TopicRatingMixin):
	__tablename__ = 'TopicLikes'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'topic_id'),
    )

class ForumCommentMixin(object):

	@declared_attr
	def comment_id(cls):
		return Column('comment_id', INTID_COLUMN_TYPE, ForeignKey("ForumCommentsCreated.comment_id"), nullable=False, index=True)


class ForumCommentFavorites(Base,BaseTableMixin,ForumCommentMixin,CreatorMixin,CourseMixin):
	__tablename__ = 'ForumCommentFavorites'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'comment_id'),
    )

class ForumCommentLikes(Base,BaseTableMixin,ForumCommentMixin,CreatorMixin,CourseMixin):
	__tablename__ = 'ForumCommentLikes'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'comment_id'),
    )

def _get_forum( db, forum_ds_id ):
	forum = db.session.query(ForumsCreated).filter( ForumsCreated.forum_ds_id == forum_ds_id ).first()
	return forum

def _get_forum_id( db, forum_ds_id ):
	forum = _get_forum( db, forum_ds_id )
	return forum and forum.forum_id

_forum_exists = _get_forum_id

def _get_forum_id_from_forum( db, forum ):
	forum_ds_id = ForumId.get_id( forum )
	return _get_forum_id( db, forum_ds_id )

def _get_topic( db, topic_ds_id ):
	topic = db.session.query(TopicsCreated).filter(
							TopicsCreated.topic_ds_id == topic_ds_id ).first()
	return topic

def _get_topic_id( db, topic_ds_id ):
	topic = _get_topic( db, topic_ds_id )
	return topic and topic.topic_id

_topic_exists = _get_topic_id

def _get_topic_id_from_topic( db, topic ):
	topic_ds_id = TopicId.get_id( topic )
	return _get_topic_id( db, topic_ds_id )

def _get_topic_from_db_id( topic_id ):
	"Return the actual topic object represented by the given db id."
	db = get_analytics_db()
	topic = db.session.query(TopicsCreated).filter(
							TopicsCreated.topic_id == topic_id ).first()
	topic = TopicId.get_object( topic.topic_ds_id )
	return topic

def create_forum(user, nti_session, course, forum):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	forum_ds_id = ForumId.get_id( forum )

	if _forum_exists( db, forum_ds_id ):
		logger.warn( 'Forum already exists (ds_id=%s) (user=%s)', forum_ds_id, user )
		return

	course_id = get_root_context_id( db, course, create=True )

	timestamp = get_created_timestamp( forum )

	new_object = ForumsCreated( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								forum_ds_id=forum_ds_id )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def delete_forum(timestamp, forum_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_forum = db.session.query(ForumsCreated).filter( ForumsCreated.forum_ds_id==forum_ds_id ).first()
	if db_forum is None:
		# This only occurs in tests (e.g nti.app.products.ou) when tearing down layers.
		# Not really much we can do about it anyway; so log and forget.
		# Could also happen with race conditions (the forum was never created in db).
		logger.info( 'Attempted to delete forum (%s) that does not exist', forum_ds_id )
		return

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
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	__traceback_info__ = topic, topic.__parent__
	topic_ds_id = TopicId.get_id( topic )

	if _topic_exists( db, topic_ds_id ):
		logger.warn( 'Topic already exists (ds_id=%s) (user=%s)',
					topic_ds_id, user )
		return

	fid = _get_forum_id_from_forum( db, topic.__parent__ )

	if not fid:
		# Ok, create our forum.
		forum = topic.__parent__
		forum_creator = get_creator( forum )
		new_forum = create_forum( forum_creator, None, course, forum )
		logger.info( 'Created forum (forum=%s) (user=%s) (course=%s)',
					forum, forum_creator, course )
		fid = new_forum.forum_id

	course_id = get_root_context_id( db, course, create=True )

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
	db.session.flush()
	return new_object

def delete_topic(timestamp, topic_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_topic = db.session.query(TopicsCreated).filter( TopicsCreated.topic_ds_id == topic_ds_id ).first()
	if db_topic is None:
		logger.info( 'Attempted to delete topic (%s) that does not exist', topic_ds_id )
		return

	db_topic.deleted = timestamp
	db_topic.topic_ds_id = None
	topic_id = db_topic.topic_id

	db.session.query( ForumCommentsCreated ).filter(
						ForumCommentsCreated.topic_id == topic_id ).update(
											{ ForumCommentsCreated.deleted : timestamp } )
	db.session.flush()

def _get_topic_rating_record( db, table, user_id, topic_id ):
	topic_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.topic_id == topic_id ).first()
	return topic_rating_record

def _create_topic_rating_record( db, table, user, session_id, timestamp, topic_id, delta, creator_id, course_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )
		user_id = user_record.user_id

		topic_rating_record = _get_topic_rating_record( db, table,
													user_id, topic_id )

		if not topic_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			topic_rating_record = table( topic_id=topic_id,
								user_id=user_id,
								timestamp=timestamp,
								session_id=session_id,
								creator_id=creator_id,
								course_id=course_id )
			db.session.add( topic_rating_record )
		elif topic_rating_record and delta < 0:
			# Delete
			db.session.delete( topic_rating_record )
		db.session.flush()

def like_topic( topic, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	topic_ds_id = TopicId.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()

	if db_topic is not None:
		db_topic.like_count += delta
		db.session.flush()
		topic_id = db_topic.topic_id
		creator_id = db_topic.user_id
		course_id = db_topic.course_id
		_create_topic_rating_record( db, TopicLikes, user,
								session_id, timestamp, topic_id, delta,
								creator_id, course_id )

def favorite_topic( topic, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	topic_ds_id = TopicId.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()

	if db_topic is not None:
		db_topic.favorite_count += delta
		db.session.flush()
		topic_id = db_topic.topic_id
		creator_id = db_topic.user_id
		course_id = db_topic.course_id
		_create_topic_rating_record( db, TopicFavorites, user,
								session_id, timestamp, topic_id, delta,
								creator_id, course_id )

def flag_topic( topic, state ):
	db = get_analytics_db()
	topic_ds_id = TopicId.get_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()
	db_topic.is_flagged = state
	db.session.flush()


def _topic_view_exists( db, user_id, topic_id, timestamp ):
	return db.session.query( TopicsViewed ).filter(
							TopicsViewed.user_id == user_id,
							TopicsViewed.topic_id == topic_id,
							TopicsViewed.timestamp == timestamp ).first()

def create_topic_view(user, nti_session, timestamp, course, context_path, topic, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	__traceback_info__ = topic, topic.__parent__
	did = _get_topic_id_from_topic( db, topic )

	if not did:
		# Create our topic (and forum) if necessary.
		topic_creator = get_creator( topic )
		new_topic = create_topic( topic_creator, None, course, topic )
		logger.info( 'Created topic (topic=%s) (user=%s) (course=%s)',
					topic, topic_creator, course )
		did = new_topic.topic_id

	fid = _get_forum_id_from_forum( db, topic.__parent__ )

	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	existing_record = _topic_view_exists( db, uid, did, timestamp )

	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			return
		else:
			logger.warn( 'Topic view already exists (user=%s) (topic=%s)',
						user, did )
			return

	context_path = get_context_path( context_path )

	new_object = TopicsViewed( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								context_path=context_path,
								forum_id=fid,
								topic_id=did,
								time_length=time_length )
	db.session.add( new_object )

def _comment_exists( db, comment_id ):
	return db.session.query( ForumCommentsCreated ).filter(
							ForumCommentsCreated.comment_id == comment_id ).count()

def create_forum_comment(user, nti_session, course, topic, comment):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	forum = topic.__parent__
	topic_id = _get_topic_id_from_topic( db, topic )
	cid = CommentId.get_id(comment)

	if not topic_id:
		# Create our topic (and forum) if necessary.
		topic_creator = get_creator( topic )
		new_topic = create_topic( topic_creator, None, course, topic )
		logger.info( 'Created topic (topic=%s) (user=%s) (course=%s)',
					topic, topic_creator, course )
		topic_id = new_topic.topic_id

	fid = _get_forum_id_from_forum( db, forum )

	if _comment_exists( db, cid ):
		logger.warn( 'Forum comment already exists (user=%s) (comment_id=%s)',
					user, cid )
		return

	course_id = get_root_context_id( db, course, create=True )
	pid = parent_user_id = None
	timestamp = get_created_timestamp( comment )
	like_count, favorite_count, is_flagged = get_ratings( comment )

	comment_length = sum( len( x ) for x in comment.body )

	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = CommentId.get_id( parent_comment )
		parent_creator = get_creator( parent_comment )
		parent_user_record = get_or_create_user( parent_creator )
		parent_user_id = parent_user_record.user_id

	new_object = ForumCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										forum_id=fid,
										topic_id=topic_id,
										parent_id=pid,
										parent_user_id=parent_user_id,
										comment_length=comment_length,
										comment_id=cid,
										like_count=like_count,
										favorite_count=favorite_count,
										is_flagged=is_flagged )
	db.session.add( new_object )
	return new_object

def delete_forum_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(ForumCommentsCreated).filter( ForumCommentsCreated.comment_id==comment_id ).first()
	if not comment:
		logger.info( 'Comment never created (%s)', comment_id )
		return
	comment.deleted=timestamp
	db.session.flush()

def _get_comment_rating_record( db, table, user_id, comment_id ):
	comment_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.comment_id == comment_id ).first()
	return comment_rating_record

def _create_forum_comment_rating_record( db, table, user, session_id, timestamp, comment_id, delta, creator_id, course_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )
		user_id = user_record.user_id

		comment_rating_record = _get_comment_rating_record( db, table,
														user_id, comment_id )

		if not comment_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			comment_rating_record = table( comment_id=comment_id,
								user_id=user_id,
								timestamp=timestamp,
								session_id=session_id,
								creator_id=creator_id,
								course_id=course_id )
			db.session.add( comment_rating_record )
		elif comment_rating_record and delta < 0:
			# Delete
			db.session.delete( comment_rating_record )
		db.session.flush()

def like_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()

	if db_comment is not None:
		db_comment.like_count += delta
		db.session.flush()
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		course_id = db_comment.course_id
		_create_forum_comment_rating_record( db, ForumCommentLikes, user,
								session_id, timestamp, comment_id, delta,
								creator_id, course_id )

def favorite_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()

	if db_comment is not None:
		db_comment.favorite_count += delta
		db.session.flush()
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		course_id = db_comment.course_id
		_create_forum_comment_rating_record( db, ForumCommentFavorites, user,
								session_id, timestamp, comment_id, delta,
								creator_id, course_id )

def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()
	db_comment.is_flagged = state
	db.session.flush()

def _resolve_comment( row, user=None, course=None ):
	# Detach this from the db, resolving objects as we go.
	make_transient( row )
	comment = CommentId.get_object( row.comment_id )
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user
	is_reply = row.parent_id is not None
	result = None

	if 		comment is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsForumComment( Comment=comment,
								user=user,
								CommentLength=row.comment_length,
								timestamp=row.timestamp,
								Flagged=row.is_flagged,
								LikeCount=row.like_count,
								FavoriteCount=row.favorite_count,
								RootContext=course,
								IsReply=is_reply )
	return result

def _resolve_topic( row, user=None, course=None ):
	make_transient( row )
	topic = TopicId.get_object( row.topic_ds_id )
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user
	result = None

	if 		topic is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsTopic( Topic=topic,
								user=user,
								timestamp=row.timestamp,
								RootContext=course )
	return result

def _resolve_topic_view( row, topic=None, user=None, course=None ):
	make_transient( row )
	topic = _get_topic_from_db_id( row.topic_id ) if topic is None else topic
	course = get_root_context( row.course_id ) if course is None else course
	user = get_user( row.user_id ) if user is None else user
	result = None

	if 		topic is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsTopicView( Topic=topic,
								user=user,
								timestamp=row.timestamp,
								RootContext=course,
								Duration=row.time_length )
	return result

def get_forum_comments_for_user( user, course=None, timestamp=None, get_deleted=False, top_level_only=False ):
	"""
	Fetch any comments for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted, or whether the comment is top-level.
	"""
	filters = []
	if not get_deleted:
		filters.append( ForumCommentsCreated.deleted == None )

	if top_level_only:
		filters.append( ForumCommentsCreated.parent_id == None )

	results = get_filtered_records( user, ForumCommentsCreated, course=course,
								timestamp=timestamp, filters=filters )
	return resolve_objects( _resolve_comment, results, user=user, course=course )

def get_topics_created_for_user( user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any topics for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = []
	if not get_deleted:
		filters.append( ForumCommentsCreated.deleted == None )

	results = get_filtered_records( user, TopicsCreated, course=course,
								timestamp=timestamp, filters=filters )

	return resolve_objects( _resolve_topic, results )

def get_topic_views( user, topic ):
	db = get_analytics_db()
	uid = get_user_db_id( user )
	topic_id = _get_topic_id_from_topic( db, topic )
	results = db.session.query(TopicsViewed).filter(
								TopicsViewed.user_id == uid,
								TopicsViewed.topic_id == topic_id ).all()

	return resolve_objects( _resolve_topic_view, results, topic=topic )

def get_comments_for_topic( topic ):
	db = get_analytics_db()
	topic_id = _get_topic_id_from_topic( db, topic )
	results = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.topic_id == topic_id,
								ForumCommentsCreated.deleted == None ).all()
	return resolve_objects( _resolve_comment, results )


def get_forum_comments( forum ):
	db = get_analytics_db()
	forum_id = _get_forum_id_from_forum( db, forum )
	results = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.forum_id == forum_id,
								ForumCommentsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_comment, results )

def get_topics_created_for_forum( forum ):
	db = get_analytics_db()
	forum_id = _get_forum_id_from_forum( db, forum )
	results = db.session.query(TopicsCreated).filter(
								TopicsCreated.forum_id == forum_id,
								TopicsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_topic, results )


# CourseReport
def get_forum_comments_for_course( course ):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.course_id == course_id,
								ForumCommentsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_comment, results, course=course )

def get_topics_created_for_course( course ):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(TopicsCreated).filter(
								TopicsCreated.course_id == course_id,
								TopicsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_topic, results, course=course )


def get_topic_view_count( topic ):
	"""
	Return the number of times this topic has been viewed.
	"""
	result = 0
	db = get_analytics_db()
	topic_id = _get_topic_id_from_topic( db, topic )
	if topic_id is not None:
		result = db.session.query(TopicsViewed).filter(
									TopicsViewed.topic_id == topic_id,
									TopicsViewed.time_length > 0 ).count()
	return result

def get_user_replies_to_others( user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	results = _get_user_replies_to_others( ForumCommentsCreated, user, course, timestamp, get_deleted )
	return resolve_objects( _resolve_comment, results, user=user, course=course )

def get_replies_to_user( user, course=None, timestamp=None, get_deleted=False  ):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	results = _get_replies_to_user( ForumCommentsCreated, user, course, timestamp, get_deleted )
	return resolve_objects( _resolve_comment, results, course=course )

def get_likes_for_users_topics( user, course=None, timestamp=None ):
	"""
	Fetch any likes created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( TopicLikes, user, course, timestamp )
	return resolve_objects( resolve_like, results, obj_creator=user)

def get_favorites_for_users_topics( user, course=None, timestamp=None ):
	"""
	Fetch any favorites created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( TopicFavorites, user, course, timestamp )
	return resolve_objects( resolve_favorite, results, obj_creator=user)

def get_likes_for_users_comments( user, course=None, timestamp=None ):
	"""
	Fetch any likes created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( ForumCommentLikes, user, course, timestamp )
	return resolve_objects( resolve_like, results, obj_creator=user)

def get_favorites_for_users_comments( user, course=None, timestamp=None ):
	"""
	Fetch any favorites created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( ForumCommentFavorites, user, course, timestamp )
	return resolve_objects( resolve_favorite, results, obj_creator=user)
