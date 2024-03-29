#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.blogs import BlogLikes
from nti.analytics_database.blogs import BlogsViewed
from nti.analytics_database.blogs import BlogsCreated
from nti.analytics_database.blogs import BlogFavorites
from nti.analytics_database.blogs import BlogCommentLikes
from nti.analytics_database.blogs import BlogCommentsCreated
from nti.analytics_database.blogs import BlogCommentFavorites
from nti.analytics_database.blogs import BlogCommentsUserFileUploadMimeTypes

from nti.analytics.common import get_creator
from nti.analytics.common import get_ratings
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_created_timestamp

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_body_text_length

from nti.analytics.database.mime_types import build_mime_type_records

from nti.analytics.database.query_utils import resolve_like
from nti.analytics.database.query_utils import resolve_favorite
from nti.analytics.database.query_utils import get_filtered_records
from nti.analytics.database.query_utils import get_ratings_for_user_objects
from nti.analytics.database.query_utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database.query_utils import get_user_replies_to_others as _get_user_replies_to_others

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import get_ds_id

logger = __import__('logging').getLogger(__name__)


def _get_blog(db, blog_ds_id):
	blog = db.session.query(BlogsCreated).filter(
							BlogsCreated.blog_ds_id == blog_ds_id).first()
	return blog


def _get_blog_id( db, blog_ds_id ):
	blog = _get_blog( db, blog_ds_id )
	return blog and blog.blog_id

_blog_exists = _get_blog_id


def _set_blog_attributes(blog_record, blog):
	"""
	Set the blog attributes for this blog record.
	"""
	blog_length = 0
	try:
		if blog.description is not None:
			blog_length = len(blog.description)
	except AttributeError:
		blog_length = get_body_text_length( blog )
	like_count, favorite_count, is_flagged = get_ratings( blog )
	blog_record.like_count = like_count
	blog_record.favorite_count = favorite_count
	blog_record.is_flagged = is_flagged
	blog_record.blog_length = blog_length


def create_blog(user, nti_session, blog_entry):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	blog_ds_id = get_ds_id( blog_entry )

	if _blog_exists(db, blog_ds_id):
		logger.warn('Blog already exists (blog_id=%s) (user=%s)', blog_ds_id, user)
		return

	timestamp = get_created_timestamp( blog_entry )

	new_object = BlogsCreated(session_id=sid,
							  timestamp=timestamp,
							  blog_ds_id=blog_ds_id )
	new_object._user_record = user_record
	_set_blog_attributes(new_object, blog_entry)
	db.session.add( new_object )
	# See .boards.py
	if getattr( blog_entry, 'headline', None ) is not None:
		create_blog_comment(user, nti_session, blog_entry, blog_entry.headline )
	return new_object


def update_blog(user, nti_session, blog):
	"""
	Update our blog, creating if it does not exist.
	"""
	db = get_analytics_db()
	blog_ds_id = get_ds_id(blog)
	blog_record = _get_blog( db, blog_ds_id )
	if blog_record is None:
		create_blog(user, nti_session, blog)
	else:
		_set_blog_attributes( blog_record, blog )


def delete_blog( timestamp, blog_ds_id ):
	db = get_analytics_db()
	blog = db.session.query(BlogsCreated).filter(
									BlogsCreated.blog_ds_id == blog_ds_id ).first()
	if not blog:
		logger.info( 'Blog never created (%s)', blog_ds_id )
		return
	blog.deleted = timestamp
	blog.blog_ds_id = None
	blog_id = blog.blog_id

	db.session.query(BlogCommentsCreated ).filter(
					 BlogCommentsCreated.blog_id == blog_id ).update(
									{BlogCommentsCreated.deleted : timestamp})


def _get_blog_rating_record( db, table, user_record, blog_id ):
	blog_rating_record = db.session.query( table ).filter(
									table.user_id == user_record.user_id,
									table.blog_id == blog_id ).first()
	return blog_rating_record


