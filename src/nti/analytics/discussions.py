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
from .common import get_nti_session
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import process_event
from .common import IDLookup

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
			logger.debug( 	"Forum comment created (user=%s) (discussion=%s) (course=%s)", 
							user, discussion, course )

def _remove_comment( db, oid, timestamp ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		db.delete_forum_comment( timestamp, comment )
		logger.debug( 	"Forum comment deleted (comment=%s)", 
						comment )
	
@component.adapter( frm_interfaces.IGeneralForumComment, 
					lce_interfaces.IObjectAddedEvent )
def _add_general_forum_comment(comment, event):
	process_event( _add_comment, comment )

@component.adapter(frm_interfaces.IGeneralForumComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_general_forum_comment(comment, event):
	if nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
		timestamp = datetime.utcnow()
		process_event( _remove_comment, comment, timestamp=timestamp )

# Topic
def _add_topic( db, oid ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = get_creator( topic )
		nti_session = get_nti_session()
		course = get_course( topic )
		db.create_discussion( user, nti_session, course, topic )
		logger.debug( 	"Discussion created (user=%s) (discussion=%s)", 
						user, topic )

def _modify_topic( db, oid, timestamp=None ):
	# TODO
	pass

def _remove_topic( db, oid, timestamp=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		db.delete_discussion( timestamp, topic )
		logger.debug( 	"Discussion deleted (discussion=%s)", 
						topic )

@component.adapter( frm_interfaces.ITopic, lce_interfaces.IObjectAddedEvent )
def _topic_added( topic, event ):
	process_event( _add_topic, topic )

@component.adapter( frm_interfaces.ITopic, lce_interfaces.IObjectModifiedEvent )
def _topic_modified( topic, event ):
	timestamp = datetime.utcnow()
	process_event( _modify_topic, topic, timestamp=timestamp )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdRemovedEvent )
def _topic_removed( topic, event ):
	# TODO Does this event occur for topics?
	timestamp = datetime.utcnow()
	process_event( _remove_topic, topic, timestamp=timestamp )

# Forum
def _remove_forum( db, oid, timestamp ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		db.delete_forum( timestamp, forum )
		logger.debug( "Forum deleted (forum=%s)", forum )

def _add_forum( db, oid ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		user = get_creator( forum )
		nti_session = get_nti_session()
		course = get_course( forum )
		db.create_forum( user, nti_session, course, forum )
		logger.debug( 	"Forum created (user=%s) (forum=%s) (course=%s)", 
						user, forum, course )

def _modify_forum( db, oid ):
	# TODO How do we handle these modify events?
	pass

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectAddedEvent )
def _forum_added( forum, event ):
	process_event( _add_forum, forum )

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectModifiedEvent )
def _forum_modified( forum, event ):
	timestamp = datetime.utcnow()
	process_event( _modify_forum, forum )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdRemovedEvent )
def _forum_removed( forum, event ):
	timestamp = datetime.utcnow()
	timestamp = get_deleted_time( forum )
	process_event( _remove_forum, forum, timestamp=timestamp )
		
component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	# Exclude blogs
	# TODO Note comments may end up here...
	result = True
	if frm_interfaces.IForum.providedBy(obj):
		process_event( _add_forum, obj )
	
	elif frm_interfaces.ITopic.providedBy(obj) \
		and not (	frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
				or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj ) ):
		
		process_event( _add_topic, obj )
	
	elif frm_interfaces.IGeneralForumComment.providedBy( obj ) \
		and not frm_interfaces.IPersonalBlogComment.providedBy( obj ):
		
		process_event( _add_comment, obj )
	else:
		result = False
		
	return result
