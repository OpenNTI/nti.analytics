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

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.intid import interfaces as intid_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from nti.analytics import interfaces as analytic_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import get_deleted_time
from .common import get_object_root
from .common import get_course
from .common import process_event

def _is_topic( obj ):
	# Exclude blogs
	result = 	frm_interfaces.ITopic.providedBy(obj) \
			and not (	frm_interfaces.IPersonalBlogEntry.providedBy( obj ) \
					or 	frm_interfaces.IPersonalBlogEntryPost.providedBy( obj ) )
	return result

def _is_forum_comment( obj ):
	result = 	frm_interfaces.IGeneralForumComment.providedBy( obj ) \
			and not frm_interfaces.IPersonalBlogComment.providedBy( obj )
	return result

# Comments
def _add_comment( db, oid, nti_session=None ):
	comment = ntiids.find_object_with_ntiid( oid )
	if comment is not None:
		user = get_creator( comment )
		nti_session = get_nti_session_id( user )
		discussion = get_object_root( comment, frm_interfaces.ITopic )
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
					intid_interfaces.IIntIdAddedEvent )
def _add_general_forum_comment(comment, event):
	if _is_forum_comment( comment ):
		user = get_creator( comment )
		nti_session = get_nti_session_id( user )
		process_event( _add_comment, comment, nti_session=nti_session )

@component.adapter(frm_interfaces.IGeneralForumComment,
				   lce_interfaces.IObjectModifiedEvent)
def _modify_general_forum_comment(comment, event):
	if		_is_forum_comment( comment ) \
		and nti_interfaces.IDeletedObjectPlaceholder.providedBy( comment ):
			timestamp = datetime.utcnow()
			process_event( _remove_comment, comment, timestamp=timestamp )

# Topic
def _add_topic( db, oid, nti_session=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		user = get_creator( topic )
		course = get_course( topic )
		db.create_discussion( user, nti_session, course, topic )
		logger.debug( "Discussion created (user=%s) (discussion=%s)", user, topic )

def _remove_topic( db, oid, timestamp=None ):
	topic = ntiids.find_object_with_ntiid( oid )
	if topic is not None:
		db.delete_discussion( timestamp, topic )
		logger.debug( "Discussion deleted (discussion=%s)", topic )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdAddedEvent )
def _topic_added( topic, event ):
	if _is_topic( topic ):
		user = get_creator( topic )
		nti_session = get_nti_session_id( user )
		process_event( _add_topic, topic, nti_session=nti_session )

@component.adapter( frm_interfaces.ITopic, lce_interfaces.IObjectModifiedEvent )
def _topic_modified( topic, event ):
	pass
# 	if _is_topic( topic ):
# 		# What's this?
# 		timestamp = datetime.utcnow()
# 		process_event( _modify_topic, topic, timestamp=timestamp )

@component.adapter( frm_interfaces.ITopic, intid_interfaces.IIntIdRemovedEvent )
def _topic_removed( topic, event ):
	if _is_topic( topic ):
		timestamp = datetime.utcnow()
		process_event( _remove_topic, topic, timestamp=timestamp )

# Forum
def _remove_forum( db, oid, timestamp ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		db.delete_forum( timestamp, forum )
		logger.debug( "Forum deleted (forum=%s)", forum )

def _add_forum( db, oid, nti_session=None ):
	forum = ntiids.find_object_with_ntiid( oid )
	if forum is not None:
		user = get_creator( forum )
		course = get_course( forum )
		db.create_forum( user, nti_session, course, forum )
		logger.debug( 'test' )
		logger.debug( 	"Forum created (user=%s) (forum=%s) (course=%s)",
						user, forum, course )

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdAddedEvent )
def _forum_added( forum, event ):
	user = get_creator( forum )
	nti_session = get_nti_session_id( user )
	process_event( _add_forum, forum, nti_session=nti_session )

@component.adapter( frm_interfaces.IForum, lce_interfaces.IObjectModifiedEvent )
def _forum_modified( forum, event ):
	pass

@component.adapter( frm_interfaces.IForum, intid_interfaces.IIntIdRemovedEvent )
def _forum_removed( forum, event ):
	timestamp = datetime.utcnow()
	timestamp = get_deleted_time( forum )
	process_event( _remove_forum, forum, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	# TODO Note comments may end up here...
	result = True
	if frm_interfaces.IForum.providedBy(obj):
		process_event( _add_forum, obj )
	elif _is_topic( obj ):
		process_event( _add_topic, obj )
	elif _is_forum_comment( obj ):
		process_event( _add_comment, obj )
	else:
		result = False

	return result
