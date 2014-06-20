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

from . import utils
from . import create_job
from . import get_job_queue
from . import get_user_from_object
from . import interfaces as analytic_interfaces


@component.adapter(frm_interfaces.ITopic, lce_interfaces.IObjectAddedEvent)
def _topic_added( topic, event ):
	_process_topic_added( topic )

@component.adapter(frm_interfaces.ITopic, lce_interfaces.IObjectModifiedEvent)
def _topic_modified( topic, event ):
	_process_topic_modified( topic )

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

def _delete_comment( db, oid, timestamp ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment:
		db.delete_blog_comment( timestamp, comment )

def _process_comment_removed( comment, timestamp ):
	queue = get_job_queue()
	oid = to_external_ntiid_oid( comment )
	job = create_job( _delete_comment, oid=oid, timestamp=timestamp )
	queue.put( job )

def _process_comment_added( comment ):
	queue = get_job_queue()
	oid = to_external_ntiid_oid( comment )
	job = create_job( _add_comment, oid=oid )
	queue.put( job )
	
@component.adapter( frm_interfaces.IGeneralForumComment, 
					lce_interfaces.IObjectAddedEvent )
def _add_general_forum_comment(comment, event):
	_process_comment_added( comment )

@component.adapter(frm_interfaces.IGeneralForumComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_general_forum_comment(comment, event):
# 	# FIXME Could these be changes in sharing? Perhaps different by object type.
# 	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
# 		# TODO Can we get this time from the event?
# 		timestamp = get_deleted_time( comment )
# 		_process_comment_removed( comment, timestamp )
	_modify_personal_blog_comment( comment, event )

# Blogs
def _add_forum( oid ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum:
		user = get_creator( forum )
		nti_session = get_nti_session()
		db.create_thought( user, nti_session, forum )

def _process_forum_added( forum ):
	oid = to_external_ntiid_oid( forum )
	queue = get_job_queue()
	job = create_job( _add_forum, oid=oid )
	queue.put( job )

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectAddedEvent )
def _forum_added( forum, event ):
	_process_forum_add_mod_event( forum )

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectModifiedEvent )
def _forum_modified( forum, event ):
	# TODO How do we handle these modify events?
	_process_forum_add_mod_event( forum )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdRemovedEvent )
def _forum_removed( forum, event ):
	# Remove topics
	for topic in forum.values():
		_remove_topic( topic )
	_process_discussion_remove_events(db, [get_primary_key(forum)])
		
component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if frm_interfaces.IForum.providedBy(obj):
		_process_forum_added( obj )
	
	elif frm_interfaces.ITopic.providedBy(obj):
		_process_topic_added( obj )
	
	elif frm_interfaces.IGeneralForumComment.providedBy( obj ):
		_process_comment_added( obj )
	else:
		result = False
	return result
