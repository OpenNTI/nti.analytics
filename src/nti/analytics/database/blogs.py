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

from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.schema import Sequence
from sqlalchemy.orm.session import make_transient
from sqlalchemy.ext.declarative import declared_attr

from nti.analytics.common import get_creator
from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import BlogId
from nti.analytics.identifier import CommentId

from nti.analytics.read_models import AnalyticsBlog
from nti.analytics.read_models import AnalyticsBlogComment

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event
from nti.analytics.database import resolve_objects

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import CommentsMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin
from nti.analytics.database.meta_mixins import RatingsMixin
from nti.analytics.database.meta_mixins import CreatorMixin

from nti.analytics.database.users import get_user
from nti.analytics.database.users import get_or_create_user

from nti.analytics.database._utils import resolve_like
from nti.analytics.database._utils import resolve_favorite
from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_filtered_records
from nti.analytics.database._utils import get_ratings_for_user_objects
from nti.analytics.database._utils import get_replies_to_user as _get_replies_to_user
from nti.analytics.database._utils import get_user_replies_to_others as _get_user_replies_to_others

class BlogMixin(object):

	@declared_attr
	def blog_id(cls):
		return Column('blog_id', Integer, ForeignKey("BlogsCreated.blog_id"), nullable=False, index=True)

class BlogsCreated(Base,BaseTableMixin,DeletedMixin,RatingsMixin):
	__tablename__ = 'BlogsCreated'
	blog_ds_id = Column('blog_ds_id', INTID_COLUMN_TYPE, nullable=True, autoincrement=False )
	blog_length = Column('blog_length', Integer, nullable=True, autoincrement=False)
	blog_id = Column('blog_id', Integer, Sequence( 'blog_seq' ), index=True, nullable=False, primary_key=True )

class BlogsViewed(Base,BaseViewMixin,BlogMixin,TimeLengthMixin):
	__tablename__ = 'BlogsViewed'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'blog_id', 'timestamp'),
    )

class BlogCommentsCreated(Base,CommentsMixin,BlogMixin,RatingsMixin):
	__tablename__ = 'BlogCommentsCreated'

	__table_args__ = (
        PrimaryKeyConstraint('comment_id'),
    )

class BlogFavorites(Base,BaseTableMixin,BlogMixin,CreatorMixin):
	__tablename__ = 'BlogFavorites'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'blog_id'),
    )

class BlogLikes(Base,BaseTableMixin,BlogMixin,CreatorMixin):
	__tablename__ = 'BlogLikes'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'blog_id'),
    )

class BlogCommentMixin(object):

	@declared_attr
	def comment_id(cls):
		return Column('comment_id', INTID_COLUMN_TYPE, ForeignKey("BlogCommentsCreated.comment_id"), nullable=False, index=True)


class BlogCommentFavorites(Base,BaseTableMixin,BlogCommentMixin, CreatorMixin):
	__tablename__ = 'BlogCommentFavorites'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'comment_id'),
    )

class BlogCommentLikes(Base,BaseTableMixin,BlogCommentMixin, CreatorMixin):
	__tablename__ = 'BlogCommentLikes'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'comment_id'),
    )

def _get_blog_id( db, blog_ds_id ):
	blog = db.session.query(BlogsCreated).filter( BlogsCreated.blog_ds_id == blog_ds_id ).first()
	return blog and blog.blog_id

_blog_exists = _get_blog_id

def create_blog( user, nti_session, blog_entry ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	blog_ds_id = BlogId.get_id( blog_entry )

	if _blog_exists( db, blog_ds_id ):
		logger.warn( 'Blog already exists (blog_id=%s) (user=%s)', blog_ds_id, user )
		return

	like_count, favorite_count, is_flagged = get_ratings( blog_entry )
	timestamp = get_created_timestamp( blog_entry )
	blog_length = None

	# TODO What about the headline?
	# TODO We should probably capture text length when possible
	# and marking if canvas or video are embedded.
	try:
		if blog_entry.description is not None:
			blog_length = len( blog_entry.description )
	except AttributeError:
		try:
			blog_length = sum( len( x ) for x in blog_entry.body )
		except TypeError:
			# Embedded Video
			pass

	new_object = BlogsCreated( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								blog_length=blog_length,
								blog_ds_id=blog_ds_id,
								like_count=like_count,
								favorite_count=favorite_count,
								is_flagged=is_flagged )
	db.session.add( new_object )
	db.session.flush()
	return new_object

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

	db.session.query( BlogCommentsCreated ).filter(
						BlogCommentsCreated.blog_id == blog_id ).update(
									{ BlogCommentsCreated.deleted : timestamp } )
	db.session.flush()

def _get_blog_rating_record( db, table, user_id, blog_id ):
	blog_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.blog_id == blog_id ).first()
	return blog_rating_record

