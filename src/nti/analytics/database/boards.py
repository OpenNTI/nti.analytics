#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import func

from nti.analytics_database.boards import TopicLikes
from nti.analytics_database.boards import TopicsViewed
from nti.analytics_database.boards import ForumsCreated
from nti.analytics_database.boards import TopicsCreated
from nti.analytics_database.boards import TopicFavorites
from nti.analytics_database.boards import ForumCommentLikes
from nti.analytics_database.boards import ForumCommentsCreated
from nti.analytics_database.boards import ForumCommentFavorites
from nti.analytics_database.boards import ForumCommentsUserFileUploadMimeTypes

from nti.dataserver.interfaces import IEntity

from nti.analytics.common import get_course
from nti.analytics.common import get_creator
from nti.analytics.common import get_ratings
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_object_root
from nti.analytics.common import get_created_timestamp

from nti.analytics.identifier import get_ds_id
from nti.analytics.identifier import get_ds_object

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_body_text_length
from nti.analytics.database._utils import get_root_context_ids

from nti.analytics.database.mime_types import build_mime_type_records

from nti.analytics.database.query_utils import resolve_like
from nti.analytics.database.query_utils import resolve_favorite
from nti.analytics.database.query_utils import get_filtered_records
from nti.analytics.database.query_utils import get_ratings_for_user_objects
from nti.analytics.database.query_utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database.query_utils import get_user_replies_to_others as _get_user_replies_to_others

from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user_db_id

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

def _get_root_context_ids( obj ):
	"""
	For the given object, return the root context ids (tuple of context_id/entity_context_id),
	creating records if needed.
	"""
	root_context = get_course( obj )
	if root_context is None:
		root_context = get_object_root( obj, IEntity )
	return get_root_context_ids( root_context )

def _get_forum( db, forum_ds_id ):
	forum = db.session.query(ForumsCreated).filter(
							 ForumsCreated.forum_ds_id == forum_ds_id ).first()
	return forum

def _get_forum_id( db, forum_ds_id ):
	forum = _get_forum( db, forum_ds_id )
	return forum and forum.forum_id

_forum_exists = _get_forum_id

def _get_forum_id_from_forum( db, forum ):
	forum_ds_id = get_ds_id( forum )
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
	topic_ds_id = get_ds_id( topic )
	return _get_topic_id( db, topic_ds_id )

def _get_topic_from_db_id( topic_id ):
	"Return the actual topic object represented by the given db id."
	db = get_analytics_db()
	topic = db.session.query(TopicsCreated).filter(
							 TopicsCreated.topic_id == topic_id ).first()
	topic = get_ds_object( topic.topic_ds_id )
	return topic

