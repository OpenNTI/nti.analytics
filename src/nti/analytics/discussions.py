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
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import process_event

from . import utils
from . import interfaces as analytic_interfaces

# Comments
def _add_comment( db, oid ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		nti_session = get_nti_session()
		discussion = get_comment_root( comment, frm_interfaces.ITopic )
		course = get_course( discussion )
		if discussion:
			db.create_forum_comment( user, nti_session, course, discussion, comment )

def _remove_comment( db, oid, timestamp ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db.delete_forum_comment( timestamp, comment )
	
@component.adapter( frm_interfaces.IGeneralForumComment, 
					lce_interfaces.IObjectAddedEvent )
def _add_general_forum_comment(comment, event):
	process_event( comment, _add_comment )

@component.adapter(frm_interfaces.IGeneralForumComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_general_forum_comment(comment, event):
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		# TODO Can we get this time from the event?
		timestamp = get_deleted_time( comment )
		process_event( comment, _remove_comment, timestamp=timestamp )

# Topic
def _add_topic( db, oid ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = get_creator( topic )
		nti_session = get_nti_session()
		course = get_course( topic )
		db.create_discussion( user, nti_session, course, topic )

def _modify_topic( db, oid ):
	# TODO
	pass

def _remove_topic( db, oid, timestamp ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		db.delete_discussion( user, timestamp, topic )

@component.adapter( frm_interfaces.ITopic, lce_interfaces.IObjectAddedEvent )
def _topic_added( topic, event ):
	process_event( topic, _add_topic )

@component.adapter( frm_interfaces.ITopic, lce_interfaces.IObjectModifiedEvent )
def _topic_modified( topic, event ):
	process_event( topic, _modify_topic )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdRemovedEvent )
def _topic_removed( topic, event ):
	# Can this event occur for topics?
	timestamp = get_deleted_time( topic )
	process_event( topic, _remove_topic, timestamp=timestamp )

# Forum
def _remove_forum( db, oid, timestamp ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		db.delete_forum( user, timestamp, forum )

def _add_forum( db, oid ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		user = get_creator( forum )
		nti_session = get_nti_session()
		course = get_course( forum )
		db.create_forum( user, nti_session, course, forum )

def _modify_forum( db, oid ):
	# TODO How do we handle these modify events?
	pass

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectAddedEvent )
def _forum_added( forum, event ):
	process_event( forum, _add_forum )

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectModifiedEvent )
def _forum_modified( forum, event ):
	process_event( forum, _modify_forum )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdRemovedEvent )
def _forum_removed( forum, event ):
	timestamp = get_deleted_time( forum )
	process_event( forum, _remove_forum, timestamp=timestamp )
		
component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	# TODO Note comments may end up here...
	result = True
	if frm_interfaces.IForum.providedBy(obj):
		process_event( obj, _add_forum )
	
	elif frm_interfaces.ITopic.providedBy(obj):
		process_event( obj, _add_topic )
	
	elif frm_interfaces.IGeneralForumComment.providedBy( obj ):
		process_event( obj, _add_comment )
	else:
		result = False
		
	return result