def _create_blog_rating_record( db, table, user, session_id, timestamp, blog_id, delta, creator_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )
		user_id = user_record.user_id

		blog_rating_record = _get_blog_rating_record( db, table,
													user_id, blog_id )

		if not blog_rating_record and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			blog_rating_record = table( blog_id=blog_id,
								user_id=user_id,
								timestamp=timestamp,
								session_id=session_id,
								creator_id=creator_id )
			db.session.add( blog_rating_record )
		elif blog_rating_record and delta < 0:
			# Delete
			db.session.delete( blog_rating_record )
		db.session.flush()

def like_blog( blog, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
								BlogsCreated.blog_ds_id == blog_ds_id ).first()

	if db_blog is not None:
		db_blog.like_count += delta
		db.session.flush()
		creator_id = db_blog.user_id
		blog_id = db_blog.blog_id
		_create_blog_rating_record( db, BlogLikes, user,
								session_id, timestamp,
								blog_id, delta, creator_id )

def favorite_blog( blog, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
								BlogsCreated.blog_ds_id == blog_ds_id ).first()

	if db_blog is not None:
		db_blog.favorite_count += delta
		db.session.flush()
		creator_id = db_blog.user_id
		blog_id = db_blog.blog_id
		_create_blog_rating_record( db, BlogFavorites, user,
								session_id, timestamp,
								blog_id, delta, creator_id )

def flag_blog( blog, state ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter(
							BlogsCreated.blog_ds_id == blog_ds_id ).first()
	db_blog.is_flagged = state
	db.session.flush()

def _blog_view_exists( db, user_id, blog_id, timestamp ):
	return db.session.query( BlogsViewed ).filter(
							BlogsViewed.user_id == user_id,
							BlogsViewed.blog_id == blog_id,
							BlogsViewed.timestamp == timestamp ).first()

def create_blog_view(user, nti_session, timestamp, context_path, blog_entry, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	blog_ds_id = BlogId.get_id( blog_entry )
	blog_id = _get_blog_id( db, blog_ds_id )

	if blog_id is None:
		blog_creator = get_creator( blog_entry )
		new_blog = create_blog( blog_creator, None, blog_entry )
		logger.info( 'Created new blog (%s) (%s)', blog_creator, blog_entry )
		blog_id = new_blog.blog_id

	timestamp = timestamp_type( timestamp )

	existing_record = _blog_view_exists( db, uid, blog_id, timestamp )

	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			return
		else:
			logger.warn( 'Blog view already exists (user=%s) (blog_id=%s)',
						user, blog_id )
			return

	context_path = get_context_path( context_path )

	new_object = BlogsViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								context_path=context_path,
								blog_id=blog_id,
								time_length=time_length )
	db.session.add( new_object )

def _blog_comment_exists( db, cid ):
	return db.session.query( BlogCommentsCreated ).filter(
							BlogCommentsCreated.comment_id == cid ).count()

def create_blog_comment(user, nti_session, blog, comment ):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	blog_ds_id = BlogId.get_id( blog )
	bid = _get_blog_id( db, blog_ds_id )
	cid = CommentId.get_id( comment )

	if bid is None:
		blog_creator = get_creator( blog )
		new_blog = create_blog( blog_creator, None, blog )
		logger.info( 'Created new blog (%s) (%s)', blog_creator, blog )
		bid = new_blog.blog_id

	if _blog_comment_exists( db, cid ):
		logger.warn( 'Blog comment already exists (comment_id=%s)', cid )
		return

	pid = parent_user_id = None
	like_count, favorite_count, is_flagged = get_ratings( comment )

	timestamp = get_created_timestamp( comment )
	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = CommentId.get_id( parent_comment )
		parent_creator = get_creator( parent_comment )
		parent_user_record = get_or_create_user( parent_creator )
		parent_user_id = parent_user_record.user_id

	comment_length = sum( len( x ) for x in comment.body ) if comment.body else 0

	new_object = BlogCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										blog_id=bid,
										parent_id=pid,
										parent_user_id=parent_user_id,
										comment_length=comment_length,
										comment_id=cid,
										like_count=like_count,
										favorite_count=favorite_count,
										is_flagged=is_flagged )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def delete_blog_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(BlogCommentsCreated).filter(
										BlogCommentsCreated.comment_id == comment_id ).first()
	if not comment:
		logger.info( 'Blog comment never created (%s)', comment_id )
		return
	comment.deleted=timestamp
	db.session.flush()

