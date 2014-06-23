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

from .common import get_creator
from .common import get_nti_session
from .common import to_external_ntiid_oid
from .common import get_deleted_time
from .common import get_comment_root
from .common import process_event

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

# Comments
def _add_comment( db, oid ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment:
		user = get_creator( blog )
		nti_session = get_nti_session()
		blog = get_comment_root( comment, 
								( frm_interfaces.IPersonalBlogEntry, frm_interfaces.IPersonalBlogEntryPost ) )
		if blog:
			db.create_blog_comment( user, nti_session, blog, comment )

def _remove_comment( db, oid, timestamp ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment:
		db.delete_blog_comment( timestamp, comment )

@component.adapter( frm_interfaces.IPersonalBlogComment, 
					lce_interfaces.IObjectAddedEvent)
def _add_personal_blog_comment(comment, event):
	process_event( comment, _add_comment )


@component.adapter(frm_interfaces.IPersonalBlogComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_personal_blog_comment(comment, event):
	# FIXME Could these be changes in sharing? Perhaps different by object type.
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		# TODO Can we get this time from the event?
		timestamp = get_deleted_time( comment )
		process_event( comment, _remove_comment, timestamp=timestamp )


# Blogs
def _add_blog( db, oid ):
	blog = ntiids.find_object_with_ntiid( oid )
	if blog:
		user = get_creator( blog )
		nti_session = get_nti_session()
		db.create_thought( user, nti_session, blog )

@component.adapter(	frm_interfaces.IPersonalBlogEntry, 
					frm_interfaces.IPersonalBlogEntryPost,
					lce_interfaces.IObjectAddedEvent )
def _blog_added( blog, event ):
	process_event( blog, _add_blog )
		
# NOTE: We do not expect blog removed events.

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if 		frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
		or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj ):
		
		process_event( obj, _add_blog )
	elif frm_interfaces.IPersonalBlogComment.providedBy( obj ):
		
		process_event( obj, _add_comment )
	else:
		result = False
	return result
