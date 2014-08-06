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
from nti.analytics.identifier import BlogId
from nti.analytics.identifier import CommentId
_sessionid = SessionId()
_courseid = CourseId()
_blogid = BlogId()
_commentid = CommentId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import CommentsMixin

from nti.analytics.database.users import get_or_create_user

class BlogMixin(BaseViewMixin):

	@declared_attr
	def blog_id(cls):
		return Column('blog_id', Integer, ForeignKey("BlogsCreated.blog_id"), nullable=False, index=True, primary_key=True )

class BlogsCreated(Base,BaseTableMixin,DeletedMixin):
	__tablename__ = 'BlogsCreated'
	blog_id = Column('blog_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )

class BlogsViewed(Base,BlogMixin):
	__tablename__ = 'BlogsViewed'

class BlogCommentsCreated(Base,CommentsMixin,BlogMixin):
	__tablename__ = 'BlogCommentsCreated'


def create_blog( user, nti_session, blog_entry ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	blog_id = _blogid.get_id( blog_entry )

	timestamp = get_created_timestamp( blog_entry )

	new_object = BlogsCreated( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								blog_id=blog_id )
	db.session.add( new_object )

def delete_blog( timestamp, blog_id ):
	db = get_analytics_db()
	blog = db.session.query(BlogsCreated).filter(
									BlogsCreated.blog_id == blog_id ).one()
	blog.deleted = timestamp

	db.session.query( BlogCommentsCreated ).filter(
						BlogCommentsCreated.blog_id == blog_id ).update(
									{ BlogCommentsCreated.deleted : timestamp } )
	db.session.flush()

def create_blog_view(user, nti_session, timestamp, blog_entry):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	blog_id = _blogid.get_id( blog_entry )
	timestamp = timestamp_type( timestamp )

	new_object = BlogsViewed( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								blog_id=blog_id )
	db.session.add( new_object )

def create_blog_comment(user, nti_session, blog, comment ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	bid = _blogid.get_id( blog )
	cid = _commentid.get_id( comment )
	pid = None

	timestamp = get_created_timestamp( comment )
	parent_comment = getattr( comment, 'inReplyTo', None )
	if parent_comment is not None:
		pid = _commentid.get_id( parent_comment )

	new_object = BlogCommentsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										blog_id=bid,
										parent_id=pid,
										comment_id=cid )
	db.session.add( new_object )

def delete_blog_comment(timestamp, comment_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	comment = db.session.query(BlogCommentsCreated).filter(
						BlogCommentsCreated.comment_id == comment_id ).one()
	comment.deleted=timestamp
	db.session.flush()

