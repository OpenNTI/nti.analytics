#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.intid import interfaces as intid_interfaces
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from .common import get_creator
from .common import get_nti_session_id
from .common import to_external_ntiid_oid
from .common import get_deleted_time
from .common import get_comment_root
from .common import process_event
from .common import get_entity

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

# Comments
def _add_comment( db, oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		user = get_entity( user )
		blog = get_comment_root( comment, 
								( frm_interfaces.IPersonalBlogEntry, frm_interfaces.IPersonalBlogEntryPost ) )
		if blog:
			db.create_blog_comment( user, nti_session, blog, comment )
			logger.debug( "Blog comment created (user=%s) (blog=%s)", user, blog )

def _remove_comment( db, oid, timestamp=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db.delete_blog_comment( timestamp, comment )
		logger.debug( "Blog comment deleted (blog=%s)", blog )

@component.adapter( frm_interfaces.IPersonalBlogComment, 
					lce_interfaces.IObjectAddedEvent)
def _add_personal_blog_comment(comment, event):
	user = get_creator( comment )
	user = get_entity( user )
	nti_session = get_nti_session_id( user )
	process_event( _add_comment, comment, nti_session=nti_session )


@component.adapter(frm_interfaces.IPersonalBlogComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_personal_blog_comment(comment, event):
	# FIXME Could these be changes in sharing? Perhaps different by object type.
	# IObjectSharingModifiedEvent	
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		timestamp = datetime.utcnow()
		process_event( _remove_comment, comment, timestamp=timestamp )


# Blogs
def _add_blog( db, oid, nti_session=None ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog is not None:
		user = get_creator( blog )
		user = get_entity( user )
		db.create_blog( user, nti_session, blog )
		logger.debug( "Blog created (user=%s) (blog=%s)", user, blog )

@component.adapter(	frm_interfaces.IPersonalBlogEntry, 
					frm_interfaces.IPersonalBlogEntryPost,
					lce_interfaces.IObjectAddedEvent )
def _blog_added( blog, event ):
	user = get_creator( blog )
	user = get_entity( user )
	nti_session = get_nti_session_id( user )
	process_event( _add_blog, blog, nti_session=nti_session )
		
# NOTE: We do not expect blog removed events.

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