def _get_blog_comment_rating_record( db, table, user_id, comment_id ):
	blog_coment_rating_record = db.session.query( table ).filter(
									table.user_id == user_id,
									table.comment_id == comment_id ).first()
	return blog_coment_rating_record

def _create_blog_comment_rating_record( db, table, user, session_id, timestamp, comment_id, delta, creator_id ):
	"""
	Creates a like or favorite record, based on given table. If
	the delta is negative, we delete the like or favorite record.
	"""
	if user is not None:
		user_record = get_or_create_user( user )
		user_id = user_record.user_id

		blog_comment_rating = _get_blog_comment_rating_record( db, table,
															user_id, comment_id)

		if not blog_comment_rating and delta > 0:
			# Create
			timestamp = timestamp_type( timestamp )
			blog_comment_rating = table( comment_id=comment_id,
								user_id=user_id,
								timestamp=timestamp,
								session_id=session_id,
								creator_id=creator_id )
			db.session.add( blog_comment_rating )
		elif blog_comment_rating and delta < 0:
			# Delete
			db.session.delete( blog_comment_rating )
		db.session.flush()

def like_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
								BlogCommentsCreated.comment_id == comment_id ).first()

	if db_comment is not None:
		db_comment.like_count += delta
		db.session.flush()
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		_create_blog_comment_rating_record( db, BlogCommentLikes, user,
								session_id, timestamp, comment_id, delta, creator_id )

def favorite_comment( comment, user, session_id, timestamp, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
									BlogCommentsCreated.comment_id == comment_id ).first()

	if db_comment is not None:
		db_comment.favorite_count += delta
		db.session.flush()
		creator_id = db_comment.user_id
		comment_id = db_comment.comment_id
		_create_blog_comment_rating_record( db, BlogCommentFavorites, user,
								session_id, timestamp, comment_id, delta, creator_id )

def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter(
									BlogCommentsCreated.comment_id == comment_id ).first()
	db_comment.is_flagged = state
	db.session.flush()

def _resolve_blog( row, user=None ):
	make_transient( row )
	blog = BlogId.get_object( row.blog_ds_id )
	user = get_user( row.user_id ) if user is None else user

	result = None
	if 		blog is not None \
		and user is not None:
		result = AnalyticsBlog( Blog=blog,
								user=user,
								timestamp=row.timestamp,
								Flagged=row.is_flagged,
								LikeCount=row.like_count,
								FavoriteCount=row.favorite_count,
								BlogLength=row.blog_length )
	return result

def _resolve_blog_comment( row, user=None, parent_user=None ):
	make_transient( row )
	comment = CommentId.get_object( row.comment_id )
	user = get_user( row.user_id ) if user is None else user

	result = None
	if 		comment is not None \
		and user is not None:

		is_reply = row.parent_id is not None
		if 		parent_user is None \
			and row.parent_user_id is not None:
			parent_user = get_user( row.parent_user_id )

		result = AnalyticsBlogComment( Comment=comment,
								user=user,
								timestamp=row.timestamp,
								CommentLength=row.comment_length,
								Flagged=row.is_flagged,
								LikeCount=row.like_count,
								FavoriteCount=row.favorite_count,
								IsReply=is_reply,
								RepliedToUser=parent_user )
	return result

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