def _create_blog_rating_record( db, table, user, session_id, timestamp, blog_id, delta, creator_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user(user)
		blog_rating_record = _get_blog_rating_record(db, table,
													 user_record, blog_id)

		if not blog_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type(timestamp)
			blog_rating_record = table(blog_id=blog_id,
									   timestamp=timestamp,
									   session_id=session_id,
									   creator_id=creator_id)
			blog_rating_record._user_record = user_record
			db.session.add( blog_rating_record )
		elif blog_rating_record and delta < 0:
			# Delete
			db.session.delete( blog_rating_record )


def like_blog( blog, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	blog_ds_id = get_ds_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
								BlogsCreated.blog_ds_id == blog_ds_id).first()

	if db_blog is not None:
		creator_id = db_blog.user_id
		blog_id = db_blog.blog_id
		_set_blog_attributes( db_blog, blog )
		_create_blog_rating_record(db, BlogLikes, user,
								   session_id, timestamp,
								   blog_id, delta, creator_id)


def favorite_blog( blog, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	blog_ds_id = get_ds_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
							   BlogsCreated.blog_ds_id == blog_ds_id ).first()

	if db_blog is not None:
		creator_id = db_blog.user_id
		blog_id = db_blog.blog_id
		_set_blog_attributes( db_blog, blog )
		_create_blog_rating_record( db, BlogFavorites, user,
									session_id, timestamp,
									blog_id, delta, creator_id )


def flag_blog( blog, state ):
	db = get_analytics_db()
	blog_ds_id = get_ds_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
							   BlogsCreated.blog_ds_id == blog_ds_id ).first()
	db_blog.is_flagged = state


def _blog_view_exists( db, user_id, blog_id, timestamp ):
	return db.session.query(BlogsViewed ).filter(
							BlogsViewed.user_id == user_id,
							BlogsViewed.blog_id == blog_id,
							BlogsViewed.timestamp == timestamp ).first()


def create_blog_view(user, nti_session, timestamp, context_path, blog_entry, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = nti_session
	blog_ds_id = get_ds_id( blog_entry )
	blog_record = _get_blog(db, blog_ds_id)

	if blog_record is None:
		blog_creator = get_creator( blog_entry )
		blog_record = create_blog( blog_creator, None, blog_entry )
		logger.info( 'Created new blog (%s) (%s)', blog_creator, blog_entry )

	timestamp = timestamp_type( timestamp )

	existing_record = _blog_view_exists( db, uid, blog_record.blog_id, timestamp )

	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
			return
		else:
			logger.warn('Blog view already exists (user=%s) (blog_id=%s) (time_length=%s)',
						user, blog_record.blog_id, time_length)
			return

	context_path = get_context_path( context_path )

	new_object = BlogsViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								context_path=context_path,
								time_length=time_length )
	new_object._blog_record = blog_record
	db.session.add( new_object )


def _get_blog_comment( db, cid ):
	comment = db.session.query( BlogCommentsCreated ).filter(
								BlogCommentsCreated.comment_id == cid ).first()
	return comment


def _blog_comment_exists( db, cid ):
	return _get_blog_comment( db, cid ) is not None


def _set_mime_records( db, comment_record, blog_comment ):
	"""
	Set the mime type records for our obj, removing any
	previous records present.
	"""
	# Delete the old records.
	for mime_record in comment_record._file_mime_types:
		db.session.delete( mime_record )
	comment_record._file_mime_types = []

	file_mime_types = build_mime_type_records( db, blog_comment, BlogCommentsUserFileUploadMimeTypes )
	comment_record._file_mime_types.extend( file_mime_types )


def _set_blog_comment_attributes( db, comment_record, comment ):
	"""
	Set the comment attributes for this comment record.
	"""
	like_count, favorite_count, is_flagged = get_ratings(comment)
	comment_record.like_count = like_count
	comment_record.favorite_count = favorite_count
	comment_record.is_flagged = is_flagged
	comment_record.comment_length = get_body_text_length( comment )
	_set_mime_records( db, comment_record, comment )


def create_blog_comment(user, nti_session, blog, comment ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	sid = nti_session
	blog_ds_id = get_ds_id( blog )
	blog_record = _get_blog( db, blog_ds_id )
	cid = get_ds_id( comment )

	if blog_record is None:
		blog_creator = get_creator( blog )
		blog_record = create_blog( blog_creator, None, blog )
		logger.info( 'Created new blog (%s) (%s)', blog_creator, blog )

	if _blog_comment_exists( db, cid ):
		logger.warn( 'Blog comment already exists (comment_id=%s)', cid )
		return

	pid = parent_user_id = None

	timestamp = get_created_timestamp( comment )
	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = get_ds_id( parent_comment )
		parent_creator = get_creator( parent_comment )
		parent_user_record = get_or_create_user( parent_creator )
		parent_user_id = parent_user_record.user_id

	new_object = BlogCommentsCreated(session_id=sid,
									 timestamp=timestamp,
									 parent_id=pid,
									 parent_user_id=parent_user_id,
									 comment_id=cid)

	new_object._blog_record = blog_record
	_set_blog_comment_attributes( db, new_object, comment )
	new_object._user_record = user
	db.session.add(new_object)
	return new_object


def update_blog_comment(user, nti_session, blog, comment):
	"""
	Update our blog comment, creating if it does not exist.
	"""
	db = get_analytics_db()
	cid = get_ds_id( comment )
	comment_record = _get_blog_comment( db, cid )
	if comment_record is None:
		create_blog_comment(user, nti_session, blog, comment)
	else:
		_set_blog_comment_attributes( db, comment_record, comment )


def delete_blog_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(BlogCommentsCreated).filter(
										BlogCommentsCreated.comment_id == comment_id).first()
	if not comment:
		logger.info('Blog comment never created (%s)', comment_id)
		return
	comment.deleted=timestamp


def _get_blog_comment_rating_record( db, table, user_id, comment_id ):
	blog_coment_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.comment_id == comment_id).first()
	return blog_coment_rating_record