def create_forum(user, nti_session, forum):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	forum_ds_id = get_ds_id( forum )

	if _forum_exists( db, forum_ds_id ):
		logger.warn( 'Forum already exists (ds_id=%s) (user=%s)', forum_ds_id, user )
		return

	course_id, entity_root_context_id = _get_root_context_ids( forum )

	timestamp = get_created_timestamp( forum )

	new_object = ForumsCreated( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								entity_root_context_id=entity_root_context_id,
								forum_ds_id=forum_ds_id )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def delete_forum(timestamp, forum_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_forum = db.session.query(ForumsCreated).filter(
								ForumsCreated.forum_ds_id==forum_ds_id ).first()
	if db_forum is None:
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

def _set_topic_attributes( topic_record, topic ):
	"""
	Set the topic attributes for this topic record.
	"""
	like_count, favorite_count, is_flagged = get_ratings(topic)
	topic_record.like_count = like_count
	topic_record.favorite_count = favorite_count
	topic_record.is_flagged = is_flagged

def create_topic(user, nti_session, topic):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	__traceback_info__ = topic, topic.__parent__
	topic_ds_id = get_ds_id( topic )

	if _topic_exists( db, topic_ds_id ):
		logger.warn( 'Topic already exists (ds_id=%s) (user=%s)',
					topic_ds_id, user )
		return

	fid = _get_forum_id_from_forum( db, topic.__parent__ )
	forum = topic.__parent__

	if not fid:
		# Ok, create our forum.
		forum_creator = get_creator( forum )
		new_forum = create_forum( forum_creator, None, forum )
		logger.info( 'Created forum (forum=%s) (user=%s)',
					forum, forum_creator )
		fid = new_forum.forum_id

	course_id, entity_root_context_id = _get_root_context_ids( forum )

	timestamp = get_created_timestamp( topic )

	new_object = TopicsCreated( user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id,
								entity_root_context_id=entity_root_context_id,
								forum_id=fid,
								topic_ds_id=topic_ds_id )
	_set_topic_attributes( new_object, topic )
	db.session.add( new_object )
	db.session.flush()
	# We manually roll our headline into the comments table (same in blogs),
	# since these objects are not broadcast. This may make it difficult to
	# get topic/headline stats only without accessing the ds, and it will
	# be difficult to get non-headline comment data only.
	if getattr( topic, 'headline', None ) is not None:
		create_forum_comment(user, nti_session, topic, topic.headline)
	return new_object

def update_topic(user, nti_session, topic):
	"""
	Update our topic, creating if it does not exist.
	"""
	db = get_analytics_db()
	topic_ds_id = get_ds_id( topic )
	topic_record = _get_topic( db, topic_ds_id )
	if topic_record is None:
		create_topic(user, nti_session, topic)
	else:
		_set_topic_attributes( topic_record, topic )

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

def _create_topic_rating_record( db, table, user, session_id, timestamp, topic_id, delta, creator_id, course_id, entity_root_context_id ):
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
								course_id=course_id,
								entity_root_context_id=entity_root_context_id )
			db.session.add( topic_rating_record )
		elif topic_rating_record and delta < 0:
			# Delete
			db.session.delete( topic_rating_record )
		db.session.flush()

