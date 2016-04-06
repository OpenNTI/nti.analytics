#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from zope import component
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from contentratings.interfaces import IObjectRatedEvent

from nti.ntiids import ntiids
from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.dataserver.interfaces import IObjectFlaggedEvent
from nti.dataserver.interfaces import IObjectFlaggingEvent
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users.users import User
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.analytics import get_factory
from nti.analytics import BLOGS_ANALYTICS
from nti.analytics import COMMENTS_ANALYTICS

from nti.analytics.interfaces import IObjectProcessor
from nti.analytics.sessions import get_nti_session_id

from nti.analytics.common import get_creator
from nti.analytics.common import get_object_root
from nti.analytics.common import process_event
from nti.analytics.common import get_rating_from_event

from nti.analytics.database import blogs as db_blogs

from nti.analytics.identifier import get_ds_id

get_blogs = db_blogs.get_blogs
get_blog_comments = db_blogs.get_blog_comments
get_replies_to_user = db_blogs.get_replies_to_user
get_user_replies_to_others = db_blogs.get_user_replies_to_others
get_likes_for_users_blogs = db_blogs.get_likes_for_users_blogs
get_favorites_for_users_blogs = db_blogs.get_favorites_for_users_blogs
get_likes_for_users_comments = db_blogs.get_likes_for_users_comments
get_favorites_for_users_comments = db_blogs.get_favorites_for_users_comments

def _get_blog_queue():
	factory = get_factory()
	return factory.get_queue( BLOGS_ANALYTICS )

def _get_comment_queue():
	factory = get_factory()
	return factory.get_queue( COMMENTS_ANALYTICS )

def _is_blog( obj ):
	return 	IPersonalBlogEntry.providedBy( obj )

def _is_blog_comment( obj ):
	return 	IPersonalBlogComment.providedBy( obj ) \
		or 	IPersonalBlogEntryPost.providedBy( obj )

# Comments
def _add_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		blog = get_object_root( comment, IPersonalBlogEntry )
		if blog is None:
			blog = get_object_root( comment, IPersonalBlogEntryPost )
		if blog is not None:
			db_blogs.create_blog_comment( user, nti_session, blog, comment )
			logger.debug( "Blog comment created (user=%s) (blog=%s)", user, blog )

def _update_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		blog = get_object_root( comment, IPersonalBlogEntry )
		if blog is None:
			blog = get_object_root( comment, IPersonalBlogEntryPost )
		if blog is not None:
			db_blogs.update_blog_comment( user, nti_session, blog, comment )
			logger.debug( "Blog comment updated (user=%s) (blog=%s)", user, blog )

def _remove_comment( comment_id, timestamp=None ):
	db_blogs.delete_blog_comment( timestamp, comment_id )
	logger.debug( "Blog comment deleted (blog=%s)", comment_id )

