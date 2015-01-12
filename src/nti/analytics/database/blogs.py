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
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.schema import Sequence

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_ratings

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import BlogId
from nti.analytics.identifier import CommentId

from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import CommentsMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin
from nti.analytics.database.meta_mixins import RatingsMixin

from nti.analytics.database.users import get_or_create_user

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

def like_blog( blog, delta ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter( BlogsCreated.blog_ds_id == blog_ds_id ).one()
	db_blog.like_count += delta
	db.session.flush()

def favorite_blog( blog, delta ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter( BlogsCreated.blog_ds_id == blog_ds_id ).one()
	db_blog.favorite_count += delta
	db.session.flush()

def flag_blog( blog, state ):
	db = get_analytics_db()
	blog_ds_id = BlogId.get_id( blog )
	db_blog = db.session.query(BlogsCreated).filter( BlogsCreated.blog_ds_id == blog_ds_id ).one()
	db_blog.is_flagged = state
	db.session.flush()

def _blog_view_exists( db, user_id, blog_id, timestamp ):
	return db.session.query( BlogsViewed ).filter(
							BlogsViewed.user_id == user_id,
							BlogsViewed.blog_id == blog_id,
							BlogsViewed.timestamp == timestamp ).first()

def create_blog_view(user, nti_session, timestamp, blog_entry, time_length):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	blog_ds_id = BlogId.get_id( blog_entry )
	blog_id = _get_blog_id( db, blog_ds_id )
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

	new_object = BlogsViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								blog_id=blog_id,
								time_length=time_length )
	db.session.add( new_object )

def _blog_comment_exists( db, cid ):
	return db.session.query( BlogCommentsCreated ).filter(
							BlogCommentsCreated.comment_id == cid ).count()

def create_blog_comment(user, nti_session, blog, comment ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	blog_ds_id = BlogId.get_id( blog )
	bid = _get_blog_id( db, blog_ds_id )
	cid = CommentId.get_id( comment )

	if _blog_comment_exists( db, cid ):
		logger.warn( 'Blog comment already exists (comment_id=%s)', cid )
		return

	pid = None
	like_count, favorite_count, is_flagged = get_ratings( comment )

	timestamp = get_created_timestamp( comment )
	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = CommentId.get_id( parent_comment )

	comment_length = sum( len( x ) for x in comment.body )

	new_object = BlogCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										blog_id=bid,
										parent_id=pid,
										comment_length=comment_length,
										comment_id=cid,
										like_count=like_count,
										favorite_count=favorite_count,
										is_flagged=is_flagged )
	db.session.add( new_object )

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

def like_comment( comment, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter( BlogCommentsCreated.comment_id == comment_id ).one()
	db_comment.like_count += delta
	db.session.flush()

def favorite_comment( comment, delta ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter( BlogCommentsCreated.comment_id == comment_id ).one()
	db_comment.favorite_count += delta
	db.session.flush()

def flag_comment( comment, state ):
	db = get_analytics_db()
	comment_id = CommentId.get_id( comment )
	db_comment = db.session.query(BlogCommentsCreated).filter( BlogCommentsCreated.comment_id == comment_id ).one()
	db_comment.is_flagged = state
	db.session.flush()