def like_topic( topic, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	topic_ds_id = get_ds_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()

	if db_topic is not None:
		db.session.flush()
		topic_id = db_topic.topic_id
		creator_id = db_topic.user_id
		course_id = db_topic.course_id
		_set_topic_attributes( db_topic, topic )
		entity_root_context_id = db_topic.entity_root_context_id
		_create_topic_rating_record( db, TopicLikes, user,
									session_id, timestamp, topic_id, delta,
									creator_id, course_id, entity_root_context_id )

def favorite_topic( topic, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	topic_ds_id = get_ds_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()

	if db_topic is not None:
		db.session.flush()
		topic_id = db_topic.topic_id
		creator_id = db_topic.user_id
		course_id = db_topic.course_id
		_set_topic_attributes( db_topic, topic )
		entity_root_context_id = db_topic.entity_root_context_id
		_create_topic_rating_record( db, TopicFavorites, user,
								session_id, timestamp, topic_id, delta,
								creator_id, course_id, entity_root_context_id )

def flag_topic( topic, state ):
	db = get_analytics_db()
	topic_ds_id = get_ds_id( topic )
	db_topic = db.session.query(TopicsCreated).filter(
								TopicsCreated.topic_ds_id == topic_ds_id ).first()
	db_topic.is_flagged = state
	db.session.flush()

def _topic_view_exists( db, user_id, topic_id, timestamp ):
	return db.session.query(TopicsViewed ).filter(
							TopicsViewed.user_id == user_id,
							TopicsViewed.topic_id == topic_id,
							TopicsViewed.timestamp == timestamp ).first()

def create_topic_view(user, nti_session, timestamp, root_context, context_path, topic, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	__traceback_info__ = topic, topic.__parent__
	did = _get_topic_id_from_topic( db, topic )

	if not did:
		# Create our topic (and forum) if necessary.
		topic_creator = get_creator( topic )
		new_topic = create_topic( topic_creator, None, topic )
		logger.info( 'Created topic (topic=%s) (user=%s)',
					topic, topic_creator )
		did = new_topic.topic_id

	fid = _get_forum_id_from_forum( db, topic.__parent__ )

	course_id, entity_root_context_id = get_root_context_ids( root_context )
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
								entity_root_context_id=entity_root_context_id,
								context_path=context_path,
								forum_id=fid,
								topic_id=did,
								time_length=time_length )
	db.session.add( new_object )

def _get_comment( db, comment_id ):
	comment = db.session.query( ForumCommentsCreated ).filter(
							 	ForumCommentsCreated.comment_id == comment_id ).first()
	return comment

def _comment_exists( db, comment_id ):
	comment = _get_comment( db, comment_id )
	return comment is not None

def _set_mime_records( db, comment_record, comment ):
	"""
	Set the mime type records for our obj, removing any
	previous records present.
	"""
	# Delete the old records.
	for mime_record in comment_record._file_mime_types:
		db.session.delete( mime_record )
	comment_record._file_mime_types = []

	file_mime_types = build_mime_type_records( db, comment, ForumCommentsUserFileUploadMimeTypes )
	comment_record._file_mime_types.extend( file_mime_types )

def _set_comment_attributes( db, comment_record, comment ):
	"""
	Set the comment attributes for this comment record.
	"""
	like_count, favorite_count, is_flagged = get_ratings(comment)
	comment_record.like_count = like_count
	comment_record.favorite_count = favorite_count
	comment_record.is_flagged = is_flagged
	comment_record.comment_length = get_body_text_length( comment )
	_set_mime_records( db, comment_record, comment )

def create_forum_comment(user, nti_session, topic, comment):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	forum = topic.__parent__
	topic_id = _get_topic_id_from_topic( db, topic )
	cid = get_ds_id(comment)

	if not topic_id:
		# Create our topic (and forum) if necessary.
		topic_creator = get_creator( topic )
		new_topic = create_topic( topic_creator, None, topic )
		logger.info( 'Created topic (topic=%s) (user=%s)',
					topic, topic_creator )
		topic_id = new_topic.topic_id

	fid = _get_forum_id_from_forum( db, forum )

	if _comment_exists( db, cid ):
		logger.warn( 'Forum comment already exists (user=%s) (comment_id=%s)',
					user, cid )
		return

	course_id, entity_root_context_id = _get_root_context_ids( forum )
	pid = parent_user_id = None
	timestamp = get_created_timestamp( comment )

	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = get_ds_id( parent_comment )
		parent_creator = get_creator( parent_comment )
		parent_user_record = get_or_create_user( parent_creator )
		parent_user_id = parent_user_record.user_id

	new_object = ForumCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										entity_root_context_id=entity_root_context_id,
										forum_id=fid,
										topic_id=topic_id,
										parent_id=pid,
										parent_user_id=parent_user_id,
										comment_id=cid )
	_set_comment_attributes( db, new_object, comment )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def update_comment(user, nti_session, topic, comment):
	"""
	Update our comment, creating if it does not exist.
	"""
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	comment_record = _get_comment( db, comment_id )
	if comment_record is None:
		create_forum_comment(user, nti_session, topic, comment)
	else:
		_set_comment_attributes( db, comment_record, comment )

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

def _create_forum_comment_rating_record( db, table, user, session_id, timestamp, comment_id, delta, creator_id, course_id, entity_root_context_id ):
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
								course_id=course_id,
								entity_root_context_id=entity_root_context_id )
			db.session.add( comment_rating_record )
		elif comment_rating_record and delta < 0:
			# Delete
			db.session.delete( comment_rating_record )
		db.session.flush()

def like_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()

	if db_comment is not None:
		db.session.flush()
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		course_id = db_comment.course_id
		_set_comment_attributes( db, db_comment, comment )
		entity_root_context_id = db_comment.entity_root_context_id
		_create_forum_comment_rating_record( db, ForumCommentLikes, user,
								session_id, timestamp, comment_id, delta,
								creator_id, course_id, entity_root_context_id )

def favorite_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()

	if db_comment is not None:
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		course_id = db_comment.course_id
		_set_comment_attributes( db, db_comment, comment )
		entity_root_context_id = db_comment.entity_root_context_id
		_create_forum_comment_rating_record( db, ForumCommentFavorites, user,
								session_id, timestamp, comment_id, delta,
								creator_id, course_id, entity_root_context_id )

def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.comment_id == comment_id ).one()
	db_comment.is_flagged = state
	db.session.flush()