def _flag_comment( oid, state=False ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db_blogs.flag_comment( comment, state )
		logger.debug( 'Blog comment flagged (comment=%s) (state=%s)', comment, state )

def _favorite_comment( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_blogs.favorite_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment favorite (comment=%s)', comment )

def _like_comment( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_blogs.like_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment liked (comment=%s)', comment )

@component.adapter( IPersonalBlogComment, IIntIdAddedEvent)
def _add_personal_blog_comment(comment, _):
	nti_session = get_nti_session_id()
	process_event( _get_comment_queue, _add_comment, comment, nti_session=nti_session )

def _do_modify_comment(comment):
	if IDeletedObjectPlaceholder.providedBy( comment ):
		comment_id = get_ds_id( comment )
		timestamp = datetime.utcnow()
		process_event( _get_comment_queue, _remove_comment, comment_id=comment_id, timestamp=timestamp )
	else:
		nti_session = get_nti_session_id()
		process_event( _get_comment_queue, _update_comment, comment, nti_session=nti_session )

@component.adapter( IPersonalBlogComment, IObjectModifiedEvent )
def _modify_personal_blog_comment(comment, _):
	_do_modify_comment(comment)

@component.adapter( IPersonalBlogEntryPost, IObjectModifiedEvent )
def _modify_blog_post(comment, _):
	_do_modify_comment(comment)

# Blogs
def _add_blog( oid, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = get_creator( blog )
		db_blogs.create_blog( user, nti_session, blog )
		logger.debug( "Blog created (user=%s) (blog=%s)", user, blog )

def _update_blog( oid, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = get_creator( blog )
		db_blogs.update_blog( user, nti_session, blog )
		logger.debug( "Blog updated (user=%s) (blog=%s)", user, blog )

def _do_blog_added( blog, _ ):
	nti_session = get_nti_session_id()
	process_event( _get_blog_queue, _add_blog, blog, nti_session=nti_session )

def _flag_blog( oid, state=False ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		db_blogs.flag_blog( blog, state )
		logger.debug( 'Blog flagged (blog=%s) (state=%s)', blog, state )

def _favorite_blog( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = User.get_user( username )
		db_blogs.favorite_blog( blog, user, nti_session, timestamp, delta )
		logger.debug( 'Blog favorite (blog=%s)', blog )

def _like_blog( oid, username=None, delta=0, timestamp=None, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = User.get_user( username )
		db_blogs.like_blog( blog, user, nti_session, timestamp, delta )
		logger.debug( 'Blog liked (blog=%s)', blog )

@component.adapter( IObjectFlaggingEvent )
def _blog_flagged( event ):
	obj = event.object
	state = IObjectFlaggedEvent.providedBy( event )
	if _is_blog( obj ):
		process_event( _get_blog_queue, _flag_blog, obj, state=state )
	elif _is_blog_comment( obj ):
		process_event( _get_comment_queue, _flag_comment, obj, state=state )

@component.adapter( IObjectRatedEvent )
def _blog_rated( event ):
	obj = event.object
	_favorite_call = _like_call = _queue = None

	if _is_blog( obj ):
		_like_call = _like_blog
		_favorite_call = _favorite_blog
		_queue = _get_blog_queue
	elif _is_blog_comment( obj ):
		_like_call = _like_comment
		_favorite_call = _favorite_comment
		_queue = _get_comment_queue

	if _like_call is not None:
		timestamp = event.rating.timestamp
		nti_session = get_nti_session_id()
		is_favorite, delta = get_rating_from_event( event )
		to_call = _favorite_call if is_favorite else _like_call
		process_event( _queue, to_call,
					obj,
					username=event.rating.userid,
					delta=delta, nti_session=nti_session,
					timestamp=timestamp )

@component.adapter(	IPersonalBlogEntry, IIntIdAddedEvent )
def _blog_added( blog, event ):
	_do_blog_added( blog, event )

@component.adapter(	IPersonalBlogEntry, IObjectModifiedEvent )
def _blog_updated( blog, event ):
	nti_session = get_nti_session_id()
	process_event( _get_blog_queue, _update_blog, blog, nti_session=nti_session )

def _delete_blog( blog_id, timestamp ):
	db_blogs.delete_blog( timestamp, blog_id )
	logger.debug( 'Blog deleted (blog_id=%s)', blog_id )

@component.adapter(	IPersonalBlogEntry, IIntIdRemovedEvent )
def _blog_removed( blog, _ ):
	timestamp = datetime.utcnow()
	blog_id = get_ds_id( blog )
	process_event( _get_blog_queue, _delete_blog, blog_id=blog_id, timestamp=timestamp )

component.moduleProvides( IObjectProcessor )

def init( obj ):
	result = True
	if _is_blog( obj ):
		process_event( _get_blog_queue, _add_blog, obj )
	elif _is_blog_comment( obj ):
		process_event( _get_comment_queue, _add_comment, obj )
	else:
		result = False
	return result