def _create_blog_comment_rating_record( db, table, user, session_id, timestamp, comment_id, delta, creator_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )

		blog_comment_rating = _get_blog_comment_rating_record(db,
															  table,
															  user_record.user_id,
															  comment_id)

		if not blog_comment_rating and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			blog_comment_rating = table(comment_id=comment_id,
									    timestamp=timestamp,
									    session_id=session_id,
									    creator_id=creator_id )
			blog_comment_rating._user_record = user_record
			db.session.add(blog_comment_rating)
		elif blog_comment_rating and delta < 0:
			# Delete
			db.session.delete( blog_comment_rating )


def like_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
								BlogCommentsCreated.comment_id == comment_id).first()

	if db_comment is not None:
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		_set_blog_comment_attributes(db, db_comment, comment)
		_create_blog_comment_rating_record(db, BlogCommentLikes, user,
										   session_id, timestamp, comment_id, delta, creator_id)


def favorite_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
									BlogCommentsCreated.comment_id == comment_id).first()

	if db_comment is not None:
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		_set_blog_comment_attributes( db, db_comment, comment )
		_create_blog_comment_rating_record( db, BlogCommentFavorites, user,
								session_id, timestamp, comment_id, delta, creator_id )


def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = get_ds_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
									BlogCommentsCreated.comment_id == comment_id ).first()
	db_comment.is_flagged = state


def _resolve_blog( row, user=None ):
	if user is not None:
		row.user = user
	return row


def _resolve_blog_comment( row, user=None, parent_user=None ):
	if user is not None:
		row.user = user
	if parent_user is not None:
		row.RepliedToUser = parent_user
	return row


def get_blogs( user, get_deleted=False, **kwargs ):
	"""
	Fetch any blogs for a user created *after* the optionally given
	timestamp.  Optionally, can include/exclude deleted.
	"""
	filters = []
	if not get_deleted:
		filters.append( BlogsCreated.deleted == None )
	results = get_filtered_records( user, BlogsCreated,
								filters=filters, **kwargs )
	return resolve_objects( _resolve_blog, results, user=user )


def get_blog_comments( user, get_deleted=False, **kwargs ):
	"""
	Fetch any blog comments a user created *after* the optionally given
	timestamp.  Optionally, can include/exclude deleted.
	"""
	filters = []
	if not get_deleted:
		filters.append( BlogCommentsCreated.deleted == None )
	results = get_filtered_records( user, BlogCommentsCreated,
								filters=filters, **kwargs )
	return resolve_objects( _resolve_blog_comment, results, user=user )


def get_user_replies_to_others( user, **kwargs ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	results = _get_user_replies_to_others( BlogCommentsCreated, user, **kwargs )
	return resolve_objects( _resolve_blog_comment, results, user=user )


def get_replies_to_user( user, **kwargs  ):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	results = _get_replies_to_user( BlogCommentsCreated, user, **kwargs )
	return resolve_objects( _resolve_blog_comment, results, parent_user=user )


def get_likes_for_users_blogs( user, **kwargs ):
	"""
	Fetch any likes created for a user's blogs *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	results = get_ratings_for_user_objects( BlogLikes, user, **kwargs )
	return resolve_objects( resolve_like, results, obj_creator=user )


def get_favorites_for_users_blogs( user, **kwargs ):
	"""
	Fetch any favorites created for a user's blogs *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	results = get_ratings_for_user_objects( BlogFavorites, user, **kwargs )
	return resolve_objects( resolve_favorite, results, obj_creator=user )


def get_likes_for_users_comments( user, **kwargs ):
	"""
	Fetch any likes created for a user's comments *after* the optionally given
	timestamp.  Optionally, can filter by course and include/exclude
	deleted.
	"""
	results = get_ratings_for_user_objects( BlogCommentLikes, user, **kwargs )
	return resolve_objects( resolve_like, results, obj_creator=user )


def get_favorites_for_users_comments( user, **kwargs ):
	"""
	Fetch any favorites created for a user's comments *after* the optionally given
	timestamp.
	"""
	results = get_ratings_for_user_objects( BlogCommentFavorites, user, **kwargs )
	return resolve_objects( resolve_favorite, results, obj_creator=user )
