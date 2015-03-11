#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from contentratings.interfaces import IObjectRatedEvent

from nti.intid import interfaces as intid_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users.users import User
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from nti.analytics import interfaces as analytic_interfaces
from nti.analytics.sessions import get_nti_session_id

from .common import get_creator
from .common import get_object_root
from .common import process_event
from .common import get_rating_from_event

from nti.analytics.database import blogs as db_blogs

from nti.analytics.identifier import BlogId
from nti.analytics.identifier import CommentId

from nti.analytics import get_factory
from nti.analytics import BLOGS_ANALYTICS
from nti.analytics import COMMENTS_ANALYTICS

def _get_blog_queue():
	factory = get_factory()
	return factory.get_queue( BLOGS_ANALYTICS )

def _get_comment_queue():
	factory = get_factory()
	return factory.get_queue( COMMENTS_ANALYTICS )

def _is_blog( obj ):
	return 	frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
		or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj )

def _is_blog_comment( obj ):
	return frm_interfaces.IPersonalBlogComment.providedBy( obj )

# Comments
def _add_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		blog = get_object_root( comment, frm_interfaces.IPersonalBlogEntry )
		if blog is None:
			blog = get_object_root( comment, frm_interfaces.IPersonalBlogEntryPost )
		if blog:
			db_blogs.create_blog_comment( user, nti_session, blog, comment )
			logger.debug( "Blog comment created (user=%s) (blog=%s)", user, blog )

def _remove_comment( comment_id, timestamp=None ):
	db_blogs.delete_blog_comment( timestamp, comment_id )
	logger.debug( "Blog comment deleted (blog=%s)", comment_id )

def _flag_comment( oid, state=False ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db_blogs.flag_comment( comment, state )
		logger.debug( 'Blog comment flagged (comment=%s) (state=%s)', comment, state )

def _favorite_comment( oid, username, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_blogs.favorite_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment favorite (comment=%s)', comment )

def _like_comment( oid, username, delta=0, timestamp=None, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = User.get_user( username )
		db_blogs.like_comment( comment, user, nti_session, timestamp, delta )
		logger.debug( 'Comment liked (comment=%s)', comment )

@component.adapter( frm_interfaces.IPersonalBlogComment,
					intid_interfaces.IIntIdAddedEvent)
def _add_personal_blog_comment(comment, event):
	nti_session = get_nti_session_id()
	process_event( _get_comment_queue, _add_comment, comment, nti_session=nti_session )


@component.adapter(frm_interfaces.IPersonalBlogComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_personal_blog_comment(comment, event):
	# TODO Could these be changes in sharing? Perhaps different by object type.
	# IObjectSharingModifiedEvent
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		timestamp = datetime.utcnow()
		comment_id = CommentId.get_id( comment )
		process_event( _get_comment_queue, _remove_comment, comment_id=comment_id, timestamp=timestamp )




# Blogs
def _add_blog( oid, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = get_creator( blog )
		db_blogs.create_blog( user, nti_session, blog )
		logger.debug( "Blog created (user=%s) (blog=%s)", user, blog )

def _do_blog_added( blog, event ):
	nti_session = get_nti_session_id()
	process_event( _get_blog_queue, _add_blog, blog, nti_session=nti_session )

def _flag_blog( oid, state=False ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		db_blogs.flag_blog( blog, state )
		logger.debug( 'Blog flagged (blog=%s) (state=%s)', blog, state )

def _favorite_blog( oid, username, delta=0, timestamp=None, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = User.get_user( username )
		db_blogs.favorite_blog( blog, user, nti_session, timestamp, delta )
		logger.debug( 'Blog favorite (blog=%s)', blog )

def _like_blog( oid, username, delta=0, timestamp=None, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = User.get_user( username )
		db_blogs.like_blog( blog, user, nti_session, timestamp, delta )
		logger.debug( 'Blog liked (blog=%s)', blog )


@component.adapter( nti_interfaces.IObjectFlaggingEvent )
def _blog_flagged( event ):
	obj = event.object
	state = True if nti_interfaces.IObjectFlaggedEvent.providedBy( event ) else False
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
					obj, event.rating.userid,
					delta=delta, nti_session=nti_session,
					timestamp=timestamp )

@component.adapter(	frm_interfaces.IPersonalBlogEntry,
					intid_interfaces.IIntIdAddedEvent )
def _blog_added( blog, event ):
	_do_blog_added( blog, event )

def _delete_blog( blog_id, timestamp ):
	db_blogs.delete_blog( timestamp, blog_id )
	logger.debug( 'Blog deleted (blog_id=%s)', blog_id )

@component.adapter(	frm_interfaces.IPersonalBlogEntry,
					intid_interfaces.IIntIdRemovedEvent )
def _blog_removed( blog, event ):
	timestamp = datetime.utcnow()
	blog_id = BlogId.get_id( blog )
	process_event( _get_blog_queue, _delete_blog, blog_id=blog_id, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if _is_blog( obj ):
		process_event( _get_blog_queue, _add_blog, obj )
	elif _is_blog_comment( obj ):
		process_event( _get_comment_queue, _add_comment, obj )
	else:
		result = False
	return result
