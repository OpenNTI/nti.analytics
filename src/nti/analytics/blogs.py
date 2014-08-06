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

from nti.intid import interfaces as intid_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from nti.analytics import interfaces as analytic_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import get_object_root
from .common import process_event

from nti.analytics.database import blogs as db_blogs

from nti.analytics.identifier import BlogId
from nti.analytics.identifier import CommentId
_commentid = CommentId()
_blogid = BlogId()

# Comments
def _add_comment( oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		blog = get_object_root( comment, frm_interfaces.IPersonalBlogEntry )
		if blog is None:
			# TODO Need to find out which type we should look for.
			blog = get_object_root( comment, frm_interfaces.IPersonalBlogEntryPost )
		if blog:
			db_blogs.create_blog_comment( user, nti_session, blog, comment )
			logger.debug( "Blog comment created (user=%s) (blog=%s)", user, blog )

def _remove_comment( comment_id, timestamp=None ):
	db_blogs.delete_blog_comment( timestamp, comment_id )
	logger.debug( "Blog comment deleted (blog=%s)", comment_id )

@component.adapter( frm_interfaces.IPersonalBlogComment,
					intid_interfaces.IIntIdAddedEvent)
def _add_personal_blog_comment(comment, event):
	user = get_creator( comment )
	nti_session = get_nti_session_id( user )
	process_event( _add_comment, comment, nti_session=nti_session )


@component.adapter(frm_interfaces.IPersonalBlogComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_personal_blog_comment(comment, event):
	# TODO Could these be changes in sharing? Perhaps different by object type.
	# IObjectSharingModifiedEvent
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		timestamp = datetime.utcnow()
		comment_id = _commentid.get_id( comment )
		process_event( _remove_comment, comment_id=comment_id, timestamp=timestamp )


# Blogs
def _add_blog( oid, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = get_creator( blog )
		db_blogs.create_blog( user, nti_session, blog )
		logger.debug( "Blog created (user=%s) (blog=%s)", user, blog )

def _do_blog_added( blog, event ):
	user = get_creator( blog )
	nti_session = get_nti_session_id( user )
	process_event( _add_blog, blog, nti_session=nti_session )

@component.adapter(	frm_interfaces.IPersonalBlogEntry,
					intid_interfaces.IIntIdAddedEvent )
def _blog_added( blog, event ):
	_do_blog_added( blog, event )

def _delete_blog( db, blog_id, timestamp ):
	db.delete_blog( timestamp, blog_id )
	logger.debug( 'Blog deleted (blog_id=%s)', blog_id )

@component.adapter(	frm_interfaces.IPersonalBlogEntry,
					intid_interfaces.IIntIdRemovedEvent )
def _blog_removed( blog, event ):
	timestamp = datetime.utcnow()
	blog_id = _blogid.get_id( blog )
	process_event( _delete_blog, blog_id=blog_id, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if 		frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
		or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj ):
		process_event( _add_blog, obj )
	elif frm_interfaces.IPersonalBlogComment.providedBy( obj ):
		process_event( _add_comment, obj )
	else:
		result = False
	return result