def _resolve_comment( row, user=None, course=None, parent_user=None ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	if parent_user is not None:
		row.RepliedToUser = parent_user
	return row

def _resolve_topic( row, user=None, course=None ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row

def _resolve_topic_view( row, topic=None, user=None, course=None ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	if topic is not None:
		row.Topic = topic
	return row

def get_forum_comments_for_user( user=None, course=None,
						get_deleted=False, top_level_only=False,
						replies_only=False, **kwargs ):
	"""
	Fetch any comments for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted, or whether the comment is top-level.
	"""
	filters = []
	if replies_only and top_level_only:
		return ()

	if not get_deleted:
		filters.append( ForumCommentsCreated.deleted == None )

	if top_level_only:
		filters.append( ForumCommentsCreated.parent_id == None )

	results = get_filtered_records( user, ForumCommentsCreated, course=course,
								replies_only=replies_only, filters=filters, **kwargs )
	return resolve_objects( _resolve_comment, results, user=user, course=course )

get_forum_comments = get_forum_comments_for_user

def get_topics_created_for_user( user, course=None, get_deleted=False, **kwargs ):
	"""
	Fetch any topics for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	filters = []
	if not get_deleted:
		filters.append( TopicsCreated.deleted == None )

	results = get_filtered_records( user, TopicsCreated, course=course,
								filters=filters, **kwargs )

	return resolve_objects( _resolve_topic, results, course=course )

def get_topic_views( user=None, topic=None, course=None, **kwargs ):

	filters = []
	if topic is not None:
		db = get_analytics_db()
		topic_id = _get_topic_id_from_topic( db, topic )
		filters.append( TopicsViewed.topic_id == topic_id )

	results = get_filtered_records( user, TopicsViewed, course=course,
								filters=filters, **kwargs )
	return resolve_objects( _resolve_topic_view, results, user=user, topic=topic, course=course )

def get_topic_last_view( topic, user ):
	db = get_analytics_db()
	topic_id = _get_topic_id_from_topic( db, topic )
	user_id = get_user_db_id( user )
	result = db.session.query( func.max( TopicsViewed.timestamp )  ).filter(
										TopicsViewed.topic_id == topic_id,
										TopicsViewed.user_id == user_id ).one()
	return result and result[0]

def get_comments_for_topic( topic ):
	db = get_analytics_db()
	topic_id = _get_topic_id_from_topic( db, topic )
	results = db.session.query(ForumCommentsCreated).filter(
								ForumCommentsCreated.topic_id == topic_id,
								ForumCommentsCreated.deleted == None ).all()
	return resolve_objects( _resolve_comment, results )


def get_comments_for_forum( forum ):
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

def get_topics_created_for_course( course ):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	results = db.session.query(TopicsCreated).filter(
								TopicsCreated.course_id == course_id,
								TopicsCreated.deleted == None  ).all()
	return resolve_objects( _resolve_topic, results, course=course )

def get_user_replies_to_others( user, course=None, topic=None, **kwargs ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	filters = None
	if topic is not None:
		db = get_analytics_db()
		topic_id = _get_topic_id_from_topic( db, topic )
		if topic_id is not None:
			filters = ( ForumCommentsCreated.topic_id == topic_id, )
		else:
			return ()
	results = _get_user_replies_to_others( ForumCommentsCreated, user, course,
										filters=filters, **kwargs )
	return resolve_objects( _resolve_comment, results, user=user, course=course )

def get_replies_to_user( user, course=None, **kwargs  ):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	results = _get_replies_to_user( ForumCommentsCreated, user, **kwargs )
	return resolve_objects( _resolve_comment, results, course=course, parent_user=user )

def get_likes_for_users_topics( user, **kwargs ):
	"""
	Fetch any likes created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( TopicLikes, user, **kwargs )
	return resolve_objects( resolve_like, results, obj_creator=user)

def get_favorites_for_users_topics( user, **kwargs ):
	"""
	Fetch any favorites created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( TopicFavorites, user, **kwargs )
	return resolve_objects( resolve_favorite, results, obj_creator=user)

def get_likes_for_users_comments( user, **kwargs ):
	"""
	Fetch any likes created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( ForumCommentLikes, user, **kwargs)
	return resolve_objects( resolve_like, results, obj_creator=user)

def get_favorites_for_users_comments( user, **kwargs ):
	"""
	Fetch any favorites created for a user's topics *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_ratings_for_user_objects( ForumCommentFavorites, user, **kwargs )
	return resolve_objects( resolve_favorite, results, obj_creator=user)
